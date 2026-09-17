"""Explicit image searches using Wikimedia Commons, with source and credit metadata."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from web_access import PageParser, WebError, WebRequest, clean, normalize_url

ENDPOINT = 'https://commons.wikimedia.org/w/api.php?'


def search_target(prompt):
    match = re.fullmatch(r'(?is)(?:/images\s+|(?:please\s+)?(?:show|find|search)(?:\s+me)?\s+(?:images|pictures|photos)(?:\s+(?:of|for))?\s+)(.+)', prompt.strip())
    if prompt.strip() == '/images':
        raise WebError('Usage: /images emerald crystal — search Wikimedia Commons.')
    if not match:
        return None
    query = match.group(1).strip()
    if len(query) > 160:
        raise WebError('Keep the image search under 160 characters.')
    return ENDPOINT + urlencode({'action': 'query', 'format': 'json', 'formatversion': '2',
                                'generator': 'search', 'gsrsearch': query + ' filetype:bitmap',
                                'gsrnamespace': '6', 'gsrlimit': '4', 'prop': 'imageinfo',
                                'iiprop': 'url|mime|extmetadata', 'iiurlwidth': '320',
                                'iiextmetadatafilter': 'Artist|LicenseShortName'})


def metadata_text(value):
    parser = PageParser('https://commons.wikimedia.org/')
    parser.feed(value)
    return clean(parser.readable())[:160]


def results(data, url):
    images, lines, links = [], [], []
    for page in sorted(data.get('query', {}).get('pages', []), key=lambda p: p.get('index', 0)):
        info = (page.get('imageinfo') or [{}])[0]
        if info.get('mime') not in ('image/png', 'image/jpeg', 'image/webp'):
            continue
        image_url = normalize_url(info.get('thumburl') or info['url'])
        description = normalize_url(info['descriptionurl'])
        metadata = info.get('extmetadata', {})
        artist = metadata_text(metadata.get('Artist', {}).get('value', 'Credit on source page'))
        license_name = metadata_text(metadata.get('LicenseShortName', {}).get('value', 'See source license'))
        title = clean(page.get('title', 'Image').removeprefix('File:'))[:120]
        credit = f'{artist} · {license_name} · {description}'
        images.append({'url': image_url, 'alt': title, 'source': credit[:500]})
        links.append(description)
        lines.append(title + '\n' + credit)
        if len(images) == 2:
            break
    return {'url': url, 'requested_url': url, 'title': 'Wikimedia Commons image results',
            'text': '\n\n'.join(lines) or 'No supported images found. Try more specific search words.',
            'links': links, 'images': images, 'truncated': False,
            'observed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}


def search(url):
    if not url.startswith(ENDPOINT):
        raise WebError('Invalid image search endpoint.')
    request = Request(url, headers={'User-Agent': 'NORA-Linux/13 (https://noralinux.com) Canvas',
                                   'Accept': 'application/json', 'Accept-Encoding': 'identity'})
    with urlopen(request, timeout=10) as response:
        data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise WebError('Image search response is too large.')
    data = json.loads(data)
    if 'error' in data:
        raise WebError('Wikimedia Commons could not complete this image search.')
    return results(data, url)


class ImageSearchRequest(WebRequest):
    worker_script = str(Path(__file__).resolve())


if __name__ == '__main__':
    try:
        result = search(sys.argv[2])
    except (WebError, OSError, ValueError, KeyError, TypeError) as error:
        result = {'error': 'Image search unavailable. Check your connection or try again. ' + str(error)[:180]}
    print(json.dumps(result))
