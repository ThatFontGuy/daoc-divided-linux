"""World audit against the server's own navigation meshes (read-only): what NPCs, travel routes and arrival points
stand on, so placement problems can be found after world or navmesh changes.

Each spot is compared with the navmesh of its zone (<runtime>/server/navmesh/zoneNNN.nav):
    ok           on a navmesh polygon within 64 units of its height
    floating     the nearest floor below is 64-1000 units down
    underground  the nearest floor is 64-1000 units above it
    no floor     no navmesh within 1000 units up or down (water, cliffs, unmeshed roofs)
    no navmesh   the zone has no navmesh file
Flying, swimming and statue NPCs are reported apart ("ignored").
Travel routes: every leg is also walked every 32 units; a leg that leaves the navmesh or climbs more than 48 units
between samples is "blocked" (a horse would cut through geometry or fly).
"""
from __future__ import annotations

import collections
import math
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEAR, FAR = 64, 1000
FLYING, SWIMMING, STATUE = 0x20, 0x100, 0x80


def _navcomp():
    for root in (HERE.parents[1] / 'server/tools/navmesh_splice', HERE / 'navmesh_splice'):
        if (root / 'navcomp.py').is_file():
            sys.path.insert(0, str(root))
            from navcomp import NavAreas
            return NavAreas
    raise ValueError('The audit needs source/server/tools/navmesh_splice (run it from the Offline DAoC source tree)')


class World:
    """Zones from the database and their navmeshes, loaded on first use."""

    def __init__(self, con, navmesh: Path):
        self.NavAreas = _navcomp()
        self.navmesh = navmesh
        self.zones = [(r['ZoneID'], r['RegionID'], r['OffsetX'] * 8192, r['OffsetY'] * 8192,
                       r['Width'] * 8192, r['Height'] * 8192)
                      for r in con.execute('SELECT ZoneID, RegionID, OffsetX, OffsetY, Width, Height FROM Zones')]
        self.meshes = {}

    def zone(self, region, x, y):
        return next((z for z, r, ox, oy, w, h in self.zones if r == region and ox <= x < ox + w and oy <= y < oy + h), None)

    def mesh(self, zone):
        if zone not in self.meshes:
            path = self.navmesh / f'zone{zone:03d}.nav'
            self.meshes[zone] = self.NavAreas(str(path)) if path.is_file() else None
        return self.meshes[zone]

    def floor(self, region, x, y, z, tolerance):
        """Height of the navmesh polygon nearest z within tolerance, or None; 'no navmesh' when the zone has none."""
        zone = self.zone(region, x, y)
        mesh = self.mesh(zone) if zone is not None else None
        if mesh is None:
            return 'no navmesh'
        poly = mesh.locate(x, y, z, tolerance=tolerance)
        return None if poly is None else mesh.height(poly, x, y)

    def classify(self, region, x, y, z):
        near = self.floor(region, x, y, z, NEAR)
        if near == 'no navmesh':
            return near, None
        if near is not None:
            return 'ok', near
        wide = self.floor(region, x, y, z, FAR)
        if wide is None:
            return 'no floor', None
        return ('floating' if wide < z else 'underground'), wide

    def leg_clear(self, region, a, b):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 32))
        z = a[2]
        for i in range(1, n + 1):
            x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
            h = self.floor(region, x, y, z, 96)
            if h == 'no navmesh':
                return True
            if h is None or abs(h - z) > 48:
                return False
            z = h
        return True


