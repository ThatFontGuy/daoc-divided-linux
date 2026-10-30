"""Replace only the Stormforged package/class-64 content with Storm Sovereign.
Preview by default. Player/account/inventory/progression tables are never written.
"""
import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stormforged'))
from seed_stormforged import seed as legacy_seed, row_copy, source_row, PACKAGE, CAREER, CLASS

LEVELS=(1,5,10,15,20,30,40,50)
# key, name, unlock, target, type, settings at rank 50 (damage scales by tier)
SPELLS=[
 (0,'Lightning Spear',1,'Enemy','StormSovereignAbility',dict(Range=1500,Damage=250,CastTime=2.5,Power=18,ClientEffect=3510)),
 (1,"Winter's Grasp",11,'Enemy','StormSovereignAbility',dict(Range=1500,Damage=160,CastTime=2,Power=16,ClientEffect=14321)),
 (2,'Royal Thunder',21,'Enemy','StormSovereignAbility',dict(Range=1500,Damage=180,RecastDelay=15,Power=12,ClientEffect=3549)),
 (3,'Chain of the Crown',31,'Self','StormSovereignAbility',dict(Radius=350,Damage=200,RecastDelay=15,Power=16,ClientEffect=3528)),
 (4,'Stormbreak',41,'Self','StormSovereignAbility',dict(Radius=350,Damage=250,CastTime=2.3,Power=25,ClientEffect=3528)),
 (5,'Eye of the Storm',45,'Self','StormSovereignAbility',dict(Radius=350,Damage=100,Duration=30,Frequency=30,RecastDelay=30,Power=20,ClientEffect=3525)),
 (6,'Royal Presence',1,'Self','StormforgedChant',dict(Radius=1500,Duration=65535,Frequency=40,Power=0,ClientEffect=3534)),
 (7,'Decree: Advance',15,'Self','StormSovereignAbility',dict(Radius=1500,Duration=10,RecastDelay=30,Power=5,ClientEffect=3534)),
 (8,'Decree: Stand Fast',20,'Self','StormSovereignAbility',dict(Radius=1500,Duration=10,RecastDelay=30,Power=5,ClientEffect=3536)),
 (9,'Decree: Strike True',25,'Self','StormSovereignAbility',dict(Radius=1500,Duration=10,RecastDelay=30,Power=5,ClientEffect=3537)),
 (10,"Sovereign's Renewal",11,'Self','StormSovereignAbility',dict(RecastDelay=30,Power=10,Value=25,ClientEffect=3517)),
 (11,'Rally to the Crown',31,'Self','StormSovereignAbility',dict(Radius=1500,RecastDelay=90,Power=20,Value=15,ClientEffect=3517)),
 (12,'Will of the Sovereign',45,'Self','StormSovereignAbility',dict(Duration=3,RecastDelay=180,Power=0,ClientEffect=3535)),
 (13,'Armor of the Crown',1,'Self','StormforgedWard',dict(Duration=65535,Power=0,Value=100,ClientEffect=3537)),
 (14,'Runic Ward',25,'Self','StormSovereignAbility',dict(Duration=65535,Power=0,ClientEffect=3536)),
 (15,'Runic Armament',11,'Self','StormSovereignAbility',dict(Duration=65535,Power=0,ClientEffect=3537)),
 (16,"Sovereign's Challenge",10,'Enemy','StormSovereignAbility',dict(Range=1500,RecastDelay=10,Power=0,ClientEffect=3549)),
 (17,"Hunter's Mark",25,'Enemy','StormSovereignAbility',dict(Range=1500,Duration=30,RecastDelay=30,Power=0,ClientEffect=3538)),
 (18,'Runic Reversal',35,'Self','StormSovereignAbility',dict(Duration=8,RecastDelay=45,Power=5,ClientEffect=3536)),
 (19,'Storm Wolf',5,'Self','StormSovereignWolf',dict(Duration=65535,CastTime=3,Damage=-100,Value=50,LifeDrainReturn=60171001,Power=10,ClientEffect=3531)),
 (20,'Storm Crown',40,'Self','StormforgedAvatar',dict(Duration=60,Frequency=40,RecastDelay=180,Value=918,Radius=350,Power=20,ClientEffect=3537)),
 (21,"Sovereign's Hammerfall",15,'Enemy','StormSovereignAbility',dict(Range=2100,Radius=350,Damage=350,RecastDelay=15,Power=10,ClientEffect=3541)),
 (22,'Veil of Winter',30,'Self','StormSovereignAbility',dict(Duration=65535,Power=0,ClientEffect=3538))]
