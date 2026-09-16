# NORA Terminal

NORA Terminal is a desktop chat application styled like an emerald-and-dark
terminal. It opens automatically at Xfce login and is also available from the
Applications menu. Type a message and press Enter; Shift+Enter adds a line.
Replies stream into the transcript. Stop or Escape cancels a reply. New chat
clears the conversation. `/help`, `/model`, and `/clear` are local shortcuts.
See [OS_ACCESS_VALIDATION.md](OS_ACCESS_VALIDATION.md) for the tested ISO and its evidence.

NORA speaks as the operating system and can inspect its running Linux environment
and execute commands. It supports typed interaction; voice input/output is not
implemented. The small local model can still make factual and command-syntax mistakes.

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
block. A single such block appears in an editable **Proposed command** area.
Choose **Run command** to execute it. Model output alone never executes a command.
Requests such as “list files”, “what processes are running”, and “what is your IP
address” select fixed inspection commands directly.

Commands run through Bash as the logged-in Linux user, with stdout/stderr streamed
into the chat and the actual exit code shown. There is no automatic privilege
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
only for model context, while the chat shows output up to the command limit.

## Offline model

- Runtime: llama.cpp v0.4.1 / build b10964, official Linux amd64 CPU binaries.
- Model: Qwen2.5-0.5B-Instruct Q4_K_M (491,400,032 bytes).
- Context: 4,096 tokens, one request at a time, replies capped at 256 tokens.
- The client limits each prompt to 1,600 UTF-8 bytes and trims the oldest complete
  exchanges to keep recent conversation within a conservative 2,400-byte budget.
- Model service: `nora-llm.service`, listening only on `127.0.0.1:8088` inside NORA.
  GPU offload, remote model downloads, the server web UI, and agent tools are disabled.
- App history is held in memory, not saved by the app. Closing the window or choosing
  New chat clears the history and last command result, but does not undo command
  effects. Command output can reach the local model on a subsequent question.
  Stopped model replies are excluded from history; real command failures and
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
| `config/includes.chroot/usr/local/bin/nora-llm` | CPU inference settings |
| `config/includes.chroot/etc/systemd/system/nora-llm.service` | Model startup with an unprivileged service identity |
| `config/includes.chroot/etc/xdg/autostart/nora-terminal.desktop` | Open the chat window at login |
| `tests/test_chat_client.py` | Streaming, cancellation, errors, and Unicode context limits |
| `tests/test_os_access.py` | System facts, actual command effects, process cleanup, and proposal boundaries |

Tests: `python3 -m unittest discover -s tests -v`. They use a temporary localhost
HTTP server and temporary directories for command tests; no external model or network service is required. A real ISO boot
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
