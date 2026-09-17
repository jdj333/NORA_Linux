"""A lightweight, original vector emerald inspired by NORA's existing logo."""
import math
import time
import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_foreign('cairo')
from gi.repository import GLib, Gtk
from presence_model import ACTIVE, LABELS, intensity


class EmeraldPresence(Gtk.Box):
    EXPRESSIONS = {'ready': 'smiling', 'loading': 'resting',
                   'thinking': 'curious', 'replying': 'expressive smile',
                   'reading': 'curious', 'command': 'focused', 'stopping': 'resting'}

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.state = 'loading'
        self.started = time.monotonic()
        self.last_chunk = None
        self.settle_at = None
        self.animate = True
        self.paused = False
        self.timer = None
        self.disposed = False
        self.area = Gtk.DrawingArea()
        self.area.set_size_request(76, 76)
        self.area.connect('draw', self.draw)
        self.area.connect('map', self.sync_timer)
        self.area.connect('unmap', self.stop_timer)
        self.pack_start(self.area, False, False, 0)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        words.set_valign(Gtk.Align.CENTER)
        title = Gtk.Label(label='NORA', xalign=0)
        title.get_style_context().add_class('presence-name')
        words.pack_start(title, False, False, 0)
        self.label = Gtk.Label(label=LABELS[self.state], xalign=0)
        self.label.get_style_context().add_class('presence-state')
        words.pack_start(self.label, False, False, 0)
        subtitle = Gtk.Label(label='Your operating system', xalign=0)
        subtitle.get_style_context().add_class('status')
        words.pack_start(subtitle, False, False, 0)
        self.pack_start(words, True, True, 0)
        self.settings = self.get_settings()
        self.settings_handler = self.settings.connect('notify::gtk-enable-animations', self.sync_timer)
        self.connect('destroy', self.shutdown)
        self.update_accessibility()

    def update_accessibility(self):
        self.area.get_accessible().set_name(
            'NORA emerald: ' + LABELS[self.state] + ' (' + self.EXPRESSIONS[self.state] + ')')
        self.area.set_tooltip_text('NORA · ' + LABELS[self.state] + '\nGlow follows activity and incoming reply text.')

    def motion_enabled(self):
        return self.animate and self.settings.get_property('gtk-enable-animations')

    def set_animated(self, enabled):
        self.animate = bool(enabled)
        self.sync_timer()

    def set_paused(self, paused):
        self.paused = paused
        self.sync_timer()

    def set_activity(self, state):
        if self.disposed:
            return
        if state not in LABELS:
            raise ValueError('Unknown NORA activity.')
        self.settle_at = None
        if self.state != state:
            self.state = state
            self.started = time.monotonic()
            self.last_chunk = None
        self.label.set_text(LABELS[state])
        self.update_accessibility()
        self.sync_timer()

    def reply_chunk(self):
        self.set_activity('replying')
        self.last_chunk = time.monotonic()
        self.area.queue_draw()

    def acknowledge(self):
        # Instant local answers get one brief response pulse, not a fake stream.
        self.reply_chunk()
        self.settle_at = time.monotonic() + 0.9
        self.sync_timer()

    def stop_timer(self, *_):
        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None

    def sync_timer(self, *_):
        if self.disposed:
            return
        self.area.queue_draw()
        needed = (not self.paused and self.area.get_mapped() and
                  ((self.motion_enabled() and self.state in ACTIVE) or self.settle_at is not None))
        if needed and self.timer is None:
            self.timer = GLib.timeout_add(50, self.tick)
        elif not needed:
            self.stop_timer()

    def tick(self):
        if self.disposed:
            self.timer = None
            return False
        if self.settle_at is not None and time.monotonic() >= self.settle_at:
            self.timer = None
            self.set_activity('ready')
            return False
        self.area.queue_draw()
        return True

    def shutdown(self, *_):
        if not self.disposed:
            self.stop_timer()
            self.settings.disconnect(self.settings_handler)
            self.disposed = True

    @staticmethod
    def polygon(cr, points):
        cr.move_to(*points[0])
        for point in points[1:]:
            cr.line_to(*point)
        cr.close_path()

    def draw(self, widget, cr):
        now = time.monotonic()
        energy = intensity(self.state, now - self.started,
                           None if self.last_chunk is None else now - self.last_chunk,
                           self.motion_enabled())
        self.paint(cr, widget.get_allocated_width(), widget.get_allocated_height(), energy, self.state)
        return False

    @classmethod
    def paint(cls, cr, width, height, energy, state='ready'):
        """Retain the logo's chevron; let its cursor become an expressive mouth."""
        cr.save()
        cr.translate(width / 2, height / 2)
        scale = min(width, height) / 112
        cr.scale(scale, scale)
        halo = cairo.RadialGradient(0, 0, 10, 0, 0, 53)
        halo.add_color_stop_rgba(0, 0.08, 0.94, 0.57, 0.06 + energy * 0.20)
        halo.add_color_stop_rgba(0.65, 0.03, 0.80, 0.43, 0.05 + energy * 0.13)
        halo.add_color_stop_rgba(1, 0.01, 0.48, 0.25, 0)
        cr.set_source(halo)
        cr.arc(0, 0, 53, 0, math.tau)
        cr.fill()
        # Scale changes stay below 2%; most motion comes from light, not bouncing.
        cr.scale(1 + energy * 0.024, 1 + energy * 0.024)
        outer = [(0, -38), (24, -16), (30, 8), (0, 38), (-30, 8), (-24, -16)]
        inner = [(0, -23), (16, -8), (17, 13), (0, 25), (-17, 13), (-16, -8)]
        colors = [(0.04, 0.68, 0.45), (0.35, 0.98, 0.76), (0.04, 0.53, 0.35),
                  (0.24, 0.92, 0.68), (0.12, 0.72, 0.54), (0.49, 1.0, 0.81)]
        cls.polygon(cr, inner)
        cr.set_source_rgb(0.015, 0.10 + energy * 0.04, 0.07)
        cr.fill()
        for index, color in enumerate(colors):
            nxt = (index + 1) % len(outer)
            gradient = cairo.LinearGradient(*outer[index], *inner[nxt])
            gradient.add_color_stop_rgb(0, *color)
            gradient.add_color_stop_rgb(1, *(channel * 0.50 for channel in color))
            cls.polygon(cr, [outer[index], outer[nxt], inner[nxt], inner[index]])
            cr.set_source(gradient)
            cr.fill_preserve()
            cr.set_source_rgba(0.56, 1, 0.83, 0.27 + energy * 0.22)
            cr.set_line_width(0.65)
            cr.stroke()
            # A fine facet diagonal gives the crystal structure at small sizes.
            cr.move_to(*outer[index])
            cr.line_to(*inner[nxt])
            cr.set_source_rgba(0.50, 1, 0.78, 0.18)
            cr.stroke()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        for thickness, alpha in ((8, 0.06 + energy * 0.12), (3, 0.90)):
            cr.set_source_rgba(0.68, 1, 0.83, alpha)
            cr.set_line_width(thickness)
            cr.move_to(-8, -6)
            cr.line_to(-1, 0)
            cr.line_to(-8, 6)
            if state == 'ready':
                # The website's friendly curved cursor, readable at small sizes.
                cr.move_to(3, 7)
                cr.curve_to(6, 11, 10, 11, 13, 7)
            elif state == 'replying':
                # A small open smile follows the same text-driven energy as the halo.
                # Reduced motion supplies constant energy, so the mouth stays still.
                opening = 2 + energy * 4
                cr.move_to(3, 6)
                cr.curve_to(6, 7, 10, 7, 13, 6)
                cr.curve_to(11, 8 + opening, 5, 8 + opening, 3, 6)
                cr.close_path()
            elif state in ('thinking', 'reading'):
                cr.move_to(3, 8)
                cr.curve_to(7, 9, 10, 7, 13, 5)
            else:
                cr.move_to(3, 7)
                cr.line_to(12, 7)
            cr.stroke()
        cr.restore()
