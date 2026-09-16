# NORA Terminal

NORA Terminal is a desktop chat application styled like an emerald-and-dark
terminal. It opens automatically at Xfce login and is also available from the
Applications menu. Type a message and press Enter; Shift+Enter adds a line.
Replies stream into the transcript. Stop or Escape cancels a reply. New chat
clears the conversation. `/help`, `/model`, and `/clear` are local shortcuts.
See [CHAT_VALIDATION.md](CHAT_VALIDATION.md) for the tested ISO and its evidence.

This version supports typed chat. It does not listen to the microphone, speak,
execute shell commands, inspect files, or access the internet. Model output is
rendered as plain text. The compact model can make factual and command-syntax
mistakes; it is a prototype assistant, not a system administration agent.

## Offline model

- Runtime: llama.cpp v0.4.1 / build b10964, official Linux amd64 CPU binaries.
- Model: Qwen2.5-0.5B-Instruct Q4_K_M (491,400,032 bytes).
- Context: 4,096 tokens, one request at a time, replies capped at 256 tokens.
- The client limits each prompt to 1,600 UTF-8 bytes and trims the oldest complete
  exchanges to keep recent conversation within a conservative 2,400-byte budget.
- Model service: `nora-llm.service`, listening only on `127.0.0.1:8088` inside NORA.
  GPU offload, remote model downloads, the server web UI, and agent tools are disabled.
- App history is held in memory, not saved to disk. Closing the window or choosing
  New chat clears it. Cancelled or failed exchanges are not added to model context.

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
| `config/includes.chroot/usr/local/bin/nora-llm` | CPU inference settings |
| `config/includes.chroot/etc/systemd/system/nora-llm.service` | Model startup with an unprivileged service identity |
| `config/includes.chroot/etc/xdg/autostart/nora-terminal.desktop` | Open the chat window at login |
| `tests/test_chat_client.py` | Streaming, cancellation, errors, and Unicode context limits |

Tests: `python3 -m unittest discover -s tests -v`. They use a temporary localhost
HTTP server; no external model or network service is required. A real ISO boot
and generated reply are also required to validate a release.

To disable automatic window opening for one user, use Xfce's **Session and Startup →
Application Autostart** settings and uncheck NORA Terminal. The model service can
be stopped separately with `sudo systemctl stop nora-llm`.

## Diagnostics inside NORA

```sh
systemctl status nora-llm
journalctl -u nora-llm -b --no-pager
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
