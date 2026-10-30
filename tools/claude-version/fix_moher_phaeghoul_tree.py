"""Move the Cliffs of Moher phaeghoul that spawns inside a dead tree. Default is a read-only dry run.

Use --apply only after the server and launcher are closed. Changes only XYZ for one existing spawn.
Its level, loot, identity, respawn time and 200-unit roaming range are kept.

Evidence (checked 2026-09-30):
- The spawn is 4 units from client fixture 83, "Dead Tree" (Hdeadtree.nif), in
  zone203 fixtures.csv at local 11520,52736,5224. No other fixture is within 900 units.
- The new spot comes from zone203.nav. It is 279 units from the tree and at least 150 from
  every other phaeghoul. It has open walkable ground in all directions for its full
  200-unit roam radius, and has complete paths to and from all nine other camp spawns.
"""
import argparse
import datetime
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # <playable>/tools/claude-version/
DB = ROOT / 'runtime/data/opendaoc.sqlite3.db'
ZONE_OFFSET = (221184, 417792)  # zone 203, Cliffs of Moher
MOB_ID = '8128f262-0367-479d-bb76-694aa276ec25'
OLD = (232706, 470524, 5224)
NEW = (232904, 470722, 5249)


def validate(db):
    row = db.execute('SELECT * FROM Mob WHERE Mob_ID=?', (MOB_ID,)).fetchone()
    if row is None or row['Name'] != 'phaeghoul' or row['Region'] != 200:
        raise RuntimeError('Spawn identity changed: ' + MOB_ID)
    if tuple(row[k] for k in ('X', 'Y', 'Z')) not in (OLD, NEW):
        raise RuntimeError('Spawn moved since this fix was prepared: ' + MOB_ID)
    return dict(row)


def update(db):
    before = validate(db)
    db.execute('UPDATE Mob SET X=?,Y=?,Z=? WHERE Mob_ID=?', (*NEW, MOB_ID))
    after = validate(db)
    assert all(after[k] == v for k, v in before.items() if k not in ('X', 'Y', 'Z'))
    assert tuple(after[k] for k in ('X', 'Y', 'Z')) == NEW


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True) as source:
        source.row_factory = sqlite3.Row
        row = validate(source)
        # Exercise the exact update on an in-memory copy of this row only.
        with sqlite3.connect(':memory:') as test:
            test.row_factory = sqlite3.Row
            schema = source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Mob'").fetchone()[0]
            test.execute(schema)
            columns = ','.join('"' + k + '"' for k in row)
            test.execute('INSERT INTO Mob (' + columns + ') VALUES (' + ','.join('?' for _ in row) + ')', tuple(row.values()))
            update(test)
            update(test)  # Idempotency.
    print(MOB_ID, OLD, '->', NEW, 'local:', (NEW[0] - ZONE_OFFSET[0], NEW[1] - ZONE_OFFSET[1], NEW[2]))
    if not args.apply:
        print('Dry run passed: only XYZ changes; rerun is safe. Live database untouched.')
        return
    running = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        'Get-Process CoreServer,DOLServer,OfflineDAoC -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'], text=True)
    if running.strip():
        raise RuntimeError('Close server and launcher before applying: ' + running.strip())
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT / 'runtime/server/deployment-backups' / ('moher-phaeghoul-' + stamp)
    backup.mkdir(parents=True, exist_ok=False)
    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        with sqlite3.connect(backup / 'opendaoc.sqlite3.db') as copy:
            db.backup(copy)
        db.execute('BEGIN IMMEDIATE')
        update(db)
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('Integrity check failed; rolling back')
        db.commit()
    print('Applied. Backup:', backup)


if __name__ == '__main__':
    main()
