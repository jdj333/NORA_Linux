from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat'))
from presence_model import ACTIVE, LABELS, intensity


class PresenceTests(unittest.TestCase):
    def test_idle_is_static_and_thinking_breathes_slowly(self):
        self.assertEqual(intensity('ready', 0), intensity('ready', 123))
        self.assertLess(intensity('thinking', 0), intensity('thinking', 1.8))
        self.assertAlmostEqual(intensity('thinking', 0), intensity('thinking', 3.6))

    def test_reply_accent_decays_after_actual_text_chunk(self):
        self.assertGreater(intensity('replying', 0, 0), intensity('replying', 0, 1))
        self.assertAlmostEqual(intensity('replying', 0, 5), intensity('replying', 0), places=4)

    def test_reduced_motion_is_static_and_all_levels_are_bounded(self):
        for state in LABELS:
            self.assertEqual(intensity(state, 0, 0, False), intensity(state, 100, 4, False))
            for t in range(100):
                value = intensity(state, t / 10, t / 10)
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 0.82)
        self.assertNotIn('loading', ACTIVE)


if __name__ == '__main__':
    unittest.main()
