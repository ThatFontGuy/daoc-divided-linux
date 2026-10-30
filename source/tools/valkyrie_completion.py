"""Finish the player Valkyrie on the existing class-library baseline. Definition-only, transactional caller."""
import sqlite3
CLASS=34
PACKAGE='local-valk-completion-v6'
VERSION='6'
# Level, name, existing visual/melee template, opening (any/block/parry/front/side/back/previous name).
SWORD=[(1,'Whirling Blade','Whirling Blade','any'),(2,'Stabbing Blade','Whirling Blade','Whirling Blade'),
 (4,'Frost Cut','Frost Cut','block'),(6,'Draw Out','Draw Out','any'),(8,'Northern Lights','Northern Lights','front'),
 (10,'Assault','Assault','Frost Cut'),(12,'Temper','Temper','any'),(15,'Aurora','Aurora','Northern Lights'),
 (18,"Baldur's Fury","Baldur's Fury",'side'),(21,'Reinforcement','Reinforcement','parry'),
 (25,'Ice Storm','Ice Storm','block'),(29,'Rush','Rush','Reinforcement'),(34,'Polar Rift','Polar Rift','any'),
 (36,"Odin's Clip","Baldur's Fury",'back'),(39,"Niord's Fury","Niord's Fury",'back'),
 (40,"Odin's Bite",'Aurora','side'),(44,"Sif's Revenge","Sif's Revenge",'Ice Storm'),
 (47,"Odin's Deathblow",'Aurora',"Odin's Bite"),(50,'Ragnarok','Ragnarok',"Niord's Fury")]
SPEAR=[(1,'Thrusting Spear','Dazzling Spear','any'),(2,'Dazzling Spear','Dazzling Spear','any'),
 (4,'Return Thrust','Return Thrust','parry'),(6,'Engage','Engage','any'),(8,'Extend Reach','Extend Reach','Return Thrust'),
 (10,'Lancer','Lancer','any'),(12,'Dismissal','Dismissal','any'),(15,'Wounding Thrust','Wounding Thrust','Engage'),
 (18,'Stab','Stab','parry'),(21,'Perforate','Perforate','side'),(25,'Lunging Thrust','Lunging Thrust','Lancer'),
 (29,'Raze','Raze','Stab'),(32,'Windmill','Dazzling Spear','any'),(34,'Whirling Spear','Whirling Spear','any'),
 (39,'Razor Edge','Razor Edge','back'),(41,'Roundhouse','Whirling Spear','Windmill'),
 (44,"Odin's Wrath","Odin's Wrath",'Razor Edge'),(50,"Gungnir's Fury","Gungnir's Fury",'Perforate')]
SHIELDS=[(1,'Smash','Numb','any'),(3,'Numb','Numb','any'),(8,'Stun','Stun','block'),(13,'Disable','Disable','side'),
 (18,'Incapacitate','Incapacitate','block'),(23,'Paralyze','Paralyze','back'),(29,'Bash','Bash','block'),
 (34,'Maneuver','Numb','any'),(35,'Mangle','Mangle','side'),(40,'Pin','Numb','any'),(42,'Slam','Slam','any'),
 (43,'Sideswipe','Mangle','Maneuver'),(47,'Brace','Numb','Pin'),(50,'Brutalize','Brutalize','block')]
