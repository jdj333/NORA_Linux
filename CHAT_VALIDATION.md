# NORA Terminal prototype validation

Validated on 2026-09-16. This record covers the new chat-enabled image;
[VALIDATION.md](VALIDATION.md) records the earlier desktop-only prototype.

Artifact: `dist/nora-linux-13-chat-amd64.hybrid.iso` (2,950,234,112 bytes).

SHA-256:

```text
526396cab8998a79993ef086f9f029d27f88d632fb52f5e7198d23b3493fcec7
```

Passed:

- The official llama.cpp CPU archive, Qwen model, and model license matched their
  pinned SHA-256 hashes. Licenses and provenance are included in `/opt/nora/llm`.
- The updated filesystem includes GTK/Python dependencies, the offline model,
  enabled `nora-llm.service`, and Xfce autostart for NORA Terminal.
- The assembled ISO has BIOS and UEFI boot records and the required live payload.
- A fresh extraction of the final ISO passed all 788 entries in each of its
  SHA-256 and MD5 manifests. The workspace ISO matched the external checksum.
- A fresh BIOS boot of this exact image reached the NORA desktop and opened
  NORA Terminal automatically, without a manual application launch.
- The model became ready automatically. The application streamed a complete
  reply to “Hello NORA. Introduce yourself in one short sentence.”
- The guest network was disconnected with QMP `set_link` before booting the live
  system and remained disconnected through the conversation and cancellation test.
  The model therefore loaded and generated its reply offline, inside NORA.
- Escape stopped a second request; the window reported that the interrupted
  exchange was excluded from context and returned to its ready state.
- `/clear` was used to reset the test conversation for handoff. Guest networking
  was re-enabled afterward.
- Eight transport tests passed: streaming/request contract, HTTP failure,
  truncated and malformed streams, cancellation before a request and during a
  blocked stream, context pruning, and UTF-8 input limits. Source syntax checks passed.

Test environment: QEMU TCG amd64 emulation on the ARM64 Docker VM, CPU `max`,
2 guest CPUs, 1,280 MiB guest RAM, and noVNC browser access. Generation was slow
under emulation; the small model is a functional starting point, not a quality or
performance benchmark. Prefer at least 2 GB guest RAM for ongoing testing.

The image was incrementally assembled from the previously verified desktop ISO
and retained root filesystem. The source includes the same application, assets
preparation step, service, and hooks for subsequent full live-build runs; a new
full package build from that source has not been run.

Evidence in `dist/`: `SHA256SUMS.chat`, `chat-iso-structure.txt`,
`chat-internal-sha256.log`, `chat-internal-md5.log`, `chat-finalize.log`,
`chat-repack.log`, `chat-build-packages.txt`, `chat-startup.png`,
`chat-offline-reply.png`, and `chat-stop.png`.

Not yet validated for this image: a new UEFI desktop boot, Secure Boot, disk
installation, installed-system upgrades, or physical hardware. Voice input/output
and command execution are not implemented. The earlier image's UEFI result does
not substitute for a fresh UEFI boot of this artifact.
