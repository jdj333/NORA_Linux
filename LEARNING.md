# NORA Linux build learning

Last updated: 2026-09-16. Read this before rebuilding or debugging NORA.
These notes describe the first Debian 13 amd64 prototype build and its corrections.
Use [README.md](README.md) for the full build and [VALIDATION.md](VALIDATION.md)
for the tested artifact, checksum, evidence, and outstanding tests.

## Start here to avoid repeating work

1. Read the validation record and inspect the current diff before changing anything.
2. Recheck mutable facts cheaply: Docker availability, container state, available
   disk space, and which ISO is being tested. Do not repeat settled research.
3. Choose the smallest necessary operation:

   | Change | Work needed |
   | --- | --- |
   | Documentation | Check references and examples; no ISO build |
   | Boot-menu labels or colors | Update source hook, patch extracted ISO menus, reseal ISO |
   | Desktop defaults or scripts | Update source, patch extracted rootfs, repack SquashFS, reseal ISO |
   | Packages, kernel, architecture, or Debian base | Full live-build run |

4. Check script syntax, paths, permissions, and hook assumptions before compression.
5. Test the exact final ISO. A successful build is not evidence of correct branding
   or a working desktop. Stop repeating checks once they pass unless inputs change.

The tested `dist/` ISO was corrected and resealed after the initial full build.
`dist/build.log` describes that initial build; `dist/finalize.log` describes final
assembly. The source includes the corrections, but a subsequent full build from
that corrected source has not been validated. The original build container's ISO
is older: copying its `dist/.` over the workspace would overwrite the tested release.

## Base and build configuration

- NORA is a Debian derivative defined by live-build configuration, package
  selection, and branding. It does not require a Git fork of Debian itself.
- Keep `--distribution trixie` in `auto/config`. The moving alias `stable` would
  eventually select a different major version. Security and updates are enabled.
- Changing mirrors and base-image tags mean builds are not byte-reproducible.
  Retain package manifests and checksums; pin inputs separately if reproducibility
  becomes a requirement.
- The observed live-build version was `20250505+deb13u1`. Internal paths and
  behavior below are version-specific evidence, not permanent API guarantees.
- Generated live-build configuration can retain old settings. Prefer a fresh
  build tree. `sudo lb clean --purge` deliberately removes build state and caches;
  do not use it as a routine response to a slow or successful build.
- Minimal builder installs using `--no-install-recommends` needed explicit
  `file`, `rsync`, `xz-utils`, `zstd`, and `bzip2`; retain the dependencies in
  [Dockerfile](Dockerfile).
- Firmware and the graphical Debian installer add separate package and initramfs
  stages after much of the live desktop is complete. Do not mistake these for a
  restarted build or remove requested features just to save build time.
- Keep `set -euo pipefail` around `lb build | tee ...`; otherwise logging can hide
  a build failure. Wait for checksum commands to finish before copying outputs.

## macOS, Docker, and slow builds

The first build used an ARM64 Mac with a Linux ARM64 Docker VM, approximately
2 CPUs and 2 GiB RAM. The amd64 builder ran through emulation. It worked, but XZ
SquashFS compression alone took about 25 minutes. Prefer native amd64 Linux for
full builds. This is an observation, not a timing guarantee.

Inspect before repairing the environment:

```sh
uname -sm
docker info --format '{{.OSType}} {{.Architecture}}'
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
df -h .
```

A sandbox socket permission failure did not mean Docker was broken: the same
command with tool-level access succeeded. `colima list` reported a broken profile
while the Docker daemon worked. Verify the daemon before restarting anything.
Build containers require privileged Linux mount operations; the existing workflow
uses `docker cp`, without mounting host directories into the privileged builder.

For an existing running build, use small status reads:

```sh
docker top nora-iso-build -eo pid,ppid,etime,args
docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' nora-iso-build
docker exec nora-iso-build tail -n 30 /build/dist/build.log
```

`mksquashfs -no-progress` can be silent for a long time. During this build its
output was `/build/chroot/filesystem.squashfs`, with the source temporarily at
`/build/chroot/chroot`. Later the output moved to `binary/live/filesystem.squashfs`.
Inspect the process arguments and file growth at the current stage; do not restart
a progressing build because an assumed path is absent or the log is quiet.

Native ARM64 `xorriso` and SquashFS tools can manipulate this amd64 image. Native
repacking was substantially faster than emulated repacking. A QEMU VM exited during
concurrent extraction on the small Docker VM; memory pressure was suspected, not
proven. Sequence extraction, compression, and boots, and bound repacking resources.