# Explicit Valkyrie effects; never inherit Warrior/Hunter effect links.
EFFECTS={
 'Stabbing Blade':('bleed',8,20),'Frost Cut':('haste',16,20),'Draw Out':('taunt',17,0),
 'Northern Lights':('haste',19,20),'Assault':('stun',0,4),'Temper':('taunt',-19,0),'Aurora':('rend',.03,0),
 "Baldur's Fury":('snare',40,9),'Reinforcement':('bleed',14,20),'Ice Storm':('haste',19,20),
 'Rush':('haste',21,20),'Polar Rift':('dd',45,0),"Odin's Clip":('snare',70,6),"Niord's Fury":('snare',40,15),
 "Odin's Bite":('rend',.06,0),"Sif's Revenge":('bleed',32,20),"Odin's Deathblow":('dd',150,0),'Ragnarok':('dd',150,0),
 'Return Thrust':('bleed',8,20),'Engage':('taunt',17,0),'Extend Reach':('haste',18,20),'Dismissal':('taunt',-19,0),
 'Wounding Thrust':('snare',40,14),'Stab':('bleed',14,20),'Perforate':('snare',40,19),'Lunging Thrust':('haste',21,20),
 'Raze':('dd',50,0),'Razor Edge':('stun',0,7),'Roundhouse':('crush-pbae',200,0),"Odin's Wrath":('bleed',26,20),
 "Gungnir's Fury":('spirit-pbae',150,0),'Numb':('stun',0,2),'Stun':('stun',0,3),'Disable':('stun',0,4),
 'Incapacitate':('stun',0,5),'Paralyze':('stun',0,6),'Bash':('stun',0,7),'Mangle':('stun',0,8),
 'Pin':('snare',70,6),'Slam':('stun',0,5),'Brace':('ablative',300,600),'Brutalize':('stun',0,10)}
RAS=['AugStr','AugCon','AugDex','AugQui','AugAcuity','LongWind','Regeneration','Toughness','MasteryOfWater',
 'Lifter','VeilRecovery','MasteryOfBlocking','MasteryOfParrying','MasteryOfPain','MasteryOfMagery','WildPower',
 'Serenity','EtherealBond','AvoidanceOfMagic','DeterminationHybrid','FirstAid','MCL','RagingPower','SecondWind',
 'IgnorePain','EmptyMind','Purge','MasteryOfHealing','WildHealing','MasteryOfConcentration']

