# Local voice mode

NORA can listen and speak entirely on this computer using **Moonshine Small
Streaming English** for recognition and **Kokoro v1.0 INT8** for speech. The
existing Qwen model still generates conversational answers and canvas diagrams.
Speech models add audio input/output; they do not increase Qwen's reasoning or
image-understanding abilities.

## Using voice

1. Open NORA Chat. **Voice off** is the default at every launch. No speech worker
   or microphone is opened until you enable it.
2. In **Settings**, choose Heart or Bella (American English), a microphone, and
   speakers, or leave the audio devices on the system defaults. Choices last for
   this application session. Opening Settings switches voice off.
3. Click **Voice off** to enable voice. Model loading is shown before **Listening ·
   microphone on**. Speak normally and pause to finish your turn. Recognized words
   enter the same conversation and canvas workflow as typed messages.
4. NORA closes the microphone while preparing and speaking her response, then
   resumes listening automatically. The emerald follows microphone and playback
   amplitude; the existing animation setting also applies to voice.
5. **Pause listening** releases the microphone. **Resume listening** starts another
   turn. **Stop voice** interrupts synthesis/playback and returns to listening.
   Click **Voice on** to turn the entire feature off and stop its worker immediately.

Voice turns take turns with NORA; talking over her does not interrupt her yet.
Use the on-screen controls to interrupt. Full-duplex conversation and acoustic
echo cancellation are not implemented. Startup music stops when voice is enabled.

Switching chats, starting a new chat, opening Settings, or closing the window
switches voice off. Typed messages pause listening while they are processed.
The chat and canvas remain available when audio devices or models fail.

If you already have a draft, recognized words appear as **HEARD** in the transcript
and the draft is preserved. Voice pauses so you can finish it. Slash commands and
explicit canvas-clearing requests are placed in the input for review and **Send**.
Spoken natural-language command requests go through the model's proposal/review
path; they do not trigger the typed read-only command shortcuts automatically.
Model-proposed shell commands still require **Run** in the terminal.

## Privacy and audio behavior

- No API keys, cloud inference, runtime model downloads, or wake-word listener.
- Raw microphone audio stays in bounded memory buffers and is not recorded to disk.
  Recognized text and replies follow the existing local chat-history policy.
- Audio-device enumeration in Settings does not open a recording stream.
- Microphone capture and speech playback never overlap in the worker. A brief
  delay after playback allows the speaker tail to decay before listening resumes.
- The worker is a separate, unprivileged process. Turning voice off kills it even
  if native inference is busy, releasing its device handles and model memory.
- Code blocks, canvas directives, and raw URLs are omitted or simplified for
  speech. Spoken replies are capped at 1,600 characters; full text remains in chat.
  Speech is synthesized in short chunks after the text reply completes.
- English is the initial supported language. Accent, background noise, technical
  vocabulary, microphone quality, and CPU load affect recognition and latency.

## Offline build assets

`scripts/voice-assets.json` pins speech models and license notices by URL, byte
count, and SHA-256. `scripts/voice-requirements.txt` locks the Python runtime and
its transitive dependencies with published wheel hashes. Models and runtime live
in `/opt/nora/voice`; generated files are ignored by Git. Speech model assets are
about 251 MiB, plus runtime dependencies and their installed size.

Run on the host before either build path:

```sh
python3 scripts/prepare-llm.py
python3 scripts/prepare-voice.py
```

The Docker builder installs the locked runtime for amd64 automatically. GitHub
Actions stages the voice models and verifies real inference in a network-disabled
container before building the ISO. For a native Debian
13 amd64 build, install the runtime into the overlay first:

```sh
sudo apt-get install python3-pip
python3 -m pip install --only-binary=:all: --require-hashes \
  --target config/includes.chroot/opt/nora/voice/python \
  -r scripts/voice-requirements.txt
sudo ./scripts/build.sh
```

This uses an isolated target directory, not the system Python environment.
`prepare-voice.py --verify-only` checks every asset before the ISO build. The live
image includes PortAudio and espeak-ng dependencies. Models, libraries, and
license notices travel inside the ISO; no first-use downloads are required.

Upstream sources:
[Moonshine](https://github.com/moonshine-ai/moonshine),
[Kokoro model](https://huggingface.co/hexgrad/Kokoro-82M), and
[Kokoro ONNX runtime](https://github.com/thewh1teagle/kokoro-onnx).
The selected English Moonshine model uses MIT licensing; Kokoro weights are
Apache-2.0. Bundled runtime dependencies retain their own license notices.

## Verification and remaining hardware checks

See [VOICE_VALIDATION.md](VOICE_VALIDATION.md) for measured results and limits.

Run `python3 -m unittest discover -s tests` for policy and controller checks;
GTK checks require Linux, GTK3, and a display (`xvfb-run -a` works).

On an installed voice-enabled NORA image:

```sh
python3 scripts/verify-voice.py
```

Run that command from a source checkout. It synthesizes both voices, recognizes
the generated speech, checks silence, and rejects Python network calls. No audio
device is opened. `NORA_VOICE_ROOT` can point at another staged runtime.

`tests/voice_worker_harness.py` and `tests/run_voice_worker_smoke.py` exercise the
real worker and real models with simulated input/output devices. They check
transcription, playback levels, turn-taking, and device release on pause. The
fixture must be generated speech, not private microphone audio.

Physical microphone/speaker testing is still required: device permissions,
volume, noise, accents, speaker echo, hot unplug, and end-to-end response time.
A browser noVNC connection does not establish that the guest has a microphone or
speaker route; VM audio forwarding needs separate setup and testing. Current
ISO support remains amd64, not Raspberry Pi. Native ARM-container tests do not
establish Raspberry Pi performance or boot support.
