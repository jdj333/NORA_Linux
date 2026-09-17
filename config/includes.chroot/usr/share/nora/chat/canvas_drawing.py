"""Cairo shapes and directed links for the native GTK whiteboard."""
import math
from canvas_model import CARD_WIDTH, node_height
from style import rgb


def node_shape(_widget, cr, card):
    width, height = _widget.get_allocated_width(), _widget.get_allocated_height()
    shape = card.get('shape', 'card')
    if shape == 'diamond':
        cr.move_to(width / 2, 2)
        cr.line_to(width - 2, height / 2)
        cr.line_to(width / 2, height - 2)
        cr.line_to(2, height / 2)
        cr.close_path()
    else:
        radius = 18 if shape == 'pill' else 8
        for x, y, start in ((width - radius - 2, radius + 2, -math.pi / 2),
                            (width - radius - 2, height - radius - 2, 0),
                            (radius + 2, height - radius - 2, math.pi / 2),
                            (radius + 2, radius + 2, math.pi)):
            cr.arc(x, y, radius, start, start + math.pi / 2)
        cr.close_path()
    cr.set_source_rgb(*rgb('node'))
    cr.fill_preserve()
    cr.set_source_rgb(*rgb('accent' if card.get('shape') == 'diamond' else 'node_border'))
    cr.set_line_width(1)
    cr.stroke()
    return False


def connections(cr, cards, links, positions):
    lookup = {c['id']: c for c in cards}
    for link in links:
        a, b = lookup.get(link['from']), lookup.get(link['to'])
        if not a or not b:
            continue
        ax, ay = positions.get(a['id'], (a['x'], a['y']))
        bx, by = positions.get(b['id'], (b['x'], b['y']))
        ah, bh = node_height(a), node_height(b)
        dx, dy = bx - ax, by - ay
        if abs(dx) > abs(dy):
            right = dx > 0
            start = (ax + (CARD_WIDTH if right else 0), ay + ah / 2)
            end = (bx + (0 if right else CARD_WIDTH), by + bh / 2)
            bend = (end[0] - start[0]) / 2
            controls = (start[0] + bend, start[1], end[0] - bend, end[1])
            angle = 0 if right else math.pi
        else:
            down = dy >= 0
            start = (ax + CARD_WIDTH / 2, ay + (ah if down else 0))
            end = (bx + CARD_WIDTH / 2, by + (0 if down else bh))
            bend = (end[1] - start[1]) / 2
            controls = (start[0], start[1] + bend, end[0], end[1] - bend)
            angle = math.pi / 2 if down else -math.pi / 2
        cr.set_source_rgb(*rgb('connector'))
        cr.set_line_width(1.2)
        cr.move_to(*start)
        if abs(dy) > ah + 60 and abs(dx) < CARD_WIDTH:
            # A side channel keeps long links from crossing intermediate nodes.
            side = max(12, min(ax, bx) - 20)
            cr.line_to(start[0], start[1] + (14 if dy > 0 else -14))
            cr.line_to(side, start[1] + (14 if dy > 0 else -14))
            cr.line_to(side, end[1] - (14 if dy > 0 else -14))
            cr.line_to(end[0], end[1] - (14 if dy > 0 else -14))
            cr.line_to(*end)
        else:
            cr.curve_to(*controls, *end)
        cr.stroke()
        cr.move_to(*end)
        for offset in (-0.5, 0.5):
            cr.line_to(end[0] - 9 * math.cos(angle + offset), end[1] - 9 * math.sin(angle + offset))
        cr.close_path()
        cr.fill()
        if link['label']:
            cr.select_font_face('DM Sans')
            cr.set_font_size(10)
            label = link['label']
            extents = cr.text_extents(label)
            x, y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            cr.set_source_rgb(*rgb('canvas'))
            cr.rectangle(x - extents[2] / 2 - 4, y - 8, extents[2] + 8, 14)
            cr.fill()
            cr.set_source_rgb(*rgb('muted'))
            cr.move_to(x - extents[2] / 2, y + 2)
            cr.show_text(label)


def grid(cr):
    """Paint only visible dots, even when a saved board spans thousands of pixels."""
    x1, y1, x2, y2 = cr.clip_extents()
    cr.set_source_rgb(*rgb('grid'))
    for x in range(int(x1 // 24) * 24 + 12, int(x2) + 1, 24):
        for y in range(int(y1 // 24) * 24 + 12, int(y2) + 1, 24):
            cr.arc(x, y, 0.8, 0, math.tau)
            cr.fill()
