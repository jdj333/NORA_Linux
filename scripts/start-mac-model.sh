#!/bin/sh
# Optional development server; the ISO still defaults to its own offline model.
set -eu
cd "$(dirname "$0")/.."
exec llama-server --model config/includes.chroot/opt/nora/llm/model.gguf \
  --alias nora-local --host 127.0.0.1 --port 8089 \
  --ctx-size 4096 --parallel 1 --threads 2 --threads-batch 2 \
  --batch-size 128 --ubatch-size 128 --n-gpu-layers 99 --offline
