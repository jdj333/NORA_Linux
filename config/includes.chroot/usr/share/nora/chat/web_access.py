"""Explicit website reads, isolated for bounded time and responsive cancellation."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_DOWNLOAD = 2 * 1024 * 1024
MAX_TEXT = 16000
READ_SECONDS = 30


class WebError(Exception):
    pass


class WebCancelled(WebError):
    pass


def normalize_url(value):
    value = value.strip()
    if not value or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value):
        raise WebError('Enter one website URL, up to 2,048 characters, without spaces.')
    if '://' not in value:
        value = 'https://' + value
    try:
        parts = urlsplit(value)
        if parts.scheme not in ('http', 'https') or not parts.hostname:
            raise ValueError()
        if parts.username is not None or parts.password is not None:
            raise WebError('Use a website URL without embedded credentials.')
        host = parts.hostname.encode('idna').decode('ascii')
        if ':' in host:
            host = '[' + host + ']'
        if parts.port is not None:
            host += ':' + str(parts.port)
        return urlunsplit((parts.scheme, host, quote(parts.path or '/', safe="/%:@!$&'()*+,;=-._~"),
                           quote(parts.query, safe="%=&?/:@!$'()*+,;~-._"), ''))
    except (ValueError, UnicodeError):
        raise WebError('Use an http:// or https:// website URL.') from None


def target(prompt):
    """Route explicit page requests independently of the small local model."""
    text = prompt.strip()
    if text == '/web':
        raise WebError('Usage: /web https://example.com — or “Look up example.com”.')
    if text.startswith('/web '):
        return normalize_url(text[5:])
    address = r'(?:https?://[^\s<>]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}(?::\d+)?(?:/[^\s<>]*)?)'
    if re.fullmatch(address, text):
        return normalize_url(text)
    if re.match(r'(?i)^(?:please\s+)?(?:look\s+up|lookup|read|visit|open|browse|summarize|check|what\b|how\b|tell\b)', text):
        found = re.search(address, text)
        if found:
            return normalize_url(found.group().rstrip('.,!?);'))
    return None


def clean(text):
    return ''.join(c for c in text if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127
                   and c not in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'))


class PageParser(HTMLParser):
    HIDDEN = {'script', 'style', 'template', 'svg', 'iframe', 'noscript'}
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    BLOCK = {'p', 'div', 'section', 'article', 'main', 'h1', 'h2', 'h3', 'h4', 'li', 'tr', 'br', 'hr'}

    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.hidden = []
        self.in_title = False
        self.title = []
        self.text = []
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.hidden:
            if tag not in self.VOID:
                self.hidden.append(tag)
            return
        if tag in self.HIDDEN or 'hidden' in attrs or attrs.get('aria-hidden') == 'true':
            if tag not in self.VOID:
                self.hidden.append(tag)
            return
        if tag == 'title':
            self.in_title = True
        if tag in self.BLOCK:
            self.text.append('\n')
        image = (attrs.get('src') or attrs.get('data-src')) if tag == 'img' else None
        if tag == 'meta' and attrs.get('property') == 'og:image':
            image = attrs.get('content')
        if image and len(self.images) < 6:
            try:
                image = normalize_url(urljoin(self.url, image))
                if not any(item['url'] == image for item in self.images):
                    self.images.append({'url': image, 'alt': clean(attrs.get('alt') or '')[:120]})
            except WebError:
                pass
        if tag == 'a' and attrs.get('href') and len(self.links) < 20:
            try:
                link = normalize_url(urljoin(self.url, attrs['href']))
                if link not in self.links:
                    self.links.append(link)
            except WebError:
                pass

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.hidden:
            if tag in self.hidden:
                del self.hidden[len(self.hidden) - 1 - self.hidden[::-1].index(tag):]
            return
        if tag == 'title':
            self.in_title = False
        if tag in self.BLOCK:
            self.text.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            (self.title if self.in_title else self.text).append(data)

    def readable(self):
        return '\n'.join(' '.join(line.split()) for line in ''.join(self.text).splitlines() if line.strip())


class Redirects(HTTPRedirectHandler):
    max_redirections = 5
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = normalize_url(newurl)
        if req.full_url.startswith('https://') and url.startswith('http://'):
            raise WebError('The website redirected from HTTPS to insecure HTTP; read the HTTP URL explicitly if intended.')
        return super().redirect_request(req, fp, code, msg, headers, url)


def fetch(url):
    url = normalize_url(url)
    request = Request(url, headers={'User-Agent': 'NORA-Linux/13 WebsiteReader',
                                   'Accept': 'text/html,application/xhtml+xml,text/plain',
                                   'Accept-Encoding': 'identity'})
    try:
        with build_opener(Redirects()).open(request, timeout=10) as response:
            media = response.headers.get_content_type()
            if media not in ('text/html', 'application/xhtml+xml', 'text/plain'):
                raise WebError(f'This address returned {media}, not a readable HTML or text page.')
            data = response.read(MAX_DOWNLOAD + 1)
            limited = len(data) > MAX_DOWNLOAD
            data = data[:MAX_DOWNLOAD]
            compression = response.headers.get('Content-Encoding', 'identity').lower()
            if compression == 'gzip':
                decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                try:
                    data = decoder.decompress(data, MAX_DOWNLOAD + 1)
                except zlib.error:
                    raise WebError('The website returned invalid compressed content.') from None
                limited = limited or len(data) > MAX_DOWNLOAD or not decoder.eof
                data = data[:MAX_DOWNLOAD]
            elif compression != 'identity':
                raise WebError(f'This website requires unsupported {compression} compression; try Firefox.')
            encoding = response.headers.get_content_charset() or 'utf-8'
            try:
                text = data.decode(encoding, errors='replace')
            except LookupError:
                text = data.decode('utf-8', errors='replace')
            final_url = normalize_url(response.geturl())
            title, links, images = '', [], []
            if media != 'text/plain':
                parser = PageParser(final_url)
                parser.feed(text)
                text = parser.readable()
                title = ' '.join(''.join(parser.title).split())
                links = parser.links
                images = parser.images
            text = clean(text).strip()
            if not text:
                raise WebError('The page contains no readable text. It may need JavaScript or a browser login; try Firefox.')
            return {'url': final_url, 'requested_url': url, 'title': clean(title)[:300],
                    'text': text[:MAX_TEXT], 'links': links, 'images': images,
                    'truncated': limited or len(text) > MAX_TEXT,
                    'observed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    except HTTPError as error:
        code = error.code
        error.close()
        raise WebError(f'The website returned HTTP {code}. It may be unavailable or restrict automated readers.') from None
    except (URLError, OSError, ValueError) as error:
        raise WebError('Could not read the website. Check your internet connection, address, and the site’s HTTPS certificate. '
                       + clean(str(error))[:180]) from None


class WebRequest:
    worker_script = str(Path(__file__).resolve())
    def __init__(self, url, timeout=READ_SECONDS):
        self.url = normalize_url(url)
        self.timeout = timeout
        self.cancelled = threading.Event()
        self.lock = threading.Lock()
        self.process = None

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.process is not None:
                self.process.kill()

    def run(self):
        with self.lock:
            if self.cancelled.is_set():
                raise WebCancelled('Website read stopped.')
            # A separate process bounds DNS, connection and body reads together.
            self.process = process = subprocess.Popen(
                [sys.executable, self.worker_script, '--fetch', self.url],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        started = time.monotonic()
        try:
            while True:
                try:
                    output, _ = process.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    if time.monotonic() - started >= self.timeout:
                        raise WebError('The website read timed out. Check your connection or try again.')
            if self.cancelled.is_set():
                raise WebCancelled('Website read stopped.')
            if process.returncode:
                raise WebError('The website reader could not finish this request.')
            result = json.loads(output)
            if 'error' in result:
                raise WebError(result['error'])
            return result
        finally:
            with self.lock:
                if process.poll() is None:
                    process.kill()
                self.process = None
            process.communicate()


def evidence(page, prompt):
    """Select a short, relevant excerpt for the 4K-context offline model."""
    terms = set(re.findall(r'\w{4,}', prompt.lower())) - {'what', 'this', 'that', 'page', 'website', 'summarize'}
    lines = page['text'].splitlines()
    ranked = sorted(range(len(lines)), key=lambda i: (-sum(t in lines[i].lower() for t in terms), i))
    chosen, used = [], 0
    for i in ranked:
        line = lines[i].encode('utf-8')[:1800 - used].decode('utf-8', 'ignore')
        if line:
            chosen.append((i, line))
            used += len(line.encode('utf-8')) + 1
        if used >= 1800:
            break
    return {'url': page['url'], 'title': page['title'], 'observed_utc': page['observed_utc'],
            'excerpt': '\n'.join(line for _, line in sorted(chosen)), 'partial': True,
            'images': page.get('images', [])[:2]}


if __name__ == '__main__':
    try:
        result = fetch(sys.argv[2]) if len(sys.argv) == 3 and sys.argv[1] == '--fetch' else {'error': 'Expected --fetch URL.'}
    except WebError as error:
        result = {'error': str(error)}
    print(json.dumps(result, ensure_ascii=False))
