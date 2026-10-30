"""Definition-only trainer import and saved-progress installer regression checks."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
TOOLS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TOOLS))
import import_expansion_trainers as migration
import install_expansion_trainers as installer
import valkyrie_progression
ROOT=TOOLS.parents[1];WORLD=ROOT/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
class ExpansionTrainerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with closing(sqlite3.connect(':memory:')) as fixture,closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as source:
   for table in ['Mob','NPCEquipment','Regions','Zones','Spell','SpellLine','Specialization','ClassXSpecialization','LineXSpell','ServerProperty']:
    fixture.execute(source.execute('select sql from sqlite_master where type="table" and name=?',(table,)).fetchone()[0])
    query='select * from "'+table+'"'
    if table=='Mob':query+=" where coalesce(PackageID,'')<>'OfflineDAoC.ExpansionTrainers.EoD.v1'"
    if table=='ServerProperty':query+=" where lower(Key)='valkyrie_test_data_version'"
    rows=source.execute(query).fetchall()
    if rows:fixture.executemany('insert into "'+table+'" values ('+','.join('?' for _ in rows[0])+')',rows)
   if not fixture.execute('select 1 from Mob where Mob_ID=?',(migration.TEMPORARY_VALKYRIE,)).fetchone():
    fixture.row_factory=sqlite3.Row
    reference=dict(fixture.execute('select * from Mob where Mob_ID=?',(valkyrie_progression.REFERENCE_TRAINER,)).fetchone())
    reference.update(Mob_ID=migration.TEMPORARY_VALKYRIE,Name='Valkyrie Trainer',Guild='Valkyrie Trainer',ClassType='DOL.GS.Trainer.ValkyrieTrainer',NPCTemplateID=0,AggroLevel=0)
    fixture.execute('insert into Mob ('+','.join('"'+k+'"' for k in reference)+') values ('+','.join('?' for _ in reference)+')',list(reference.values()))
   fixture.commit();cls.snapshot=fixture.serialize()
 def setUp(self):self.db=sqlite3.connect(':memory:');self.db.deserialize(self.snapshot);self.db.row_factory=sqlite3.Row
 def tearDown(self):self.db.close()
 def apply(self):
  with self.db:return migration.apply(self.db)
 def stable(self):
  rows=[tuple(r) for r in self.db.execute("select * from Mob where coalesce(PackageID,'')<>? and Mob_ID<>?",(migration.PACKAGE,migration.TEMPORARY_VALKYRIE))]
  return hashlib.sha256(repr(sorted(rows,key=repr)).encode()).hexdigest()
 def test_imports_exact_trainers_without_touching_other_spawns_and_reapplies(self):
  before=self.stable();result=self.apply();self.assertEqual(result['added'],94)
  self.assertEqual(self.stable(),before)
  self.assertEqual(dict(self.db.execute('select Guild,count(*) from Mob where PackageID=? group by Guild',(migration.PACKAGE,)).fetchall()),{'Valkyrie Trainer':13,'Warlock Trainer':13,'Vampiir Trainer':14,'Bainshee Trainer':14,'Heretic Trainer':12,'Mauler Trainer':28})
  self.assertFalse(self.db.execute('select 1 from Mob where Mob_ID=?',(migration.TEMPORARY_VALKYRIE,)).fetchone())
  again=self.apply();self.assertEqual(again['added'],0);self.assertEqual(again['already_installed'],94)
 def test_locations_and_appearances_are_preserved_but_scripts_are_valid(self):
  self.apply();sources=migration.source_rows()
  source_text='\n'.join(p.read_text(encoding='utf-8-sig') for p in (ROOT/'source/server/GameServer/trainer').rglob('*.cs'))
  for row in sources:
   actual=self.db.execute('select * from Mob where Mob_ID=?',(row['Mob_ID'],)).fetchone()
   for col in ['Name','X','Y','Z','Heading','Region','Realm','Model','Size','EquipmentTemplateID']:self.assertEqual(actual[col],row[col])
   self.assertIn('class '+actual['ClassType'].rsplit('.',1)[1]+' ',source_text)
   self.assertEqual(actual['NPCTemplateID'],0);self.assertEqual(actual['AggroLevel'],0)
   self.assertNotIn(actual['ClassType'],['DOL.GS.GameNPC','DOL.GS.Trainer.MaulerTrainer'])
 def test_missing_equipment_rolls_back_and_keeps_temporary_trainer(self):
  template=next(r['EquipmentTemplateID'] for r in migration.source_rows() if r['EquipmentTemplateID'])
  self.db.execute('delete from NPCEquipment where TemplateID=?',(template,));self.db.commit()
  count=self.db.execute('select count(*) from Mob').fetchone()[0]
  with self.assertRaisesRegex(ValueError,'equipment'):self.apply()
  self.assertEqual(count,self.db.execute('select count(*) from Mob').fetchone()[0])
 def test_reapply_refuses_to_overwrite_later_trainer_edits(self):
  self.apply();row=migration.source_rows()[0]
  self.db.execute('update Mob set X=X+100 where Mob_ID=?',(row['Mob_ID'],));self.db.commit()
  with self.assertRaisesRegex(ValueError,'collision'):self.apply()
  self.assertEqual(self.db.execute('select X from Mob where Mob_ID=?',(row['Mob_ID'],)).fetchone()[0],row['X']+100)
 def test_equivalent_existing_spawn_is_not_duplicated(self):
  self.apply();row=migration.source_rows()[0]
  self.db.execute('update Mob set Mob_ID=?,PackageID=? where Mob_ID=?',('other-installed-trainer','other-package',row['Mob_ID']));self.db.commit()
  result=self.apply();self.assertEqual(result['equivalent_existing'],1);self.assertEqual(result['added'],0)
 def test_old_valkyrie_setup_does_not_restore_temporary_trainer(self):
  self.apply()
  with self.db:valkyrie_progression.apply(self.db)
  self.assertFalse(self.db.execute('select 1 from Mob where Mob_ID=?',(migration.TEMPORARY_VALKYRIE,)).fetchone())
 def test_installer_preserves_progress_and_guarded_rollback(self):
  with tempfile.TemporaryDirectory(prefix='trainer-test-',dir=ROOT/'artifacts') as folder:
   base=Path(folder);root=base/'artifacts/modern-client-test';data=root/'runtime/data';data.mkdir(parents=True);(root/'backups').mkdir()
   database=data/'opendaoc.sqlite3.db'
   self.db.execute('create table Account (TestSentinel text)');self.db.execute("insert into Account values ('saved progress')");self.db.commit()
   with closing(sqlite3.connect(database)) as dest:self.db.backup(dest)
   before=database.read_bytes()
   with patch.object(installer,'REPO',base),patch.object(installer,'stopped'):
    self.assertTrue(installer.install(root)['preview']);self.assertEqual(before,database.read_bytes())
    result=installer.install(root,True);self.assertEqual(result['progress_tables_verified'],1)
    installed=database.read_bytes()
    with closing(sqlite3.connect(database)) as db,db:
     self.assertEqual(db.execute('select * from Account').fetchall(),[('saved progress',)])
     db.execute("insert into Account values ('newer progress')")
    with self.assertRaisesRegex(ValueError,'progress changed'):installer.install(root,rollback=Path(result['backup']))
    database.write_bytes(installed);installer.install(root,rollback=Path(result['backup']))
    self.assertEqual(before,database.read_bytes())
