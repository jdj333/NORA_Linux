# Website-matched workspace style

The desktop style was matched to the public `https://noralinux.com/styles.css`
stylesheet and the user's workspace screenshot. The shared `style.py` palette
uses mint `#a0f3c0`, forest `#0b130f`, node fill `#15231a`, and muted borders.
Conversation text uses DM Sans at 13 px; headings use Space Grotesk; both command
views retain 12 px DejaVu Sans Mono. The emerald header is more compact and the
canvas has a clipped, viewport-sized dot grid.

Both fonts are bundled under their original SIL Open Font Licenses. Source
commit, download URLs, and SHA-256 hashes are recorded in
`config/includes.chroot/usr/share/fonts/truetype/nora/README.md`.

Validation:

- `fc-match` inside NORA selects DM-Sans.ttf and Space-Grotesk.ttf.
- All 22 existing GTK integration tests passed (26.454 seconds). No new tests
  were added for this visual-only change.
- The live style preview parsed the GTK CSS and rendered the conversation,
  decision flow, icon controls, dotted grid, and downloaded image at 1280×800.
- Python syntax and `git diff --check` passed.

Evidence: `dist/style-preview.png`, `dist/style-checks.png`, and guest
`/tmp/nora-style-tests.log`. The preview used a temporary history database;
the normal app was reopened with its saved chats. Its in-progress reply was
stopped during the normal close needed to reload fonts and style.

Source and the running VM's temporary overlay were updated. The ISO and published
release have not been rebuilt.
