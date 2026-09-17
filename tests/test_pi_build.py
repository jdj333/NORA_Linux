"""Validate pinned Pi inputs and the boot/storage invariants of the build recipe."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PiBuildTests(unittest.TestCase):
    def test_assets_are_explicit_arm64_and_sha256_pinned(self):
        assets = json.loads((ROOT / 'scripts/pi/assets.json').read_text())
        self.assertEqual(set(assets), {'base.img.xz', 'llama-arm64.tar.gz'})
        for asset in assets.values():
            self.assertTrue(asset['url'].startswith('https://'))
            self.assertIn('arm64', asset['url'])
            self.assertRegex(asset['sha256'], r'^[a-f0-9]{64}$')
            self.assertNotIn('/latest/', asset['url'])

    def test_shell_scripts_parse(self):
        for path in (ROOT / 'scripts/pi').glob('*.sh'):
            with self.subTest(script=path.name):
                subprocess.run(['bash', '-n', str(path)], check=True)

    def test_no_host_model_or_shared_login_secret(self):
        script = (ROOT / 'scripts/pi/first-boot.sh').read_text()
        self.assertIn('until passwd "$user"', script)
        self.assertNotIn('live', script)
        for path in (ROOT / 'scripts/pi').glob('*.sh'):
            self.assertNotIn('10.0.2.2', path.read_text())


if __name__ == '__main__':
    unittest.main()
