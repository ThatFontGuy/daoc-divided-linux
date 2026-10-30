"""Valkyrie research-to-data pass 1. Existing saves are never rewritten."""
import datetime,json,sqlite3,subprocess
from pathlib import Path

RANKS=[(1,"Odin's Heel",5,1),(4,"Odin's Hoof",15,2),(7,"Odin's Greater Hoof",26,5),
       (9,"Odin's Claw",32,6),(13,"Odin's Greater Claw",44,8),(19,"Odin's Horn",65,11),
       (25,"Odin's Greater Horn",83,15),(35,"Odin's Ram",114,21),(45,"Odin's Greater Ram",145,28)]
NATIVE="Odin's Will"
TRAINER='local-valkyrie-test-trainer'
REFERENCE_TRAINER='d0cfb7f0-fb44-4307-bbc7-e55724b4b1dd'
# Every Valkyrie spell gets its own tooltip so the client never shows a borrowed icon's stock text.
# Block 27000-27160 mirrors spell IDs 64990-65150 (65151+ are stock spells) (Sluaghbinder uses 29000, Pendragon 26000, Stormforged 20600).
TOOLTIP_BASE=27000
def tooltip(spell_id):return TOOLTIP_BASE+spell_id-64990

def apply(c):
    c.row_factory=sqlite3.Row
    def insert(table,values):
        keys=list(values)
        c.execute('INSERT INTO "'+table+'" ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[values[k] for k in keys])
    template=c.execute("SELECT * FROM Spell WHERE SpellID=64990 AND Spell_ID='local-valk-odins-heel'").fetchone()
    if template is None:raise ValueError('Apply the verified Valkyrie starter slice first.')
    expected=c.execute('SELECT Spec,IsBaseLine FROM SpellLine WHERE KeyName=?',(NATIVE,)).fetchone()
    if expected is None or expected['Spec']!=NATIVE or expected['IsBaseLine']!=0:
        raise ValueError('Native specialization line is not the expected Valkyrie spec line.')
    if c.execute('SELECT COUNT(*) FROM ClassXSpecialization WHERE SpecKeyName=? AND ClassID<>34',(NATIVE,)).fetchone()[0]:
        raise ValueError('Unexpected shared specialization; review impact before modifying.')
    for i,(level,name,damage,power) in enumerate(RANKS):
        spell_id=64990+i;key='local-valk-odins-heel' if i==0 else f'local-valk-odins-rank-{level}'
        existing=c.execute('SELECT Spell_ID FROM Spell WHERE SpellID=?',(spell_id,)).fetchall()
        if existing and (len(existing)!=1 or existing[0]['Spell_ID']!=key):raise ValueError('Spell ID collision: '+str(spell_id))
        values=dict(template)
        values.update(SpellID=spell_id,Spell_ID=key,Name=name,Description='Valkyrie instant Spirit damage; borrowed visual assets.',Damage=damage,Power=power,DamageType=15,Range=1500,CastTime=0,Duration=0,Frequency=0,Pulse=0,PulsePower=0,Radius=0,RecastDelay=20,Value=0,Concentration=0,Type='DirectDamage',Target='Enemy',SubSpellID=0,SharedTimerGroup=64990,SpellGroup=64990,EffectGroup=0,TooltipId=tooltip(spell_id),PackageID='local-valk-progression-v2')
        if not existing:insert('Spell',values)
        else:
            fields=[k for k in values if k!='Spell_ID']
            c.execute('UPDATE Spell SET '+','.join('"'+k+'"=?' for k in fields)+' WHERE Spell_ID=?',[values[k] for k in fields]+[key])
        link=f'local-valk-native-dd-{level}'
        if not c.execute('SELECT 1 FROM LineXSpell WHERE LineXSpell_ID=?',(link,)).fetchone():
            insert('LineXSpell',dict(LineXSpell_ID=link,LineName=NATIVE,SpellID=spell_id,Level=level))
    c.execute('UPDATE Specialization SET Implementation=? WHERE KeyName=?',('DOL.GS.LiveSpellHybridSpecialization',NATIVE))
    # Remove only our prototype wiring; keep the existing character, skills and shared heal rows.
    c.execute("DELETE FROM LineXSpell WHERE LineXSpell_ID IN ('local-valk-heel-1','local-valk-heal-1') AND LineName='LocalValkyrieLevelOne'")
    c.execute("DELETE FROM ClassXSpecialization WHERE ClassID=34 AND SpecKeyName='LocalValkyrieSpells'")
    imported_trainers=c.execute("SELECT 1 FROM Mob WHERE Guild='Valkyrie Trainer' AND PackageID='OfflineDAoC.ExpansionTrainers.EoD.v1'").fetchone()
    if not imported_trainers and not c.execute('SELECT 1 FROM Mob WHERE Mob_ID=?',(TRAINER,)).fetchone():
        trainer=c.execute('SELECT * FROM Mob WHERE Mob_ID=?',(REFERENCE_TRAINER,)).fetchone()
        if trainer is None:raise ValueError('Expected existing Mularn Viking trainer reference is missing.')
        values=dict(trainer)
        values.update(Mob_ID=TRAINER,Name='Valkyrie Trainer',Guild='Valkyrie Trainer',ClassType='DOL.GS.Trainer.ValkyrieTrainer',NPCTemplateID=0,AggroLevel=0)
        insert('Mob',values)
    key='valkyrie_test_data_version'
    current=c.execute('SELECT Value FROM ServerProperty WHERE lower(Key)=?',(key,)).fetchone()
    if current is not None:
        # Reapplying an earlier pass must never roll back a later revision.
        if int(current['Value'] or 0)<2:c.execute('UPDATE ServerProperty SET Value=? WHERE lower(Key)=?',('2',key))
    else:
        insert('ServerProperty',dict(ServerProperty_ID='local-'+key,Key=key,Value='2',DefaultValue='0',Category='classes',Description='Installed isolated Valkyrie test data revision'))
    return {'NativeInstantRanks':len(RANKS),'SharedReuseSeconds':20,'Trainer':'Imported Eve of Darkness Valkyrie trainers' if imported_trainers else 'Mularn, co-located with Saeunn (existing Viking trainer)','ExistingCharactersModified':False}

def main():
    repo=Path(__file__).resolve().parents[2];root=repo/'artifacts/modern-client-test';db=root/'runtime/data/opendaoc.sqlite3.db'
    check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; if([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 10330){exit 9}"],capture_output=True)
    if check.returncode:raise SystemExit('Stop the test server; listener inspection must succeed before applying data.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=root/'backups'/('pre-valkyrie-progression-'+stamp+'.sqlite3.db')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:source.backup(target)
    with sqlite3.connect(db) as c:
        c.execute('BEGIN IMMEDIATE');report=apply(c);c.commit()
    (root/'valkyrie-progression-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__=='__main__':main()
