"""Valkyrie spell icons and visual effects as on live, from Eve of Darkness (db-public e0e6ed28).

valkyrie-icons-eod.json maps each owned Valkyrie spell (and the Odin's Aura proc spells) to the icon and
client effect of the same spell in Eve of Darkness's Odin's Will, Valkyrie Mending Spec and Mending lines.
Every ID exists in the bundled 1.130 client's spells.csv, which has its own Valkyrie block (12501-12554,
14810-14812). Only Icon and ClientEffect change; tooltips, mechanics and saves are untouched.

Weapon-style proc spells have no Valkyrie row in the client or Eve of Darkness, so STYLE_PROC_VISUALS gives
them the client's generic proc visual for their damage type and shape (spirit dd1/dd 2/PBAE; Roundhouse
takes the cold PBAE that Eve of Darkness uses for the same Crush proc, Force of the Roundhouse).
Rerun after valkyrie_progression/mending/odins_will/completion, which copy their template's icon.
"""
import datetime,hashlib,json,sqlite3,subprocess,sys
from pathlib import Path

DATA=Path(__file__).with_name('valkyrie-icons-eod.json')
EXPECTED_DATA_HASH='58540f70b28b39f2f02924a09bc9d9d4ec80140ff9b5c3f73ebaf16ff391d0e7'

# SpellID: (name, client spells.csv row used as both Icon and ClientEffect)
STYLE_PROC_VISUALS={
    65230:('Raze Effect',14325),            # 50 Spirit, single target: spirit dd1
    65212:('Polar Rift Effect',14325),      # 45 Spirit, single target
    65217:("Odin's Deathblow Effect",14326),# 150 Spirit, single target: spirit dd 2
    65218:('Ragnarok Effect',14326),
    65236:("Gungnir's Fury Effect",14329),  # 150 Spirit PBAoE: spirit PBAE
    65215:("Odin's Bite Effect",14329),     # Spirit power drain around the target
    65207:('Aurora Effect',14329),
    65234:('Roundhouse Effect',14323),      # 200 Crush PBAoE
}

def mapping():
    raw=DATA.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_DATA_HASH:raise ValueError('valkyrie-icons-eod.json hash mismatch')
    wanted={int(k):v for k,v in json.loads(raw)['spells'].items()}
    for spell_id,(name,row) in STYLE_PROC_VISUALS.items():
        wanted[spell_id]=dict(Name=name,Icon=row,ClientEffect=row)
    return wanted

def apply(c):
    c.row_factory=sqlite3.Row
    version=c.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='valkyrie_test_data_version'").fetchone()
    if version is None or int(version['Value'] or 0)<4:raise ValueError("Apply Valkyrie Odin's Will revision 4 first.")
    wanted=mapping();changed=[]
    for spell_id,row in wanted.items():
        spell=c.execute('SELECT Spell_ID,Name,Icon,ClientEffect FROM Spell WHERE SpellID=?',(spell_id,)).fetchone()
        if spell is None or not (spell['Spell_ID'] or '').startswith('local-valk-'):raise ValueError(f'Spell {spell_id} is not an owned Valkyrie spell')
        if spell['Name']!=row['Name'].removesuffix(' (proc)'):raise ValueError(f"Spell {spell_id} is {spell['Name']!r}, expected {row['Name']!r}")
        if (spell['Icon'],spell['ClientEffect'])!=(row['Icon'],row['ClientEffect']):
            changed.append(dict(SpellID=spell_id,Name=spell['Name'],From=[spell['Icon'],spell['ClientEffect']],To=[row['Icon'],row['ClientEffect']]))
            c.execute('UPDATE Spell SET Icon=?,ClientEffect=? WHERE SpellID=?',(row['Icon'],row['ClientEffect'],spell_id))
    return dict(Managed=len(wanted),Changed=changed,SavesModified=False)

def main():
    repo=Path(__file__).resolve().parents[2];root=repo/'artifacts/modern-client-test';db=root/'runtime/data/opendaoc.sqlite3.db'
    if '--apply' not in sys.argv:
        with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(':memory:') as c:
            source.backup(c);report=apply(c)
        print(json.dumps(dict(Preview=True,Managed=report['Managed'],Changed=len(report['Changed']))));return
    check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; if([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 10330){exit 9}"],capture_output=True)
    if check.returncode:raise SystemExit('Stop the test server; listener inspection must succeed before applying data.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=root/'backups'/('pre-valkyrie-icons-'+stamp+'.sqlite3.db')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:source.backup(target)
    with sqlite3.connect(db) as c:
        c.execute('BEGIN IMMEDIATE');report=apply(c);c.commit()
    (root/'valkyrie-icons-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(Managed=report['Managed'],Changed=len(report['Changed']),Backup=backup.name)))

if __name__=='__main__':main()
