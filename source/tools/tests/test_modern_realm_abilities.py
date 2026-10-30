from contextlib import closing
import sqlite3, unittest, sys
from pathlib import Path
TOOLS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TOOLS))
import modern_realm_abilities as migration
WORLD=TOOLS.parents[1]/'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'

class ModernRealmAbilitiesTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:'); self.db.row_factory=sqlite3.Row
  with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as source:source.backup(self.db)
 def tearDown(self):self.db.close()
 def snapshot(self,table):return [tuple(r) for r in self.db.execute('select * from '+table+' order by rowid')]
 def test_preserves_claude_visuals_trainers_custom_abilities_and_all_progress(self):
  tables=['Spell','Style','Mob','NPCEquipment','DOLCharacters','Account','offline_world_bots']
  before={t:self.snapshot(t) for t in tables}
  custom=[tuple(r) for r in self.db.execute("select * from Ability where KeyName like 'Sovereign_%' or KeyName like 'Pendragon_%'")]
  with self.db:migration.apply(self.db)
  for t in tables:self.assertEqual(before[t],self.snapshot(t),t)
  self.assertEqual(custom,[tuple(r) for r in self.db.execute("select * from Ability where KeyName like 'Sovereign_%' or KeyName like 'Pendragon_%'")])
 def test_idempotent_unique_class_lists_and_private_internal_id(self):
  with self.db:migration.apply(self.db)
  before=self.snapshot('Ability'),self.snapshot('ClassXRealmAbility_Atlas')
  with self.db:migration.apply(self.db)
  self.assertEqual(before,(self.snapshot('Ability'),self.snapshot('ClassXRealmAbility_Atlas')))
  for cls in (11,31,32,43):
   self.assertEqual(self.db.execute("select AbilityKey from ClassXRealmAbility_Atlas where CharClass=? and (AbilityKey like '%Determination%' or AbilityKey like '%DeterminationHybrid%')",(cls,)).fetchall()[0][0],'Modern_LightTankDetermination')
  self.assertEqual(self.db.execute('select count(*) from Ability where InternalID=3040').fetchone()[0],1)
  self.assertEqual(self.db.execute("select count(*) from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_AvoidanceOfMagic'").fetchone()[0],0)
  for cls in (33,39,58,59,60,61,62):
   self.assertGreater(self.db.execute('select count(*) from ClassXRealmAbility_Atlas where CharClass=?',(cls,)).fetchone()[0],5)
 def test_refuses_to_reprice_purchased_legacy_abilities(self):
  self.db.execute('delete from DOLCharacters')
  # Use a minimal save row to exercise the allocation guard without any player details.
  self.db.execute('drop table DOLCharacters')
  self.db.execute('create table DOLCharacters (SerializedRealmAbilities text)')
  self.db.execute("insert into DOLCharacters values ('AtlasOF_AugStr|5;')")
  self.db.execute("update Ability set Implementation='DOL.GS.RealmAbilities.AtlasOF_RAStrengthEnhancer' where KeyName='AtlasOF_AugStr'")
  self.db.commit()
  with self.assertRaisesRegex(ValueError,'refund migration'):
   with self.db:migration.apply(self.db)
 def test_all_declared_handlers_exist(self):
  with self.db:migration.apply(self.db)
  source=(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernRealmPassives.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernFirstAid.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernRecoveryRealmAbilities.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernGroupRealmAbilities.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernDamageRealmAbilities.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernStormRealmAbilities.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernUtilityRealmAbilities.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernSharedActives.cs').read_text()+(TOOLS.parent/'server/GameServer/realmabilities/handlers/ModernStealthRealmAbilities.cs').read_text()
  for key in migration.KEYS:self.assertIn('class Modern'+key+' :',source)
  for key,(handler,_) in migration.EXTRA.items():self.assertIn('class '+handler+' :',source)

 def test_modern_actives_have_one_binding_per_class_and_no_free_light_tank_charge(self):
  before=[tuple(r) for r in self.db.execute("select * from SpecXAbility where AbilityKey not in ('Charge','Vanish')")]
  with self.db:migration.apply(self.db)
  self.assertEqual(before,[tuple(r) for r in self.db.execute("select * from SpecXAbility where AbilityKey not in ('Charge','Vanish')")])
  self.assertFalse(self.db.execute("select 1 from SpecXAbility where AbilityKey='Charge' and Spec in ('BerserkerCareer','MercenaryCareer','BlademasterCareer','SavageCareer')").fetchone())
  for names in [('AtlasOF_Purge','AtlasOF_PurgeReduced'),('AtlasOF_IgnorePain','AtlasOF_IgnorePainTank'),('Charge','Valkyrie_Charge')]:
   self.assertFalse(self.db.execute('select CharClass from ClassXRealmAbility_Atlas where AbilityKey in (?,?) group by CharClass having count(*)>1',names).fetchall())
  self.assertTrue(self.db.execute("select 1 from ClassXRealmAbility_Atlas where CharClass=59 and AbilityKey='AtlasOF_Concentration'").fetchone())
 def test_old_class_keys_and_serialized_cooldowns_are_preserved(self):
  keys=[tuple(r) for r in self.db.execute("select CharClass,AbilityKey from ClassXRealmAbility_Atlas where AbilityKey in ('AtlasOF_PurgeReduced','AtlasOF_IgnorePainTank','Valkyrie_Charge')")]
  self.db.execute('drop table DOLCharacters')
  self.db.execute('create table DOLCharacters (SerializedRealmAbilities text, DisabledAbilities text)')
  self.db.execute("insert into DOLCharacters values ('', 'AtlasOF_PurgeReduced|600000;Valkyrie_Charge|45000')")
  with self.db:migration.apply(self.db)
  self.assertEqual(self.db.execute('select DisabledAbilities from DOLCharacters').fetchone()[0],'AtlasOF_PurgeReduced|600000;Valkyrie_Charge|45000')
  for cls,key in keys:self.assertTrue(self.db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?',(cls,key)).fetchone())

 def test_live_1128_control_access_moves_are_applied_after_baseline(self):
  with self.db:migration.apply(self.db)
  for cls,key in [(4,'AtlasOF_Ichor'),(34,'AtlasOF_Ichor'),(29,'AtlasOF_StaticTempest')]:
   self.assertFalse(self.db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?',(cls,key)).fetchone())
  for cls,key in [(7,'AtlasOF_Ichor'),(29,'AtlasOF_Ichor'),(34,'AtlasOF_StaticTempest')]:
   self.assertTrue(self.db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?',(cls,key)).fetchone())
 def test_live_shared_actives_replace_single_rank_atlas_versions(self):
  with self.db:migration.apply(self.db)
  for key,classes in [('Speed of Sound',{4,24,48}),('Perfect Recovery',{6,26,33,47}),('Decimation Trap',{7,29,40,59}),('Dashing Defense',{2,22,44}),('Divine Intervention',{6,26,33,47})]:
   bound={r[0] for r in self.db.execute('select CharClass from ClassXRealmAbility_Atlas where AbilityKey=?',(key,))}
   self.assertTrue(classes<=bound,key)
  for atlas in migration.REPLACED_ATLAS:
   self.assertFalse(self.db.execute('select 1 from ClassXRealmAbility_Atlas where AbilityKey=?',(atlas,)).fetchone(),atlas)
  for key,(handler,_) in migration.EXTRA.items():
   self.assertEqual(self.db.execute('select Implementation from Ability where KeyName=?',(key,)).fetchone()[0],'DOL.GS.RealmAbilities.'+handler)
 def test_stealth_pass_follows_live_1126_and_1122b(self):
  with self.db:migration.apply(self.db)
  bound={r[0] for r in self.db.execute("select CharClass from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_MasteryOfStealth'")}
  self.assertTrue(set(migration.STEALTH_CLASSES)<=bound)
  self.assertFalse(self.db.execute("select 1 from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_Vanish'").fetchone())
  self.assertEqual(sorted(r[0] for r in self.db.execute("select CharClass from ClassXRealmAbility_Atlas where AbilityKey='Vanish'")),list(migration.ASSASSINS),'1.123: trainable for assassins only')
  self.assertFalse(self.db.execute("select 1 from SpecXAbility where AbilityKey='Vanish'").fetchone(),'No longer a Stealth spec grant')
 def test_class_access_audit_removes_old_frontiers_everywhere_and_keeps_custom_uniques(self):
  unique={cls:{r[0] for r in self.db.execute('select AbilityKey from ClassXRealmAbility_Atlas where CharClass=?',(cls,)) if r[0] not in migration.OLD_FRONTIERS_ONLY} for cls in migration.CUSTOM_CLASSES}
  with self.db:migration.apply(self.db)
  marks=','.join('?'*len(migration.AUDIT_REMOVED))
  self.assertFalse(self.db.execute('select CharClass,AbilityKey from ClassXRealmAbility_Atlas where AbilityKey in (%s) and CharClass not in (34,63,64,65)'%marks,migration.AUDIT_REMOVED).fetchall())
  marks=','.join('?'*len(migration.OLD_FRONTIERS_ONLY))
  self.assertFalse(self.db.execute('select CharClass,AbilityKey from ClassXRealmAbility_Atlas where AbilityKey in (%s)'%marks,migration.OLD_FRONTIERS_ONLY).fetchall())
  for cls,keys in unique.items():
   self.assertTrue(keys<={r[0] for r in self.db.execute('select AbilityKey from ClassXRealmAbility_Atlas where CharClass=?',(cls,))},cls)
  self.assertTrue(self.db.execute("select 1 from ClassXRealmAbility_Atlas where CharClass=63 and AbilityKey='AtlasOF_CripplingPlague'").fetchone())
  self.assertTrue(self.db.execute("select 1 from ClassXRealmAbility_Atlas where CharClass=34 and AbilityKey='Valhalla''s Blessing'").fetchone())
  left=[r[0] for r in self.db.execute("select distinct c.AbilityKey from ClassXRealmAbility_Atlas c join Ability a on a.KeyName=c.AbilityKey where c.CharClass not in (34,63,64,65) and a.Implementation not like 'DOL.GS.RealmAbilities.Modern%'") if r[0] not in migration.RR5_BINDINGS]
  self.assertEqual(left,[],'Every base-class realm ability is a modern live handler or an audited RR5')
 def test_custom_classes_get_live_hybrid_picks_and_valkyrie_matches_live(self):
  with self.db:migration.apply(self.db)
  for cls,keys in migration.CUSTOM_ADDITIONS.items():
   bound={r[0] for r in self.db.execute('select AbilityKey from ClassXRealmAbility_Atlas where CharClass=?',(cls,))}
   self.assertTrue(set(keys)<=bound,cls)
   self.assertFalse({'AtlasOF_Determination','AtlasOF_DeterminationHybrid'}<=bound,'Determination must not be bound twice')
   left=[r[0] for r in self.db.execute("select c.AbilityKey from ClassXRealmAbility_Atlas c join Ability a on a.KeyName=c.AbilityKey where c.CharClass=? and a.Implementation not like 'DOL.GS.RealmAbilities.Modern%' and c.AbilityKey not in ('AtlasOF_CripplingPlague') and c.AbilityKey not like 'Sovereign_%' and c.AbilityKey not like 'Pendragon_%'",(cls,))]
   self.assertEqual(left,[],cls)
  valkyrie={r[0] for r in self.db.execute('select AbilityKey from ClassXRealmAbility_Atlas where CharClass=34')}
  self.assertIn('AtlasOF_StaticTempest',valkyrie); self.assertNotIn('AtlasOF_Ichor',valkyrie)
  self.assertTrue({"Valhalla's Blessing",'Valkyrie_Charge','Dual Threat','Mastery of Focus','AtlasOF_MasteryOfHealing','AtlasOF_WildHealing'}<=valkyrie)
 def test_audited_rr5s_are_bound_to_their_live_class_only(self):
  with self.db:migration.apply(self.db)
  for key,cls in migration.RR5_BINDINGS.items():
   self.assertEqual([r[0] for r in self.db.execute('select CharClass from ClassXRealmAbility_Atlas where AbilityKey=?',(key,))],[cls],key)
 def test_live_replacement_rr5s_have_rows_and_modern_handlers(self):
  with self.db:migration.apply(self.db)
  for key,(handler,internal,icon,_) in migration.MODERN_RR5_ROWS.items():
   row=self.db.execute('select Implementation,IconID,InternalID from Ability where KeyName=?',(key,)).fetchone()
   self.assertEqual(row[0],'DOL.GS.RealmAbilities.'+handler,key); self.assertEqual(row[1],icon,key)
   if internal: self.assertEqual(row[2],internal,key)
  for _,internal,_,_ in migration.MODERN_RR5_ROWS.values():
   if internal: self.assertEqual(self.db.execute('select count(*) from Ability where InternalID=?',(internal,)).fetchone()[0],1,internal)
  handlers=TOOLS.parent/'server/GameServer/realmabilities/handlers'
  source=''.join(f.read_text(encoding='utf-8',errors='replace') for f in handlers.rglob('*.cs'))
  for handler,*_ in migration.MODERN_RR5_ROWS.values(): self.assertIn('class '+handler+' :',source)
 def test_warlock_gets_its_live_realm_abilities_and_rr5(self):
  with self.db:migration.apply(self.db)
  bound={r[0] for r in self.db.execute('select AbilityKey from ClassXRealmAbility_Atlas where CharClass=59')}
  self.assertTrue(set(migration.WARLOCK_LIVE_RAS)<=bound)
  self.assertIn('Boiling Cauldron',bound)
  self.assertEqual(self.db.execute("select Implementation from Ability where KeyName='Boiling Cauldron'").fetchone()[0],'DOL.GS.RealmAbilities.ModernBoilingCauldron')
