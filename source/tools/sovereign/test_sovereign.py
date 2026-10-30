"""Read-only fixture: prove migration idempotency, timers, styles and progress preservation."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import unittest
from seed_sovereign import seed, SPELLS, PACKAGE
REPO=Path(__file__).resolve().parents[3]
WORLD=REPO/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
class MigrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.db=sqlite3.connect(':memory:')
  with sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True) as src: src.backup(cls.db)
  cls.db.row_factory=sqlite3.Row
  cls.before=cls.progress()
  with cls.db: cls.summary=seed(cls.db)
 @classmethod
 def progress(cls):
  result={}
  for table in __import__('json').loads((REPO/'source/tools/OfflineDaoc.ProgressImport/progress-policy.json').read_text())['ProgressTables']:
   if cls.db.execute('select 1 from sqlite_master where type="table" and name=?',(table,)).fetchone():
    rows=cls.db.execute(f'select * from "{table}"').fetchall()
    result[table]=hashlib.sha256(repr(sorted(map(tuple,rows),key=repr)).encode()).hexdigest()
  return result
 def latest(self,key):
  return self.db.execute('select s.* from Spell s join LineXSpell l on s.SpellID=l.SpellID where l.LineName=? order by l.Level desc limit 1',(f'Stormforged.Sovereign{key:02}',)).fetchone()
 def test_progress_untouched_and_reseed_is_safe(self):
  self.assertEqual(self.before,self.progress())
  with self.db: summary=seed(self.db)
  self.assertEqual(self.summary,summary)
  self.assertEqual(self.before,self.progress())
 def test_requested_timers_and_shapes(self):
  for key in (2,3,21): self.assertEqual(self.latest(key)['RecastDelay'],15)
  self.assertEqual((self.latest(3)['Target'],self.latest(3)['CastTime']),('Self',0))
  self.assertEqual((self.latest(4)['CastTime'],self.latest(4)['RecastDelay']),(2.3,0))
  self.assertEqual((self.latest(5)['Target'],self.latest(5)['Duration'],self.latest(5)['RecastDelay']),('Self',30,30))
  self.assertEqual((self.latest(10)['CastTime'],self.latest(10)['RecastDelay']),(0,30))
  self.assertEqual((self.latest(20)['Duration'],self.latest(20)['RecastDelay']),(60,180))
  self.assertEqual(self.latest(21)['Range'],2100)
  for key in (7,8,9): self.assertEqual((self.latest(key)['RecastDelay'],self.latest(key)['SharedTimerGroup']),(30,0))
 def test_private_realm_abilities_and_frost_icons(self):
  from seed_sovereign import PRIVATE_RAS
  for key,_,internal,icon,implementation,_ in PRIVATE_RAS:
   row=self.db.execute('select * from Ability where KeyName=?',(key,)).fetchone()
   self.assertEqual((row['InternalID'],row['IconID'],row['Implementation']),(internal,icon,'DOL.GS.RealmAbilities.'+implementation))
   classes=[r[0] for r in self.db.execute('select CharClass from ClassXRealmAbility_Atlas where AbilityKey=?',(key,))]
   self.assertEqual(classes,[64])
  self.assertEqual((self.latest(1)['Icon'],self.latest(1)['ClientEffect']),(14321,14321))
  rr5=self.db.execute('select * from Spell where SpellID=62960').fetchone()
  self.assertEqual((rr5['Duration'],rr5['Damage'],rr5['Radius']),(20,300,500))
  self.assertFalse(self.db.execute('select 1 from LineXSpell where SpellID=62960').fetchone())
 def test_automatic_skills_and_private_styles(self):
  specs=dict(self.db.execute('select SpecKeyName,LevelAcquired from ClassXSpecialization where ClassID=64'))
  for key in ('Sword','Hammer','Axe','Spear','Shields','Parry','Stealth'): self.assertLess(specs[key],0)
  self.assertEqual(self.db.execute('select count(*) from Style where ClassId=64').fetchone()[0],35)
  self.assertEqual(self.db.execute('select count(*) from StyleXSpell where ClassID=64').fetchone()[0],35)
  self.assertFalse(self.db.execute('select 1 from StyleXSpell x left join Spell s on s.SpellID=x.SpellID where x.ClassID=64 and s.SpellID is null').fetchone())
 def test_only_one_wolf_and_no_old_summon_buttons(self):
  self.assertEqual(self.latest(19)['Type'],'StormSovereignWolf')
  self.assertEqual(self.db.execute('select Model from NpcTemplate where TemplateId=60171001').fetchone()[0],'459')
  self.assertFalse(self.db.execute("select 1 from Spell s join LineXSpell l on l.SpellID=s.SpellID where s.PackageID=? and s.Type in ('StormforgedPet','SummonAnimistFnF','StormforgedRide')",(PACKAGE,)).fetchone())
 def test_client_addresses_do_not_collide(self):
  self.assertFalse(self.db.execute("select 1 from LineXSpell where LineName like 'Stormforged.%' group by LineName,Level having count(*)>1").fetchone())
  self.assertEqual(self.latest(6)['Damage'],50)
  self.assertEqual(self.latest(6)['Value'],205)
  for key,_,unlock,_,_,_ in SPELLS:
   self.assertEqual(self.db.execute('select min(Level) from LineXSpell where LineName=?',(f'Stormforged.Sovereign{key:02}',)).fetchone()[0],unlock)
 def test_stuns_require_a_chain_and_style_procs_are_private(self):
  for row in self.db.execute('select * from Style where ClassId=64 and (ID-1800)%7=4'):
   self.assertEqual(row['AttackResultRequirement'],7)
   self.assertEqual(row['OpeningRequirementValue'],row['ID']-3)
 def test_client_patch_keeps_hash_guards_and_original_output(self):
  import sys
  sys.path.insert(0,str(REPO/'source/tools/stormforged'))
  from patch_modern_client import patch
  original=(REPO/'artifacts/modern-client-test/backups/client-bundle-20261021-165832-708287/game.original.dll').read_bytes()
  old=patch(original)
  self.assertEqual(hashlib.sha256(old).hexdigest(),'b67c4a92f5ef245348cda4b192252ea7a5fb5519c85933480982782e369f0440')
  new=patch(original,sovereign=True)
  self.assertIn(b'Storm Sovereign\0',new)
  self.assertEqual(new,patch(original,sovereign=True))
  with self.assertRaises(ValueError): patch(new,sovereign=True)
 def test_guarded_install_and_rollback_on_an_isolated_fixture(self):
  import tempfile, shutil
  from unittest.mock import patch as mock_patch
  from install_sovereign import install
  source=REPO/'artifacts/modern-client-test'
  with tempfile.TemporaryDirectory(prefix='sovereign-installer-test-',dir=REPO/'artifacts') as folder:
   root=Path(folder).resolve()
   self.assertTrue(root.is_relative_to((REPO/'artifacts').resolve()))
   files=['runtime/client-modern/app/game.dll','runtime/modern-client.json',
    'backups/client-bundle-20261021-165832-708287/game.original.dll']
   files += [d+'/GameServer.dll' for d in ('runtime/server','runtime/server/lib','runtime/server/win-x64')]
   for rel in files:
    (root/rel).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source/rel,root/rel)
   world=root/'runtime/data/opendaoc.sqlite3.db';world.parent.mkdir(parents=True)
   with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(world)) as dst: src.backup(dst)
   # This installer intentionally rejects an Albion-patched client. Keep its fixture
   # on its own supported Midgard-only baseline instead of weakening the hash guard.
   import json
   from patch_modern_client import patch as midgard_client
   baseline=midgard_client((root/'backups/client-bundle-20261021-165832-708287/game.original.dll').read_bytes(),sovereign=True)
   (root/'runtime/client-modern/app/game.dll').write_bytes(baseline)
   profile=root/'runtime/modern-client.json';settings=json.loads(profile.read_text())
   settings['GameSha256']=hashlib.sha256(baseline).hexdigest().upper();profile.write_text(json.dumps(settings))
   original={rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in files}
   original[world.relative_to(root).as_posix()]=hashlib.sha256(world.read_bytes()).hexdigest()
   with mock_patch('install_sovereign.stopped'):
    result=install(root,apply=True)
    self.assertTrue(result['verified'])
    self.assertEqual(result['progress_tables_verified'],len(self.before))
    install(root,rollback=Path(result['backup']))
   for rel,digest in original.items(): self.assertEqual(hashlib.sha256((root/rel).read_bytes()).hexdigest(),digest)
if __name__=='__main__': unittest.main()
