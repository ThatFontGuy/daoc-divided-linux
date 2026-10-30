"""Add Albion's Pendragon using the installed Midgard Sovereign as its balance source.

Never reseed or change Midgard, stock classes, or player progress. The installer wraps
this in a checked private database transaction before deploying a backed-up copy.
"""
import sqlite3
from seed_sovereign import row_copy, source_row

CLASS=65
PACKAGE='OfflineDAoC.Pendragon.v1'
CAREER='PendragonCareer'
OFFSET=1600
TEMPLATE=60172001
NAMES=['Crownfire Lance','Binding Radiance','Royal Smite','Chains of the Crown','Crownfire Burst',
       'Field of Judgement','Royal Procession','Decree: Advance','Decree: Stand Fast','Decree: Strike True',
       "Sovereign's Renewal",'Rally to the Crown','Will of the Pendragon','Armor of the Crown','Sacred Ward',
       'Consecrated Armament',"Sovereign's Challenge",'Royal Ambush','Radiant Reversal','Royal Lion',
       'Lion of Albion',"King's Advance",'Veil of Avalon']
# Installed stock spell effects: wizard fire, cleric smite/heal, paladin buffs.
FX={0:313,1:1605,2:1605,3:316,4:316,5:307,6:1678,7:1678,8:1506,9:1457,10:15314,11:15319,
    12:1506,13:1457,14:1506,15:1678,16:1605,17:1678,18:1506,19:1457,20:1678,21:316,22:1506,24:316}
STYLE_NAMES={
 'Crush':['Crownstrike','Shatterguard','Royal Reprisal','Judgement Fall','Royal Verdict','Hammer of Albion','Hidden Judgement'],
 'Slash':['Crowned Slash',"King's Reprieve",'Royal Riposte','Sunlit Cut','Crownstrike',"Sovereign's Edge",'Silent Coronation'],
 'Thrust':['Radiant Sting','Bloodmark','Royal Fury','Searing Rend','Burning Verdict',"Executioner's Light",'Hidden Wrath'],
 'Polearm':['Royal Thrust','Pierce the Veil','Royal Counter','Crownreach','Sunbind',"Dragon's Reach",'Silent Sentinel'],
 'Shields':['Royal Rebuke','Break Their Guard','Hold the Throne','Shield Rush','Crownfall','The Unbroken Crown','Hidden Crown'],
 'Two Handed':['Royal Cleave','Shatter the Line','Crown Reprisal','Judgement Sweep','The Final Decree',"Pendragon's Verdict",'Hidden Majesty']}
SPEC_MAP={'Hammer':'Crush','Sword':'Slash','Axe':'Thrust','Spear':'Polearm','Shields':'Shields','Parry':'Parry','Stealth':'Stealth',
          'StormforgedCareer':CAREER,'CharacterStyleUserCareer':'CharacterStyleUserCareer'}

def themed(text):
 for old,new in [('Storm Sovereign','Pendragon Sovereign'),('Storm Wolf','Royal Lion'),('Storm Crown','Lion of Albion'),
                 ('royal storm','royal radiance'),('winter','radiant'),('Winter','Radiant'),('frost','holy fire'),
                 ('Frost','Holy Fire'),('lightning','holy fire'),('Lightning','Holy Fire'),('energy','heat'),
                 ('Cold damage','Heat damage'),('cold damage','heat damage'),('Thane hammer','royal blade'),
                 ('Runic','Sacred'),('Stormbreak','Crownfire Burst')]:
  text=text.replace(old,new)
 return text

