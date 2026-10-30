"""Staged Cursed Forest camp repair. Default is a read-only dry run.

Use --apply only after the server and launcher are closed. Changes only XYZ
for three existing spawns; retains levels, loot, identities and roaming rules.
Positions were checked against zone208.nav, including 260-unit radial clearance
and complete paths between positions. Client tree clearance needs a live check.
"""
import argparse
import datetime
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / 'runtime/data/opendaoc.sqlite3.db'
MOVES = (
    ('a5fcfaa8-5e59-4a99-acf5-3b1fbee4ae97', (467388,523107,5090), (467047,522587,5075)),
    ('e1a79181-8d10-4cde-a27d-8244311f2adb', (467577,522996,5103), (468547,522587,5091)),
    ('d897c969-737e-4d12-a082-81612a5d4a26', (467304,524483,4995), (468047,523337,5115)),
)

def validate(db):
    rows=[]
    for identity, old, new in MOVES:
        row=db.execute('SELECT * FROM Mob WHERE Mob_ID=?',(identity,)).fetchone()
        if row is None or row['Name']!='forest poacher' or row['Region']!=200:
            raise RuntimeError('Spawn identity changed: '+identity)
        if tuple(row[k] for k in ('X','Y','Z')) not in (old,new):
            raise RuntimeError('Spawn moved since preparation: '+identity)
        rows.append(dict(row))
    return rows

def update(db):
    before=validate(db)
    for identity, old, new in MOVES:
        db.execute('UPDATE Mob SET X=?,Y=?,Z=? WHERE Mob_ID=?',(*new,identity))
    after=validate(db)
    for original,current in zip(before,after):
        assert all(current[k]==v for k,v in original.items() if k not in ('X','Y','Z'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True) as source:
        source.row_factory=sqlite3.Row
        rows=validate(source)
        # Exercise the exact update on an in-memory copy of these rows only.
        with sqlite3.connect(':memory:') as test:
            test.row_factory=sqlite3.Row
            schema=source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Mob'").fetchone()[0]
            test.execute(schema)
            columns=','.join('"'+k+'"' for k in rows[0])
            for row in rows:
                test.execute('INSERT INTO Mob ('+columns+') VALUES ('+','.join('?' for _ in row)+')',tuple(row.values()))
            update(test)
            update(test)  # Idempotency.
        for identity,old,new in MOVES:
            print(identity,old,'->',new,'local:',(new[0]-450560,new[1]-483328,new[2]))
    if not args.apply:
        print('Dry run passed: only XYZ changes; rerun is safe. Live database untouched.')
        return
    running=subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-Process CoreServer,DOLServer,OfflineDAoC -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'],text=True)
    if running.strip():
        raise RuntimeError('Close server and launcher before applying: '+running.strip())
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup=ROOT/'runtime/server/deployment-backups'/('forest-poacher-'+stamp)
    backup.mkdir(parents=True,exist_ok=False)
    with sqlite3.connect(DB) as db:
        db.row_factory=sqlite3.Row
        with sqlite3.connect(backup/'opendaoc.sqlite3.db') as copy:
            db.backup(copy)
        db.execute('BEGIN IMMEDIATE')
        update(db)
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':
            raise RuntimeError('Integrity check failed; rolling back')
        db.commit()
    print('Applied. Backup:',backup)

if __name__=='__main__': main()