def run(db: Path, navmesh: Path, regions=None, zones=None, routes=True, progress=print):
    """{'summary': {...}, 'findings': [...]} for the world database `db`."""
    con = sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    with closing(con):
        world = World(con, navmesh)
        wanted = lambda region, x, y: (not regions or region in regions) and \
            (not zones or world.zone(region, x, y) in zones)
        findings, summary = [], collections.Counter()

        def check(kind, key, label, region, x, y, z, ignore=''):
            if not wanted(region, x, y):
                return
            status, floor = world.classify(region, x, y, z)
            zone = world.zone(region, x, y)
            if status != 'ok':
                status = f'ignored ({ignore}, {status})' if ignore and status != 'no navmesh' else status
            summary[(kind, status)] += 1
            if status != 'ok':
                findings.append({'kind': kind, 'status': status, 'key': key, 'label': label, 'region': region,
                                 'zone': zone, 'x': x, 'y': y, 'z': z,
                                 'floor': None if floor is None else round(floor)})

        n = 0
        for r in con.execute('SELECT Mob_ID, Name, Region, X, Y, Z, Flags FROM Mob'):
            flags = r['Flags'] or 0
            ignore = 'flying' if flags & FLYING else 'swimming' if flags & SWIMMING else 'statue' if flags & STATUE else ''
            check('npc', r['Mob_ID'], r['Name'], r['Region'], r['X'], r['Y'], r['Z'], ignore)
            n += 1
            if n % 5000 == 0:
                progress(f'{n} NPCs checked')
        for table, key, region, x, y, z, label in (
                ('BindPoint', 'BindPoint_ID', 'Region', 'X', 'Y', 'Z', "'bind point'"),
                ('Teleport', 'Teleport_ID', 'RegionID', 'X', 'Y', 'Z', 'TeleportID'),
                ('ZonePoint', 'ZonePoint_ID', 'TargetRegion', 'TargetX', 'TargetY', 'TargetZ', 'Id'),
                ('StartupLocation', 'StartupLocation_ID', 'Region', 'XPos', 'YPos', 'ZPos', "'start location'")):
            try:
                rows = con.execute(f'SELECT {key}, {label}, {region}, {x}, {y}, {z} FROM {table}').fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                check(table.lower(), row[0], str(row[1]), row[2], row[3], row[4], row[5])
        progress('arrival points checked')
        if routes:
            sold = {r[0].lower() for r in con.execute('SELECT DISTINCT ItemTemplateID FROM MerchantItem')}
            points = collections.defaultdict(list)
            for r in con.execute('SELECT PathID, Step, X, Y, Z FROM PathPoints ORDER BY PathID, Step'):
                points[r['PathID']].append((r['X'], r['Y'], r['Z']))
            region_rows = {r[0]: r[1] for r in con.execute('SELECT PathID, RegionID FROM Path')}
            for pid, pts in points.items():
                # Flying (griffon, dragonfly) and boat routes follow no floor.
                if pid.lower().startswith(('griffon', 'dragonfly', 'bt_', 'boat')):
                    continue
                # Path rows often carry region 0: take the region whose navmesh holds the first point.
                region = region_rows.get(pid) or next(
                    (r for r in sorted({z[1] for z in world.zones})
                     if world.zone(r, *pts[0][:2]) is not None and
                     isinstance(world.floor(r, *pts[0], 200), float)), None)
                if region is None or not wanted(region, *pts[0][:2]):
                    continue
                kind = 'stable route' if pid.lower() in sold else 'path'
                for i, p in enumerate(pts):
                    status, floor = world.classify(region, *p)
                    summary[(kind + ' point', status)] += 1
                    if status not in ('ok', 'no navmesh'):
                        findings.append({'kind': kind + ' point', 'status': status, 'key': pid, 'label': f'step {i + 1}',
                                         'region': region, 'zone': world.zone(region, p[0], p[1]),
                                         'x': p[0], 'y': p[1], 'z': p[2],
                                         'floor': None if floor is None else round(floor)})
                if kind == 'stable route':
                    for i, (a, b) in enumerate(zip(pts, pts[1:])):
                        ok = world.leg_clear(region, a, b)
                        summary[(kind + ' leg', 'ok' if ok else 'blocked')] += 1
                        if not ok:
                            findings.append({'kind': 'stable route leg', 'status': 'blocked', 'key': pid,
                                             'label': f'leg {i + 1}', 'region': region,
                                             'zone': world.zone(region, a[0], a[1]), 'x': a[0], 'y': a[1], 'z': a[2],
                                             'floor': None})
            progress('travel routes checked')
        missing = sorted({world.zone(r['Region'], r['X'], r['Y']) for r in con.execute('SELECT Region, X, Y FROM Mob')}
                         - {None} - {z for z in world.meshes if world.meshes[z] is not None})
        return {'summary': {f'{k} / {s}': v for (k, s), v in sorted(summary.items())},
                'zones without navmesh': [z for z in missing if world.mesh(z) is None],
                'findings': findings}
