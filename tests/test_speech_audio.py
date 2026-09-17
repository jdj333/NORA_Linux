"""Clocked playback and cancellation through real GStreamer, without speakers."""
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat'))
try:
    import numpy as np
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    from speech_audio import SpeechAudio
    Gst.init(None)
    AVAILABLE = True
except (ImportError, ValueError):
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires numpy and GStreamer')
class SpeechAudioTests(unittest.TestCase):
    def player(self, duration):
        sink = Gst.ElementFactory.make('fakesink')
        sink.set_property('sync', True)
        return SpeechAudio(np.zeros(int(24000 * duration), dtype=np.float32), 24000, sink)

    def test_playback_preserves_duration_and_cleans_generated_file(self):
        player = self.player(.6)
        directory = Path(player.temp.name)
        start = time.monotonic()
        try:
            player.start()
            while not player.wait():
                self.assertLess(time.monotonic() - start, 5)
            self.assertGreaterEqual(time.monotonic() - start, .55)
        finally:
            player.close()
        self.assertFalse(directory.exists())

    def test_cancel_stops_without_waiting_for_complete_sentence(self):
        player = self.player(10)
        try:
            player.start()
            player.abort()
            self.assertTrue(player.wait())
        finally:
            player.close()
            player.close()
