"""Modern Warlock first playable test kit. Definition-only migration; caller owns transaction.
Unverified live details are tracked in docs/WARLOCK-MODERN-TEST.md, never silently certified.
"""
import csv
import io
import sqlite3
import sys
from pathlib import Path

PACKAGE = 'local-warlock-test-v1'
LINES = ('Cursing', 'Cursing Spec', 'Hexing', 'Witchcraft')

def ensure_start_location(c):
    """Reuse the installed modern Midgard start, matching all Warlock races and menu region 0."""
    c.row_factory=sqlite3.Row
    existing=c.execute('select * from StartupLocation where ClassID=59 and RealmID=2 and RaceID=0 and ClientRegionID=0 and MinVersion<=1130 and Region>0 and XPos>0 and YPos>0 order by MinVersion desc limit 1').fetchone()
    if existing:return dict(existing)
    source=c.execute('select * from StartupLocation where ClassID=34 and RealmID=2 and RaceID=0 and ClientRegionID=0 and MinVersion<=1130 and Region=100 and XPos>0 and YPos>0 order by MinVersion desc limit 1').fetchone()
    if source is None:raise ValueError('Missing verified modern Midgard starting-location template')
    row=dict(source);row.pop('StartupLoc_ID');row['ClassID']=59
    c.execute('insert into StartupLocation ('+','.join(row)+') values ('+','.join('?' for _ in row)+')',list(row.values()))
    return row

