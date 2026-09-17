import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       'config/includes.chroot/usr/share/nora/chat'))
from history_store import HistoryStore, default_path


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state/chats.sqlite3'
        self.store = HistoryStore(self.path)
        self.addCleanup(self.store.close)

    def state(self, title='Question'):
        return {'version': 1, 'title': title, 'history': [{'role': 'user', 'content': '私の質問'}],
                'transcript': [['私の質問', 'you']], 'terminal': [['output', None]],
                'cwd': '/tmp', 'draft': 'draft', 'command_draft': 'printf test',
                'last_command': {'exit_code': 0}, 'last_page': None}

    def test_round_trip_multiple_chats_active_and_permissions(self):
        first, second = self.state(), self.state('Second')
        self.store.save('one', first)
        self.store.save('two', second)
        other = HistoryStore(self.path)
        try:
            self.assertEqual(other.active(), 'two')
            self.assertEqual(other.load('one'), first)
            self.assertEqual(other.load('two'), second)
            self.assertEqual(len(other.list_chats()), 2)
        finally:
            other.close()
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)

    def test_clear_removes_context_and_active_metadata(self):
        self.store.save('one', self.state('secret-marker-782354'))
        self.store.save('two', self.state())
        self.store.clear()
        self.assertEqual(self.store.list_chats(), [])
        self.assertIsNone(self.store.active())
        self.assertNotIn(b'secret-marker-782354', self.path.read_bytes())

    def test_failed_delete_rolls_back_both_tables(self):
        self.store.save('one', self.state())
        self.store.db.execute("CREATE TRIGGER prevent_delete BEFORE DELETE ON settings "
                              "BEGIN SELECT RAISE(ABORT, 'failed'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.clear()
        self.assertEqual(self.store.active(), 'one')
        self.assertEqual(self.store.load('one'), self.state())

    def test_corrupt_context_is_rejected_and_preserved(self):
        self.store.save('one', self.state())
        with self.store.db:
            self.store.db.execute("UPDATE chats SET state='not json'")
        with self.assertRaises(ValueError):
            self.store.load('one')
        self.assertEqual(len(self.store.list_chats()), 1)

    def test_xdg_state_directory_requires_absolute_path(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': '/tmp/nora-state-test'}):
            self.assertEqual(default_path(), Path('/tmp/nora-state-test/nora/chats.sqlite3'))
        with patch.dict(os.environ, {'XDG_STATE_HOME': 'relative'}):
            self.assertEqual(default_path(), Path.home() / '.local/state/nora/chats.sqlite3')

    def test_animation_preference_survives_reopen_and_history_clear(self):
        self.assertTrue(self.store.animation_enabled())
        self.store.set_animation(False)
        self.store.save('one', self.state())
        self.store.clear()
        other = HistoryStore(self.path)
        try:
            self.assertFalse(other.animation_enabled())
            self.assertIsNone(other.active())
            self.assertEqual(other.list_chats(), [])
        finally:
            other.close()


if __name__ == '__main__':
    unittest.main()
