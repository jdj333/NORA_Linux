# NORA Terminal

NORA Terminal is a desktop chat application styled like an emerald-and-dark
terminal. It opens automatically at Xfce login and is also available from the
Applications menu. It opens maximized, with desktop panels and window controls
visible; use the window's restore button to resize it. Type a message and press
Enter; Shift+Enter adds a line.
The bundled `music/NoraLinuxStartupSong.mp3` plays once when the application
opens a new window, including at login. It does not loop or replay when switching
chats or bringing an existing window forward. Closing the window stops playback;
audio-device or decoder failures leave chat available. Playback uses the desktop's
default audio output and volume and does not open the microphone.
Conversation and website results appear on the left. A shared concept canvas
occupies the upper right, with a compact command terminal underneath. The terminal
starts collapsed to give the canvas more room. Click **Terminal · Show commands**
to expand it or **Hide commands** to collapse it. Running a command or preparing a
model-proposed command expands it automatically. Its output and draft remain when
collapsed. The terminal
shows commands, streamed output, and exit status. Drag either divider to resize
the conversation, canvas, or terminal. Type a command below the canvas and press Enter or choose **Run command**;
Shift+Enter adds a line. Each pane has its own Stop button for its active operation.
One operation runs at a time; you can draft in either input while it runs.
New chat saves the current chat and opens a fresh conversation and terminal.
Select a chat in the left sidebar to resume it. **Clear output** clears only the
current chat's terminal display.
`/help`, `/model`, and `/clear` are local chat shortcuts.
See [OS_ACCESS_VALIDATION.md](OS_ACCESS_VALIDATION.md) for the tested ISO and its evidence.
See [SPLIT_PANE_VALIDATION.md](SPLIT_PANE_VALIDATION.md) for the newer live application checks.

NORA speaks as the operating system and can inspect its running Linux environment
and execute commands. It supports typed interaction and optional local voice. Voice starts off;
see [VOICE.md](VOICE.md) for listening, speaking, audio devices, and privacy. The small local model can still make factual and command-syntax mistakes.

## NORA's emerald presence

The workspace matches the website's typography and palette: bundled DM Sans for
13 px conversation text, Space Grotesk for headings, and 12 px monospace for the
command terminal. Mint `#a0f3c0`, forest canvas `#0b130f`, and node surface
`#15231a` come from the website stylesheet. Fonts are available offline, with
their licenses and pinned source checksums in `usr/share/fonts/truetype/nora`.
The dotted canvas, thin dividers, and compact emerald header leave more room for
the conversation and diagrams. UI colors live together in `style.py`.

A faceted emerald with NORA's `>` mark and an expressive cursor stays above the conversation. It represents
the same operating-system identity as the logo and responds to real application
activity:

| State | Emerald behavior |
| --- | --- |
| Ready | Friendly curved smile, steady quiet glow |
| Model starting | Relaxed straight cursor, dimmer still emerald |
| Thinking | Curious tilted mouth, slow 3.6-second light pulse while awaiting model text |
| Replying | Small open smile and brighter accents following received reply chunks |
| Reading / running commands | Curious / focused expression, gentle pulse and corresponding label |
| Stopping | Resting straight cursor until cancellation completes |

The smile follows the website's emerald persona: the chevron stays recognizable
and the cursor becomes a mouth. Expressions reflect application activity; they
do not infer emotions from conversation content. With animation disabled, each
activity keeps a still expression.

Instant system answers get one brief response pulse. The glow is subtle and the
gem changes scale by less than 2%; the canvas remains the main visual workspace.
Status text and an accessible name accompany the animation. **Settings → Animate
NORA and the canvas** disables motion while retaining state labels. This preference is
saved locally and is kept when chat history is cleared. The system GTK animation
preference is also respected. Timers stop at idle, on minimize/unmap, and on close.

When Voice is enabled, listening and speaking have distinct emerald states.
Their glow follows microphone and playback levels respectively. NORA does not
record her own output to animate the emerald. Reduced motion keeps these states
still while preserving their labels. Text-only chat retains its reply animation.
See [VOICE.md](VOICE.md) for the offline engines, controls, and validation limits.

## Using the canvas in conversation

“Visually show me an idea” immediately sketches a concrete example with connected
nodes, even while the language model is loading. For a specific topic, ask for a
diagram, explanation, comparison, or plan; the model is encouraged to include
short maps and concept bullets in ordinary replies too.

