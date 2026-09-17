"""Play the bundled startup song once, without blocking the GTK main loop."""
import logging
from pathlib import Path


class StartupAudio:
    def __init__(self, on_finished=None):
        self.player = None
        self.on_finished = on_finished
        self.bus = None
        self.handler = None
        self.finished = False
        self.gst = None

    def play(self):
        # Also guards a queued startup callback after the window has closed.
        if self.finished or self.player is not None:
            return False
        path = Path('/usr/share/nora/music/NoraLinuxStartupSong.mp3')
        try:
            if not path.is_file():
                raise FileNotFoundError(path)
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst
            self.gst = Gst
            Gst.init(None)
            self.player = Gst.ElementFactory.make('playbin', 'nora-startup')
            if self.player is None:
                raise RuntimeError('GStreamer playbin is unavailable')
            self.player.set_property('uri', path.as_uri())
            self.bus = self.player.get_bus()
            self.bus.add_signal_watch()
            self.handler = self.bus.connect('message', self.message)
            if self.player.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError('Could not start audio playback')
        except (ImportError, ValueError, OSError, RuntimeError) as error:
            logging.warning('NORA startup music unavailable: %s', error)
            self.stop()
        return False

    def message(self, _bus, message):
        if message.type == self.gst.MessageType.ERROR:
            error, _debug = message.parse_error()
            logging.warning('NORA startup music: %s', error.message)
            self.stop()
        elif message.type == self.gst.MessageType.EOS:
            self.stop()

    def stop(self):
        callback, self.on_finished = self.on_finished, None
        self.finished = True
        if self.bus is not None:
            self.bus.disconnect(self.handler)
            self.bus.remove_signal_watch()
            self.bus = None
            self.handler = None
        if self.player is not None:
            self.player.set_state(self.gst.State.NULL)
            self.player = None
        if callback is not None:
            callback()
