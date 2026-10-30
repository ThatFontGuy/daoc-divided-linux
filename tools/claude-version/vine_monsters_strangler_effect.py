"""Give the invisible vine monsters the strangler's Tangling Vines effect. Default is a read-only dry run.

  python tools\\claude-version\\vine_monsters_strangler_effect.py            (dry run)
  python tools\\claude-version\\vine_monsters_strangler_effect.py --apply    (server and launcher closed)
  python tools\\claude-version\\vine_monsters_strangler_effect.py --undo     (back to plain GameNPC)

choker, shackler and Throttler (Dales of Devwy) and tendril (Aegir's Landing) use model 667, the
client's "Invisible Warrior", with no equipment and no effect, so only their name shows. The
strangler next to them uses the same invisible model, but its DOL.GS.Scripts.Strangler class plays
the client effect 5206 "Tangling Vines" on itself every 3 seconds, which is what players see.
This gives these four monsters (their spawns and their templates) the same class. Stats, level,
loot and model are unchanged. Like the strangler, they then think every 3 seconds and are no longer
offered as bounty, reputation-hunt or charm targets (those lists take plain GameNPC only).
"""
import argparse
import datetime
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # <playable>/tools/claude-version/
DB = ROOT / 'runtime/data/opendaoc.sqlite3.db'
PLAIN = 'DOL.GS.GameNPC'
STRANGLER = 'DOL.GS.Scripts.Strangler'
# name, region, template id, expected spawn count
TARGETS = [
    ('choker', 51, 60159172, 4),
    ('shackler', 51, 60165895, 6),
    ('Throttler', 51, 60167055, 1),
    ('tendril', 151, 60166896, 7),
]


def change(db, undo=False):
    old, new = (STRANGLER, PLAIN) if undo else (PLAIN, STRANGLER)
    counts = []
    for name, region, template, spawns in TARGETS:
        rows = db.execute('SELECT ClassType, Model FROM Mob WHERE Name=? AND Region=? AND NPCTemplateID=?',
                          (name, region, template)).fetchall()
        if len(rows) != spawns or any(str(r[1]) != '667' for r in rows):
            raise RuntimeError(f'{name}: expected {spawns} spawns on model 667, found {len(rows)}; data changed')
        if any(r[0] not in (old, new) for r in rows):
            raise RuntimeError(f'{name}: unexpected ClassType {set(r[0] for r in rows)}')
        t = db.execute('SELECT Name, Model, ClassType FROM NpcTemplate WHERE TemplateId=?', (template,)).fetchone()
        if t is None or t[0] != name or str(t[1]).strip() != '667' or t[2] not in (old, new):
            raise RuntimeError(f'{name}: template {template} changed since this fix was prepared')
        m = db.execute('UPDATE Mob SET ClassType=? WHERE Name=? AND Region=? AND NPCTemplateID=? AND ClassType=?',
                       (new, name, region, template, old)).rowcount
        t = db.execute('UPDATE NpcTemplate SET ClassType=? WHERE TemplateId=? AND ClassType=?',
                       (new, template, old)).rowcount
        counts.append((name, m, t))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true')
    group.add_argument('--undo', action='store_true')
    args = parser.parse_args()
    undo = args.undo
    with sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(':memory:') as test:
        source.backup(test)
        first = change(test, undo)
        again = change(test, undo)
        if any(m or t for _, m, t in again):
            raise RuntimeError('Second run was not a no-op')
    for name, m, t in first:
        print(f'{name}: spawns changed {m}, template changed {t}')
    if not (args.apply or args.undo):
        print('Dry run passed; rerun is safe. Live database untouched.')
        return
    running = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        'Get-Process CoreServer,DOLServer,OfflineDAoC,game -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'], text=True)
    if running.strip():
        raise RuntimeError('Close the server, launcher and game first: ' + running.strip())
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT / 'runtime/server/deployment-backups' / ('vine-monsters-' + ('undo-' if undo else '') + stamp)
    backup.mkdir(parents=True, exist_ok=False)
    with sqlite3.connect(DB) as db:
        with sqlite3.connect(backup / 'opendaoc.sqlite3.db') as copy:
            db.backup(copy)
        db.execute('BEGIN IMMEDIATE')
        change(db, undo)
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('Integrity check failed; rolling back')
        db.commit()
    print('Applied.' if not undo else 'Undone.', 'Backup:', backup)


if __name__ == '__main__':
    main()
