"""Bounded public-web image thumbnails; decoded in a cancellable child process."""
import base64
import http.client
import ipaddress
import json
from pathlib import Path
import socket
import ssl
import sys
from urllib.parse import urljoin, urlsplit
from web_access import WebError, WebRequest, normalize_url

MAX_IMAGE_BYTES = 3 * 1024 * 1024


def public_address(host, port):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    ips = [item[4][0] for item in addresses]
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise WebError('Canvas images must use public internet addresses.')
    return ips[0]


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, secure):
        super().__init__(host, port, timeout=8)
        self.address, self.secure = address, secure

    def connect(self):
        # Connect to the checked address, not a second DNS lookup; preserve TLS SNI.
        self.sock = socket.create_connection((self.address, self.port), self.timeout)
        if self.secure:
            try:
                self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self.host)
            except Exception:
                self.sock.close()
                raise


def download(url):
    url = normalize_url(url)
    for _ in range(6):
        parts = urlsplit(url)
        secure = parts.scheme == 'https'
        port = parts.port or (443 if secure else 80)
        address = public_address(parts.hostname, port)
        connection = PinnedConnection(parts.hostname, port, address, secure)
        try:
            path = parts.path + ('?' + parts.query if parts.query else '')
            connection.request('GET', path, headers={
                'User-Agent': 'NORA-Linux/13 Canvas', 'Accept': 'image/png,image/jpeg,image/webp',
                'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location:
                    raise WebError('Image redirect has no destination.')
                target = normalize_url(urljoin(url, location))
                if secure and target.startswith('http://'):
                    raise WebError('Image redirected to insecure HTTP.')
                url = target
                continue
            if response.status != 200:
                raise WebError(f'Image returned HTTP {response.status}.')
            media = response.getheader('Content-Type', '').split(';')[0].strip().lower()
            if media not in ('image/png', 'image/jpeg', 'image/webp'):
                raise WebError('Canvas supports PNG, JPEG, and WebP images.')
            if response.getheader('Content-Encoding', 'identity') != 'identity':
                raise WebError('Compressed image responses are unsupported.')
            data = response.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise WebError('Image is larger than 3 MiB.')
            return data, url, media
        finally:
            connection.close()
    raise WebError('Too many image redirects.')


def thumbnail(data, media):
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf, GLib
    expected = {'image/png': 'png', 'image/jpeg': 'jpeg', 'image/webp': 'webp'}[media]
    try:
        loader = GdkPixbuf.PixbufLoader.new_with_type(expected)
        dimensions = []
        def size_prepared(_loader, width, height):
            dimensions.append((width, height))
            ratio = min(1, 220 / max(1, width), 100 / max(1, height))
            loader.set_size(max(1, int(width * ratio)), max(1, int(height * ratio)))
        loader.connect('size-prepared', size_prepared)
        try:
            for offset in range(0, len(data), 1024):
                loader.write(data[offset:offset + 1024])
                if dimensions and (max(dimensions[0]) > 8192 or dimensions[0][0] * dimensions[0][1] > 16000000):
                    raise WebError('Image dimensions are too large.')
        finally:
            loader.close()
        pixbuf = loader.get_pixbuf()
        if not pixbuf:
            raise WebError('Image could not be decoded.')
        ok, output = pixbuf.save_to_bufferv('png', [], [])
        if not ok or len(output) > 130000:
            raise WebError('Thumbnail could not be stored.')
        return base64.b64encode(output).decode('ascii')
    except GLib.Error:
        raise WebError('Image format is unavailable or its data is invalid.') from None


def fetch_image(url):
    data, final_url, media = download(url)
    return {'image_data': thumbnail(data, media), 'url': final_url}


class ImageRequest(WebRequest):
    worker_script = str(Path(__file__).resolve())


if __name__ == '__main__':
    try:
        result = fetch_image(sys.argv[2])
    except (WebError, OSError, ValueError, http.client.HTTPException) as error:
        result = {'error': str(error)[:300]}
    print(json.dumps(result))
