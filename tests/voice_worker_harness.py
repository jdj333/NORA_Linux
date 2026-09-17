"""Real speech worker with simulated sound devices for offline integration checks.

Not imported by unittest discovery. A parent harness supplies JSON commands and
NORA_TEST_AUDIO (a generated float32 NumPy fixture) to test real STT/TTS without
opening host devices. Model inference and the worker protocol are unchanged.
"""
import os
import runpy
import socket
import sys
import threading
import time
from pathlib import Path
import numpy as np
import sounddevice as sd


def no_network(*args, **kwargs):
    raise AssertionError('Unexpected network access during voice inference')


socket.socket.connect = no_network
socket.create_connection = no_network
fixture = np.load(os.environ['NORA_TEST_AUDIO'])
fixture = np.concatenate((fixture, np.zeros(48000, dtype=np.float32)))


class Stream:
    def __init__(self, *, callback, blocksize, finished_callback=None, **kwargs):
        self.callback = callback
        self.blocksize = blocksize
        self.finished = finished_callback
        self.stopped = threading.Event()

    def start(self):
        self.trace('open')
        threading.Thread(target=self.run, daemon=True).start()

    def trace(self, event):
        with open(os.environ['NORA_TEST_TRACE'], 'a') as output:
            output.write(('output' if self.finished else 'input') + ' ' + event + '\n')

    def run(self):
        cursor = 0
        try:
            while not self.stopped.is_set():
                frames = np.zeros((self.blocksize, 1), dtype=np.float32)
                if self.finished is None:
                    count = min(self.blocksize, max(0, len(fixture) - cursor))
                    frames[:count, 0] = fixture[cursor:cursor + count]
                    cursor += count
                self.callback(frames, self.blocksize, None, None)
                self.stopped.wait(self.blocksize / 24000)
        except (sd.CallbackStop, sd.CallbackAbort):
            pass
        finally:
            if self.finished:
                self.finished()

    def abort(self):
        self.stopped.set()

    def close(self):
        self.stopped.set()
        self.trace('close')


sd.InputStream = Stream
sd.OutputStream = Stream
sd.query_devices = lambda *args: {'default_samplerate': 24000}
sys.path.insert(0, str(Path(os.environ['NORA_CHAT_DIR'])))
runpy.run_path(str(Path(os.environ['NORA_CHAT_DIR']) / 'voice_worker.py'), run_name='__main__')
