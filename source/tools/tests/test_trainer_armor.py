"""Definition-only integration tests; never copies or mutates account/character data."""
import importlib.util,sqlite3,unittest
from pathlib import Path

tools=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('trainerarmor',tools/'trainer_armor.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class TrainerArmorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database=tools.parents[1]/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
        if not database.exists():raise unittest.SkipTest('Prepared modern test definitions are required.')
        fixture=sqlite3.connect(':memory:')
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source:
            for table,where in [('Mob',"WHERE ClassType LIKE 'DOL.GS.Trainer.%' OR NPCTemplateID IN (SELECT NPCTemplateID FROM Mob WHERE ClassType LIKE 'DOL.GS.Trainer.%' AND NPCTemplateID>0)"),
                                ('NpcTemplate','WHERE TemplateId IN (SELECT NPCTemplateID FROM Mob WHERE ClassType LIKE \'DOL.GS.Trainer.%\')'),('NPCEquipment','')]:
                fixture.execute(source.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?',(table,)).fetchone()[0])
                data=source.execute(f'SELECT * FROM "{table}" {where}').fetchall()
                if data:fixture.executemany(f'INSERT INTO "{table}" VALUES ('+','.join('?' for _ in data[0])+')',data)
        # Frode the Thane trainer's own NPC template carries the old gear; reset both so the test is independent of the live DB.
        with fixture:
            fixture.execute("UPDATE Mob SET EquipmentTemplateID='MidStuddedChainHammer' WHERE Name='Frode' AND ClassType='DOL.GS.Trainer.ThaneTrainer'")
            fixture.execute("UPDATE NpcTemplate SET EquipmentTemplateID='MidStuddedChainHammer' WHERE TemplateId=(SELECT NPCTemplateID FROM Mob WHERE Name='Frode' AND ClassType='DOL.GS.Trainer.ThaneTrainer')")
        cls.fixture=fixture.serialize();fixture.close()

    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.deserialize(self.fixture)

    def tearDown(self):self.c.close()

    def gear(self,name,class_type):
        return self.c.execute('SELECT m.EquipmentTemplateID,t.EquipmentTemplateID FROM Mob m LEFT JOIN NpcTemplate t ON t.TemplateId=m.NPCTemplateID WHERE m.Name=? AND m.ClassType=?',(name,class_type)).fetchone()

    def test_advanced_trainers_wear_their_class_set_including_npc_template(self):
        with self.c:module.apply(self.c)
        self.assertEqual(tuple(self.gear('Frode','DOL.GS.Trainer.ThaneTrainer')),('thane','thane'))
        wrong=self.c.execute("SELECT COUNT(*) FROM Mob WHERE ClassType='DOL.GS.Trainer.ArmsmanTrainer' AND EquipmentTemplateID<>'armsman'").fetchone()[0]
        self.assertEqual(wrong,0)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM Mob WHERE ClassType='DOL.GS.Trainer.AlbionMaulerTrainer' AND EquipmentTemplateID<>'mauler_alb'").fetchone()[0],0)

    def test_base_and_custom_trainers_are_untouched(self):
        kinds=('Stormforged','Pendragon','Fighter','Acolyte','Mage','Elementalist','Viking','Seer','Mystic','Guardian','Naturalist',
               'Stalker','Forester','Magician','Rogue','AlbionRogue','MidgardRogue','Disciple')
        marks=','.join('?' for _ in kinds)
        query=f'SELECT Mob_ID,EquipmentTemplateID FROM Mob WHERE ClassType IN ({marks})'
        args=['DOL.GS.Trainer.'+k+'Trainer' for k in kinds]
        before=dict(self.c.execute(query,args).fetchall())
        with self.c:module.apply(self.c)
        self.assertTrue(before);self.assertEqual(dict(self.c.execute(query,args).fetchall()),before)

    def test_reapply_changes_nothing(self):
        with self.c:module.apply(self.c)
        with self.c:report=module.apply(self.c)
        self.assertEqual((report['MobsChanged'],report['NpcTemplatesChanged']),([],[]))

    def test_missing_template_rolls_back(self):
        self.c.execute("DELETE FROM NPCEquipment WHERE TemplateID='thane'");self.c.commit()
        before=self.gear('Frode','DOL.GS.Trainer.ThaneTrainer')
        with self.assertRaises(ValueError):
            with self.c:module.apply(self.c)
        self.assertEqual(tuple(self.gear('Frode','DOL.GS.Trainer.ThaneTrainer')),tuple(before))

if __name__=='__main__':unittest.main()
