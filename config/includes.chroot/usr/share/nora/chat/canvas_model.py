"""Shared whiteboard notes derived from visible conversation, never hidden reasoning."""
import base64
import struct
import copy
import json
import re
import uuid

CATEGORIES = ('Questions', 'Ideas', 'Facts', 'Actions')
MAX_CARDS = 60
CARD_WIDTH, CARD_HEIGHT, GAP = 250, 194, 40
SHAPES = ('card', 'pill', 'diamond')
MAX_LINKS = 120


def node_height(card):
    return 194 if card.get('image_url') else (160 if card.get('shape') == 'diamond' else
                                             164 if card['body'] else 108)


def clip(text, limit):
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def validate(state):
    if state is None:
        return {'cards': [], 'follow': True}
    if not isinstance(state, dict) or not isinstance(state.get('follow'), bool):
        raise ValueError('Invalid saved canvas.')
    cards = state.get('cards')
    if not isinstance(cards, list) or len(cards) > MAX_CARDS:
        raise ValueError('Invalid saved canvas cards.')
    ids = set()
    for card in cards:
        if not isinstance(card, dict) or any(not isinstance(card.get(key), str)
                                           for key in ('id', 'title', 'body', 'category', 'source')):
            raise ValueError('Invalid saved card text.')
        if (not card['id'] or card['id'] in ids or card['category'] not in CATEGORIES or
                len(card['title']) > 80 or len(card['body']) > 1200 or len(card['source']) > 500):
            raise ValueError('Invalid saved card.')
        ids.add(card['id'])
        if any(type(card.get(key)) is not int or not 0 <= card[key] <= 20000 for key in ('x', 'y')):
            raise ValueError('Invalid saved card position.')
        if card.get('shape', 'card') not in SHAPES:
            raise ValueError('Invalid node shape.')
        for key, limit in (('image_url', 2048), ('image_error', 300), ('image_data', 180000)):
            if not isinstance(card.get(key, ''), str) or len(card.get(key, '')) > limit:
                raise ValueError('Invalid image node.')
        if card.get('image_data'):
            try:
                data = base64.b64decode(card['image_data'], validate=True)
                if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data) < 24:
                    raise ValueError()
                width, height = struct.unpack('>II', data[16:24])
                if not (0 < width <= 240 and 0 < height <= 120):
                    raise ValueError()
            except (ValueError, struct.error):
                raise ValueError('Invalid saved thumbnail.') from None
    links = state.get('links', [])
    if not isinstance(links, list) or len(links) > MAX_LINKS:
        raise ValueError('Invalid canvas links.')
    for link in links:
        if (not isinstance(link, dict) or not isinstance(link.get('from'), str) or
                not isinstance(link.get('to'), str) or link['from'] not in ids or
                link['to'] not in ids or link['from'] == link['to'] or
                not isinstance(link.get('label'), str) or len(link['label']) > 60):
            raise ValueError('Invalid canvas connection.')
    return copy.deepcopy(state)


def make_card(title, body, category='Ideas', source='Your note'):
    if category not in CATEGORIES:
        raise ValueError('Choose a card category.')
    return {'id': uuid.uuid4().hex, 'title': clip(title or 'Untitled', 80),
            'body': clip(body, 1200), 'category': category, 'source': clip(source, 500), 'x': 16, 'y': 16}


def conversation_cards(prompt, answer, source=None):
    cards = [make_card(clip(prompt, 60), prompt, 'Questions', 'Your message')]
    # Extract excerpts only from the visible answer. Do not interpret shell blocks
    # or ask the small local model to expose its internal reasoning.
    text = re.sub(r'```.*?```', '', answer, flags=re.S)
    parts = [re.sub(r'^\s*(?:[-*•]|\d+[.)])\s+', '', line).strip()
             for line in text.splitlines() if line.strip()]
    if len(parts) == 1:
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', parts[0])
    for part in parts[:3]:
        if not part:
            continue
        category = 'Facts' if source else ('Actions' if re.match(
            r'(?i)^(?:next|try|create|install|check|open|use|run|add|build|test|consider)\b', part) else 'Ideas')
        title = clip(part.split(':', 1)[0], 60)
        cards.append(make_card(title, clip(part, 420), category, source or 'NORA reply · excerpt'))
    return cards


