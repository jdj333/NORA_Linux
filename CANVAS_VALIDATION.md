# Shared canvas validation

Validated on 2026-09-16 against source and the running NORA live guest.

- All 54 non-GUI tests passed on the host. Four new canvas tests cover visible
  excerpt classification, shell-block exclusion, grouping and non-overlap,
  persisted-state validation, and the 1,000-byte model-context bound.
- All 15 GTK tests passed inside NORA (16.656 seconds), including three new canvas
  checks: automatic cards and the Follow chat toggle, manual edits and positions
  across chat switches/reopening, clearing the board with all history, arranging
  and removing cards, and rejecting delayed edits after a chat switch. Existing
  command, cancellation, history, and storage-error tests still pass.
- The host discovers 69 tests and skips 15 GTK checks because it lacks GTK/display;
  the guest runs those checks with isolated temporary history databases.
- Visually verified the maximized layout at 1280×800: chat sidebar on the far left,
  conversation beside it, canvas above the compact terminal on the right.
- A real `/uptime` conversation created a question card and a sourced measurement
  card. Dragged the measurement card with the mouse. Created a “Shared workspace”
  note through Add card, and executed `whoami` in the lower-right terminal with
  Exit 0 and a separate command-result card.
- Closed and reopened the application: the dragged card position, manual note,
  command-result card, and terminal transcript returned. Used the visible Edit,
  Remove, and Arrange buttons successfully; the remaining notes grouped into a
  grid without losing their source labels or crashing GTK.
- Python syntax, Git whitespace, and Actions workflow checks passed.
- Subsequent default-collapse change: relaunched the live application and verified
  that only the terminal toggle is visible, allowing the canvas to fill the right
  workspace. Expanded and collapsed it with the mouse; retained command output
  and controls returned. Evidence: `dist/terminal-collapsed.png` and
  `dist/terminal-expanded.png`. Syntax and whitespace checks passed for this
  small UI change; the test totals above describe the preceding canvas version.

Local evidence (ignored artifacts): `.build/chat/canvas-tests.log`,
`dist/canvas-tests.png`, `dist/canvas-startup.png`, `dist/canvas-cards.png`,
`dist/canvas-dragged.png`, `dist/canvas-add-dialog.png`, and
`dist/canvas-command.png`, `dist/canvas-reopened.png`, `dist/canvas-edited.png`,
and `dist/canvas-final.png`. Guest GTK log: `/tmp/nora-canvas-tests.log`.

The source and live application's temporary overlay were updated. Existing ISOs
and the published release are unchanged. Card persistence across a full live-VM
shutdown requires persistent storage; app reopening and per-chat storage are
tested. No new full model-generated response was required for these UI checks;
model completion integration is exercised with controlled responses.

The board collects excerpts from visible conversation using deterministic rules.
It is a shared whiteboard, not a view of hidden model reasoning. Cards are bounded
to 60 per chat, can be edited by the user, and never execute commands. Only a
bounded recent subset of notes is sent back to the local model. Model excerpts
and website excerpts are not automatically promoted to verified facts.

## Visual explanations, links, movement, and images

Updated on 2026-09-16:

- 66 non-GUI tests passed on the host; the 88-test discovery skips 22 GTK tests.
  New checks cover directed branch maps, decision nodes, cycles, source image
  discovery, Commons credits, size limits, public-address checks, redirects, and
  cancelled image requests. Log: `.build/chat/visual-canvas-tests.log`.
- All 22 GTK tests passed inside NORA after the layout refinements (23.671 s).
  They cover link persistence/removal, moved nodes, thumbnail persistence without
  a refetch, rejection of image results from an old chat, image URL allowlisting,
  reduced-motion layout, and existing command/chat/history behavior. Guest log:
  `/tmp/nora-visual-tests.log`.
- A temporary preview used an isolated history database and a controlled reply
  (`Idea -> Ready? -> Action`). The live renderer showed capsules, a decision
  diamond, directed connections, compact icon controls, and a PNG fetched from
  python.org. Screenshot: `dist/visual-final-preview.png`. This checks the reply
  integration and real image fetching; it is not a model-generated-answer test.
- A live Commons search for emerald crystals returned two sourced image results.
  The first result was a ship with a matching name, illustrating why search
  relevance and the image's actual subject must not be assumed.

The model is prompted to format processes as short arrow lines and concepts as
labeled bullets. Other replies fall back to connected excerpts. The current
text-only model does not inspect the pixels of fetched images. Existing chats
remain compatible and reopening cached image nodes does not download again.
Only the source and temporary live application overlay were updated; no ISO or
release was rebuilt.

Implementation references: [GTK Layout](https://docs.gtk.org/gtk3/class.Layout.html),
[GdkPixbuf loader](https://docs.gtk.org/gdk-pixbuf/class.PixbufLoader.html),
[MediaWiki search](https://www.mediawiki.org/wiki/API:Search), and
[image metadata](https://www.mediawiki.org/wiki/API:Imageinfo).