DESCRIPTIONS={
 0:'Lightning damage at range.',1:'Cold damage and a 30% snare for 8 seconds.',2:'Instant lightning strike. 15-second reuse.',
 3:'Instant lightning burst around the caster. 350 radius; 15-second reuse.',4:'Lightning burst around the caster. 2.3-second base cast, no reuse timer.',
 5:'A stationary storm forms at your feet, striking enemies every 3 seconds for 30 seconds. Reuse: 30 seconds; one storm per owner.',
 6:'One maintained chant: health, power and endurance regeneration, combat/stealth speed, armor, damage add, haste and all magic resists. Final strength at level 40.',
 7:'Party movement speed increases for 10 seconds, including combat. Independent 30-second reuse.',8:'Party gains 10% absorption for 10 seconds. Independent 30-second reuse.',
 9:'Party gains accuracy and 10% melee damage for 10 seconds. Independent 30-second reuse.',10:'Instantly restore 25% maximum health. 30-second reuse.',
 11:'Party restores 15% health and 20% endurance. 90-second reuse.',12:'Break stun, mez and snares; immune to those effects for 3 seconds. Usable while controlled.',
 13:'Full base and specialization buffs to all eight stats, scaling with your level.',14:'Additional magic resistance outside the normal buff cap.',
 15:'Weapon-dependent procs: hammer lightning, sword healing, axe frost, spear lightning arc; blocks can grant a protective ward.',
 16:'Taunt your enemy to protect your allies.',17:'From stealth: mark an enemy. Your next melee hit against it deals 30% additional damage.',
 18:'Parrying an attack returns lightning damage. Lasts 8 seconds.',19:'Summon a permanent Storm Wolf at your level: 4x pet health, double damage (triple during Storm Crown), and its hits heal it for 30% of the damage dealt. It shares stealth.',
 20:'Royal storm transformation for one minute: +50% melee damage, double royal spell damage, royal spells cast in at most 0.25 seconds, +20% absorption, +20% melee haste, 10% health/power/endurance every 4 seconds, 1.5x life/power/endurance steal and lightning pulses. Three-minute reuse.',
 21:'Throw a Thane hammer and teleport beside an enemy within 2100. Strong primary impact, half damage around it; +10 critical chance on the primary hit from stealth. Instant; 15-second reuse.',
 22:'A maintained winter veil helps concealment and increases movement while hidden.'}
STYLE_NAMES={
 'Hammer':['Thunderstroke','Shatterguard','Thunder Reprisal','Winterfall','Royal Verdict',"Thor's Judgement",'Hidden Thunder'],
 'Sword':['Crowned Slash',"King's Reprieve",'Royal Riposte','Wintercut','Crownstrike',"Sovereign's Edge",'Silent Coronation'],
 'Axe':['Winterbite','Bloodmark','Royal Fury','Frost Rend','Winter Verdict',"Executioner's Storm",'Hidden Wrath'],
 'Spear':['Storm Thrust','Pierce the Veil','Storm Counter',"Winter's Reach",'Stormbind',"Gungnir's Echo",'Silent Spear'],
 'Shields':['Royal Rebuke','Break Their Guard','Hold the Throne','Shield Rush','Crownfall','The Unbroken Crown','Hidden Crown']}

PRIVATE_RAS = (
 ('Sovereign_RoyalFortitude','Royal Fortitude',1900,3536,'SovereignRoyalFortitude','Maximum health +3/6/9%. Three ranks, incremental costs 2/4/6 realm skill points.'),
 ('Sovereign_StormMastery','Storm Mastery',1901,3541,'SovereignStormMastery','Melee and spell damage +2/4/6%. Three ranks, incremental costs 2/4/6 realm skill points.'),
 ('Sovereign_CrownsResolve',"Crown's Resolve",1902,3537,'SovereignCrownsResolve','All nine secondary resists +2/4/6%. Three ranks, incremental costs 2/4/6 realm skill points.'),
 ('Sovereign_WrathOfTheCrown','Wrath of the Crown',1903,3528,'SovereignWrathOfTheCrown','Free RR5 ability: empower you and your Storm Wolf for 20 seconds (+20% melee/spell damage, +10% melee/spell critical chance), then unleash 300 energy damage within 500. Five-minute reuse.'))

