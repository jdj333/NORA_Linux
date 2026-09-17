"""GTK shared concept canvas with editable, draggable, per-chat cards."""
import base64
import threading
import time
from collections import deque
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango
from canvas_model import (CATEGORIES, CARD_HEIGHT, CARD_WIDTH, MAX_CARDS,
                          MAX_LINKS, SHAPES, node_height, arrange_graph, reply_scene, make_card, next_position, validate)
from canvas_drawing import connections, node_shape, grid
from canvas_images import ImageRequest
from web_access import WebError, normalize_url
from canvas_intent import directive


class Canvas(Gtk.Box):
    def __init__(self, changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(16)
        self.changed = changed
        self.cards = []
        self.links = []
        self.positions = {}
        self.motion = None
        self.animated = True
        self.image_queue = deque()
        self.image_requests = {}
        self.connect('destroy', self.shutdown)
        self.connect('unmap', self.stop_motion)
        self.widgets = {}
        self.drag = None
        self.loading = False
        self.generation = 0
        header = Gtk.Box(spacing=8)
        title = Gtk.Label(label='CANVAS / SHARED UNDERSTANDING', xalign=0)
        title.get_style_context().add_class('pane-title')
        header.pack_start(title, True, True, 0)
        for title, action in (('Add card', self.edit_card), ('Arrange', self.organize)):
            button = Gtk.Button(label=title)
            button.connect('clicked', action)
            header.pack_start(button, False, False, 0)
        self.pack_start(header, False, False, 0)
        row = Gtk.Box(spacing=8)
        self.follow = Gtk.CheckButton(label='Follow chat')
        self.follow.set_active(True)
        self.follow.connect('toggled', self.follow_changed)
        row.pack_start(self.follow, False, False, 0)
        self.note = Gtk.Label(label='Visual explanations · Drag nodes to explore', xalign=0)
        self.note.get_style_context().add_class('status')
        self.note.set_ellipsize(Pango.EllipsizeMode.END)
        row.pack_start(self.note, True, True, 0)
        self.pack_start(row, False, False, 0)
        self.layout = Gtk.Layout()
        self.layout.get_style_context().add_class('whiteboard')
        self.layout.set_size(550, 220)
        self.wires = Gtk.DrawingArea()
        self.wires.connect('draw', self.draw_connections)
        self.layout.put(self.wires, 0, 0)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_min_content_height(140)
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.layout)
        self.scroll.connect('size-allocate', self.viewport_changed)
        frame = Gtk.Frame()
        frame.add(self.scroll)
        self.pack_start(frame, True, True, 0)
        self.empty = Gtk.Label(label='A shared space for understanding\n\nAsk NORA to explain a concept or process.\n'
                              'She will connect ideas here as we talk.\n\nDrag nodes to explore their connections.', xalign=0)
        self.empty.get_style_context().add_class('status')
        self.layout.put(self.empty, 24, 28)
        self.empty.set_no_show_all(True)
        self.empty.show()

    def viewport_changed(self, *_):
        if hasattr(self, 'empty'):
            self.update_extent()

    def follow_changed(self, *_):
        if not self.loading:
            self.changed()

    def snapshot(self):
        return validate({'cards': self.cards, 'links': self.links, 'follow': self.follow.get_active()})

    def restore(self, state):
        state = validate(state)
        self.loading = True
        self.stop_motion()
        self.cancel_images()
        self.generation += 1
        self.drag = None
        for widget in self.widgets.values():
            widget.destroy()
        self.widgets.clear()
        self.cards = state['cards']
        self.links = state.get('links', [])
        self.follow.set_active(state['follow'])
        for card in self.cards:
            self.render(card)
        self.update_extent()
        self.scroll.get_hadjustment().set_value(0)
        self.scroll.get_vadjustment().set_value(0)
        self.loading = False

    def update_extent(self):
        self.empty.set_visible(not self.cards)
        width = max(280, self.scroll.get_allocated_width() - 4,
                    max((c['x'] + CARD_WIDTH + 40 for c in self.cards), default=0))
        height = max(180, self.scroll.get_allocated_height() - 4, max((c['y'] + node_height(c) + 40 for c in self.cards), default=0))
        self.layout.set_size(width, height)
        self.wires.set_size_request(width, height)
        self.wires.queue_draw()
        lookup = {c['id']: c['title'] for c in self.cards}
        self.wires.get_accessible().set_name('Connections: ' + '; '.join(
            lookup.get(l['from'], '') + ' ' + l['label'] + ' ' + lookup.get(l['to'], '') for l in self.links))
        self.note.set_text(f'{len(self.cards)} nodes · {len(self.links)} connections' if self.cards else
                           'Visual explanations · Drag nodes to explore')

    def draw_connections(self, _widget, cr):
        grid(cr)
        connections(cr, self.cards, self.links, self.positions)
        return False

    def set_animated(self, enabled):
        self.animated = enabled
        if not enabled:
            self.stop_motion()

    def stop_motion(self, *_):
        if self.motion is not None:
            GLib.source_remove(self.motion)
            self.motion = None
        self.positions.clear()
        for card in self.cards:
            widget = self.widgets.get(card['id'])
            if widget:
                widget.set_opacity(1)
                self.layout.move(widget, card['x'], card['y'])
        if hasattr(self, 'wires'):
            self.wires.queue_draw()

    def animate_scene(self, origins, fresh=()):
        self.stop_motion()
        if not (self.animated and self.get_settings().get_property('gtk-enable-animations') and self.get_mapped()):
            return
        started = time.monotonic()
        def tick():
            progress = min(1, (time.monotonic() - started) / 0.45)
            eased = 1 - (1 - progress) ** 3
            if not self.get_settings().get_property('gtk-enable-animations'):
                progress = eased = 1
            for card in self.cards:
                x, y = origins.get(card['id'], (card['x'], card['y'] + 12))
                pos = (round(x + (card['x'] - x) * eased), round(y + (card['y'] - y) * eased))
                self.positions[card['id']] = pos
                self.layout.move(self.widgets[card['id']], *pos)
                if card['id'] in fresh:
                    self.widgets[card['id']].set_opacity(0.2 + 0.8 * eased)
            self.wires.queue_draw()
            if progress == 1:
                self.motion = None
                self.positions.clear()
                return False
            return True
        self.motion = GLib.timeout_add(25, tick)
        tick()

    def cancel_images(self):
        self.image_queue.clear()
        for request in self.image_requests.values():
            request.cancel()
        self.image_requests.clear()

    def shutdown(self, *_):
        self.generation += 1
        self.stop_motion()
        self.cancel_images()

    def add(self, card, notify=True):
        if len(self.cards) >= MAX_CARDS:
            self.note.set_text('Canvas full (60 cards) · Remove a card to add more')
            return False
        card['x'], card['y'] = next_position(self.cards, self.scroll.get_allocated_width())
        self.cards.append(card)
        self.render(card)
        self.update_extent()
        if notify:
            self.changed()
        return True

    def record(self, prompt, answer, source=None, allowed_images=()):
        if not self.follow.get_active():
            return
        gesture = directive(answer) if source is None else None
        if gesture == 'clear':
            self.clear_scene()
            return
        if gesture == 'arrange':
            self.organize()
            return
        nodes, links, images = reply_scene(prompt, answer, source)
        if gesture == 'replace':
            self.clear_scene(generated_only=True)
        # Retire old generated explanations before the board reaches its limit.
        for old in list(self.cards):
            if len(self.cards) + len(nodes) + len(images) <= MAX_CARDS:
                break
            if old.get('generated'):
                self.remove_by_id(old['id'])
        for node in nodes:
            node['generated'] = True
        existing = {c['id'] for c in self.cards}
        # Keep each explanation connected, including repeated concepts across turns.
        mapping = {}
        fresh = set()
        for node in nodes:
            match = next((c for c in self.cards if c['body'] == node['body'] and
                          c['title'] == node['title'] and c['category'] == node['category']), None)
            if match:
                mapping[node['id']] = match['id']
            elif self.add(node, notify=False):
                mapping[node['id']] = node['id']
                fresh.add(node['id'])
        for link in links:
            if link['from'] in mapping and link['to'] in mapping:
                link = dict(link, **{'from': mapping[link['from']], 'to': mapping[link['to']]})
                if link['from'] != link['to'] and link not in self.links and len(self.links) < MAX_LINKS:
                    self.links.append(link)
        if fresh:
            group = [c for c in self.cards if c['id'] in fresh]
            group_links = [l for l in self.links if l['from'] in fresh and l['to'] in fresh]
            arrange_graph(group, group_links, self.scroll.get_allocated_width())
            base = max((c['y'] + node_height(c) + 40 for c in self.cards if c['id'] in existing), default=0)
            for node in group:
                node['y'] = min(20000, node['y'] + base)
            self.update_extent()
            self.animate_scene({c['id']: (c['x'], c['y']) for c in self.cards if c['id'] not in fresh}, fresh)
            if self.get_mapped():
                GLib.idle_add(self.reveal_node, group[0]['id'], self.generation)
        # Model image URLs must be real candidates from the fetched page, not invented.
        for alt, url in images:
            if url in allowed_images:
                self.add_image(url, alt or 'Website image', source or 'Image from the page')
        self.update_extent()
        self.changed()

    def clear_scene(self, generated_only=False):
        for card in list(self.cards):
            # Legacy generated cards predate the explicit ownership flag.
            generated = card.get('generated', card['source'] in (
                'NORA explanation', 'NORA reply · excerpt', 'Your message'))
            if not generated_only or generated:
                self.remove_by_id(card['id'])
        self.update_extent()
        self.changed()

    def reveal_node(self, card_id, generation):
        card = next((c for c in self.cards if c['id'] == card_id), None)
        if card and generation == self.generation:
            self.scroll.get_vadjustment().set_value(max(0, card['y'] - 24))
        return False

    def record_result(self, title, body, source):
        if self.follow.get_active():
            self.add(make_card(title, body, 'Facts', source))

    def record_page(self, page):
        if self.follow.get_active():
            card = make_card(page['title'] or 'Website', page['text'][:420], 'Ideas',
                             'Website excerpt · ' + page['url'] + ' · ' + page['observed_utc'])
            if self.add(card):
                for item in page.get('images', [])[:2]:
                    image = self.add_image(item['url'], item.get('alt') or 'Website image', item.get('source') or page['url'])
                    if image and len(self.links) < MAX_LINKS:
                        self.links.append({'from': card['id'], 'to': image['id'], 'label': 'illustration'})
                self.update_extent()
                self.changed()

    def add_image(self, url, title='Image', source='Your image URL'):
        url = normalize_url(url)
        existing = next((c for c in self.cards if c.get('image_url') == url), None)
        if existing:
            if not existing.get('image_data') and existing['id'] not in self.image_requests and not any(
                    item[0] == existing['id'] for item in self.image_queue):
                existing['image_error'] = ''
                self.image_queue.append((existing['id'], url))
                self.start_images()
            return existing
        card = make_card(title, '', 'Ideas', source)
        card.update(image_url=url, image_data='', image_error='')
        if not self.add(card):
            return None
        self.image_queue.append((card['id'], url))
        self.start_images()
        return card

    def start_images(self):
        while self.image_queue and len(self.image_requests) < 2:
            card_id, url = self.image_queue.popleft()
            request = ImageRequest(url, timeout=20)
            self.image_requests[card_id] = request
            generation = self.generation
            def worker(cid=card_id, req=request, gen=generation):
                try:
                    result, error = req.run(), None
                except (WebError, OSError, ValueError) as exc:
                    result, error = None, str(exc)
                GLib.idle_add(self.image_finished, cid, req, gen, result, error)
            threading.Thread(target=worker, daemon=True).start()

    def image_finished(self, card_id, request, generation, result, error):
        if generation != self.generation or self.image_requests.get(card_id) is not request:
            return False
        self.image_requests.pop(card_id)
        card = next((c for c in self.cards if c['id'] == card_id), None)
        if card:
            card['image_data'] = result['image_data'] if result else ''
            card['image_error'] = (error or '')[:300]
            self.widgets.pop(card_id).destroy()
            self.render(card)
            self.changed()
        self.start_images()
        return False

    def render(self, card):
        frame = Gtk.Overlay()
        frame.get_style_context().add_class('concept-node')
        frame.set_size_request(CARD_WIDTH, node_height(card))
        background = Gtk.DrawingArea()
        background.connect('draw', node_shape, card)
        frame.add(background)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        diamond = card.get('shape') == 'diamond'
        content.set_margin_start(48 if diamond else 12)
        content.set_margin_end(48 if diamond else 12)
        content.set_margin_top(32 if diamond else 12)
        content.set_margin_bottom(24 if diamond else 12)
        frame.add_overlay(content)
        handle = Gtk.EventBox()
        handle.set_visible_window(False)
        handle.set_can_focus(True)
        handle.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                          Gdk.EventMask.POINTER_MOTION_MASK)
        handle.connect('button-press-event', self.drag_start, card)
        handle.connect('motion-notify-event', self.drag_move, card)
        handle.connect('button-release-event', self.drag_end)
        handle.connect('key-press-event', self.move_key, card)
        handle.get_accessible().set_name(f"Move node: {card['title']}")
        handle.set_tooltip_text('Drag to move · Arrow keys move a focused node')
        title = Gtk.Label(label=card['title'], xalign=0.5 if diamond else 0)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_max_width_chars(16 if diamond else 26)
        title.set_width_chars(16 if diamond else 26)
        title.set_tooltip_text(card['title'])
        title.get_style_context().add_class('card-title')
        handle.add(title)
        compact = not card['body'] and not card.get('image_url')
        content.pack_start(handle, compact, compact, 0)
        if card.get('image_url'):
            if card.get('image_data'):
                try:
                    loader = GdkPixbuf.PixbufLoader.new_with_type('png')
                    loader.write(base64.b64decode(card['image_data']))
                    loader.close()
                    image = Gtk.Image.new_from_pixbuf(loader.get_pixbuf())
                    image.get_accessible().set_name(card['title'])
                    content.pack_start(image, True, True, 0)
                except (GLib.Error, ValueError):
                    content.pack_start(Gtk.Label(label='Image unavailable'), True, True, 0)
            else:
                label = Gtk.Label(label='Image unavailable' if card.get('image_error') else
                                  ('Loading image…' if card['id'] in self.image_requests or
                                   any(item[0] == card['id'] for item in self.image_queue) else 'Image pending'))
                label.set_tooltip_text(card.get('image_error') or card['image_url'])
                content.pack_start(label, True, True, 0)
        elif card['body']:
            body = Gtk.Label(label=card['body'], xalign=0.5 if diamond else 0, yalign=0.5)
            body.set_line_wrap(True)
            body.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            body.set_max_width_chars(16 if diamond else 26)
            body.set_width_chars(16 if diamond else 26)
            body.set_lines(2 if diamond else 4)
            body.set_ellipsize(Pango.EllipsizeMode.END)
            body.set_tooltip_text(card['body'])
            content.pack_start(body, True, True, 0)
        footer = Gtk.Box(spacing=2)
        if not diamond:
            source = Gtk.Label(label=card['source'], xalign=0)
            source.set_ellipsize(Pango.EllipsizeMode.END)
            source.set_max_width_chars(16)
            source.set_tooltip_text(card['source'] + ('\n' + card['image_url'] if card.get('image_url') else ''))
            source.get_style_context().add_class('status')
            footer.pack_start(source, True, True, 0)
        for label, icon, callback in (('Edit node', 'document-edit-symbolic', self.edit_card),
                                      ('Remove node', 'edit-delete-symbolic', self.remove_card)):
            button = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.MENU)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class('node-tool')
            button.set_tooltip_text(label)
            button.get_accessible().set_name(label)
            button.connect('clicked', callback, card['id'])
            footer.pack_end(button, False, False, 0)
        content.pack_start(footer, False, False, 0)
        self.widgets[card['id']] = frame
        self.layout.put(frame, card['x'], card['y'])
        frame.show_all()

    def move_card(self, card, x, y):
        card['x'], card['y'] = max(0, min(20000, int(x))), max(0, min(20000, int(y)))
        self.layout.move(self.widgets[card['id']], card['x'], card['y'])
        self.update_extent()

    def drag_start(self, widget, event, card):
        if event.button != 1:
            return False
        self.stop_motion()
        widget.grab_focus()
        self.drag = (card['id'], event.x_root, event.y_root, card['x'], card['y'])
        return True

    def drag_move(self, _widget, event, card):
        if self.drag and self.drag[0] == card['id']:
            _, x, y, start_x, start_y = self.drag
            self.move_card(card, start_x + event.x_root - x, start_y + event.y_root - y)
            return True
        return False

    def drag_end(self, *_):
        if self.drag:
            self.drag = None
            self.changed()
        return False

    def move_key(self, _widget, event, card):
        directions = {Gdk.KEY_Left: (-16, 0), Gdk.KEY_Right: (16, 0), Gdk.KEY_Up: (0, -16), Gdk.KEY_Down: (0, 16)}
        if event.keyval in directions:
            self.stop_motion()
            dx, dy = directions[event.keyval]
            self.move_card(card, card['x'] + dx, card['y'] + dy)
            self.changed()
            return True
        return False

    def organize(self, *_):
        origins = {c['id']: (c['x'], c['y']) for c in self.cards}
        arrange_graph(self.cards, self.links, self.scroll.get_allocated_width())
        self.update_extent()
        self.animate_scene(origins)
        self.changed()

    def remove_card(self, _button, card_id):
        # Defer widget destruction until the clicked button's event has returned.
        GLib.idle_add(self.remove_by_id, card_id)

    def remove_by_id(self, card_id):
        self.stop_motion()
        request = self.image_requests.pop(card_id, None)
        if request:
            request.cancel()
        self.image_queue = deque(item for item in self.image_queue if item[0] != card_id)
        self.links = [link for link in self.links if card_id not in (link['from'], link['to'])]
        widget = self.widgets.pop(card_id, None)
        if widget:
            widget.destroy()
            self.cards = [card for card in self.cards if card['id'] != card_id]
            self.update_extent()
            self.changed()
        self.start_images()
        return False

    def edit_card(self, _button=None, card_id=None):
        card = next((c for c in self.cards if c['id'] == card_id), None)
        dialog = Gtk.Dialog(title='Edit card' if card else 'Add card', transient_for=self.get_toplevel(), modal=True)
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Save card', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(16)
        box.set_spacing(8)
        title = Gtk.Entry()
        title.set_max_length(80)
        title.set_placeholder_text('Card title')
        title.set_text(card['title'] if card else '')
        category = Gtk.ComboBoxText()
        for value in CATEGORIES:
            category.append_text(value)
        category.set_active(CATEGORIES.index(card['category']) if card else 1)
        body = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        body.get_buffer().set_text(card['body'] if card else '')
        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(380, 160)
        scroll.add(body)
        for widget in (title, category, scroll, Gtk.Label(label='Up to 1,200 characters · Cards never run commands')):
            box.add(widget)
        shape = Gtk.ComboBoxText()
        for value in SHAPES:
            shape.append_text(value)
        shape.set_active(SHAPES.index(card.get('shape', 'card')) if card else 0)
        box.add(Gtk.Label(label='Node shape'))
        box.add(shape)
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            buffer = body.get_buffer()
            updated = make_card(title.get_text(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False),
                                category.get_active_text(), 'Your note' if not card else 'Edited by you · ' + card['source'])
            updated['shape'] = shape.get_active_text()
            # Defer replacing the card widget until its Edit button event returns.
            GLib.idle_add(self.save_edit, card_id, updated, self.generation)
        dialog.destroy()

    def save_edit(self, card_id, updated, generation=None):
        if generation is not None and generation != self.generation:
            return False
        card = next((c for c in self.cards if c['id'] == card_id), None)
        if card:
            self.stop_motion()
            updated.update(id=card['id'], x=card['x'], y=card['y'], generated=False)
            self.widgets.pop(card_id).destroy()
            card.update(updated)
            self.render(card)
            self.update_extent()
            self.changed()
        elif card_id is None:
            self.add(updated)
        return False