def definitions():
    rows = []
    def add(id, line, level, name, icon, **kw):
        d = dict(SpellID=id, Spell_ID=f'{PACKAGE}-{id}', PackageID=PACKAGE,
                 TooltipId=28000+id-66000, Name=name, Description='Modern Warlock player test kit.',
                 Type='DirectDamage', Target='Enemy', Range=1500, CastTime=2.5,
                 DamageType=14, Icon=icon, ClientEffect=icon, SpellGroup=id,
                 Message1='You are affected by '+name+'.', Message2='{0} is affected by '+name+'.',
                 Message3=name+' ends.', Message4=name+' ends on {0}.')
        d.update(kw)
        rows.append((line, level, d))
    # Maintained stance; Power is the cost of each subsequent secondary, never activation cost.
    for base,line,levels,names,values,costs,icons,kind in [
        (66000,'Cursing Spec',[1,11,22,32,42,49],['Enduring Range','Expanded Range','Extended Range','Boundless Range','Critical Range','Perennial Range'],[3,5,7,10,15,20],[5]*6,[12170,12171,12172,12173,12174,12175],'range/radius bonus'),
        (66010,'Hexing',[2,12,22,29,39,48],['Steady Cast','Solid Cast','Fixed Cast','Fortified Cast','Anchored Cast','Unshakeable Cast'],[50,40,35,25,20,10],[40,32,25,19,14,10],[12165,12165,12166,12167,12168,12169],'damage penalty; uninterruptible secondary'),
        (66020,'Witchcraft',[5,17,28,36,41],['Pure Cast','Fluent Cast','Skillful Cast','Artistic Cast','Masterful Cast'],[40,33,25,15,5],[0]*5,[12160,12161,12162,12199,12163],'cast-time penalty; free secondary')]:
        for i,(lv,n,v,p,ic) in enumerate(zip(levels,names,values,costs,icons)):
            add(base+i,line,lv,n,ic,Type='WarlockPrimer',Target='Self',Range=0,CastTime=0,Value=v,Power=p,
                EffectGroup=66000,Description=f'Toggle maintained primer: {v}% {kind}. Secondary cost: {p}% base power. One stance at a time; cannot switch while casting.')
    for i,(lv,n,d,p) in enumerate([(1,'Minor Annulling Curse',5,2),(2,'Annulling Curse',9,2),(5,'Minor Consuming Curse',21,4),(8,'Consuming Curse',32,5),(12,'Major Consuming Curse',45,8),(15,'Minor Dismantling Curse',57,9),(20,'Dismantling Curse',73,12),(26,'Major Dismantling Curse',96,16),(33,'Minor Crushing Curse',120,21),(43,'Crushing Curse',155,27),(50,'Major Crushing Curse',179,33)]):
        add(66030+i,'Cursing',lv,n,12001+i,Damage=d,Power=p,CastTime=2.6)
    for i,(lv,n,d,p) in enumerate([(4,'Cursed Blast',24,3),(7,'Cursed Burst',36,5),(10,'Cursed Explosion',55,6),(13,'Cursed Mortar',75,8),(17,'Cursed Bomb',98,10),(22,'Cursed Ruination',116,13),(28,'Cursed Destruction',149,17),(36,'Cursed Devastation',188,23),(46,'Cursed Annihilation',239,30)]):
        add(66045+i,'Cursing',lv,n,12015+i,Type='Bolt',Damage=d,Power=p,Range=1875,RecastDelay=20)
    for i,(lv,n,d,p) in enumerate([(6,'Lessen Movement',11,2),(9,'Diffuse Movement',15,4),(16,'Disperse Movement',27,8),(23,'Suppress Movement',36,11),(31,'Quell Movement',48,15),(40,'Abolish Movement',61,20),(48,'Annihilate Movement',73,25)]):
        add(66055+i,'Cursing',lv,n,12085+i,Type='SpeedDecrease',Value=99,Duration=d,Power=p)
    for i,(lv,n,d,p) in enumerate([(5,'Lesser Twisting Curse',29,4),(10,'Twisting Curse',50,7),(15,'Lesser Winding Curse',70,10),(21,'Winding Curse',95,14),(26,'Lesser Wrenching Curse',116,17),(33,'Wrenching Curse',145,20),(39,'Lesser Warping Curse',170,25),(46,'Warping Curse',209,33)]):
        add(66065+i,'Cursing Spec',lv,n,12176+i,Damage=d,Power=p,DamageType=15,CastTime=2.6)
    for i,(lv,n,d) in enumerate([(6,'Spell Burst',38),(17,'Spell Bombardment',111),(25,'Spell Blast',178),(31,"Spellbinder's Burst",222),(38,"Spellbinder's Bombardment",273),(45,"Spellbinder's Blast",325)]):
        add(66075+i,'Cursing Spec',lv,n,[12140,12140,12141,12142,12142,12143][i],Damage=d,Radius=300,Range=0,IsSecondary=1)
    for i,(lv,n,v) in enumerate([(12,'Unmake Perception',20),(18,'Unmake Vision',25),(29,'Unmake Seeing',45),(40,'Unmake Sight',65)]):
        add(66085+i,'Cursing Spec',lv,n,12129+i,Type='Nearsight',Value=v,Duration=60,Range=2300,CastTime=2,IsSecondary=1)
    for i,(lv,n,d,p,r) in enumerate([(3,'Molding Hex',13,3,70),(8,'Rotting Hex',32,5,70),(14,'Dissolving Hex',55,9,70),(20,'Decaying Hex',79,13,70),(27,'Decomposing Hex',106,17,70),(35,'Polluting Hex',136,22,80),(43,'Corrupting Hex',167,28,80),(47,'Putrefying Hex',184,33,90)]):
        add(66100+i,'Hexing',lv,n,12184+i,Type='Lifedrain',Damage=d,Power=p,LifeDrainReturn=r,DamageType=12)
    for i,(lv,n,v,p) in enumerate([(7,'Sap Vigor',19,6),(17,'Subvert Vigor',24,9),(25,'Exhaust Vigor',28,11),(32,'Sap Vitality',34,14),(39,'Subvert Vitality',39,18),(45,'Exhaust Vitality',46,22)]):
        add(66110+i,'Hexing',lv,n,12110+i,Type='ConstitutionDebuff',Value=v,Power=p,CastTime=0,Duration=30,RecastDelay=5)
    for i,(lv,n,t) in enumerate([(4,'Spell of Creeping',10),(10,'Spell of Slowness',15),(18,'Spell of Languoring',20),(26,'Spell of Lumbering',25),(33,'Spell of Sluggishness',30),(42,'Spell of Crawling',35)]):
        add(66120+i,'Hexing',lv,n,12120+i,Type='SpeedDecrease',Value=40,Duration=t,CastTime=2,IsSecondary=1)
    for i,(lv,n,t) in enumerate([(28,'Hex of Tangling Root',50),(40,'Hex of Tenacious Root',61),(49,'Hex of Detaining Root',73)]):
        add(66130+i,'Hexing',lv,n,12089+i,Type='SpeedDecrease',Value=99,Duration=t,Radius=350,IsSecondary=1)
    for i,(lv,n,v,p) in enumerate([(1,'Major Spell of Renewal',14,2),(6,'Major Spell of Revigoration',64,6),(10,'Major Spell of Reparation',97,8),(12,'Major Spell of Relief',120,11),(18,'Major Spell of Revival',172,14),(26,'Major Spell of Restoration',243,18),(32,'Major Spell of Healing',300,24),(42,'Major Spell of Mending',387,30)]):
        add(66140+i,'Witchcraft',lv,n,12075+i,Type='Heal',Target='Realm',Range=2000,Value=v,Power=p)
    for i,(lv,n,v) in enumerate([(15,'Confluence of Renewal',103),(29,'Confluence of Restoration',163),(38,'Confluence of Healing',223),(46,'Confluence of Mending',283)]):
        add(66150+i,'Witchcraft',lv,n,12135+min(i,2),Type='Heal',Target='Group',Range=2000,Radius=2000,Value=v,CastTime=3,IsSecondary=1)
    for i,(lv,n,v,p) in enumerate([(13,'Spell of Protection',8,4),(24,'Greater Spell of Protection',12,6),(33,'Lesser Spell of Absorption',16,8),(43,'Spell of Absorption',21,10),(49,'Greater Spell of Absorption',26,12)]):
        add(66160+i,'Witchcraft',lv,n,12035+i,Type='ArmorAbsorptionBuff',Target='Self',Range=0,Value=v,Power=p,CastTime=3,Duration=1200,EffectGroup=66160)
    for i,(lv,n,v) in enumerate([(30,'Degrade Armor',100),(40,'Rot Armor',165),(50,'Erode Armor',250)]):
        add(66165+i,'Witchcraft',lv,n,12110+i,Type='ArmorFactorDebuff',Value=v,CastTime=3,Duration=20,IsSecondary=1)
    for id,lv,n,typ,ic in [(66170,23,'Spell of Negating','CurePoison',12145),(66171,35,'Spell of Curing','CureDisease',12146)]:
        add(id,'Witchcraft',lv,n,ic,Type=typ,Target='Realm',CastTime=3.2,IsSecondary=1)
    add(66172,'Witchcraft',44,'Spell of Creation',12155,Type='Resurrect',Target='Realm',CastTime=4,ResurrectHealth=10,ResurrectMana=10,IsSecondary=1)
    for id,lv,n,v,ic in [(66173,25,'Spell of Regeneration',5,12145),(66174,48,'Spell of Power',20,12146)]:
        add(id,'Witchcraft',lv,n,ic,Type='PowerRegenBuff',Target='Self',Range=0,Value=v,CastTime=3,Duration=60,MoveCast=1,IsSecondary=1,EffectGroup=66173)
    chambers=[('Cursing Spec',16,'Chamber of Destruction',12153,'Adds 10% spell critical chance for 20 seconds.'),('Cursing Spec',37,'Chamber of Decimation',12153,'265 matter damage within 300 units.'),('Hexing',16,'Chamber of Lesser Fate',12151,'Restores 40% maximum power.'),('Hexing',37,'Chamber of Greater Fate',12155,'Resets Quickcast.'),('Witchcraft',16,'Chamber of Restraint',12152,'Heals nearby group for 3% maximum health every 2 seconds for 20 seconds.'),('Witchcraft',37,'Chamber of Creation',12154,'Restores 50% friendly target maximum health within 2000 units.')]
    for i,(line,lv,n,ic,desc) in enumerate(chambers):
        add(66180+i,line,lv,n,ic,Type='WarlockChamber',Target='Self',Range=0,CastTime=6,Description=desc+' Load stationary for 6 seconds. Use again to release instantly, including while moving. Shared 10-second chamber reuse.')
    add(66290,None,37,'Decimation Burst',12141,Damage=265,Radius=300,Range=0,CastTime=0,Uninterruptible=1)
    # Chain costs and the top Dread reuse are provisional test defaults; see the guide.
    for stage,base,entries,damage_type,duration,freq,cast in [
        (1,66200,[(8,'Weak Dread',10,10),(22,'Minor Dread',20,25),(32,'Lesser Dread',35,50),(42,'Dread',55,100)],10,25,50,0),
        (2,66210,[(14,'Weak Anguish',12,0),(24,'Minor Anguish',37,0),(34,'Lesser Anguish',47,0),(44,'Anguish',60,0)],14,30,40,3),
        (3,66220,[(27,'Minor Agony',30,0),(37,'Lesser Agony',60,0),(47,'Agony',125,0)],11,25,30,2.5),
        (4,66230,[(50,'Doom',215,0)],14,10,25,3)]:
        for i,(lv,n,d,shield) in enumerate(entries):
            sub=66240+i if stage==1 else 66250 if stage==3 else 66251 if stage==4 else 0
            add(base+i,'Witchcraft',lv,n,CHAIN_ICONS[stage][i],Type='WarlockChainDot',Damage=d,DamageType=damage_type,
                Power=-7,Duration=duration,Frequency=freq,CastTime=cast,RecastDelay=12 if stage==1 else 0,
                EffectGroup=66200+stage,SubSpellID=sub,
                Description=f'Witchcraft chain stage {stage}. Agony requires your Dread and Anguish; Doom also requires Agony. Test default: 7% base power.')
            rows[-1][2]['_stage']=stage
            if stage==1:
                add(sub,None,lv,n+' Shield',12035+i,Type='MagicAblativeArmor',Target='Self',Range=0,CastTime=0,Value=shield,Damage=100,Duration=25,EffectGroup=66240)
    add(66250,None,47,'Agony Disease',15072,Type='Disease',Duration=25,CastTime=0)
    add(66251,None,50,'Doom Final Hit',15069,Damage=475,CastTime=0)
    live_additions(add)
    return rows