## Branding gotchas that were reproduced and fixed

| Surface | Lesson |
| --- | --- |
| Binary hook | live-build already runs it inside `binary/`. Use `boot/` and `isolinux/`, not `binary/boot/`. The original incorrect search silently succeeded without edits; retain explicit directory preconditions. |
| Chroot hook | Paths refer to the target filesystem root, such as `/etc` and `/usr`. |
| Boot menus | Change visible labels and theme directives while preserving kernel arguments, initrd paths, and boot layout. BIOS and UEFI use different files; inspect both. |
| OS identity | The hook diverts `/usr/lib/os-release` before supplying NORA identity. Persistence across installed-system upgrades remains untested. |
| GTK | The GTK3 dark resource path used is `/org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css`. An existing CSS file alone does not prove the running session selected the theme. |
| Wallpaper | Xfce 4.20 can show its implicit wallpaper without any `last-image` properties. Sleeping and updating only existing properties did nothing. The helper explicitly creates settings for connected X11 monitors. |
| Wallpaper scope | The current helper assumes X11 screen 0 and initial workspaces 0–3. Hotplug, multiple X screens, and Wayland are unvalidated. |
| Live user | `username=nora` does not set the display name. `/etc/live/config.conf` also needs `LIVE_USER_FULLNAME="NORA Live User"`. |
| Copied files | `docker cp` introduced host UID/GID ownership into patched rootfs files. Set ownership and modes on those specific files before repacking. Never recursively make the whole rootfs root-owned; service accounts need their ownership. |

The wallpaper helper is
[`config/includes.chroot/usr/local/bin/nora-desktop-defaults`](config/includes.chroot/usr/local/bin/nora-desktop-defaults).
It writes `$HOME/.config/nora-desktop-initialized` only after success. For an
intentional retest in a disposable live session, remove that user's marker and
rerun the helper. Do not reset an existing user's chosen wallpaper casually.

## Cheap source checks

Run from the repository root. Check each shell file separately: `sh -n file1 file2`
checks only the first file, with the others becoming arguments.

```sh
for file in scripts/build.sh scripts/verify-iso.sh; do
  bash -n "$file" || exit 1
done
for file in auto/config config/hooks/live/0900-nora.hook.chroot \
  config/hooks/live/0950-nora-menu.hook.binary \
  config/includes.chroot/usr/local/bin/nora-desktop-defaults; do
  sh -n "$file" || exit 1
done
python3 - <<'PY'
import ast
from pathlib import Path
import xml.etree.ElementTree as ET
ast.parse(Path('scripts/qmp.py').read_text())
for path in Path('config').rglob('*.xml'):
    ET.parse(path)
PY
```

## Incremental repair without a full package rebuild

Always change the repository source as well as the image. Keep the last good ISO
and write a new output. These commands run inside the Linux verifier environment,
using fresh `/test/iso` and `/test/rootfs` directories. They illustrate the verified
repair workflow; substitute the actual changed files rather than blindly applying
an old patch.

```sh
xorriso -osirrox on -indev /test/nora.iso -extract / /test/iso
unsquashfs -d /test/rootfs /test/iso/live/filesystem.squashfs
# Copy corrected source files into their matching /test/rootfs paths first.
chown 0:0 /test/rootfs/usr/local/bin/nora-desktop-defaults /test/rootfs/etc/live/config.conf
chmod 755 /test/rootfs/usr/local/bin/nora-desktop-defaults
chmod 644 /test/rootfs/etc/live/config.conf
mksquashfs /test/rootfs /test/nora-rootfs.squashfs \
  -noappend -comp xz -no-progress -processors 2 -mem 512M
unsquashfs -lls /test/nora-rootfs.squashfs etc/live/config.conf usr/local/bin/nora-desktop-defaults
unsquashfs -cat /test/nora-rootfs.squashfs usr/share/backgrounds/nora/logo.png | sha256sum
cp /test/nora-rootfs.squashfs /test/iso/live/filesystem.squashfs
```

Use `-noappend`: the default can append to an existing SquashFS destination.
For menu-only fixes, skip rootfs extraction and compression. Run the corrected
binary hook with the extracted ISO root as its working directory.

