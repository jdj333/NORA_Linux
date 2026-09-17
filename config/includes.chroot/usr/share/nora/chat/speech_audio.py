"""Buffered speech playback using the same GStreamer path as startup music."""
import tempfile
import threading
import wave
from pathlib import Path


class SpeechAudio:
    def __init__(self, samples, rate, sink=None):
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        import numpy as np
        self.gst = Gst
        Gst.init(None)
        self.lock = threading.RLock()
        self.stopped = False
        self.player = None
        self.temp = tempfile.TemporaryDirectory(prefix='nora-speech-')
        try:
            path = Path(self.temp.name) / 'speech.wav'
            with wave.open(str(path), 'wb') as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(int(rate))
                output.writeframes((np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes())
            self.player = Gst.ElementFactory.make('playbin', 'nora-speech')
            if self.player is None:
                raise RuntimeError('GStreamer speech player unavailable')
            self.player.set_property('uri', path.as_uri())
            if sink is not None:  # Test sink; normal playback uses system output.
                self.player.set_property('audio-sink', sink)
            self.bus = self.player.get_bus()
        except Exception:
            self.close()
            raise

    def start(self):
        with self.lock:
            if not self.stopped and self.player.set_state(self.gst.State.PLAYING) == self.gst.StateChangeReturn.FAILURE:
                raise RuntimeError('Could not start speech playback')

    def wait(self, seconds=.05):
        with self.lock:
            if self.stopped:
                return True
        message = self.bus.timed_pop_filtered(int(seconds * self.gst.SECOND),
                                             self.gst.MessageType.EOS | self.gst.MessageType.ERROR)
        if message is None:
            return self.stopped
        if message.type == self.gst.MessageType.ERROR:
            raise RuntimeError(message.parse_error()[0].message)
        return True

    def position(self):
        with self.lock:
            if self.stopped:
                return 0
            ok, position = self.player.query_position(self.gst.Format.TIME)
            return position / self.gst.SECOND if ok else 0

    def abort(self):
        with self.lock:
            self.stopped = True
            if self.player is not None:
                self.player.set_state(self.gst.State.NULL)

    def close(self):
        self.abort()
        self.temp.cleanup()
