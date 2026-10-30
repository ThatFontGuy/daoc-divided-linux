"""Checks of the 1.130 world overlay (modern_world_overlay.py) on small fake client folders."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import modern_world_overlay as o


def write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def snapshot(app: Path) -> dict:
    return {p.relative_to(app).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*') if p.is_file()}


class WorldOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.classic, self.client, self.backups = root / 'classic', root / 'modern', root / 'backups'
        for app in (self.classic, self.client):
            write(app / 'game.dll', b'game ' + app.name.encode())
        # A zone whose files differ, and whose folder is spelled differently in each client.
        write(self.classic / 'zones' / 'zone000' / 'dat000.mpk', b'classic zone')
        write(self.client / 'zones' / 'Zone000' / 'dat000.mpk', b'live zone')
        write(self.classic / 'zones' / 'zones.mpk', b'classic zones table')
        write(self.client / 'zones' / 'zones.mpk', b'live zones table')
        # The same file in both: untouched.
        write(self.classic / 'zones' / 'Nifs' / 'tree.npk', b'tree')
        write(self.client / 'zones' / 'Nifs' / 'tree.npk', b'tree')
        # Only the classic client has it (Marfach Caverns).
        write(self.classic / 'zones' / 'zone276' / 'dat276.mpk', b'marfach')
        # OpenDAoC's own keep model, and a live New Towns model the classic client doesn't have.
        write(self.classic / 'Newtowns' / 'zones' / 'Nifs' / 'hborderkeep1.npk', b'opendaoc keep')
        write(self.client / 'Newtowns' / 'zones' / 'Nifs' / 'hborderkeep1.npk', b'live keep')
        write(self.client / 'Newtowns' / 'zones' / 'Nifs' / 'bchurch1.npk', b'live church')
        # Frontier model.
        write(self.classic / 'frontiers' / 'Nifs' / 'gatehouse_lvl4.npk', b'classic gate')
        write(self.client / 'frontiers' / 'Nifs' / 'gatehouse_lvl4.npk', b'live gate')
        # Outside the world folders: never touched, even when different or missing.
        write(self.classic / 'figures' / 'ab_pet01.nif', b'private pet')
        write(self.classic / 'ui' / 'skin.dds', b'classic ui')
        write(self.client / 'ui' / 'skin.dds', b'live ui')
        self.closed = mock.patch.object(o, 'running_from', return_value=[])
        self.closed.start()

    def tearDown(self):
        self.closed.stop()
        self.temp.cleanup()

    def test_plan_lists_only_world_changes(self):
        entries = {e['path']: e['action'] for e in o.plan(self.classic, self.client)['entries']}
        self.assertEqual(entries, {
            'zones/zone000/dat000.mpk': 'replace',
            'zones/zones.mpk': 'replace',
            'zones/zone276/dat276.mpk': 'add',
            'newtowns/zones/nifs/hborderkeep1.npk': 'replace',
            'newtowns/zones/nifs/bchurch1.npk': 'remove',
            'frontiers/nifs/gatehouse_lvl4.npk': 'replace',
        })

    def test_only_limits_the_plan(self):
        entries = {e['path']: e['action'] for e in
                   o.plan(self.classic, self.client, ['zones/zones.mpk', 'zones/zone276'])['entries']}
        self.assertEqual(entries, {'zones/zones.mpk': 'replace', 'zones/zone276/dat276.mpk': 'add'})

    def test_apply_makes_the_world_files_match_the_classic_client(self):
        folder = o.apply(self.classic, self.client, self.backups, write=True)
        self.assertEqual((self.client / 'zones' / 'Zone000' / 'dat000.mpk').read_bytes(), b'classic zone')
        self.assertEqual([p.name for p in (self.client / 'zones').iterdir() if p.name.lower() == 'zone000'], ['Zone000'])
        self.assertEqual((self.client / 'zones' / 'zone276' / 'dat276.mpk').read_bytes(), b'marfach')
        self.assertFalse((self.client / 'Newtowns' / 'zones' / 'Nifs' / 'bchurch1.npk').exists())
        self.assertEqual((self.client / 'ui' / 'skin.dds').read_bytes(), b'live ui')
        self.assertFalse((self.client / 'figures').exists())
        self.assertEqual((self.client / 'game.dll').read_bytes(), b'game modern')
        self.assertEqual(o.plan(self.classic, self.client)['entries'], [])
        self.assertEqual((folder / 'files' / 'newtowns' / 'zones' / 'nifs' / 'bchurch1.npk').read_bytes(), b'live church')

    def test_preview_changes_nothing(self):
        before = snapshot(self.client)
        self.assertIsNone(o.apply(self.classic, self.client, self.backups, write=False))
        self.assertEqual(snapshot(self.client), before)
        self.assertFalse(self.backups.exists())

    def test_rollback_restores_the_original_client(self):
        before = snapshot(self.client)
        folder = o.apply(self.classic, self.client, self.backups, write=True)
        o.rollback(self.client, folder, write=True)
        self.assertEqual(snapshot(self.client), before)

    def test_rollback_refuses_after_a_later_change(self):
        folder = o.apply(self.classic, self.client, self.backups, write=True)
        write(self.client / 'zones' / 'Zone000' / 'dat000.mpk', b'edited later')
        with self.assertRaises(SystemExit):
            o.rollback(self.client, folder, write=True)
        self.assertEqual((self.client / 'zones' / 'Zone000' / 'dat000.mpk').read_bytes(), b'edited later')

    def test_a_failed_apply_restores_the_client(self):
        before = snapshot(self.client)
        with mock.patch.object(o, 'verify', return_value=['zones/zones.mpk has the wrong contents']):
            with self.assertRaises(RuntimeError):
                o.apply(self.classic, self.client, self.backups, write=True)
        self.assertEqual(snapshot(self.client), before)

    def test_refuses_while_the_client_runs(self):
        before = snapshot(self.client)
        with mock.patch.object(o, 'running_from', return_value=[str(self.client / 'game.dll')]):
            with self.assertRaises(SystemExit):
                o.apply(self.classic, self.client, self.backups, write=True)
        self.assertEqual(snapshot(self.client), before)


if __name__ == '__main__':
    unittest.main()
