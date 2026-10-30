from contextlib import closing
import importlib.util
import sqlite3
from pathlib import Path
import unittest,sys,tempfile
from unittest.mock import patch
TOOLS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TOOLS))
import modern_tireless as migration
import install_modern_tireless as installer
ROOT=TOOLS.parents[1];WORLD=ROOT/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
class FreeTirelessTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
  with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as source:
   for table in ['Ability','SpecXAbility','ClassXSpecialization','ClassXRealmAbility_Atlas']:
    self.db.execute(source.execute('select sql from sqlite_master where type="table" and name=?',(table,)).fetchone()[0])
    rows=source.execute('select * from '+table).fetchall()
    if rows:self.db.executemany('insert into '+table+' values ('+','.join('?' for _ in rows[0])+')',rows)
  self.db.commit()
 def tearDown(self):self.db.close()
 def seed(self):
  with self.db:return migration.apply(self.db)
 def test_all_classes_receive_native_tireless_free_at_one(self):
  self.seed()
  row=self.db.execute("select SpecLevel,AbilityLevel,ClassId from SpecXAbility where Spec='CharacterCareer' and AbilityKey='Tireless'").fetchone()
  self.assertEqual(tuple(row),(1,1,0));self.assertTrue(self.db.execute("select 1 from ClassXSpecialization where ClassID=0 and SpecKeyName='CharacterCareer'").fetchone())
  self.assertFalse(self.db.execute("select 1 from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_Tireless'").fetchone())
 def test_idempotent_and_custom_abilities_are_preserved(self):
  custom=[tuple(r) for r in self.db.execute("select * from ClassXRealmAbility_Atlas where AbilityKey like 'Sovereign_%' or AbilityKey like 'Pendragon_%'")]
  self.seed();before=[tuple(r) for r in self.db.execute('select * from SpecXAbility')];self.seed()
  self.assertEqual(before,[tuple(r) for r in self.db.execute('select * from SpecXAbility')]);self.assertEqual(custom,[tuple(r) for r in self.db.execute("select * from ClassXRealmAbility_Atlas where AbilityKey like 'Sovereign_%' or AbilityKey like 'Pendragon_%'")])
 def test_rejects_unexpected_native_handler(self):
  self.db.execute("update Ability set Implementation='Foreign.Handler' where KeyName='Tireless'");self.db.commit()
  with self.assertRaisesRegex(ValueError,'Unexpected'):self.seed()
 def test_installer_is_transactional_preserves_unrelated_trainer_and_progress_data(self):
  with tempfile.TemporaryDirectory(prefix='tireless-install-test-',dir=ROOT/'artifacts') as folder:
   base=Path(folder);root=base/'artifacts/modern-client-test';data=root/'runtime/data';data.mkdir(parents=True);(root/'backups').mkdir()
   world=data/'opendaoc.sqlite3.db'
   self.db.execute('create table Account (Save text)');self.db.execute("insert into Account values ('keep save')")
   self.db.execute('create table NPCEquipment (Sentinel text)');self.db.execute("insert into NPCEquipment values ('Claude armor')");self.db.commit()
   with closing(sqlite3.connect(world)) as dest:self.db.backup(dest)
   build=base/'build';build.mkdir();(build/'GameServer.dll').write_bytes(b'tested-new-server')
   for directory in ['runtime/server','runtime/server/lib','runtime/server/win-x64']:
    p=root/directory;p.mkdir(parents=True,exist_ok=True);(p/'GameServer.dll').write_bytes(b'previous-server')
   with patch.object(installer,'REPO',base),patch.object(installer,'stopped'):
    self.assertTrue(installer.install(root)['preview'])
    result=installer.install(root,True,build_dir=build)
    self.assertEqual(result['progress_tables_verified'],1)
    with closing(sqlite3.connect(world)) as db:
     self.assertEqual(db.execute('select * from Account').fetchall(),[('keep save',)])
     self.assertEqual(db.execute('select * from NPCEquipment').fetchall(),[('Claude armor',)])
    installer.install(root,rollback=Path(result['backup']))
    self.assertEqual((root/'runtime/server/GameServer.dll').read_bytes(),b'previous-server')
    with closing(sqlite3.connect(world)) as db:self.assertEqual(db.execute('select * from Account').fetchall(),[('keep save',)])
    # A concurrent class-creation patch must never receive an older server build.
    source=base/'source/server/GameServer';source.mkdir(parents=True)
    code=source/'ClaudeClassCreation.cs';code.write_text('// newer source')
    import os
    stamp=(build/'GameServer.dll').stat().st_mtime+10
    os.utime(code,(stamp,stamp))
    with self.assertRaisesRegex(ValueError,'source changed'):
     installer.install(root,True,build_dir=build)
    self.assertEqual((root/'runtime/server/GameServer.dll').read_bytes(),b'previous-server')
