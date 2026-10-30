"""Class trainers wear their class's epic armor, as on Eve of Darkness (db-public e0e6ed28).

Every advanced-class trainer gets its class equipment template (for example 'thane', 'mauler_alb'): the
class's epic armor set. These templates already exist locally and were checked slot by slot against Eve of
Darkness. Base-class trainers (Fighter, Viking, Seer, ...) have no epic armor and are left alone, as are
custom trainers (Stormforged, Pendragon).

An NPC template's equipment replaces the Mob's at load, so a trainer's NPC template is updated too, but only
when no other kind of NPC uses it. Only Mob and NpcTemplate equipment fields change; saves are never touched.
"""
import datetime,json,sqlite3,subprocess,sys
from pathlib import Path

CLASS_TEMPLATES={c:c.lower() for c in ['Animist','Armsman','Bainshee','Bard','Berserker','Blademaster','Bonedancer','Cabalist',
    'Champion','Cleric','Druid','Eldritch','Enchanter','Friar','Healer','Heretic','Hero','Hunter','Infiltrator','Mentalist',
    'Mercenary','Minstrel','Necromancer','Nightshade','Paladin','Ranger','Reaver','Runemaster','Savage','Scout','Shadowblade',
    'Shaman','Skald','Sorcerer','Spiritmaster','Thane','Theurgist','Valewalker','Valkyrie','Vampiir','Warden','Warlock',
    'Warrior','Wizard']}
CLASS_TEMPLATES.update(AlbionMauler='mauler_alb',HiberniaMauler='mauler_hib',MidgardMauler='mauler_mid')
PREFIX='DOL.GS.Trainer.'

def planned(c):
    """{Mob_ID: wanted equipment template} for every advanced-class trainer."""
    wanted={}
    for mob_id,class_type in c.execute(f"SELECT Mob_ID,ClassType FROM Mob WHERE ClassType LIKE '{PREFIX}%'"):
        short=class_type[len(PREFIX):].removesuffix('Trainer')
        if short in CLASS_TEMPLATES:wanted[mob_id]=CLASS_TEMPLATES[short]
    return wanted

def apply(c):
    c.row_factory=sqlite3.Row
    have={r[0] for r in c.execute('SELECT DISTINCT TemplateID FROM NPCEquipment')}
    wanted=planned(c)
    missing=sorted(set(wanted.values())-have)
    if missing:raise ValueError('Missing equipment templates: '+', '.join(missing))
    mobs=[];templates={}
    for mob_id,template in wanted.items():
        mob=c.execute('SELECT Mob_ID,Name,ClassType,EquipmentTemplateID,NPCTemplateID FROM Mob WHERE Mob_ID=?',(mob_id,)).fetchone()
        if (mob['EquipmentTemplateID'] or '')!=template:
            mobs.append(dict(Mob_ID=mob_id,Name=mob['Name'],From=mob['EquipmentTemplateID'],To=template))
        if mob['NPCTemplateID']>0:
            npc=c.execute('SELECT TemplateId,EquipmentTemplateID FROM NpcTemplate WHERE TemplateId=?',(mob['NPCTemplateID'],)).fetchall()
            if len(npc)!=1 or not npc[0]['EquipmentTemplateID'] or npc[0]['EquipmentTemplateID']==template:continue
            others=c.execute('SELECT COUNT(*) FROM Mob WHERE NPCTemplateID=? AND ClassType<>?',(mob['NPCTemplateID'],mob['ClassType'])).fetchone()[0]
            if others:continue  # shared with other NPCs: leave the template alone
            previous=templates.get(mob['NPCTemplateID'])
            if previous and previous['To']!=template:raise ValueError('Conflicting wanted gear for NPC template '+str(mob['NPCTemplateID']))
            templates[mob['NPCTemplateID']]=dict(TemplateId=mob['NPCTemplateID'],From=npc[0]['EquipmentTemplateID'],To=template)
    for m in mobs:c.execute('UPDATE Mob SET EquipmentTemplateID=? WHERE Mob_ID=?',(m['To'],m['Mob_ID']))
    for t in templates.values():c.execute('UPDATE NpcTemplate SET EquipmentTemplateID=? WHERE TemplateId=?',(t['To'],t['TemplateId']))
    return dict(ManagedTrainers=len(wanted),MobsChanged=mobs,NpcTemplatesChanged=list(templates.values()),SavesModified=False)

def main():
    repo=Path(__file__).resolve().parents[2];root=repo/'artifacts/modern-client-test';db=root/'runtime/data/opendaoc.sqlite3.db'
    if '--apply' not in sys.argv:
        with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(':memory:') as c:
            source.backup(c);report=apply(c)
        print(json.dumps(dict(Preview=True,ManagedTrainers=report['ManagedTrainers'],MobsChanged=len(report['MobsChanged']),NpcTemplatesChanged=len(report['NpcTemplatesChanged']))));return
    check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; if([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 10330){exit 9}"],capture_output=True)
    if check.returncode:raise SystemExit('Stop the test server; listener inspection must succeed before applying data.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=root/'backups'/('pre-trainer-armor-'+stamp+'.sqlite3.db')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:source.backup(target)
    with sqlite3.connect(db) as c:
        c.execute('BEGIN IMMEDIATE');report=apply(c);c.commit()
    (root/'trainer-armor-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(ManagedTrainers=report['ManagedTrainers'],MobsChanged=len(report['MobsChanged']),NpcTemplatesChanged=len(report['NpcTemplatesChanged']),Backup=str(backup))))

if __name__=='__main__':main()