def seed_realm_abilities(db):
 ability_base=source_row(db,'Ability',"KeyName='AtlasOF_AugStr'")
 binding_base=source_row(db,'ClassXRealmAbility_Atlas','CharClass=21')
 extra=['AtlasOF_MasteryOfMagery','AtlasOF_WildPower','AtlasOF_WildMinion','AtlasOF_MasteryOfStealth']
 for key,name,internal,icon,implementation,description in PRIVATE_RAS:
  if db.execute('select 1 from Ability where InternalID=? and KeyName<>?',(internal,key)).fetchone(): raise ValueError('Private RA identity collision')
  # Keep existing AbilityID on reseeds so previously trained RAs retain their identity.
  exists=db.execute('select 1 from Ability where KeyName=?',(key,)).fetchone()
  values=(name,description,internal,icon,'DOL.GS.RealmAbilities.'+implementation)
  if exists:
   db.execute('update Ability set Name=?,Description=?,InternalID=?,IconID=?,Implementation=? where KeyName=?',values+(key,))
  else:
   row_copy(db,'Ability',ability_base,dict(KeyName=key,Name=name,Description=description,InternalID=internal,IconID=icon,Implementation=values[-1]))
  extra.append(key)
 for key in extra:
  if not db.execute('select 1 from Ability where KeyName=?',(key,)).fetchone(): raise ValueError('Missing realm ability '+key)
  if not db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=64 and AbilityKey=?',(key,)).fetchone():
   row_copy(db,'ClassXRealmAbility_Atlas',binding_base,dict(CharClass=64,AbilityKey=key))