def arrange(cards, width):
    columns = max(1, min(4, (max(280, width) - GAP) // (CARD_WIDTH + GAP)))
    ordered = sorted(cards, key=lambda card: CATEGORIES.index(card['category']))
    for index, card in enumerate(ordered):
        card['x'] = GAP + (index % columns) * (CARD_WIDTH + GAP)
        card['y'] = GAP + (index // columns) * (CARD_HEIGHT + GAP)


def next_position(cards, width):
    columns = max(1, min(4, (max(280, width) - GAP) // (CARD_WIDTH + GAP)))
    for index in range(MAX_CARDS * 8):
        x, y = GAP + index % columns * (CARD_WIDTH + GAP), GAP + index // columns * (CARD_HEIGHT + GAP)
        if not any(abs(x - c['x']) < CARD_WIDTH + 8 and abs(y - c['y']) < CARD_HEIGHT + 8 for c in cards):
            return x, y
    return GAP, min(20000, max((c['y'] for c in cards), default=0) + CARD_HEIGHT + GAP)


def evidence(cards):
    notes = [{'category': c['category'], 'title': clip(c['title'], 50), 'note': clip(c['body'], 120)}
             for c in cards[-4:]]
    while notes and len(json.dumps(notes, ensure_ascii=False).encode('utf-8')) > 1000:
        notes.pop(0)
    return notes


def reply_scene(prompt, answer, source=None):
    """Build a bounded explanation graph from visible Markdown, never execute it."""
    text = re.sub(r'```.*?```', '', answer, flags=re.S)
    images = re.findall(r'!\[([^]\n]{0,80})\]\((https?://[^\s)]+)\)', text)[:2]
    text = re.sub(r'!\[[^]\n]*\]\([^)]*\)', '', text)
    nodes, links, by_title = [], [], {}
    def node(title):
        title = clip(title.strip().strip('*` '), 80)
        if title not in by_title:
            card = make_card(title, '', 'Ideas', source or 'NORA explanation')
            card['shape'] = 'diamond' if title.endswith('?') else 'pill'
            nodes.append(card)
            by_title[title] = card
        return by_title[title]
    for line in text.splitlines():
        parts = [part.strip() for part in re.split(r'\s*(?:->|→)\s*', line)]
        if 2 <= len(parts) <= 6 and all(0 < len(p) <= 80 for p in parts) and len(nodes) + len(parts) <= 10:
            chain = [node(p) for p in parts]
            for start, end in zip(chain, chain[1:]):
                link = {'from': start['id'], 'to': end['id'], 'label': 'leads to'}
                if start is not end and link not in links:
                    links.append(link)
    if not nodes:
        nodes = conversation_cards(prompt, text, source)
        nodes[0]['shape'] = 'pill'
        if len(prompt) <= 60:
            nodes[0]['body'] = ''
        steps = bool(re.search(r'^\s*1[.)]\s', text, re.M))
        for index, card in enumerate(nodes[1:]):
            if ':' in card['body']:
                title, body = card['body'].split(':', 1)
                card.update(title=clip(title.strip('* '), 60), body=body.strip())
            start = nodes[index] if steps else nodes[0]
            links.append({'from': start['id'], 'to': card['id'],
                          'label': 'next' if steps else 'explains'})
    return nodes, links, images


def arrange_graph(cards, links, width):
    """Topological layers, wrapped within each layer; cycles remain visible."""
    if not links:
        arrange(cards, width)
        return
    columns = max(1, min(4, (max(280, width) - GAP) // (CARD_WIDTH + GAP)))
    remaining = {c['id'] for c in cards}
    placed, y = set(), GAP
    while remaining:
        layer = [c for c in cards if c['id'] in remaining and all(
            link['from'] in placed for link in links if link['to'] == c['id'])]
        if not layer:
            layer = [next(c for c in cards if c['id'] in remaining)]
        for offset in range(0, len(layer), columns):
            row = layer[offset:offset + columns]
            row_width = len(row) * CARD_WIDTH + (len(row) - 1) * GAP
            left = max(GAP, (width - row_width) // 2)
            for index, card in enumerate(row):
                card['x'] = left + index * (CARD_WIDTH + GAP)
                card['y'] = y
            y += max(node_height(card) for card in row) + GAP
        placed.update(c['id'] for c in layer)
        remaining.difference_update(placed)
