"""Parity, isolation, asset references and native selection checks on private copies."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import struct
import unittest
from seed_pendragon import seed, PACKAGE, OFFSET, FX
from install_sovereign import progress
from test_resist_display import offset,run
from patch_pendragon_client import patch,RACES

REPO=Path(__file__).resolve().parents[3]
ROOT=REPO/'artifacts/modern-client-test'
WORLD=ROOT/'runtime/data/opendaoc.sqlite3.db'

def midgard(db):
 result={}
 for table,condition in [('Spell',"PackageID='OfflineDAoC.Stormforged.v1'"),('SpellLine',"KeyName like 'Stormforged.%'"),
  ('Style','ClassId=64'),('StyleXSpell','ClassID=64'),('ClassXSpecialization','ClassID=64'),
  ('SpecXAbility',"Spec='StormforgedCareer'"),('ClassXRealmAbility_Atlas','CharClass=64'),
  ('NpcTemplate','TemplateId between 60171001 and 60171004')]:
  result[table]=sorted(map(tuple,db.execute('select * from '+table+' where '+condition)),key=repr)
 return result

class PendragonTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.db=sqlite3.connect(':memory:');cls.db.row_factory=sqlite3.Row
  with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as src:src.backup(cls.db)
  cls.before=progress(cls.db);cls.midgard=midgard(cls.db)
  with cls.db:cls.result=seed(cls.db)
 def test_reseed_preserves_midgard_and_all_progress(self):
  self.assertEqual(progress(self.db),self.before);self.assertEqual(midgard(self.db),self.midgard)
  with self.db:self.assertEqual(seed(self.db),self.result)
  self.assertEqual(progress(self.db),self.before);self.assertEqual(midgard(self.db),self.midgard)
 def test_every_royal_spell_matches_installed_midgard_power(self):
  for alb in self.db.execute('select * from Spell where PackageID=? and SpellID<64300',(PACKAGE,)):
   mid=self.db.execute('select * from Spell where SpellID=?',(alb['SpellID']-OFFSET,)).fetchone()
   for field in ('Damage','Power','CastTime','RecastDelay','Range','Radius','Duration','Frequency','Target','Type'):
    self.assertEqual(alb[field],mid[field],(alb['Name'],field))
  self.assertEqual(self.result['styles'],42)
  specs=dict(self.db.execute('select SpecKeyName,LevelAcquired from ClassXSpecialization where ClassID=65'))
  for key in ('Slash','Crush','Thrust','Two Handed','Polearm','Shields','Parry','Stealth'):self.assertLess(specs[key],0)
  self.assertEqual(self.db.execute('select count(*) from Style where ClassId=65').fetchone()[0],42)
  self.assertFalse(self.db.execute('select 1 from StyleXSpell x left join Spell s on x.SpellID=s.SpellID where x.ClassID=65 and s.SpellID is null').fetchone())
 def test_realm_abilities_are_separate_and_rr5_is_free_career_granted(self):
  private=list(self.db.execute("select AbilityKey from ClassXRealmAbility_Atlas where CharClass=65 and AbilityKey like 'Pendragon_%'"))
  self.assertEqual(len(private),4)
  for key, in private:
   self.assertFalse(self.db.execute('select 1 from ClassXRealmAbility_Atlas where AbilityKey=? and CharClass<>65',(key,)).fetchone())
  self.assertFalse(self.db.execute('select 1 from LineXSpell where SpellID=64560').fetchone())
  self.assertEqual(self.db.execute('select Duration,Damage,Radius from Spell where SpellID=64560').fetchone()[:],(20,300,500))
 def test_asset_references_exist_and_starter_items_are_present(self):
  import os,sys
  os.environ['OFFLINE_DAOC_CLIENT']=str(ROOT/'runtime/client-modern/app')
  sys.path.insert(0,str(REPO/'tools/pet-art'));import daoc_catalog as c
  data=c.gamedata();effects={int(r[0]) for r in c.csv_rows(data,'spells.csv') if r and r[0].isdigit()}
  for effect, in self.db.execute('select distinct ClientEffect from Spell where PackageID=?',(PACKAGE,)):
   if effect:self.assertIn(effect,effects)
  models={int(r[0]) for r in c.csv_rows(data,'monsters.csv') if r and r[0].isdigit()}
  for model in (100,1193):self.assertIn(model,models)
  self.assertFalse(self.db.execute("select 1 from StarterEquipment s left join ItemTemplate i on s.TemplateID=i.Id_nb where s.Class='65' and i.Id_nb is null").fetchone())
 def test_native_patch_replays_all_albion_races_and_preserves_midgard_resists(self):
  original=(ROOT/'backups/client-bundle-20261021-165832-708287/game.original.dll').read_bytes()
  data=patch(original)
  self.assertIn(b'Pendragon Sovereign\0',data);self.assertIn(b'Storm Sovereign\0',data)
  with self.assertRaises(ValueError):patch(data)
  at=offset(data,0x5b0b19);self.assertEqual(data[at],0xe9)
  race_va=0x5b0b1e+struct.unpack_from('<i',data,at+1)[0];pc=offset(data,race_va);start=pc
  self.assertEqual(data[pc],0x58);pc+=1 # balances pointer already pushed by original code
  for race in RACES:
   self.assertEqual(data[pc:pc+3],bytes.fromhex('c745ec'))
   self.assertEqual(struct.unpack_from('<I',data,pc+3)[0],race)
   self.assertEqual(data[pc+7:pc+13],bytes.fromhex('8d45ec 50 89f0'))
   self.assertEqual(data[pc+13],0xe8)
   self.assertEqual(race_va+pc-start+18+struct.unpack_from('<i',data,pc+14)[0],0x5b440d)
   pc+=18
  self.assertEqual(data[pc],0xe9)
  self.assertEqual(race_va+pc-start+5+struct.unpack_from('<i',data,pc+1)[0],0x5b0b57)
  for index in range(9):self.assertEqual(run(data,24,3,10,index),(0xd4934c+4*index,34))
 def test_guarded_installer_and_rollback_preserve_saved_progress(self):
  import tempfile,shutil
  from unittest.mock import patch as mock
  from install_pendragon import install
  with tempfile.TemporaryDirectory(prefix='pendragon-test-',dir=REPO/'artifacts') as folder:
   target=Path(folder)
   self.assertTrue(target.resolve().is_relative_to((REPO/"artifacts").resolve()))
   files=['runtime/client-modern/app/game.dll','runtime/modern-client.json','backups/client-bundle-20261021-165832-708287/game.original.dll']
   files += [d+'/GameServer.dll' for d in ('runtime/server','runtime/server/lib','runtime/server/win-x64')]
   for rel in files:
    (target/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,target/rel)
   db=target/'runtime/data/opendaoc.sqlite3.db';db.parent.mkdir(parents=True)
   with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(db)) as dest:src.backup(dest)
   hashes={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [db]+[target/r for r in files]}
   with mock('install_pendragon.stopped'):
    result=install(target,apply=True);self.assertTrue(result['verified']);self.assertEqual(result['progress_tables_verified'],37)
    install(target,rollback=Path(result['backup']))
   for rel,digest in hashes.items():self.assertEqual(hashlib.sha256((target/rel).read_bytes()).hexdigest(),digest)

if __name__=='__main__':unittest.main()
