"""Public-address boundaries, bounded downloads, and sourced image discovery."""
import http.server
import json
from pathlib import Path
import socket
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat'))
from canvas_images import download, public_address, MAX_IMAGE_BYTES, ImageRequest
from image_search import search_target, results
from web_access import PageParser, WebError, WebCancelled


class Handler(http.server.BaseHTTPRequestHandler):
    requests = []
    def log_message(self, *_):
        pass
    def do_GET(self):
        self.requests.append(dict(self.headers))
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', 'http://127.0.0.1/private')
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'image/svg+xml' if self.path == '/svg' else 'image/png')
        self.end_headers()
        try:
            self.wfile.write(b'x' * (MAX_IMAGE_BYTES + 1) if self.path == '/large' else b'fixture')
        except (BrokenPipeError, ConnectionResetError):
            pass


class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://public.example:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_public_dns_rejects_mixed_private_and_special_addresses(self):
        for address in ('127.0.0.1', '10.0.2.2', '169.254.169.254', '::1', 'fc00::1'):
            records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 80))]
            with patch('canvas_images.socket.getaddrinfo', return_value=records), self.assertRaises(WebError):
                public_address('example.org', 80)
        records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 80))]
        with patch('canvas_images.socket.getaddrinfo', return_value=records):
            self.assertEqual(public_address('example.org', 80), '8.8.8.8')

    def test_download_is_bounded_and_has_no_cookies_or_credentials(self):
        with patch('canvas_images.public_address', return_value='127.0.0.1'):
            data, url, media = download(self.url + '/png')
            self.assertEqual(data, b'fixture')
            self.assertEqual(media, 'image/png')
            for path in ('/large', '/svg'):
                with self.assertRaises(WebError):
                    download(self.url + path)
        self.assertNotIn('Authorization', Handler.requests[0])
        self.assertNotIn('Cookie', Handler.requests[0])
        self.assertIn('public.example', Handler.requests[0]['Host'])

    def test_redirect_rechecks_destination_and_cancel_prevents_launch(self):
        with patch('canvas_images.public_address', side_effect=['127.0.0.1', WebError('private')]), self.assertRaises(WebError):
            download(self.url + '/redirect')
        request = ImageRequest('https://example.org/image.png')
        request.cancel()
        with self.assertRaises(WebCancelled):
            request.run()
        self.assertIsNone(request.process)

    def test_page_candidates_exclude_hidden_and_non_web_images(self):
        parser = PageParser('https://example.org/page')
        parser.feed('<meta property="og:image" content="/hero.png"><img src="/hero.png">'
                    '<div hidden><img src="/private.png"></div><img src="file:///etc/passwd">'
                    '<img src="/other.jpg" alt="A garden">')
        self.assertEqual(parser.images, [{'url': 'https://example.org/hero.png', 'alt': ''},
                                         {'url': 'https://example.org/other.jpg', 'alt': 'A garden'}])

    def test_search_routes_and_retains_artist_license_source(self):
        for prompt in ('/images emerald', 'Show me images of emerald', 'find photos of emerald'):
            self.assertIn('gsrsearch=emerald', search_target(prompt))
        self.assertIsNone(search_target('Explain gardening'))
        info = {'mime': 'image/jpeg', 'url': 'https://upload.wikimedia.org/a.jpg',
                'descriptionurl': 'https://commons.wikimedia.org/wiki/File:A.jpg',
                'extmetadata': {'Artist': {'value': '<b>Artist Name</b>'},
                                'LicenseShortName': {'value': 'CC BY 4.0'}}}
        page = results({'query': {'pages': [{'title': 'File:A.jpg', 'imageinfo': [info]}]}}, 'https://example.org/')
        self.assertEqual(len(page['images']), 1)
        self.assertIn('Artist Name · CC BY 4.0', page['images'][0]['source'])
        self.assertNotIn('<b>', json.dumps(page))


if __name__ == '__main__':
    unittest.main()
