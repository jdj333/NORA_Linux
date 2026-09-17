#!/usr/bin/env python3
"""NORA's GTK chat terminal; launched once per graphical login."""
import threading
import re
import sqlite3
import uuid
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk, Pango
from client import Cancelled, ChatError, ChatRequest, context, ready
from commands import CommandRequest, change_directory, suggested_command
from system_info import answer as system_answer, inspection_command, model_facts, snapshot, topics
from web_access import WebError, WebRequest, evidence as web_evidence, target as web_target
from history_store import HistoryStore
from canvas import Canvas
from canvas_model import evidence as canvas_evidence
from presence import EmeraldPresence
from web_access import normalize_url
from image_search import ImageSearchRequest, search_target
from startup_audio import StartupAudio
from canvas_intent import action as canvas_action, example as canvas_example
from voice import VoiceSession, devices as voice_devices

from style import CSS, COLORS


class Terminal(Gtk.ApplicationWindow):
    def __init__(self, application, history_path=None):
        super().__init__(application=application, title='NORA workspace')
        self.set_default_size(1180, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.history = []
        self.cwd = str(Path.home())
        self.last_command = None
        self.last_page = None
        self.request = None
        self.closed = False
        self.startup_audio = StartupAudio()
        self.voice = VoiceSession(GLib.idle_add, self.voice_event)
        self.probing = False
        self.model_ready = False
        self.store = None
        self.chat_id = uuid.uuid4().hex
        self.chat_title = 'New chat'
        self.restoring = True
        self.save_source = None
        self.connect('delete-event', self.close_window)
        header = Gtk.HeaderBar(title='NORA workspace', subtitle='Local conversation · Visual workspace')
        header.set_show_close_button(True)
        self.set_titlebar(header)
        self.new_button = Gtk.Button(label='New chat')
        self.new_button.connect('clicked', self.clear)
        header.pack_end(self.new_button)
        self.settings_button = Gtk.Button(label='Settings')
        self.settings_button.connect('clicked', self.open_settings)
        header.pack_end(self.settings_button)
        self.voice_button = Gtk.ToggleButton(label='Voice off')
        self.voice_button.set_tooltip_text('Enable local listening and spoken replies for this session')
        self.voice_button.connect('toggled', self.toggle_voice)
        header.pack_end(self.voice_button)
        self.voice_control = Gtk.Button(label='Resume listening')
        self.voice_control.set_no_show_all(True)
        self.voice_control.connect('clicked', self.control_voice)
        header.pack_end(self.voice_control)
        layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(layout)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.set_border_width(12)
        sidebar.get_style_context().add_class('sidebar')
        sidebar.set_size_request(178, -1)
        title = Gtk.Label(label='CONVERSATIONS', xalign=0)
        title.get_style_context().add_class('pane-title')
        sidebar.pack_start(title, False, False, 0)
        self.chat_list = Gtk.ListBox()
        self.chat_list.get_style_context().add_class('chats')
        self.chat_list.connect('row-selected', self.select_chat)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.chat_list)
        sidebar.pack_start(scroll, True, True, 0)
        self.save_status = Gtk.Label(label='Saved on this computer', xalign=0)
        self.save_status.set_line_wrap(True)
        self.save_status.set_max_width_chars(21)
        self.save_status.get_style_context().add_class('status')
        sidebar.pack_start(self.save_status, False, False, 0)
        layout.pack_start(sidebar, False, False, 0)
        self.panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.panes.set_wide_handle(False)
        self.panes.set_position(390)
        layout.pack_start(self.panes, True, True, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_border_width(20)
        body.get_style_context().add_class('conversation')
        body.set_size_request(360, -1)
        self.panes.pack1(body, resize=True, shrink=False)
        self.presence = EmeraldPresence()
        body.pack_start(self.presence, False, False, 0)
        self.connect('window-state-event', self.window_state)
        self.transcript = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.transcript.set_top_margin(8)
        self.transcript.set_bottom_margin(8)
        self.transcript.set_pixels_inside_wrap(3)
        self.transcript.set_pixels_below_lines(2)
        self.buffer = self.transcript.get_buffer()
        self.buffer.create_tag('nora', foreground=COLORS['accent'], weight=700)
        self.buffer.create_tag('you', foreground=COLORS['text'], weight=700)
        self.buffer.create_tag('note', foreground=COLORS['muted'])
        self.buffer.create_tag('error', foreground=COLORS['error'])
        self.end_mark = self.buffer.create_mark('end', self.buffer.get_end_iter(), False)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.transcript)
        body.pack_start(scroll, True, True, 0)
        self.status = Gtk.Label(label='OS access ready · Loading the offline model…', xalign=0)
        self.status.get_style_context().add_class('status')
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(44)
        body.pack_start(self.status, False, False, 0)
        frame = Gtk.Frame()
        frame.get_style_context().add_class('composer')
        self.input = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.input.set_left_margin(10)
        self.input.set_right_margin(10)
        self.input.set_top_margin(10)
        self.input.set_bottom_margin(10)
        self.input.set_tooltip_text('Ask NORA a question. Enter sends; Shift+Enter adds a line.')
        self.input.get_accessible().set_name('Message to NORA')
        self.input.connect('key-press-event', self.key_press)
        input_scroll = Gtk.ScrolledWindow()
        input_scroll.set_min_content_height(58)
        input_scroll.set_max_content_height(110)
        input_scroll.add(self.input)
        frame.add(input_scroll)
        body.pack_start(frame, False, False, 0)
        controls = Gtk.Box(spacing=10)
        hint = Gtk.Label(label='Enter sends · /web URL · /help', xalign=0)
        hint.get_style_context().add_class('status')
        hint.set_line_wrap(True)
        hint.set_max_width_chars(24)
        controls.pack_start(hint, True, True, 0)
        self.stop_button = Gtk.Button(label='Stop')
        self.stop_button.set_sensitive(False)
        self.stop_button.connect('clicked', self.stop)
        controls.pack_end(self.stop_button, False, False, 0)
        self.send_button = Gtk.Button(label='Send ↵')
        self.send_button.get_style_context().add_class('suggested-action')
        self.send_button.set_sensitive(True)
        self.send_button.connect('clicked', self.send)
        controls.pack_end(self.send_button, False, False, 0)
        body.pack_start(controls, False, False, 0)
        self.workspace = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.workspace.set_wide_handle(False)
        self.workspace.set_position(10000)
        self.panes.pack2(self.workspace, resize=True, shrink=False)
        self.canvas = Canvas(self.schedule_save)
        self.workspace.pack1(self.canvas, resize=True, shrink=False)
        self.build_terminal_pane()
        self.welcome()
        try:
            self.store = HistoryStore(history_path)
            self.presence.set_animated(self.store.animation_enabled())
            self.canvas.set_animated(self.store.animation_enabled())
            active = self.store.active()
            if active:
                self.restore_chat(active, self.store.load(active))
        except (OSError, sqlite3.Error, ValueError) as error:
            self.storage_error(error)
            if self.store:
                self.store.close()
                self.store = None
        self.restoring = False
        for buffer in (self.buffer, self.terminal_buffer, self.input.get_buffer(), self.command_input.get_buffer()):
            buffer.connect('changed', self.schedule_save)
        self.persist_chat()
        self.maximize()
        self.show_all()
        self.input.grab_focus()
        self.poll()
        self.poll_source = GLib.timeout_add_seconds(3, self.poll)

    def toggle_voice(self, button):
        if button.get_active():
            if self.request:
                button.set_active(False)
                self.status.set_text('Finish the current operation before enabling voice.')
                return
            self.startup_audio.stop()
            try:
                self.voice.enable()
            except (OSError, RuntimeError) as error:
                button.set_active(False)
                self.status.set_text(str(error))
                return
            if not self.voice.enabled:
                button.set_active(False)
                return
            button.set_label('Voice on')
            self.voice_control.show()
            self.status.set_text('Preparing local voice · microphone opens only while listening')
        else:
            self.voice.disable()
            button.set_label('Voice off')
            self.voice_control.hide()
            if not self.closed:
                self.idle_status()

    def control_voice(self, *_):
        if self.voice.state in ('speaking', 'loading'):
            # Reclaim a device even if native synthesis/loading is still busy.
            self.voice.disable()
            try:
                self.voice.enable()
                if self.request:
                    self.voice.pause()
            except (OSError, RuntimeError) as error:
                self.voice_button.set_active(False)
                self.status.set_text(str(error))
        elif self.voice.state == 'listening':
            self.voice.pause()
            self.voice_control.set_label('Resume listening')
            self.status.set_text('Voice paused · microphone off')
            self.presence.set_activity('ready')
        elif not self.request:
            self.voice.listen()
        else:
            self.status.set_text('NORA will listen after this operation finishes.')

    def voice_event(self, event):
        if self.closed:
            return
        kind = event['event']
        if kind == 'error':
            self.voice_button.set_active(False)
            self.status.set_text('Voice off · ' + event['message'])
        elif kind == 'state':
            state = event['state']
            self.voice_control.set_label('Pause listening' if state == 'listening' else 'Stop voice')
            self.status.set_text(event['message'])
            if state in ('listening', 'speaking'):
                self.presence.audio_activity(state)
            elif not self.request:
                self.presence.set_activity('thinking')
        elif kind == 'level':
            self.presence.audio_activity(event['state'], event['level'])
        elif kind == 'partial':
            self.status.set_text('Hearing: ' + event['text'][:140])
        elif kind == 'transcript':
            text = event['text'].strip()
            self.voice.pause()
            self.voice_control.set_label('Resume listening')
            if self.request or self.buffer_text(self.input.get_buffer()).strip():
                self.append('HEARD > ' + text + '\n[Your current draft was kept.]\n\n', 'note')
                self.status.set_text('Voice paused · finish your draft, then resume listening')
                return
            self.input.get_buffer().set_text(text)
            self.send(from_voice=True)
        elif kind in ('done', 'idle'):
            if not self.request:
                self.voice.listen()

    def voice_reply(self, answer):
        if self.voice.enabled:
            self.voice_control.set_label('Stop voice')
            self.status.set_text('Preparing NORA’s voice · microphone off')
            if not self.voice.speak(answer):
                self.voice.listen()

    def voice_settings(self, content):
        label = Gtk.Label(label='Voice is local and off at every startup. No audio recordings are saved.\n'
                          'Listening pauses while NORA replies. Spoken commands require review.', xalign=0)
        label.set_line_wrap(True)
        content.add(label)
        voice = Gtk.ComboBoxText()
        voice.append('af_heart', 'Heart · American English')
        voice.append('af_bella', 'Bella · American English')
        voice.set_active_id(self.voice.voice)
        voice.connect('changed', lambda box: setattr(self.voice, 'voice', box.get_active_id()))
        content.add(voice)
        inputs, outputs = Gtk.ComboBoxText(), Gtk.ComboBoxText()
        for box, title in ((inputs, 'Microphone · system default'), (outputs, 'Speakers · system default')):
            box.append('default', title)
            box.set_active_id('default')
            content.add(box)
        hint = Gtk.Label(label='Loading audio devices…', xalign=0)
        content.add(hint)
        alive = [True]
        content.connect('destroy', lambda *_: alive.__setitem__(0, False))
        def populate(found, error):
            if not alive[0]:
                return False
            for device in found:
                for box, key in ((inputs, 'input'), (outputs, 'output')):
                    if device[key]:
                        box.append(str(device['id']), device['name'])
            for box, attr in ((inputs, 'input_device'), (outputs, 'output_device')):
                value = getattr(self.voice, attr)
                box.set_active_id(str(value) if value is not None else 'default')
                def select(combo, name=attr):
                    selected = combo.get_active_id()
                    setattr(self.voice, name, None if selected in (None, 'default') else int(selected))
                box.connect('changed', select)
            hint.set_text(error or 'Device and voice choices apply to this application session.')
            return False
        def worker():
            try:
                found = voice_devices()
                GLib.idle_add(populate, found, None)
            except Exception as error:
                GLib.idle_add(populate, [], 'Audio devices unavailable: ' + str(error)[:140])
        threading.Thread(target=worker, daemon=True).start()

    def window_state(self, _window, event):
        self.presence.set_paused(bool(event.new_window_state & Gdk.WindowState.ICONIFIED))
        return False

    @staticmethod
    def buffer_text(buffer):
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    @staticmethod
    def buffer_parts(buffer):
        parts = []
        start = buffer.get_start_iter()
        while not start.is_end():
            end = start.copy()
            end.forward_to_tag_toggle(None)
            tags = [tag.get_property('name') for tag in start.get_tags()]
            parts.append([buffer.get_text(start, end, False), tags[0] if tags else None])
            start = end
        return parts

    def storage_error(self, error):
        self.save_status.set_text('History could not be saved or loaded')
        self.save_status.set_tooltip_text(str(error))

    def schedule_save(self, *_):
        if not self.restoring and not self.closed and self.store and self.save_source is None:
            self.save_source = GLib.timeout_add(750, self.autosave)

    def autosave(self):
        self.save_source = None
        self.persist_chat()
        return False

    def persist_chat(self):
        if self.restoring or not self.store:
            return False
        state = {'version': 1, 'title': self.chat_title, 'history': self.history,
                 'transcript': self.buffer_parts(self.buffer), 'terminal': self.buffer_parts(self.terminal_buffer),
                 'cwd': self.cwd, 'last_command': self.last_command, 'last_page': self.last_page,
                 'draft': self.buffer_text(self.input.get_buffer()),
                 'command_draft': self.buffer_text(self.command_input.get_buffer()),
                 'canvas': self.canvas.snapshot()}
        try:
            self.store.save(self.chat_id, state)
            self.refresh_chats()
            self.save_status.set_text('Saved on this computer')
            self.save_status.set_tooltip_text(str(self.store.path))
            return True
        except (OSError, sqlite3.Error, ValueError) as error:
            self.storage_error(error)
            return False

    def refresh_chats(self):
        self.restoring = True
        try:
            chats = self.store.list_chats()
            existing = {row.chat_id: row for row in self.chat_list.get_children()}
            present = {chat_id for chat_id, _title in chats}
            for chat_id, row in existing.items():
                if chat_id not in present:
                    self.chat_list.remove(row)
            # Keep existing rows alive during pointer/keyboard selection. Removing
            # the clicked row inside row-selected can crash GTK's event handling.
            for chat_id, title in reversed(chats):
                row = existing.get(chat_id)
                if row is None:
                    row = Gtk.ListBoxRow()
                    row.chat_id = chat_id
                    label = Gtk.Label(xalign=0)
                    label.set_ellipsize(Pango.EllipsizeMode.END)
                    label.set_max_width_chars(20)
                    label.set_width_chars(20)
                    row.add(label)
                    self.chat_list.insert(row, 0)
                row.get_child().set_text(title)
                row.set_tooltip_text(title)
                if chat_id == self.chat_id:
                    self.chat_list.select_row(row)
            self.chat_list.show_all()
        finally:
            self.restoring = False

    def restore_chat(self, chat_id, state):
        self.restoring = True
        try:
            self.chat_id, self.chat_title = chat_id, state['title']
            self.history = state['history']
            self.last_command, self.last_page = state.get('last_command'), state.get('last_page')
            self.cwd = state['cwd'] if Path(state['cwd']).is_dir() else str(Path.home())
            for buffer, key in ((self.buffer, 'transcript'), (self.terminal_buffer, 'terminal')):
                buffer.set_text('')
                for text, tag in state[key]:
                    end = buffer.get_end_iter()
                    if tag and buffer.get_tag_table().lookup(tag):
                        buffer.insert_with_tags_by_name(end, text, tag)
                    else:
                        buffer.insert(end, text)
            self.input.get_buffer().set_text(state['draft'])
            self.command_input.get_buffer().set_text(state['command_draft'])
            self.canvas.restore(state.get('canvas'))
            self.command_label.set_text('Command · Enter runs, Shift+Enter adds a line')
            self.terminal_status.set_text('Ready · Restored commands are not rerun')
            self.idle_status()
        finally:
            self.restoring = False

    def select_chat(self, _list, row):
        if self.restoring or self.request or row is None or row.chat_id == self.chat_id:
            return
        self.voice_button.set_active(False)
        chat_id = row.chat_id
        if not self.persist_chat():
            return
        try:
            state = self.store.load(chat_id)
            self.restore_chat(chat_id, state)
            self.persist_chat()
        except (OSError, sqlite3.Error, ValueError) as error:
            self.storage_error(error)

    def name_chat(self, prompt):
        if self.chat_title == 'New chat':
            self.chat_title = ' '.join(prompt.split())[:70] or 'New chat'

    def reset_chat(self):
        self.voice_button.set_active(False)
        self.restoring = True
        self.chat_id, self.chat_title = uuid.uuid4().hex, 'New chat'
        self.history = []
        self.last_command = self.last_page = None
        self.cwd = str(Path.home())
        self.buffer.set_text('')
        self.terminal_buffer.set_text('')
        self.input.get_buffer().set_text('')
        self.command_input.get_buffer().set_text('')
        self.canvas.restore(None)
        self.command_label.set_text('Command · Enter runs, Shift+Enter adds a line')
        self.terminal_status.set_text('Ready · Commands run as your Linux user')
        self.welcome()
        self.idle_status()
        self.restoring = False
        self.persist_chat()

    def open_settings(self, *_):
        self.voice_button.set_active(False)
        dialog = Gtk.Dialog(title='NORA Settings', transient_for=self, modal=True)
        dialog.add_button('Close', Gtk.ResponseType.CLOSE)
        content = dialog.get_content_area()
        content.set_border_width(20)
        content.set_spacing(16)
        self.voice_settings(content)
        animation = Gtk.CheckButton(label='Animate NORA and the canvas')
        animation.set_active(self.presence.animate)
        animation.connect('toggled', self.change_animation)
        content.add(animation)
        label = Gtk.Label(label='Chats and context are saved locally on this computer.\n'
                          'A live session without persistent storage loses them at shutdown.', xalign=0)
        label.set_line_wrap(True)
        label.set_max_width_chars(62)
        content.add(label)
        button = Gtk.Button(label='Clear all history and contexts…')
        button.set_sensitive(not self.request and self.store is not None)
        button.connect('clicked', self.confirm_clear_history, dialog)
        content.add(button)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def change_animation(self, button):
        self.presence.set_animated(button.get_active())
        self.canvas.set_animated(button.get_active())
        if self.store:
            try:
                self.store.set_animation(button.get_active())
            except (OSError, sqlite3.Error) as error:
                self.storage_error(error)

    def confirm_clear_history(self, _button, parent):
        dialog = Gtk.MessageDialog(transient_for=parent, modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   text='Clear all saved chats and contexts?')
        dialog.format_secondary_text('This deletes all conversations, canvas cards, drafts, terminal history, and saved '
                                     'website and command context. It cannot be undone. Files changed by commands remain.')
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Clear all', Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            if self.clear_all_history():
                parent.response(Gtk.ResponseType.CLOSE)

    def clear_all_history(self):
        if self.request or not self.store:
            return False
        try:
            self.store.clear()
        except (OSError, sqlite3.Error) as error:
            self.storage_error(error)
            return False
        if self.save_source is not None:
            GLib.source_remove(self.save_source)
            self.save_source = None
        self.reset_chat()
        return True

    def build_terminal_pane(self):
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.workspace.pack2(shell, resize=False, shrink=False)
        self.terminal_toggle = Gtk.ToggleButton(label='▸ Terminal · Show commands')
        self.terminal_toggle.set_margin_start(10)
        self.terminal_toggle.set_margin_end(10)
        self.terminal_toggle.set_margin_top(5)
        self.terminal_toggle.set_margin_bottom(5)
        shell.pack_start(self.terminal_toggle, False, False, 0)
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.terminal_body = pane
        pane.set_border_width(10)
        pane.set_size_request(320, 240)
        shell.pack_start(pane, True, True, 0)
        heading = Gtk.Box(spacing=8)
        title = Gtk.Label(label='TERMINAL', xalign=0)
        title.get_style_context().add_class('pane-title')
        heading.pack_start(title, True, True, 0)
        self.clear_terminal_button = Gtk.Button(label='Clear output')
        self.clear_terminal_button.connect('clicked', self.clear_terminal)
        heading.pack_end(self.clear_terminal_button, False, False, 0)
        pane.pack_start(heading, False, False, 0)
        self.directory = Gtk.Label(label=self.cwd, xalign=0)
        self.directory.set_selectable(True)
        self.directory.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.directory.set_max_width_chars(30)
        self.directory.get_style_context().add_class('status')
        heading.pack_start(self.directory, True, True, 0)
        self.terminal_view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.NONE)
        self.terminal_view.get_accessible().set_name('Command output')
        self.terminal_view.get_style_context().add_class('terminal')
        self.terminal_view.set_left_margin(10)
        self.terminal_view.set_right_margin(10)
        self.terminal_view.set_top_margin(10)
        self.terminal_buffer = self.terminal_view.get_buffer()
        self.terminal_buffer.create_tag('command', foreground=COLORS['accent'], weight=700)
        self.terminal_buffer.create_tag('note', foreground=COLORS['muted'])
        self.terminal_buffer.create_tag('error', foreground=COLORS['error'])
        self.terminal_end = self.terminal_buffer.create_mark('end', self.terminal_buffer.get_end_iter(), False)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(64)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.terminal_view)
        frame = Gtk.Frame()
        frame.add(scroll)
        pane.pack_start(frame, True, True, 0)
        self.terminal_status = Gtk.Label(label='Ready · Commands run as your Linux user', xalign=0)
        self.terminal_status.set_ellipsize(Pango.EllipsizeMode.END)
        self.terminal_status.get_style_context().add_class('status')
        pane.pack_start(self.terminal_status, False, False, 0)
        self.command_label = Gtk.Label(label='Command · Enter runs, Shift+Enter adds a line', xalign=0)
        self.command_label.set_line_wrap(True)
        self.command_label.set_max_width_chars(40)
        pane.pack_start(self.command_label, False, False, 0)
        self.command_input = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.command_input.get_accessible().set_name('Terminal command')
        self.command_input.get_style_context().add_class('terminal')
        self.command_input.set_left_margin(10)
        self.command_input.set_top_margin(10)
        self.command_input.connect('key-press-event', self.command_key_press)
        command_scroll = Gtk.ScrolledWindow()
        command_scroll.set_min_content_height(34)
        command_scroll.set_max_content_height(64)
        command_scroll.add(self.command_input)
        frame = Gtk.Frame()
        frame.add(command_scroll)
        pane.pack_start(frame, False, False, 0)
        controls = Gtk.Box(spacing=10)
        hint = Gtk.Label(label='/cd path · /pwd · Escape stops', xalign=0)
        hint.set_line_wrap(True)
        hint.set_max_width_chars(22)
        hint.get_style_context().add_class('status')
        controls.pack_start(hint, True, True, 0)
        self.terminal_stop_button = Gtk.Button(label='Stop')
        self.terminal_stop_button.set_sensitive(False)
        self.terminal_stop_button.connect('clicked', self.stop)
        controls.pack_end(self.terminal_stop_button, False, False, 0)
        self.run_button = Gtk.Button(label='Run command')
        self.run_button.get_style_context().add_class('suggested-action')
        self.run_button.connect('clicked', self.run_proposal)
        controls.pack_end(self.run_button, False, False, 0)
        pane.pack_start(controls, False, False, 0)
        self.append_terminal('NORA command terminal\nCommands, output, and exit status appear here.\n\n', 'note')
        pane.show_all()
        pane.set_no_show_all(True)
        pane.hide()
        self.terminal_toggle.connect('toggled', self.toggle_terminal)

    def toggle_terminal(self, button):
        expanded = button.get_active()
        self.terminal_body.set_visible(expanded)
        button.set_label('▾ Terminal · Hide commands' if expanded else '▸ Terminal · Show commands')
        self.workspace.set_position(max(180, self.workspace.get_allocated_height() - 300) if expanded else 10000)
        if expanded:
            self.command_input.grab_focus()

    def append_terminal(self, text, tag=None):
        if self.closed:
            return False
        end = self.terminal_buffer.get_end_iter()
        if tag:
            self.terminal_buffer.insert_with_tags_by_name(end, text, tag)
        else:
            self.terminal_buffer.insert(end, text)
        self.terminal_view.scroll_mark_onscreen(self.terminal_end)
        return False

    def clear_terminal(self, *_):
        if not isinstance(self.request, CommandRequest):
            self.terminal_buffer.set_text('')

    def command_key_press(self, widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not event.state & Gdk.ModifierType.SHIFT_MASK:
            self.run_proposal()
            return True
        if event.keyval == Gdk.KEY_Escape and isinstance(self.request, CommandRequest):
            self.stop()
            return True
        return False

    def append(self, text, tag=None):
        if self.closed:
            return False
        end = self.buffer.get_end_iter()
        if tag:
            self.buffer.insert_with_tags_by_name(end, text, tag)
        else:
            self.buffer.insert(end, text)
        self.transcript.scroll_mark_onscreen(self.end_mark)
        return False

    def welcome(self):
        self.append('NORA  /  YOUR LINUX OPERATING SYSTEM\n\n', 'nora')
        self.append('I am NORA Linux. Ask about my disk space, memory, kernel, or running processes.\n'
                    'Use the terminal below the canvas to run commands, or /web URL to read a website.\n\n')
        self.append('I connect ideas visually on our canvas. Ask for a concept map or a process; '
                    'drag nodes to explore the connections.\n\n', 'note')
        self.append('Commands and their output appear in the terminal. Review NORA’s suggestions there before Run.\n'
                    'Chats and context are saved locally. Switch chats on the left; manage history in Settings.\n\n', 'note')

    def idle_status(self):
        if not self.request:
            if not self.voice.enabled or self.voice.state == 'waiting':
                self.presence.set_activity('ready' if self.model_ready else 'loading')
        model = 'Offline model ready' if self.model_ready else 'Model starting; system questions and commands are ready'
        if not self.voice.enabled:
            self.status.set_text(f'● {model}')
        self.directory.set_text(self.cwd)
        self.chat_list.set_sensitive(not self.request)
        self.settings_button.set_sensitive(not self.request)

    def poll(self):
        if self.closed:
            return False
        if not self.probing and not self.request:
            self.probing = True
            def worker():
                available = ready()
                GLib.idle_add(self.health_result, available)
            threading.Thread(target=worker, daemon=True).start()
        return True

    def health_result(self, available):
        self.probing = False
        if self.closed:
            return False
        self.model_ready = available
        if not self.request:
            self.send_button.set_sensitive(True)
            self.idle_status()
        return False

    def key_press(self, widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not event.state & Gdk.ModifierType.SHIFT_MASK:
            self.send()
            return True
        if event.keyval == Gdk.KEY_Escape and self.request:
            self.stop()
            return True
        return False

    def clear(self, *_):
        if self.request:
            return
        if self.store and not self.persist_chat():
            return
        self.reset_chat()
        self.input.grab_focus()

    def exchange(self, prompt, answer, source=None, draw=True):
        self.name_chat(prompt)
        self.append('YOU  > ', 'you')
        self.append(prompt + '\n\n')
        self.append('NORA > ', 'nora')
        self.append(answer + '\n')
        if source:
            self.append(source + '\n', 'note')
        self.append('\n')
        self.history.extend([{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': answer}])
        if draw:
            self.canvas.record(prompt, answer, source)
        self.presence.acknowledge()
        self.input.get_buffer().set_text('')
        self.schedule_save()

        self.voice_reply(answer)

    def busy(self, request, label):
        self.voice.pause()
        self.request = request
        self.presence.set_activity('command' if isinstance(request, CommandRequest) else
                                   'reading' if isinstance(request, WebRequest) else 'thinking')
        self.chat_list.set_sensitive(False)
        self.settings_button.set_sensitive(False)
        self.send_button.set_sensitive(False)
        self.new_button.set_sensitive(False)
        command = isinstance(request, CommandRequest)
        self.stop_button.set_sensitive(not command)
        self.terminal_stop_button.set_sensitive(command)
        self.clear_terminal_button.set_sensitive(not command)
        self.run_button.set_sensitive(False)
        self.status.set_text(label)
        self.schedule_save()

    def run_proposal(self, *_):
        if self.request:
            return
        buffer = self.command_input.get_buffer()
        command = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()
        if command == '/cd' or command.startswith('/cd '):
            try:
                self.cwd = change_directory(command[3:], self.cwd)
                self.append_terminal(f'$ {command}\n{self.cwd}\n\n', 'note')
                buffer.set_text('')
                self.idle_status()
                self.terminal_status.set_text('Ready')
                self.schedule_save()
            except (OSError, ValueError) as error:
                self.terminal_status.set_text(str(error))
            return
        if command == '/pwd':
            self.append_terminal(f'$ /pwd\n{self.cwd}\n\n', 'note')
            buffer.set_text('')
            return
        self.start_command(command, 'Terminal command', from_terminal=True)

    def start_command(self, command, prompt, from_terminal=False):
        if self.request:
            return
        try:
            request = CommandRequest(command, self.cwd)
        except ValueError as error:
            self.terminal_status.set_text(str(error))
            return
        self.terminal_toggle.set_active(True)
        self.name_chat(command if from_terminal else prompt)
        if not from_terminal:
            self.append('YOU  > ', 'you')
            self.append(prompt + '\n\n')
            self.append('NORA > Running in the terminal on the right.\n\n', 'note')
            self.input.get_buffer().set_text('')
        self.command_from_terminal = from_terminal
        self.append_terminal(f'{self.cwd}\n', 'note')
        self.append_terminal('$ ' + request.command + '\n', 'command')
        if from_terminal:
            self.command_input.get_buffer().set_text('')
            self.command_label.set_text('Command · Enter runs, Shift+Enter adds a line')
        self.terminal_status.set_text('Running… Escape or Stop terminates this command.')
        self.busy(request, 'Command running in the terminal →')
        def worker():
            try:
                result = request.run(lambda chunk: GLib.idle_add(self.command_chunk, request, chunk))
                GLib.idle_add(self.command_finished, request, prompt, result, None)
            except (OSError, ValueError) as error:
                GLib.idle_add(self.command_finished, request, prompt, None, error)
        threading.Thread(target=worker, daemon=True).start()

    def command_chunk(self, request, chunk):
        if self.request is request:
            self.append_terminal(chunk)
        return False

    def command_finished(self, request, prompt, result, error):
        if self.closed or self.request is not request:
            return False
        if error:
            self.append_terminal(f'\nCommand could not run: {error}\n\n', 'error')
            self.terminal_status.set_text('Command could not run')
            self.last_command = {'command': request.command, 'cwd': request.cwd,
                                 'error': str(error), 'reason': 'failed to launch'}
        else:
            self.append_terminal('\n' + result.summary() + '\n\n', 'note' if result.exit_code == 0 else 'error')
            self.terminal_status.set_text(result.summary())
            self.last_command = result.model_evidence()
            self.canvas.record_result(result.command, result.summary() + '\n' + result.output[:400],
                                      'Command result · ' + result.cwd)
            self.history.extend([{'role': 'user', 'content': prompt},
                                 {'role': 'assistant', 'content': f'Command {result.command}: {result.summary()}'}])
        self.request = None
        self.stop_button.set_sensitive(False)
        self.terminal_stop_button.set_sensitive(False)
        self.clear_terminal_button.set_sensitive(True)
        self.run_button.set_sensitive(True)
        self.new_button.set_sensitive(True)
        self.send_button.set_sensitive(True)
        self.idle_status()
        self.schedule_save()
        (self.command_input if self.command_from_terminal else self.input).grab_focus()
        if self.voice.enabled:
            self.voice_reply('Command stopped.' if request.cancelled.is_set() else
                             'The command failed. See the terminal for details.' if error else
                             'The command has finished. Its output is in the terminal.')
        return False

    def read_website(self, url, prompt, request_type=WebRequest):
        self.name_chat(prompt)
        request = request_type(url)
        self.last_page = None
        self.append('YOU  > ', 'you')
        self.append(prompt + '\n\n')
        self.append('WEB  > ', 'nora')
        self.append('Finding images on Wikimedia Commons…\n' if request_type is ImageSearchRequest else
                    f'Reading {url}\n', 'note')
        self.input.get_buffer().set_text('')
        self.busy(request, 'Reading website… Stop cancels the request.')
        def worker():
            try:
                page = request.run()
                GLib.idle_add(self.website_finished, request, prompt, page, None)
            except (WebError, OSError, ValueError) as error:
                GLib.idle_add(self.website_finished, request, prompt, None, error)
        threading.Thread(target=worker, daemon=True).start()

    def website_finished(self, request, prompt, page, error):
        if self.closed or self.request is not request:
            return False
        if request.cancelled.is_set():
            self.append('Website read stopped.\n\n', 'note')
        elif error:
            self.append(str(error) + '\n\n', 'error')
        else:
            self.last_page = page
            self.canvas.record_page(page)
            self.append((page['title'] or 'Website text') + '\n', 'nora')
            self.append(f"Source: {page['url']}\nRead at {page['observed_utc']}\n\n", 'note')
            self.append(page['text'][:6000] + '\n\n')
            if page['truncated'] or len(page['text']) > 6000:
                self.append('[Page excerpt; some content was omitted.]\n', 'note')
            if page['links']:
                self.append('Links on this page (use /web URL to read one):\n' +
                            '\n'.join(page['links'][:6]) + '\n\n', 'note')
            self.append('I read this page. Ask me to summarize it or ask a follow-up question.\n\n', 'note')
            self.history.extend([{'role': 'user', 'content': prompt},
                                 {'role': 'assistant', 'content': f"Read website: {page['url']}. See WEB_PAGE for its text."}])
        self.request = None
        self.stop_button.set_sensitive(False)
        self.run_button.set_sensitive(True)
        self.new_button.set_sensitive(True)
        self.send_button.set_sensitive(True)
        self.idle_status()
        self.schedule_save()
        self.input.grab_focus()
        if self.voice.enabled:
            self.voice_reply('Website read stopped.' if request.cancelled.is_set() else
                             'I could not read that page. The details are in chat.' if error else
                             'I read the page. Ask me to summarize it or ask a follow-up question.')
        return False

    def send(self, *_, from_voice=False):
        if self.request:
            return
        buffer = self.input.get_buffer()
        prompt = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()
        if not prompt:
            return
        self.voice.pause()
        if from_voice and (prompt.startswith('/') or canvas_action(prompt) == 'clear'):
            self.status.set_text('Voice paused · review the recognized action and press Send')
            return
        gesture = canvas_action(prompt)
        if gesture:
            if gesture == 'clear':
                self.canvas.clear_scene()
                answer = 'I’ve cleared our canvas for a fresh idea. Our conversation is still here.'
            else:
                self.canvas.organize()
                answer = 'I’ve arranged our canvas so the relationships are easier to follow.'
            self.exchange(prompt, answer, draw=False)
            return
        sketch = canvas_example(prompt)
        if sketch:
            self.exchange(prompt, sketch)
            return
        image_match = re.match(r'(?i)^(?:/image\s+|(?:please\s+)?show\s+(?:me\s+)?(?:an?\s+)?image\s+)(\S+)\s*$', prompt)
        if prompt == '/image' or image_match:
            try:
                if not image_match:
                    raise WebError('Usage: /image https://example.com/picture.png')
                url = normalize_url(image_match.group(1))
                if not self.canvas.add_image(url, 'Your image', url):
                    raise WebError('Canvas full. Remove a node before adding an image.')
                self.name_chat(prompt)
                self.append('YOU  > ' + prompt + '\n\n')
                self.append('NORA > I’m loading that image on our canvas.\n\n', 'nora')
                buffer.set_text('')
                self.schedule_save()
            except WebError as error:
                self.status.set_text(str(error))
            return
        if prompt == '/run' or prompt.startswith('/run '):
            self.start_command(prompt[4:].strip(), prompt)
            return
        if prompt == '/cd' or prompt.startswith('/cd '):
            try:
                self.cwd = change_directory(prompt[3:], self.cwd)
                self.exchange(prompt, f'My command working directory is now {self.cwd}.')
                self.idle_status()
            except (OSError, ValueError) as error:
                self.status.set_text(str(error))
            return
        if prompt == '/pwd':
            self.exchange(prompt, f'My command working directory is {self.cwd}.')
            return
        if prompt in ('/clear', '/help', '/model'):
            buffer.set_text('')
            if prompt == '/clear':
                self.clear()
            elif prompt == '/model':
                self.append('MODEL  Qwen2.5-0.5B-Instruct · Q4_K_M · llama.cpp · offline\n\n', 'note')
            else:
                self.append('HELP\n/clear — new conversation\n/model — model details\n'
                            '/system /disk /memory /cpu /uptime — live OS facts\n'
                            '/files /network /processes — run a read-only inspection\n'
                            '/web URL — read an HTML/text website; bare URLs and “Look up example.com” work too\n'
                            '/image URL — show a public PNG/JPEG/WebP image on the canvas\n'
                            '/images TOPIC — find images on Wikimedia Commons; “Show images of TOPIC” works too\n'
                            'Ask a follow-up to summarize or discuss the most recently read page.\n'
                            '/run COMMAND — execute a shell command as your Linux user\n'
                            '/cd PATH — change directory (plain path); /pwd — show directory\n'
                            'Commands run in the right terminal pane. Type there directly, or use /run here.\n'
                            'Model proposals appear in the terminal input; review or edit them before Run.\n'
                            'Commands have no interactive input; use a regular terminal for password prompts.\n'
                            'Limits: 60 seconds and 32 KiB of output per command.\n'
                            'New chat saves this chat and starts a fresh context. Select saved chats on the left.\n'
                            'Canvas: Follow chat maps explanations as connected nodes; Arrange moves them together.\n'
                            'Use the pencil/trash icons to edit/remove nodes. Website images include their source.\n'
                            'Drag card headers (or focus and use arrow keys) to move them. Cards never run commands.\n'
                            'Settings can delete all history and contexts. Clear output clears the terminal display.\n'
                            'Deleting history does not undo commands.\n'
                            'Enter — send; Shift+Enter — new line; Escape — stop reply\n'
                            'If the model stays unavailable, open a regular terminal and run:\n'
                            '  systemctl status nora-llm\n  sudo journalctl -u nora-llm -b --no-pager\n\n', 'note')
            return
        try:
            search_url = search_target(prompt)
            if search_url:
                self.read_website(search_url, prompt, ImageSearchRequest)
                return
            url = web_target(prompt)
            if url:
                self.read_website(url, prompt)
                return
        except WebError as error:
            self.status.set_text(str(error))
            return
        page_question = self.last_page and re.search(r'\b(page|website|site|article|it|they|their)\b', prompt, re.I)
        selected = [] if page_question else topics(prompt)
        if selected:
            facts = snapshot(self.cwd)
            answer, source = system_answer(facts, selected)
            self.exchange(prompt, answer, source)
            return
        inspection = None if from_voice else inspection_command(prompt)
        if inspection:
            self.start_command(inspection, prompt)
            return
        if not self.model_ready:
            self.status.set_text('The model is still starting. Your message is kept here; try again when ready.')
            return
        try:
            messages, trimmed = context(self.history, prompt, model_facts(snapshot(self.cwd)), self.last_command,
                                        web_evidence(self.last_page, prompt) if self.last_page else None,
                                        canvas_evidence(self.canvas.cards))
        except ChatError as error:
            self.status.set_text(str(error))
            return
        buffer.set_text('')
        self.name_chat(prompt)
        self.append('YOU  > ', 'you')
        self.append(prompt + '\n\n')
        if trimmed:
            self.append('[Older turns omitted from the model context to keep the conversation responsive.]\n', 'note')
        self.append('NORA > ', 'nora')
        request = ChatRequest()
        self.busy(request, 'NORA is thinking with current OS facts…')
        def worker():
            try:
                answer = request.stream(messages, lambda chunk: GLib.idle_add(self.chunk, request, chunk))
                GLib.idle_add(self.finish, request, messages, answer, None)
            except (ChatError, Cancelled) as error:
                GLib.idle_add(self.finish, request, messages, None, error)
        threading.Thread(target=worker, daemon=True).start()

    def chunk(self, request, chunk):
        if self.request is request and not request.cancelled.is_set():
            self.presence.reply_chunk()
            self.append(chunk)
            self.status.set_text('NORA is replying…')
        return False

    def finish(self, request, messages, answer, error):
        if self.closed or self.request is not request:
            return False
        if request.cancelled.is_set() or isinstance(error, Cancelled):
            self.append('\n[Reply stopped. This exchange was not added to context.]', 'note')
        elif error:
            self.append('\n' + str(error), 'error')
            # Restore failed input, unless the user has already drafted the next message.
            if self.input.get_buffer().get_char_count() == 0:
                self.input.get_buffer().set_text(messages[-1]['content'])
        else:
            self.history = messages[1:] + [{'role': 'assistant', 'content': answer}]
            self.canvas.record(messages[-1]['content'], answer,
                               allowed_images=[image['url'] for image in self.last_page.get('images', [])]
                               if self.last_page else ())
            if self.last_page:
                self.append(f"\nSource: {self.last_page['url']} (read {self.last_page['observed_utc']})", 'note')
            command = suggested_command(answer)
            if command:
                if self.command_input.get_buffer().get_char_count() == 0:
                    self.command_input.get_buffer().set_text(command)
                    self.terminal_toggle.set_active(True)
                    self.command_label.set_text('Proposed by NORA · Review or edit, then Run')
                    self.terminal_status.set_text('Proposed command ready · Not executed')
                    self.append('\n[Command prepared in the terminal on the right. Choose Run to execute.]', 'note')
                else:
                    self.append('\n[Your terminal draft was kept. Copy the suggested command there to run it.]', 'note')
        self.append('\n\n')
        self.request = None
        self.stop_button.set_sensitive(False)
        self.run_button.set_sensitive(True)
        self.new_button.set_sensitive(True)
        self.send_button.set_sensitive(True)
        self.idle_status()
        self.schedule_save()
        self.input.grab_focus()
        if not error and not request.cancelled.is_set():
            self.voice_reply(answer)
        elif self.voice.enabled:
            self.voice.listen()
        return False

    def stop(self, *_):
        if self.request:
            self.presence.set_activity('stopping')
            self.request.cancel()
            self.stop_button.set_sensitive(False)
            self.terminal_stop_button.set_sensitive(False)
            if isinstance(self.request, CommandRequest):
                self.terminal_status.set_text('Stopping command…')
            else:
                self.status.set_text('Stopping…')

    def close_window(self, *_):
        if self.closed:
            return False
        if self.request:
            if isinstance(self.request, CommandRequest):
                self.request.cancel(kill=True)
                self.append_terminal('\n[Interrupted when this window closed; final exit status unavailable.]\n', 'note')
                self.last_command = None
            else:
                self.request.cancel()
                self.append('\n[Interrupted when this window closed; incomplete reply is not in context.]\n', 'note')
        if self.store and not self.persist_chat():
            return True
        self.closed = True
        self.voice.disable()
        self.startup_audio.stop()
        self.presence.shutdown()
        self.canvas.shutdown()
        if self.save_source is not None:
            GLib.source_remove(self.save_source)
            self.save_source = None
        GLib.source_remove(self.poll_source)
        if self.store:
            self.store.close()
        self.history.clear()
        return False


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.noralinux.Terminal', flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            window = Terminal(self)
            GLib.idle_add(window.startup_audio.play)
        window.present()


if __name__ == '__main__':
    Application().run()
