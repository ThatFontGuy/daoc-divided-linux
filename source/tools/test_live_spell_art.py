"""Read-only check of the client-art step (live_spell_art.py) on a private copy of the modern test world."""
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest
import live_spell_art as a

WORLD = Path(__file__).resolve().parents[2] / 'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'


class LiveSpellArtTests(unittest.TestCase):
    def test_named_spells_take_the_client_art_and_reapplying_is_stable(self):
        if not WORLD.is_file():
            self.skipTest('Modern test world is not available')
        db = sqlite3.connect(':memory:')
        with closing(sqlite3.connect(WORLD.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            src.backup(db)
        with db:
            first = a.apply(db)
            self.assertEqual(a.apply(db), first)
        self.assertEqual(a.ART['Acid Shot 1'], 7445)  # Codex's worked example: spells.csv line 3846
        rows = db.execute("select ClientEffect, Icon from Spell where Name='Acid Shot 1' and PackageID like 'local-%-live-v1'").fetchall()
        self.assertTrue(rows and all(r == (7445, 7445) for r in rows))


if __name__ == '__main__':
    unittest.main()
