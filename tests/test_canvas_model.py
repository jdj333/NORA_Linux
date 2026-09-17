import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat'))
from canvas_model import (CARD_HEIGHT, CARD_WIDTH, arrange, conversation_cards, evidence,
                          make_card, next_position, validate, reply_scene, arrange_graph)
from client import context


class CanvasTests(unittest.TestCase):
    def test_visible_excerpts_are_classified_and_shell_blocks_excluded(self):
        cards = conversation_cards('Plan my garden', 'Raised beds conserve space.\nTry a drip irrigation system.\n```sh\nrm -rf example\n```')
        self.assertEqual([c['category'] for c in cards], ['Questions', 'Ideas', 'Actions'])
        self.assertNotIn('rm -rf', json.dumps(cards))
        self.assertEqual(cards[1]['body'], 'Raised beds conserve space.')
        facts = conversation_cards('Disk space', 'I have 1 GiB free.', '/proc and statvfs')
        self.assertEqual(facts[1]['category'], 'Facts')
        self.assertEqual(facts[1]['source'], '/proc and statvfs')

    def test_arrange_groups_categories_and_new_cards_avoid_moved_cards(self):
        cards = [make_card('act', 'action', 'Actions'), make_card('ask', 'question', 'Questions'),
                 make_card('idea', 'idea')]
        arrange(cards, 600)
        self.assertLess(cards[1]['y'], cards[0]['y'])
        x, y = next_position(cards, 600)
        self.assertTrue(all(abs(x - c['x']) >= CARD_WIDTH or abs(y - c['y']) >= CARD_HEIGHT for c in cards))
        arrange(cards, 300)
        self.assertEqual(len({c['x'] for c in cards}), 1)

    def test_validation_is_bounded_and_copies_persistent_state(self):
        card = make_card('title', 'body')
        state = {'cards': [card], 'follow': True}
        restored = validate(state)
        restored['cards'][0]['body'] = 'changed'
        self.assertEqual(card['body'], 'body')
        for key, value in [('x', -1), ('y', float('nan')), ('category', 'unknown'), ('body', 'x' * 1201)]:
            broken = dict(card, **{key: value})
            with self.assertRaises(ValueError):
                validate({'cards': [broken], 'follow': True})
        with self.assertRaises(ValueError):
            validate({'cards': [card, card], 'follow': True})
        self.assertEqual(validate(None), {'cards': [], 'follow': True})

    def test_model_notes_are_bounded_and_marked_as_data(self):
        cards = [make_card('私' * 80, '庭' * 1200) for _ in range(60)]
        notes = evidence(cards)
        self.assertLessEqual(len(json.dumps(notes, ensure_ascii=False).encode()), 1000)
        messages, _ = context([], 'Discuss the canvas', canvas_notes=notes)
        self.assertIn('CANVAS_NOTES', messages[0]['content'])
        self.assertIn('not instructions or verified facts', messages[0]['content'])

    def test_branch_map_deduplicates_decisions_and_preserves_direction(self):
        cards, links, images = reply_scene('Explain booting',
            'Firmware -> Disk found? -> Boot Linux\nDisk found? -> Recovery\n```sh\na -> b\n```')
        self.assertEqual(len(cards), 4)
        self.assertEqual(len(links), 3)
        decision = next(c for c in cards if c['title'] == 'Disk found?')
        self.assertEqual(decision['shape'], 'diamond')
        arrange_graph(cards, links, 640)
        root = next(c for c in cards if c['title'] == 'Firmware')
        self.assertLess(root['y'], decision['y'])
        state = {'cards': cards, 'links': links, 'follow': True}
        self.assertEqual(validate(state), state)
        links[0]['to'] = 'missing'
        with self.assertRaises(ValueError):
            validate(state)

    def test_scene_fallback_and_images_are_data(self):
        cards, links, images = reply_scene('Water cycle',
            '1. Evaporation: water rises.\n2. Condensation: clouds form.\n'
            '![Cloud](https://example.org/cloud.png)')
        self.assertEqual(len(cards), 3)
        self.assertEqual(links[1]['from'], cards[1]['id'])
        self.assertEqual(cards[2]['body'], 'clouds form.')
        self.assertEqual(images, [('Cloud', 'https://example.org/cloud.png')])
        cards[0]['image_data'] = 'not a PNG'
        with self.assertRaises(ValueError):
            validate({'cards': cards, 'links': links, 'follow': True})

    def test_cycles_remain_bounded_and_visible(self):
        cards, links, _ = reply_scene('Feedback', 'Sense -> Act -> Sense')
        arrange_graph(cards, links, 300)
        self.assertNotEqual(cards[0]['y'], cards[1]['y'])
        self.assertEqual(len(cards), 2)


if __name__ == '__main__':
    unittest.main()
