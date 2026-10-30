"""Valkyrie data pass 4: chain armor from level 1 and a chain starter set (owner decision, October 23, 2026).

MidArmor ability level 4 is chain (Warriors get it at 10, Thanes at 12). The Valkyrie keeps the shared
starter shield and sword; only its armor rows change, from the Viking bronze stelskodd (studded) set to the
matching level-2 bronze pansarkedja (chain) set. Other Viking classes keep their studded rows.
Existing characters and their inventories are never rewritten; this affects newly created Valkyries.
"""
import datetime,json,sqlite3,subprocess
from pathlib import Path

VERSION='5'
CLASS='34'
CHAIN_LEVEL=4
SLOTS=['helm','gloves','boots','sleeves','leggings']
STUDDED=['bronze_stelskodd_'+s for s in SLOTS+['jerkin']]
CHAIN=['bronze_pansarkedja_'+s for s in SLOTS+['hauberk']]

def without_class(classes,class_id):
    return ''.join(x+';' for x in classes.split(';') if x and x!=class_id)

def apply(c):
    c.row_factory=sqlite3.Row
    def insert(table,values):
        keys=list(values)
        c.execute('INSERT INTO "'+table+'" ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[values[k] for k in keys])
    version=c.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='valkyrie_test_data_version'").fetchone()
    if version is None or int(version['Value'] or 0)<4:raise ValueError("Apply Valkyrie Odin's Will revision 4 first.")
    grant=c.execute("SELECT AbilityLevel FROM SpecXAbility WHERE Spec='ValkyrieCareer' AND AbilityKey='MidArmor' AND SpecLevel=1 AND ClassId=34").fetchall()
    if len(grant)!=1:raise ValueError('Expected exactly one level-1 Valkyrie MidArmor grant.')
    c.execute("UPDATE SpecXAbility SET AbilityLevel=? WHERE Spec='ValkyrieCareer' AND AbilityKey='MidArmor' AND SpecLevel=1 AND ClassId=34",(CHAIN_LEVEL,))
    for template in CHAIN:
        item=c.execute('SELECT Object_Type,Realm FROM ItemTemplate WHERE Id_nb=?',(template,)).fetchone()
        if item is None or (item['Object_Type'],item['Realm'])!=(35,2):raise ValueError('Missing Midgard chain template '+template)
    for template in STUDDED:
        for row in c.execute('SELECT StarterEquipmentID,Class FROM StarterEquipment WHERE TemplateID=?',(template,)).fetchall():
            if CLASS in row['Class'].split(';'):
                c.execute('UPDATE StarterEquipment SET Class=? WHERE StarterEquipmentID=?',(without_class(row['Class'],CLASS),row['StarterEquipmentID']))
    for template in CHAIN:
        if not c.execute("SELECT 1 FROM StarterEquipment WHERE TemplateID=? AND Class=?",(template,CLASS+';')).fetchone():
            insert('StarterEquipment',dict(Class=CLASS+';',TemplateID=template))
    if int(version['Value'])<int(VERSION):
        c.execute("UPDATE ServerProperty SET Value=? WHERE lower(Key)='valkyrie_test_data_version'",(VERSION,))
    return {'MidArmorLevelAtOne':CHAIN_LEVEL,'StarterArmor':CHAIN,'ExistingCharactersModified':False}

def main():
    repo=Path(__file__).resolve().parents[2];root=repo/'artifacts/modern-client-test';db=root/'runtime/data/opendaoc.sqlite3.db'
    check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; if([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 10330){exit 9}"],capture_output=True)
    if check.returncode:raise SystemExit('Stop the test server; listener inspection must succeed before applying data.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=root/'backups'/('pre-valkyrie-chain-armor-'+stamp+'.sqlite3.db')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:source.backup(target)
    with sqlite3.connect(db) as c:
        c.execute('BEGIN IMMEDIATE');report=apply(c);c.commit()
    (root/'valkyrie-chain-armor-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__=='__main__':main()
