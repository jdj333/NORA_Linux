"""Voice lifecycle, stale-result rejection and spoken-text policy tests."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat'))
from voice import VoiceSession
from voice_text import spoken_text, speech_chunks


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.spawn = Mock()
        self.voice = VoiceSession(lambda fn, *args: fn(*args), self.events.append, self.spawn)

    def live(self):
        process = Mock()
        process.stdin = io.StringIO()
        self.voice.process = process
        self.voice.enabled = True
        return process

    def test_default_off_never_starts_worker(self):
        self.assertFalse(self.voice.enabled)
        self.voice.pause()
        self.voice.listen()
        self.assertFalse(self.voice.speak('Hello'))
        self.spawn.assert_not_called()

    def test_disable_kills_worker_and_discards_late_transcripts(self):
        process = self.live()
        self.voice.listen()
        old_turn = self.voice.turn
        self.voice.disable()
        process.kill.assert_called_once()
        self.voice.deliver(process, {'event': 'transcript', 'turn': old_turn, 'text': 'run something'})
        self.assertEqual(self.events, [])
        self.assertIsNone(self.voice.process)
        self.assertFalse(self.voice.enabled)

    def test_speech_invalidates_microphone_events(self):
        process = self.live()
        self.voice.listen()
        old_turn = self.voice.turn
        self.voice.speak('Hello Nora')
        self.voice.deliver(process, {'event': 'transcript', 'turn': old_turn, 'text': 'echo'})
        self.assertEqual(self.events, [])
        self.voice.deliver(process, {'event': 'state', 'turn': self.voice.turn, 'state': 'speaking'})
        self.assertEqual(self.voice.state, 'speaking')
        self.assertIn('"action": "speak"', process.stdin.getvalue())

    def test_old_worker_cannot_affect_new_session(self):
        old = self.live()
        new = self.live()
        self.voice.deliver(old, {'event': 'error', 'turn': 0, 'message': 'late'})
        self.voice.exited(old)
        self.assertIs(self.voice.process, new)
        self.assertEqual(self.events, [])

    def test_pause_discards_previous_turn(self):
        process = self.live()
        self.voice.listen()
        turn = self.voice.turn
        self.voice.pause()
        self.voice.deliver(process, {'event': 'transcript', 'turn': turn, 'text': 'stale'})
        self.assertEqual(self.events, [])
        self.assertEqual(self.voice.state, 'waiting')

    def test_broken_pipe_disables_voice(self):
        process = self.live()
        process.stdin.close()
        self.voice.listen()
        self.assertFalse(self.voice.enabled)
        process.kill.assert_called_once()
        self.assertEqual(self.events[-1]['event'], 'error')

    def test_speech_skips_code_urls_and_canvas_instructions(self):
        text = spoken_text('Canvas: replace\nHello **Nora**.\n```sh\nrm -rf example\n```\n'
                           '[Read this](https://example.org) A -> B')
        self.assertNotIn('rm -rf', text)
        self.assertNotIn('Canvas:', text)
        self.assertNotIn('https:', text)
        self.assertIn('Hello Nora.', text)
        self.assertIn('then', text)
        self.assertNotIn('secret', spoken_text('```sh\nsecret'))

    def test_synthesis_chunks_and_total_reply_are_bounded(self):
        chunks = speech_chunks('Hello. ' + 'word ' * 1000)
        self.assertTrue(chunks)
        self.assertLessEqual(max(map(len, chunks)), 240)
        self.assertLessEqual(sum(map(len, chunks)), 1600)
        self.assertEqual(speech_chunks('Canvas: clear'), [])


if __name__ == '__main__':
    unittest.main()
