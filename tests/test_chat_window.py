"""GTK integration checks; run with a display or xvfb-run on Linux."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.environ.get('NORA_CHAT_DIR', str(
    Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat')))
try:
    from app import Terminal, Gtk, GLib, Gio
    from client import ChatRequest
    from canvas_model import make_card
    GUI_AVAILABLE = Gtk.init_check()[0]
except (ImportError, ValueError):
    GUI_AVAILABLE = False


@unittest.skipUnless(GUI_AVAILABLE, 'GTK3 and a display are required (use xvfb-run)')
class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = Gtk.Application(application_id='org.noralinux.WindowTests',
                                          flags=Gio.ApplicationFlags.NON_UNIQUE)
        cls.application.register(None)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        poll = patch.object(Terminal, 'poll', return_value=True)
        poll.start()
        self.addCleanup(poll.stop)
        self.history_path = Path(self.temp.name) / 'state/chats.sqlite3'
        self.window = Terminal(self.application, history_path=self.history_path)
        self.window.cwd = self.temp.name
        self.window.model_ready = True
        self.window.idle_status()

    def tearDown(self):
        self.window.close_window()
        self.window.destroy()
        self.drain()

    def enable_test_voice(self):
        def enable():
            self.window.voice.enabled = True
            self.window.voice.state = 'listening'
        patcher = patch.object(self.window.voice, 'enable', side_effect=enable)
        patcher.start()
        self.addCleanup(patcher.stop)
        commands = patch.object(self.window.voice, 'command')
        commands.start()
        self.addCleanup(commands.stop)
        self.window.voice_button.set_active(True)

    def test_voice_failure_survives_model_health_refresh(self):
        self.window.voice_event({'event': 'error', 'message': 'No output device'})
        self.window.health_result(True)
        self.assertEqual(self.window.status.get_text(), 'Voice off · No output device')
        self.enable_test_voice()
        self.assertIsNone(self.window.voice_error)

    def test_voice_preloads_at_start_without_microphone_once(self):
        def enable():
            self.window.voice.enabled = True
            self.window.voice.state = 'listening'
        with patch.object(self.window.voice, 'enable', side_effect=enable) as start:
            self.assertFalse(self.window.voice.enabled)
            self.window.start_default_voice()
            self.drain()
            self.assertFalse(self.window.voice.microphone_enabled)
            self.assertTrue(self.window.voice_button.get_active())
            self.assertTrue(self.window.voice.enabled)
            self.window.start_default_voice()
            start.assert_called_once()

    def test_typed_reply_speaks_without_enabling_microphone(self):
        self.enable_test_voice()
        with patch.object(self.window.voice, 'speak', return_value=True) as speak, patch.object(self.window.voice, 'listen') as listen:
            self.window.voice_reply('Hello')
            self.window.voice_event({'event': 'done', 'turn': self.window.voice.turn})
            speak.assert_called_once_with('Hello')
            listen.assert_not_called()
        self.assertFalse(self.window.microphone_button.get_active())

    def test_new_chat_cancels_pending_startup_voice(self):
        with patch.object(self.window.voice, 'enable') as start:
            self.window.reset_chat()
            self.window.startup_audio.stop()
            self.drain()
            start.assert_not_called()

    def test_closed_window_cannot_start_voice_from_music_callback(self):
        with patch.object(self.window.voice, 'enable') as start:
            self.window.close_window()
            self.drain()
            start.assert_not_called()

    def test_voice_waits_for_music_and_transcript_keeps_canvas(self):
        self.assertFalse(self.window.voice.enabled)
        self.assertFalse(self.window.voice_button.get_active())
        self.enable_test_voice()
        with patch.object(self.window.voice, 'speak', return_value=True) as speak:
            self.window.voice_event({'event': 'transcript', 'text': 'Visually show me an idea'})
            self.assertGreater(len(self.window.canvas.links), 0)
            speak.assert_called_once()
            # Refreshing chat titles must not switch off voice.
            self.assertTrue(self.window.voice.enabled)

    def test_voice_never_executes_recognized_slash_commands(self):
        self.enable_test_voice()
        with patch.object(self.window, 'start_command') as run:
            self.window.voice_event({'event': 'transcript', 'text': '/run touch /tmp/never'})
            run.assert_not_called()
        self.assertIn('/run touch', self.window.buffer_text(self.window.input.get_buffer()))
        self.assertIn('review', self.window.status.get_text())

    def test_voice_does_not_overwrite_draft_and_switching_chat_disables_it(self):
        self.enable_test_voice()
        self.window.input.get_buffer().set_text('My draft')
        self.window.voice_event({'event': 'transcript', 'text': 'New words'})
        self.assertEqual(self.window.buffer_text(self.window.input.get_buffer()), 'My draft')
        self.assertIn('New words', self.window.buffer_text(self.window.buffer))
        self.window.clear()
        self.assertTrue(self.window.voice.enabled)
        self.assertFalse(self.window.voice.microphone_enabled)

    def test_voice_levels_respect_reduced_motion_and_off(self):
        self.enable_test_voice()
        self.window.voice_event({'event': 'state', 'state': 'speaking', 'message': 'Speaking'})
        self.window.voice_event({'event': 'level', 'state': 'speaking', 'level': .7})
        self.assertEqual(self.window.presence.state, 'speaking')
        self.assertEqual(self.window.presence.audio_level, .7)
        self.window.presence.set_animated(False)
        self.window.voice_button.set_active(False)
        self.assertFalse(self.window.voice.enabled)
        self.assertEqual(self.window.presence.state, 'ready')

    def test_visual_request_draws_without_model_and_clear_keeps_chat(self):
        self.window.model_ready = False
        self.window.input.get_buffer().set_text('Visually show me an idea')
        self.window.send()
        self.assertGreaterEqual(len(self.window.canvas.links), 3)
        self.assertIsNone(self.window.request)
        self.window.input.get_buffer().set_text('Clear the canvas')
        self.window.send()
        self.assertEqual(self.window.canvas.cards, [])
        self.assertEqual(self.window.canvas.links, [])
        self.assertEqual(len(self.window.history), 4)

    def test_model_can_replace_arrange_and_clear_with_follow_control(self):
        board = self.window.canvas
        from canvas_model import make_card
        note = make_card('Keep my note', 'A user note')
        board.add(note)
        board.record('First', 'Old -> Diagram')
        board.record('Next', 'Canvas: replace\nSeed -> Plant -> Flower')
        self.assertEqual({c['title'] for c in board.cards},
                         {'Keep my note', 'Seed', 'Plant', 'Flower'})
        board.record('Arrange', 'Canvas: arrange')
        self.assertEqual(len(board.cards), 4)
        board.follow.set_active(False)
        board.record('Keep', 'Canvas: clear')
        self.assertEqual(len(board.cards), 4)
        board.follow.set_active(True)
        board.record('Clear', 'Canvas: clear')
        self.assertEqual(board.cards, [])
        self.assertEqual(board.links, [])

    def test_generated_nodes_make_room_at_capacity(self):
        board = self.window.canvas
        from canvas_model import make_card, MAX_CARDS
        for i in range(MAX_CARDS):
            card = make_card(str(i), '')
            card['generated'] = True
            board.add(card)
        board.record('New', 'Fresh -> View')
        self.assertEqual(len(board.cards), MAX_CARDS)
        self.assertIn('Fresh', [c['title'] for c in board.cards])

    def drain(self):
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)

    def wait_for_command(self):
        deadline = time.monotonic() + 8
        while self.window.request and time.monotonic() < deadline:
            self.drain()
            time.sleep(0.01)
        self.assertIsNone(self.window.request)

    @staticmethod
    def text(buffer):
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def test_manual_output_is_separate_and_chat_draft_survives(self):
        chat_before = self.text(self.window.buffer)
        self.window.input.get_buffer().set_text('unfinished question')
        self.window.command_input.get_buffer().set_text('printf pane-output')
        self.window.run_proposal()
        self.wait_for_command()
        output = self.text(self.window.terminal_buffer)
        self.assertIn('pane-output', output)
        self.assertIn('Exit 0', output)
        self.assertEqual(self.text(self.window.buffer), chat_before)
        self.assertEqual(self.text(self.window.input.get_buffer()), 'unfinished question')
        self.assertEqual(self.window.last_command['output'], 'pane-output')

    def test_chat_command_routes_output_right_and_keeps_terminal_draft(self):
        self.window.command_input.get_buffer().set_text('printf later')
        self.window.input.get_buffer().set_text('/run printf chat-command-output')
        self.window.send()
        self.wait_for_command()
        chat = self.text(self.window.buffer)
        self.assertIn('Running in the terminal on the right', chat)
        self.assertNotIn('Exit 0', chat)
        self.assertIn('chat-command-output\nExit 0', self.text(self.window.terminal_buffer))
        self.assertEqual(self.text(self.window.command_input.get_buffer()), 'printf later')

    def propose(self, command):
        request = ChatRequest()
        self.window.busy(request, 'Test reply')
        self.window.finish(request, [{'role': 'system', 'content': ''}, {'role': 'user', 'content': 'Propose a command'}],
                           '```sh\n' + command + '\n```', None)

    def test_proposal_waits_in_right_input_until_run(self):
        self.propose('touch proposal-proof')
        proof = Path(self.temp.name) / 'proposal-proof'
        self.assertFalse(proof.exists())
        self.assertEqual(self.text(self.window.command_input.get_buffer()), 'touch proposal-proof')
        self.assertIn('Not executed', self.window.terminal_status.get_text())
        self.assertTrue(self.window.run_button.get_sensitive())
        self.window.run_proposal()
        self.wait_for_command()
        self.assertTrue(proof.exists())

    def test_proposal_preserves_an_existing_terminal_draft(self):
        self.window.command_input.get_buffer().set_text('printf my-draft')
        self.propose('touch should-not-exist')
        self.assertEqual(self.text(self.window.command_input.get_buffer()), 'printf my-draft')
        self.assertFalse((Path(self.temp.name) / 'should-not-exist').exists())

    def test_terminal_stop_reports_cancellation_on_right(self):
        self.window.command_input.get_buffer().set_text('printf started; sleep 30')
        self.window.run_proposal()
        self.assertTrue(self.window.terminal_stop_button.get_sensitive())
        self.assertFalse(self.window.stop_button.get_sensitive())
        deadline = time.monotonic() + 8
        while not self.text(self.window.terminal_buffer).endswith('started') and time.monotonic() < deadline:
            self.drain()
            time.sleep(0.01)
        self.assertTrue(self.text(self.window.terminal_buffer).endswith('started'))
        self.window.stop()
        self.wait_for_command()
        self.assertIn('stopped', self.text(self.window.terminal_buffer).lower())
        self.assertNotIn('stopped', self.text(self.window.buffer).lower())
        self.assertTrue(self.window.run_button.get_sensitive())

    def test_failure_and_directory_changes_stay_in_terminal(self):
        self.window.command_input.get_buffer().set_text('/cd /tmp')
        self.window.run_proposal()
        self.assertEqual(self.window.cwd, str(Path('/tmp').resolve()))
        self.assertEqual(self.window.directory.get_text(), self.window.cwd)
        self.window.command_input.get_buffer().set_text('false')
        self.window.run_proposal()
        self.wait_for_command()
        self.assertIn('Exit 1', self.text(self.window.terminal_buffer))
        self.assertNotIn('Exit 1', self.text(self.window.buffer))

    def test_new_chat_archives_both_panes_and_clear_output_only_clears_terminal(self):
        self.window.append('Keep conversation\n')
        self.window.append_terminal('Keep terminal\n')
        self.window.clear_terminal()
        self.assertIn('Keep conversation', self.text(self.window.buffer))
        self.assertEqual(self.text(self.window.terminal_buffer), '')
        self.window.append_terminal('Terminal remains\n')
        self.window.command_input.get_buffer().set_text('draft remains')
        old_id = self.window.chat_id
        self.window.clear()
        self.assertNotIn('Terminal remains', self.text(self.window.terminal_buffer))
        self.assertEqual(self.text(self.window.command_input.get_buffer()), '')
        self.assertNotIn('Keep conversation', self.text(self.window.buffer))
        self.select(old_id)
        self.assertIn('Terminal remains', self.text(self.window.terminal_buffer))
        self.assertEqual(self.text(self.window.command_input.get_buffer()), 'draft remains')
        self.assertIn('Keep conversation', self.text(self.window.buffer))

    def select(self, chat_id):
        row = next(row for row in self.window.chat_list.get_children() if row.chat_id == chat_id)
        self.window.chat_list.select_row(row)
        # GTK still uses the clicked row after row-selected returns.
        self.assertIs(row.get_parent(), self.window.chat_list)

    def reopen(self):
        self.window.close_window()
        self.window.destroy()
        self.window = Terminal(self.application, history_path=self.history_path)

    def seed_context(self):
        self.window.exchange('First saved question', 'Saved answer')
        self.window.last_command = {'command': 'printf saved', 'output': 'saved', 'exit_code': 0}
        self.window.last_page = {'url': 'https://example.com/', 'title': 'Example',
                                 'text': 'Saved website text', 'observed_utc': '2026-09-16T00:00:00Z'}
        self.window.input.get_buffer().set_text('saved draft')
        self.window.command_input.get_buffer().set_text('touch must-not-auto-run')
        self.window.append_terminal('saved command output\n')

    def test_reopen_restores_context_drafts_and_does_not_execute(self):
        self.seed_context()
        chat_id = self.window.chat_id
        self.reopen()
        self.assertEqual(self.window.chat_id, chat_id)
        self.assertIn('Saved answer', self.text(self.window.buffer))
        self.assertEqual(self.window.history[-1]['content'], 'Saved answer')
        self.assertEqual(self.window.last_command['output'], 'saved')
        self.assertEqual(self.window.last_page['text'], 'Saved website text')
        self.assertEqual(self.text(self.window.input.get_buffer()), 'saved draft')
        self.assertEqual(self.text(self.window.command_input.get_buffer()), 'touch must-not-auto-run')
        self.assertFalse((Path(self.temp.name) / 'must-not-auto-run').exists())
        self.assertIsNone(self.window.request)

    def test_switch_isolates_contexts_and_restores_previous_chat(self):
        self.seed_context()
        first = self.window.chat_id
        self.window.clear()
        second = self.window.chat_id
        self.assertEqual(self.window.history, [])
        self.assertIsNone(self.window.last_page)
        self.assertIsNone(self.window.last_command)
        self.window.exchange('Second question', 'Second answer')
        self.select(first)
        self.assertEqual(self.window.history[-1]['content'], 'Saved answer')
        self.assertEqual(self.window.last_page['text'], 'Saved website text')
        self.select(second)
        self.assertEqual(self.window.history[-1]['content'], 'Second answer')
        self.assertIsNone(self.window.last_page)
        self.assertNotIn('Saved answer', self.text(self.window.buffer))

    def test_clear_all_erases_every_context_and_stays_empty_after_reopen(self):
        self.seed_context()
        old_id = self.window.chat_id
        self.window.clear()
        self.seed_context()
        self.assertIsNotNone(self.window.save_source)
        self.assertTrue(self.window.clear_all_history())
        self.assertIsNone(self.window.save_source)
        self.reopen()
        self.assertNotEqual(self.window.chat_id, old_id)
        self.assertEqual(len(self.window.store.list_chats()), 1)
        self.assertEqual(self.window.history, [])
        self.assertIsNone(self.window.last_command)
        self.assertIsNone(self.window.last_page)
        self.assertEqual(self.text(self.window.input.get_buffer()), '')
        self.assertEqual(self.text(self.window.command_input.get_buffer()), '')
        self.assertEqual(self.text(self.window.terminal_buffer), '')
        self.assertNotIn('Saved answer', self.text(self.window.buffer))
        self.assertNotIn(b'Saved website text', self.history_path.read_bytes())

    def test_active_request_blocks_switch_and_clear_and_late_result(self):
        self.seed_context()
        first = self.window.chat_id
        self.window.clear()
        second = self.window.chat_id
        request = ChatRequest()
        self.window.busy(request, 'Testing')
        self.select(first)
        self.window.clear()
        self.assertFalse(self.window.clear_all_history())
        self.assertEqual(self.window.chat_id, second)
        self.assertFalse(self.window.settings_button.get_sensitive())
        self.window.stop()
        self.window.finish(request, [{'role': 'user', 'content': 'Question'}], None, None)
        self.assertTrue(self.window.clear_all_history())
        self.window.finish(request, [], 'stale result', None)
        self.assertNotIn('stale result', self.text(self.window.buffer))

    def test_save_failure_keeps_current_chat_and_reports_error(self):
        import sqlite3
        self.seed_context()
        chat_id = self.window.chat_id
        with patch.object(self.window.store, 'save', side_effect=sqlite3.OperationalError('disk full')):
            self.window.clear()
            self.assertEqual(self.window.chat_id, chat_id)
            self.assertIn('could not', self.window.save_status.get_text())
        with patch.object(self.window.store, 'clear', side_effect=sqlite3.OperationalError('read only')):
            self.assertFalse(self.window.clear_all_history())
            self.assertEqual(self.window.chat_id, chat_id)

    def test_canvas_excerpts_follow_toggle_and_no_command_execution(self):
        self.window.exchange('Plan a garden', 'Raised beds save space.\nTry drip irrigation.')
        self.assertEqual(len(self.window.canvas.cards), 3)
        self.assertIsNone(self.window.request)
        self.window.canvas.follow.set_active(False)
        self.window.exchange('Another question', 'Another idea')
        self.assertEqual(len(self.window.canvas.cards), 3)
        self.window.canvas.add(make_card('A shell snippet', 'touch never-execute'))
        self.assertFalse((Path(self.temp.name) / 'never-execute').exists())

    def test_canvas_positions_edits_and_context_are_saved_per_chat(self):
        board = self.window.canvas
        card = make_card('My idea', 'Original body')
        board.add(card)
        board.move_card(card, 133, 212)
        board.drag_end()
        board.save_edit(card['id'], make_card('Updated idea', 'Edited body', 'Actions'))
        board.follow.set_active(False)
        first = self.window.chat_id
        self.window.clear()
        self.assertEqual(self.window.canvas.cards, [])
        self.select(first)
        restored = self.window.canvas.cards[0]
        self.assertEqual((restored['x'], restored['y']), (133, 212))
        self.assertEqual(restored['body'], 'Edited body')
        self.reopen()
        self.assertFalse(self.window.canvas.follow.get_active())
        self.assertEqual(self.window.canvas.cards[0]['title'], 'Updated idea')
        self.assertTrue(self.window.clear_all_history())
        self.reopen()
        self.assertEqual(self.window.canvas.cards, [])

    def test_canvas_arrange_remove_and_stale_edit_after_switch(self):
        board = self.window.canvas
        board.add(make_card('Second', 'Action', 'Actions'))
        board.add(make_card('First', 'Question', 'Questions'))
        board.organize()
        self.assertLess(board.cards[1]['y'] * 10000 + board.cards[1]['x'],
                        board.cards[0]['y'] * 10000 + board.cards[0]['x'])
        board.remove_by_id(board.cards[0]['id'])
        self.assertEqual(len(board.cards), 1)
        generation = board.generation
        self.window.clear()
        board.save_edit(None, make_card('Stale', 'Stale data'), generation)
        self.assertEqual(board.cards, [])

    def test_visual_links_persist_follow_drag_and_disappear_with_node(self):
        board = self.window.canvas
        board.record('Explain booting', 'Firmware -> Disk found? -> Linux\nDisk found? -> Recovery')
        self.assertEqual(len(board.cards), 4)
        self.assertEqual(len(board.links), 3)
        node = board.cards[1]
        board.move_card(node, 100, 300)
        board.stop_motion()
        self.reopen()
        board = self.window.canvas
        self.assertEqual(len(board.links), 3)
        self.assertEqual(board.cards[1]['x'], 100)
        board.remove_by_id(board.cards[1]['id'])
        self.assertEqual(board.links, [])
        board.snapshot()

    def test_image_completion_is_cached_and_stale_result_does_not_cross_chats(self):
        import io
        import base64
        import cairo
        stream = io.BytesIO()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 20, 10)
        surface.write_to_png(stream)
        result = {'image_data': base64.b64encode(stream.getvalue()).decode(), 'url': 'https://example.org/a.png'}
        board = self.window.canvas
        with patch.object(board, 'start_images'):
            card = board.add_image(result['url'], 'Image', 'Source')
        request = object()
        board.image_requests[card['id']] = request
        board.image_queue.clear()
        board.image_finished(card['id'], request, board.generation, result, None)
        self.assertEqual(card['image_data'], result['image_data'])
        with patch('canvas.ImageRequest') as download:
            self.reopen()
            download.assert_not_called()
        self.assertEqual(self.window.canvas.cards[0]['image_data'], result['image_data'])
        board = self.window.canvas
        generation = board.generation
        self.window.clear()
        board.image_finished(card['id'], request, generation, result, None)
        self.assertEqual(board.cards, [])

    def test_model_image_urls_require_fetched_candidates_and_reduced_motion_stops_layout(self):
        board = self.window.canvas
        with patch.object(board, 'add_image') as image:
            board.record('clouds', '![Cloud](https://example.org/cloud.png)')
            image.assert_not_called()
            board.record('clouds', '![Cloud](https://example.org/cloud.png)',
                         allowed_images=['https://example.org/cloud.png'])
            image.assert_called_once()
        board.set_animated(False)
        board.organize()
        self.assertIsNone(board.motion)
        for card in board.cards:
            self.assertEqual(board.widgets[card['id']].get_opacity(), 1)

    def test_emerald_tracks_real_request_callbacks_and_stop(self):
        presence = self.window.presence
        self.assertEqual(presence.state, 'ready')
        request = ChatRequest()
        self.window.busy(request, 'Thinking')
        self.assertEqual(presence.state, 'thinking')
        self.window.chunk(request, 'Hello')
        self.assertEqual(presence.state, 'replying')
        self.assertIsNotNone(presence.last_chunk)
        self.assertIn('Replying', presence.area.get_accessible().get_name())
        self.window.stop()
        self.assertEqual(presence.state, 'stopping')
        self.window.finish(request, [{'role': 'user', 'content': 'Hello'}], None, None)
        self.assertEqual(presence.state, 'ready')
        self.assertIsNone(presence.timer)
        self.window.chunk(request, 'late data')
        self.assertEqual(presence.state, 'ready')

    def test_emerald_motion_setting_persists_and_removes_animation_timer(self):
        presence = self.window.presence
        self.drain()
        presence.set_activity('thinking')
        button = Gtk.CheckButton()
        button.set_active(False)
        self.window.change_animation(button)
        self.assertIsNone(presence.timer)
        self.assertEqual(presence.label.get_text(), 'Thinking…')
        self.reopen()
        self.assertFalse(self.window.presence.animate)

    def test_emerald_draws_distinct_glow_levels_and_cleans_up(self):
        import cairo
        from presence import EmeraldPresence
        images = []
        for energy in (0.18, 0.75):
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 112, 112)
            EmeraldPresence.paint(cairo.Context(surface), 112, 112, energy)
            surface.flush()
            images.append(bytes(surface.get_data()))
        self.assertNotEqual(images[0], images[1])
        self.window.presence.set_activity('thinking')
        self.window.presence.shutdown()
        self.assertIsNone(self.window.presence.timer)
        self.assertTrue(self.window.presence.disposed)

    def test_emerald_honors_system_reduced_motion_and_pausing(self):
        presence = self.window.presence
        original = presence.settings.get_property('gtk-enable-animations')
        self.addCleanup(presence.settings.set_property, 'gtk-enable-animations', original)
        presence.settings.set_property('gtk-enable-animations', False)
        presence.set_activity('thinking')
        self.assertFalse(presence.motion_enabled())
        self.assertIsNone(presence.timer)
        presence.settings.set_property('gtk-enable-animations', True)
        presence.set_paused(True)
        self.assertIsNone(presence.timer)


if __name__ == '__main__':
    unittest.main(verbosity=2)
