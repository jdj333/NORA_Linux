#!/usr/bin/env python3
"""Stage and verify locked speech models; never downloads at application startup."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / 'scripts/voice-assets.json'
CACHE = ROOT / '.build/voice-assets'
OUTPUT = ROOT / 'config/includes.chroot/opt/nora/voice'


def valid(path, spec):
    if not path.is_file() or path.stat().st_size != spec['bytes']:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == spec['sha256']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(LOCK.read_text())
    for name, spec in manifest['assets'].items():
        destination = OUTPUT / name
        if args.verify_only:
            if not valid(destination, spec):
                raise RuntimeError('Missing or invalid voice asset: ' + name)
            continue
        cached = CACHE / name
        cached.parent.mkdir(parents=True, exist_ok=True)
        if not valid(cached, spec):
            temporary = cached.with_suffix('.download')
            for attempt in range(3):
                try:
                    request = urllib.request.Request(spec['url'], headers={'User-Agent': 'NORA-Linux/1.0'})
                    with urllib.request.urlopen(request, timeout=180) as source, temporary.open('wb') as target:
                        shutil.copyfileobj(source, target)
                    if not valid(temporary, spec):
                        raise RuntimeError('Voice asset checksum mismatch: ' + name)
                    temporary.replace(cached)
                    break
                except Exception:
                    temporary.unlink(missing_ok=True)
                    if attempt == 2:
                        raise
                    time.sleep(2)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not valid(destination, spec):
            shutil.copy2(cached, destination)
        print('Verified voice asset: ' + name, flush=True)
    if not args.verify_only:
        (OUTPUT / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
        shutil.copy2(ROOT / 'scripts/voice-requirements.txt', OUTPUT / 'voice-requirements.txt')
    elif not (OUTPUT / 'provenance.json').is_file():
        raise RuntimeError('Missing voice provenance manifest')


if __name__ == '__main__':
    main()
