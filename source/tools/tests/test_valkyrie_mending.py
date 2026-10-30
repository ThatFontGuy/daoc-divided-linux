"""Definition-only integration tests; never copies or mutates account/character data."""
import importlib.util,sqlite3,unittest
from pathlib import Path

tools=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,tools/file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
module=load('valkmending','valkyrie_mending.py')
progression=load('valkprogress','valkyrie_progression.py')

class ValkyrieMendingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database=tools.parents[1]/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
        if not database.exists():raise unittest.SkipTest('Prepared modern test definitions are required.')
        fixture=sqlite3.connect(':memory:')
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source:
            for table in ['Spell','SpellLine','Specialization','ClassXSpecialization','LineXSpell','Mob','ServerProperty']:
                fixture.execute(source.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?',(table,)).fetchone()[0])
                query='SELECT * FROM "'+table+'"'
                if table=='Mob':query+=" WHERE Mob_ID IN ('"+progression.REFERENCE_TRAINER+"','"+progression.TRAINER+"')"
                if table=='ServerProperty':query+=" WHERE lower(Key)='valkyrie_test_data_version'"
                data=source.execute(query).fetchall()
                if data:fixture.executemany('INSERT INTO "'+table+'" VALUES ('+','.join('?' for _ in data[0])+')',data)
        fixture.commit()
        # Start every test from revision 2 so the fixture does not depend on whether the live DB was upgraded.
        with fixture:
            for _,spell_id,_,_,_,_ in module.planned():fixture.execute('DELETE FROM Spell WHERE SpellID=?',(spell_id,))
            fixture.execute("DELETE FROM LineXSpell WHERE LineXSpell_ID LIKE 'local-valk-mend-%'")
            fixture.execute('DELETE FROM SpellLine WHERE KeyName=?',(module.BASELINE,))
            progression.apply(fixture)
        cls.fixture=fixture.serialize();fixture.close()

    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.deserialize(self.fixture)

    def tearDown(self):self.c.close()

    def line(self,name):
        return [tuple(r) for r in self.c.execute('SELECT l.Level,s.Name,s.Type,s.Target,s.Value,s.Power,s.CastTime,s.Range,s.Radius,s.Duration,s.Frequency,s.RecastDelay '
                                               'FROM LineXSpell l JOIN Spell s ON s.SpellID=l.SpellID WHERE l.LineName=? ORDER BY l.Level,s.Name',(name,))]

    def test_reapply_does_not_duplicate(self):
        with self.c:module.apply(self.c)
        first=self.line(module.BASELINE)+self.line(module.SPEC_LINE)
        with self.c:module.apply(self.c)
        self.assertEqual(self.line(module.BASELINE)+self.line(module.SPEC_LINE),first)
        self.assertEqual(self.c.execute('SELECT COUNT(*) FROM SpellLine WHERE KeyName=?',(module.BASELINE,)).fetchone()[0],1)

    def test_baseline_is_class_hinted_and_complete(self):
        with self.c:module.apply(self.c)
        self.assertEqual(tuple(self.c.execute('SELECT Spec,IsBaseLine,ClassIDHint FROM SpellLine WHERE KeyName=?',(module.BASELINE,)).fetchone()),('Mending',1,34))
        rows=self.line(module.BASELINE)
        self.assertEqual(len(rows),27)
        self.assertIn((3,'Cure Poison','CurePoison','Realm',0.0,-6,3.2,1500,0,0,0,0),rows)
        self.assertIn((46,'Emendation','Heal','Realm',231.0,29,2.8,2000,0,0,0,0),rows)
        self.assertIn((45,'Group Emendation','Heal','Group',93.0,19,2.0,2000,0,0,0,0),rows)
        self.assertNotIn('Minor Refinement',[r[1] for r in rows])

    def test_spec_kit_values(self):
        with self.c:module.apply(self.c)
        rows=self.line(module.SPEC_LINE)
        self.assertEqual(len(rows),32)
        self.assertIn((35,'Redeem from Valhalla','Resurrect','Corpse',0.0,-25,0.0,1500,0,0,0,300),rows)
        self.assertIn((20,"Odin's Elixir",'HealOverTime','Realm',40.0,40,0.0,2000,0,10,20,10),rows)
        self.assertIn((45,"Odin's Greater Elixir",'HealthRegenBuff','Realm',95.0,75,0.0,2000,0,10,0,10),rows)
        self.assertIn((47,"Valkyrie's Remedy",'HealthRegenBuff','Group',55.0,55,3.0,2000,0,15,0,0),rows)
        self.assertIn((50,"Odin's Emendation",'Heal','Realm',500.0,99,0.0,0,350,0,0,15),rows)
        rez=self.c.execute("SELECT ResurrectHealth,ResurrectMana FROM Spell WHERE Name='Redeem from Valhalla'").fetchone()
        self.assertEqual(tuple(rez),(25,25))

    def test_copies_get_their_own_tooltips(self):
        with self.c:module.apply(self.c)
        rows=self.c.execute("SELECT SpellID,TooltipId FROM Spell WHERE PackageID=?",(module.PACKAGE,)).fetchall()
        self.assertTrue(rows)
        self.assertTrue(all(tip==27000+spell-64990 for spell,tip in rows))
        tips=[tip for _,tip in rows]
        self.assertEqual(self.c.execute(f"SELECT COUNT(*) FROM Spell WHERE TooltipId IN ({','.join('?' for _ in tips)}) AND PackageID<>?",tips+[module.PACKAGE]).fetchone()[0],0)

    def test_shared_lines_are_unchanged(self):
        def snapshot():
            return [tuple(r) for r in self.c.execute("SELECT s.* FROM LineXSpell l JOIN Spell s ON s.SpellID=l.SpellID WHERE l.LineName IN ('Mending','Shaman Mend Spec','Healer Mending Spec') ORDER BY s.SpellID,l.LineName")]
        before=snapshot()
        with self.c:module.apply(self.c)
        self.assertEqual(snapshot(),before)

    def test_requires_revision_two(self):
        self.c.execute("UPDATE ServerProperty SET Value='1' WHERE lower(Key)='valkyrie_test_data_version'");self.c.commit()
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)

    def test_collision_rolls_back(self):
        self.c.execute("INSERT INTO Spell(SpellID,Spell_ID,Name) VALUES(65040,'other-feature','Not our spell')");self.c.commit()
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)
        self.assertIsNone(self.c.execute('SELECT 1 FROM SpellLine WHERE KeyName=?',(module.BASELINE,)).fetchone())
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM Spell WHERE PackageID=?",(module.PACKAGE,)).fetchone()[0],0)

if __name__=='__main__':unittest.main()
