"""Definition-only integration tests; never copies or mutates account/character data."""
import importlib.util,sqlite3,unittest
from pathlib import Path

tools=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('valkicons',tools/'valkyrie_icons.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ValkyrieIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database=tools.parents[1]/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
        if not database.exists():raise unittest.SkipTest('Prepared modern test definitions are required.')
        fixture=sqlite3.connect(':memory:')
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source:
            for table,where in [('Spell',"WHERE Spell_ID LIKE 'local-valk-%' OR SpellID IN (1371,1372,3031,2951,3001)"),('ServerProperty',"WHERE lower(Key)='valkyrie_test_data_version'")]:
                fixture.execute(source.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?',(table,)).fetchone()[0])
                data=source.execute(f'SELECT * FROM "{table}" {where}').fetchall()
                if data:fixture.executemany(f'INSERT INTO "{table}" VALUES ('+','.join('?' for _ in data[0])+')',data)
        # Reset to the borrowed placeholder art so the test does not depend on the live DB's state.
        with fixture:fixture.execute("UPDATE Spell SET Icon=2951,ClientEffect=2951 WHERE Spell_ID LIKE 'local-valk-%'")
        cls.fixture=fixture.serialize();fixture.close()

    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.deserialize(self.fixture)

    def tearDown(self):self.c.close()

    def art(self,name):
        return tuple(self.c.execute("SELECT Icon,ClientEffect FROM Spell WHERE Name=? AND Spell_ID LIKE 'local-valk-%' ORDER BY SpellID",(name,)).fetchone())

    def test_live_icons_from_reference(self):
        with self.c:module.apply(self.c)
        self.assertEqual(self.art("Odin's Heel"),(12509,12509))
        self.assertEqual(self.art("Valhalla's Scorn"),(12525,12525))
        self.assertEqual(self.art("Odin's Faith"),(14810,14810))
        self.assertEqual(self.art("Odin's Antidote"),(4411,4411))
        proc=self.c.execute("SELECT Icon FROM Spell WHERE Spell_ID='local-valk-ow-aura-proc-100'").fetchone()[0]
        self.assertEqual(proc,12554)
        self.assertEqual(self.art('Ragnarok Effect'),(14326,14326))
        self.assertEqual(self.art("Gungnir's Fury Effect"),(14329,14329))
        self.assertEqual(self.art('Roundhouse Effect'),(14323,14323))

    def test_shared_stock_rows_and_tooltips_untouched(self):
        stock='SELECT * FROM Spell WHERE SpellID IN (1371,1372,3031,2951,3001) ORDER BY SpellID'
        tooltips="SELECT SpellID,TooltipId FROM Spell WHERE Spell_ID LIKE 'local-valk-%' ORDER BY SpellID"
        rows=lambda query:[tuple(r) for r in self.c.execute(query)]
        before,tips=rows(stock),rows(tooltips)
        with self.c:module.apply(self.c)
        self.assertEqual(rows(stock),before)
        self.assertEqual(rows(tooltips),tips)

    def test_reapply_changes_nothing(self):
        with self.c:module.apply(self.c)
        with self.c:self.assertEqual(module.apply(self.c)['Changed'],[])

    def test_renamed_spell_rolls_back(self):
        self.c.execute("UPDATE Spell SET Name='Something else' WHERE SpellID=65135");self.c.commit()
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)
        self.assertEqual(self.art("Odin's Heel"),(2951,2951))

if __name__=='__main__':unittest.main()
