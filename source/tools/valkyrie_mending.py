"""Valkyrie research-to-data pass 2: Mending baseline and Mending specialization.

Values are the official Class Library tables (https://www.darkageofcamelot.com/class-library-valkyrie/,
undated). Healer, Shaman and Seer keep the shared 'Mending' baseline untouched: the Valkyrie gets its own
class-hinted baseline line, which Specialization.GetSpellLinesForLiving prefers over the shared one.
Existing saves are never rewritten.
"""
import datetime,json,sqlite3,subprocess
from pathlib import Path

BASELINE='Valkyrie Mending'
SPEC_LINE='Valkyrie Mending Spec'
PACKAGE='local-valk-mending-v3'
VERSION='3'
# Shared rows that already match the Valkyrie tables exactly; linked, never modified.
SHARED_LINKS=[(3,1371),(7,1372),(10,3031)]  # Cure Poison, Cure Disease, Arrival from Valhalla

# (key, template spell, spell group, effect group, mechanics shared by every rank, ranks)
# rank: (level, name, value, power, cast seconds); cast None means the family's CastTime.
FAMILIES=[
    ('minor-heal',3001,65001,0,dict(Type='Heal',Target='Realm',Range=2000,CastTime=2.3),
     [(1,'Minor Mending',6,1),(5,'Minor Improvement',16,3),(8,'Minor Reconstitution',23,4),(11,'Minor Amelioration',31,5),
      (14,'Minor Purification',38,6),(18,'Minor Recovery',48,8),(23,'Minor Reparation',60,9),(29,'Minor Restoration',75,11),
      (37,'Minor Reconstruction',95,14),(47,'Minor Emendation',119,17)]),
    ('heal',3021,65002,0,dict(Type='Heal',Target='Realm',Range=2000,CastTime=2.8),
     [(4,'Refinement',26,4),(6,'Improvement',36,5),(9,'Reconstitution',50,7),(12,'Amelioration',65,9),(16,'Purification',85,11),
      (21,'Recovery',109,14),(27,'Reparation',138,18),(31,'Restoration',158,20),(36,'Reconstruction',183,23),(46,'Emendation',231,29)]),
    ('group-heal',3041,65003,0,dict(Type='Heal',Target='Group',Range=2000),
     [(15,'Group Reparation',33,9,2.6),(25,'Group Purification',53,13,2.4),(35,'Group Restoration',73,16,2.2),(45,'Group Emendation',93,19,2.0)]),
]
SPEC_FAMILIES=[
    ('major-heal',3101,65010,0,dict(Type='Heal',Target='Realm',Range=2000),
     [(5,'Major Reconstitution',55,5,3.2),(8,'Major Amelioration',82,7,3.1),(11,'Major Purification',109,9,3.0),(14,'Major Recovery',136,11,2.9),
      (18,'Major Reparation',172,13,2.8),(25,'Major Restoration',235,19,2.7),(33,'Major Reconstruction',307,24,2.6),(42,'Major Emendation',387,30,2.5)]),
    ('instant-rez',3121,65011,0,dict(Type='Resurrect',Target='Corpse',Range=1500,CastTime=0,RecastDelay=300,ResurrectHealth=25,ResurrectMana=25),
     [(35,'Redeem from Valhalla',0,-25)]),
    # "Buff (Health Regeneration)": added per regeneration tick, like the Shaman's Frigg's line.
    ('regen',3111,65012,13882,dict(Type='HealthRegenBuff',Target='Realm',Range=2000,CastTime=0,Duration=10,RecastDelay=10),
     [(30,"Odin's Greater Antidote",65,45),(35,"Odin's Greater Medicant",75,55),(40,"Odin's Greater Cure",85,65),(45,"Odin's Greater Elixir",95,75)]),
    # Pulse every 2 s follows OpenDAoC's own Valkyrie Odin's Elixir row (121009); the page gives no pulse rate.
    ('hot',121009,65013,13881,dict(Type='HealOverTime',Target='Realm',Range=2000,CastTime=0,Duration=10,Frequency=20,RecastDelay=10),
     [(5,"Odin's Antidote",10,10),(10,"Odin's Medicant",20,20),(15,"Odin's Cure",30,30),(20,"Odin's Elixir",40,40)]),
    ('group-regen',3098,65014,13882,dict(Type='HealthRegenBuff',Target='Group',Range=2000,CastTime=3.0,Duration=15),
     [(32,"Valkyrie's Aid",25,25),(37,"Valkyrie's Alleviation",35,35),(42,"Valkyrie's Redress",45,45),(47,"Valkyrie's Remedy",55,55)]),
    ('group-hot',3131,65015,13881,dict(Type='HealOverTime',Target='Group',Range=2000,CastTime=3.0,Duration=15,Frequency=20),
     [(7,"Shieldmaiden's Aid",10,10),(12,"Shieldmaiden's Alleviation",20,20),(17,"Shieldmaiden's Redress",30,30),(22,"Shieldmaiden's Remedy",40,40)]),
    # Realm target with range 0 centres the radius on the caster. No distance falloff (HealSpellHandler has none).
    ('pbae-heal',3085,65016,0,dict(Type='Heal',Target='Realm',Range=0,Radius=350,CastTime=0,RecastDelay=15),
     [(9,"Odin's Amelioration",108,23),(12,"Odin's Purification",138,29),(16,"Odin's Recovery",177,36),(22,"Odin's Reparation",235,48),
      (31,"Odin's Restoration",314,64),(41,"Odin's Reconstruction",411,81),(50,"Odin's Emendation",500,99)]),
]
FIRST_BASELINE_ID=65000
FIRST_SPEC_ID=65030
# Mechanical fields reset on every copy so nothing leaks from a template.
# Own tooltip per spell (see valkyrie_progression.TOOLTIP_BASE): 27000 + SpellID - 64990.
TOOLTIP_BASE=27000
RESET=dict(Value=0,Damage=0,DamageType=0,Duration=0,Frequency=0,Pulse=0,PulsePower=0,Radius=0,RecastDelay=0,Concentration=0,
           ResurrectHealth=0,ResurrectMana=0,LifeDrainReturn=0,AmnesiaChance=0,SubSpellID=0,SharedTimerGroup=0,
           MoveCast=0,Uninterruptible=0,IsFocus=0,AllowBolt=0)

