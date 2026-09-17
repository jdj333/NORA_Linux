# NORA feature history

History of requested features and their implementation state. This is a product
record, not proof that every feature is present in a published ISO.

Initialized **2026-09-16** from the development conversation, repository history,
and checked-in guides. Requests in the table follow conversation order; exact
request times were not retained. Refer to the commits and evidence rather than
inferring a release date from this document's creation date.

## Status conventions

- **Committed:** implementation is in the named commit; release/VM deployment is
  a separate fact.
- **Local:** implemented in the working tree, not yet committed or published.
- **Researched:** findings or recommendations exist; no implementation claimed.
- **Recorded:** documentation or workflow request has been captured.

The voice implementation and these logs are included in this revision, following
**715f4f7** on `main`. Their ISO release and VM deployment remain unverified.
Do not label them released until the matching build and release have been verified. [TEST_FEEDBACK_LOOPS.md](TEST_FEEDBACK_LOOPS.md) tracks validation.

## Requested features

| ID | Request and intent | State / implementation record | Guide or validation |
| --- | --- | --- | --- |
| F-001 | Build a Debian 13 derivative named NORA, using the supplied emerald logo, dark theme, and a bootable ISO | Committed: `fa2952f`; amd64 live-build configuration, Xfce, BIOS/UEFI entries. Physical hardware and Secure Boot need validation | [README](README.md), [initial validation](VALIDATION.md) |
| F-002 | Save reusable commands and gotchas to reduce repeated learning | Committed: `LEARNING.md`; ongoing additions remain part of each relevant change | [Learning notes](LEARNING.md) |
| F-003 | Open a terminal-like local AI chat at login; use a local model without an API key | Committed: `fc8f043`; Qwen2.5-0.5B-Instruct Q4_K_M with llama.cpp, GTK autostart | [Chat guide](CHAT.md), [initial chat tests](CHAT_VALIDATION.md) |
| F-004 | Let NORA inspect the OS and run commands; speak as the OS itself | Committed: `71fb13d`; measured OS facts, explicit commands, reviewable model proposals | [OS access validation](OS_ACCESS_VALIDATION.md) |
| F-005 | Build the ISO in GitHub Actions and publish it in repository releases | Committed: `71fb13d`; successful main builds publish prereleases, split ISO assets, and checksums. Voice model verification is a local extension | [Release workflow](.github/workflows/build-iso.yml), [README](README.md) |
| F-006 | Access the web and read websites when online | Committed by `50c441c`; URL text reader with source information and bounded model context | [Web validation](WEB_ACCESS_VALIDATION.md) |
| F-007 | Separate conversation from the command terminal on the right | Committed by `50c441c`; independent conversation and command displays | [Pane validation](SPLIT_PANE_VALIDATION.md) |
| F-008 | Start maximized, retaining desktop panels and window controls | Committed by `50c441c`; maximized window, not exclusive fullscreen | [Chat guide](CHAT.md) |
| F-009 | Persistent history tabs/sidebar and a setting to clear all history and context | Committed by `50c441c`; per-chat SQLite state, drafts, terminal output, and canvas. Reboot persistence needs persistent storage | [History validation](HISTORY_VALIDATION.md) |
| F-010 | Put the terminal at bottom right and reserve the main right area for a visual canvas | Committed by `50c441c`; shared concept canvas and resizable panes | [Canvas validation](CANVAS_VALIDATION.md) |
| F-011 | Collapse the terminal by default to give the canvas room | Committed by `50c441c`; expands for command execution/proposals | [Canvas validation](CANVAS_VALIDATION.md) |
| F-012 | Represent NORA with an emerald that subtly pulses while processing/responding | Committed by `50c441c`; activity-driven vector presence and reduced-motion setting. Audio-driven states are part of F-021 | [Emerald validation](EMERALD_VALIDATION.md) |
| F-013 | Add expressions, including the website's smile | Committed by `50c441c`; expressions for readiness, processing, replies, and actions | [Expressions validation](EMERALD_VALIDATION.md#expressions-update) |
| F-014 | Communicate visually using nodes, links, shapes, movement, and web images; quiet icon editing controls | Committed by `50c441c`; connected diagrams, source-backed images, animation, and icon controls. Canvas shows explanations, not private model reasoning | [Visual canvas validation](CANVAS_VALIDATION.md#visual-explanations-links-movement-and-images) |
| F-015 | Match the website's slicker style, smaller fonts, and green palette | Committed by `50c441c`; bundled DM Sans/Space Grotesk, mint/forest palette, dotted canvas | [Style validation](STYLE_VALIDATION.md) |
| F-016 | Research Raspberry Pi 3/4/5 support, especially Pi 5 | Researched; current amd64 ISO does not boot on Pi. Separate ARM firmware/kernel/image/runtime work and board testing remain | [Hardware status](README.md#current-status-and-supported-hardware) |
| F-017 | Research fully local listening and speaking; voice off by default | Researched, followed by implementation request F-021. Moonshine/Kokoro selected; Piper discussed as a lighter future option | [Voice guide](VOICE.md) |
| F-018 | Explain NORA better in the README with website links and emerald logo | Committed: `715f4f7`; clearer product explanation, website links, and the supplied logo | [README](README.md) |
| F-019 | Play the supplied MP3 when chat starts | Committed: `715f4f7`; plays once and stops at window close. Local voice work also stops it when enabling voice | [Chat guide](CHAT.md), TFL-003 in [test log](TEST_FEEDBACK_LOOPS.md) |
| F-020 | Treat “show me an idea” as a canvas request; allow frequent visual responses, moving/replacing/clearing visuals | Committed: `715f4f7`; direct example sketch, stronger model guidance, canvas gestures, and generated-card reclamation. Model use of diagrams is not guaranteed on every reply | [Canvas interaction guide](CHAT.md#using-the-canvas-in-conversation), TFL-004 in [test log](TEST_FEEDBACK_LOOPS.md) |
| F-021 | Implement local listening and speech, toggle controls, audio settings, emerald feedback, and the discussed privacy behavior | Committed with this log revision: Moonshine Small Streaming English + Kokoro INT8, Heart/Bella voices, default-off worker, turn-taking, device controls, transcript/command review, offline packaging and CI checks. No full-duplex interruption or Piper fallback implemented | [Voice guide](VOICE.md), [voice validation](VOICE_VALIDATION.md), TFL-005/006 in [test log](TEST_FEEDBACK_LOOPS.md) |
| F-022 | Keep regression commands, passes, failures, fixes, and outstanding validation in one file | Committed with this log revision: this request created `TEST_FEEDBACK_LOOPS.md` and seeded it with evidenced historical outcomes | [Test feedback loops](TEST_FEEDBACK_LOOPS.md) |
| F-023 | Keep a history of requested features | Committed with this log revision: this request created this feature log | This document |

The repeated commit/push and VM-start requests are delivery operations,
not new product capabilities; relevant milestones are recorded below.

## Delivery milestones

These are historical source-control milestones. No current GitHub workflow or
release status was queried while initializing this log.

| Commit | Recorded delivery |
| --- | --- |
| `fa2952f` | Initial Debian 13 project |
| `fc8f043` | Autostarting offline chat |
| `71fb13d` | OS access and ISO release pipeline |
| `a7ff8b5` | Streaming/command cancellation race corrections |
| `50c441c` | Visual workspace, persistent history, web images, emerald, and styling; pushed to main |
| `715f4f7` | Canvas interaction improvements, README, and startup music; pushed to main |
| This revision, following `715f4f7` | Local voice implementation and regression/feature logs committed together; ISO release and VM deployment still pending |

The earlier browser noVNC connection was confirmed working by the user. That is
historical VM-access evidence, not confirmation that a VM is currently running
or that microphone forwarding exists.

## Updating this log

For each new request, append a stable feature ID, preserve its original intent,
and record the implementation commit, relevant test-loop IDs, and deployment
state when known. Update the status as work progresses; retain meaningful scope
changes and limitations. Research is not implementation, and a push is not a
successful release.

```markdown
| F-NNN | User request and intended behavior | State; source commit or local changes; limits | Guide and TFL IDs |
```

## Local testing milestone — 2026-09-16

User requested restarting NORA with more RAM and cores. Started the latest local
workspace (source `0efeed2`) in an 8 GiB / 6-vCPU QEMU guest, backed by Colima with
16 GiB / 8 CPUs. Verified the maximized workspace and offline-model-ready status
through a fresh screenshot; opened the noVNC viewer. See **TFL-008**. Voice stays
off by default; this browser connection does not forward physical audio. This
local development remaster is distinct from the GitHub release build.

## Audio-capable Mac VM setup — 2026-09-16

User requested configuring the proposed UTM setup. Installed UTM 4.7.5 and
prepared `dist/NORA Linux.utm` with 8 GiB / 6 CPUs and Intel HDA duplex audio.
UTM was opened; automated start is blocked by macOS automation permission
(error -1743). Physical audio and UTM guest boot remain unverified. See TFL-009.

### UTM playback verification

Following the import fix, the user confirmed startup music plays successfully
in the UTM session (**TFL-011**). Speaker playback is now user-verified;
microphone input and synthesized voice replies remain unverified.

## Chat performance tuning — 2026-09-16

User authorized context/thread tuning and native Mac inference for development.
Reduced system prompt size, skipped OS snapshots for simple greetings, enabled
prompt caching, and added an opt-in host endpoint while retaining the ISO's
built-in offline default. Benchmarked two/four native CPU threads and Metal;
started the same model with Metal on Mac loopback. Paused the older browser VM.
User confirmed **Host model ready** in the updated UTM workspace. All 107 Linux
regressions pass; see TFL-012 and CHAT.md. Changes are local and not yet committed.

## Voice-on startup default — 2026-09-16

User requested voice be enabled by default, superseding the original off-by-default
requirement. Implemented automatic activation after startup music completes (or
immediately if unavailable), while retaining manual off/pause and error fallback.
Chat changes and Settings cancel pending activation. Updated README, voice guide,
and model capability description. All 110 Linux tests pass; see TFL-013.
Running-VM update is staged and awaiting user application/verification.

## Clear speech playback — 2026-09-16

Investigated missing/garbled replies using a guest diagnostic. Confirmed repeated
PortAudio underruns; user heard the same waveform clearly through GStreamer.
Changed default speaker playback to that buffered path, retained explicit device
support, and kept voice errors visible. 113 Linux tests and real model/worker
integration pass. Fix staged for the running guest; see TFL-014/TFL-015. Emulated
speech generation is still slow and is not accelerated by the Mac chat model.

## Preloaded speech with microphone off — 2026-09-16

User revised voice startup: preload speech into memory, speak chat replies, and
keep the microphone off by default. Implemented independent Voice/Mic controls,
background prepare command, retained speech model across replies/chat changes,
and Stop speech without unloading. Listening requires explicit Mic on. Full Linux
suite (115 tests) and real-worker preload/audio lifecycle checks pass. See TFL-016.
Live-guest update staged; generation under emulation remains slow.

## Commit scope following 0efeed2

Chat context tuning and optional native Mac chat inference, GStreamer default
speech playback, persistent error display, speech preloading and separate
microphone opt-in, regression tests, CI test dependencies, and operational logs
are included together. User confirms mic-off behavior; speech-generation latency
under emulation remains unresolved. Native Mac speech synthesis is not included.
Final pre-commit regression: TFL-017, 115 tests passed.
