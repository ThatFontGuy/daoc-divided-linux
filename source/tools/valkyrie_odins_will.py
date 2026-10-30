"""Valkyrie research-to-data pass 3: the rest of the Odin's Will specialization.

Values are the official Class Library tables (https://www.darkageofcamelot.com/class-library-valkyrie/,
undated). The nine instant damage ranks from pass 1 stay as they are. Frontal cones use Target 'Cone'
with Range as the cone length and Radius as the 90-degree arc (SpellHandler.SelectTargets).
Needs the server build that adds ValkyrieDexQuiShearCone/ValkyrieAcuityShearCone and percent PulsePower.
Existing saves are never rewritten.
"""
import datetime,json,sqlite3,subprocess
from pathlib import Path

LINE="Odin's Will"
PACKAGE='local-valk-odins-will-v4'
VERSION='4'
FIRST_ID=65100
CONE=dict(Target='Cone',Range=700,Radius=90,DamageType=15)

# (key, template spell, spell group, mechanics shared by every rank, ranks)
# rank: (level, name, main value, power, extra per-rank fields)
FAMILIES=[
    ('call-from-valhalla',3077,65101,dict(Type='Resurrect',Target='Corpse',Range=1500,CastTime=4.0,ResurrectHealth=65,ResurrectMana=35),
     [(43,'Call from Valhalla',None,-25,{})]),
    ('cone-dd',64990,65102,dict(CONE,Type='DirectDamage',CastTime=0,RecastDelay=30),
     [(8,"Valhalla's Scorn",20,5,{}),(18,"Valhalla's Spite",40,12,{}),(28,"Valhalla's Contempt",60,16,{}),
      (38,"Valhalla's Disdain",80,26,{}),(48,"Valhalla's Rage",100,32,{})]),
    # Group chant: the ablative refreshes every 6 s pulse; 30% of each magical hit is absorbed.
    ('faith',1008,65103,dict(Type='MagicAblativeArmor',Target='Group',Range=1500,CastTime=0,Duration=6,Frequency=60,Pulse=1,RecastDelay=8,Damage=30),
     [(30,"Odin's Faith",60,0,{}),(40,"Odin's Virtue",90,0,{}),(50,"Odin's Temperance",120,0,{})]),
    # 10% of max power to start, 9% per 5 s pulse (negative PulsePower = percent).
    ('retribution',25610,65104,dict(CONE,Type='FrontalPulseConeDD',CastTime=0,Duration=0,Frequency=50,Pulse=1,PulsePower=-9,RecastDelay=8),
     [(5,"Odin's Minor Retribution",7,-10,{}),(12,"Odin's Lesser Retribution",13,-10,{}),(22,"Odin's Retribution",23,-10,{}),
      (32,"Odin's Greater Retribution",33,-10,{}),(42,"Odin's Major Retribution",43,-10,{})]),
    # Value is filled with the proc spell's ID; Frequency 10 = 10% chance.
    ('aura',11232,65105,dict(Type='OffensiveProc',Target='Group',Range=1000,CastTime=3.0,Duration=600,Frequency=10),
     [(8,"Odin's Minor Aura",20,3,{}),(17,"Odin's Lesser Aura",40,6,{}),(26,"Odin's Aura",60,10,{}),
      (34,"Odin's Greater Aura",80,13,{}),(44,"Odin's Full Aura",100,18,{})]),
    # Shears: Damage per rank, Value = strongest buff removed (0 = any). Families split by reuse so both stay on the list.
    ('dexqui-shear',64990,65106,dict(CONE,Type='ValkyrieDexQuiShearCone',CastTime=0,RecastDelay=300),
     [(17,'Vindictive Graze',56,16,dict(Value=75)),(37,'Vindictive Nip',112,16,dict(Value=0))]),
    ('dexqui-shear-fast',64990,65107,dict(CONE,Type='ValkyrieDexQuiShearCone',CastTime=0,RecastDelay=60),
     [(27,'Vindictive Laceration',56,26,dict(Value=75)),(47,'Vindictive Bite',112,32,dict(Value=0))]),
    ('acu-shear',64990,65108,dict(CONE,Type='ValkyrieAcuityShearCone',CastTime=0,RecastDelay=300),
     [(19,"Valkyrie's Authority",56,18,dict(Value=75)),(39,"Valkyrie's Command",112,16,dict(Value=0))]),
    ('acu-shear-fast',64990,65109,dict(CONE,Type='ValkyrieAcuityShearCone',CastTime=0,RecastDelay=60),
     [(29,"Valkyrie's Supremecy",56,28,dict(Value=75)),(49,"Valkyrie's Dominance",112,32,dict(Value=0))]),
    ('cone-snare',2673,65110,dict(CONE,Type='SpeedDecrease',CastTime=0,RecastDelay=30),
     [(12,"Odin's Restraint",50,5,dict(Duration=10)),(24,"Odin's Restriction",60,14,dict(Duration=20)),
      (36,"Odin's Grasp",70,21,dict(Duration=30)),(46,"Odin's Lock",80,28,dict(Duration=40))]),
]
# Which field carries a family's main per-rank value.
MAIN={'cone-dd':'Damage','retribution':'Damage','dexqui-shear':'Damage','dexqui-shear-fast':'Damage',
      'acu-shear':'Damage','acu-shear-fast':'Damage'}
# Proc spells cast by the aura buffs; owned rows, never linked to a line.
PROC_TEMPLATE=11243
# Own tooltip per spell (see valkyrie_progression.TOOLTIP_BASE): 27000 + SpellID - 64990.
TOOLTIP_BASE=27000
RESET=dict(Value=0,Damage=0,DamageType=0,Duration=0,Frequency=0,Pulse=0,PulsePower=0,Radius=0,RecastDelay=0,Concentration=0,
           ResurrectHealth=0,ResurrectMana=0,LifeDrainReturn=0,AmnesiaChance=0,SubSpellID=0,SharedTimerGroup=0,EffectGroup=0,
           MoveCast=0,Uninterruptible=0,IsFocus=0,AllowBolt=0)

