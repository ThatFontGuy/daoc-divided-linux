"""Add Hibernia's Tuatha Sovereign using the installed Midgard Sovereign as its balance source.

Never reseed or change Midgard, Albion, stock classes, or player progress. The installer wraps
this in a checked private database transaction before deploying a backed-up copy.
"""
import sqlite3
from seed_sovereign import row_copy, source_row

CLASS=67
PACKAGE='OfflineDAoC.Tuatha.v1'
CAREER='TuathaCareer'
OFFSET=10600
FIRST,LAST=73000,73572
# The client reads tooltip IDs as signed 16-bit: keep every one at or below 32767.
TOOLTIP=25000
TEMPLATE=60173001
COMPANION_MODEL=576   # stock faerie drake
CROWN_MODEL=339       # stock sidhe tiarna (Sidhe lord)
STYLE_BASE=2200
# Style's own primary key: a fixed block, never SQLite's next free value (Death Knight owns 6600-6699).
STYLE_KEY=6700
NAMES=['Spirit Lance','Grasp of the Bramble',"Tara's Judgement",'Ring of the Sidhe','Otherworld Burst',
       'Fairy Ring','Court of the Sidhe','Decree: Advance','Decree: Stand Fast','Decree: Strike True',
       "Sovereign's Renewal",'Rally to the Crown','Will of the Tuatha','Armor of the Crown','Glamour Ward',
       'Wildwood Armament',"Sovereign's Challenge",'Glamoured Ambush','Thorn Reversal','Faerie Drake',
       'Otherworld Ascendant','Step Between Worlds','Veil of the Sidhe']
# Installed stock Hibernian effects: Champion Valor, Animist paths, Mentalist and Druid lines.
FX={0:5433,1:5439,2:5433,3:11025,4:11025,5:11338,6:5445,7:5445,8:11523,9:5005,10:4828,11:4608,
    12:11523,13:5019,14:11008,15:5005,16:5426,17:5417,18:11025,19:11331,20:5445,21:11314,22:11008,24:11025}
STYLE_FX=11019
WRATH_FX=11314
# Index order follows the Midgard weapons: Hammer, Sword, Axe, Spear, Shields; then the extra line.
STYLE_NAMES={
 'Blunt':['Cairnstrike','Shatter the Oath','Hillfort Reprisal','Fall of Tara','Verdict of the Mound','Hammer of the Dagda','Hidden Cairn'],
 'Blades':['Sidhe Slash',"Queen's Reprieve",'Court Riposte','Moonlit Cut','Crownstrike of Tara',"Nuada's Edge",'Silent Glamour'],
 'Piercing':['Thornsting','Bloodbriar','Wild Fury','Bramble Rend','Barbed Verdict',"Morrigan's Kiss",'Hidden Thorn'],
 'Celtic Spear':['Royal Thrust','Pierce the Veil','Spear Counter','Reach of Lugh','Spirit Bind','Gae Bolga','Silent Sentinel'],
 'Shields':['Royal Rebuke','Break Their Guard','Hold the Mound','Shield Rush','Crownfall','The Unbroken Court','Hidden Crown'],
 'Large Weapons':['Royal Cleave','Shatter the Line','Court Reprisal','Judgement Sweep','The Final Decree',"Ard Ri's Verdict",'Hidden Majesty']}
SPEC_MAP={'Hammer':'Blunt','Sword':'Blades','Axe':'Piercing','Spear':'Celtic Spear','Shields':'Shields','Parry':'Parry','Stealth':'Stealth',
          'StormforgedCareer':CAREER,'CharacterStyleUserCareer':'CharacterStyleUserCareer'}
WEAPON_MAP={'Weaponry: Swords':'Weaponry: Blades','Weaponry: Hammers':'Weaponry: Blunt','Weaponry: Axes':'Weaponry: Piercing',
            'Weaponry: Spears':'Weaponry: Celtic Spears','MidArmor':'HibArmor'}
