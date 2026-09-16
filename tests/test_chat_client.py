"""Exercise the real HTTP stream parser against a local fake model server."""
import http.server
import json
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat'))
from client import Cancelled, ChatError, ChatRequest, context


class Handler(http.server.BaseHTTPRequestHandler):
    mode = 'success'
    observed = None
    connected = threading.Event()
    release = threading.Event()

    def log_message(self, *_):
        pass

    def do_POST(self):
        Handler.observed = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(503 if self.mode == 'unavailable' else 200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        if self.mode == 'unavailable':
            return
        if self.mode == 'wait':
            self.wfile.flush()
            self.connected.set()
            self.release.wait(3)
            return
        if self.mode == 'invalid':
            self.wfile.write(b'data: not-json\n\n')
            return
        for chunk in ['Hello ', 'NORA 🌿']:
            event = {'choices': [{'delta': {'content': chunk}}]}
            self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
            self.wfile.flush()
        if self.mode != 'truncated':
            self.wfile.write(b'data: [DONE]\n\n')


class ChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.mode = 'success'
        Handler.connected.clear()
        Handler.release.clear()
        self.request = ChatRequest(port=self.server.server_port)
        self.messages, _ = context([], 'Hello')

    def test_stream_and_request_contract(self):
        chunks = []
        result = self.request.stream(self.messages, chunks.append)
        self.assertEqual(chunks, ['Hello ', 'NORA 🌿'])
        self.assertEqual(result, 'Hello NORA 🌿')
        self.assertTrue(Handler.observed['stream'])
        self.assertEqual(Handler.observed['messages'], self.messages)
        self.assertNotIn('tools', Handler.observed)

    def test_http_failure(self):
        Handler.mode = 'unavailable'
        with self.assertRaisesRegex(ChatError, '503'):
            self.request.stream(self.messages, lambda _: None)

    def test_incomplete_stream_is_not_success(self):
        Handler.mode = 'truncated'
        with self.assertRaisesRegex(ChatError, 'before the reply finished'):
            self.request.stream(self.messages, lambda _: None)

    def test_invalid_stream(self):
        Handler.mode = 'invalid'
        with self.assertRaises(ChatError):
            self.request.stream(self.messages, lambda _: None)

    def test_cancel_before_request(self):
        self.request.cancel()
        with self.assertRaises(Cancelled):
            self.request.stream(self.messages, lambda _: None)

    def test_cancel_unblocks_waiting_stream(self):
        Handler.mode = 'wait'
        errors = []
        def worker():
            try:
                self.request.stream(self.messages, lambda _: None)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(Handler.connected.wait(2))
        self.request.cancel()
        thread.join(2)
        Handler.release.set()
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Cancelled)

    def test_context_trims_pairs_without_mutating_history(self):
        history = [{'role': 'user', 'content': 'old' * 400},
                   {'role': 'assistant', 'content': 'answer' * 100},
                   {'role': 'user', 'content': 'recent'},
                   {'role': 'assistant', 'content': 'reply'}]
        messages, trimmed = context(history, 'new' * 400)
        self.assertTrue(trimmed)
        self.assertEqual(len(history), 4)
        self.assertEqual(messages[1:3], history[2:])
        self.assertEqual(messages[0]['role'], 'system')

    def test_input_limit_counts_utf8_bytes(self):
        with self.assertRaises(ChatError):
            context([], '🌿' * 401)
        with self.assertRaises(ChatError):
            context([], '   ')


if __name__ == '__main__':
    unittest.main()