def seed(db):
 db.row_factory=sqlite3.Row
 source_spells=db.execute('select * from Spell where SpellID between 62400 and 62960 and PackageID=?',('OfflineDAoC.Stormforged.v1',)).fetchall()
 if len(source_spells)<150: raise ValueError('Install the current Storm Sovereign first')
 for row in db.execute('select SpellID,PackageID from Spell where SpellID between 64000 and 64560'):
  if row['PackageID']!=PACKAGE: raise ValueError('Pendragon spell identity collision')
 for row in db.execute('select SpecKeyName from ClassXSpecialization where ClassID=65'):
  if row[0] not in set(SPEC_MAP.values())|{'Two Handed'}: raise ValueError('Class 65 already in use')
 existing=db.execute('select PackageID from NpcTemplate where TemplateId=?',(TEMPLATE,)).fetchone()
 if existing and existing[0]!=PACKAGE: raise ValueError('Royal Lion template collision')
 for row in db.execute('select ID,ClassId from Style where ID between 1900 and 1941'):
  if row['ClassId']!=CLASS: raise ValueError('Pendragon style identity collision')
 db.execute('delete from LineXSpell where SpellID in (select SpellID from Spell where PackageID=?)',(PACKAGE,))
 for table,where,args in [('Spell','PackageID=?',(PACKAGE,)),('SpellLine',"KeyName like 'Pendragon.%'",()),
  ('Style','ClassId=65',()),('StyleXSpell','ClassID=65',()),('ClassXSpecialization','ClassID=65',()),
  ('SpecXAbility','Spec=?',(CAREER,)),('Specialization','KeyName=?',(CAREER,))]:
  db.execute('delete from '+table+' where '+where,args)
 row_copy(db,'Specialization',source_row(db,'Specialization',"KeyName='StormforgedCareer'"),
          dict(KeyName=CAREER,Name='Pendragon Sovereign',Description='Royal holy fire and automatic weapon training.'))
 for row in db.execute('select * from ClassXSpecialization where ClassID=64').fetchall():
  row_copy(db,'ClassXSpecialization',row,dict(ClassID=65,SpecKeyName=SPEC_MAP[row['SpecKeyName']]))
 row_copy(db,'ClassXSpecialization',source_row(db,'ClassXSpecialization','ClassID=64'),dict(ClassID=65,SpecKeyName='Two Handed',LevelAcquired=-11))
 weapon_map={'Weaponry: Swords':'Weaponry: Slashing','Weaponry: Hammers':'Weaponry: Crushing',
             'Weaponry: Axes':'Weaponry: Thrusting','Weaponry: Spears':'Weaponry: Polearms','MidArmor':'AlbArmor'}
 for row in db.execute("select * from SpecXAbility where Spec='StormforgedCareer'").fetchall():
  key=weapon_map.get(row['AbilityKey'],row['AbilityKey'])
  source_row(db,'Ability','KeyName=?',(key,))
  row_copy(db,'SpecXAbility',row,dict(Spec=CAREER,ClassId=65,AbilityKey=key,AbilityLevel=5 if key=='AlbArmor' else row['AbilityLevel']))
 row_copy(db,'SpecXAbility',source_row(db,'SpecXAbility','Spec=?',(CAREER,)),
          dict(Spec=CAREER,SpecLevel=1,ClassId=65,AbilityKey='Weaponry: Two Handed',AbilityLevel=0))
 for row in db.execute("select * from SpellLine where KeyName like 'Stormforged.%'").fetchall():
  key=int(row['KeyName'].rsplit('Sovereign',1)[1])
  row_copy(db,'SpellLine',row,dict(KeyName=row['KeyName'].replace('Stormforged.','Pendragon.'),Name=NAMES[key],Spec=CAREER,ClassIDHint=65))
 for row in source_spells:
  old=row['SpellID'];new=old+OFFSET;key=(old-62400)%32
  name=NAMES[key] if old<62656 and key<len(NAMES) else themed(row['Name'])
  changes=dict(SpellID=new,Spell_ID='pendragon-'+str(new),PackageID=PACKAGE,Name=name,Description=themed(row['Description'] or ''),
               TooltipId=26000+new-64000,DamageType=10)
  if row['SubSpellID']: changes['SubSpellID']=row['SubSpellID']+OFFSET
  if row['SpellGroup']: changes['SpellGroup']=row['SpellGroup']+OFFSET
  if old<62656:
   changes.update(Icon=FX.get(key,316),ClientEffect=FX.get(key,316))
   if key==19: changes['LifeDrainReturn']=TEMPLATE
   if key==20: changes['Value']=1193
  elif old in (62950,62951): changes.update(Icon=313,ClientEffect=313,Name='Royal Lion '+('Searing Bite' if old==62950 else 'Crownfire'))
  elif old==62960: changes.update(Icon=316,ClientEffect=316,Name='Wrath of the Pendragon')
  elif 62700<=old<62735: changes.update(Icon=316,ClientEffect=316)
  if db.execute('select 1 from Spell where TooltipId=?',(changes['TooltipId'],)).fetchone(): raise ValueError('Pendragon tooltip collision')
  row_copy(db,'Spell',row,changes)
  for link in db.execute('select * from LineXSpell where SpellID=?',(old,)).fetchall():
   row_copy(db,'LineXSpell',link,dict(SpellID=new,LineName=link['LineName'].replace('Stormforged.','Pendragon.')))
 # Two-handed gets its own seven styles using the same power profile as Crush.
 for index,(spec,names) in enumerate(STYLE_NAMES.items()):
  native=source_row(db,'Style','ClassId=2 and SpecKeyName=?',(spec,))
  for action,name in enumerate(names):
   old_index=(index if index<5 else 0)*7+action
   original=source_row(db,'Style','ClassId=64 and ID=?',(1800+old_index,))
   new_id=1900+index*7+action;proc=64300+index*7+action
   opening=original['OpeningRequirementValue']
   if opening: opening=new_id-action+(opening-(1800+old_index-action))
   row_copy(db,'Style',original,dict(ClassId=65,ID=new_id,Name=name,SpecKeyName=spec,Icon=native['Icon'],
       WeaponTypeRequirement=native['WeaponTypeRequirement'],TwoHandAnimation=native['TwoHandAnimation'],OpeningRequirementValue=opening))
   if index==5:
    source=source_row(db,'Spell','SpellID=?',(64300+action,))
    row_copy(db,'Spell',source,dict(SpellID=proc,Spell_ID='pendragon-'+str(proc),TooltipId=26000+proc-64000,Name=name+' Effect'))
   else: db.execute('update Spell set Name=? where SpellID=?',(name+' Effect',proc))
   row_copy(db,'StyleXSpell',source_row(db,'StyleXSpell','ClassID=64 and StyleID=?',(1800+old_index,)),dict(ClassID=65,StyleID=new_id,SpellID=proc))
 db.execute('delete from NpcTemplate where TemplateId=?',(TEMPLATE,))
 row_copy(db,'NpcTemplate',source_row(db,'NpcTemplate','TemplateId=60171001'),
          dict(TemplateId=TEMPLATE,Name='Royal Lion',Model='100',Spells='64550;64551',PackageID=PACKAGE))
 # Separate keys/identities, shared executable RA scaling and cooldowns.
 db.execute('delete from ClassXRealmAbility_Atlas where CharClass=65')
 for binding in db.execute('select * from ClassXRealmAbility_Atlas where CharClass=64').fetchall():
  old=binding['AbilityKey'];key=old
  if old.startswith('Sovereign_'):
   key=old.replace('Sovereign_','Pendragon_',1);original=source_row(db,'Ability','KeyName=?',(old,))
   internal=original['InternalID']+20
   if db.execute('select 1 from Ability where InternalID=? and KeyName<>?',(internal,key)).fetchone(): raise ValueError('Pendragon RA identity collision')
   exists=db.execute('select 1 from Ability where KeyName=?',(key,)).fetchone()
   if not exists: row_copy(db,'Ability',original,dict(KeyName=key,InternalID=internal,Name=themed(original['Name']).replace('Wrath of the Crown','Wrath of the Pendragon'),Description=themed(original['Description']),IconID=316 if old.endswith('WrathOfTheCrown') else 1506))
  row_copy(db,'ClassXRealmAbility_Atlas',binding,dict(CharClass=65,AbilityKey=key))
 db.execute('delete from StartupLocation where ClassID=65')
 for row in db.execute('select * from StartupLocation where ClassID=1').fetchall(): row_copy(db,'StartupLocation',row,dict(ClassID=65))
 row_copy(db,'StartupLocation',source_row(db,'StartupLocation','ClassID=1'),dict(ClassID=65,RaceID=0))
 db.execute("delete from StarterEquipment where Class='65'")
 starter=source_row(db,'StarterEquipment','1=1')
 for item in ['bronze_breastplate','bronze_plate_arms','bronze_plate_boots','bronze_plate_gauntlets','bronze_plate_helm','bronze_plate_legs','practice_sword','rowan_tower_shield2']:
  source_row(db,'ItemTemplate','Id_nb=?',(item,))
  row_copy(db,'StarterEquipment',starter,dict(Class='65',TemplateID=item))
 trainer=source_row(db,'Mob',"Guild='Paladin Trainer' and Region=10")
 db.execute("delete from Mob where Mob_ID='pendragon-trainer'")
 row_copy(db,'Mob',trainer,dict(Mob_ID='pendragon-trainer',Name='Crownwarden',Guild='Pendragon Sovereign Trainer',ClassType='DOL.GS.Trainer.PendragonTrainer',X=trainer['X']+120,NPCTemplateID=0,PackageID=PACKAGE))
 if db.execute("select 1 from ServerProperty where Key='enable_pendragon'").fetchone(): db.execute("update ServerProperty set Value='True' where Key='enable_pendragon'")
 else: row_copy(db,'ServerProperty',source_row(db,'ServerProperty',"Key='enable_stormforged'"),dict(Key='enable_pendragon',ServerProperty_ID='enable_pendragon',Value='True',DefaultValue='False',Description='Enable Albion Pendragon Sovereign.'))
 from seed_decree_chambers import seed as seed_chambers
 seed_chambers(db,classes=(65,))
 return dict(class_id=65,name='Pendragon Sovereign',styles=42,spell_ranks=len(source_spells)+7,player_tables_changed=False)
