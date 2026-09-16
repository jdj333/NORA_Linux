import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'package_release', Path(__file__).resolve().parents[1] / 'scripts/package-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleasePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'dist'
        self.source.mkdir()
        self.destination = Path(self.temp.name) / 'release'

    def prepare(self, data):
        (self.source / release.ISO_NAME).write_bytes(data)
        (self.source / 'SHA256SUMS').write_text(
            f'{hashlib.sha256(data).hexdigest()}  {release.ISO_NAME}\n')
        for name in ('build-packages.txt', 'iso-structure.txt', 'internal-sha256.log', 'build-info.json'):
            (self.source / name).write_text('test evidence\n')

    def test_parts_reassemble_exactly_and_all_checksums_match(self):
        for size in (1, 64, 65, 200):
            with self.subTest(size=size):
                data = bytes(range(size))
                self.prepare(data)
                target = self.destination / str(size)
                release.package(self.source, target, part_bytes=64)
                parts = sorted(target.glob('*.part-*'))
                self.assertEqual(b''.join(p.read_bytes() for p in parts), data)
                self.assertTrue(all(0 < p.stat().st_size <= 64 for p in parts))
                for line in (target / 'SHA256SUMS.parts').read_text().splitlines():
                    digest, name = line.split()
                    self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), digest)
                self.assertEqual((target / 'SHA256SUMS').read_bytes(), (self.source / 'SHA256SUMS').read_bytes())
                self.assertEqual((target / 'build-info.json').read_text(), 'test evidence\n')

    def test_corrupted_iso_cannot_be_packaged_successfully(self):
        self.prepare(b'original bytes')
        (self.source / release.ISO_NAME).write_bytes(b'tampered bytes')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            release.package(self.source, self.destination, part_bytes=8)
        self.assertFalse((self.destination / 'SHA256SUMS.parts').exists())

    def test_missing_empty_and_misnamed_iso_fail(self):
        with self.assertRaises(ValueError):
            release.package(self.source, self.destination)
        self.prepare(b'')
        with self.assertRaises(ValueError):
            release.package(self.source, self.destination)
        self.prepare(b'nonempty')
        (self.source / 'SHA256SUMS').write_text('123  wrong.iso\n')
        with self.assertRaisesRegex(ValueError, 'unexpected file'):
            release.package(self.source, self.destination)

    def test_refuses_to_mix_builds_or_exceed_asset_limit(self):
        self.prepare(b'nonempty')
        self.destination.mkdir()
        with self.assertRaises(FileExistsError):
            release.package(self.source, self.destination)
        for size in (0, -1, 2 * 1024**3):
            with self.assertRaises(ValueError):
                release.package(self.source, self.destination, part_bytes=size)


if __name__ == '__main__':
    unittest.main()