STARTER=['cruanach_coif','cruanach_gloves','cruanach_boots','cruanach_hauberk','cruanach_leggings','cruanach_sleeves',
         'short_sword','elm_tower_shield3']

def themed(text):
 for old,new in [('Storm Sovereign','Tuatha Sovereign'),('Storm Wolf','Faerie Drake'),('Storm Crown','Otherworld Ascendant'),
                 ('royal storm','royal glamour'),('winter','glamour'),('Winter','Glamour'),('frost','spirit'),
                 ('Frost','Spirit'),('lightning','spirit'),('Lightning','Spirit'),('energy','spirit'),
                 ('Cold damage','Spirit damage'),('cold damage','spirit damage'),('Thane hammer','spirit spear'),
                 ('Runic','Glamour'),('Stormbreak','Otherworld Burst'),('wolf','drake'),('Wolf','Drake')]:
  text=text.replace(old,new)
 return text

def seed(db):
 db.row_factory=sqlite3.Row
 source_spells=db.execute('select * from Spell where SpellID between 62400 and 62960 and PackageID=?',('OfflineDAoC.Stormforged.v1',)).fetchall()
 if len(source_spells)<150: raise ValueError('Install the current Storm Sovereign first')
 # Reject collisions before deleting anything; all our IDs are stable across reseeds.
 for row in db.execute('select SpellID,PackageID from Spell where SpellID between ? and ?',(FIRST,LAST)):
  if row['PackageID']!=PACKAGE: raise ValueError('Tuatha spell identity collision')
 for row in db.execute('select PackageID from Spell where TooltipId between ? and ?',(TOOLTIP,TOOLTIP+LAST-FIRST)):
  if row['PackageID']!=PACKAGE: raise ValueError('Tuatha tooltip collision')
 for row in db.execute('select SpecKeyName from ClassXSpecialization where ClassID=?',(CLASS,)):
  if row[0] not in set(SPEC_MAP.values())|{'Large Weapons'}: raise ValueError('Class 67 already in use')
 existing=db.execute('select PackageID from NpcTemplate where TemplateId=?',(TEMPLATE,)).fetchone()
 if existing and existing[0]!=PACKAGE: raise ValueError('Faerie Drake template collision')
 for row in db.execute('select ID,ClassId from Style where ID between ? and ?',(STYLE_BASE,STYLE_BASE+41)):
  if row['ClassId']!=CLASS: raise ValueError('Tuatha style identity collision')
 for row in db.execute('select StyleID,ClassId from Style where StyleID between ? and ?',(STYLE_KEY,STYLE_KEY+41)):
  if row['ClassId']!=CLASS: raise ValueError('Tuatha StyleID collision')
 db.execute('delete from LineXSpell where SpellID in (select SpellID from Spell where PackageID=?)',(PACKAGE,))
 for table,where,args in [('Spell','PackageID=?',(PACKAGE,)),('SpellLine',"KeyName like 'Tuatha.%'",()),
  ('Style','ClassId=?',(CLASS,)),('StyleXSpell','ClassID=?',(CLASS,)),('ClassXSpecialization','ClassID=?',(CLASS,)),
  ('SpecXAbility','Spec=?',(CAREER,)),('Specialization','KeyName=?',(CAREER,))]:
  db.execute('delete from '+table+' where '+where,args)
 row_copy(db,'Specialization',source_row(db,'Specialization',"KeyName='StormforgedCareer'"),
          dict(KeyName=CAREER,Name='Tuatha Sovereign',Description='Royal spirit magic and automatic weapon training.'))
 for row in db.execute('select * from ClassXSpecialization where ClassID=64').fetchall():
  row_copy(db,'ClassXSpecialization',row,dict(ClassID=CLASS,SpecKeyName=SPEC_MAP[row['SpecKeyName']]))
 row_copy(db,'ClassXSpecialization',source_row(db,'ClassXSpecialization','ClassID=64'),dict(ClassID=CLASS,SpecKeyName='Large Weapons',LevelAcquired=-11))
 for row in db.execute("select * from SpecXAbility where Spec='StormforgedCareer'").fetchall():
  key=WEAPON_MAP.get(row['AbilityKey'],row['AbilityKey'])
  source_row(db,'Ability','KeyName=?',(key,))
  row_copy(db,'SpecXAbility',row,dict(Spec=CAREER,ClassId=CLASS,AbilityKey=key))
 row_copy(db,'SpecXAbility',source_row(db,'SpecXAbility','Spec=?',(CAREER,)),
          dict(Spec=CAREER,SpecLevel=1,ClassId=CLASS,AbilityKey='Weaponry: Large Weapons',AbilityLevel=0))
 for row in db.execute("select * from SpellLine where KeyName like 'Stormforged.%'").fetchall():
  key=int(row['KeyName'].rsplit('Sovereign',1)[1])
  row_copy(db,'SpellLine',row,dict(KeyName=row['KeyName'].replace('Stormforged.','Tuatha.'),Name=NAMES[key],Spec=CAREER,ClassIDHint=CLASS))
 for row in source_spells:
  old=row['SpellID'];new=old+OFFSET;key=(old-62400)%32
  name=NAMES[key] if old<62656 and key<len(NAMES) else themed(row['Name'])
  changes=dict(SpellID=new,Spell_ID='tuatha-'+str(new),PackageID=PACKAGE,Name=name,Description=themed(row['Description'] or ''),
               TooltipId=TOOLTIP+new-FIRST,DamageType=15)
  if row['SubSpellID']: changes['SubSpellID']=row['SubSpellID']+OFFSET
  if row['SpellGroup']: changes['SpellGroup']=row['SpellGroup']+OFFSET
  if old<62656:
   changes.update(Icon=FX.get(key,11025),ClientEffect=FX.get(key,11025))
   if key==19: changes['LifeDrainReturn']=TEMPLATE
   if key==20: changes['Value']=CROWN_MODEL
  elif old in (62950,62951): changes.update(Icon=4618,ClientEffect=4618,Name='Faerie Drake '+('Spirit Bite' if old==62950 else 'Glamourfire'))
  elif old==62960: changes.update(Icon=WRATH_FX,ClientEffect=WRATH_FX,Name='Wrath of the Tuatha')
  elif 62700<=old<62735: changes.update(Icon=STYLE_FX,ClientEffect=STYLE_FX)
  row_copy(db,'Spell',row,changes)
  for link in db.execute('select * from LineXSpell where SpellID=?',(old,)).fetchall():
   row_copy(db,'LineXSpell',link,dict(SpellID=new,LineName=link['LineName'].replace('Stormforged.','Tuatha.')))
 # Large Weapons gets its own seven styles using the same power profile as Blunt.
 for index,(spec,names) in enumerate(STYLE_NAMES.items()):
  native=source_row(db,'Style','ClassId=44 and SpecKeyName=?',(spec,))
  for action,name in enumerate(names):
   old_index=(index if index<5 else 0)*7+action
   original=source_row(db,'Style','ClassId=64 and ID=?',(1800+old_index,))
   new_id=STYLE_BASE+index*7+action;proc=73300+index*7+action
   opening=original['OpeningRequirementValue']
   if opening: opening=new_id-action+(opening-(1800+old_index-action))
   row_copy(db,'Style',original,dict(StyleID=STYLE_KEY+index*7+action,ClassId=CLASS,ID=new_id,Name=name,SpecKeyName=spec,Icon=native['Icon'],
       WeaponTypeRequirement=native['WeaponTypeRequirement'],TwoHandAnimation=native['TwoHandAnimation'],OpeningRequirementValue=opening))
   if index==5:
    source=source_row(db,'Spell','SpellID=?',(73300+action,))
    row_copy(db,'Spell',source,dict(SpellID=proc,Spell_ID='tuatha-'+str(proc),TooltipId=TOOLTIP+proc-FIRST,Name=name+' Effect'))
   else: db.execute('update Spell set Name=? where SpellID=?',(name+' Effect',proc))
   row_copy(db,'StyleXSpell',source_row(db,'StyleXSpell','ClassID=64 and StyleID=?',(1800+old_index,)),dict(ClassID=CLASS,StyleID=new_id,SpellID=proc))
 db.execute('delete from NpcTemplate where TemplateId=?',(TEMPLATE,))
 row_copy(db,'NpcTemplate',source_row(db,'NpcTemplate','TemplateId=60171001'),
          dict(TemplateId=TEMPLATE,Name='Faerie Drake',Model=str(COMPANION_MODEL),Spells='73550;73551',PackageID=PACKAGE))
 # Separate keys/identities, shared executable RA scaling and cooldowns.
 db.execute('delete from ClassXRealmAbility_Atlas where CharClass=?',(CLASS,))
 for binding in db.execute('select * from ClassXRealmAbility_Atlas where CharClass=64').fetchall():
  old=binding['AbilityKey'];key=old
  if old.startswith('Sovereign_'):
   key=old.replace('Sovereign_','Tuatha_',1);original=source_row(db,'Ability','KeyName=?',(old,))
   internal=original['InternalID']+40
   if db.execute('select 1 from Ability where InternalID=? and KeyName<>?',(internal,key)).fetchone(): raise ValueError('Tuatha RA identity collision')
   if not db.execute('select 1 from Ability where KeyName=?',(key,)).fetchone():
    row_copy(db,'Ability',original,dict(KeyName=key,InternalID=internal,Name=themed(original['Name']).replace('Wrath of the Crown','Wrath of the Tuatha'),
             Description=themed(original['Description']),IconID=WRATH_FX if old.endswith('WrathOfTheCrown') else 5445))
  row_copy(db,'ClassXRealmAbility_Atlas',binding,dict(CharClass=CLASS,AbilityKey=key))
 db.execute('delete from StartupLocation where ClassID=?',(CLASS,))
 for row in db.execute('select * from StartupLocation where ClassID=44').fetchall(): row_copy(db,'StartupLocation',row,dict(ClassID=CLASS))
 row_copy(db,'StartupLocation',source_row(db,'StartupLocation','ClassID=44'),dict(ClassID=CLASS,RaceID=0))
 db.execute('delete from StarterEquipment where Class=?',(str(CLASS),))
 starter=source_row(db,'StarterEquipment','1=1')
 for item in STARTER:
  source_row(db,'ItemTemplate','Id_nb=?',(item,))
  row_copy(db,'StarterEquipment',starter,dict(Class=str(CLASS),TemplateID=item))
 trainer=source_row(db,'Mob',"Guild='Hero Trainer' and Region=201")
 db.execute("delete from Mob where Mob_ID='tuatha-trainer'")
 row_copy(db,'Mob',trainer,dict(Mob_ID='tuatha-trainer',Name='Brehon of Tara',Guild='Tuatha Sovereign Trainer',ClassType='DOL.GS.Trainer.TuathaTrainer',
          X=trainer['X']+120,NPCTemplateID=0,PackageID=PACKAGE))
 if db.execute("select 1 from ServerProperty where Key='enable_tuatha'").fetchone(): db.execute("update ServerProperty set Value='True' where Key='enable_tuatha'")
 else: row_copy(db,'ServerProperty',source_row(db,'ServerProperty',"Key='enable_stormforged'"),dict(Key='enable_tuatha',ServerProperty_ID='enable_tuatha',Value='True',DefaultValue='False',Description='Enable the Hibernian Tuatha Sovereign.'))
 from seed_decree_chambers import seed as seed_chambers
 seed_chambers(db,classes=(CLASS,))
 return dict(class_id=CLASS,name='Tuatha Sovereign',styles=42,spell_ranks=len(source_spells)+7,player_tables_changed=False)
