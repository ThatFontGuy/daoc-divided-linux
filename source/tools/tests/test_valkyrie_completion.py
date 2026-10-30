"""Definition integration checks; fixtures never include saved player data."""
from contextlib import closing
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import unittest
TOOLS=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('valk_completion',TOOLS/'valkyrie_completion.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
WORLD=TOOLS.parents[1]/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
class ValkyrieCompletionTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as source:
   for table in ['Spell','Style','StyleXSpell','Ability','ClassXRealmAbility_Atlas','SpecXAbility','ServerProperty']:
    self.c.execute(source.execute('select sql from sqlite_master where type="table" and name=?',(table,)).fetchone()[0])
    query='select * from "'+table+'"'
    if table=='ServerProperty':query+=" where lower(Key)='valkyrie_test_data_version'"
    rows=source.execute(query).fetchall()
    if rows:self.c.executemany('insert into "'+table+'" values ('+','.join('?' for _ in rows[0])+')',rows)
  self.c.commit()
 def tearDown(self):self.c.close()
 def seed(self):
  with self.c:return module.apply(self.c)
 def fingerprint(self,table,where='1=1'):
  rows=[tuple(r) for r in self.c.execute('select * from "'+table+'" where '+where)]
  return hashlib.sha256(repr(sorted(rows,key=repr)).encode()).hexdigest()
 def test_all_weapon_lines_and_reapply(self):
  self.seed();self.assertEqual(self.c.execute('select count(*) from Style where ClassId=34').fetchone()[0],51)
  counts={r[0]:r[1] for r in self.c.execute('select SpecKeyName,count(*) from Style where ClassId=34 group by SpecKeyName')}
  self.assertEqual(counts,dict(Sword=19,Spear=18,Shields=14))
  before={t:self.fingerprint(t) for t in ['Style','Spell','StyleXSpell','Ability','SpecXAbility','ClassXRealmAbility_Atlas']}
  self.seed();self.assertEqual(before,{t:self.fingerprint(t) for t in before})
 def test_chains_reference_earlier_styles_in_same_line(self):
  self.seed();rows={r['ID']:r for r in self.c.execute('select * from Style where ClassId=34')}
  for row in rows.values():
   if row['AttackResultRequirement']==7:
    previous=rows[row['OpeningRequirementValue']]
    self.assertEqual(previous['SpecKeyName'],row['SpecKeyName']);self.assertLess(previous['SpecLevelRequirement'],row['SpecLevelRequirement'])
  self.assertEqual(rows[146]['SpecLevelRequirement'],1)
  for name in ['Frost Cut','Ice Storm']:
   row=next(r for r in rows.values() if r['Name']==name);self.assertEqual((row['OpeningRequirementType'],row['AttackResultRequirement']),(1,4))
 def test_stuns_power_rend_and_ablative_effects(self):
  self.seed()
  def effect(name):return self.c.execute('select p.* from Style s join StyleXSpell x on x.StyleID=s.ID and x.ClassID=s.ClassId join Spell p on p.SpellID=x.SpellID where s.ClassId=34 and s.Name=?',(name,)).fetchone()
  self.assertEqual(effect('Slam')['Duration'],5);self.assertEqual(effect('Razor Edge')['Duration'],7)
  brace=effect('Brace');self.assertEqual((brace['Type'],brace['Value'],brace['Damage'],brace['Target'],brace['Duration']),('AblativeArmor',300,50,'Self',600))
  rend=effect('Aurora');self.assertEqual((rend['Type'],rend['Value'],rend['Radius'],rend['Range']),('PowerRend',.03,350,0))
  self.assertEqual(effect("Odin's Bite")['Value'],.06)
  self.assertEqual((effect('Roundhouse')['Damage'],effect('Roundhouse')['Radius']),(200,250))
  self.assertEqual((effect("Gungnir's Fury")['Damage'],effect("Gungnir's Fury")['Radius']),(150,700))
 def test_realm_abilities_and_shield_progression(self):
  self.seed();keys={r[0] for r in self.c.execute('select AbilityKey from ClassXRealmAbility_Atlas where CharClass=34')}
  self.assertIn("Valhalla's Blessing",keys);self.assertIn('Valkyrie_Charge',keys)
  modern=self.c.execute("select 1 from Ability where KeyName='AtlasOF_AoM' and Implementation='DOL.GS.RealmAbilities.ModernAoM'").fetchone()
  self.assertIn('AtlasOF_Determination' if modern else 'AtlasOF_DeterminationHybrid',keys)
  if modern:
   self.assertIn('AtlasOF_AoM',keys);self.assertNotIn('AtlasOF_AvoidanceOfMagic',keys)
  self.assertGreaterEqual(len(keys),32 if self.c.execute("select 1 from SpecXAbility where Spec='CharacterCareer' and AbilityKey='Tireless' and ClassId=0 and SpecLevel=1").fetchone() else 33)
  shields=[tuple(r) for r in self.c.execute("select SpecLevel,AbilityLevel from SpecXAbility where Spec='ValkyrieCareer' and AbilityKey='Shield' order by SpecLevel")]
  self.assertEqual(shields,[(1,1),(5,2),(10,3)])
 def test_stock_classes_and_shared_spell_rows_unchanged(self):
  checks={'Style':'ClassId<>34','StyleXSpell':'ClassID<>34','SpecXAbility':"Spec<>'ValkyrieCareer'",'Spell':"coalesce(PackageID,'')<>'local-valk-completion-v6'",'ClassXRealmAbility_Atlas':'CharClass<>34'}
  before={t:self.fingerprint(t,w) for t,w in checks.items()};self.seed()
  self.assertEqual(before,{t:self.fingerprint(t,w) for t,w in checks.items()})
 def test_identity_collision_rolls_back(self):
  row=dict(self.c.execute('select * from Spell where SpellID=64990').fetchone());row.update(SpellID=65200,Spell_ID='foreign-test',PackageID='foreign')
  self.c.execute('delete from Spell where SpellID=65200')
  self.c.execute('insert into Spell ('+','.join('"'+k+'"' for k in row)+') values ('+','.join('?' for _ in row)+')',list(row.values()));self.c.commit()
  before=self.fingerprint('Style')
  with self.assertRaisesRegex(ValueError,'collision'):self.seed()
  self.assertEqual(before,self.fingerprint('Style'))
 def test_client_effects_exist_and_no_dangling_proc_links(self):
  self.seed()
  import sys
  sys.path.insert(0,str(TOOLS.parents[1]/'tools/pet-art'))
  import daoc_catalog as catalog
  catalog.CLIENT=WORLD.parents[1]/'client-modern/app'
  known={int(r[0]) for r in catalog.csv_rows(catalog.gamedata(),'spells.csv') if r and r[0].isdigit()}
  for row in self.c.execute('select ClientEffect,Icon,TooltipId from Spell where PackageID=?',(module.PACKAGE,)):
   self.assertTrue(row[0]==0 or row[0] in known);self.assertIn(row[1],known);self.assertLess(row[2],32768)
  self.assertFalse(self.c.execute('select 1 from StyleXSpell x left join Spell p on p.SpellID=x.SpellID where x.ClassID=34 and p.SpellID is null').fetchone())

 def test_guarded_installer_preserves_progress_and_refuses_rollback_after_play(self):
  import sys,tempfile,json
  from unittest.mock import patch
  sys.path.insert(0,str(TOOLS))
  import install_valkyrie_completion as installer
  with tempfile.TemporaryDirectory(prefix='valk-install-test-',dir=TOOLS.parents[1]/'artifacts') as folder:
   base=Path(folder);root=base/'artifacts/modern-client-test';data=root/'runtime/data';data.mkdir(parents=True)
   database=data/'opendaoc.sqlite3.db'
   self.c.execute('create table Account (TestSentinel text)');self.c.execute("insert into Account values ('preserve this save')");self.c.commit()
   with closing(sqlite3.connect(database)) as dest:self.c.backup(dest)
   for directory in ['runtime/server','runtime/server/lib','runtime/server/win-x64']:
    target=root/directory;target.mkdir(parents=True,exist_ok=True);(target/'GameServer.dll').write_bytes(b'previous-tested-server')
   (root/'backups').mkdir();build=base/'build';build.mkdir();(build/'GameServer.dll').write_bytes(b'new-tested-server')
   old=database.read_bytes()
   with patch.object(installer,'REPO',base),patch.object(installer,'stopped'):
    preview=installer.install(root,build_dir=build);self.assertTrue(preview['preview']);self.assertEqual(database.read_bytes(),old)
    result=installer.install(root,True,build_dir=build);self.assertEqual(result['progress_tables_verified'],1)
    with closing(sqlite3.connect(database)) as installed:
     self.assertEqual(installed.execute('select * from Account').fetchall(),[('preserve this save',)])
     self.assertEqual(installed.execute('select count(*) from Style where ClassId=34').fetchone()[0],51)
    just_installed=database.read_bytes()
    with closing(sqlite3.connect(database)) as played,played:played.execute("insert into Account values ('new progress')")
    with self.assertRaisesRegex(ValueError,'progress changed'):installer.install(root,rollback=Path(result['backup']))
    database.write_bytes(just_installed)
    installer.install(root,rollback=Path(result['backup']))
    self.assertEqual(database.read_bytes(),old)
    self.assertEqual((root/'runtime/server/GameServer.dll').read_bytes(),b'previous-tested-server')
