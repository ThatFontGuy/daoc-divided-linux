"""Remove the low-level Cothrom Gorge spore seeds and make Leptus always level 6. Default is a read-only dry run.

Use --apply only after the server and launcher are closed.

1. Leptus (Domnann, NpcTemplate 60163225): the template level "6;51" rolled level 6 or level 51 on
   every respawn, putting a roaming level 51 aggressive creature among level 0-8 starter mobs.
   The template level becomes "6" and the two Leptus spawns are stored at level 6. Nothing else
   about Leptus changes.
2. Venomous spore seed (Cothrom Gorge, NpcTemplate 60167608): 13 level 6-7 spawns sit inside the
   level 42-55 venomous spore / lurking shrouder / botonid disperser field and drew level 6-11
   bots across the Shrouded Isles to die. Six of them were already recorded by the 1.65 spawn
   audit as post-legacy neutral spawns. Every seed gets a row in that archive table
   (offline_classic165_removed_mobs, with a reason) and is deleted from Mob. The level 48-55
   "venomous spore" spawns (NpcTemplate 60167607) are untouched.
3. Bots whose saved camp is a spore seed camp have that saved camp/target/route cleared so they
   choose a new camp. With no live seeds, the camp catalog can no longer offer one.
"""
import argparse
import datetime
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # <playable>/tools/claude-version/
DB = ROOT / 'runtime/data/opendaoc.sqlite3.db'
LEPTUS_TEMPLATE = 60163225
SEED_TEMPLATE = 60167608
SPORE_TEMPLATE = 60167607
SEED_REASON = ('Low-level venomous spore seed inside the level 42-55 Cothrom Gorge spore field; '
               'removed so low-level bots are not sent there (2026-09-30)')
SEED_CAMP = '%:venomous spore seed:%'


def seed_rows(db):
    return db.execute("SELECT * FROM Mob WHERE Name='venomous spore seed' AND Region=181 AND NPCTemplateID=?",
                      (SEED_TEMPLATE,)).fetchall()


def spore_count(db):
    return db.execute('SELECT COUNT(*) FROM Mob WHERE NPCTemplateID=?', (SPORE_TEMPLATE,)).fetchone()[0]


def has_table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def update(db):
    template = db.execute('SELECT Name, Level FROM NpcTemplate WHERE TemplateId=?', (LEPTUS_TEMPLATE,)).fetchone()
    if template is None or template['Name'] != 'Leptus' or template['Level'] not in ('6;51', '6'):
        raise RuntimeError('Leptus template changed since this fix was prepared')
    db.execute("UPDATE NpcTemplate SET Level='6' WHERE TemplateId=?", (LEPTUS_TEMPLATE,))
    leptus = db.execute("UPDATE Mob SET Level=6 WHERE NPCTemplateID=? AND Name='Leptus'", (LEPTUS_TEMPLATE,)).rowcount

    spores_before = spore_count(db)
    seeds = seed_rows(db)
    if any(row['Level'] > 10 for row in seeds):
        raise RuntimeError('A seed spawn is above level 10; refusing to touch it')
    columns = list(seeds[0].keys()) if seeds else []
    for row in seeds:
        # Six seeds already have an archive row from the 1.65 audit; keep that original row.
        if db.execute('SELECT 1 FROM offline_classic165_removed_mobs WHERE Mob_ID=?', (row['Mob_ID'],)).fetchone() is None:
            db.execute('INSERT INTO offline_classic165_removed_mobs (' + ','.join('"' + c + '"' for c in columns) +
                       ',RemovalReason,RemovedUtc) VALUES (' + ','.join('?' for _ in columns) + ',?,?)',
                       (*tuple(row), SEED_REASON, datetime.datetime.now(datetime.timezone.utc).isoformat()))
        db.execute('DELETE FROM Mob WHERE Mob_ID=?', (row['Mob_ID'],))
    if spore_count(db) != spores_before or seed_rows(db):
        raise RuntimeError('Seed removal touched the wrong rows')

    bots = 0
    if has_table(db, 'offline_world_bots'):
        bots = db.execute("UPDATE offline_world_bots SET CurrentCampId='', TargetName='', TravelDestination='', "
                          "ItineraryJson='', CurrentGoal='Find a reachable level-appropriate XP camp', "
                          "Activity='Choosing a new camp' WHERE CurrentCampId LIKE ?", (SEED_CAMP,)).rowcount
    return leptus, len(seeds), spores_before, bots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    # Run the exact change twice on an in-memory copy of the whole database first.
    with sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(':memory:') as test:
        source.backup(test)
        test.row_factory = sqlite3.Row
        leptus, seeds, spores, bots = update(test)
        again = update(test)
        if again[1] or again[3]:
            raise RuntimeError('Second run was not a no-op')
    print(f'Leptus spawns set to level 6: {leptus}; seeds archived and removed: {seeds}; '
          f'venomous spores kept: {spores}; bots with a seed camp cleared: {bots}')
    if not args.apply:
        print('Dry run passed; rerun is safe. Live database untouched.')
        return
    running = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        'Get-Process CoreServer,DOLServer,OfflineDAoC -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'], text=True)
    if running.strip():
        raise RuntimeError('Close server and launcher before applying: ' + running.strip())
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT / 'runtime/server/deployment-backups' / ('cothrom-seeds-leptus-' + stamp)
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
