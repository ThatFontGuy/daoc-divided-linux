"""Checks of the navmesh folder installer (live_world_navmesh.py) with a real junction: the target is never touched."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import live_world_navmesh as n


class NavmeshInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.classic = root / 'classic-navmesh'
        self.classic.mkdir()
        (self.classic / 'zone000.nav').write_bytes(b'classic mesh')
        self.server = root / 'server'
        self.server.mkdir()
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.server / 'navmesh'), str(self.classic)], check=True, capture_output=True)
        self.staged = root / 'staged'
        self.staged.mkdir()
        (self.staged / 'zone000.nav').write_bytes(b'live mesh')
        (self.staged / 'roads.json').write_text('{}')
        self.backups = root / 'backups'
        self.stopped = mock.patch.object(n, 'check_stopped', return_value=None)
        self.stopped.start()

    def tearDown(self):
        self.stopped.stop()
        if os.path.isjunction(self.server / 'navmesh'):
            os.rmdir(self.server / 'navmesh')
        self.temp.cleanup()

    def test_install_replaces_the_junction_and_leaves_its_target_alone(self):
        n.install(self.server, self.staged, self.backups, write=True)
        self.assertFalse(os.path.isjunction(self.server / 'navmesh'))
        self.assertEqual((self.server / 'navmesh' / 'zone000.nav').read_bytes(), b'live mesh')
        self.assertEqual((self.classic / 'zone000.nav').read_bytes(), b'classic mesh')
        self.assertEqual(sorted(p.name for p in self.classic.iterdir()), ['zone000.nav'])

    def test_rollback_restores_the_junction(self):
        folder = n.install(self.server, self.staged, self.backups, write=True)
        n.rollback(self.server, folder, write=True)
        self.assertTrue(os.path.isjunction(self.server / 'navmesh'))
        self.assertEqual((self.server / 'navmesh' / 'zone000.nav').read_bytes(), b'classic mesh')
        self.assertEqual((self.classic / 'zone000.nav').read_bytes(), b'classic mesh')

    def test_rollback_refuses_a_folder_it_did_not_install(self):
        folder = n.install(self.server, self.staged, self.backups, write=True)
        (self.server / 'navmesh' / n.MARKER).unlink()
        with self.assertRaises(SystemExit):
            n.rollback(self.server, folder, write=True)
        self.assertTrue((self.server / 'navmesh' / 'zone000.nav').exists())

    def test_preview_changes_nothing(self):
        self.assertIsNone(n.install(self.server, self.staged, self.backups, write=False))
        self.assertTrue(os.path.isjunction(self.server / 'navmesh'))


if __name__ == '__main__':
    unittest.main()
