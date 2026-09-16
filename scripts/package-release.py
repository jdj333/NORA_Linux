#!/usr/bin/env python3
"""Split a verified ISO into GitHub-sized assets with a verifiable round trip."""
import argparse
import hashlib
from pathlib import Path
import shutil

ISO_NAME = 'nora-linux-13-amd64.hybrid.iso'
PART_BYTES = 1900 * 1024 * 1024  # Strictly below GitHub's 2 GiB asset limit.
BUFFER_BYTES = 8 * 1024 * 1024


def package(source, destination, part_bytes=PART_BYTES):
    source, destination = Path(source), Path(destination)
    iso = source / ISO_NAME
    if not iso.is_file() or not iso.stat().st_size:
        raise ValueError('A nonempty built ISO is required.')
    if not 0 < part_bytes < 2 * 1024**3:
        raise ValueError('Part size must be positive and below 2 GiB.')
    expected, name = (source / 'SHA256SUMS').read_text().strip().split()
    if name != ISO_NAME:
        raise ValueError('The ISO checksum names an unexpected file.')
    destination.mkdir(parents=True, exist_ok=False)  # Never mix separate builds.
    whole = hashlib.sha256()
    parts = []
    with iso.open('rb') as reader:
        remaining = iso.stat().st_size
        while remaining:
            part = destination / f'{ISO_NAME}.part-{len(parts):03d}'
            digest = hashlib.sha256()
            length = min(remaining, part_bytes)
            with part.open('wb') as writer:
                while length:
                    data = reader.read(min(length, BUFFER_BYTES))
                    if not data:
                        raise ValueError('ISO ended before its declared size.')
                    writer.write(data)
                    digest.update(data)
                    whole.update(data)
                    length -= len(data)
                    remaining -= len(data)
            parts.append(f'{digest.hexdigest()}  {part.name}\n')
        if reader.read(1):
            raise ValueError('ISO changed size during packaging.')
    if whole.hexdigest() != expected:
        raise ValueError('ISO checksum mismatch; do not publish these parts.')
    (destination / 'SHA256SUMS.parts').write_text(''.join(parts))
    shutil.copy2(source / 'SHA256SUMS', destination / 'SHA256SUMS')
    for name in ('build-packages.txt', 'iso-structure.txt', 'internal-sha256.log', 'build-info.json'):
        shutil.copy2(source / name, destination / name)
    (destination / 'README-download.md').write_text(f'''# NORA Linux 13 — amd64 prototype

Debian 13 (Trixie), emerald/dark Xfce, and the offline NORA system terminal.
This CI build passed automated tests, ISO boot-record checks, and its internal
SHA-256 manifest. CI does not yet boot the desktop or test installation/hardware.

## Download and reconstruct the bootable ISO

GitHub limits each release asset to less than 2 GiB. Download **all {len(parts)}**
`{ISO_NAME}.part-*` files, `SHA256SUMS.parts`, and `SHA256SUMS` from this release
into an otherwise empty directory. Parts are raw consecutive ISO bytes; they are
not individually bootable. On Linux or macOS, run:

```sh
shasum -a 256 -c SHA256SUMS.parts
cat {ISO_NAME}.part-* > {ISO_NAME}
shasum -a 256 -c SHA256SUMS
```

Each check must report OK before using the reconstructed ISO. On Linux,
`sha256sum -c` is an alternative to `shasum -a 256 -c`.

Boot the reconstructed ISO in an amd64 VM or write it as an image to a USB drive.
It contains BIOS and UEFI boot entries. It is not a Raspberry Pi image.
The live user is `nora`, with password `live`; live-session changes are temporary.

`build-info.json` identifies the exact source commit and Actions run.
`build-packages.txt` records installed package versions. The included model/runtime
licenses and provenance are inside the ISO under `/opt/nora/llm`.
''')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    package(args.source, args.destination)
