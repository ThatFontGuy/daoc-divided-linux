"""Parity, isolation, asset references and installer checks on private copies of the modern test world."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import unittest
from seed_tuatha import seed, PACKAGE, OFFSET, COMPANION_MODEL, CROWN_MODEL, CLASS
from install_sovereign import progress

REPO=Path(__file__).resolve().parents[3]
ROOT=REPO/'artifacts/modern-client-test'
WORLD=ROOT/'runtime/data/opendaoc.sqlite3.db'

def others(db):
 """Every Midgard and Albion royal row; the Tuatha seed must not change any of them."""
 result={}
 for table,condition in [('Spell',"PackageID in ('OfflineDAoC.Stormforged.v1','OfflineDAoC.Pendragon.v1')"),
  ('SpellLine',"KeyName like 'Stormforged.%' or KeyName like 'Pendragon.%'"),('Style','ClassId in (64,65)'),
  ('StyleXSpell','ClassID in (64,65)'),('ClassXSpecialization','ClassID in (63,64,65,66)'),
  ('SpecXAbility',"Spec in ('StormforgedCareer','PendragonCareer')"),('ClassXRealmAbility_Atlas','CharClass in (64,65,66)'),
  ('NpcTemplate','TemplateId between 60171001 and 60172001')]:
  result[table]=sorted(map(tuple,db.execute('select * from '+table+' where '+condition)),key=repr)
 return result

class TuathaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.db=sqlite3.connect(':memory:');cls.db.row_factory=sqlite3.Row
  with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as src:src.backup(cls.db)
  cls.before=progress(cls.db);cls.others=others(cls.db)
  with cls.db:cls.result=seed(cls.db)
 def test_reseed_preserves_other_realms_and_all_progress(self):
  self.assertEqual(progress(self.db),self.before);self.assertEqual(others(self.db),self.others)
  with self.db:self.assertEqual(seed(self.db),self.result)
  self.assertEqual(progress(self.db),self.before);self.assertEqual(others(self.db),self.others)
 def test_every_royal_spell_matches_installed_midgard_power(self):
  for hib in self.db.execute('select * from Spell where PackageID=? and SpellID<73300',(PACKAGE,)):
   mid=self.db.execute('select * from Spell where SpellID=?',(hib['SpellID']-OFFSET,)).fetchone()
   for field in ('Damage','Power','CastTime','RecastDelay','Range','Radius','Duration','Frequency','Target','Type'):
    self.assertEqual(hib[field],mid[field],(hib['Name'],field))
   self.assertEqual(hib['DamageType'],15,hib['Name'])
  low,high=self.db.execute('select min(TooltipId),max(TooltipId) from Spell where PackageID=?',(PACKAGE,)).fetchone()
  self.assertGreaterEqual(low,25000);self.assertLessEqual(high,32767,'client reads tooltip IDs as signed 16-bit')
  self.assertEqual(self.db.execute('select count(*) from Spell where TooltipId between ? and ? and PackageID<>?',(low,high,PACKAGE)).fetchone()[0],0)
  self.assertEqual(self.result['styles'],42)
  specs=dict(self.db.execute('select SpecKeyName,LevelAcquired from ClassXSpecialization where ClassID=?',(CLASS,)))
  for key in ('Blades','Blunt','Piercing','Large Weapons','Celtic Spear','Shields','Parry','Stealth'):self.assertLess(specs[key],0)
  self.assertEqual(self.db.execute('select count(*) from Style where ClassId=?',(CLASS,)).fetchone()[0],42)
  self.assertEqual(self.db.execute('select min(StyleID),max(StyleID) from Style where ClassId=?',(CLASS,)).fetchone()[:],(6700,6741))
  self.assertFalse(self.db.execute('select 1 from Style where StyleID between 6600 and 6699 and ClassId<>66').fetchone(),'Death Knight StyleID block')
  self.assertFalse(self.db.execute('select 1 from StyleXSpell x left join Spell s on x.SpellID=s.SpellID where x.ClassID=? and s.SpellID is null',(CLASS,)).fetchone())
  armor=self.db.execute("select AbilityLevel from SpecXAbility where Spec='TuathaCareer' and AbilityKey='HibArmor'").fetchone()
  self.assertEqual(armor[0],4,'scale armor')
 def test_realm_abilities_are_separate_and_rr5_is_free_career_granted(self):
  private=list(self.db.execute("select AbilityKey from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey like 'Tuatha_%'",(CLASS,)))
  self.assertEqual(len(private),4)
  for key, in private:
   self.assertFalse(self.db.execute('select 1 from ClassXRealmAbility_Atlas where AbilityKey=? and CharClass<>?',(key,CLASS)).fetchone())
  self.assertFalse(self.db.execute('select 1 from LineXSpell where SpellID=73560').fetchone())
  self.assertEqual(self.db.execute('select Duration,Damage,Radius from Spell where SpellID=73560').fetchone()[:],(20,300,500))
  self.assertEqual(self.db.execute("select Value from ServerProperty where Key='enable_tuatha'").fetchone()[0],'True')
 def test_asset_references_exist_and_starter_items_are_present(self):
  import os,sys
  os.environ['OFFLINE_DAOC_CLIENT']=str(ROOT/'runtime/client-modern/app')
  sys.path.insert(0,str(REPO/'tools/pet-art'));import daoc_catalog as c
  data=c.gamedata();effects={int(r[0]) for r in c.csv_rows(data,'spells.csv') if r and r[0].isdigit()}
  for effect, in self.db.execute('select distinct ClientEffect from Spell where PackageID=?',(PACKAGE,)):
   if effect:self.assertIn(effect,effects)
  models={int(r[0]) for r in c.csv_rows(data,'monsters.csv') if r and r[0].isdigit()}
  for model in (COMPANION_MODEL,CROWN_MODEL):self.assertIn(model,models)
  self.assertFalse(self.db.execute("select 1 from StarterEquipment s left join ItemTemplate i on s.TemplateID=i.Id_nb where s.Class=? and i.Id_nb is null",(str(CLASS),)).fetchone())
  self.assertTrue(self.db.execute("select 1 from Mob where Mob_ID='tuatha-trainer' and Region=201").fetchone())
 def test_guarded_installer_and_rollback_preserve_saved_progress(self):
  import tempfile,shutil,json
  from unittest.mock import patch as mock
  from install_tuatha import install
  with tempfile.TemporaryDirectory(prefix='tuatha-test-',dir=REPO/'artifacts') as folder:
   target=Path(folder)
   files=['runtime/client-modern/app/game.dll','runtime/modern-client.json','backups/client-bundle-20261021-165832-708287/game.original.dll']
   files += [d+'/GameServer.dll' for d in ('runtime/server','runtime/server/lib','runtime/server/win-x64')]
   for rel in files:
    (target/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,target/rel)
   db=target/'runtime/data/opendaoc.sqlite3.db';db.parent.mkdir(parents=True)
   with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(db)) as dest:src.backup(dest)
   hashes={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [db]+[target/r for r in files]}
   with mock('install_tuatha.stopped'):
    result=install(target,apply=True);self.assertTrue(result['verified']);self.assertEqual(result['progress_tables_verified'],37)
    client=hashlib.sha256((target/'runtime/client-modern/app/game.dll').read_bytes()).hexdigest()
    self.assertEqual(json.loads((target/'runtime/modern-client.json').read_text())['GameSha256'].lower(),client)
    install(target,rollback=Path(result['backup']))
   for rel,digest in hashes.items():self.assertEqual(hashlib.sha256((target/rel).read_bytes()).hexdigest(),digest)

if __name__=='__main__':unittest.main()
