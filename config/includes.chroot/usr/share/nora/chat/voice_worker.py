#!/usr/bin/env python3
"""Offline speech worker. JSON pipes only; raw microphone audio stays in memory.

The GTK process can kill this worker to release audio immediately, even while
native inference is busy. Models are loaded lazily and retained between turns.
"""
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time

ROOT = Path(os.environ.get('NORA_VOICE_ROOT', '/opt/nora/voice'))
sys.path.insert(0, str(ROOT / 'python'))
from voice_text import speech_chunks


def main():
    # Native libraries sometimes print to stdout. Keep the protocol on its own fd.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), 'w', buffering=1)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    write_lock = threading.Lock()

    def emit(kind, turn=0, **fields):
        with write_lock:
            protocol.write(json.dumps(dict(event=kind, turn=turn, **fields)) + '\n')

    try:
        import numpy as np
        import sounddevice as sd
        if '--devices' in sys.argv:
            devices = [{'id': i, 'name': d['name'], 'input': d['max_input_channels'] > 0,
                        'output': d['max_output_channels'] > 0}
                       for i, d in enumerate(sd.query_devices())]
            emit('devices', devices=devices)
            return
        from moonshine_voice import Transcriber, ModelArch
        from moonshine_voice.transcriber import TranscriptEventListener
        from kokoro_onnx import Kokoro
        import onnxruntime as ort
    except Exception as error:
        emit('error', message='Voice runtime unavailable: ' + str(error))
        return

    commands = queue.Queue(maxsize=1)
    gate = threading.RLock()
    current = {'turn': 0, 'stream': None}
    closed = threading.Event()

    def close_audio():
        with gate:
            stream = current['stream']
            current['stream'] = None
            if stream is not None:
                stream.abort()
                stream.close()

    def receiver():
        try:
            for line in sys.stdin:
                if len(line) > 12000:
                    raise ValueError('Voice request too large')
                command = json.loads(line)
                if command.get('action') not in ('prepare', 'listen', 'speak', 'pause'):
                    raise ValueError('Unknown voice action')
                with gate:
                    current['turn'] = int(command['turn'])
                    close_audio()
                try:
                    commands.get_nowait()
                except queue.Empty:
                    pass
                commands.put_nowait(command)
        finally:
            closed.set()
            close_audio()

    threading.Thread(target=receiver, daemon=True).start()
    asr = None
    tts = None
    def load_tts():
        nonlocal tts
        if tts is None:
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            session = ort.InferenceSession(str(ROOT / 'tts/model.onnx'), sess_options=options,
                                           providers=['CPUExecutionProvider'])
            tts = Kokoro.from_session(session, str(ROOT / 'tts/voices.bin'))

    while not closed.is_set():
        try:
            command = commands.get(timeout=.1)
        except queue.Empty:
            continue
        turn = command['turn']
        alive = lambda: not closed.is_set() and current['turn'] == turn
        try:
            if command['action'] == 'pause':
                continue
            if command['action'] == 'prepare':
                emit('state', turn, state='loading', message='Loading speech model · microphone off')
                load_tts()
                if alive():
                    emit('prepared', turn)
                continue
            if command['action'] == 'listen':
                emit('state', turn, state='loading', message='Preparing local listening…')
                if asr is None:
                    asr = Transcriber(str(ROOT / 'stt'), ModelArch.SMALL_STREAMING)
                if not alive():
                    continue
                audio = queue.Queue(maxsize=100)
                failure = threading.Event()
                finals = []

                class Listener(TranscriptEventListener):
                    def on_line_text_changed(self, event):
                        if alive():
                            emit('partial', turn, text=event.line.text[:1600])

                    def on_line_completed(self, event):
                        if alive() and event.line.text.strip():
                            finals.append(event.line.text.strip())

                    def on_error(self, event):
                        failure.set()

                # A new stream means no previous turn's audio/transcript is retained.
                stt_stream = asr.create_stream()
                stt_stream.add_listener(Listener())
                stt_stream.start()

                def capture(indata, frames, timing, status):
                    if not alive():
                        raise sd.CallbackAbort
                    if status:
                        failure.set()
                    try:
                        audio.put_nowait(indata[:, 0].copy())
                    except queue.Full:
                        failure.set()

                device = command.get('input')
                rate = int(sd.query_devices(device, 'input')['default_samplerate'])
                try:
                    with gate:
                        if alive():
                            stream = sd.InputStream(device=device, samplerate=rate, channels=1,
                                                    dtype='float32', blocksize=max(1, rate // 10),
                                                    callback=capture)
                            current['stream'] = stream
                            stream.start()
                    if alive():
                        emit('state', turn, state='listening', message='Listening · microphone on')
                    deadline = time.monotonic() + 60
                    while alive() and not finals and time.monotonic() < deadline:
                        if failure.is_set():
                            raise RuntimeError('Microphone audio could not keep up. Try again or use a faster device.')
                        try:
                            samples = audio.get(timeout=.1)
                        except queue.Empty:
                            continue
                        emit('level', turn, state='listening', level=float(min(1, np.sqrt(np.mean(samples ** 2)) * 8)))
                        stt_stream.add_audio(samples.tolist(), rate)
                    if failure.is_set() and alive():
                        raise RuntimeError('Microphone audio was interrupted. Please repeat your message.')
                finally:
                    close_audio()
                    # Stop can flush a final segment, but cancelled turns never submit it.
                    stt_stream.stop()
                    stt_stream.close()
                if alive():
                    if finals:
                        emit('transcript', turn, text=' '.join(finals)[:1600])
                    else:
                        emit('idle', turn)
            elif command['action'] == 'speak':
                emit('state', turn, state='loading', message='Preparing NORA’s voice…')
                load_tts()
                voice = command.get('voice', 'af_heart')
                if voice not in ('af_heart', 'af_bella'):
                    raise ValueError('Unknown voice')
                for text in speech_chunks(command.get('text', '')[:6000]):
                    if not alive():
                        break
                    samples, rate = tts.create(text, voice=voice, lang='en-us', speed=1.0)
                    if not alive():
                        break
                    samples = np.asarray(samples, dtype=np.float32)
                    if command.get('output') is None:
                        from speech_audio import SpeechAudio
                        try:
                            with gate:
                                if not alive():
                                    continue
                                stream = SpeechAudio(samples, rate)
                                current['stream'] = stream
                                stream.start()
                            emit('state', turn, state='speaking', message='NORA is speaking · microphone off')
                            deadline = time.monotonic() + len(samples) / rate + 15
                            while alive() and not stream.wait():
                                if time.monotonic() > deadline:
                                    raise RuntimeError('Audio output stopped responding')
                                start = min(len(samples), int(stream.position() * rate))
                                frame = samples[start:start + max(1, rate // 20)]
                                level = float(min(1, np.sqrt(np.mean(frame ** 2)) * 6)) if len(frame) else 0.0
                                emit('level', turn, state='speaking', level=level)
                        finally:
                            close_audio()
                        continue
                    cursor = [0]
                    energy = [0.0]
                    done = threading.Event()

                    def playback(outdata, frames, timing, status):
                        outdata.fill(0)
                        if not alive():
                            raise sd.CallbackAbort
                        start = cursor[0]
                        count = min(frames, len(samples) - start)
                        if count:
                            outdata[:count, 0] = samples[start:start + count]
                            energy[0] = float(min(1, np.sqrt(np.mean(outdata[:count] ** 2)) * 6))
                        cursor[0] += count
                        if cursor[0] >= len(samples):
                            raise sd.CallbackStop

                    try:
                        with gate:
                            if alive():
                                stream = sd.OutputStream(device=command.get('output'), samplerate=rate,
                                                         channels=1, dtype='float32', blocksize=rate // 20, latency='high',
                                                         callback=playback, finished_callback=done.set)
                                current['stream'] = stream
                                stream.start()
                        if alive():
                            emit('state', turn, state='speaking', message='NORA is speaking · microphone off')
                        deadline = time.monotonic() + len(samples) / rate + 10
                        while alive() and not done.wait(.05):
                            if time.monotonic() > deadline:
                                raise RuntimeError('Audio output stopped responding')
                            emit('level', turn, state='speaking', level=energy[0])
                    finally:
                        close_audio()
                if alive():
                    # Allow the loudspeaker tail to decay before listening again.
                    time.sleep(.35)
                    emit('done', turn)
        except Exception as error:
            close_audio()
            if alive():
                emit('error', turn, message=str(error)[:500])
    if asr is not None:
        asr.close()


if __name__ == '__main__':
    main()