Before ISO assembly, regenerate both `sha256sum.txt` and `md5sum.txt` inside the
extracted ISO, retaining their existing member lists. Do not indiscriminately hash
every file: manifests must not include themselves, and boot-image files can be
modified during ISO assembly. This Python recipe matches the current NORA
manifests' simple two-space separator and unescaped filenames:

```sh
python3 - <<'PY'
import hashlib
from pathlib import Path
root = Path('/test/iso').resolve()
for algorithm, filename in [('sha256', 'sha256sum.txt'), ('md5', 'md5sum.txt')]:
    manifest = root / filename
    rows = []
    for line in manifest.read_text().splitlines():
        _, name = line.split('  ', 1)
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f'Path outside ISO: {name}')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, algorithm).hexdigest()
        rows.append(f'{digest}  {name}\n')
    manifest.write_text(''.join(rows))
PY
```

The first release used this mapping with xorriso's boot-layout replay. Map every
changed file; omit the SquashFS mapping for menu-only changes. The output path
must be fresh. Do not replace this with a generic ISO creation command that loses
the hybrid boot configuration.

```sh
xorriso -indev /test/nora.iso -outdev /test/nora-release.iso \
  -map /test/iso/isolinux/menu.cfg /isolinux/menu.cfg \
  -map /test/iso/isolinux/stdmenu.cfg /isolinux/stdmenu.cfg \
  -map /test/iso/isolinux/live.cfg /isolinux/live.cfg \
  -map /test/iso/boot/grub/grub.cfg /boot/grub/grub.cfg \
  -map /test/iso/boot/grub/live-theme/theme.txt /boot/grub/live-theme/theme.txt \
  -map /test/iso/live/filesystem.squashfs /live/filesystem.squashfs \
  -map /test/iso/sha256sum.txt /sha256sum.txt \
  -map /test/iso/md5sum.txt /md5sum.txt \
  -boot_image any replay
```

Then extract the newly assembled ISO into a fresh directory and check its contents.
Run in a shell with `set -e` so a failed command stops the sequence:

```sh
set -e
bash /test/verify-iso.sh /test/nora-release.iso
xorriso -osirrox on -indev /test/nora-release.iso -extract / /test/release-checks
(cd /test/release-checks && sha256sum -c sha256sum.txt) > /test/internal-sha256.log 2>&1
(cd /test/release-checks && md5sum -c md5sum.txt) > /test/internal-md5.log 2>&1
```

Generate the final external checksum using the release filename, copy the artifact
and checksum back, then verify the host copy with
`(cd dist && shasum -a 256 -c SHA256SUMS)`. Never reuse the initial ISO checksum.

## Reusable BIOS and UEFI boot checks

The native verifier includes QEMU, OVMF, xorriso, and SquashFS tools. Inspect existing
containers first; reuse useful cached data or select a new name rather than blindly
deleting a container. Host setup for a new test container:

```sh
docker build -f scripts/Dockerfile.verify -t nora-iso-verifier:trixie .
docker run -d --name nora-boot-test nora-iso-verifier:trixie sleep infinity
docker cp dist/nora-linux-13-amd64.hybrid.iso nora-boot-test:/test/nora.iso
docker cp scripts/qmp.py nora-boot-test:/test/qmp.py
docker cp scripts/verify-iso.sh nora-boot-test:/test/verify-iso.sh
docker exec -it nora-boot-test bash
```

Inside that container, start a diskless BIOS test:

```sh
qemu-system-x86_64 -m 1024 -smp 2 -accel tcg \
  -cdrom /test/nora.iso -boot d -display none -vga std \
  -qmp unix:/test/qmp.sock,server=on,wait=off \
  -serial file:/test/serial.log -daemonize -pidfile /test/qemu.pid
python3 /test/qmp.py /test/qmp.sock screendump '{"filename":"/test/bios-boot.png","format":"png"}'
python3 /test/qmp.py /test/qmp.sock human-monitor-command '{"command-line":"sendkey ret"}'
```

Allow startup time, capture a fresh desktop screenshot, and inspect it. A temporary
black screen occurred during normal startup; use bounded waits and process checks.
If QMP refuses a connection, inspect whether QEMU exited before blaming the ISO.
In a booted Xfce session, these diagnostics verify identity, applied theme, and DHCP:

```sh
python3 /test/qmp.py /test/qmp.sock human-monitor-command '{"command-line":"sendkey ctrl-alt-t"}'
# Wait for the terminal to open and receive focus before typing.
python3 /test/qmp.py /test/qmp.sock type-text '{"text":"cat /etc/os-release; xfconf-query -c xsettings -p /Net/ThemeName; ip -4 -brief address\n"}'
```

