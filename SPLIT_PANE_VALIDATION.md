# Conversation and terminal pane validation

Validated on 2026-09-16 against source and the running NORA live guest.

- All 45 non-GUI tests passed on the host. The seven GTK tests skip there because
  GTK/display support is unavailable; all seven passed separately inside NORA
  using its real GTK3 desktop (9.230 seconds).
- GUI checks exercised direct command execution and real file creation after Run,
  chat `/run` routing, preserving drafts in both inputs, proposal review without
  automatic execution, cancellation after output begins, nonzero exits, directory
  changes, and independent chat/terminal clearing.
- Restarted NORA Terminal with the updated application. Visually verified both
  panes, controls, and the dark emerald styling at the guest's 1280×800 resolution.
- Verified the subsequent maximized-by-default startup change in the live guest:
  the window fills the available desktop while retaining the Xfce panel and
  normal window controls. Evidence: `dist/chat-maximized.png`.
- Asked “How much disk space do you have” and received current guest measurements
  on the left. Sent `/run df -h /` from chat and saw output and Exit 0 on the right.
  Entered `whoami` directly on the right and received `nora`, also with Exit 0.
- Python syntax, Git whitespace, and Actions workflow checks passed. The workflow
  now installs GTK3 and Xvfb and uses system Python so GUI tests run in CI.

Local evidence (ignored build artifacts): `dist/panes-tests.png`,
`dist/panes-startup.png`, `dist/panes-commands.png`, and
`.build/chat/panes-tests.log`. The GUI test log is also in the live guest at
`/tmp/nora-panes-tests.log`.

This updates repository source and the guest's temporary application overlay.
It does not rebuild an ISO or change the published release. A future ISO build
includes these source files automatically. No new full model-generated reply was
needed for these UI checks; proposal handling used a controlled model response.

The right pane is a command console with streamed stdout/stderr, not an interactive
PTY. Password prompts and full-screen programs still require a regular terminal.
Operations remain serialized, with the existing 60-second and 32-KiB command
limits. New chat clears model context, including the last command evidence, while
preserving the terminal display, draft, and working directory.
