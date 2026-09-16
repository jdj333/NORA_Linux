"""Local-only streaming chat transport. No shell execution or saved history."""
import http.client
import json
import socket
import threading

SYSTEM_PROMPT = (
    'You are NORA, the friendly assistant built into NORA Linux 13, based on Debian '
    'Trixie with the Xfce desktop. Answer clearly and briefly in English unless '
    'asked for another language. You can chat and explain Linux commands. You '
    'cannot execute commands, inspect files, or see the computer. Never claim '
    'you have performed an action. If unsure, say so.'
)
MAX_INPUT_BYTES = 1600
HISTORY_BYTES = 2400


class ChatError(Exception):
    pass


class Cancelled(Exception):
    pass


def context(history, prompt):
    """Keep complete recent exchanges within a conservative UTF-8 byte budget."""
    prompt = prompt.strip()
    if not prompt:
        raise ChatError('Type a message first.')
    if len(prompt.encode('utf-8')) > MAX_INPUT_BYTES:
        raise ChatError('Please shorten your message (limit: 1,600 UTF-8 bytes).')
    previous = [dict(message) for message in history]
    while previous and sum(len(m['content'].encode('utf-8')) for m in previous) + len(prompt.encode('utf-8')) > HISTORY_BYTES:
        del previous[:2]
    return [{'role': 'system', 'content': SYSTEM_PROMPT}, *previous,
            {'role': 'user', 'content': prompt}], len(previous) != len(history)


def ready():
    connection = http.client.HTTPConnection('127.0.0.1', 8088, timeout=2)
    try:
        connection.request('GET', '/health')
        response = connection.getresponse()
        return response.status == 200
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


class ChatRequest:
    def __init__(self, host='127.0.0.1', port=8088):
        self.connection = http.client.HTTPConnection(host, port, timeout=120)
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()
        sock = self.connection.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def stream(self, messages, on_chunk):
        text = []
        try:
            if self.cancelled.is_set():
                raise Cancelled()
            self.connection.connect()
            if self.cancelled.is_set():
                raise Cancelled()
            self.connection.request('POST', '/v1/chat/completions', body=json.dumps({
                'model': 'nora-local', 'messages': messages, 'stream': True,
                'max_tokens': 256, 'temperature': 0.5,
            }), headers={'Content-Type': 'application/json'})
            response = self.connection.getresponse()
            if response.status != 200:
                raise ChatError(f'Model returned HTTP {response.status}. Try New chat, or wait for the model to finish loading.')
            finished = False
            while True:
                if self.cancelled.is_set():
                    raise Cancelled()
                line = response.readline(1024 * 1024)
                if not line:
                    break
                if not line.startswith(b'data:'):
                    continue
                data = line[5:].strip()
                if data == b'[DONE]':
                    finished = True
                    break
                event = json.loads(data)
                if event.get('error'):
                    raise ChatError('The local model reported an error. Try New chat.')
                choices = event.get('choices') or []
                if not choices:
                    continue
                chunk = choices[0].get('delta', {}).get('content') or ''
                if chunk:
                    text.append(chunk)
                    on_chunk(chunk)
            if self.cancelled.is_set():
                raise Cancelled()
            if not finished:
                raise ChatError('The model connection ended before the reply finished. Please retry.')
            if not text:
                raise ChatError('The model returned an empty reply. Please retry.')
            return ''.join(text)
        except (OSError, http.client.HTTPException) as error:
            if self.cancelled.is_set():
                raise Cancelled() from error
            raise ChatError('Cannot reach the local model. Wait for startup, then try again.') from error
        except (ValueError, KeyError, TypeError) as error:
            raise ChatError('The local model sent an invalid reply. Please retry.') from error
        finally:
            self.connection.close()