NORA can include `Canvas: replace`, `Canvas: arrange`, or `Canvas: clear` on its
own line in a reply. These gestures replace her previous explanation, rearrange
the board, or clear it. They only affect the canvas and never execute commands.
Replacing an explanation preserves manually added or edited notes. When the board
fills, older generated nodes make room for new visuals. **Follow chat** pauses
automatic canvas changes when unchecked. Say “Clear the canvas” or “Arrange the
canvas” to act on the board directly, without deleting conversation history.

The small model can still miss a requested diagram; the prompt guidance does not
guarantee every generated response will use the canvas.

## Saved chats and settings

Chats are titled from their first question or command and saved automatically on
this computer. The left sidebar restores each chat's conversation, terminal output,
drafts, canvas cards and positions, working directory, recent model context, and last website and command
results. Restoring a chat never executes its commands. Closing and reopening NORA
returns to the last active chat. Finish or stop the current operation before
switching chats or clearing history.

Choose **Settings → Clear all history and contexts… → Clear all** to delete all
saved conversations, canvas cards, terminal transcripts, drafts, website excerpts, and command
context. This starts one empty chat. Cancel leaves everything intact. Deleting
history does not undo commands or remove files they created.

Storage is `$XDG_STATE_HOME/nora/chats.sqlite3`, normally
`~/.local/state/nora/chats.sqlite3`, in a user-only directory with a user-only
database file. History is local and unencrypted. Saves occur within approximately
one second of changes and synchronously on chat switching and normal close;
an abrupt crash can lose the newest unsaved text. Storage errors appear below the
chat list. Full transcripts are retained, but model prompts still use the bounded
recent context described below. Saved website and command results retain their
original observation times; they are not refreshed merely by reopening a chat.

On an installed system or a persistent home directory, chats survive reboots.
The current live ISO/VM uses temporary storage, so its chats survive application
restarts but disappear when the live session shuts down. See
[HISTORY_VALIDATION.md](HISTORY_VALIDATION.md) for validation details.

## Visual conversation canvas

NORA explains in chat and on the canvas. With **Follow chat** enabled, a completed
reply builds an explanation map from its visible text:

- Short arrow lines such as `Sunlight -> Leaves -> Growth` become directed links.
  Repeated names join branches; names ending in `?` become decision diamonds.
- Numbered steps form a sequence. Concept bullets (`Name: explanation`) form
  branches around the question. Ordinary prose falls back to connected excerpts.
- Nodes use rounded cards, capsules, or diamonds. Drag their headers (or use arrow
  keys while focused); connections follow. **Arrange** places linked nodes in
  layers and gently moves them into position. New maps fade into view.
- Small pencil and trash icons replace the Edit/Remove buttons. They brighten on
  hover or keyboard focus, have tooltips and accessible names, and remain usable
  without a pointer. Editing also lets you choose the node shape.
- **Settings → Animate NORA and the canvas** disables motion in both areas. The
  GTK animation preference also applies. Movement finishes within 450 ms, with
  no continuous canvas animation timer.

The small local model is prompted to use these visual formats; when it does not,
the excerpt fallback still provides a map. This is a high-level explanation of
concepts and relationships, not a display of private model reasoning. Nodes and
links are communication aids, not independently verified facts. Shell blocks
are excluded and canvas content never executes commands.

### Images when online

Use **“Show images of emerald crystals”** or `/images emerald crystals` to search
Wikimedia Commons. NORA places up to two thumbnails on the canvas with file-page
sources, artist credits, and license metadata. Search relevance comes from
Commons; a result is not confirmation of what an image depicts.

`/web URL` also discovers up to two images on the page and adds them with their
source. `/image https://example.org/picture.png` displays a specific public image
and can retry an earlier failed image. The model may select Markdown images from
URLs discovered on the last fetched page; invented URLs are not downloaded.
The current local model is text-only and uses captions/page text, not image vision.

PNG, JPEG, and supported WebP images are fetched without credentials or cookies,
with public-address checks on each redirect, a 3 MiB limit, 20-second timeout,
and bounded dimensions. SVG and executable content are not loaded. A failed or
offline image leaves an unavailable placeholder with the reason in its tooltip.
Two image workers run at most; removing a node, switching chats, clearing history,
or closing the window cancels relevant work. Image search words are sent to
Commons, and image requests go to their source sites.

Nodes, links, positions, and downloaded thumbnails are saved with each chat.
Reopening history uses saved thumbnails without downloading them again; clearing
all history removes those thumbnails too. Existing card-only chats remain valid.
The limits are 60 nodes and 120 links per chat, with 80-character titles and
1,200-character bodies. Up to four recent text nodes fit into the model's
1,000-byte canvas-context budget. Images do not consume model image tokens.
See [CANVAS_VALIDATION.md](CANVAS_VALIDATION.md) for validation evidence.