The helper's `type-text` supports a limited character map, not arbitrary clipboard
input. Capture screenshots with distinct names for the current boot; stale files
are not evidence of a successful new test. Copy screenshots to the host with
`docker cp nora-boot-test:/test/bios-boot.png dist/bios-boot.png` and view them.

Quit the BIOS VM before starting UEFI. Remove a stale test socket only after
confirming its QEMU process has exited. Inside the container:

```sh
python3 /test/qmp.py /test/qmp.sock quit
cp /usr/share/OVMF/OVMF_VARS_4M.fd /test/uefi-vars.fd
qemu-system-x86_64 -m 1024 -smp 2 -accel tcg \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
  -drive if=pflash,format=raw,file=/test/uefi-vars.fd \
  -cdrom /test/nora.iso -boot d -display none -vga std \
  -qmp unix:/test/qmp.sock,server=on,wait=off \
  -serial file:/test/uefi-serial.log -daemonize -pidfile /test/qemu.pid
```

Repeat menu, desktop, and screenshot checks. Quit QEMU after collecting evidence,
then run `docker stop nora-boot-test` on the host to avoid leaving tests running.
These tests attach no host disk and do not validate installation.

## What verification does and does not establish

- `scripts/verify-iso.sh` checks BIOS/UEFI boot records and live payload files.
  It does not boot the ISO or test the installer.
- Internal manifest checks catch content mismatches; the external SHA-256 identifies
  the exact delivered image. Both matter after remastering.
- Actual BIOS and UEFI desktop boots passed for the artifact in `VALIDATION.md`.
  Its NORA identity, theme, logo, live-user name, and DHCP address were checked.
- DHCP does not prove external connectivity. Signed shim/GRUB packages and build
  messages about Secure Boot do not prove booting with enrolled keys enabled.
- Installation, installed-system upgrades and branding persistence, Secure Boot,
  and physical hardware remain untested. Do not promote the prototype to a
  supported release based only on these VM checks.

## Interactive desktop and offline chat lessons

- macOS Screen Sharing connected a socket but stalled at its password dialog with
  this QEMU VNC server using `auth=none`. The Linux password `live` is unrelated
  to VNC authentication. `query-vnc` listing a client did not prove a usable desktop.
- The user confirmed that noVNC in a browser worked. The current local viewer is
  `http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale`. Its container is
  `nora-browser`; the QEMU container is `nora-desktop`. Check that both still exist
  and are running before reusing these names. Keep published ports bound to
  `127.0.0.1`, not all host interfaces.
- The viewer was created from `nora-iso-verifier:trixie`, with Debian's `novnc` and
  `python3-websockify` installed. The running command is
  `websockify --web=/usr/share/novnc 6080 nora:5900`, where Docker's container link
  resolves `nora` to `nora-desktop`. It does not change the ISO or guest desktop.
- For a display fix, check HTTP delivery and the complete RFB authentication and
  framebuffer initialization. A socket connection or an independent QMP screenshot
  alone does not prove the user's viewer works.
- Offline chat build instructions and pinned model provenance are in [CHAT.md](CHAT.md)
  and `scripts/prepare-llm.py`. Read these before downloading new model files.
  `config/includes.chroot/opt/nora/llm/` is generated and ignored by Git.
- llama.cpp's GitHub `releases/latest` returned a semantic release with only
  `nightly-tag.txt`, not CPU archives. Resolve that file to the corresponding build
  release, then pin its artifact URL and published digest. The prepared runtime
  dynamically loads implementation and CPU libraries; copying only `llama-server`
  is insufficient.
- A process started through an amd64 chroot on this ARM host appeared as
  `/usr/bin/qemu-x86_64 ./llama-server ...` in `/proc`, not as `./llama-server`.
  Inspect actual process arguments before trying to stop a model test.
- The existing filesystem already had Python GI, GTK3 introspection, and libgomp.
  They are now explicit package requirements. Recheck installed packages when
  changing the base, rather than assuming desktop dependencies remain transitive.
- A real generated reply and transport tests are separate from a fresh boot test
  of systemd startup, Xfce autostart, and the chat window. Verify all layers before
  claiming that the bundled assistant works from the ISO.

## OS access and incremental rebuild lessons

- Keep common system measurements deterministic. Read `/proc/meminfo` using
  `MemAvailable`, and use filesystem statistics for disk space. A live ISO's
  writable overlay is temporary and does not report the host Mac's disk capacity.
  Label sources and observation time; never sum root and home blindly.
