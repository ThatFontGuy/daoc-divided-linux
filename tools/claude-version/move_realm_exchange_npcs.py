"""Move the Midgard and Albion Realm Exchange NPCs and their two guards. Default is a read-only dry run.

  python tools\\claude-version\\move_realm_exchange_npcs.py            (dry run)
  python tools\\claude-version\\move_realm_exchange_npcs.py --apply    (server, launcher and game closed)
  python tools\\claude-version\\move_realm_exchange_npcs.py --undo     (back to the previous spots)

The Jordheim broker (for example Brynhild; each install picks the names) had been moved into the
narrow vault-keeper corridor, where bots traded with it through a wall. It goes back to the small
ledge by the Name Registrar. The Camelot broker (for example Adalyn) was crowded onto the
vault-keeper platform; it moves into the open courtyard in front of the benches. Rows are found
by their fixed Mob_ID, never by name.
Each broker faces the owner's chosen direction with a guard on either side. Only position and
heading change: names, models, gear, listings and money are untouched. Bots find the broker by
its live position, so no bot data needs changing. The spots were proven on the installed navmesh
by source/server/Tests/UnitTests/UT_RealmExchangeRelocation.cs.
"""
import argparse
import datetime
import math
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # <playable>/tools/claude-version/
DB = ROOT / 'runtime/data/opendaoc.sqlite3.db'
ZONE_OFFSET = 8192  # Camelot and Jordheim zones start at 1 * 8192; /loc shows zone coordinates

# realm id prefix, region, old (x, y, z, heading), new /loc (x, y, z), new heading, guard spacing
MOVES = [
    ('offline-realm-exchange-midgard', 101, (32250, 28294, 8819, 2048), (23549, 19848, 8798), 4094, 100),
    ('offline-realm-exchange-albion', 10, (36200, 30300, 8000, 0), (28429, 22509, 8002), 2066, 90),
]


def positions(prefix, old, loc, heading, spacing):
    """{Mob_ID: (old x, y, z, heading), (new x, y, z, heading)} for the broker and both guards."""
    ox, oy, oz, oh = old
    nx, ny, nz = loc[0] + ZONE_OFFSET, loc[1] + ZONE_OFFSET, loc[2]
    # DOL heading h faces (-sin, cos); its sides lie along (cos, sin). The old rows sat on
    # the X axis at -/+ their spacing, as the setup tool wrote them.
    angle = heading * 2 * math.pi / 4096
    side = (math.cos(angle), math.sin(angle))
    old_spacing = {'offline-realm-exchange-midgard': 100, 'offline-realm-exchange-albion': 90}[prefix]
    rows = {prefix: ((ox, oy, oz, oh), (nx, ny, nz, heading))}
    for suffix, sign in (('-guard-left', -1), ('-guard-right', 1)):
        rows[prefix + suffix] = (
            (ox + sign * old_spacing, oy, oz, oh),
            (round(nx + sign * spacing * side[0]), round(ny + sign * spacing * side[1]), nz, heading))
    return rows


def plan():
    rows = {}
    for prefix, region, old, loc, heading, spacing in MOVES:
        for mob_id, (before, after) in positions(prefix, old, loc, heading, spacing).items():
            rows[mob_id] = (region, before, after)
    return rows


def change(db, undo=False):
    changed = []
    for mob_id, (region, before, after) in plan().items():
        frm, to = (after, before) if undo else (before, after)
        row = db.execute('SELECT Region, X, Y, Z, Heading, PackageID FROM Mob WHERE Mob_ID=?', (mob_id,)).fetchone()
        if row is None or row[0] != region or row[5] != 'offline_realm_exchange':
            raise RuntimeError(f'{mob_id}: row missing or not an exchange row; data changed')
        current = tuple(int(v) for v in row[1:5])
        if current not in (frm, to):
            raise RuntimeError(f'{mob_id}: at {current}, expected {frm}; it was moved since this fix was prepared')
        n = db.execute('UPDATE Mob SET X=?, Y=?, Z=?, Heading=? WHERE Mob_ID=? AND X=? AND Y=? AND Z=? AND Heading=?',
                       (*to, mob_id, *frm)).rowcount
        changed.append((mob_id, frm, to, n))
    return changed


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
        if any(n for *_, n in change(test, undo)):
            raise RuntimeError('Second run was not a no-op')
    for mob_id, frm, to, n in first:
        print(f'{mob_id}: {frm} -> {to} ({"changes" if n else "already there"})')
    if not (args.apply or args.undo):
        print('Dry run passed; rerun is safe. Live database untouched.')
        return
    running = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        'Get-Process CoreServer,DOLServer,OfflineDAoC,game -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'], text=True)
    if running.strip():
        raise RuntimeError('Close the server, launcher and game first: ' + running.strip())
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT / 'runtime/server/deployment-backups' / ('realm-exchange-move-' + ('undo-' if undo else '') + stamp)
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