def apply(c):
 c.row_factory=sqlite3.Row
 version=c.execute("select Value from ServerProperty where lower(Key)='valkyrie_test_data_version'").fetchone()
 if version is None or int(version[0])<5:raise ValueError('Install Valkyrie chain/tooltips revision 5 first')
 def insert(table,values):
  c.execute('insert into "'+table+'" ('+','.join('"'+k+'"' for k in values)+') values ('+','.join('?' for _ in values)+')',list(values.values()))
 def clone(table,source,changes):
  data=dict(source);data.update(changes)
  for key in ('StyleID','AbilityID','SpecXAbilityID'):
   if key in data and key not in changes:data.pop(key)
  # Use the table's actual integer autoincrement key, not guessed names.
  for col in c.execute('pragma table_info("'+table+'")'):
   if col['pk'] and col['type'].upper()=='INTEGER' and col['name'] not in changes:data.pop(col['name'],None)
  insert(table,data)
 for row in c.execute('select ID,Name from Style where ClassId=34').fetchall():
  if row['Name'] not in {x[1] for x in SWORD+SPEAR+SHIELDS}:raise ValueError('Unknown Valkyrie style; preserve and review')
 if c.execute("select 1 from Spell where SpellID between 65200 and 65260 and coalesce(PackageID,'')<>?",(PACKAGE,)).fetchone():raise ValueError('Valkyrie style spell collision')
 if c.execute("select 1 from Spell where TooltipId between 27210 and 27270 and coalesce(PackageID,'')<>?",(PACKAGE,)).fetchone():raise ValueError('Valkyrie style tooltip collision')
 old_style_keys={r['ID']:r['StyleID'] for r in c.execute('select ID,StyleID from Style where ClassId=34')}
 c.execute('delete from StyleXSpell where ClassID=34');c.execute('delete from Style where ClassId=34')
 c.execute('delete from Spell where PackageID=?',(PACKAGE,))
 source_spell=c.execute('select * from Spell where SpellID=64990').fetchone()
 source_link=c.execute('select * from StyleXSpell limit 1').fetchone()
 index=0
 for spec,source_class,definitions in [('Sword',21,SWORD),('Spear',25,SPEAR),('Shields',21,SHIELDS)]:
  ids={name:(146 if name=='Whirling Blade' else 2000+index+i) for i,(_,name,_,_) in enumerate(definitions)}
  for level,name,template,opening in definitions:
   native=c.execute('select * from Style where ClassId=? and SpecKeyName=? and Name=?',(source_class,spec,template)).fetchone()
   if native is None:raise ValueError('Missing melee template '+template)
   style_id=ids[name];values=dict(ClassId=34,ID=style_id,Name=name,SpecLevelRequirement=level,OpeningRequirementType=0,OpeningRequirementValue=0,AttackResultRequirement=0,StealthRequirement=0,RandomProc=0)
   if opening in ('block','parry'):values.update(OpeningRequirementType=1,AttackResultRequirement=4 if opening=='block' else 3)
   elif opening in ('front','side','back'):values.update(OpeningRequirementType=2,OpeningRequirementValue={'back':0,'side':1,'front':2}[opening])
   elif opening!='any':values.update(OpeningRequirementValue=ids[opening],AttackResultRequirement=7)
   if name in ('Stabbing Blade','Thrusting Spear','Windmill','Smash','Maneuver','Pin','Sideswipe','Brace'):
    values.update(GrowthRate={'Stabbing Blade':.37,'Thrusting Spear':.04,'Windmill':.15,'Smash':.04,'Maneuver':.04,'Pin':.04,'Sideswipe':.64,'Brace':.04}[name],EnduranceCost=4 if name in ('Thrusting Spear','Windmill','Maneuver','Pin') else 10)
   if name=='Roundhouse':values.update(GrowthRate=.64,EnduranceCost=15,BonusToHit=15)
   if name=='Maneuver':values['BonusToDefense']=20
   if name=='Brace':values.update(EnduranceCost=20,BonusToHit=15)
   if name=='Stabbing Blade':values.update(EnduranceCost=10,BonusToHit=10)
   if style_id in old_style_keys:values['StyleID']=old_style_keys[style_id]
   clone('Style',native,values)
   if name in EFFECTS:
    kind,value,duration=EFFECTS[name];spell_id=65200+index
    changes=dict(SpellID=spell_id,Spell_ID='local-valk-style-'+str(spell_id),Name=name+' Effect',PackageID=PACKAGE,TooltipId=27210+index,
      Target='Enemy',Range=350,CastTime=0,Power=0,Value=0,Damage=0,DamageType=15,Type='DirectDamage',Duration=duration,
      Frequency=0,Pulse=0,PulsePower=0,Radius=0,RecastDelay=0,SharedTimerGroup=0,SpellGroup=spell_id,EffectGroup=0,
      SubSpellID=0,Concentration=0,LifeDrainReturn=0,MoveCast=1,Uninterruptible=1,IsFocus=0,IsPrimary=0,IsSecondary=0,
      Description='Valkyrie weapon style effect; class-library baseline.',ClientEffect=14321,Icon=14321)
    if kind=='bleed':changes.update(Type='StyleBleeding',Damage=value,Frequency=40,ClientEffect=2130,Icon=2130)
    elif kind=='haste':changes.update(Type='StyleCombatSpeedDebuff',Value=value,ClientEffect=2140,Icon=2140)
    elif kind=='snare':changes.update(Type='StyleSpeedDecrease',Value=value,ClientEffect=2135,Icon=2135)
    elif kind=='stun':changes.update(Type='StyleStun',ClientEffect=2132,Icon=2132)
    elif kind=='taunt':changes.update(Type='StyleTaunt',Value=value,ClientEffect=0,Icon=2131)
    elif kind=='rend':changes.update(Type='PowerRend',Value=value,Radius=350,Range=0)
    elif kind=='ablative':changes.update(Type='AblativeArmor',Target='Self',Value=value,Damage=50,ClientEffect=1506,Icon=1506)
    else:changes.update(Damage=value,Radius=250 if kind=='crush-pbae' else 700 if kind=='spirit-pbae' else 0,Range=0 if 'pbae' in kind else 350,DamageType=1 if kind=='crush-pbae' else 15)
    clone('Spell',source_spell,changes)
    clone('StyleXSpell',source_link,dict(StyleXSpell_ID='local-valk-style-link-'+str(spell_id),ClassID=34,StyleID=style_id,SpellID=spell_id,Chance=100))
   index+=1
 # Keep the original starting grants and add missing career milestones only.
 career=c.execute("select * from SpecXAbility where Spec='ValkyrieCareer' limit 1").fetchone()
 for level,key,rank in [(5,'Shield',2),(10,'Shield',3),(10,'Protect',1),(20,'Protect',2),(15,'Intercept',0)]:
  if not c.execute('select 1 from Ability where KeyName=?',(key,)).fetchone():raise ValueError('Missing ability '+key)
  if not c.execute("select 1 from SpecXAbility where Spec='ValkyrieCareer' and SpecLevel=? and AbilityKey=? and AbilityLevel=? and ClassId=34",(level,key,rank)).fetchone():
   clone('SpecXAbility',career,dict(Spec='ValkyrieCareer',SpecLevel=level,AbilityKey=key,AbilityLevel=rank,ClassId=34))
 # Use the installed Atlas passives/actives instead of mixing duplicate modern versions.
 keys=['AtlasOF_'+key for key in RAS]+["Valhalla's Blessing",'Valkyrie_Charge']
 modern_shared=c.execute("select 1 from Ability where KeyName='AtlasOF_AoM' and Implementation='DOL.GS.RealmAbilities.ModernAoM'").fetchone()
 if modern_shared:
  keys=[{'AtlasOF_AvoidanceOfMagic':'AtlasOF_AoM','AtlasOF_DeterminationHybrid':'AtlasOF_Determination'}.get(key,key) for key in keys]
 free_tireless=c.execute("select 1 from SpecXAbility where Spec='CharacterCareer' and AbilityKey='Tireless' and ClassId=0 and SpecLevel=1 and AbilityLevel=1").fetchone()
 if free_tireless:c.execute("delete from ClassXRealmAbility_Atlas where CharClass=34 and AbilityKey='AtlasOF_Tireless'")
 else:keys.append('AtlasOF_Tireless')
 charge=c.execute("select * from Ability where KeyName='Valkyrie_Charge'").fetchone()
 if charge and charge['Implementation'] not in ('DOL.GS.RealmAbilities.ValkyrieChargeAbility','DOL.GS.RealmAbilities.ModernCharge'):raise ValueError('Charge key collision')
 if not charge:
  if c.execute("select 1 from Ability where InternalID=940").fetchone():raise ValueError('Charge internal identity collision')
  native=c.execute("select * from Ability where KeyName='Charge'").fetchone()
  clone('Ability',native,dict(KeyName='Valkyrie_Charge',Name='Charge',InternalID=940,Description='15 seconds of Charge, usable without selecting an enemy player.',Implementation='DOL.GS.RealmAbilities.ValkyrieChargeAbility'))
 binding=c.execute('select * from ClassXRealmAbility_Atlas limit 1').fetchone()
 for key in keys:
  if not c.execute('select 1 from Ability where KeyName=?',(key,)).fetchone():raise ValueError('Missing realm ability '+key)
  if not c.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=34 and AbilityKey=?',(key,)).fetchone():
   clone('ClassXRealmAbility_Atlas',binding,dict(CharClass=34,AbilityKey=key,ClassXRealmAbility_Atlas_ID='local-valk-ra-'+key))
 if int(version[0])<6:c.execute("update ServerProperty set Value='6' where lower(Key)='valkyrie_test_data_version'")
 return dict(class_id=34,styles=index,style_effects=len(EFFECTS),realm_abilities=len(keys),revision=6)
