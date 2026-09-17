# Test feedback loops

A running record of NORA regression tests, validation commands, failures, fixes,
and remaining checks. Use this with [FEATURE_LOG.md](FEATURE_LOG.md) and
[LEARNING.md](LEARNING.md) before repeating work.

Initialized **2026-09-16**. Repository HEAD at initialization: **715f4f7**.
Voice implementation is still in the working tree. Earlier results below are
historical evidence, not fresh validation of every feature against today's tree.

## Recording a test loop

1. Record the feature ID, source commit **and dirty state**, environment, and exact
   artifact being tested. For an ISO, record its filename and SHA-256.
2. Record the command, result, passed/failed/skipped counts, and evidence location.
3. Keep failures and blocked attempts. Explain the cause and the corrective change.
4. Add the confirming rerun separately; do not overwrite the failed result.
5. Stop repeating a passing check unless inputs change or an unresolved concern
   justifies it. Record untested hardware and deployment steps explicitly.

**PASS** means the stated check passed. **FAIL** means it ran and found a problem.
**BLOCKED** means the environment prevented the check. **SKIPPED** is not a pass.
**NOT RUN** means there is no execution evidence. A successful source test or
builder image does not establish that an ISO boots or that physical audio works.

Do not put credentials, private conversations, microphone recordings, or complete
sensitive command output in this log. Summarize the result and link safe evidence.
Local `.build/` and `dist/` artifacts are ignored by Git and may later disappear;
the checked-in summary remains the durable record.

## Reusable commands

These are recipes, not claims that a new run has occurred. Run from the repository
root. Check the environment and staged assets first.

| Check | Command | Requirements / limits |
| --- | --- | --- |
| Source state | `git rev-parse HEAD` and `git status --short` | Record both; uncommitted changes matter |
| Whitespace | `git diff --check` | Covers tracked changes; review new files too |
| Build shell | `bash -n scripts/build.sh` | Syntax only |
| Python suite | `python3 -m unittest discover -s tests -v` | HTTP fixtures need loopback; GTK checks skip without GTK/display |
| Full Linux suite | `xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -v` | Debian Python, GTK3, Cairo, Xvfb, xauth |
| GTK regression | `xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -p test_chat_window.py -v` | Temporary chat databases; no real history deletion |
| Voice asset integrity | `python3 scripts/prepare-voice.py --verify-only` | Requires staged voice assets; checks hashes and sizes |
| Real speech inference | `NORA_VOICE_ROOT=/opt/nora/voice python3 scripts/verify-voice.py` | Installed runtime; synthetic speech and silence, no audio devices |
| amd64 builder | `docker build --platform linux/amd64 -t nora-builder:voice .` | Prepare chat and voice assets first; builder only, not an ISO |
| Network-isolated speech | See command below | Tests packaged runtime, not microphone or speakers |
| ISO structure | `./scripts/verify-iso.sh dist/nora-linux-13-amd64.hybrid.iso` | Does not replace BIOS/UEFI boot tests |
| ISO checksum | `(cd dist && shasum -a 256 -c SHA256SUMS)` | Verify the exact artifact named in the manifest |

With a freshly built builder containing `scripts/verify-voice.py`:

```sh
docker run --rm --platform linux/amd64 --network none --entrypoint python3 \
  -e NORA_VOICE_ROOT=/build/config/includes.chroot/opt/nora/voice \
  nora-builder:voice scripts/verify-voice.py
```

The real worker smoke test requires the speech runtime, a **generated** float32
NumPy audio fixture at 24 kHz, and the following environment. Replace the paths
with the actual staged Linux paths; these are not a microphone recording:

```sh
NORA_VOICE_ROOT=/path/to/voice \
NORA_CHAT_DIR=/path/to/chat \
NORA_TEST_AUDIO=/path/to/generated-speech.npy \
python3 tests/run_voice_worker_smoke.py
```

See [VOICE.md](VOICE.md) for preparation and [VOICE_VALIDATION.md](VOICE_VALIDATION.md)
for measured results. Under amd64 emulation, speech validation can take minutes.

To retain a **new** full Linux regression run without hiding its exit status:

