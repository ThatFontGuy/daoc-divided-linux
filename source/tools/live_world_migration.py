"""Move this world's spawns and doors onto live's (retail 1.130) geometry: fix B of docs/MODERN-CLIENT-WORLD-MISMATCH.md.

    python live_world_migration.py plan     <db> <classic exports> <live exports> <zones.dat> <zone ids> <plan.json>
    python live_world_migration.py apply    <db> <plan.json> --backups <folder> [--apply]
    python live_world_migration.py rollback <db> <backup folder> [--apply]

<classic exports> and <live exports> are OpenDAoC-BuildNav output folders (base/zones) built from the classic
client and from the 1.130 client: zoneNNN.obj (collision geometry, world units / 32, y up), zoneNNN.doors and,
for the live side, zoneNNN.nav. The plan step reads them and the world read-only:

  * A position is "affected" when the live geometry differs there from the classic geometry: a surface now cuts
    through the body (16-160 units above the floor), the floor under it moved more than 48 units, or it lost its
    floor. Unaffected rows are left exactly as they are.
  * An affected position moves to the nearest spot on the live navmesh (so the server can path there) in a
    large connected walkable area, within 200 units of its height: first straight up or down, then in rings out
    to 800 units. Failing that, onto the live floor straight below or above within 800 units (keep guards whose
    classic wall walk is gone). Failing that (tower tops and ledges the navmesh leaves out), onto the nearest live
    surface with standing room, searched the same way. Anything still unplaced is listed as unresolved and left alone.
  * Checked: Mob, BindPoint, Teleport, ZonePoint targets, WorldObject and PathPoints.
  * Doors: a door whose ID live also has takes live's position (heading turned by the model's change); a door
    whose ID live lacks moves to live's nearest door of the same model family (btavern -> btavern_normal) within
    512 units, keeping its realm, lock and guild. Doors live adds that the world doesn't have are left to the
    server's unknown-door handling.

apply previews unless --apply is given. It refuses while the database is locked (server running), copies the
database to --backups first, changes only rows that still hold the plan's old values, and verifies them.
rollback puts the plan's old values back on the rows it changed (leaving everything saved since untouched).
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server' / 'tools' / 'navmesh_splice'))

FORMAT = 1
BODY_LOW, BODY_HIGH = 16, 160
FLOOR_MOVED = 48
SEARCH_HEIGHT = 200
SEARCH_RADIUS = 800
SEARCH_STEP = 32
FALLBACK_HEIGHT = 800
GEOMETRY_DROP = 1500  # tower guards whose live tower has no top: onto the courtyard rather than in the air
MIN_AREA_POLYS = 200
DOOR_FAMILY_RADIUS = 512
DOOR_SUFFIX = re.compile(r'(_normal|_burned|_reconstructed|_nuked|_frozen|_p\d\d)$')

# (table, key column, region column, x, y, z, extra columns to carry)
POINT_TABLES = [
    ('Mob', 'Mob_ID', 'Region', 'X', 'Y', 'Z', ('Name',)),
    ('BindPoint', 'BindPoint_ID', 'Region', 'X', 'Y', 'Z', ()),
    ('Teleport', 'Teleport_ID', 'RegionID', 'X', 'Y', 'Z', ('TeleportID',)),
    ('ZonePoint', 'ZonePoint_ID', 'TargetRegion', 'TargetX', 'TargetY', 'TargetZ', ('Id',)),
    ('WorldObject', 'WorldObject_ID', 'Region', 'X', 'Y', 'Z', ('Name',)),
]


# Structures live moved as a whole. Live pulled three border keeps back inland (the old-frontier copies stay in the
# client's zone files but can't be reached). Positions are the keep fixtures' centres; the turn is measured from the
# two gate doors of each copy (the fixture angles differ by the models' own facing too). Every row near a keep moves
# and turns with it, then takes the new floor.
STRUCTURES = [
    dict(name='Castle Sauvage', region=1, src=(585088, 477056), dst=(583936, 486720), turn=0),
    dict(name='Snowdonia Fortress', region=1, src=(528384, 358784), dst=(516608, 372800), turn=45),
    dict(name='Svasud Faste', region=100, src=(766208, 669536), dst=(765312, 673472), turn=-9),
]
# (table, key, region column, x, y, z, heading column, radius from the keep centre)
STRUCTURE_TABLES = [
    ('Mob', 'Mob_ID', 'Region', 'X', 'Y', 'Z', 'Heading', 2000),
    ('BindPoint', 'BindPoint_ID', 'Region', 'X', 'Y', 'Z', None, 2600),
    ('Teleport', 'Teleport_ID', 'RegionID', 'X', 'Y', 'Z', 'Heading', 2600),
    ('WorldObject', 'WorldObject_ID', 'Region', 'X', 'Y', 'Z', 'Heading', 2600),
    ('ZonePoint', 'ZonePoint_ID', 'TargetRegion', 'TargetX', 'TargetY', 'TargetZ', 'TargetHeading', 1000),
    ('Area', 'Area_ID', 'Region', 'X', 'Y', 'Z', None, 1000),
]


def carry(structure, x, y):
    """(x, y) moved with the structure: turned about its old centre, then shifted to its new one."""
    a = math.radians(structure['turn'])
    dx, dy = x - structure['src'][0], y - structure['src'][1]
    return (structure['dst'][0] + dx * math.cos(a) - dy * math.sin(a),
            structure['dst'][1] + dx * math.sin(a) + dy * math.cos(a))


def turn_heading(heading, degrees):
    """A DAoC heading (0-4095, atan2(-dx, dy)) turned with the world by `degrees` (counter-clockwise in x, y)."""
    return int(round(heading + degrees * 4096 / 360)) % 4096


# ---------------------------------------------------------------- geometry

class Geometry:
    """Collision triangles of one zone export, indexed by 128-unit cells, for vertical ray hits."""
    CELL = 128

    def __init__(self, path: Path):
        vertices, self.grid = [], collections.defaultdict(list)
        with open(path) as stream:
            for line in stream:
                if line.startswith('v '):
                    _, x, y, z = line.split()[:4]
                    vertices.append((float(x) * 32, float(z) * 32, float(y) * 32))
                elif line.startswith('f '):
                    a, b, c = (vertices[int(p.split('/')[0]) - 1] for p in line.split()[1:4])
                    x0, x1 = int(min(a[0], b[0], c[0]) // self.CELL), int(max(a[0], b[0], c[0]) // self.CELL)
                    y0, y1 = int(min(a[1], b[1], c[1]) // self.CELL), int(max(a[1], b[1], c[1]) // self.CELL)
                    if x1 - x0 > 40 or y1 - y0 > 40:
                        continue
                    for gx in range(x0, x1 + 1):
                        for gy in range(y0, y1 + 1):
                            self.grid[(gx, gy)].append((a, b, c))

    def heights(self, x, y):
        out = []
        for a, b, c in self.grid.get((int(x // self.CELL), int(y // self.CELL)), ()):
            v0x, v0y, v1x, v1y = b[0] - a[0], b[1] - a[1], c[0] - a[0], c[1] - a[1]
            d = v0x * v1y - v1x * v0y
            if abs(d) < 1e-9:
                continue
            v2x, v2y = x - a[0], y - a[1]
            u, v = (v2x * v1y - v1x * v2y) / d, (v0x * v2y - v2x * v0y) / d
            if u >= -1e-6 and v >= -1e-6 and u + v <= 1 + 1e-6:
                out.append(a[2] + u * (b[2] - a[2]) + v * (c[2] - a[2]))
        return out


def floor_below(heights, z):
    return max((h for h in heights if h <= z + FLOOR_MOVED), default=None)


def affected(classic: Geometry, live: Geometry, x, y, z) -> str | None:
    hc, hl = classic.heights(x, y), live.heights(x, y)
    if any(z + BODY_LOW < h < z + BODY_HIGH for h in hl) and not any(z + BODY_LOW < h < z + BODY_HIGH for h in hc):
        return 'inside live geometry'
    fc, fl = floor_below(hc, z), floor_below(hl, z)
    if fc is not None and abs(fc - z) < 64 and (fl is None or abs(fl - z) >= 64):
        return 'lost its floor'
    if fc is not None and fl is not None and abs(fc - fl) > FLOOR_MOVED:
        return 'floor moved'
    return None


class Walkable:
    """The live navmesh: a spot counts when it lies on a polygon of a large connected walkable area."""

    def __init__(self, nav_path: Path):
        from navcomp import NavAreas
        self.nav = NavAreas(str(nav_path))
        sizes = collections.Counter(self.nav._find(i) for i in range(len(self.nav.polys)))
        self.big = {root for root, n in sizes.items() if n >= MIN_AREA_POLYS}

    def at(self, x, y, z, tolerance):
        poly = self.nav.locate(x, y, z, tolerance=tolerance)
        if poly is None or self.nav._find(poly) not in self.big:
            return None
        return self.nav.height(poly, x, y)


def relocate(walk: Walkable, x, y, z):
    """(x, y, z, how) on the live navmesh, nearest first, or None."""
    h = walk.at(x, y, z, SEARCH_HEIGHT)
    if h is not None:
        return x, y, h, 'height fixed'
    for radius in range(SEARCH_STEP, SEARCH_RADIUS + 1, SEARCH_STEP):
        steps = max(8, int(2 * math.pi * radius / SEARCH_STEP))
        best = None
        for k in range(steps):
            a = 2 * math.pi * k / steps
            px, py = x + radius * math.cos(a), y + radius * math.sin(a)
            ph = walk.at(px, py, z, SEARCH_HEIGHT)
            if ph is not None and (best is None or abs(ph - z) < abs(best[2] - z)):
                best = (px, py, ph)
        if best:
            return round(best[0]), round(best[1]), best[2], f'moved {radius} units'
    h = walk.at(x, y, z, FALLBACK_HEIGHT)
    if h is not None:
        return x, y, h, 'dropped to the live floor'
    return None


def standing_room(live: Geometry, x, y, z, height):
    """The live surface nearest `z` (within `height`) with nothing 16-160 units above it, or None."""
    hits = live.heights(x, y)
    floors = [h for h in hits if abs(h - z) <= height and not any(h + BODY_LOW < o < h + BODY_HIGH for o in hits)]
    return min(floors, key=lambda h: abs(h - z), default=None)


def place_on_geometry(live: Geometry, x, y, z):
    """For spots off the navmesh (tower tops, ledges): a live surface with standing room, straight up or down within
    FALLBACK_HEIGHT, else the nearest within SEARCH_HEIGHT in rings out to SEARCH_RADIUS. (x, y, z, how) or None."""
    h = standing_room(live, x, y, z, SEARCH_HEIGHT)
    if h is not None:
        return x, y, h, 'height fixed on live geometry (off the navmesh)'
    for radius in range(SEARCH_STEP, SEARCH_RADIUS + 1, SEARCH_STEP):
        steps = max(8, int(2 * math.pi * radius / SEARCH_STEP))
        best = None
        for k in range(steps):
            a = 2 * math.pi * k / steps
            px, py = x + radius * math.cos(a), y + radius * math.sin(a)
            ph = standing_room(live, px, py, z, SEARCH_HEIGHT)
            if ph is not None and (best is None or abs(ph - z) < abs(best[2] - z)):
                best = (px, py, ph)
        if best:
            return round(best[0]), round(best[1]), best[2], f'moved {radius} units on live geometry (off the navmesh)'
    h = standing_room(live, x, y, z, GEOMETRY_DROP)
    if h is not None:
        return x, y, h, 'dropped to live geometry (off the navmesh)'
    return None


# ---------------------------------------------------------------- zones and doors

def load_zones(zones_dat: Path) -> dict[int, tuple[int, int, int]]:
    """{zone id: (region, x offset, y offset)} from a client zones.dat."""
    text = zones_dat.read_text(encoding='latin1')
    out = {}
    for section in re.split(r'\n(?=\[)', text):
        m = re.match(r'\[zone(\d+)\]', section, re.I)
        if m:
            kv = {k.lower(): v.strip() for k, v in re.findall(r'^\s*(\w+)\s*=\s*([^;\r\n]*)', section, re.M)}
            try:
                out[int(m.group(1))] = (int(kv['region']), int(kv['region_offset_x']) * 8192, int(kv['region_offset_y']) * 8192)
            except (KeyError, ValueError):
                pass
    return out


def read_doors(path: Path) -> dict[int, tuple[str, int, int, int, int]]:
    """{door id: (model, x, y, z, heading)} from a BuildNav .doors export."""
    if not path.exists():
        return {}
    pattern = r'VALUES\((\d+), "([^"]+)", (-?\d+), (-?\d+), (-?\d+), (-?\d+)'
    return {int(m[1]): (m[2], int(m[3]), int(m[4]), int(m[5]), int(m[6])) for m in re.finditer(pattern, path.read_text())}


def family(model: str) -> str:
    return DOOR_SUFFIX.sub('', model.lower().rsplit('.', 1)[0])


def plan_doors(db, zone, classic_doors, live_doors):
    changes, unresolved = [], []
    rows = db.execute('select Door_ID, InternalID, X, Y, Z, Heading from Door where InternalID between ? and ?',
                      (zone * 1000000, zone * 1000000 + 999999)).fetchall()
    taken = {r[1] for r in rows}
    for key, door_id, x, y, z, heading in rows:
        old = dict(InternalID=door_id, X=x, Y=y, Z=z, Heading=heading)
        target = door_id if door_id in live_doors else None
        if target is None and door_id in classic_doors:
            model, cx, cy, _, _ = classic_doors[door_id]
            near = [(math.hypot(lx - cx, ly - cy), lid) for lid, (lm, lx, ly, _, _) in live_doors.items()
                    if lid not in taken and family(lm) == family(model)]
            near = [n for n in near if n[0] <= DOOR_FAMILY_RADIUS]
            if near:
                target = min(near)[1]
                taken.add(target)
        if target is None:
            if door_id in classic_doors:
                unresolved.append(dict(table='Door', key=key, id=door_id, reason='live has no such door nearby'))
            continue
        _, lx, ly, lz, lh = live_doors[target]
        turn = (lh - classic_doors[door_id][4]) if door_id in classic_doors else 0
        new = dict(InternalID=target, X=lx, Y=ly, Z=lz, Heading=(heading + turn) % 4096)
        if new['InternalID'] != door_id or math.dist((x, y, z), (lx, ly, lz)) > 32:
            changes.append(dict(table='Door', key_column='Door_ID', key=key, old=old, new=new,
                                reason='door renumbered' if target != door_id else 'door moved'))
    return changes, unresolved


# ---------------------------------------------------------------- plan

def plan(db_path: Path, classic_dir: Path, live_dir: Path, zones_dat: Path, zone_ids: list[int]) -> dict:
    with closing(sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        return _plan(db, db_path, classic_dir, live_dir, zones_dat, zone_ids)


def _plan(db, db_path, classic_dir, live_dir, zones_dat, zone_ids):
    zones = load_zones(zones_dat)
    changes, unresolved, summary = plan_structures(db, zones, classic_dir, live_dir)
    carried = {(c['table'], c['key']) for c in changes}
    paths = collections.defaultdict(list)
    for path_id, step, x, y, z, key, region in db.execute(
            'select p.PathID, p.Step, p.X, p.Y, p.Z, p.PathPoints_ID, h.RegionID from PathPoints p join Path h on h.PathID = p.PathID'):
        paths[region].append((key, x, y, z, f'path {path_id} step {step}'))
    for zone in zone_ids:
        name = f'zone{zone:03d}'
        if zone not in zones or not (classic_dir / f'{name}.obj').exists() or not (live_dir / f'{name}.obj').exists():
            summary[zone] = 'skipped (no export)'
            continue
        region, ox, oy = zones[zone]
        classic, live = Geometry(classic_dir / f'{name}.obj'), Geometry(live_dir / f'{name}.obj')
        walk = None
        counts = collections.Counter()
        points = []
        for table, key_column, region_column, xc, yc, zc, extra in POINT_TABLES:
            for row in db.execute(f'select {key_column}, {xc}, {yc}, {zc} {"".join(", " + e for e in extra)} from {table} '
                                  f'where {region_column}=? and {xc}>=? and {xc}<? and {yc}>=? and {yc}<?',
                                  (region, ox, ox + 65536, oy, oy + 65536)):
                points.append((table, key_column, (xc, yc, zc), row[0], row[1], row[2], row[3], ' '.join(map(str, row[4:]))))
        for key, x, y, z, label in paths.get(region, ()):
            if ox <= x < ox + 65536 and oy <= y < oy + 65536:
                points.append(('PathPoints', 'PathPoints_ID', ('X', 'Y', 'Z'), key, x, y, z, label))
        for table, key_column, columns, key, x, y, z, label in points:
            if (table, key) in carried:
                continue
            reason = affected(classic, live, x, y, z)
            if reason is None:
                continue
            if walk is None:
                if not (live_dir / f'{name}.nav').exists():
                    unresolved.append(dict(table=table, key=key, label=label, zone=zone, reason=reason + '; no live navmesh'))
                    continue
                walk = Walkable(live_dir / f'{name}.nav')
            spot = relocate(walk, x, y, z) or place_on_geometry(live, x, y, z)
            if spot is None:
                unresolved.append(dict(table=table, key=key, label=label, zone=zone, x=x, y=y, z=z, reason=reason))
                counts['unresolved'] += 1
                continue
            nx, ny, nz, how = spot
            changes.append(dict(table=table, key_column=key_column, key=key, label=label, zone=zone,
                                old={columns[0]: x, columns[1]: y, columns[2]: z},
                                new={columns[0]: int(round(nx)), columns[1]: int(round(ny)), columns[2]: int(round(nz))},
                                reason=f'{reason}; {how}'))
            counts[table] += 1
        door_changes, door_unresolved = plan_doors(db, zone, read_doors(classic_dir / f'{name}.doors'),
                                                   read_doors(live_dir / f'{name}.doors'))
        changes += door_changes
        unresolved += door_unresolved
        counts['Door'] += len(door_changes)
        counts['unresolved'] += len(door_unresolved)
        summary[zone] = dict(counts)
        print(f'zone {zone}: {dict(counts) or "no changes"}', flush=True)
    return dict(format=FORMAT, database=str(db_path), zones=zone_ids, summary=summary, changes=changes, unresolved=unresolved)


def zone_at(zones, region, x, y):
    return next((z for z, (r, ox, oy) in zones.items() if r == region and ox <= x < ox + 65536 and oy <= y < oy + 65536), None)


def plan_structures(db, zones, classic_dir, live_dir):
    """Rows carried with the STRUCTURES (moved keeps). Returns (changes, unresolved, summary)."""
    changes, unresolved, summary = [], [], {}
    cache = {}

    def load(kind, zone):
        if (kind, zone) not in cache:
            folder = classic_dir if kind == 'classic' else live_dir
            path = folder / f'zone{zone:03d}.{"nav" if kind == "walk" else "obj"}'
            cache[(kind, zone)] = None if not path.exists() else Walkable(path) if kind == 'walk' else Geometry(path)
        return cache[(kind, zone)]

    for s in STRUCTURES:
        region = s['region']
        src_zone, dst_zone = zone_at(zones, region, *s['src']), zone_at(zones, region, *s['dst'])
        area = db.execute('select Z from Area where Region=? and abs(X-?)<1000 and abs(Y-?)<1000',
                          (region, *s['src'])).fetchone()
        reference = area[0] if area else 0
        dst_walk = load('walk', dst_zone)
        dst_floor = dst_walk.at(*s['dst'], reference, 3000) if dst_walk else None
        if dst_floor is None:
            unresolved.append(dict(table='Structure', key=s['name'], reason='no live floor at the new keep'))
            continue
        lift = dst_floor - reference
        counts = collections.Counter()
        for table, key_column, region_column, xc, yc, zc, hc, radius in STRUCTURE_TABLES:
            columns = [key_column, xc, yc, zc] + ([hc] if hc else [])
            for row in db.execute(f'select {", ".join(columns)} from {table} where {region_column}=? and '
                                  f'({xc}-?)*({xc}-?)+({yc}-?)*({yc}-?) < ?',
                                  (region, s['src'][0], s['src'][0], s['src'][1], s['src'][1], radius * radius)):
                key, x, y, z = row[:4]
                nx, ny = carry(s, x, y)
                zone = zone_at(zones, region, nx, ny)
                walk, live = load('walk', zone), load('live', zone)
                guess = z + lift
                h = walk.at(nx, ny, guess, SEARCH_HEIGHT) if walk else None
                how = 'on the live navmesh'
                if h is None and live is not None:
                    h = standing_room(live, nx, ny, guess, SEARCH_HEIGHT)
                    how = 'on live geometry (off the navmesh)'
                if h is None:
                    h, how = guess, 'height kept relative to the keep'
                old = {xc: x, yc: y, zc: z}
                new = {xc: int(round(nx)), yc: int(round(ny)), zc: int(round(h))}
                if hc:
                    old[hc] = row[4]
                    new[hc] = turn_heading(row[4], s['turn'])
                changes.append(dict(table=table, key_column=key_column, key=key, label=s['name'], zone=zone,
                                    old=old, new=new, reason=f"moved with {s['name']}; {how}"))
                counts[table] += 1
        summary[s['name']] = dict(counts)
        print(f"{s['name']}: {dict(counts)}", flush=True)
    return changes, unresolved, summary


# ---------------------------------------------------------------- apply / rollback

def check_closed(db_path: Path):
    """The server holds the world open; refuse unless we can take an exclusive lock at once."""
    try:
        with closing(sqlite3.connect(db_path, timeout=0.5)) as con:
            con.execute('begin exclusive')
            con.rollback()
    except sqlite3.OperationalError:
        raise SystemExit('The world database is in use (is the server running?). Nothing was changed.')


def _matches(con, change, values):
    columns = list(values)
    row = con.execute(f'select {", ".join(columns)} from {change["table"]} where {change["key_column"]}=?',
                      (change['key'],)).fetchone()
    return row is not None and all(int(round(a)) == int(round(b)) for a, b in zip(row, (values[c] for c in columns)))


def _write(con, change, values):
    sets = ', '.join(f'{c}=?' for c in values)
    con.execute(f'update {change["table"]} set {sets} where {change["key_column"]}=?', (*values.values(), change['key']))


def _split_changed(con, changes, side, skip_changed):
    """(rows to write, rows left alone). A row no longer holding the plan's `side` values was rewritten since (the
    server re-saves some spawns, e.g. dragons lifted onto their lair floor): refuse, or with skip_changed keep it."""
    changed = [c for c in changes if not _matches(con, c, c[side])]
    if changed and not skip_changed:
        first = changed[0]
        raise SystemExit(f'{len(changed)} rows changed since (e.g. {first["table"]} {first["key"]} {first.get("label", "")}). '
                         'Nothing was changed. Use --skip-changed to leave those rows as they are now.')
    for c in changed:
        print(f'  left as it is now: {c["table"]} {c["key"]} {c.get("label", "")}')
    keys = {(c['table'], c['key']) for c in changed}
    return [c for c in changes if (c['table'], c['key']) not in keys], changed


def apply(db_path: Path, plan_path: Path, backups: Path, write: bool, skip_changed: bool = False):
    data = json.loads(plan_path.read_text(encoding='utf-8'))
    counts = collections.Counter(c['table'] for c in data['changes'])
    print(f'Plan: {sum(counts.values())} rows ({dict(counts)}), {len(data["unresolved"])} unresolved left alone')
    if not write:
        print('Preview only. Run again with --apply to change the world.')
        return None
    check_closed(db_path)
    folder = backups / f'live-world-{datetime.now():%Y%m%d-%H%M%S-%f}'
    folder.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as src, closing(sqlite3.connect(folder / db_path.name)) as dst:
        src.backup(dst)
    con = sqlite3.connect(db_path)
    try:
        con.execute('begin immediate')
        writes, skipped = _split_changed(con, data['changes'], 'old', skip_changed)
        for change in writes:
            _write(con, change, change['new'])
        bad = [c for c in writes if not _matches(con, c, c['new'])]
        if bad:
            raise RuntimeError(f'{len(bad)} rows did not take their new values')
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    # The backup's plan lists only the rows actually written, so a rollback restores exactly those.
    (folder / 'plan.json').write_text(json.dumps(dict(data, changes=writes, skipped=skipped), indent=1), encoding='utf-8')
    (folder / 'applied.txt').write_text(f'Applied {len(writes)} rows to {db_path}\n', encoding='utf-8')
    print(f'Applied and verified {len(writes)} rows ({len(skipped)} left as they were). Backup: {folder}')
    return folder


def rollback(db_path: Path, folder: Path, write: bool, skip_changed: bool = False):
    data = json.loads((folder / 'plan.json').read_text(encoding='utf-8'))
    print(f'Rollback of {len(data["changes"])} rows from {folder}')
    if not write:
        print('Preview only. Run again with --apply to restore the rows.')
        return
    check_closed(db_path)
    con = sqlite3.connect(db_path)
    try:
        con.execute('begin immediate')
        writes, skipped = _split_changed(con, data['changes'], 'new', skip_changed)
        for change in writes:
            _write(con, change, change['old'])
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    (folder / 'rolled-back.txt').write_text(f'Rolled back {len(writes)} rows of {db_path}; left {len(skipped)} as they were\n',
                                            encoding='utf-8')
    print(f'Rolled back {len(writes)} rows ({len(skipped)} left as they were).')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    for name in ('db', 'classic', 'live', 'zones_dat'):
        p.add_argument(name, type=Path)
    p.add_argument('zone_ids')
    p.add_argument('out', type=Path)
    a = sub.add_parser('apply'); a.add_argument('db', type=Path); a.add_argument('plan', type=Path)
    a.add_argument('--backups', type=Path, required=True); a.add_argument('--apply', action='store_true')
    a.add_argument('--skip-changed', action='store_true', help='leave rows rewritten since the plan as they are')
    r = sub.add_parser('rollback'); r.add_argument('db', type=Path); r.add_argument('backup', type=Path)
    r.add_argument('--apply', action='store_true')
    r.add_argument('--skip-changed', action='store_true', help='leave rows rewritten since the migration as they are')
    args = parser.parse_args(argv)
    if args.command == 'plan':
        data = plan(args.db, args.classic, args.live, args.zones_dat, [int(z) for z in args.zone_ids.split(',')])
        args.out.write_text(json.dumps(data, indent=1), encoding='utf-8')
        counts = collections.Counter(c['table'] for c in data['changes'])
        print(f'{sum(counts.values())} rows to change {dict(counts)}, {len(data["unresolved"])} unresolved. Plan: {args.out}')
    elif args.command == 'apply':
        apply(args.db, args.plan, args.backups, args.apply, args.skip_changed)
    else:
        rollback(args.db, args.backup, args.apply, args.skip_changed)


if __name__ == '__main__':
    main()
