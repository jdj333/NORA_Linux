"""User-invoked shell execution with streamed output and bounded process groups."""
import codecs
from dataclasses import dataclass
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import threading
import time

MAX_COMMAND_BYTES = 4096
MAX_OUTPUT_BYTES = 32768
TIMEOUT_SECONDS = 60


def validate(command):
    if not command.strip():
        raise ValueError('Enter a command after /run.')
    if len(command.encode('utf-8')) > MAX_COMMAND_BYTES:
        raise ValueError('Command exceeds 4,096 UTF-8 bytes.')
    if any((ord(c) < 32 and c not in '\n\t') or c in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069' for c in command):
        raise ValueError('Command contains hidden control or text-direction characters.')
    return command.strip()


def suggested_command(answer):
    """A fenced shell block is a proposal only. Never execute model text here."""
    blocks = re.findall(r'^```(?:sh|bash|shell)\s*\n(.*?)^```\s*$', answer, re.M | re.S)
    if len(blocks) != 1:
        return None
    try:
        return validate(blocks[0])
    except ValueError:
        return None


def change_directory(value, current):
    # Treat paths literally; do not evaluate shell substitutions or expand $VAR.
    target = Path(value.strip() or '~').expanduser()
    if not target.is_absolute():
        target = Path(current) / target
    target = target.resolve(strict=True)
    if not target.is_dir():
        raise ValueError('That path is not a directory.')
    if not os.access(target, os.X_OK):
        raise PermissionError('You do not have permission to enter that directory.')
    return str(target)


def display_output(text):
    # GTK renders plain text; remove control characters, including terminal escapes.
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    return ''.join(c for c in text if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127))


@dataclass
class Result:
    command: str
    cwd: str
    output: str
    exit_code: int
    reason: str
    elapsed: float

    def summary(self):
        return f'Exit {self.exit_code} · {self.reason} · {self.elapsed:.1f}s'

    def model_evidence(self):
        # Preserve both the start and end of output, where errors often appear.
        data = self.output.encode('utf-8')
        excerpt = self.output if len(data) <= 800 else (
            data[:350].decode('utf-8', 'ignore') + '\n[output shortened]\n' + data[-350:].decode('utf-8', 'ignore'))
        return {'command': self.command[:400], 'cwd': self.cwd, 'exit_code': self.exit_code,
                'reason': self.reason, 'output': excerpt}


class CommandRequest:
    def __init__(self, command, cwd, timeout=TIMEOUT_SECONDS, output_limit=MAX_OUTPUT_BYTES):
        self.command = validate(command)
        self.cwd = str(cwd)
        self.timeout = timeout
        self.output_limit = output_limit
        self.cancelled = threading.Event()
        self.process = None
        self.lock = threading.Lock()
        self.signal_lock = threading.Lock()
        self.term_sent = False
        self.hard_killed = False

    def cancel(self, kill=False):
        self.cancelled.set()
        with self.lock:
            if self.process is not None:
                self.signal_group(self.process, signal.SIGKILL if kill else signal.SIGTERM)

    def signal_group(self, process, number):
        with self.signal_lock:
            # UI cancellation and the worker may race. Send TERM only once,
            # and never signal again after KILL (the group may already be gone).
            if self.hard_killed or (number == signal.SIGTERM and self.term_sent):
                return
            try:
                os.killpg(process.pid, number)
            except ProcessLookupError:
                pass
            except PermissionError:
                # macOS can return EPERM for an already-dead process group.
                # A live group we cannot signal is a real error, not success.
                if process.poll() is None:
                    raise
            if number == signal.SIGKILL:
                self.hard_killed = True
            elif number == signal.SIGTERM:
                self.term_sent = True

    def run(self, on_chunk):
        started = time.monotonic()
        if self.cancelled.is_set():
            return Result(self.command, self.cwd, '', -1, 'cancelled before launch', 0)
        environment = os.environ.copy()
        environment.update(TERM='dumb', NO_COLOR='1', PAGER='cat', LC_ALL='C.UTF-8')
        # Bash pipelines/redirections are intentional for explicitly submitted
        # commands. No model-generated text reaches here without a Run click.
        with self.lock:
            if self.cancelled.is_set():
                return Result(self.command, self.cwd, '', -1, 'cancelled before launch', 0)
            process = self.process = subprocess.Popen(
                ['/bin/bash', '--noprofile', '--norc', '-o', 'pipefail', '-c', self.command],
                cwd=self.cwd, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                start_new_session=True, bufsize=0)
        output = []
        received = 0
        reason = 'completed'
        stopping = None
        decoder = codecs.getincrementaldecoder('utf-8')('replace')
        try:
            os.set_blocking(process.stdout.fileno(), False)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map() or process.poll() is None:
                    now = time.monotonic()
                    if stopping is None:
                        if self.cancelled.is_set(): reason = 'stopped by you'
                        elif now - started >= self.timeout: reason = 'time limit reached'
                        if reason != 'completed':
                            self.signal_group(process, signal.SIGTERM)
                            stopping = now
                    if stopping is not None and now - stopping >= 0.25:
                        self.signal_group(process, signal.SIGKILL)
                        break
                    for key, _ in selector.select(0.05):
                        data = os.read(key.fd, 4096)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        allowed = max(0, self.output_limit - received)
                        part = data[:allowed]
                        received += len(part)
                        decoded = display_output(decoder.decode(part))
                        if decoded:
                            output.append(decoded)
                            on_chunk(decoded)
                        if len(data) > allowed and stopping is None:
                            reason = 'output limit reached'
                            self.signal_group(process, signal.SIGTERM)
                            stopping = time.monotonic()
            if stopping is not None:
                self.signal_group(process, signal.SIGKILL)
            if self.cancelled.is_set() and reason == 'completed':
                reason = 'stopped by you'
            tail = display_output(decoder.decode(b'', final=True))
            if tail:
                output.append(tail)
                on_chunk(tail)
            code = process.wait(timeout=2)
            return Result(self.command, self.cwd, ''.join(output), code, reason, time.monotonic() - started)
        finally:
            if process.poll() is None:
                self.signal_group(process, signal.SIGKILL)
                process.wait()
            process.stdout.close()
            with self.lock:
                self.process = None
