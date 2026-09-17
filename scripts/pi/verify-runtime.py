#!/usr/bin/env python3
"""Exercise the installed native chat server; never use an external model host."""
import json
import subprocess
import time
import urllib.error
import urllib.request

with open('/tmp/nora-model-check.log', 'w') as log:
    server = subprocess.Popen([
        '/opt/nora/llm/llama-server', '--model', '/opt/nora/llm/model.gguf',
        '--host', '127.0.0.1', '--port', '18088', '--ctx-size', '1024',
        '--threads', '2', '--n-gpu-layers', '0', '--offline', '--no-warmup',
    ], stdout=log, stderr=log)
    try:
        for attempt in range(180):
            if server.poll() is not None:
                raise RuntimeError('Native chat server exited; see /tmp/nora-model-check.log')
            try:
                with urllib.request.urlopen('http://127.0.0.1:18088/health', timeout=2) as reply:
                    if reply.status == 200:
                        break
            except (OSError, urllib.error.URLError):
                time.sleep(1)
        else:
            raise TimeoutError('Native chat server did not become ready')
        request = urllib.request.Request('http://127.0.0.1:18088/completion',
            data=json.dumps({'prompt': 'The capital of France is', 'n_predict': 12,
                             'temperature': 0}).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=180) as reply:
            result = json.load(reply)
        assert result['content'].strip(), result
        print('PASS: native ARM64 local chat inference:', repr(result['content']))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
