# Emerald presence validation

Validated on 2026-09-16 against source and the running NORA live guest.

- All 58 non-GUI tests passed on the host. New checks cover static idle/reduced
  motion, the slow thinking pulse, text-chunk accent decay, bounded intensity,
  and the animation preference surviving reopening and history deletion.
- All 19 GTK tests passed inside NORA (29.219 seconds). New checks cover the real
  busy/chunk/Stop/completion callbacks, accessible state labels, rejected late
  chunks, saved motion settings, system reduced-motion preference, pausing and
  timer cleanup, and different Cairo output for low/high glow levels. Existing
  chat, command, canvas, and history tests still pass.
- The host discovers 77 tests and skips 19 GTK tests because it lacks GTK/display;
  the guest runs them using temporary history databases.
- Cairo and its PyGObject bridge were already available in the guest. Both are
  now explicit ISO and CI dependencies. Python syntax, Git whitespace, and Actions
  workflow checks passed.

Evidence: `.build/chat/emerald-tests.log`, `dist/emerald-tests.png`, and guest log
`/tmp/nora-emerald-tests.log` (local test artifacts).

Visually checked the maximized live application at 1280×800: the emerald sits
above the conversation, the canvas retains the right side, and the command
terminal stays collapsed. A real `Hello Nora` model request displayed Thinking;
Escape stopped the request and restored Ready. Captures:
`dist/emerald-ready.png`, `dist/emerald-thinking-a.png`,
`dist/emerald-thinking-b.png`, and `dist/emerald-stopped.png`.
Streaming reply accents were verified through GTK callbacks and envelope tests;
the live model request was cancelled before its first reply chunk.

This adds an original vector rendition of NORA's emerald/terminal-mark identity
and activity visualization. It does not add microphone input, synthesized speech,
or self-listening. Reply accents currently follow text chunks; future speech must
use actual output-audio levels to claim audio synchronization.

The source and live application's temporary overlay were updated. Existing ISOs
and published releases were not rebuilt. The model, prompts, and command
authorization behavior remain unchanged by the presence widget.

## Expressions update

The emerald now retains its chevron while the cursor becomes the website-inspired
smile. Ready uses a curved smile; thinking/reading use a curious tilt; replies use
a small open smile driven by the existing intensity; command/loading/stopping use
a straight cursor. Reduced motion keeps the mouth static for each activity.
The three envelope tests passed on the host, and all four existing emerald GTK
checks passed in the live guest (11.535 seconds). Python syntax and whitespace
checks passed. The update changes the renderer and accessible expression names;
it adds no new model requests or animation timers.
All four mouth shapes were visually checked in a temporary GTK preview
(`dist/expressions-preview.png`); the check output is captured in
`dist/expressions-checks.png` and stored in guest `/tmp/nora-expression-tests.log`.
