"""Mauler style trees. Numeric growth factors are explicit test estimates, not verified retail factors."""
import csv
import io
from mauler_test_data import insert,PACKAGE

# Level, name, opening, growth, hit, defense, endurance, effect kind/value/duration.
FISTS=[
 (1,'Ducking Blow','any',.1,0,0,10,None,0,0),(2,'Jab','any',.8,5,5,15,None,0,0),
 (4,'Uppercut','Jab',.8,10,0,10,'snare',40,10),(6,'Jaw Breaker','Uppercut',.3,5,5,10,'haste',5,15),
 (8,'Owl Strike','any',.5,10,-5,10,'taunt',20,0),(10,'Heart Stopper','front',.3,10,5,10,'tap',25,0),
 (12,'Body Blow','any',0,10,15,10,'taunt',-20,0),(15,'Haymaker','side',.8,5,5,10,'stun',0,5),
 (18,'Wind Taker','back',.5,10,0,5,'snare',40,10),(21,'Rib Cracker','Heart Stopper',.8,10,5,10,'dd',25,0),
 (25,'Eagle Strike','Owl Strike',.5,15,-5,10,'snare',30,10),(29,'Gut Shot','Wind Taker',.5,10,5,10,'tap',75,0),
 (34,'Dislocation','evade',.8,10,0,15,'stun',0,5),(39,'Cross','Haymaker',.8,10,5,15,'aoesnare',40,10),
 (44,'Counter Blow','Dislocation',.8,10,5,10,'haste',25,30),(50,'Phoenix Strike','Owl Strike',.8,15,5,10,'dd',130,0)]
STAFF=[
 (1,'Wild Swing','any',.8,-5,-10,10,'pierce',2,9),(2,'Splintered Strike','Wild Swing',.5,5,5,5,'haste',8,20),
 (4,'Focused Breach','Splintered Strike',.8,10,0,5,'abs',5,30),(6,'Rescue','any',.8,15,5,10,'taunt',20,0),
 (8,'Percussion','side',.3,10,-5,10,'stun',0,5),(10,'Cinder Strike','front',.3,10,5,10,'tap',25,0),
 (12,'Subterfuge','any',0,10,15,10,'taunt',-20,0),(15,'Jolting Staff','Wild Swing',.5,10,5,10,'energy',50,60),
 (18,'Smelting Blow','Percussion',.5,15,0,5,'ablative',50,60),(21,'Turbid Staff','Wild Swing',.5,10,5,10,'speed',50,9),
 (25,"Wildbull's Staff",'Percussion',1.1,0,-20,20,'strip',3,0),(29,'Ember Clip','evade',.5,10,5,10,'haste',30,20),
 (34,'Burning Cloud','back',.8,5,0,15,'stun',0,7),(39,'Scorching Cloud','Burning Cloud',1.1,15,-5,15,'castslow',50,30),
 (44,'Forging Clip','Ember Clip',1.1,15,0,10,'bleed',35,30),(50,"Farseer's Staff",'Turbid Staff',1.1,15,10,10,'free',1,15)]

