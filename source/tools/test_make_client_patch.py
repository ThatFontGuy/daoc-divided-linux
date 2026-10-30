"""Checks of the modern client patch (make_client_patch.py): synthetic edits, and the real pristine 1.130 client when
this machine has one (OFFLINE_DAOC_PRISTINE_1130, or the developer's OpenDAoC copy)."""
import base64
import hashlib
import os
import unittest
from pathlib import Path
import make_client_patch as m

PRISTINE = Path(os.environ.get('OFFLINE_DAOC_PRISTINE_1130', Path.home() / 'Desktop/OpenDAoC/DAoC Full Client/Dark Age of Camelot'))
MODERN_TEST = Path(__file__).resolve().parents[2] / 'artifacts/modern-client-test/runtime/client-modern/app'


def entry(original, patched):
    return dict(Path='x', InputSha256=m.sha(original), OutputSha256=m.sha(patched), OutputSize=len(patched),
                Edits=[dict(At=at, Remove=remove, Insert=base64.b64encode(block).decode('ascii'))
                       for at, remove, block in m.edits(original, patched)])


class ClientPatchTests(unittest.TestCase):
    def test_in_place_changes_and_growth(self):
        original = bytes(range(256)) * 5000  # over 1 MB: compared in place
        patched = bytearray(original)
        patched[10:14] = b'ABCD'
        patched[500000] = 0xFF
        patched += b'new section'
        e = entry(original, bytes(patched))
        self.assertEqual(m.apply(original, e), bytes(patched))
        self.assertEqual(len(e['Edits']), 3)

    def test_an_insertion_keeps_only_the_new_text(self):
        original = b''.join(b'<line%d>value %d</line%d>\r\n' % (i, i * 7, i) for i in range(60))
        cut = original.index(b'<line30>')
        patched = original[:cut] + b'<c>added</c>\r\n' + original[cut:]
        e = entry(original, patched)
        self.assertEqual(m.apply(original, e), patched)
        # Only the added line's length ships (the matcher may align it a few bytes either way).
        self.assertEqual(sum(len(base64.b64decode(x['Insert'])) for x in e['Edits']), len(b'<c>added</c>\r\n'))
        self.assertTrue(all(x['Remove'] == 0 for x in e['Edits']))

    def test_refuses_another_input(self):
        original, patched = b'x' * 100, b'y' * 100
        with self.assertRaises(ValueError):
            m.apply(b'z' * 100, entry(original, patched))

    def test_a_whole_file_replacement_is_one_guarded_edit(self):
        stock, ours = b'stock splash archive' * 50, b'our splash'
        e = entry(stock, ours) | dict(Edits=[dict(At=at, Remove=remove, Insert=base64.b64encode(block).decode('ascii'))
                                             for at, remove, block in m.replace_whole(stock, ours)])
        self.assertEqual(len(e['Edits']), 1)
        self.assertEqual(m.apply(stock, e), ours)
        with self.assertRaises(ValueError):
            m.apply(b'a different splash', e)

    def test_the_real_client_patch_rebuilds_the_test_client(self):
        if not (PRISTINE / 'game.dll').is_file():
            self.skipTest('No pristine 1.130 client on this machine')
        patch = m.build(PRISTINE)
        self.assertEqual([f['Path'] for f in patch['Files']], ['game.dll', 'pregame/character_creation.xml', 'pregame/splash.mpk'])
        game = patch['Files'][0]
        self.assertEqual((game['InputSha256'][:8], game['OutputSha256'][:8]), ('3915a495', '39d82bb0'))
        # The stock 1.130 loading screen in, the Divided Realms splash out, in one edit.
        splash = patch['Files'][2]
        self.assertEqual(splash['InputSha256'][:8], '9348c3a6')
        self.assertEqual(splash['OutputSha256'], m.sha(m.SPLASH.read_bytes()))
        self.assertEqual(len(splash['Edits']), 1)
        self.assertEqual(m.apply((PRISTINE / 'pregame/splash.mpk').read_bytes(), splash), m.SPLASH.read_bytes())
        if MODERN_TEST.is_dir():
            for f in patch['Files']:
                self.assertEqual(hashlib.sha256((MODERN_TEST / f['Path']).read_bytes()).hexdigest(), f['OutputSha256'], f['Path'])


if __name__ == '__main__':
    unittest.main()