## System questions and commands

Ask **“How much disk space do you have?”**, **“How much RAM do you have?”**, or
**“Who are you?”**. NORA reads current Linux data and answers directly, with its
measurement sources and timestamp. These questions work even while the LLM is
loading. In a live session, storage refers to the temporary writable overlay;
it is not the Mac's physical disk capacity. Root and home may share one filesystem.

| Input | Behavior |
| --- | --- |
| `/system` | Current OS, kernel, CPU, RAM, filesystem space, and uptime |
| `/disk`, `/memory`, `/cpu`, `/uptime` | A fresh measurement of that resource |
| `/files`, `/network`, `/processes` | Run a fixed read-only inspection command |
| `/run df -h /` | Execute the exact supplied shell command immediately |
| `/run cat /etc/os-release` | Read a file through the current user's permissions |
| `/cd /home/nora` | Change the working directory for subsequent commands |
| `/pwd` | Show the command working directory |

For other action requests, the model can propose a command in a fenced shell
block. A single such block appears in the editable terminal input on the right.
An existing terminal draft is preserved; in that case, copy the suggested command
from the conversation when ready.
Choose **Run command** to execute it. Model output alone never executes a command.
Requests such as “list files”, “what processes are running”, and “what is your IP
address” select fixed inspection commands directly.

Commands run through Bash as the logged-in Linux user, with stdout/stderr streamed
into the right terminal pane and the actual exit code shown. Chat `/run` requests
and fixed inspection commands also send their output there. There is no automatic privilege
elevation; explicit commands such as `sudo` retain the operating system's usual
permission behavior. Each command gets a fresh, noninteractive shell. Use `/cd`
to persist the working directory across commands; shell variables and `cd` inside
`/run` do not persist. `/cd` takes a plain path (spaces are allowed), expands `~`,
and does not evaluate shell expressions.

Stop/Escape terminates the foreground command group. Each command is limited to
60 seconds and 32 KiB of output; output or time limits terminate the command group
and are reported explicitly. Interactive programs/password prompts belong in a
regular terminal. This is not a sandbox: commands can modify files or use the
network, and programs that deliberately detach from the process group are outside
its cancellation guarantee. Clearing chat or cancelling a command does not undo
changes already made.

General model questions receive a compact, freshly collected OS snapshot and the
most recent command result with bounded output. Tool output is treated as data,
not instructions; it is never automatically executed. Large results are shortened
only for model context, while the terminal shows output up to the command limit.

## Reading websites

See [WEB_ACCESS_VALIDATION.md](WEB_ACCESS_VALIDATION.md) for the live-guest checks.

Type **“Look up noralinux.com”**, paste a website address, or use
`/web https://noralinux.com`. NORA fetches the page, extracts readable text, and
shows the title, final source URL, read time, and links. This works while the local
model is loading. Ask **“Summarize the page”** or a follow-up question afterward;
the local model receives a bounded excerpt from the most recently read page.
Follow a listed link with another `/web URL`. Each chat keeps its own fetched page;
a new chat begins without website context.

Website requests require internet access (or reachability for a local website).
Only the requested URL is sent to the website; chat history, system facts, and
command results stay with the local model. The reader does not use browser cookies
or login sessions and does not execute JavaScript. HTML and plain text, redirects,
and gzip responses are supported. Login-only pages, browser challenges, JavaScript
apps, and PDFs may require Firefox. This is a URL reader, not a general search engine.

Stop/Escape cancels a read, including stalled DNS or body transfers. Reads have a
30-second overall deadline, 10-second socket timeout, 2 MiB download/decompression
limits, and 16,000 characters of retained text. The transcript displays up to 6,000
characters and marks excerpts. The model gets up to 1,800 UTF-8 bytes selected for
the question, so it may not see every detail of a long page. Read times describe
when NORA fetched a page, not its publication date. Failed reads are reported
directly and do not provide stale page context to the model. Retrieved text is
untrusted source material and never automatically runs commands.

## Offline model

- Runtime: llama.cpp v0.4.1 / build b10964, official Linux amd64 CPU binaries.
- Model: Qwen2.5-0.5B-Instruct Q4_K_M (491,400,032 bytes).
- Context: 4,096 tokens, one request at a time, replies capped at 256 tokens.
- The client limits each prompt to 1,600 UTF-8 bytes and trims the oldest complete
  exchanges to keep recent conversation within a conservative 2,400-byte budget.
- Model service: `nora-llm.service`, listening only on `127.0.0.1:8088` inside NORA.
  GPU offload, remote model downloads, the server web UI, and agent tools are disabled.
