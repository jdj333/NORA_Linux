"""GTK-independent controller for the disposable local speech worker."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

from voice_text import spoken_text

ROOT = Path(os.environ.get('NORA_VOICE_ROOT', '/opt/nora/voice'))
WORKER = Path(__file__).with_name('voice_worker.py')


class VoiceSession:
    def __init__(self, dispatch, callback, popen=subprocess.Popen):
        self.dispatch = dispatch
        self.callback = callback
        self.popen = popen
        self.process = None
        self.enabled = False
        self.turn = 0
        self.state = 'off'
        self.input_device = None
        self.output_device = None
        self.voice = 'af_heart'

    def enable(self):
        if self.enabled:
            return
        if not (ROOT / 'provenance.json').is_file():
            raise RuntimeError('Local voice assets are missing. Install a voice-enabled NORA image.')
        env = dict(os.environ, PYTHONUNBUFFERED='1', OMP_NUM_THREADS='2')
        self.process = self.popen([sys.executable, str(WORKER)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, encoding='utf-8', bufsize=1, env=env)
        self.enabled = True
        self.state = 'loading'
        threading.Thread(target=self.read, args=(self.process,), daemon=True).start()
        self.listen()

    def read(self, process):
        try:
            for line in process.stdout:
                if len(line) > 32000:
                    raise ValueError('Invalid voice worker response')
                event = json.loads(line)
                self.dispatch(self.deliver, process, event)
        except (OSError, ValueError):
            pass
        finally:
            process.wait()
            process.stdout.close()
            self.dispatch(self.exited, process)

    def deliver(self, process, event):
        if not self.enabled or self.process is not process:
            return False
        if event.get('turn') not in (0, self.turn):
            return False
        kind = event.get('event')
        if kind == 'state':
            self.state = event['state']
        elif kind == 'transcript':
            self.state = 'waiting'
        elif kind in ('done', 'idle'):
            self.state = 'waiting'
        self.callback(event)
        return False

    def exited(self, process):
        if self.enabled and self.process is process:
            self.disable()
            self.callback({'event': 'error', 'message': 'Local voice worker stopped. You can enable voice to retry.'})
        return False

    def command(self, action, **fields):
        if not self.enabled:
            return
        self.turn += 1
        try:
            self.process.stdin.write(json.dumps(dict(action=action, turn=self.turn, **fields)) + '\n')
            self.process.stdin.flush()
        except (OSError, ValueError):
            self.disable()
            self.callback({'event': 'error', 'message': 'Local voice connection stopped. Enable voice to retry.'})

    def listen(self):
        if self.enabled:
            self.state = 'loading'
            self.command('listen', input=self.input_device)

    def pause(self):
        if self.enabled:
            self.state = 'waiting'
            self.command('pause')

    def speak(self, text):
        text = spoken_text(text)
        if self.enabled and text:
            self.state = 'loading'
            self.command('speak', text=text, voice=self.voice, output=self.output_device)
            return True
        return False

    def disable(self):
        self.enabled = False
        self.state = 'off'
        self.turn += 1
        process, self.process = self.process, None
        if process:
            # Kill native inference too. This is the process that owns both devices.
            try:
                process.kill()
            except ProcessLookupError:
                pass
            if process.stdin:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            # The reader thread reaps it; never block GTK on model shutdown.


def devices():
    result = subprocess.run([sys.executable, str(WORKER), '--devices'], capture_output=True,
                            text=True, timeout=15, check=True)
    event = json.loads(result.stdout)
    if event.get('event') != 'devices':
        raise RuntimeError(event.get('message', 'Audio devices unavailable'))
    return event['devices']