# Modern client art: Dread 1-4, Anguish 1-4, Agony 1-3 and Doom.
CHAIN_ICONS = {1: [15080, 15081, 15082, 15083], 2: [15075, 15076, 15077, 15078], 3: [15070, 15071, 15072], 4: [15069]}

def live_additions(add):
    """Current-live spells missing from the first kit (sources in docs/WARLOCK-MODERN-TEST.md)."""
    # Cursing secondary bolts (1.114b). Specialization direct damage is Spirit since 1.127.
    for i,(lv,n,d,ic) in enumerate([(2,'Lesser Bolt of Ruin',14,12065),(4,'Greater Bolt of Ruin',29,12066),(9,'Lesser Bolt of Havoc',63,12067),
            (14,'Greater Bolt of Havoc',96,12068),(20,'Bolt of Destruction',136,12070),(24,'Greater Bolt of Destruction',162,12071),
            (28,'Lesser Bolt of Death',189,12072),(36,'Bolt of Death',243,12073),(48,'Greater Bolt of Death',324,12074)]):
        add(66300+i,'Cursing Spec',lv,n,ic,Type='Bolt',Damage=d,DamageType=15,Power=0,Range=1875,CastTime=2.5,RecastDelay=20,IsSecondary=1)
    # Cursing 50 Spellbinder's Torrent (1.126, 2020-02-12 hotfix): 365, no snare, realm targets only.
    add(66360,'Cursing Spec',50,"Spellbinder's Torrent",12143,Type='WarlockTorrent',Damage=365,Radius=300,Range=0,CastTime=2.5,IsSecondary=1,
        Description="Secondary PBAoE: 365 matter damage within 300 to enemy realm players, pets and realm guards only.")
    # Hexing secondary AoE damage and snare (1.114b; no power since 1.116; Hindering moved to 36 in 1.122B).
    for i,(lv,n,d) in enumerate([(5,'Hex of Creeping',13),(9,'Hex of Slowing',22),(19,'Hex of Lumbering',52),(30,'Hex of Crawling',81),
            (36,'Hex of Hindering',111),(46,'Hex of Snaring',131)]):
        add(66310+i,'Hexing',lv,n,12101+i,Type='DamageSpeedDecrease',Damage=d,Value=35,Duration=30,Radius=350,Range=1500,CastTime=3,Power=0,IsSecondary=1)
    # Hexing Matter debuffs (1.116 added 15/25/40 at 23/34/44; the 1.128c note calls the top rank the 50% debuff, matching the
    # class library's 15/30/50 at 23/34/45, used here). Scourge also applies 40% Cold and Heat debuffs for 12 s (1.128c).
    for i,(lv,n,v,pw) in enumerate([(23,'Malevolent Affliction',15,12),(34,'Malevolent Pestilence',30,16),(45,'Malevolent Scourge',50,24)]):
        add(66320+i,'Hexing',lv,n,12057+i,Type='MatterResistDebuff',Value=v,Duration=8,CastTime=2,Power=pw,
            SubSpellID=66323 if i==2 else 0)
    add(66323,None,45,'Malevolent Scourge Cold',12059,Type='ColdResistDebuff',Value=40,Duration=12,CastTime=0,SubSpellID=66324)
    add(66324,None,45,'Malevolent Scourge Heat',12059,Type='HeatResistDebuff',Value=40,Duration=12,CastTime=0)
    # Hexing single-pet fear (1.122B; durations 1.123B; 3.5 s cast 1.129).
    for i,(lv,n,dur,pw) in enumerate([(1,'Fear Slave',5,6),(11,'Expel Slave',9,15),(21,'Intimidate Slave',15,26),(31,'Daunt Slave',22,35),(41,'Terrify Slave',30,43)]):
        add(66330+i,'Hexing',lv,n,15197+i,Type='WarlockPetFear',Duration=dur,CastTime=3.5,Power=pw,Range=1500,
            Description='Sends an enemy pet running in fear, causing its master to lose control. 60-second immunity afterwards.')
    # Witchcraft group healing-potency aura (1.123; 34/45 lowered to 8/10% by the 2018-03-28 hotfix).
    for i,(lv,n,v) in enumerate([(9,'Relaxing Incantation',2),(19,'Restful Incantation',4),(27,'Soothing Incantation',6),(34,'Calming Incantation',8),(45,'Ameliorating Incantation',10)]):
        add(66340+i,'Witchcraft',lv,n,15412+i,Type='WarlockHealingAura',Target='Group',Range=1500,Radius=1500,Value=v,CastTime=3,
            Duration=8,Pulse=1,Frequency=80,Power=-10,PulsePower=-10,EffectGroup=66340,
            Description=f'Pulsing group aura: increases the healing done by all grouped allies by {v}%.')
    # Witchcraft Misery AoE damage over time (1.123).
    for i,(lv,n,d,pw) in enumerate([(3,'Puny Misery',6,9),(13,'Weak Misery',33,17),(23,'Minor Misery',53,23),(33,'Lesser Misery',65,36),(43,'Misery',83,47)]):
        add(66350+i,'Witchcraft',lv,n,15407+i,Type='DamageOverTime',Damage=d,DamageType=15,Radius=350,Range=1500,CastTime=3,
            Duration=12,Frequency=20,Power=pw,EffectGroup=66350)

