#!/usr/bin/env python3
"""Offline inference smoke test. Run with the bundled runtime on Linux.

No microphone, speaker, or network access is needed. The generated speech is an
in-memory test fixture; this does not measure real microphone/room performance.
"""
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT = Path(os.environ.get('NORA_VOICE_ROOT', '/opt/nora/voice'))
sys.path.insert(0, str(ROOT / 'python'))


def deny_network(*args, **kwargs):
    raise AssertionError('Voice inference must not use the network')


socket.socket.connect = deny_network
socket.create_connection = deny_network
import numpy as np
import onnxruntime as ort
from kokoro_onnx import Kokoro
from moonshine_voice import Transcriber, ModelArch
from moonshine_voice.transcriber import TranscriptEventListener


def main():
    print('Loading offline speech engines…', file=sys.stderr, flush=True)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    engine = Kokoro.from_session(ort.InferenceSession(str(ROOT / 'tts/model.onnx'),
                                sess_options=options, providers=['CPUExecutionProvider']),
                                str(ROOT / 'tts/voices.bin'))
    recognizer = Transcriber(str(ROOT / 'stt'), ModelArch.SMALL_STREAMING)
    results = []
    for voice in ('af_heart', 'af_bella'):
        print('Checking ' + voice, file=sys.stderr, flush=True)
        start = time.monotonic()
        audio, rate = engine.create('Hello Nora. Please show me an idea.', voice=voice, lang='en-us')
        assert rate == 24000 and len(audio) > rate and np.max(np.abs(audio)) > .01
        synth_seconds = time.monotonic() - start
        words = []

        class Listener(TranscriptEventListener):
            def on_line_completed(self, event):
                words.append(event.line.text)

        stream = recognizer.create_stream()
        stream.add_listener(Listener())
        stream.start()
        for offset in range(0, len(audio), rate // 10):
            stream.add_audio(audio[offset:offset + rate // 10].tolist(), rate)
        stream.add_audio([0.0] * (rate * 2), rate)
        stream.stop()
        stream.close()
        transcript = ' '.join(words)
        assert 'idea' in transcript.lower() and 'hello' in transcript.lower(), transcript
        results.append({'voice': voice, 'audio_seconds': round(len(audio) / rate, 2),
                        'synthesis_seconds': round(synth_seconds, 2), 'transcript': transcript})
    silent = recognizer.transcribe_without_streaming([0.0] * 48000, 16000)
    assert not any(line.text.strip() for line in silent.lines), silent
    recognizer.close()
    print(json.dumps({'result': 'PASS', 'network': 'Python network calls disabled',
                      'silence': 'no transcript', 'round_trips': results}, indent=2))


if __name__ == '__main__':
    main()
