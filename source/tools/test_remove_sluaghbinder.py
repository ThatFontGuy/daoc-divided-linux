"""Read-only checks of the Sluaghbinder removal on a private copy of the modern test world."""
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest
import remove_sluaghbinder as r

WORLD = Path(__file__).resolve().parents[2] / 'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'


class RemoveSluaghbinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORLD.is_file():
            raise unittest.SkipTest('Modern test world is not available')
        cls.db = sqlite3.connect(':memory:')
        with closing(sqlite3.connect(WORLD.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            src.backup(cls.db)
        cls.stock_mobs = cls.db.execute("select count(*) from Mob where Name like '%sluagh%'").fetchone()[0]
        with cls.db:
            cls.result = r.apply(cls.db)

    def count(self, sql, *args):
        return self.db.execute(sql, args).fetchone()[0]

    def test_custom_rows_are_gone(self):
        self.assertEqual(self.count('select count(*) from Spell where SpellID between 59000 and 59111'), 0)
        self.assertEqual(self.count('select count(*) from SpellLine where ClassIDHint=63'), 0)
        self.assertEqual(self.count("select count(*) from Specialization where KeyName like '%Sluagh%' or KeyName='Cairn Oath'"), 0)
        for table, column in (('Style', 'ClassId'), ('ClassXRealmAbility_Atlas', 'CharClass'), ('StartupLocation', 'ClassID'),
                              ('offline_level50_loadouts', 'ClassId')):
            self.assertEqual(self.count(f'select count(*) from {table} where {column}=63'), 0, table)
        self.assertEqual(self.count("select count(*) from ItemTemplate where Id_nb like 'sluagh!_%' escape '!'"), 0)
        self.assertEqual(self.count("select count(*) from NpcTemplate where PackageID='Sluaghbinder_Pets'"), 0)
        self.assertEqual(self.count("select count(*) from Ability where KeyName='AtlasOF_CripplingPlague'"), 0)

    def test_stock_monsters_and_other_lines_stay(self):
        self.assertEqual(self.count("select count(*) from Mob where Name like '%sluagh%'"), self.stock_mobs)
        self.assertGreater(self.stock_mobs, 0)
        self.assertFalse(self.db.execute('select 1 from LineXSpell l left join Spell s on s.SpellID=l.SpellID where s.SpellID is null '
                                         'and l.SpellID between 59000 and 59111').fetchone())

    def test_reapplying_changes_nothing(self):
        with self.db:
            self.assertEqual(r.apply(self.db), dict(sluaghbinder_removed={}))


if __name__ == '__main__':
    unittest.main()
