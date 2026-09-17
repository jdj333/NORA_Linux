# Local voice validation

Verified 2026-09-16 for the working-tree local voice implementation.

## Automated checks

- **105 tests passed**, including **29 GTK integration tests**, in the Debian 13
  Linux test container under Xvfb. Coverage includes default-off behavior, stale
  worker/turn events, disable/kill, broken pipes, spoken-text limits, preserving
  drafts, reviewing recognized slash commands, voice state/emerald levels, and
  canvas use from recognized speech.
- Real **Moonshine Small Streaming English** and **Kokoro v1.0 INT8** inference:
  both `af_heart` and `af_bella` synthesized “Hello Nora. Please show me an idea.”
  Recognition returned the same words (with minor punctuation differences).
  Silence produced no transcript. Python networking was disabled in the test.
- Real worker integration with simulated sound devices passed: transcription,
  playback, nonzero input/output amplitude events, no overlapping microphone and
  speaker streams, and device release on pause. This used generated speech as
  input, not a recording of the user.
- The **amd64 Docker builder** installed all hash-locked runtime dependencies and
  verified the staged model checksums successfully.
- The packaged **amd64 runtime** passed both voice/recognition round trips and
  silence checks inside a container started with `--network none`.
- Python compilation, build-shell syntax, asset verification, and diff whitespace
  checks passed.

## Performance observations and limits

These are short diagnostic runs, not a hardware benchmark:

| Environment | Heart synthesis | Bella synthesis | Generated audio |
| --- | --- | --- | --- |
| Native ARM64 Debian test container on this Mac | 3.17 s | 3.68 s | about 2.2 s each |
| amd64 Debian container under QEMU emulation on this ARM Mac | 127.67 s | 144.37 s | about 2.3 s each |

Other test workloads shared the Docker VM. The figures exclude Qwen response time
and microphone endpoint detection. Emulated amd64 is unsuitable for comfortable
voice conversation here. These results do not predict native amd64 or Pi 5 speed.

No physical microphone/speaker session, accent/noise study, hot-unplug test,
acoustic echo test, or full ISO boot was performed for this change. The live VM
has not been updated with voice. Validate those separately before calling this a
hardware-tested release. Use [VOICE.md](VOICE.md) for controls and test commands.
