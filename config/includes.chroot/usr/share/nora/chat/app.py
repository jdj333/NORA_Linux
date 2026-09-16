#!/usr/bin/env python3
"""NORA's GTK chat terminal; launched once per graphical login."""
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk
from client import Cancelled, ChatError, ChatRequest, context, ready

CSS = b'''
window { background: #07130f; color: #def4e9; }
headerbar { background: #10271e; color: #def4e9; border-bottom: 1px solid #215440; }
textview, textview text { background: #07130f; color: #def4e9; }
textview { font-family: monospace; font-size: 14px; }
textview selection { background: #176b4a; color: #ffffff; }
button { background: #153c2b; color: #def4e9; border: 1px solid #28684d; box-shadow: none; }
button:hover { background: #205b40; }
button:disabled { color: #82978c; }
button.suggested-action { background: #2ac784; color: #062517; }
label.status { color: #8fbaa4; font-size: 12px; }
frame { border: 1px solid #28684d; }
'''


class Terminal(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title='NORA Terminal')
        self.set_default_size(940, 630)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.history = []
        self.request = None
        self.closed = False
        self.probing = False
        self.model_ready = False
        self.connect('delete-event', self.close_window)
        header = Gtk.HeaderBar(title='NORA Terminal', subtitle='Local conversation · Qwen2.5 0.5B')
        header.set_show_close_button(True)
        self.set_titlebar(header)
        self.new_button = Gtk.Button(label='New chat')
        self.new_button.connect('clicked', self.clear)
        header.pack_end(self.new_button)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_border_width(18)
        self.add(body)
        self.transcript = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.transcript.set_top_margin(8)
        self.transcript.set_bottom_margin(8)
        self.buffer = self.transcript.get_buffer()
        self.buffer.create_tag('nora', foreground='#44e6a0', weight=700)
        self.buffer.create_tag('you', foreground='#b5d5ff', weight=700)
        self.buffer.create_tag('note', foreground='#8fbaa4')
        self.buffer.create_tag('error', foreground='#ffb29e')
        self.end_mark = self.buffer.create_mark('end', self.buffer.get_end_iter(), False)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.transcript)
        body.pack_start(scroll, True, True, 0)
        self.status = Gtk.Label(label='Loading the offline model…', xalign=0)
        self.status.get_style_context().add_class('status')
        body.pack_start(self.status, False, False, 0)
        frame = Gtk.Frame()
        self.input = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.input.set_left_margin(10)
        self.input.set_right_margin(10)
        self.input.set_top_margin(10)
        self.input.set_bottom_margin(10)
        self.input.set_tooltip_text('Ask NORA a question. Enter sends; Shift+Enter adds a line.')
        self.input.get_accessible().set_name('Message to NORA')
        self.input.connect('key-press-event', self.key_press)
        input_scroll = Gtk.ScrolledWindow()
        input_scroll.set_min_content_height(72)
        input_scroll.set_max_content_height(110)
        input_scroll.add(self.input)
        frame.add(input_scroll)
        body.pack_start(frame, False, False, 0)
        controls = Gtk.Box(spacing=10)
        hint = Gtk.Label(label='Enter to send · Shift+Enter for a new line · /help', xalign=0)
        hint.get_style_context().add_class('status')
        controls.pack_start(hint, True, True, 0)
        self.stop_button = Gtk.Button(label='Stop')
        self.stop_button.set_sensitive(False)
        self.stop_button.connect('clicked', self.stop)
        controls.pack_end(self.stop_button, False, False, 0)
        self.send_button = Gtk.Button(label='Send ↵')
        self.send_button.get_style_context().add_class('suggested-action')
        self.send_button.set_sensitive(False)
        self.send_button.connect('clicked', self.send)
        controls.pack_end(self.send_button, False, False, 0)
        body.pack_start(controls, False, False, 0)
        self.welcome()
        self.show_all()
        self.input.grab_focus()
        self.poll()
        self.poll_source = GLib.timeout_add_seconds(3, self.poll)

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
        self.append('NORA  /  LOCAL CHAT\n\n', 'nora')
        self.append('Hello. Ask me a question, explore an idea, or ask for help with Linux.\n\n')
        self.append('Everything runs on this computer. Chats stay in memory and are cleared when you close this window.\n'
                    'I explain commands; I do not run them. This small model can make mistakes.\n\n', 'note')

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
            self.send_button.set_sensitive(available)
            self.status.set_text('● Offline model ready' if available else
                                 'Waiting for the local model… First startup can take a minute. /help for diagnostics.')
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
        self.history.clear()
        self.buffer.set_text('')
        self.welcome()
        self.input.grab_focus()

    def send(self, *_):
        if self.request:
            return
        buffer = self.input.get_buffer()
        prompt = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()
        if not prompt:
            return
        if prompt in ('/clear', '/help', '/model'):
            buffer.set_text('')
            if prompt == '/clear':
                self.clear()
            elif prompt == '/model':
                self.append('MODEL  Qwen2.5-0.5B-Instruct · Q4_K_M · llama.cpp · offline\n\n', 'note')
            else:
                self.append('HELP\n/clear — new conversation\n/model — model details\n'
                            'Enter — send; Shift+Enter — new line; Escape — stop reply\n'
                            'If the model stays unavailable, open a regular terminal and run:\n'
                            '  systemctl status nora-llm\n  journalctl -u nora-llm -b --no-pager\n\n', 'note')
            return
        if not self.model_ready:
            self.status.set_text('The model is still starting. Your message is kept here; try again when ready.')
            return
        try:
            messages, trimmed = context(self.history, prompt)
        except ChatError as error:
            self.status.set_text(str(error))
            return
        buffer.set_text('')
        self.append('YOU  > ', 'you')
        self.append(prompt + '\n\n')
        if trimmed:
            self.append('[Older turns omitted from the model context to keep the conversation responsive.]\n', 'note')
        self.append('NORA > ', 'nora')
        self.request = request = ChatRequest()
        self.send_button.set_sensitive(False)
        self.new_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)
        self.status.set_text('NORA is thinking…')
        def worker():
            try:
                answer = request.stream(messages, lambda chunk: GLib.idle_add(self.chunk, request, chunk))
                GLib.idle_add(self.finish, request, messages, answer, None)
            except (ChatError, Cancelled) as error:
                GLib.idle_add(self.finish, request, messages, None, error)
        threading.Thread(target=worker, daemon=True).start()

    def chunk(self, request, chunk):
        if self.request is request and not request.cancelled.is_set():
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
        self.append('\n\n')
        self.request = None
        self.stop_button.set_sensitive(False)
        self.new_button.set_sensitive(True)
        self.send_button.set_sensitive(self.model_ready)
        self.status.set_text('● Offline model ready')
        self.input.grab_focus()
        return False

    def stop(self, *_):
        if self.request:
            self.request.cancel()
            self.stop_button.set_sensitive(False)
            self.status.set_text('Stopping reply…')

    def close_window(self, *_):
        self.closed = True
        if self.request:
            self.request.cancel()
        GLib.source_remove(self.poll_source)
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
        window.present()


if __name__ == '__main__':
    Application().run()
