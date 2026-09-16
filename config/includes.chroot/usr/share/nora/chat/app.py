#!/usr/bin/env python3
"""NORA's GTK chat terminal; launched once per graphical login."""
import threading
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk
from client import Cancelled, ChatError, ChatRequest, context, ready
from commands import CommandRequest, change_directory, suggested_command
from system_info import answer as system_answer, inspection_command, model_facts, snapshot, topics

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
        self.cwd = str(Path.home())
        self.last_command = None
        self.request = None
        self.closed = False
        self.probing = False
        self.model_ready = False
        self.connect('delete-event', self.close_window)
        header = Gtk.HeaderBar(title='NORA Terminal', subtitle='NORA Linux · System terminal')
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
        self.status = Gtk.Label(label='OS access ready · Loading the offline model…', xalign=0)
        self.status.get_style_context().add_class('status')
        body.pack_start(self.status, False, False, 0)
        self.proposal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.proposal.set_no_show_all(True)
        proposal_label = Gtk.Label(label='Proposed command — edit it or choose Run to execute', xalign=0)
        self.proposal.pack_start(proposal_label, False, False, 0)
        self.command_input = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.command_input.get_accessible().set_name('Proposed command')
        command_scroll = Gtk.ScrolledWindow()
        command_scroll.set_min_content_height(48)
        command_scroll.set_max_content_height(80)
        command_scroll.add(self.command_input)
        self.proposal.pack_start(command_scroll, False, False, 0)
        self.run_button = Gtk.Button(label='Run command')
        self.run_button.connect('clicked', self.run_proposal)
        self.proposal.pack_start(self.run_button, False, False, 0)
        body.pack_start(self.proposal, False, False, 0)
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
        hint = Gtk.Label(label='Enter to send · /run command · /system · /help', xalign=0)
        hint.get_style_context().add_class('status')
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
        self.append('NORA  /  YOUR LINUX OPERATING SYSTEM\n\n', 'nora')
        self.append('I am NORA Linux. Ask about my disk space, memory, kernel, or running processes.\n'
                    'Use /run followed by a command to act on this system.\n\n')
        self.append('Commands run as your Linux user. Model suggestions have a Run button.\n'
                    'The model runs locally. Chat history clears when this window closes; command changes remain.\n\n', 'note')

    def idle_status(self):
        model = 'Offline model ready' if self.model_ready else 'Model starting; system questions and commands are ready'
        self.status.set_text(f'● {model} · {self.cwd}')

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
        self.history.clear()
        self.last_command = None
        self.proposal.hide()
        self.buffer.set_text('')
        self.welcome()
        self.input.grab_focus()

    def exchange(self, prompt, answer, source=None):
        self.proposal.hide()
        self.append('YOU  > ', 'you')
        self.append(prompt + '\n\n')
        self.append('NORA > ', 'nora')
        self.append(answer + '\n')
        if source:
            self.append(source + '\n', 'note')
        self.append('\n')
        self.history.extend([{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': answer}])
        self.input.get_buffer().set_text('')

    def busy(self, request, label):
        self.request = request
        self.proposal.hide()
        self.send_button.set_sensitive(False)
        self.new_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)
        self.status.set_text(label)

    def run_proposal(self, *_):
        buffer = self.command_input.get_buffer()
        command = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        self.start_command(command, 'Run proposed command')

    def start_command(self, command, prompt):
        if self.request:
            return
        try:
            request = CommandRequest(command, self.cwd)
        except ValueError as error:
            self.status.set_text(str(error))
            return
        self.append('YOU  > ', 'you')
        self.append(prompt + '\n\n')
        self.append('RUN  > ', 'nora')
        self.append(request.command + '\n')
        self.append(f'Working directory: {self.cwd}\n', 'note')
        self.input.get_buffer().set_text('')
        self.busy(request, 'Running command… Stop terminates this command group.')
        def worker():
            try:
                result = request.run(lambda chunk: GLib.idle_add(self.command_chunk, request, chunk))
                GLib.idle_add(self.command_finished, request, prompt, result, None)
            except (OSError, ValueError) as error:
                GLib.idle_add(self.command_finished, request, prompt, None, error)
        threading.Thread(target=worker, daemon=True).start()

    def command_chunk(self, request, chunk):
        if self.request is request:
            self.append(chunk)
        return False

    def command_finished(self, request, prompt, result, error):
        if self.closed or self.request is not request:
            return False
        if error:
            self.append(f'\nCommand could not run: {error}\n\n', 'error')
            self.last_command = {'command': request.command, 'cwd': request.cwd,
                                 'error': str(error), 'reason': 'failed to launch'}
        else:
            self.append('\n' + result.summary() + '\n\n', 'note' if result.exit_code == 0 else 'error')
            self.last_command = result.model_evidence()
            self.history.extend([{'role': 'user', 'content': prompt},
                                 {'role': 'assistant', 'content': f'Command {result.command}: {result.summary()}'}])
        self.request = None
        self.stop_button.set_sensitive(False)
        self.new_button.set_sensitive(True)
        self.send_button.set_sensitive(True)
        self.idle_status()
        self.input.grab_focus()
        return False

    def send(self, *_):
        if self.request:
            return
        buffer = self.input.get_buffer()
        prompt = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()
        if not prompt:
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
                            '/run COMMAND — execute a shell command as your Linux user\n'
                            '/cd PATH — change directory (plain path); /pwd — show directory\n'
                            'Model-proposed shell blocks can be edited and executed with Run command.\n'
                            'Commands have no interactive input; use a regular terminal for password prompts.\n'
                            'Limits: 60 seconds and 32 KiB of output per command.\n'
                            'New chat clears history, not command effects or the working directory.\n'
                            'Enter — send; Shift+Enter — new line; Escape — stop reply\n'
                            'If the model stays unavailable, open a regular terminal and run:\n'
                            '  systemctl status nora-llm\n  journalctl -u nora-llm -b --no-pager\n\n', 'note')
            return
        selected = topics(prompt)
        if selected:
            facts = snapshot(self.cwd)
            answer, source = system_answer(facts, selected)
            self.exchange(prompt, answer, source)
            return
        inspection = inspection_command(prompt)
        if inspection:
            self.start_command(inspection, prompt)
            return
        if not self.model_ready:
            self.status.set_text('The model is still starting. Your message is kept here; try again when ready.')
            return
        try:
            messages, trimmed = context(self.history, prompt, model_facts(snapshot(self.cwd)), self.last_command)
        except ChatError as error:
            self.status.set_text(str(error))
            return
        buffer.set_text('')
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
            command = suggested_command(answer)
            if command:
                self.command_input.get_buffer().set_text(command)
                self.proposal.set_no_show_all(False)
                self.proposal.show_all()
                self.proposal.set_no_show_all(True)
        self.append('\n\n')
        self.request = None
        self.stop_button.set_sensitive(False)
        self.new_button.set_sensitive(True)
        self.send_button.set_sensitive(True)
        self.idle_status()
        self.input.grab_focus()
        return False

    def stop(self, *_):
        if self.request:
            self.request.cancel()
            self.stop_button.set_sensitive(False)
            self.status.set_text('Stopping…')

    def close_window(self, *_):
        self.closed = True
        if self.request:
            if isinstance(self.request, CommandRequest):
                self.request.cancel(kill=True)
            else:
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