def planned():
    """Every row this pass owns: (linked level or None, spell id, key, template, values)."""
    rows=[];procs=[];spell_id=FIRST_ID
    for key,template,group,common,ranks in FAMILIES:
        for level,name,value,power,extra in ranks:
            values=dict(RESET);values.update(common)
            if value is not None:values[MAIN.get(key,'Value')]=value
            values.update(extra)
            values.update(SpellID=spell_id,TooltipId=TOOLTIP_BASE+spell_id-64990,Spell_ID=f'local-valk-ow-{key}-{level}',Name=name,Power=power,SpellGroup=group,PackageID=PACKAGE,
                          Description="Valkyrie Odin's Will; Class Library values, borrowed visual assets.")
            rows.append((level,spell_id,values['Spell_ID'],template,values));spell_id+=1
            if key=='aura':procs.append((values,value))
    for aura,damage in procs:
        values=dict(RESET);values.update(Type='DirectDamage',Target='Enemy',Range=300,Damage=damage,DamageType=15,Power=0,CastTime=0,
            SpellID=spell_id,TooltipId=TOOLTIP_BASE+spell_id-64990,Spell_ID=f"local-valk-ow-aura-proc-{damage}",Name=aura['Name'],SpellGroup=0,PackageID=PACKAGE,
            Description="Valkyrie Odin's Will melee proc; Class Library values.")
        aura['Value']=spell_id
        rows.append((None,spell_id,values['Spell_ID'],PROC_TEMPLATE,values));spell_id+=1
    return rows

def apply(c):
    c.row_factory=sqlite3.Row
    def insert(table,values):
        keys=list(values)
        c.execute('INSERT INTO "'+table+'" ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[values[k] for k in keys])
    version=c.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='valkyrie_test_data_version'").fetchone()
    if version is None or int(version['Value'] or 0)<3:raise ValueError('Apply Valkyrie Mending revision 3 first.')
    line=c.execute('SELECT Spec,IsBaseLine FROM SpellLine WHERE KeyName=?',(LINE,)).fetchone()
    if line is None or line['Spec']!=LINE or line['IsBaseLine']!=0:raise ValueError("Odin's Will is not the expected specialization line.")
    if c.execute('SELECT COUNT(*) FROM ClassXSpecialization WHERE SpecKeyName=? AND ClassID<>34',(LINE,)).fetchone()[0]:
        raise ValueError('Unexpected shared specialization; review impact before modifying.')
    rows=planned()
    groups=sorted({v['SpellGroup'] for *_,v in rows if v['SpellGroup']})
    marks=','.join('?' for _ in groups)
    if c.execute(f"SELECT COUNT(*) FROM Spell WHERE SpellGroup IN ({marks}) AND Spell_ID NOT LIKE 'local-valk-ow-%'",groups).fetchone()[0]:
        raise ValueError('Spell group collision')
    tips=[v['TooltipId'] for *_,v in rows]
    marks=','.join('?' for _ in tips)
    if c.execute(f"SELECT COUNT(*) FROM Spell WHERE TooltipId IN ({marks}) AND Spell_ID NOT LIKE 'local-valk-ow-%'",tips).fetchone()[0]:
        raise ValueError('Tooltip ID collision')
    for level,spell_id,key,template,values in rows:
        existing=c.execute('SELECT Spell_ID FROM Spell WHERE SpellID=?',(spell_id,)).fetchall()
        if existing and (len(existing)!=1 or existing[0]['Spell_ID']!=key):raise ValueError('Spell ID collision: '+str(spell_id))
        source=c.execute('SELECT * FROM Spell WHERE SpellID=?',(template,)).fetchone()
        if source is None:raise ValueError('Missing template spell '+str(template))
        row=dict(source);row.update(values)
        if not existing:insert('Spell',row)
        else:
            fields=[k for k in row if k!='Spell_ID']
            c.execute('UPDATE Spell SET '+','.join('"'+k+'"=?' for k in fields)+' WHERE Spell_ID=?',[row[k] for k in fields]+[key])
        if level is None:continue
        link='local-valk-ow-link-'+key[len('local-valk-ow-'):]
        if not c.execute('SELECT 1 FROM LineXSpell WHERE LineXSpell_ID=?',(link,)).fetchone():
            insert('LineXSpell',dict(LineXSpell_ID=link,LineName=LINE,SpellID=spell_id,Level=level))
    if int(version['Value'])<int(VERSION):
        c.execute("UPDATE ServerProperty SET Value=? WHERE lower(Key)='valkyrie_test_data_version'",(VERSION,))
    return {'LinkedSpells':sum(len(f[4]) for f in FAMILIES),'ProcSpells':sum(1 for r in rows if r[0] is None),
            'ExistingCharactersModified':False}

def main():
    repo=Path(__file__).resolve().parents[2];root=repo/'artifacts/modern-client-test';db=root/'runtime/data/opendaoc.sqlite3.db'
    check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; if([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 10330){exit 9}"],capture_output=True)
    if check.returncode:raise SystemExit('Stop the test server; listener inspection must succeed before applying data.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=root/'backups'/('pre-valkyrie-odins-will-'+stamp+'.sqlite3.db')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:source.backup(target)
    with sqlite3.connect(db) as c:
        c.execute('BEGIN IMMEDIATE');report=apply(c);c.commit()
    (root/'valkyrie-odins-will-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__=='__main__':main()
