#!/usr/bin/env python3
"""Fetch checksum-pinned offline chat assets into live-build's ignored overlay."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.build' / 'chat'
OUTPUT = ROOT / 'config/includes.chroot/opt/nora/llm'
REVISION = '9217f5db79a29953eb74d5343926648285ec7e67'
MODEL_ROOT = f'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/{REVISION}'
ASSETS = {
    'model-LICENSE': (
        f'{MODEL_ROOT}/LICENSE',
        '832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e'),
    'llama.tar.gz': (
        'https://github.com/ggml-org/llama.cpp/releases/download/b10964/llama-b10964-bin-ubuntu-x64.tar.gz',
        '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'),
    'model.gguf': (
        f'{MODEL_ROOT}/qwen2.5-0.5b-instruct-q4_k_m.gguf',
        '74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db'),
}


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(name, url, digest):
    path = CACHE / name
    if path.exists() and checksum(path) == digest:
        print(f'Using verified cache: {name}', flush=True)
        return path
    temporary = path.with_suffix('.download')
    print(f'Downloading {name}', flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as stream:
        shutil.copyfileobj(response, stream)
    if checksum(temporary) != digest:
        temporary.unlink()
        raise RuntimeError(f'Checksum mismatch for {name}')
    temporary.replace(path)
    return path


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    paths = {name: download(name, *spec) for name, spec in ASSETS.items()}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT.parent) as work:
        stage = Path(work)
        with tarfile.open(paths['llama.tar.gz']) as archive:
            archive.extractall(stage, filter='data')
        runtime = stage / 'llama-b10964'
        # The server dynamically loads implementation and CPU libraries beside it.
        # Retain upstream libraries and LICENSE, omit unrelated executable tools.
        for path in runtime.iterdir():
            if path.name != 'llama-server' and path.name != 'LICENSE' and not path.name.startswith('lib'):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        shutil.copy2(paths['model.gguf'], runtime / 'model.gguf')
        shutil.copy2(paths['model-LICENSE'], runtime / 'MODEL-LICENSE')
        manifest = {
            'runtime': 'llama.cpp v0.4.1 / b10964, CPU amd64',
            'model': 'Qwen2.5-0.5B-Instruct Q4_K_M',
            'model_revision': REVISION,
            'assets': {name: {'url': url, 'sha256': digest} for name, (url, digest) in ASSETS.items()},
        }
        (runtime / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        runtime.replace(OUTPUT)
    print(f'Offline model and runtime ready: {OUTPUT}')


if __name__ == '__main__':
    main()