def validate_icons(root, rows):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'new-client/pipeline'))
    from daoc_mpk import MpakArchive
    archive=MpakArchive(root/'runtime/client-modern/app/gamedata.mpk')
    catalog={int(r[0]):r for r in csv.reader(io.StringIO(archive.read('spells.csv').decode('latin1'))) if r and r[0].isdigit()}
    icons={int(r[0]) for r in csv.reader(io.StringIO(archive.read('icons.csv').decode('latin1'))) if r and r[0].isdigit()}
    for _,_,row in rows:
        if row['Icon'] not in catalog or int(catalog[row['Icon']][2]) not in icons:
            raise ValueError('Missing client artwork '+str(row['Icon']))
    return len({r['Icon'] for _,_,r in rows})

def apply(c):
    c.row_factory=sqlite3.Row
    ensure_start_location(c)
    rows=definitions()
    for field,lo,hi in [('SpellID',66000,66399),('TooltipId',28000,28399)]:
        if c.execute(f"select 1 from Spell where {field} between ? and ? and coalesce(PackageID,'')<>?",(lo,hi,PACKAGE)).fetchone():
            raise ValueError('Warlock ID collision: '+field)
    old=c.execute("select SpellID from Spell where PackageID=?",(PACKAGE,)).fetchall()
    if c.execute("select 1 from LineXSpell where LineName in (?,?,?,?) and SpellID not between 66000 and 66399",LINES).fetchone():
        raise ValueError('Warlock lines contain unknown data; review before replacing')
    c.execute('delete from LineXSpell where SpellID between 66000 and 66399')
    c.execute('delete from SpellXCustomValues where SpellID between 66000 and 66399')
    c.execute('delete from Spell where PackageID=?',(PACKAGE,))
    for line,level,row in rows:
        row=dict(row)
        stage=row.pop('_stage',None)
        c.execute('insert into Spell ('+','.join('"'+k+'"' for k in row)+') values ('+','.join('?' for _ in row)+')',list(row.values()))
        if stage is not None:
            c.execute('insert into SpellXCustomValues (SpellID,KeyName,Value) values (?,?,?)',(row['SpellID'],'WarlockStage',str(stage)))
        if line:
            c.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)',(line,row['SpellID'],level,row['Spell_ID']))
    disabled=c.execute("select Value from ServerProperty where lower(Key)='disabled_classes'").fetchone()[0]
    classes=set()
    for token in disabled.split(';'):
        if not token.strip():continue
        bounds=list(map(int,token.split('-')))
        classes.update(range(bounds[0],bounds[-1]+1))
    classes.discard(59)
    c.execute("update ServerProperty set Value=? where lower(Key)='disabled_classes'",(';'.join(map(str,sorted(classes))),))
    for key,val in [('enable_warlock_test','True'),('warlock_test_data_version','1')]:
        if c.execute('select 1 from ServerProperty where lower(Key)=?',(key,)).fetchone():
            c.execute('update ServerProperty set Value=? where lower(Key)=?',(val,key))
        else:c.execute('insert into ServerProperty (Category,Key,Description,DefaultValue,Value,ServerProperty_ID) values (?,?,?,?,?,?)',('classes',key,'Isolated modern Warlock test kit','False' if key.startswith('enable') else '0',val,'local-'+key))
    if not c.execute("select 1 from SpecXAbility where Spec='MidClothCasterCareer' and AbilityKey='Quickcast' and ClassId=59").fetchone():
        c.execute("insert into SpecXAbility (Spec,SpecLevel,AbilityKey,AbilityLevel,ClassId) values ('MidClothCasterCareer',1,'Quickcast',1,59)")
    return dict(spells=len(rows),learned_spells=sum(line is not None for line,_,_ in rows),chambers=6,primers=17,version=1)
