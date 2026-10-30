"""Read-only checks of the class proc buffs (proc_lines.py) on a private copy of the modern test world."""
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest
import proc_lines as p

WORLD = Path(__file__).resolve().parents[2] / 'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'


class ProcLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORLD.is_file():
            raise unittest.SkipTest('Modern test world is not available')
        cls.db = sqlite3.connect(':memory:'); cls.db.row_factory = sqlite3.Row
        with closing(sqlite3.connect(WORLD.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            src.backup(cls.db)
        with cls.db:
            cls.result = p.apply(cls.db)

    def parent(self, name):
        return self.db.execute('select s.*, l.LineName, l.Level as LineLevel from Spell s join LineXSpell l on l.SpellID=s.SpellID '
                               'where s.Name=? and s.PackageID=?', (name, p.PACKAGE)).fetchone()

    def child(self, parent):
        return self.db.execute('select * from Spell where SpellID=?', (int(parent['Value']),)).fetchone()

    def test_each_parent_fires_its_child_at_the_live_chance(self):
        heresy = self.parent('Protection from Heresy')
        self.assertEqual((heresy['Type'], heresy['Frequency'], heresy['Target'], heresy['LineName']), ('DefensiveProc', 25, 'Group', 'Friar Enhancement Spec'))
        self.assertEqual((self.child(heresy)['Type'], self.child(heresy)['Value'], self.child(heresy)['Target']), ('Heal', 100, 'Self'))
        dogma = self.parent("Prophet's Dogma")
        self.assertEqual((dogma['Type'], dogma['Duration'], dogma['RecastDelay'], self.child(dogma)['Target']), ('OffensiveProc', 30, 30, 'Group'))
        curator = self.parent("Nature's Sentinel")
        self.assertEqual((self.child(curator)['Value'], self.child(curator)['Radius'], self.child(curator)['Target']), (125, 250, 'Realm'))
        blows = self.parent('Banishing Blows')
        self.assertEqual((blows['Frequency'], self.child(blows)['Type'], self.child(blows)['Value'], self.child(blows)['Duration']),
                         (10, 'EnergyResistDebuff', 24, 10))
        self.assertEqual(self.parent('Battlesong of Apotheosis')['LineName'], 'Bard Nurture Spec')

    def test_children_sit_in_no_line_and_reapplying_is_stable(self):
        children = self.db.execute('select count(*) from Spell s where s.PackageID=? and not exists (select 1 from LineXSpell l where l.SpellID=s.SpellID)',
                                   (p.PACKAGE,)).fetchone()[0]
        self.assertEqual(children, self.result['proc_children'])
        with self.db:
            self.assertEqual(p.apply(self.db), self.result)
        tooltips = [r['TooltipId'] for r in self.db.execute('select TooltipId from Spell where PackageID=?', (p.PACKAGE,))]
        self.assertTrue(all(t <= 32767 for t in tooltips))
        self.assertFalse(any(p.RESERVED_TOOLTIPS[0] <= t <= p.RESERVED_TOOLTIPS[1] for t in tooltips), "the Death Knight's tooltip block stays free")


if __name__ == '__main__':
    unittest.main()
