# NORA Linux for Raspberry Pi 5

The Pi edition is a **persistent ARM64 SD-card/USB disk image**, not the PC live
ISO. It combines Raspberry Pi OS Lite **Debian 13 Trixie** with NORA's emerald
Xfce desktop, chat history, canvas, command terminal, startup music and offline
chat/voice models. The original amd64 ISO build remains separate.

This is a prototype targeting Pi 5. Automated ARM64 checks do not establish
physical Pi boot, graphics, Wi-Fi, microphone or speaker compatibility. Complete
the hardware checklist below before treating it as a tested release.

## Prepare a card

Use `dist/pi/nora-linux-13-raspberry-pi5-arm64.img.xz` with Raspberry Pi Imager's
**Use custom** image option. Check the accompanying checksum first:

```sh
cd dist/pi
shasum -a 256 -c SHA256SUMS
```

Choose the intended SD card or USB drive in Imager, then write and verify it.
Writing replaces the contents of that selected device. The compressed image can
be selected directly; there is no need to extract it or convert it to an ISO.

Suggested test setup: Pi 5 with 8 GB or more RAM, a 32 GB or larger card/USB drive,
adequate cooling and the appropriate Pi 5 power supply. The image is 10 GiB before
compression. These are test recommendations, not measured minimum requirements.
Connect a display, keyboard and mouse for first boot. Ethernet simplifies the
first test; Wi-Fi can be configured from the desktop network menu. Use an HDMI
audio display or USB audio device; select it in **PulseAudio Volume Control**.

On first boot, the inherited Pi resize mechanism expands the root filesystem.
NORA asks for a password on the console if the account has not been configured.
The default account name is `nora` (or the account created by upstream provisioning).
There is **no preset `live` password**. Once setup finishes, Xfce automatically logs
in and opens NORA. Administrative commands require your chosen password.
Chats and settings persist on the card. Speech is on and preloaded; **Mic is off**.
The local chat server runs on `127.0.0.1:8088`; no Mac model server is needed.

Raspberry Pi Imager customisation is retained through the base's cloud-init
support, but has not yet been tested with this custom image. The attached-console
setup above is the primary initial test path. SSH is not enabled by this build.

## Build

Use a native **ARM64 Linux** Docker host, including Docker on Apple Silicon.
Allow at least 20 GB free in the checkout's filesystem. Loop devices and privileged
mounts are required. This writes only an image file, not a physical SD card.

```sh
python3 scripts/pi/prepare.py
python3 scripts/prepare-voice.py
docker build -t nora-pi-builder:trixie scripts/pi
docker run --rm --privileged \
  -v "$PWD:/work" nora-pi-builder:trixie bash scripts/pi/build.sh
```

Outputs are under `dist/pi/`, with a SHA-256 checksum, package inventory, pinned
base/runtime sources, and validation report. `.build/pi/` caches large downloads
and the uncompressed image. Do not run two builds against the same checkout.
An additional read-only boot/partition check can be run after building:

```sh
docker run --rm --privileged -v "$PWD:/work:ro" \
  nora-pi-builder:trixie bash scripts/pi/verify-image.sh
```

The optional **Build NORA Raspberry Pi image** Actions workflow uses a native ARM64
runner and uploads its results as an Actions artifact; the PC ISO release workflow
is unchanged.

The official base image and llama.cpp ARM64 runtime are pinned by SHA-256 in
`scripts/pi/assets.json`. Chat weights and voice models retain their existing
checksum locks. Voice Python wheels install natively with the shared hash lock.
The apt repositories can change between builds; the package manifest records the
actual result. This is not a claim of bit-for-bit reproducibility.

Pi firmware, kernel, device trees, partition identifiers and filesystem expansion
come from the official base. `kernel=kernel8.img` selects the supported 4 KB-page
ARM64 kernel for native speech-wheel compatibility, rather than the default
Pi-5-specific 16 KB-page kernel. The ARM64 llama.cpp release dispatches between
CPU implementations; the amd64 executable is excluded from this image.

Sources: [Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/),
[official base image directory](https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2026-09-15/),
[Pi kernel configuration](https://www.raspberrypi.com/documentation/computers/config_txt.html).

## Hardware acceptance checklist

- Boot the written image on Pi 5; complete password setup and enter Xfce.
- Reboot: account setup does not repeat, NORA opens, saved chats remain.
- Confirm `uname -m` reports `aarch64` and `getconf PAGESIZE` reports `4096`.
- Confirm root space expanded with `df -h /` and `/boot/firmware` is mounted.
- Disconnect networking: ask NORA a question and hear a complete spoken reply.
- Verify Mic remains off until enabled; test transcription with your microphone.
- Select HDMI/USB audio in Volume Control; check startup music and chat speech.
- Test canvas, terminal, browser, Ethernet/Wi-Fi and a normal shutdown/reboot.
- Record first-reply latency, speech preparation time, RAM use and temperature.

Useful diagnostics:

```sh
systemctl status nora-llm nora-first-boot lightdm
journalctl -b -u nora-llm -u nora-first-boot -u lightdm
free -h
vcgencmd measure_temp
```