- Give the small model a compact fresh OS snapshot and the last real command
  result. Large context slows prompt evaluation substantially under emulation.
  The live `nora` user cannot see the system journal without elevation; use
  `sudo journalctl -u nora-llm -b --no-pager` to inspect actual model progress.
  Model-generated text is only a proposal; `/run` executes explicit user input,
  and the Run button executes the displayed, editable proposal.
- Run `python3 -m unittest discover -s tests -v` after command-runner changes.
  Verify actual file effects, stderr/exit status, process-group cancellation,
  child-held output pipes, time/output limits, and window-close races. A unittest
  run can say OK while a background thread throws: capture thread exceptions in
  cancellation tests. macOS may return EPERM for an already-dead process group;
  confirm the process exited before treating that error as harmless.
- For a temporary guest update, stage only the application overlay in a dedicated
  directory and serve it on container loopback, for example:
  `python3 -m http.server 8091 --bind 127.0.0.1 --directory /test/nora-update`.
  QEMU user networking reaches this at `http://10.0.2.2:8091/`. Do not expose the
  entire artifact directory or publish this transfer port. Stop the server after
  use. Normalize tar ownership to root and mtime to zero to avoid clock-skew
  warnings between the macOS host and guest.
- Check Docker VM RAM, not host Mac RAM: this Docker VM had about 1.9 GiB, despite
  the Mac having 32 GB. QEMU exited when compression ran alongside it; memory
  pressure is a likely cause, not a confirmed OOM diagnosis. Finish repacking,
  extraction, and copies before booting the desktop VM on this constrained host.
- The retained guest kernel has `CONFIG_SQUASHFS_ZSTD=y`. Native ARM64 repacking
  can use `mksquashfs /test/rootfs /test/new.squashfs -noappend -comp zstd
  -Xcompression-level 6 -no-progress -processors 1 -mem 256M` for a faster,
  somewhat larger development image. This does not change live-build's configured
  compression. Regenerate both internal manifests, replay the ISO boot records,
  extract and verify every manifest entry, hash the delivered copy, and boot that
  exact image. Preserve previous validated ISOs under their original names.

## GitHub build and release workflow

- `.github/workflows/build-iso.yml` builds on `main` pushes and manual runs on
  `main`. It uses a native amd64 Ubuntu runner to run the Debian 13 Docker builder;
  the host distribution does not become the ISO base. Prepare the pinned model
  before `docker build`, because the Dockerfile requires its generated overlay.
- GitHub release assets must each be under 2 GiB. Our roughly 3 GB ISO must be
  split; compressing an already compressed SquashFS does not reliably solve this.
  `python3 scripts/package-release.py dist release` creates 1,900 MiB parts,
  checksums for the parts and whole ISO, and exact reassembly instructions. Use a
  fresh output directory. Packaging verifies the whole ISO against `SHA256SUMS`.
- Publication creates a draft, uploads assets, then publishes a prerelease.
  Tags include run ID and attempt, and target the built SHA. Failed uploads leave
  drafts rather than incomplete public downloads. Reruns create distinct tags.
- CI uses no host mounts or GitHub token inside the privileged builder. It removes
  only unused SDK directories on the disposable hosted runner and checks for
  30 GiB free before building. Diagnostics survive build failures as 14-day Actions
  artifacts. Publishing permission is `contents: write`; no personal token is needed.
- Workflow validation: `actionlint .github/workflows/build-iso.yml`. Package tests
  run with `python3 -m unittest discover -s tests -v`, including chunk-boundary
  reconstruction, checksums, tampered inputs, missing inputs, and stale output.
  CI structural/manifest checks do not establish desktop boot or installation.
- The first hosted run exposed an HTTP cancellation race: for an HTTP/1.0 or
  `Connection: close` response, Python clears `HTTPConnection.sock` after headers
  while the response still streams. Retain the connected socket for shutdown and
  explicitly close the response. The regression test waits for a client-received
  chunk before cancelling; waiting only for the server to send headers can mask it.
  A macOS rerun also exposed duplicate SIGTERM from UI and worker threads; serialize
  signals and send TERM at most once, while retaining escalation to KILL.

When extending these notes, record the symptom, confirmed cause or clearly labeled
hypothesis, smallest working fix, reusable command, and verification limit. Keep
artifact-specific results in `VALIDATION.md` and reusable lessons here.
