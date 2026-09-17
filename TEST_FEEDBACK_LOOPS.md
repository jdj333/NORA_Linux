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