- Chat transcripts and recent context are saved locally and restored per chat.
  Command output can reach the local model on a subsequent question in that chat.
  Stopped model replies are excluded from model context; real command failures and
  interruption status remain available as evidence.

The model is deliberately small for the first emulated VM. Allow at least 2 GB
guest RAM for comfortable testing; 4 GB gives more room for other applications.
CPU emulation on an ARM Mac is substantially slower than a native amd64 machine.
The first reply may pause while model pages are loaded from the live ISO.

## Build and source

Run `python3 scripts/prepare-llm.py` before the normal build. It verifies pinned
SHA-256 hashes, stages the model/runtime, and includes upstream licenses and a
provenance manifest in `/opt/nora/llm`. Nothing is fetched during first login.
The generated overlay is ignored by Git; another checkout recreates it using the
same preparation command. This requires Python 3.12+ and internet at build time.

| File | Purpose |
| --- | --- |
| `scripts/prepare-llm.py` | Pinned downloads and runtime/model assembly |
| `config/includes.chroot/usr/share/nora/chat/app.py` | GTK3 desktop interface |
| `config/includes.chroot/usr/share/nora/chat/client.py` | Local HTTP streaming and context handling |
| `config/includes.chroot/usr/share/nora/chat/system_info.py` | Live Linux measurements and direct system answers |
| `config/includes.chroot/usr/share/nora/chat/commands.py` | User command execution, output limits, and cancellation |
| `config/includes.chroot/usr/share/nora/chat/web_access.py` | Cancellable HTTP(S) reads, HTML extraction, and bounded page context |
| `config/includes.chroot/usr/share/nora/chat/history_store.py` | Local transactional chat storage and clearing |
| `config/includes.chroot/usr/share/nora/chat/canvas.py` | Editable GTK whiteboard and card dragging |
| `config/includes.chroot/usr/share/nora/chat/canvas_model.py` | Excerpt extraction, categories, layout, validation, and context limits |
| `config/includes.chroot/usr/share/nora/chat/presence.py` | Vector emerald, state labels, activity animation, and lifecycle cleanup |
| `config/includes.chroot/usr/share/nora/chat/presence_model.py` | Bounded glow and text-chunk response envelope |
| `config/includes.chroot/usr/local/bin/nora-llm` | CPU inference settings |
| `config/includes.chroot/etc/systemd/system/nora-llm.service` | Model startup with an unprivileged service identity |
| `config/includes.chroot/etc/xdg/autostart/nora-terminal.desktop` | Open the chat window at login |
| `tests/test_chat_client.py` | Streaming, cancellation, errors, and Unicode context limits |
| `tests/test_os_access.py` | System facts, actual command effects, process cleanup, and proposal boundaries |
| `tests/test_web_access.py` | Website routing, HTTP fixtures, limits, errors, cancellation, and source context |
| `tests/test_chat_window.py` | GTK pane routing, drafts, command proposals, execution, Stop, and clearing |
| `tests/test_history_store.py` | Persistence, active chat, permissions, deletion rollback, and invalid data |
| `tests/test_canvas_model.py` | Card extraction, grouping, position bounds, and model context |
| `tests/test_presence_model.py` | Idle stability, slow pulses, reply decay, and reduced motion |

Tests: `python3 -m unittest discover -s tests -v`. They use a temporary localhost
HTTP server and temporary directories for command tests; no external model or network service is required.
GUI tests require GTK3 and a display. On Debian/Ubuntu, install `python3-gi
python3-cairo python3-gi-cairo gir1.2-gtk-3.0 xvfb xauth`, then use
`xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -v`.
CI uses this command; hosts without GTK/display skip the GUI tests. A real ISO boot
and generated reply are also required to validate a release.

To disable automatic window opening for one user, use Xfce's **Session and Startup →
Application Autostart** settings and uncheck NORA Terminal. The model service can
be stopped separately with `sudo systemctl stop nora-llm`.

## Diagnostics inside NORA

```sh
systemctl status nora-llm
sudo journalctl -u nora-llm -b --no-pager
curl http://127.0.0.1:8088/health
sudo systemctl restart nora-llm
nora-terminal
```

A loading model returns HTTP 503; a ready model returns HTTP 200. The app keeps
checking readiness without blocking the desktop. If it remains unavailable, inspect
the service log rather than repeatedly launching more model processes.

Upstream references: [llama.cpp release](https://github.com/ggml-org/llama.cpp/releases/tag/b10964),
[server documentation](https://github.com/ggml-org/llama.cpp/tree/b10964/tools/server),
[Qwen model and license](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/9217f5db79a29953eb74d5343926648285ec7e67).
