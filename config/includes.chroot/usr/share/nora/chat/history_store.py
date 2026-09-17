"""Private, transactional local chat storage; no model or network dependency."""
import json
import os
from pathlib import Path
import sqlite3
import time
from canvas_model import validate as validate_canvas


def default_path():
    root = Path(os.environ.get('XDG_STATE_HOME', ''))
    if not root.is_absolute():
        root = Path.home() / '.local/state'
    return root / 'nora/chats.sqlite3'


class HistoryStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.parent.chmod(0o700)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.path.chmod(0o600)
        self.db = sqlite3.connect(self.path, timeout=2)
        try:
            self.db.execute('PRAGMA secure_delete=ON')
            self.db.execute('PRAGMA journal_mode=DELETE')
            with self.db:
                self.db.execute('CREATE TABLE IF NOT EXISTS chats '
                                '(id TEXT PRIMARY KEY, title TEXT NOT NULL, state TEXT NOT NULL, updated REAL NOT NULL)')
                self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        except Exception:
            self.db.close()
            raise

    def list_chats(self):
        return self.db.execute('SELECT id, title FROM chats ORDER BY updated DESC, id').fetchall()

    def active(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='active'").fetchone()
        return row[0] if row else None

    def animation_enabled(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='animate_emerald'").fetchone()
        return not row or row[0] != '0'

    def set_animation(self, enabled):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('animate_emerald', ?)",
                            ('1' if enabled else '0',))

    def load(self, chat_id):
        row = self.db.execute('SELECT state FROM chats WHERE id=?', (chat_id,)).fetchone()
        if row is None:
            raise ValueError('Saved chat was not found.')
        state = json.loads(row[0])
        if not isinstance(state, dict) or state.get('version') != 1:
            raise ValueError('Unsupported saved chat format.')
        for key in ('title', 'cwd', 'draft', 'command_draft'):
            if not isinstance(state.get(key), str):
                raise ValueError('Invalid saved chat text.')
        for key in ('transcript', 'terminal'):
            if not isinstance(state.get(key), list) or any(
                not isinstance(part, list) or len(part) != 2 or
                not isinstance(part[0], str) or part[1] not in (None, 'nora', 'you', 'note', 'error', 'command')
                for part in state[key]
            ):
                raise ValueError('Invalid saved transcript.')
        if not isinstance(state.get('history'), list) or any(
            not isinstance(message, dict) or message.get('role') not in ('user', 'assistant') or
            not isinstance(message.get('content'), str) for message in state['history']
        ):
            raise ValueError('Invalid saved context.')
        if state.get('last_command') is not None and not isinstance(state['last_command'], dict):
            raise ValueError('Invalid saved command context.')
        page = state.get('last_page')
        if page is not None and (not isinstance(page, dict) or any(
            not isinstance(page.get(key), str) for key in ('text', 'url', 'title', 'observed_utc')
        )):
            raise ValueError('Invalid saved website context.')
        # Optional for compatibility with chats saved before the canvas existed.
        if 'canvas' in state:
            validate_canvas(state['canvas'])
        return state

    def save(self, chat_id, state):
        data = json.dumps(state, ensure_ascii=False)
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO chats VALUES (?, ?, ?, ?)',
                            (chat_id, state['title'], data, time.time()))
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('active', ?)", (chat_id,))

    def clear(self):
        # One transaction: either both saved chats and active context disappear,
        # or a storage failure leaves the previous state intact.
        with self.db:
            self.db.execute('DELETE FROM chats')
            self.db.execute("DELETE FROM settings WHERE key='active'")

    def close(self):
        self.db.close()
