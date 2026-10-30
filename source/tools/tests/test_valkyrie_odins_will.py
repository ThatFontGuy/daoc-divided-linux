"""Definition-only integration tests; never copies or mutates account/character data."""
import importlib.util,sqlite3,unittest
from pathlib import Path

tools=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,tools/file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
module=load('valkodinswill','valkyrie_odins_will.py')
mending=load('valkmending','valkyrie_mending.py')
progression=load('valkprogress','valkyrie_progression.py')

class ValkyrieOdinsWillTests(unittest.TestCase):
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
        # Start from revision 3 regardless of how far the live test DB has been upgraded.
        with fixture:
            for _,spell_id,_,_,_ in module.planned():fixture.execute('DELETE FROM Spell WHERE SpellID=?',(spell_id,))
            fixture.execute("DELETE FROM LineXSpell WHERE LineXSpell_ID LIKE 'local-valk-ow-%'")
            fixture.execute("UPDATE ServerProperty SET Value='2' WHERE lower(Key)='valkyrie_test_data_version'")
            progression.apply(fixture);mending.apply(fixture)
        cls.fixture=fixture.serialize();fixture.close()

    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.deserialize(self.fixture)

    def tearDown(self):self.c.close()

    def spell(self,name):
        return self.c.execute('SELECT * FROM Spell WHERE Name=? AND PackageID=? ORDER BY SpellID',(name,module.PACKAGE)).fetchall()

    def linked(self):
        return [tuple(r) for r in self.c.execute("SELECT l.Level,s.Name FROM LineXSpell l JOIN Spell s ON s.SpellID=l.SpellID WHERE l.LineName=? ORDER BY l.Level,s.Name",(module.LINE,))]

    def test_line_holds_full_reference_kit(self):
        with self.c:module.apply(self.c)
        rows=self.linked()
        self.assertEqual(len(rows),9+31)
        self.assertIn((43,'Call from Valhalla'),rows)
        self.assertIn((50,"Odin's Temperance"),rows)

    def test_reapply_does_not_duplicate(self):
        with self.c:module.apply(self.c)
        first=self.linked()
        with self.c:module.apply(self.c)
        self.assertEqual(self.linked(),first)

    def test_cones_use_ninety_degree_arc_and_spirit(self):
        with self.c:module.apply(self.c)
        self.c.row_factory=sqlite3.Row
        for name in ["Valhalla's Rage","Odin's Major Retribution",'Vindictive Bite',"Valkyrie's Authority","Odin's Lock"]:
            s=self.spell(name)[0]
            self.assertEqual((s['Target'],s['Range'],s['Radius'],s['DamageType']),('Cone',700,90,15),name)
        s=self.spell("Odin's Major Retribution")[0]
        self.assertEqual((s['Damage'],s['Power'],s['PulsePower'],s['Pulse'],s['Frequency'],s['RecastDelay']),(43.0,-10,-9,1,50,8))
        self.assertEqual((self.spell("Valkyrie's Authority")[0]['Value'],self.spell("Valkyrie's Command")[0]['Value']),(75.0,0.0))
        self.assertEqual((self.spell("Odin's Lock")[0]['Value'],self.spell("Odin's Lock")[0]['Duration']),(80.0,40))

    def test_aura_points_at_owned_spirit_proc(self):
        with self.c:module.apply(self.c)
        self.c.row_factory=sqlite3.Row
        aura,proc=self.spell("Odin's Full Aura")
        self.assertEqual((aura['Type'],aura['Target'],aura['Frequency'],aura['Duration'],aura['Value']),('OffensiveProc','Group',10,600,float(proc['SpellID'])))
        self.assertEqual((proc['Type'],proc['Damage'],proc['DamageType']),('DirectDamage',100.0,15))
        self.assertIsNone(self.c.execute('SELECT 1 FROM LineXSpell WHERE SpellID=?',(proc['SpellID'],)).fetchone())

    def test_faith_is_group_magic_ablative_chant(self):
        with self.c:module.apply(self.c)
        self.c.row_factory=sqlite3.Row
        s=self.spell("Odin's Virtue")[0]
        self.assertEqual((s['Type'],s['Target'],s['Value'],s['Damage'],s['Pulse'],s['Frequency'],s['Duration'],s['RecastDelay']),
                         ('MagicAblativeArmor','Group',90.0,30.0,1,60,6,8))

    def test_damage_ranks_and_tooltips_untouched(self):
        before=[tuple(r) for r in self.c.execute('SELECT * FROM Spell WHERE SpellID BETWEEN 64990 AND 64998 ORDER BY SpellID')]
        with self.c:module.apply(self.c)
        self.assertEqual([tuple(r) for r in self.c.execute('SELECT * FROM Spell WHERE SpellID BETWEEN 64990 AND 64998 ORDER BY SpellID')],before)
        rows=self.c.execute('SELECT SpellID,TooltipId FROM Spell WHERE PackageID=?',(module.PACKAGE,)).fetchall()
        self.assertTrue(all(tip==27000+spell-64990 for spell,tip in rows))

    def test_requires_revision_three(self):
        self.c.execute("UPDATE ServerProperty SET Value='2' WHERE lower(Key)='valkyrie_test_data_version'");self.c.commit()
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)

    def test_collision_rolls_back(self):
        self.c.execute("INSERT INTO Spell(SpellID,Spell_ID,Name) VALUES(65120,'other-feature','Not our spell')");self.c.commit()
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)
        self.assertEqual(self.c.execute('SELECT COUNT(*) FROM Spell WHERE PackageID=?',(module.PACKAGE,)).fetchone()[0],0)
        self.assertEqual(self.c.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='valkyrie_test_data_version'").fetchone()[0],'3')

if __name__=='__main__':unittest.main()