```bash
# Run this block in Bash, not zsh (PIPESTATUS is a Bash array).
set -o pipefail
run_dir=".build/regression/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$run_dir"
git rev-parse HEAD > "$run_dir/commit.txt"
git status --short > "$run_dir/status.txt"
xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -v 2>&1 | tee "$run_dir/tests.log"
test_exit=${PIPESTATUS[0]}
printf '%s\n' "$test_exit" > "$run_dir/exit-code.txt"
# Summarize the outcome below, including skips and the working-tree changes.
exit "$test_exit"
```

Run that block in a dedicated shell; `exit` ends it. Preserve the tested diff and
new source files separately if exact reproduction of a dirty-tree run is needed.

## Recorded feedback loops — 2026-09-16

### TFL-001 — Earlier prototype and workspace regressions

Imported from existing validation documents. Original invocations are not repeated
here where the record only retained outcomes. The commands above are reusable
recipes, not reconstructed claims about those older invocations.

| Scope / features | Recorded result | Durable evidence |
| --- | --- | --- |
| Debian ISO, branding (F-001) | PASS: final ISO internal SHA-256/MD5 manifests and documented boot checks; hardware gaps remain | [Prototype validation](VALIDATION.md) |
| Offline chat (F-003) | PASS: 8 transport tests and final ISO manifest checks | [Chat validation](CHAT_VALIDATION.md) |
| OS facts and commands (F-004) | PASS: 30 tests on macOS/Linux; real command file effects and cancellation checked | [OS access validation](OS_ACCESS_VALIDATION.md) |
| Website reading (F-006) | PASS: 45 tests, including 11 website-reader tests | [Web validation](WEB_ACCESS_VALIDATION.md) |
| Split panes (F-007) | PASS: 45 non-GUI + 7 guest GTK tests | [Pane validation](SPLIT_PANE_VALIDATION.md) |
| History (F-009) | PASS: 50 non-GUI + 12 guest GTK tests; host skipped those 12 GUI tests | [History validation](HISTORY_VALIDATION.md) |
| Initial canvas and collapse (F-010, F-011) | PASS: 54 non-GUI + 15 guest GTK tests; collapse checked separately | [Canvas validation](CANVAS_VALIDATION.md) |
| Emerald presence (F-012) | PASS: 58 non-GUI + 19 guest GTK tests | [Emerald validation](EMERALD_VALIDATION.md) |
| Expressions (F-013) | PASS: 3 envelope + 4 emerald GTK checks | [Expressions record](EMERALD_VALIDATION.md#expressions-update) |
| Visual maps/images (F-014) | PASS: 66 non-GUI + 22 guest GTK tests | [Visual canvas record](CANVAS_VALIDATION.md#visual-explanations-links-movement-and-images) |
| Website styling (F-015) | PASS: 22 existing guest GTK tests, syntax, and whitespace | [Style validation](STYLE_VALIDATION.md) |

These counts describe successive historical suites. Do not add them together as
unique tests or use them as the current suite size.

### TFL-002 — Sandbox failure followed by successful host regression

**Features:** F-019, F-020. **Source:** changes later committed in `715f4f7`.
**Environment:** macOS host, initially under restricted loopback permissions.

- **BLOCKED:** `python3 -m unittest discover -s tests` reported 3 setup errors
  because HTTP fixtures could not bind `127.0.0.1` (`PermissionError: Operation not
  permitted`). GTK checks also skipped. This did not establish a product defect.
- **Correction:** reran the same command with authorized loopback access.
- **PASS:** 88 discovered; 66 passed and 22 GTK tests skipped. Linux GUI checks
  were tracked separately.
- **Evidence:** command output in the development session; no durable raw log was
  saved for this attempt. Do not confuse this older suite with the voice suite.

### TFL-003 — Startup music lifecycle

**Feature:** F-019. **Source:** changes later committed in `715f4f7`.
**Environment:** Debian test container with GStreamer and MP3 decoder packages.

- **PASS:** an ad hoc `docker exec -i nora-desktop python3 -` check loaded
  `StartupAudio`, replaced only its audio sink with GStreamer's `fakesink`, and
  decoded the actual bundled MP3 to end-of-stream.
- **PASS:** no decoder error, cleanup at end-of-stream, no replay, early stop, and
  a startup callback cancelled before playback.
- The inline script was not retained as a reusable test file. Its entry command
  alone cannot reproduce the check; this row records the scope and result only.
- **NOT RUN:** audible playback through the user's speakers or a rebuilt ISO.

### TFL-004 — Canvas capability and autonomous layout

**Feature:** F-020. **Source:** changes later committed in `715f4f7`.

- **PASS:** `python3 -m unittest discover -s tests` on macOS: 93 discovered,
  68 passed, 25 GTK checks skipped.
- **PASS:** `docker exec -w /tmp/nora-canvas-check nora-desktop xvfb-run -a python3 -m unittest discover -s tests -p test_chat_window.py`:
  all 25 GTK tests passed.
- Checked immediate visual examples without a loaded LLM, replacement preserving
  user notes, arrange/clear, Follow chat controls, and capacity reclamation.
- **PASS:** Python compilation and `git diff --check`.
- **NOT RUN:** a new ISO boot or deployment of this update into the live VM.

### TFL-005 — Speech model integration failure and correction

**Feature:** F-021. **Source:** voice working tree based on `715f4f7`.
**Environment:** native ARM64 Debian container, isolated speech Python environment.

- **FAIL:** the first real inference check passed Kokoro synthesis but Moonshine
  rejected `Transcriber(..., options={'num_threads': '2'})` with
  `Unknown transcriber option: 'num_threads'`.
- **Correction:** removed the unsupported Moonshine option. Kokoro keeps its own
  supported ONNX session thread setting.
- **PASS:** rerun recognized the generated “Hello Nora, please show me an idea.”
  Model load was approximately 0.15 s; the recognition check completed in 0.94 s.
- **Follow-up:** both voices and silence were subsequently covered by the retained
  `scripts/verify-voice.py` in TFL-006. The original failed inline test was not saved.

### TFL-006 — Local voice regression and real inference

**Feature:** F-021. **Source:** uncommitted voice work based on `715f4f7`.
The complete suite ran before a final startup-toggle failure guard; the affected
29 GTK tests passed again after that guard. No claim of a new ISO or deployment.

| Command / check | Result |
| --- | --- |
| `docker exec -w /tmp/nora-canvas-check nora-desktop xvfb-run -a python3 -m unittest discover -s tests` | **PASS:** 105 tests, no skips; includes 29 GTK checks |
| Same command with `-p test_chat_window.py` after the final toggle guard | **PASS:** 29 GTK tests |
| `NORA_VOICE_ROOT=/tmp/nora-voice-models /tmp/nora-voice-env/bin/python /tmp/verify-voice.py` inside the ARM64 test container | **PASS:** Heart and Bella synthesize; recognition recovers the phrase; silence has no transcript; Python network calls rejected |
| `NORA_VOICE_ROOT=/tmp/nora-voice-models NORA_CHAT_DIR=/tmp/nora-canvas-check/config/includes.chroot/usr/share/nora/chat NORA_TEST_AUDIO=/tmp/nora-voice-sample.npy /tmp/nora-voice-env/bin/python /tmp/run_voice_worker_smoke.py` inside the ARM64 container | **PASS:** real engines/worker with simulated devices; audio levels, turn-taking, and release on pause |
| `docker build --platform linux/amd64 -t nora-builder:voice . > .build/voice-builder.log 2>&1` | **PASS:** target-architecture dependencies installed with hash checks; this builder snapshot preceded later source edits |
| `docker exec -e NORA_VOICE_ROOT=/build/config/includes.chroot/opt/nora/voice nora-voice-amd64 python3 /tmp/verify-voice.py` | **PASS:** packaged amd64 inference; temporary container was created with `--network none`, then removed |
| `python3 scripts/prepare-voice.py --verify-only` | **PASS:** staged model sizes and hashes |
| Python compilation, `bash -n scripts/build.sh`, `git diff --check` | **PASS** |

**Evidence:** [Voice validation](VOICE_VALIDATION.md), [voice guide](VOICE.md),
local `.build/voice-builder.log`, and development-session output. `/tmp` paths
refer to staged copies and may not exist in a future container.

**Performance finding:** generating about 2.2–2.3 seconds of speech took
3.17/3.68 seconds in the native ARM container and 127.67/144.37 seconds under amd64
emulation. Those are diagnostic observations with shared CPU resources, not
native PC or Raspberry Pi benchmarks. Functionality passed; emulation latency is
not acceptable for comfortable voice conversation.

### TFL-007 — Documentation-log validation

**Features:** F-002, F-022, F-023. **Source:** documentation working tree based on
`715f4f7`, alongside the existing uncommitted voice implementation.

**PASS:** 64 local Markdown links resolved; all 23 feature IDs were unique;
test-to-feature references existed; fenced code blocks were balanced.
**PASS:** `git diff --check`.
**NOT RUN:** application regression or ISO build; this change only adds documentation.
Evidence: local command output during creation of these logs.

Reusable documentation check (run from the repository root):

```sh
python3 - <<'CHECK'
from pathlib import Path
import re
files = ['TEST_FEEDBACK_LOOPS.md', 'FEATURE_LOG.md', 'README.md', 'LEARNING.md']
links = 0
for name in files:
    text = Path(name).read_text()
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        assert (Path(name).parent / target.split('#')[0]).exists(), (name, target)
        links += 1
    assert sum(line.startswith(chr(96) * 3) for line in text.splitlines()) % 2 == 0, name
ids = re.findall(r'^\| (F-\d{3}) \|', Path('FEATURE_LOG.md').read_text(), re.M)
assert len(ids) == len(set(ids)), 'Duplicate feature IDs'
for reference in re.findall(r'F-\d{3}', Path('TEST_FEEDBACK_LOOPS.md').read_text()):
    assert reference in ids, reference
print(f'PASS: {links} local links; {len(ids)} unique feature IDs; references and fences valid.')
CHECK
```

This checks local file targets, not HTTP reachability or rendered heading anchors.

## Outstanding validation

| Check | Status | Next evidence needed |
| --- | --- | --- |
| Physical voice input/output, accents, noise, hot unplug, speaker echo | NOT RUN | Real microphone/speaker test with chosen devices and hardware details |
| Full voice-enabled ISO build and boot | NOT RUN | Exact ISO checksum, BIOS/UEFI desktop boot, voice controls and audio |
| Native amd64 conversational latency including Qwen | NOT RUN | Time from end of speech to first spoken response, CPU/RAM and model details |
| Raspberry Pi 5 image/performance | NOT RUN | Separate ARM image and actual board testing |
| New voice workflow run on GitHub | NOT RUN | Push/run ID, source commit, and verified workflow outcome |

## Entry template

```markdown
### TFL-NNN — Short description
- Date/time (UTC):
- Feature IDs:
- Source commit and dirty changes:
- Environment / artifact / checksum:
- Exact command:
- Result: PASS / FAIL / BLOCKED / SKIPPED / NOT RUN
- Counts: passed / failed / skipped
- Evidence path or workflow URL:
- Failure cause and correction, if any:
- Confirming rerun:
- Remaining limits / next check:
```

### TFL-008 — Larger VM and latest workspace startup

- **2026-09-16**, source **0efeed2**, clean before this run; only documentation
  changed afterward. Local development remaster of the retained Debian rootfs,
  latest `config/includes.chroot`, startup music, and the pinned amd64 speech
  runtime from `nora-builder:voice`. This is not the GitHub release ISO.
- Artifact: `nora-desktop:/test/nora-voice-dev.iso`, SHA-256
  `48516162125cea552dfd74c629f30ec0e03b8cf5b10bd87fd490152fb790035c`.
- **BLOCKED initially:** sandbox denied `sysctl` and Docker socket inspection.
  Authorized elevated inspection succeeded: host 32 GiB / 10 logical CPUs.
- **FAIL, then PASS:** chroot `apt-get update` reported its absent live-medium
  file source. Online indexes refreshed; `chroot /test/rootfs apt-get install
  -y libportaudio2 libasound2-plugins espeak-ng python3-cairo python3-gi-cairo`
  then exited 0. Logs: `nora-boot-test:/test/voice-apt.log` and
  `/test/voice-install.log`.
- **PASS:** `colima stop` then `colima start --cpu 8 --memory 16`;
  `docker info --format '{{.MemTotal}} {{.NCPU}}'` returned 16733589504 bytes / 8.
- **PASS:** QEMU `-m 8192 -smp 6 -accel tcg,thread=multi`;
  `python3 /test/qmp.py /test/qmp.sock query-memory-size-summary` returned
  8589934592 bytes; `query-cpus-fast` returned six virtual CPUs.
- An early QMP connection while the ISO was still copying was refused. After
  transfer and QEMU launch completed, `query-status` returned running.
- **PASS:** noVNC HTTP page, complete RFB 3.8 authentication and framebuffer
  initialization (1280x800), and fresh QMP screenshot showing the maximized NORA
  workspace, canvas, emerald, **Voice off**, and **Offline model ready**.
  Screenshot: `nora-desktop:/test/voice-desktop.ppm`. Opened the browser at
  `http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale`.
- **NOT RUN:** new conversational inference or full regression suite in this
  guest. Physical audio is unavailable through this noVNC setup; voice quality,
  microphone forwarding, and speaker output are not validated. The GitHub build
  was still in progress when checked; no release-success claim is made.

### TFL-009 — UTM audio-capable VM setup

- **2026-09-16:** User authorized setting up UTM for speaker/microphone support.
- **PASS:** `brew install --cask utm` installed UTM 4.7.5 in `/Applications`.
- Created ignored local bundle `dist/NORA Linux.utm` with the TFL-008 ISO,
  8192 MiB RAM, six x86_64 CPUs, Q35, Intel HDA duplex audio, emulated networking,
  and a native display. No host directory sharing is configured.
- **PASS:** `plutil -lint 'dist/NORA Linux.utm/config.plist'` reported OK.
  `open -a UTM 'dist/NORA Linux.utm'` launched UTM.
- **BLOCKED:** `utmctl list` returned macOS Apple Events error -1743 (automation
  permission denied); `utmctl start` could not resolve the VM. This does not
  establish that the UI import completed. User was asked to allow automation.
- **NOT RUN:** UTM guest boot, physical speaker playback, microphone permission,
  and voice conversation. The original Docker/browser VM was preserved.

### TFL-010 — Correct UTM bundle import failure

- User screenshot confirmed UTM rejected the TFL-009 bundle. That earlier plist
  syntax check did **not** establish that UTM could decode the configuration.
- **Confirmed cause:** `Drive[0].Interface` was `ide`; UTM v4.7.5's
  `QEMUDriveInterface` enum requires the case-sensitive string `IDE`.
- Corrected `dist/NORA Linux.utm/config.plist` and reopened the absolute bundle
  path with `open -a UTM`. Verified 10 configured enum values against official
  v4.7.5 source and verified the bundled ISO exists: **PASS**.
- `utmctl list` still returned Apple Events permission error -1743. Actual import,
  boot, and speaker/microphone behavior remain awaiting UI confirmation.

### TFL-011 — User confirms startup music playback

- **2026-09-16**, following the UTM import correction in TFL-010.
- **PASS (user-observed):** User reported "Music startup verified works" in the
  UTM testing session. This confirms startup music playback through the VM's
  speaker output. No new automated command or audio recording was used.
- **NOT VERIFIED:** Microphone capture, speech recognition, synthesized NORA
  replies, or a complete voice conversation. Music playback alone does not
  establish these paths work.

### TFL-012 — Native Mac inference and chat context tuning

- **2026-09-16:** Source `0efeed2` plus local tuning changes. Paused the redundant
  Docker QEMU guest with QMP `stop`, preserving its live state. UTM stays active.
- Installed Homebrew llama.cpp 0.4.1. Ran:
  `llama-bench -m config/includes.chroot/opt/nora/llm/model.gguf -p 256 -n 64 -t 2,4 -ngl 0,99 -r 2 -o json`.
  Evidence: `.build/utm/native-bench.json`. Native CPU generation: 83.23 t/s at
  two threads, 126.26 at four. Metal: 193.16 at two, 180.56 at four. Selected two
  threads with Metal; no claim that more emulated vCPUs yield the same benefit.
- Started `scripts/start-mac-model.sh`; `/health` returned `{"status":"ok"}`.
  Loopback-only port 8089. Same bundled GGUF; no external model API.
- Compact system prompt: 1580 -> 971 characters. Social-only greetings omit fresh
  OS measurements; substantive questions retain them. Explicit prompt caching
  enabled. Production endpoint stays guest localhost; optional environment
  variables configure host inference for development.
- Actual host streaming Hello trials: tuned first token 0.060 / 0.011 seconds,
  complete reply 0.108 / 0.057 seconds. Original-prompt trials 0.090 / 0.058 seconds
  total. These short cached trials do not demonstrate a prompt-only speedup;
  the main expected gain is native inference. No timed UTM baseline was captured.
  Evidence: `.build/utm/chat-bench.json`. Initial benchmark harness failed on a
  null content delta; treating it as empty fixed the harness. App already handles
  null deltas.
- **BLOCKED then PASS:** sandbox loopback binding prevented initial transport
  test. Elevated host suite: 107 tests, 29 GTK tests skipped on macOS.
- **FAIL then PASS:** first Linux copy omitted the scripts directory required by
  the packaging test. Repeated with correct repository layout and package script:
  `docker exec -w /tmp/nora-tuning nora-desktop xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -v`.
  **107 tests passed, none skipped.** Evidence: `.build/utm/linux-tuning-tests.log`.
- User ran the scoped local updater inside UTM and confirmed **Host model ready**.
  Updated app/client and user autostart in the live guest; backups in the printed
  `/tmp/nora-model-update.*` directory. Guest speech remains emulated. Subjective
  end-to-end voice speed and a timed guest chat response are not yet measured.

### TFL-013 — Voice enabled automatically after startup music

- User changed the requested default from opt-in/off to voice-on at startup.
- New app windows queue automatic voice activation when startup music ends or
  is unavailable. Manual activation stops music and cancels the queued default.
  Explicit voice-off paths, chat changes, Settings, and window close prevent a
  pending callback from unexpectedly restarting voice. Missing audio/model
  errors retain the existing voice-off fallback and working text chat.
- Added GTK checks for exactly-once startup activation, cancellation on New chat,
  and cancellation on close. VoiceSession itself remains inert until explicitly
  enabled by the app lifecycle.
- **PASS:** `docker exec -w /tmp/nora-tuning nora-desktop xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -v`:
  **110 tests, all passed.** Log: `.build/utm/voice-default-tests.log`.
- Staged scoped loopback updater including app.py, client.py, startup_audio.py.
  User was given the command to apply it in the running UTM guest; physical
  auto-listening after the song has not yet been confirmed.

### TFL-014 — Missing spoken chat replies investigation (in progress)

- User reports chat transitions from Thinking to Ready without audible speech.
  Startup music previously worked. UTM process confirms Intel HDA duplex routed
  to SPICE, but this does not prove that the speech worker reaches playback.
- **Confirmed diagnostics defect:** voice errors disabled voice and set an error
  message, but the next model health callback overwrote it with the normal ready
  status. Added a retained voice error cleared on explicit retry.
- **PASS:** Linux GTK regression suite, including error persistence across a
  model health refresh: **33 tests passed**. Log:
  `.build/voice-diagnostics/gtk-tests.log`. Fix is local, not deployed yet.
- Prepared `.build/voice-diagnostics/check.py` for user execution in UTM. It checks
  installed source hashes, PulseAudio sink/mute state, PortAudio device list,
  and times a fixed synthesized sentence using the real speech worker. It never
  opens a microphone. Reports return only to Mac loopback port 8094.
- **Pending:** guest report and user confirmation of test playback. Do not infer
  that emulation latency, device routing, or microphone failure is the root cause
  before obtaining this evidence. Existing measured emulated TTS slowness is a
  possible contributor, not a diagnosis of this session.

#### TFL-014 follow-up — Intermittent, unintelligible playback

- User now reports occasional speech that sounds fast and unintelligible; they
  cannot distinguish pitch increase from missing syllables. This confirms some
  speech reaches playback, but not that sample timing or waveform quality is correct.
- Source inspection: Kokoro uses speed=1.0 and the returned sample rate is passed
  to PortAudio. No confirmed sample-rate mismatch was found. The 50 ms Python
  output callback ignores underflow status; callback starvation under emulation
  remains a hypothesis, not a proven cause.
- Extended the scoped guest diagnostic to generate one sentence, record sample
  rate/count, expected duration, actual stream rate, playback wall time and
  underflow callback count, then play the same generated waveform through
  GStreamer (the startup-music path). Temporary synthesized audio is removed
  afterward. No microphone recording or chat history is collected.
- **PASS:** both diagnostic Python files compile. **PENDING:** actual guest
  execution and listening comparison. No speed/pitch workaround was applied
  without establishing the playback fault.

### TFL-015 — Confirmed underruns and buffered speech playback fix

- Guest report received at `.build/voice-diagnostics/report.json`; user heard
  choppy attempts followed by clear final GStreamer playback.
- Output was unmuted, PulseAudio sink 48 kHz stereo. Synthesized waveform and
  requested/actual PortAudio stream were all 24 kHz, so no API-level rate
  mismatch was observed. Report: 32 underflow callbacks across 43 callbacks,
  repeated ALSA underruns, final 1.323-second waveform drained in 0.337 seconds
  through PortAudio. Same final waveform through GStreamer: 1.72 seconds and
  user-confirmed clear. Counters span chunks; sample count/time describe the last
  chunk. The user-reported three choppy voices are not mapped one-to-one to events.
- Synthesis of the final chunk took 60.45 seconds; complete diagnostic speech
  finished after 118.81 seconds. Playback quality and synthesis delay are separate.
- Changed system-default speech output to buffered GStreamer WAV playback, with
  sample-rate headers, playback-position-driven emerald levels, cancellation,
  EOS/error handling, and temporary-file cleanup. Explicit selected devices
  retain PortAudio with high latency. Persistent voice-error display included.
- **PASS:** full Linux suite via `/tmp/nora-voice-env/bin/python` with
  `PYTHONPATH=/usr/lib/python3/dist-packages` and xvfb: **113 tests, no skips**.
  Includes real clocked GStreamer/fakesink duration and cancellation tests.
- **PASS:** real speech-worker smoke test with actual models, generated input,
  simulated microphone, and clocked GStreamer fakesink: transcription, synthesis,
  audio levels, no input/output overlap, and audio release on pause.
  Logs: `.build/voice-diagnostics/playback-tests.log`, `buffered-worker-test.log`.
- Updated CI test dependencies so buffered playback tests can run there.
- Scoped update staged for UTM; user asked to apply it and verify a real spoken
  chat reply. Unit/integration passes are not a claim of deployed audible success.

### TFL-016 — Speech preloading, spoken chat, microphone opt-in

- User requests loading speech into memory at startup, default microphone off,
  and automatic spoken chat replies. Supersedes automatic listening at startup.
- Worker now accepts `prepare`, initializes Kokoro/ONNX once and retains it for
  later synthesis. Preparation never opens an input or output stream. ASR model
  loading remains on demand. Constructor remains inert; app activation starts
  preloading alongside startup music. Speaking or explicit mic-on stops music.
- Separate Voice and Mic controls; `listen()` cannot run unless the mic flag is
  explicitly enabled. Completed spoken replies resume listening only if mic-on.
  Stop speech pauses without unloading. Settings/chat changes cancel audio and
  mic consent, while preserving voice enablement and loaded models.
- **PASS:** complete Linux suite **115 tests**, no skips, including startup
  prepare-without-listen and speaking typed replies without mic activation.
  Evidence: `.build/voice-diagnostics/preload-tests.log`.
- **FAIL then PASS:** new integration-driver insertion initially had invalid
  indentation. Corrected it, compiled it, then ran the real model/worker test:
  prepare completed without any audio-device trace; STT, TTS, buffered playback,
  amplitude events and release/pause checks passed. Evidence:
  `.build/voice-diagnostics/preload-worker-test.log`.
- Preloading saves initialization only. The earlier ~60-second per-chunk guest
  synthesis cost is not claimed fixed. No model speedup is claimed from these tests.
- Updated scoped live-guest installer to include voice.py and all playback modules.
  User asked to apply and verify Voice on / Mic off; deployment confirmation pending.

### TFL-017 — Pre-commit regression validation

- Final working-tree application and tests copied to the Linux test environment.
  `PYTHONPATH=/usr/lib/python3/dist-packages xvfb-run -a /tmp/nora-voice-env/bin/python -m unittest discover -s tests -v`
  passed **115 tests, no skips**, in 5.331 seconds.
  Evidence: `.build/voice-diagnostics/precommit-tests.log`.
- `git diff --check` and `sh -n scripts/start-mac-model.sh` passed. Refreshed
  origin/main; local HEAD and remote matched before committing.
- User confirmed microphone is off in the updated session and reports continued
  speech preparation delay. Native Mac speech synthesis is proposed, not
  implemented in this revision. Preloading does not fix per-sentence emulation cost.

### TFL-018 — Raspberry Pi 5 ARM64 image

- **PASS:** official Pi OS Lite ARM64 Trixie base and llama.cpp b10964 ARM64
  archive SHA-256 verified against pinned `scripts/pi/assets.json`. Existing model
  and voice asset locks reused without staging the amd64 executable.
- **FAIL then fixed:** first build stopped at Xfce's configuration-file prompt.
  Added explicit `--force-confold` to retain NORA's settings. Evidence:
  `.build/pi/build-attempt-1.log`.
- **FAIL then fixed:** editing the active build script caused a shell read-offset
  parse error during attempt 2. Stopped editing active scripts and started a clean
  build from the finalized recipe. Evidence: `.build/pi/build-attempt-2.log`.
- **PASS:** preliminary image chroot loaded native ARM64 llama.cpp and generated
  a completion; both Kokoro voices generated speech and Moonshine transcribed
  "Hello Nora, please show me an idea." Silence produced no transcript. Network
  disabled in the voice check. Evidence: `.build/pi/runtime-check.log`.
- **PASS:** existing Linux application regression suite: **115 tests**, no skips,
  6.389 seconds. Evidence: `.build/pi/application-regression.log`.
- **PASS:** three Pi build configuration/shell tests:
  `python3 -m unittest discover -s tests -p test_pi_build.py -v`.
- Physical Pi 5 boot, first-boot password flow, filesystem expansion and actual
  microphone/speaker playback are **NOT TESTED**. Native Mac ARM64 inference
  results do not establish Pi performance.
- **PASS:** disposable-container first-boot integration exercised real user
  creation, password assignment, supplementary groups, LightDM autologin,
  removal of passwordless sudo defaults and reuse of an already configured account.
  Only `chvt`/`clear` were stubbed; real Pi console switching remains untested.
  Reusable command:
  `docker run --rm -v "$PWD:/work:ro" nora-pi-builder:trixie bash tests/run_pi_first_boot_smoke.sh`
  Evidence: `.build/pi/first-boot-test.log`.
- **PASS:** final clean image build completed installation and native inference;
  `systemd-analyze verify` accepted the first-boot unit. Both `e2fsck -fn` (root)
  and `fsck.fat -n` (boot) passed before compression. Evidence:
  `.build/pi/build.log`, `dist/pi/verification.txt`.
- **PASS:** independent read-only mount verification checked root/boot PARTUUIDs
  against cmdline/fstab, exact first-boot script/unit copies, the nora cloud-init
  default, empty machine-id and absent setup-complete marker.
  `docker run --rm --privileged -v "$PWD:/work:ro" nora-pi-builder:trixie bash scripts/pi/verify-image.sh`
  Evidence: `.build/pi/boot-links.log`.
- **PASS:** final shell/config tests and workflow YAML parsing. The new Actions
  workflow has not run on GitHub; local build evidence is distinct from CI results.
- **PASS:** compressed archive round trip reproduces the exact 10 GiB disk image.
  Raw image SHA-256:
  `b9554e1f6eff926618ec0879e934a8b95732e82989563f84393fe19b1dbc0047`.
  Compressed image SHA-256:
  `d12d5aafb2f03f1d38a6257bbc0e88891769a2ded9daa726429a8218b8ffae39`.
  `(cd dist/pi && shasum -a 256 -c SHA256SUMS)` reports **OK**.
  Evidence: `dist/pi/archive-roundtrip.txt`, `dist/pi/SHA256SUMS`.
- Built artifact: `dist/pi/nora-linux-13-raspberry-pi5-arm64.img.xz`.
  This is a locally built prototype ready for flashing and hardware testing, not
  a hardware-certified release. No SD card was written and no GitHub run triggered.