def seed(db):
 db.row_factory=sqlite3.Row
 # The legacy migration is kept as a tested bootstrap for starter equipment, realm abilities and race locations.
 # Permit our added Spear career before calling its class-64 collision check.
 additions=db.execute("select * from ClassXSpecialization where ClassID=64 and SpecKeyName='Spear'").fetchall()
 db.execute("delete from ClassXSpecialization where ClassID=64 and SpecKeyName='Spear'")
 legacy_seed(db)
 spell_base=source_row(db,'Spell','SpellID=3508')
 line_base=source_row(db,'SpellLine','1=1')
 link_base=source_row(db,'LineXSpell','1=1')
 for r in db.execute('select SpellID from Spell where PackageID=?',(PACKAGE,)).fetchall():
  db.execute('delete from LineXSpell where SpellID=?',(r[0],))
 db.execute('delete from Spell where PackageID=?',(PACKAGE,))
 db.execute("delete from SpellLine where KeyName like 'Stormforged.%'")
 db.execute('delete from Style where ClassId=64')
 db.execute('delete from StyleXSpell where ClassID=64')
 db.execute("update Specialization set Name='Storm Sovereign',Description='Royal storm magic and automatic weapon training.' where KeyName=?",(CAREER,))
 row_copy(db,'ClassXSpecialization',source_row(db,'ClassXSpecialization','ClassID=64'),dict(ClassID=64,SpecKeyName='Spear',LevelAcquired=-10))
 row_copy(db,'SpecXAbility',source_row(db,'SpecXAbility','Spec=?',(CAREER,)),dict(Spec=CAREER,SpecLevel=1,AbilityKey='Weaponry: Spears',AbilityLevel=0,ClassId=64))
 # Every inserted spell explicitly resets inherited stock behavior.
 defaults=dict(Target='Self',Range=0,Radius=0,Power=0,CastTime=0,Damage=0,DamageType=12,Duration=0,Frequency=0,Pulse=0,
  PulsePower=0,RecastDelay=0,Value=0,LifeDrainReturn=0,SpellGroup=0,EffectGroup=0,SubSpellID=0,SharedTimerGroup=0,
  MoveCast=0,Uninterruptible=0,IsFocus=0,Concentration=0,ClientEffect=3508,Icon=3508)
 def spell(id,name,type,level,fields,description='',line=None):
  data=dict(defaults,SpellID=id,Spell_ID=f'sovereign-{id}',Name=name,Description=description,Type=type,PackageID=PACKAGE,TooltipId=24000+id-62400)
  data.update(fields)
  data['Icon']=data['ClientEffect']
  if db.execute('select 1 from Spell where TooltipId=?',(data['TooltipId'],)).fetchone(): raise ValueError('Tooltip collision')
  row_copy(db,'Spell',spell_base,data)
  if line: row_copy(db,'LineXSpell',link_base,dict(LineName=line,SpellID=id,Level=level))
 for key,name,unlock,target,type,settings in SPELLS:
  line=f'Stormforged.Sovereign{key:02}'
  row_copy(db,'SpellLine',line_base,dict(KeyName=line,Name=name,Spec=CAREER,IsBaseLine=1,ClassIDHint=64))
  ranks=sorted(set([unlock]+[n for n in LEVELS if n>=unlock]))
  for level in ranks:
   # Fixed table tiers; unlocks between tiers use the next tier's ID but retain actual acquisition level.
   tier=max(i for i,n in enumerate(LEVELS) if n<=level)
   id=62400+tier*32+key
   if db.execute('select 1 from Spell where SpellID=?',(id,)).fetchone(): continue
   fields=dict(settings,Target=target,SpellGroup=62400+key)
   if key==6:
    cap=min(level,40); fields.update(Value=125+cap*2,Damage=10+cap,SubSpellID=62900+tier)
    spell(62900+tier,'Royal Presence Damage Add','DamageAdd',level,dict(Target='Realm',Range=1500,Duration=9,Damage=2+cap*.175,ClientEffect=0))
   elif key==20:
    fields['SubSpellID']=62400+tier*32+24
    spell(fields['SubSpellID'],'Storm Crown Lightning','StormSovereignAbility',level,dict(Target='Self',Radius=350,Damage=100,ClientEffect=3528))
   elif key==19: pass
   elif 'Damage' in fields and fields['Damage']>0: fields['Damage']=max(5,int(fields['Damage']*level/50))
   fields['Power']=max(1,int(fields.get('Power',0)*max(.2,level/50))) if fields.get('Power',0)>0 else 0
   spell(id,name,'StormSovereignAbility' if type=='StormSovereignAbility' else type,level,fields,DESCRIPTIONS[key],line)
 spell(62960,'Wrath of the Crown','StormSovereignAbility',50,dict(Target='Self',Radius=500,Damage=300,Duration=20,ClientEffect=3528),
       'RR5: empower you and your nearby Storm Wolf for 20 seconds: +20% melee/spell damage, +10% melee/spell critical chance; immediately unleash 300 energy damage within 500. Five-minute reuse. Automatically granted at realm rank 5.')
 seed_realm_abilities(db)
 # One physical wolf. No commander/support/turret buttons remain in the new spellbook.
 db.execute("update NpcTemplate set Name='Storm Wolf',Model='459',Size='50',Spells='62950;62951',TetherRange=0 where TemplateId=60171001")
 spell(62950,'Storm Wolf Frostbite','DamageSpeedDecrease',1,dict(Target='Enemy',Range=250,Damage=60,Value=20,Duration=4,RecastDelay=12,ClientEffect=14321))
 spell(62951,'Storm Wolf Lightning','DirectDamage',1,dict(Target='Enemy',Range=500,Damage=80,RecastDelay=15,ClientEffect=3509))
 style_base=source_row(db,'Style','ClassId=21')
 proc_base=source_row(db,'StyleXSpell','1=1')
 style_levels=(1,10,20,30,40,50,15)
 for wi,(spec,names) in enumerate(STYLE_NAMES.items()):
  native=source_row(db,'Style','SpecKeyName=? and ClassId<>64',(spec,))
  for action,name in enumerate(names):
   id=1800+wi*7+action
   if db.execute('select 1 from Style where ID=?',(id,)).fetchone(): raise ValueError(f'Style ID collision {id}')
   row_copy(db,'Style',style_base,dict(ID=id,ClassId=64,Name=name,SpecKeyName=spec,SpecLevelRequirement=style_levels[action],
    Icon=native['Icon'],EnduranceCost=10 if action<4 else 15,StealthRequirement=int(action==6),
    OpeningRequirementType=1 if action==2 else 2 if action==3 else 0,
    OpeningRequirementValue=0 if action!=1 and action!=4 else 1800+wi*7+(0 if action==1 else 1),
    AttackResultRequirement=(4 if wi==4 else 3) if action==2 else 7 if action in (1,4) else 0,
    WeaponTypeRequirement={'Sword':11,'Hammer':12,'Axe':13,'Spear':14,'Shields':42}[spec],
    GrowthOffset=0,GrowthRate=.55+action*.06,BonusToHit=10,BonusToDefense=5,TwoHandAnimation=native['TwoHandAnimation'],RandomProc=0,ArmorHitLocation=0))
   proc=62700+wi*7+action
   detail='3-second stun (4 seconds for shield), requires the preceding chain.' if action==4 else 'Weapon-specific lightning/frost damage, control or defensive effect; scales with character level.'
   spell(proc,name+' Effect','StormSovereignAbility',1,dict(Target='Enemy',Duration=10,ClientEffect=3541),detail)
   row_copy(db,'StyleXSpell',proc_base,dict(SpellID=proc,ClassID=64,StyleID=id,Chance=100))
 db.execute("update Mob set Name='Crownkeeper',Guild='Storm Sovereign Trainer' where Mob_ID='stormforged-trainer'")
 from seed_decree_chambers import seed as seed_chambers
 seed_chambers(db,classes=(64,))
 return dict(class_id=64,name='Storm Sovereign',styles=35,spell_ranks=db.execute('select count(*) from Spell where PackageID=?',(PACKAGE,)).fetchone()[0],player_tables_changed=False)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('database',type=Path);args=parser.parse_args()
 with sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(':memory:') as preview:
  src.backup(preview)
  with preview: print(json.dumps(seed(preview),indent=2))
