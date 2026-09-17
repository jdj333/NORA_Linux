#!/usr/bin/env python3
"""Download verified Pi assets and architecture-independent NORA models."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('assets', ROOT / 'scripts/prepare-llm.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)
# Reuse model downloader without staging the amd64 executable in the Pi image.
assets.CACHE.mkdir(parents=True, exist_ok=True)
for name in ('model.gguf', 'model-LICENSE'):
    assets.download(name, *assets.ASSETS[name])
assets.CACHE = ROOT / '.build/pi'
assets.CACHE.mkdir(parents=True, exist_ok=True)
for name, item in json.loads((ROOT / 'scripts/pi/assets.json').read_text()).items():
    assets.download(name, item['url'], item['sha256'])

manifest = {
    'runtime': 'llama.cpp b10964 CPU ARM64 with CPU feature dispatch',
    'model': 'Qwen2.5-0.5B-Instruct Q4_K_M',
    'model_revision': assets.REVISION,
    'assets': {name: {'url': assets.ASSETS[name][0], 'sha256': assets.ASSETS[name][1]}
               for name in ('model.gguf', 'model-LICENSE')},
}
manifest['assets']['runtime'] = json.loads((ROOT / 'scripts/pi/assets.json').read_text())['llama-arm64.tar.gz']
(assets.CACHE / 'llm-provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
