"""Run explicitly in Linux with the speech runtime and a generated audio fixture.

Required env: NORA_VOICE_ROOT, NORA_CHAT_DIR, NORA_TEST_AUDIO.
The fixture is generated speech, never a recording of the user.
"""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time


def main():
    with tempfile.TemporaryDirectory() as directory:
        trace = Path(directory) / 'devices.log'
        env = dict(os.environ, NORA_TEST_TRACE=str(trace))
        with (Path(directory) / 'worker.log').open('w+') as log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('voice_worker_harness.py'))],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                       text=True, env=env)
            events = queue.Queue()
            def read():
                for line in process.stdout:
                    events.put(json.loads(line))
            threading.Thread(target=read, daemon=True).start()
            def send(action, turn, **fields):
                process.stdin.write(json.dumps(dict(action=action, turn=turn, **fields)) + '\n')
                process.stdin.flush()
            def until(kind, turn):
                seen = []
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    try:
                        event = events.get(timeout=.2)
                    except queue.Empty:
                        if process.poll() is not None:
                            break
                        continue
                    assert event['event'] != 'error', event
                    if event['turn'] == turn:
                        seen.append(event)
                        if event['event'] == kind:
                            return seen
                log.seek(0)
                raise AssertionError('Voice worker timeout: ' + log.read()[-3000:])
            try:
                send('listen', 1)
                heard = until('transcript', 1)
                assert 'idea' in heard[-1]['text'].lower(), heard[-1]
                assert any(e['event'] == 'level' and e['level'] > 0 for e in heard)
                send('speak', 2, text='Hello. Here is an idea for our canvas.', voice='af_bella')
                spoken = until('done', 2)
                assert any(e['event'] == 'level' and e['level'] > 0 for e in spoken)
                send('listen', 3)
                while True:
                    state = until('state', 3)[-1]
                    if state['state'] == 'listening':
                        break
                send('pause', 4)
                time.sleep(.5)
                active = set()
                for line in trace.read_text().splitlines():
                    device, event = line.split()
                    if event == 'open':
                        assert not active, ('Microphone/output overlap', active, line)
                        active.add(device)
                    else:
                        active.remove(device)
                assert not active, ('Pause did not release devices', active)
                print('PASS: real worker transcribes, speaks, emits audio levels, takes turns, and releases devices on pause.')
            finally:
                process.kill()
                process.wait(timeout=5)
                process.stdin.close()
                process.stdout.close()


if __name__ == '__main__':
    main()