def install(c):
    from pathlib import Path
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'new-client/pipeline'))
    from daoc_mpk import MpakArchive
    root=Path(__file__).resolve().parents[2]/'artifacts/modern-client-test'
    archive=MpakArchive(root/'runtime/client-modern/app/gamedata.mpk')
    catalog={int(r[0]):r for r in csv.reader(io.StringIO(archive.read('styles.csv').decode('latin1'))) if r and r[0].isdigit()}
    # The client stores the legacy style names. Renamed modern styles retain their original art slots.
    aliases={'Turbid Staff':'Winding Blow',"Wildbull's Staff":'Shocking Staff','Scorching Cloud':'Scorching Staff','Forging Clip':'Forging Blow',"Farseer's Staff":'Tempered Strike'}
    oldkeys={(r['ClassId'],r['ID']):r['StyleID'] for r in c.execute('select * from Style where ClassID in (60,61,62)')}
    if c.execute('select 1 from Style where ClassId in (60,61,62) and ID not between 4000 and 4031').fetchone():raise ValueError('Unknown Mauler styles; preserve for review')
    c.execute('delete from StyleXSpell where ClassID in (60,61,62)');c.execute('delete from Style where ClassID in (60,61,62)')
    spell_template=dict(c.execute('select * from Spell where SpellID=67000').fetchone())
    count=0
    for offset,spec,weapon,tree in [(0,'Fist Wraps',27,FISTS),(16,'Mauler Staff',28,STAFF)]:
        ids={entry[1]:4000+offset+i for i,entry in enumerate(tree)}
        for i,(lv,name,opening,growth,hit,defense,endurance,kind,value,duration) in enumerate(tree):
            sid=ids[name];native=next((r for r in catalog.values() if r[1].casefold()==aliases.get(name,name).casefold()),None)
            if native is None:raise ValueError('Missing style art '+name)
            # Native style Icon is a styles.csv row identity; its third column refers to icons.csv.
            values=dict(ID=sid,Name=name,SpecKeyName=spec,SpecLevelRequirement=lv,Icon=int(native[0]),
                EnduranceCost=endurance,GrowthRate=growth,BonusToHit=hit,BonusToDefense=defense,
                WeaponTypeRequirement=weapon,OpeningRequirementType=0,OpeningRequirementValue=0,AttackResultRequirement=0,
                TwoHandAnimation=int(native[3]) if weapon==28 and native[3].isdigit() else 0)
            if opening in ('front','side','back'):values.update(OpeningRequirementType=2,OpeningRequirementValue={'back':0,'side':1,'front':2}[opening])
            elif opening=='evade':values.update(OpeningRequirementType=1,AttackResultRequirement=5)
            elif opening!='any':values.update(OpeningRequirementValue=ids[opening],AttackResultRequirement=7)
            effectid=67800+offset+i
            if kind:
                spell=dict(spell_template);spell.update(SpellID=effectid,Spell_ID=PACKAGE+'-'+str(effectid),TooltipId=31200+effectid-67000,
                    Name=name+' Effect',Type='DirectDamage',Target='Enemy',Range=350,CastTime=0,Value=0,Damage=0,Power=0,
                    DamageType=14,Duration=duration,Frequency=0,EffectGroup=effectid,SpellGroup=effectid,Icon=10555,ClientEffect=10555,
                    SubSpellID=0,Description='Mauler style effect: '+str(kind))
                if kind=='snare' or kind=='aoesnare':spell.update(Type='StyleSpeedDecrease',Value=value,Radius=350 if kind=='aoesnare' else 0,Icon=10621,ClientEffect=10621)
                elif kind=='haste':spell.update(Type='StyleCombatSpeedDebuff',Value=value,Icon=10582,ClientEffect=10582)
                elif kind=='stun':spell.update(Type='StyleStun',Icon=10605,ClientEffect=10605)
                elif kind=='taunt':spell.update(Type='StyleTaunt',Value=value)
                elif kind=='tap':spell.update(Type='PowerDrain',Damage=value,LifeDrainReturn=50)
                elif kind=='dd':spell.update(Damage=value)
                elif kind=='abs':spell.update(Type='ArmorAbsorptionDebuff',Value=value)
                elif kind=='ablative':spell.update(Type='AblativeArmor',Target='Self',Value=value,Damage=50)
                elif kind=='castslow':spell.update(Type='MaulerStat',Value=value)
                elif kind=='bleed':spell.update(Type='StyleBleeding',Damage=value,DamageType=13,Frequency=50)
                elif kind in ('free','pierce'):spell.update(Type='MaulerUtility',Target='Self',Value=value)
                elif kind=='strip':spell.update(Type='MaulerUtility',Value=3)
                elif kind=='speed':spell.update(Type='MaulerUtility',Target='Self',Value=9)
                elif kind=='energy':
                    spell.update(Type='OffensiveProc',Target='Self',Value=67701,Frequency=100)
                insert(c,'Spell',spell)
                if kind=='castslow':insert(c,'SpellXCustomValues',dict(SpellID=effectid,KeyName='MaulerStat',Value='15'))
            for career in (60,61,62):
                row=dict(values,ClassId=career)
                if (career,sid) in oldkeys:row['StyleID']=oldkeys[career,sid]
                insert(c,'Style',row)
                if kind:insert(c,'StyleXSpell',dict(StyleID=sid,ClassID=career,SpellID=effectid,Chance=100,StyleXSpell_ID=f'{PACKAGE}-style-{career}-{sid}'))
                count+=1
    energy=dict(spell_template);energy.update(SpellID=67701,Spell_ID=PACKAGE+'-67701',TooltipId=31200+67701-67000,Name='Jolting Energy',Type='DirectDamage',Target='Enemy',Range=350,CastTime=0,Value=0,Damage=50,DamageType=12,Icon=10555,ClientEffect=10555,EffectGroup=0)
    insert(c,'Spell',energy)
    return dict(styles_total=count,styles_per_realm=count//3)
