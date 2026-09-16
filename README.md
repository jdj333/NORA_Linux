# NORA Linux

Debian 13 (Trixie) derivative with an Xfce desktop, emerald accents, dark GTK theme,
and the supplied `logo.png`. Tracks current Trixie, security, and point updates;
does not follow Debian testing or a future Debian major release.

Target: amd64 PCs, hybrid USB/DVD live ISO with BIOS and UEFI boot entries and
Debian's live installer. Secure Boot and physical hardware support require testing.
This is a prototype, not a validated release. The logo's tagline is branding;
no voice assistant is implemented.

NORA Terminal opens at login for typed conversations with a bundled, offline
Qwen2.5 0.5B model. No API key or internet is needed after boot. It explains
commands but does not execute them. See [CHAT.md](CHAT.md) for usage and limitations.

The first ISO and verification evidence are in `dist/`. See [VALIDATION.md](VALIDATION.md)
for the tested artifact, checksum, and remaining validation.
The chat-enabled ISO is `dist/nora-linux-13-chat-amd64.hybrid.iso`; see
[CHAT_VALIDATION.md](CHAT_VALIDATION.md) for its offline conversation and startup checks.
Read [LEARNING.md](LEARNING.md) before rebuilding for reusable commands and known gotchas.

## Build on Debian 13 amd64

Allow at least 25 GB free disk and 4 GB RAM. Package mirrors require internet access.

```sh
sudo apt-get update
sudo apt-get install live-build debootstrap ca-certificates xorriso isolinux \
  syslinux-common grub-pc-bin grub-efi-amd64-bin mtools dosfstools squashfs-tools \
  file rsync xz-utils zstd bzip2 python3
python3 scripts/prepare-llm.py
sudo ./scripts/build.sh
```

Use a fresh checkout/build directory for each release. To rebuild a used tree,
run `sudo lb clean --purge` before configuring again.

## Docker / macOS

The build needs privileged Linux mount operations. Run only on a trusted local
Docker VM. An ARM Mac requires amd64 emulation; a native amd64 Linux builder is
preferable. No host filesystem is mounted into this privileged container.

```sh
python3 scripts/prepare-llm.py
docker build --platform linux/amd64 -t nora-builder:trixie .
docker run --name nora-iso-build --platform linux/amd64 --privileged nora-builder:trixie
mkdir -p dist
docker cp nora-iso-build:/build/dist/. dist/
```

The stopped container retains build diagnostics. Remove it explicitly before
reusing the same name. Output: `dist/nora-linux-13-amd64.hybrid.iso`, build log,
and `SHA256SUMS`. Mirror contents change, so builds are not byte-reproducible.

Preparing the LLM requires Python 3.12+ and downloads about 508 MB from the
official upstream projects. Downloads are checksum-pinned and cached in `.build/`.
Generated runtime/model files are included in the image but ignored by Git.

## Validation before release

`scripts/build.sh` checks the finished ISO for BIOS and UEFI boot records and
the live kernel, initramfs, and SquashFS. The report is saved in
`dist/iso-structure.txt`. Run the same check separately with:

```sh
./scripts/verify-iso.sh dist/nora-linux-13-amd64.hybrid.iso
```

Boot the ISO in both BIOS and UEFI VMs. Check the NORA desktop, wallpaper,
networking, audio, live session, and shutdown. Test installation only onto a
disposable virtual disk, then reboot without the ISO and check APT upgrades and
branding persistence. Test real target hardware and Secure Boot separately.
The live user is `nora`; Debian live-config's default live password is `live`.
The installer must create the installed user's own account and password.

## Customization

- `auto/config`: Debian suite, architecture, boot options, installer, ISO identity.
- `config/package-lists/desktop.list.chroot`: included software.
- `config/includes.chroot`: system defaults and NORA theme.
- `config/hooks/live/0900-nora.hook.chroot`: identity and desktop setup.
- `config/hooks/live/0950-nora-menu.hook.binary`: live boot-menu labels.
- `scripts/Dockerfile.verify`: QEMU test environment, native to the builder host.
- `scripts/qmp.py`: QEMU monitor helper for boot status and screenshots.
- `logo.png`: original artwork; copy it to the NORA backgrounds directory after changes.

Debian repositories provide upstream updates. Custom NORA files currently live
in the image; they need a versioned package and signed repository before an
ongoing public update service. Keep component license notices and satisfy source
distribution obligations before publishing. Non-free firmware is enabled for
hardware compatibility and has component-specific licensing.

References: https://www.debian.org/derivatives/ and
https://live-team.pages.debian.net/live-manual/html/live-manual.en.html
