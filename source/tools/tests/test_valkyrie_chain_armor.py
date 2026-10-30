"""Definition-only integration tests; never copies or mutates account/character data."""
import importlib.util,sqlite3,unittest
from pathlib import Path

tools=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('valkchain',tools/'valkyrie_chain_armor.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ValkyrieChainArmorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database=tools.parents[1]/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
        if not database.exists():raise unittest.SkipTest('Prepared modern test definitions are required.')
        fixture=sqlite3.connect(':memory:')
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source:
            for table in ['SpecXAbility','StarterEquipment','ItemTemplate','ServerProperty']:
                fixture.execute(source.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?',(table,)).fetchone()[0])
                query='SELECT * FROM "'+table+'"'
                if table=='ServerProperty':query+=" WHERE lower(Key)='valkyrie_test_data_version'"
                if table=='ItemTemplate':query+=" WHERE Id_nb LIKE 'bronze_%'"
                data=source.execute(query).fetchall()
                if data:fixture.executemany('INSERT INTO "'+table+'" VALUES ('+','.join('?' for _ in data[0])+')',data)
        # Start from the revision-4 state regardless of whether the live DB was upgraded.
        with fixture:
            fixture.execute("UPDATE ServerProperty SET Value='4' WHERE lower(Key)='valkyrie_test_data_version'")
            fixture.execute("UPDATE SpecXAbility SET AbilityLevel=3 WHERE Spec='ValkyrieCareer' AND AbilityKey='MidArmor' AND ClassId=34")
            fixture.execute("DELETE FROM StarterEquipment WHERE Class='34;' AND TemplateID LIKE 'bronze_pansarkedja_%'")
            for template in module.STUDDED:
                fixture.execute("UPDATE StarterEquipment SET Class='35;31;22;24;21;32;34;' WHERE TemplateID=? AND Class='35;31;22;24;21;32;'",(template,))
        cls.fixture=fixture.serialize();fixture.close()

    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.deserialize(self.fixture)

    def tearDown(self):self.c.close()

    def starter(self,class_id):
        return sorted(t for t,classes in self.c.execute('SELECT TemplateID,Class FROM StarterEquipment') if class_id in classes.split(';'))

    def test_chain_from_level_one(self):
        with self.c:module.apply(self.c)
        self.assertEqual(self.c.execute("SELECT AbilityLevel FROM SpecXAbility WHERE Spec='ValkyrieCareer' AND AbilityKey='MidArmor' AND SpecLevel=1 AND ClassId=34").fetchone()[0],4)

    def test_valkyrie_starts_in_chain_and_keeps_weapon_and_shield(self):
        warrior=self.starter('22')
        with self.c:module.apply(self.c)
        valk=self.starter('34')
        self.assertTrue(set(module.CHAIN)<=set(valk))
        self.assertFalse(set(module.STUDDED)&set(valk))
        self.assertIn('small_training_shield',valk);self.assertIn('training_sword_mid',valk)
        self.assertEqual(self.starter('22'),warrior)

    def test_reapply_is_stable(self):
        with self.c:module.apply(self.c)
        first=sorted(map(tuple,self.c.execute('SELECT Class,TemplateID FROM StarterEquipment')))
        with self.c:module.apply(self.c)
        self.assertEqual(sorted(map(tuple,self.c.execute('SELECT Class,TemplateID FROM StarterEquipment'))),first)

    def test_requires_revision_four(self):
        self.c.execute("UPDATE ServerProperty SET Value='3' WHERE lower(Key)='valkyrie_test_data_version'");self.c.commit()
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)

if __name__=='__main__':unittest.main()
