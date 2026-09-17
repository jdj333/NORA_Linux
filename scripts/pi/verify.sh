#!/bin/bash
set -euo pipefail
[[ $(dpkg --print-architecture) == arm64 ]]
test -s /boot/firmware/kernel8.img
test -s /boot/firmware/initramfs8
test -s /boot/firmware/bcm2712-rpi-5-b.dtb
grep -q '^kernel=kernel8.img$' /boot/firmware/config.txt
grep -q '^ID=nora$' /etc/os-release
test ! -e /var/lib/nora/setup-complete
test ! -e /etc/live/config.conf
test -s /opt/nora/llm/provenance.json
systemd-analyze verify /etc/systemd/system/nora-first-boot.service
systemctl is-enabled nora-llm.service nora-first-boot.service lightdm.service
/opt/nora/llm/llama-server --version
python3 - <<'PY'
import struct
from pathlib import Path
binary = Path('/opt/nora/llm/llama-server').read_bytes()
assert binary[:4] == b'\x7fELF' and struct.unpack_from('<H', binary, 18)[0] == 183, 'ARM64 ELF required'
import sys
sys.path.insert(0, '/opt/nora/voice/python')
import onnxruntime, kokoro_onnx, moonshine_voice, sounddevice
from gi.repository import GLib
print('PASS: ARM64 runtime, native speech imports, boot files, identity and services')
PY
python3 /tmp/nora-verify-runtime.py
python3 /tmp/nora-verify-voice.py
rm -f /tmp/nora-verify-runtime.py /tmp/nora-verify-voice.py /tmp/nora-model-check.log
