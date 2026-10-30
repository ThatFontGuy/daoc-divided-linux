"""Idempotent level-one Valkyrie test data. Only the isolated modern test DB is accepted."""
import json,sqlite3,datetime,subprocess
from pathlib import Path

repo=Path(__file__).resolve().parents[2]
root=repo/'artifacts/modern-client-test'
db=root/'runtime/data/opendaoc.sqlite3.db'
with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as state:
    version=state.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='valkyrie_test_data_version'").fetchone()
    if version and int(version[0])>=2:raise SystemExit('Valkyrie progression revision 2 already installed; prototype seed was not reapplied.')
check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
    "$ErrorActionPreference='Stop'; if([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 10330){exit 9}"],capture_output=True,text=True)
if check.returncode!=0:raise SystemExit('Could not confirm test port is unused. Stop the server and rerun with permission to inspect local listeners.')

backup=root/'backups';backup.mkdir(exist_ok=True)
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup/f'pre-valkyrie-{stamp}.sqlite3.db') as target:source.backup(target)

def remove_id(raw,remove):
    ids=set()
    for part in raw.split(';'):
        if not part.strip():continue
        pair=part.split('-')
        ids.update(range(int(pair[0]),int(pair[-1])+1))
    return ';'.join(str(x) for x in sorted(ids-{remove}))

with sqlite3.connect(db) as c:
    c.row_factory=sqlite3.Row
    def insert(table,values):
        fields=list(values)
        c.execute('INSERT INTO "'+table+'" ('+','.join('"'+x+'"' for x in fields)+') VALUES ('+','.join('?' for _ in fields)+')',[values[x] for x in fields])
    def clone(table,where,args,updates):
        row=c.execute('SELECT * FROM "'+table+'" WHERE '+where,args).fetchone()
        if row is None:raise RuntimeError('Missing reference definition: '+table)
        values=dict(row)
        for col in c.execute('PRAGMA table_info("'+table+'")'):
            if col['pk'] and 'INT' in col['type'].upper():values.pop(col['name'],None)
        values.update(updates);insert(table,values)
    def prop(key,value):
        if c.execute('UPDATE ServerProperty SET Value=? WHERE lower(Key)=?',(value,key)).rowcount==0:
            insert('ServerProperty',dict(ServerProperty_ID='local-'+key,Key=key,Value=value,DefaultValue='False',Category='classes',Description='Isolated Valkyrie test switch'))

    c.execute('BEGIN IMMEDIATE')
    for key,remove in [('disabled_classes',34),('disabled_races',17)]:
        row=c.execute('SELECT Value FROM ServerProperty WHERE lower(Key)=?',(key,)).fetchone()
        if row is None:raise RuntimeError('Missing creation settings')
        prop(key,remove_id(row['Value'],remove))
    prop('enable_valkyrie_test','True');prop('start_as_base_class','False')

    for key,level in [('Weaponry: Swords',0),('Weaponry: Spears',0),('Weaponry: Staves',0),('MidArmor',3),('Shield',1)]:
        assert c.execute('SELECT 1 FROM Ability WHERE KeyName=?',(key,)).fetchone()
        if not c.execute('SELECT 1 FROM SpecXAbility WHERE Spec=? AND AbilityKey=? AND SpecLevel=1 AND ClassId=34',('ValkyrieCareer',key)).fetchone():
            insert('SpecXAbility',dict(Spec='ValkyrieCareer',SpecLevel=1,AbilityKey=key,AbilityLevel=level,ClassId=34))

    if not c.execute('SELECT 1 FROM Specialization WHERE KeyName=?',('LocalValkyrieSpells',)).fetchone():
        insert('Specialization',dict(KeyName='LocalValkyrieSpells',Name='Valkyrie Test Spells',Icon=0,Description='Isolated level-one development slice',Implementation='DOL.GS.LiveSpellHybridSpecialization'))
    if not c.execute('SELECT 1 FROM ClassXSpecialization WHERE ClassID=34 AND SpecKeyName=?',('LocalValkyrieSpells',)).fetchone():
        insert('ClassXSpecialization',dict(ClassID=34,SpecKeyName='LocalValkyrieSpells',LevelAcquired=-4))
    if not c.execute('SELECT 1 FROM SpellLine WHERE KeyName=?',('LocalValkyrieLevelOne',)).fetchone():
        insert('SpellLine',dict(KeyName='LocalValkyrieLevelOne',Name='Valkyrie Test Spells',Spec='LocalValkyrieSpells',IsBaseLine=1,ClassIDHint=34))
    existing=c.execute('SELECT Spell_ID FROM Spell WHERE SpellID=64990').fetchall()
    if existing and (len(existing)!=1 or existing[0]['Spell_ID']!='local-valk-odins-heel'):raise RuntimeError('SpellID 64990 collision; no changes committed')
    if not existing:
        clone('Spell','SpellID=?',(2951,),dict(SpellID=64990,Spell_ID='local-valk-odins-heel',Name="Odin's Heel",Description='Level-one Valkyrie testing; placeholder existing icon/effect.',Target='Enemy',Range=1500,Power=1,CastTime=0,Damage=5,DamageType=15,Type='DirectDamage',Duration=0,Frequency=0,Pulse=0,PulsePower=0,Radius=0,RecastDelay=20,Value=0,Concentration=0,LifeDrainReturn=0,SubSpellID=0,MoveCast=1,Uninterruptible=1,IsFocus=0,IsPrimary=0,IsSecondary=0,SharedTimerGroup=64990,SpellGroup=0,EffectGroup=0,TooltipId=0,PackageID='local-valk-l1'))
    for spell,tag in [(64990,'heel'),(3001,'heal')]:
        assert c.execute('SELECT 1 FROM Spell WHERE SpellID=?',(spell,)).fetchone()
        pk='local-valk-'+tag+'-1'
        if not c.execute('SELECT 1 FROM LineXSpell WHERE LineXSpell_ID=?',(pk,)).fetchone():
            insert('LineXSpell',dict(LineXSpell_ID=pk,LineName='LocalValkyrieLevelOne',SpellID=spell,Level=1))
    if not c.execute('SELECT 1 FROM Style WHERE ClassId=34 AND ID=146').fetchone():
        clone('Style','ClassId=22 AND ID=146',(),dict(ClassId=34,SpecLevelRequirement=1))
    if not c.execute('SELECT 1 FROM StartupLocation WHERE ClassID=34 AND RealmID=2 AND RaceID=0 AND MinVersion=1130').fetchone():
        clone('StartupLocation','StartupLoc_ID=83',(),dict(ClassID=34,RealmID=2,RaceID=0,MinVersion=1130,ClientRegionID=0))
    assert c.execute('SELECT DamageType FROM Spell WHERE SpellID=64990').fetchone()[0]==15
    assert c.execute('PRAGMA foreign_key_check').fetchone() is None
    c.commit()
    report=dict(Class=34,Scope='level-one player test, not full class or bot support',StarterAbilityRows=c.execute("SELECT COUNT(*) FROM SpecXAbility WHERE Spec='ValkyrieCareer' AND ClassId=34 AND SpecLevel=1").fetchone()[0],TestSpellLinks=c.execute("SELECT COUNT(*) FROM LineXSpell WHERE LineName='LocalValkyrieLevelOne'").fetchone()[0],PlayerRecordsChanged=False)
(root/'valkyrie-seed-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
