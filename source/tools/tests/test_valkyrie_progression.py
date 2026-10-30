"""Definition-only integration tests; never copies or mutates account/character data."""
import importlib.util,sqlite3,unittest
from pathlib import Path

tool=Path(__file__).resolve().parents[1]/'valkyrie_progression.py'
spec=importlib.util.spec_from_file_location('valkprogress',tool);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ValkyrieProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database=tool.parents[2]/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
        if not database.exists():raise unittest.SkipTest('Prepared modern test definitions are required.')
        fixture=sqlite3.connect(':memory:')
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source:
            for table in ['Spell','SpellLine','Specialization','ClassXSpecialization','LineXSpell','Mob','ServerProperty']:
                fixture.execute(source.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?',(table,)).fetchone()[0])
                query='SELECT * FROM "'+table+'"'
                if table=='Mob':query+=" WHERE Mob_ID IN ('"+module.REFERENCE_TRAINER+"','"+module.TRAINER+"')"
                if table=='ServerProperty':query+=" WHERE lower(Key)='valkyrie_test_data_version'"
                data=source.execute(query).fetchall()
                if data:fixture.executemany('INSERT INTO "'+table+'" VALUES ('+','.join('?' for _ in data[0])+')',data)
        fixture.commit();cls.fixture=fixture.serialize();fixture.close()

    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.deserialize(self.fixture)

    def tearDown(self):self.c.close()

    def test_reapply_does_not_duplicate_ranks_or_trainer(self):
        with self.c:module.apply(self.c)
        with self.c:module.apply(self.c)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM LineXSpell WHERE LineXSpell_ID LIKE 'local-valk-native-dd-%'").fetchone()[0],9)
        self.assertEqual(self.c.execute('SELECT COUNT(*) FROM Mob WHERE Mob_ID=?',(module.TRAINER,)).fetchone()[0],1)

    def test_ranks_use_spec_progression_and_shared_cooldown(self):
        with self.c:module.apply(self.c)
        data=self.c.execute("SELECT l.Level,s.Damage,s.Power,s.DamageType,s.RecastDelay,s.SharedTimerGroup FROM LineXSpell l JOIN Spell s ON s.SpellID=l.SpellID WHERE l.LineXSpell_ID LIKE 'local-valk-native-dd-%' ORDER BY l.Level").fetchall()
        self.assertEqual([tuple(x) for x in data],[(level,float(damage),power,15,20,64990) for level,_,damage,power in module.RANKS])
        self.assertEqual(self.c.execute('SELECT IsBaseLine FROM SpellLine WHERE KeyName=?',(module.NATIVE,)).fetchone()[0],0)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM ClassXSpecialization WHERE ClassID=34 AND SpecKeyName='LocalValkyrieSpells'").fetchone()[0],0)

    def test_shared_baseline_heal_is_unchanged(self):
        before=tuple(self.c.execute('SELECT * FROM Spell WHERE SpellID=3001').fetchone())
        with self.c:module.apply(self.c)
        self.assertEqual(tuple(self.c.execute('SELECT * FROM Spell WHERE SpellID=3001').fetchone()),before)
        self.assertTrue(self.c.execute("SELECT 1 FROM LineXSpell WHERE LineName='Mending' AND SpellID=3001").fetchone())

    def test_ranks_get_own_tooltips_and_never_roll_back_revision(self):
        self.c.execute("UPDATE ServerProperty SET Value='4' WHERE lower(Key)='valkyrie_test_data_version'");self.c.commit()
        with self.c:module.apply(self.c)
        self.assertEqual([r[0] for r in self.c.execute('SELECT TooltipId FROM Spell WHERE SpellID BETWEEN 64990 AND 64998 ORDER BY SpellID')],list(range(27000,27009)))
        self.assertEqual(self.c.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='valkyrie_test_data_version'").fetchone()[0],'4')

    def test_collision_rolls_back_partial_updates(self):
        # Simulate another feature owning a reserved rank ID in a private fixture.
        self.c.execute('DELETE FROM Spell WHERE SpellID=64991')
        self.c.execute("INSERT INTO Spell(SpellID,Spell_ID,Name) VALUES(64991,'other-feature','Not our spell')");self.c.commit()
        before=tuple(self.c.execute('SELECT * FROM Spell WHERE SpellID=64990').fetchone())
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)
        self.assertEqual(tuple(self.c.execute('SELECT * FROM Spell WHERE SpellID=64990').fetchone()),before)

if __name__=='__main__':unittest.main()
