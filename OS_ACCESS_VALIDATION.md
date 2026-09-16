# NORA system terminal validation

Artifact assembled on 2026-09-16:
`dist/nora-linux-13-system-amd64.hybrid.iso` (3,168,141,312 bytes).

SHA-256:

```text
e3ba12572414ed31701a3234c5999ed5ff04f36f0ba9789d884b1b27d2c56677
```

This supersedes the conversation-only image recorded in
[CHAT_VALIDATION.md](CHAT_VALIDATION.md). Earlier images remain unchanged.

Passed automated and artifact checks:

- All 30 tests passed on macOS and Linux: transport, actual command file effects,
  stderr/exit codes and pipelines, closed stdin, bounded output, timeout and
  process-group cancellation, window-close races, directory handling, command
  proposal boundaries, measured system answers, and model context with real facts.
- Python source syntax and Git whitespace checks passed.
- Explicit procps and iproute2 dependencies were already installed in the retained
  filesystem (versions 2:4.0.4-9 and 6.15.0-1 respectively).
- BIOS and UEFI boot records and the live kernel/initramfs/filesystem are present.
- Fresh extraction passed all 788 entries in each internal SHA-256 and MD5 manifest.
  The delivered workspace copy matches the external SHA-256 above.

Passed from a fresh BIOS boot of this exact final image:

- Xfce opened NORA Terminal automatically; the offline model became ready without
  manually launching the app or service.
- The original disk-space question returned 579.6 MiB available of 607.8 MiB,
  identified the live overlay, and showed its sources and timestamp. `/run df -h /`
  independently reported the matching rounded values (608M total, 580M available).
- `/run printf nora-command-test > /tmp/nora-chat-command-test.txt` followed by
  `/run cat /tmp/nora-chat-command-test.txt` produced the expected content and exit 0.
- `/run false` reported exit 1. Escape cancelled `/run sleep 30`, reporting exit
  -15 and `stopped by you` after 8.6 seconds; the UI returned to ready state.
- The bundled model completed “Suggest one sh command to show disk usage.” with
  a fenced `df -h` proposal. The editable proposal and Run button appeared without
  executing it. Clicking Run produced filesystem output and exit 0 in 0.1 seconds.
  The model identified NORA Linux 13; its service log showed about 224 seconds to
  evaluate the first 256 prompt tokens under this emulation. Allow several minutes
  for model replies in this setup; direct system questions bypass inference.

Fresh-boot evidence: `system-startup.png`, `system-disk.png`,
`system-command.png`, `system-stop.png`, `system-proposal.png`,
`system-proposal-run.png`, and `system-model-log.png` in `dist/`.

The image was incrementally assembled from the retained chat filesystem, with
the updated application overlay owned by root. The kernel supports Zstd SquashFS;
this development repack uses Zstd level 6, one compressor CPU, and a 256 MiB
compressor memory limit. Internal manifests were regenerated and hybrid boot
records replayed from the earlier image. The bundled model, runtime, and service
are unchanged. A new full live-build package build has not been run.

Test environment: QEMU TCG amd64 emulation on the ARM64 Docker VM, CPU `max`,
two guest CPUs, 1,280 MiB guest RAM, and no attached host or installation disk.
The existing noVNC viewer publishes only on host loopback. Model inference under
emulation is slow; this is not a performance or model-quality benchmark.

Before final assembly, a live patch also demonstrated measured disk answers,
`df -h /`, and writing then reading `/tmp/nora-chat-command-test.txt` through the
chat window. Those screenshots (`os-access-startup.png`, `os-disk-answer.png`,
`os-command-test.png`) describe the patched earlier boot, not the final ISO.

Artifact evidence in `dist/`: `SHA256SUMS.system`, `system-iso-structure.txt`,
`system-internal-sha256.log`, `system-internal-md5.log`, `system-finalize.log`,
`system-repack.log`, and `os-access-tests.log`.

Commands execute with the logged-in user's permissions. `/run` executes explicit
user input; model proposals require Run. This is not a command sandbox or an
autonomous agent loop. Stop and limits terminate the command process group;
deliberately detached processes are outside that guarantee. Changes already made
are not undone by Stop or New chat. The small model can suggest incorrect commands.

Not validated for this image: a new UEFI desktop boot, Secure Boot, installation,
installed-system upgrades, physical hardware, or Raspberry Pi support. The image
is amd64. Voice input/output is not implemented.
