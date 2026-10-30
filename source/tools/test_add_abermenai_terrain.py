"""Checks of add_abermenai_terrain.py on a small fake client folder."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import add_abermenai_terrain as t
from add_abermenai_terrain import archive


def mpk(path: Path, name: str, files: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(archive.write(name.encode(), [archive.Entry(n, d) for n, d in files.items()]))


class AbermenaiTerrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Path(self.temp.name) / "client-opendaoc" / "app"
        maps = {"terrain.pcx": b"heights", "offset.pcx": b"offsets"}
        mpk(self.app / "zones/zone252/dat252.mpk", "dat252.mpk", {**maps, "sector.dat": b"Battlefield2"})
        mpk(self.app / "zones/zone253/dat253.mpk", "dat253.mpk", {**maps, "sector.dat": b"Battlefield4"})
        mpk(self.app / "zones/zone252/ter252.mpk", "ter252.mpk", {"patch0000-00.dds": b"tile" * 50})
        mpk(self.app / "zones/zone252/lod252.mpk", "lod252.mpk", {"lod00-00.dds": b"lod" * 50})
        patcher = mock.patch.object(t, "client_running", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.temp.cleanup()

    def test_rename_keeps_every_entry_and_names_the_archive(self):
        source = (self.app / "zones/zone252/ter252.mpk").read_bytes()
        result = t.renamed(source, b"ter253.mpk")
        name, entries = archive.read(result)
        self.assertEqual(name, b"ter253.mpk")
        self.assertEqual(entries, archive.read(source)[1])
        # directory and payload byte for byte: only the name block changed
        _, ds, ns, _ = t.struct.unpack("<4I", bytes(v ^ i for i, v in enumerate(source[5:21])))
        self.assertTrue(result.endswith(source[21 + ns:]))

    def test_preview_writes_nothing(self):
        t.install(self.app, apply=False)
        self.assertFalse((self.app / "zones/zone253/ter253.mpk").exists())

    def test_install_verify_and_rollback(self):
        t.install(self.app, apply=True)
        for kind in ("ter", "lod"):
            name, _ = archive.read((self.app / f"zones/zone253/{kind}253.mpk").read_bytes())
            self.assertEqual(name, f"{kind}253.mpk".encode())
        t.verify(self.app)
        t.install(self.app, apply=True)       # idempotent
        backup = next((self.app.parent / "backups").iterdir())
        t.rollback(self.app, backup, apply=True)
        self.assertEqual(sorted(p.name for p in (self.app / "zones/zone253").iterdir()), ["dat253.mpk"])

    def test_refuses_when_the_terrain_differs(self):
        mpk(self.app / "zones/zone253/dat253.mpk", "dat253.mpk", {"terrain.pcx": b"other", "offset.pcx": b"offsets"})
        with self.assertRaises(SystemExit):
            t.install(self.app, apply=True)

    def test_takes_thidranki_from_another_client(self):
        # a later Thidranki that no longer matches Abermenai: refused alone, accepted from the classic client
        other = Path(self.temp.name) / "modern" / "app"
        mpk(other / "zones/zone252/dat252.mpk", "dat252.mpk", {"terrain.pcx": b"live", "offset.pcx": b"live"})
        mpk(other / "zones/zone253/dat253.mpk", "dat253.mpk", {"terrain.pcx": b"heights", "offset.pcx": b"offsets"})
        with self.assertRaises(SystemExit):
            t.install(other, apply=True)
        t.install(other, apply=True, source_app=self.app)
        self.assertEqual((other / "zones/zone253/ter253.mpk").read_bytes(),
                         t.plan(self.app)["zones/zone253/ter253.mpk"])
        t.verify(other, self.app)

    def test_refuses_to_overwrite_other_content(self):
        (self.app / "zones/zone253/ter253.mpk").write_bytes(b"something else")
        with self.assertRaises(SystemExit):
            t.install(self.app, apply=True)

    def test_refuses_while_the_game_runs(self):
        with mock.patch.object(t, "client_running", return_value=True), self.assertRaises(SystemExit):
            t.install(self.app, apply=True)
        self.assertFalse((self.app / "zones/zone253/ter253.mpk").exists())


if __name__ == "__main__":
    unittest.main()