def planned():
    """Every row this pass owns: (line, spell id, key, level, template, values)."""
    rows=[]
    for line,first,families in ((BASELINE,FIRST_BASELINE_ID,FAMILIES),(SPEC_LINE,FIRST_SPEC_ID,SPEC_FAMILIES)):
        spell_id=first
        for key,template,group,effect,common,ranks in families:
            for rank in ranks:
                level,name,value,power=rank[:4]
                values=dict(RESET);values.update(common)
                if len(rank)>4:values['CastTime']=rank[4]
                values.update(SpellID=spell_id,TooltipId=TOOLTIP_BASE+spell_id-64990,Spell_ID=f'local-valk-mend-{key}-{level}',Name=name,Value=value,Power=power,
                              SpellGroup=group,EffectGroup=effect,PackageID=PACKAGE,
                              Description='Valkyrie Mending; Class Library values, borrowed visual assets.')
                rows.append((line,spell_id,values['Spell_ID'],level,template,values));spell_id+=1
    return rows

def apply(c):
    c.row_factory=sqlite3.Row
    def insert(table,values):
        keys=list(values)
        c.execute('INSERT INTO "'+table+'" ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[values[k] for k in keys])
    version=c.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='valkyrie_test_data_version'").fetchone()
    if version is None or int(version['Value'] or 0)<2:raise ValueError('Apply Valkyrie progression revision 2 first.')
    spec=c.execute('SELECT Spec,IsBaseLine,ClassIDHint FROM SpellLine WHERE KeyName=?',(SPEC_LINE,)).fetchone()
    if spec is None or spec['Spec']!='Mending' or spec['IsBaseLine']!=0 or spec['ClassIDHint']!=34:
        raise ValueError('Valkyrie Mending Spec is not the expected class-34 specialization line.')
    foreign=c.execute('SELECT COUNT(*) FROM LineXSpell WHERE LineName=? AND LineXSpell_ID NOT LIKE ?',(SPEC_LINE,'local-valk-mend-%')).fetchone()[0]
    if foreign:raise ValueError('Valkyrie Mending Spec already holds spells this pass does not own; review first.')
    baseline=c.execute('SELECT Spec,IsBaseLine,ClassIDHint FROM SpellLine WHERE KeyName=?',(BASELINE,)).fetchone()
    if baseline is None:insert('SpellLine',dict(KeyName=BASELINE,Name='Mending',Spec='Mending',IsBaseLine=1,ClassIDHint=34))
    elif (baseline['Spec'],baseline['IsBaseLine'],baseline['ClassIDHint'])!=('Mending',1,34):raise ValueError('Unexpected existing line '+BASELINE)
    rows=planned()
    owned_groups=sorted({v['SpellGroup'] for *_,v in rows})
    marks=','.join('?' for _ in owned_groups)
    if c.execute(f"SELECT COUNT(*) FROM Spell WHERE SpellGroup IN ({marks}) AND Spell_ID NOT LIKE 'local-valk-mend-%'",owned_groups).fetchone()[0]:
        raise ValueError('Spell group collision')
    if c.execute("SELECT COUNT(*) FROM Spell WHERE EffectGroup=13882 AND Spell_ID NOT LIKE 'local-valk-mend-%'").fetchone()[0]:
        raise ValueError('Effect group collision: 13882')
    tips=[v['TooltipId'] for *_,v in rows]
    marks=','.join('?' for _ in tips)
    if c.execute(f"SELECT COUNT(*) FROM Spell WHERE TooltipId IN ({marks}) AND Spell_ID NOT LIKE 'local-valk-mend-%'",tips).fetchone()[0]:
        raise ValueError('Tooltip ID collision')
    for line,spell_id,key,level,template,values in rows:
        existing=c.execute('SELECT Spell_ID FROM Spell WHERE SpellID=?',(spell_id,)).fetchall()
        if existing and (len(existing)!=1 or existing[0]['Spell_ID']!=key):raise ValueError('Spell ID collision: '+str(spell_id))
        source=c.execute('SELECT * FROM Spell WHERE SpellID=?',(template,)).fetchone()
        if source is None:raise ValueError('Missing template spell '+str(template))
        row=dict(source);row.update(values)
        if not existing:insert('Spell',row)
        else:
            fields=[k for k in row if k!='Spell_ID']
            c.execute('UPDATE Spell SET '+','.join('"'+k+'"=?' for k in fields)+' WHERE Spell_ID=?',[row[k] for k in fields]+[key])
        link='local-valk-mend-link-'+key[len('local-valk-mend-'):]
        if not c.execute('SELECT 1 FROM LineXSpell WHERE LineXSpell_ID=?',(link,)).fetchone():
            insert('LineXSpell',dict(LineXSpell_ID=link,LineName=line,SpellID=spell_id,Level=level))
    for level,spell_id in SHARED_LINKS:
        if c.execute('SELECT 1 FROM Spell WHERE SpellID=?',(spell_id,)).fetchone() is None:raise ValueError('Missing shared spell '+str(spell_id))
        link=f'local-valk-mend-link-shared-{spell_id}'
        if not c.execute('SELECT 1 FROM LineXSpell WHERE LineXSpell_ID=?',(link,)).fetchone():
            insert('LineXSpell',dict(LineXSpell_ID=link,LineName=BASELINE,SpellID=spell_id,Level=level))
    if int(version['Value'])<int(VERSION):
        c.execute("UPDATE ServerProperty SET Value=? WHERE lower(Key)='valkyrie_test_data_version'",(VERSION,))
    return {'BaselineSpells':sum(len(f[5]) for f in FAMILIES)+len(SHARED_LINKS),'SpecSpells':sum(len(f[5]) for f in SPEC_FAMILIES),
            'SharedMendingModified':False,'ExistingCharactersModified':False}

def main():
    repo=Path(__file__).resolve().parents[2];root=repo/'artifacts/modern-client-test';db=root/'runtime/data/opendaoc.sqlite3.db'
    check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; if([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 10330){exit 9}"],capture_output=True)
    if check.returncode:raise SystemExit('Stop the test server; listener inspection must succeed before applying data.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=root/'backups'/('pre-valkyrie-mending-'+stamp+'.sqlite3.db')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:source.backup(target)
    with sqlite3.connect(db) as c:
        c.execute('BEGIN IMMEDIATE');report=apply(c);c.commit()
    (root/'valkyrie-mending-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__=='__main__':main()
