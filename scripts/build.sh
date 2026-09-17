#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo 'Build inside an amd64 Debian 13 Linux environment; see README.md.' >&2
  exit 1
fi
if [[ $EUID != 0 ]]; then
  echo 'live-build needs root: sudo ./scripts/build.sh' >&2
  exit 1
fi
command -v lb >/dev/null
test -s config/includes.chroot/opt/nora/llm/model.gguf || {
  echo 'Run python3 scripts/prepare-llm.py before building (see README.md).' >&2
  exit 1
}
mkdir -p dist
install -Dm644 music/NoraLinuxStartupSong.mp3 \
  config/includes.chroot/usr/share/nora/music/NoraLinuxStartupSong.mp3
lb config
lb build 2>&1 | tee dist/build.log
iso=nora-linux-13-amd64.hybrid.iso
test -s "$iso"
./scripts/verify-iso.sh "$iso" > dist/iso-structure.txt 2>&1
cp "$iso" dist/
cp chroot/usr/share/nora/build-packages.txt dist/
(cd dist && sha256sum "$iso" > SHA256SUMS)
