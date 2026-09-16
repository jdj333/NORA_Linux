# NORA Linux 13 prototype validation

Validated on 2026-09-16. Target: 64-bit Intel/AMD PCs (amd64).

Artifact: `dist/nora-linux-13-amd64.hybrid.iso` (2,456,944,640 bytes).

SHA-256:

```text
4fe1c680f76d22a15d236d7e2d6953136bc745564f1afa0c5e476b13d6d4da68
```

Passed:

- Debian Trixie live-build completed with the current configured security and updates repositories.
- Final ISO has BIOS and UEFI El Torito records and a hybrid MBR/GPT layout.
- Kernel, initramfs, and live SquashFS are present.
- Independently extracted final ISO passed both internal SHA-256 and MD5 manifests.
- Workspace copy matches the SHA-256 calculated in the release container.
- BIOS VM boot reached the Xfce desktop with the original NORA logo and NORA Live User name.
- Running VM reported `ID=nora`, `ID_LIKE=debian`, and theme `NORA-Emerald`.
- VM network interface was up with a DHCP address; external connectivity was not tested.
- UEFI VM boot reached the same NORA desktop with the correct logo, theme, and live-user name.
- Logo content matches the original SHA-256: `9119d52880440ba5a2976f8fcb74ac7109b2806cca32ae4805c44355691b48c8`.
- Corrected wallpaper helper and live-user configuration are root-owned with appropriate permissions.
- Shell, Python, and Xfce XML syntax checks passed.

Boot-menu and wallpaper corrections were applied during validation, and the final
image was repacked and resealed. `dist/build.log` records the initial live-build
run; `dist/finalize.log` records final ISO assembly. The source configuration
includes those corrections for subsequent full builds.

Evidence is saved in `dist/`: `iso-structure.txt`, `internal-sha256.log`,
`internal-md5.log`, `build-packages.txt`, and boot/desktop screenshots.

Not yet validated: installation to disk, installed-system upgrades, Secure Boot
with enrolled keys, or physical hardware (including Wi-Fi, audio, GPU drivers,
and suspend/resume). This is a bootable prototype, not a supported public release.
