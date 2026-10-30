"""Add four bantam spectres and two koalinth sentinels at Cliffs of Moher. Default is a read-only dry run.

Use --apply only after the server and launcher are closed.

Why: two Moher spawns of each were taken off the bot camp list because they sit next to much
higher-level aggressive monsters (see AutonomousAuditedCampPolicy). That left one bantam
spectre and two Moher koalinth sentinels for bots. These new spawns are exact copies of the safe
spawn next to them (same template, level, loot, respawn time and 200-unit roam); only the
identity, position and facing differ.

How the positions were chosen (zone203.nav and zone203 fixtures.csv, checked 2026-09-30):
- snapped to the navmesh, with open walkable ground all the way round the 200-unit roam radius;
- at least 200 units from every client fixture (trees, rocks, buildings), more for large ones;
- no aggressive monster 15+ levels above the camp within 1,200 units;
- at least 150 units from any other monster and 350 from another spawn of the same monster;
- inside the same 1,500-unit bot camp cell as the safe spawn, with walking paths both ways.
"""
import argparse
import datetime
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # <playable>/tools/claude-version/
DB = ROOT / 'runtime/data/opendaoc.sqlite3.db'
SPECTRE_SOURCE = '104709c2-6fd4-4591-b0f1-74eaf7632b9a'
SENTINEL_SOURCE = '66a7a6b7-a196-45a6-aafb-e46d60010e86'
# (new Mob_ID, copied from, name, X, Y, Z, heading)
NEW_SPAWNS = [
    ('bb1e3549-8dba-4441-8213-048c7ad9d221', SPECTRE_SOURCE, 'bantam spectre', 264191, 461326, 5728, 3410),
    ('454ccc24-c996-4ad3-83b4-5f54d6773942', SPECTRE_SOURCE, 'bantam spectre', 265495, 461633, 5581, 610),
    ('5f2d6644-fe48-4264-b89e-b41743be9524', SPECTRE_SOURCE, 'bantam spectre', 265154, 461808, 5638, 1890),
    ('a8640772-f080-42cb-962a-cde99ef02983', SPECTRE_SOURCE, 'bantam spectre', 265158, 461038, 5646, 2750),
    ('6c497f5a-667a-449d-81b5-c12f205d6e93', SENTINEL_SOURCE, 'koalinth sentinel', 248579, 472226, 5522, 1240),
    ('e6fd0b7d-d082-4b4e-9509-25c4fc98e286', SENTINEL_SOURCE, 'koalinth sentinel', 248255, 471598, 5523, 3020),
]


def update(db):
    added = 0
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for mob_id, source_id, name, x, y, z, heading in NEW_SPAWNS:
        source = db.execute('SELECT * FROM Mob WHERE Mob_ID=?', (source_id,)).fetchone()
        if source is None or source['Name'] != name or source['Region'] != 200:
            raise RuntimeError('Source spawn changed since this fix was prepared: ' + source_id)
        existing = db.execute('SELECT Name, X, Y, Z FROM Mob WHERE Mob_ID=?', (mob_id,)).fetchone()
        if existing is not None:
            if tuple(existing) != (name, x, y, z):
                raise RuntimeError('A different spawn already uses ' + mob_id)
            continue
        row = dict(source)
        row.update(Mob_ID=mob_id, X=x, Y=y, Z=z, Heading=heading, LastTimeRowUpdated=stamp)
        db.execute('INSERT INTO Mob (' + ','.join('"' + k + '"' for k in row) + ') VALUES (' +
                   ','.join('?' for _ in row) + ')', tuple(row.values()))
        added += 1
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(':memory:') as test:
        source.backup(test)
        test.row_factory = sqlite3.Row
        added = update(test)
        if update(test):
            raise RuntimeError('Second run was not a no-op')
    print(f'New spawns to add: {added} of {len(NEW_SPAWNS)}')
    if not args.apply:
        print('Dry run passed; rerun is safe. Live database untouched.')
        return
    running = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        'Get-Process CoreServer,DOLServer,OfflineDAoC -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'], text=True)
    if running.strip():
        raise RuntimeError('Close server and launcher before applying: ' + running.strip())
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT / 'runtime/server/deployment-backups' / ('moher-spectre-sentinel-' + stamp)
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
