"""Inspect and install client-only Classic-side Shrouded Isles portal visuals.

This deliberately does not touch server ZonePoint data or bot navigation.
"""

import argparse
import csv
import datetime
import hashlib
import io
import os
import pathlib
import shutil
import sqlite3
import struct
import zlib
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[2]
ZONES = ROOT / "runtime" / "client-opendaoc" / "app" / "zones"
DATABASE = ROOT / "runtime" / "data" / "opendaoc.sqlite3.db"
NAVMESH = ROOT / "runtime" / "server" / "navmesh"

# Source trigger coordinates are global, while the fixture coordinates are
# local to the classic zone (using its region_offset * 8192 tile origin).
SITES = (
    # classic zone, SI zone, ZonePoint id, classic global (x,y,z), local (x,y),
    # SI realm teleporter model, existing SI-side NIF id, visual facing.
    # Facings approximate the approach from Cotswold's sign, Mularn's named
    # fixture, and Mag Mell's named fixture, respectively. They are cosmetic;
    # the transfer triggers and bot route coordinates are left untouched.
    (0, 51, 153, (564976, 509200, 2811), (16112, 25872), "BAvTeleporter.nif", 475, 315),
    (100, 151, 165, (808830, 725039, 4882), (55166, 53295), "NAegTeleport.nif", 424, 247),
    (200, 181, 167, (348198, 492819, 5240), (28710, 9491), "hibteleport.nif", 417, 254),
)

# Classic-side client crossing lines, perpendicular to approach from the
# nearest named town fixture. Each spans 180 map units, crosses at the fixed
# ZonePoint source coordinate, and accepts the immediate local floor height.
# The reverse row is required because the stock SI return zones define both
# crossing directions. These are CLIENT events, not edits to bot routing.
TRIGGERS = {
    0: ((16177, 25935), (16047, 25809), (2750, 3020), 153, "SIClassicAlb"),
    100: ((55131, 53378), (55201, 53212), (4810, 5090), 165, "SIClassicMid"),
    200: ((28685, 9577), (28735, 9405), (5170, 5450), 167, "SIClassicHib"),
}


@dataclass
class Entry:
    name: str
    content: bytes
    timestamp: int
    flags: int
    memory_offset: int


def unpack_mpk(data):
    if data[:5] != b"MPAK\x02" or len(data) < 21:
        raise ValueError("Unexpected MPK header")
    crc, directory_size, name_size, count = struct.unpack(
        "<4I", bytes(value ^ index for index, value in enumerate(data[5:21]))
    )
    if not (0 < count < 10000 and 21 + name_size + directory_size <= len(data)):
        raise ValueError("Invalid MPK sizes")
    archive_name = zlib.decompress(data[21:21 + name_size])
    compressed_directory = data[21 + name_size:21 + name_size + directory_size]
    if zlib.crc32(compressed_directory) & 0xFFFFFFFF != crc:
        raise ValueError("MPK directory checksum mismatch")
    directory = zlib.decompress(compressed_directory)
    if len(directory) != count * 284:
        raise ValueError("MPK directory entry size mismatch")
    payload = data[21 + name_size + directory_size:]
    entries = []
    names = set()
    for index in range(count):
        row = directory[index * 284:(index + 1) * 284]
        name = row[:256].split(b"\0", 1)[0].decode("latin1")
        timestamp, flags, memory, size, offset, compressed_size, file_crc = struct.unpack(
            "<7I", row[256:]
        )
        if not name or name.lower() in names or offset + compressed_size > len(payload):
            raise ValueError("Invalid MPK file directory")
        names.add(name.lower())
        compressed = payload[offset:offset + compressed_size]
        if zlib.crc32(compressed) & 0xFFFFFFFF != file_crc:
            raise ValueError(f"{name}: compressed checksum mismatch")
        content = zlib.decompress(compressed)
        if len(content) != size:
            raise ValueError(f"{name}: expanded length mismatch")
        entries.append(Entry(name, content, timestamp, flags, memory))
    return archive_name, entries


def pack_mpk(archive_name, entries):
    directory = bytearray()
    payload = bytearray()
    memory = 0
    for entry in entries:
        filename = entry.name.encode("latin1")
        if not 0 < len(filename) < 256:
            raise ValueError("Invalid filename")
        compressed = zlib.compress(entry.content, 9)
        directory += filename.ljust(256, b"\0")
        directory += struct.pack(
            "<7I", entry.timestamp, entry.flags, memory, len(entry.content),
            len(payload), len(compressed), zlib.crc32(compressed) & 0xFFFFFFFF,
        )
        memory += len(entry.content)
        payload += compressed
    names = zlib.compress(archive_name, 9)
    compressed_directory = zlib.compress(directory, 9)
    header = struct.pack(
        "<4I", zlib.crc32(compressed_directory) & 0xFFFFFFFF,
        len(compressed_directory), len(names), len(entries),
    )
    result = (b"MPAK\x02" + bytes(value ^ index for index, value in enumerate(header))
              + names + compressed_directory + payload)
    recovered_name, recovered_entries = unpack_mpk(result)
    if recovered_name != archive_name or [(e.name, e.content) for e in recovered_entries] != [
        (e.name, e.content) for e in entries
    ]:
        raise ValueError("MPK round-trip mismatch")
    return result


def csv_entries(zone):
    path = ZONES / f"zone{zone:03d}" / f"csv{zone:03d}.mpk"
    name, entries = unpack_mpk(path.read_bytes())
    return path, name, entries


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zonepoint_snapshot():
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True)
    try:
        return tuple(connection.execute(
            "SELECT * FROM ZonePoint WHERE Id IN (153,165,167) ORDER BY Id"
        ))
    finally:
        connection.close()


def navmesh_snapshot():
    return {path.name: hash_file(path) for path in sorted(NAVMESH.glob("*.nav"))}


def csv_rows(entry):
    return list(csv.reader(io.StringIO(entry.content.decode("latin1"))))


def append_row(entry, row):
    if not entry.content.endswith(b"\r\n"):
        raise ValueError(f"{entry.name} does not end in CRLF")
    return Entry(entry.name, entry.content + ",".join(row).encode("latin1") + b"\r\n",
                 entry.timestamp, entry.flags, entry.memory_offset)


def portal_rows(classic_zone, si_zone, model, source_nif_id, local_xy, facing):
    _, _, classic_entries = csv_entries(classic_zone)
    _, _, si_entries = csv_entries(si_zone)
    source_nifs = next(entry for entry in si_entries if entry.name.lower() == "nifs.csv")
    source_fixtures = next(entry for entry in si_entries if entry.name.lower() == "fixtures.csv")
    source_nif = next((row for row in csv_rows(source_nifs)[2:]
                       if row and row[0] == str(source_nif_id) and row[2].lower() == model.lower()), None)
    if source_nif is None or len(source_nif) < 9:
        raise ValueError(f"SI-side NIF mapping missing: {model}")
    source_fixture = next((row for row in csv_rows(source_fixtures)[2:]
                           if len(row) >= 15 and row[1] == str(source_nif_id)
                           and abs(int(row[3]) - local_xy[0]) < 99999), None)
    if source_fixture is None:
        raise ValueError(f"SI-side fixture missing: {model}")
    # The original NPKs already ship in the shared Nifs folder; no asset copy
    # is needed. Validate that the model package is actually loadable.
    package = ZONES / "Nifs" / (pathlib.Path(model).stem + ".npk")
    _, assets = unpack_mpk(package.read_bytes())
    if not any(asset.name.lower() == model.lower() for asset in assets):
        raise ValueError(f"Model asset missing inside {package}")

    fixture_index = next(i for i, entry in enumerate(classic_entries)
                         if entry.name.lower() == "fixtures.csv")
    nif_index = next(i for i, entry in enumerate(classic_entries)
                     if entry.name.lower() == "nifs.csv")
    fixtures = csv_rows(classic_entries[fixture_index])
    nifs = csv_rows(classic_entries[nif_index])
    if any("SI Portal Visual" in row for row in fixtures):
        raise ValueError(f"Zone {classic_zone:03d} already has a managed SI portal visual")
    next_fixture_id = max(int(row[0]) for row in fixtures[2:] if row and row[0].isdigit()) + 1
    next_unique_id = max(int(row[14]) for row in fixtures[2:]
                         if len(row) > 14 and row[14].isdigit()) + 1
    next_nif_id = max(int(row[0]) for row in nifs[2:] if row and row[0].isdigit()) + 1
    nif_row = source_nif.copy()
    nif_row[0] = str(next_nif_id)
    nif_row[1] = f"SI Portal Visual {classic_zone:03d}"
    nif_row[7] = "0"  # NIF collision disabled; gamebots keep walking through.
    nif_row[8] = "1"  # Follow the local terrain, as the SI-side fixture does.
    fixture_row = source_fixture.copy()
    fixture_row[0] = str(next_fixture_id)
    fixture_row[1] = str(next_nif_id)
    fixture_row[2] = f"SI Portal Visual {classic_zone:03d}"
    fixture_row[3], fixture_row[4], fixture_row[5] = map(str, (*local_xy, 0))
    fixture_row[6] = str(facing)
    fixture_row[7] = "100"
    fixture_row[8] = "0"  # Fixture collision disabled too.
    fixture_row[11] = "1"
    fixture_row[14] = str(next_unique_id)
    classic_entries[fixture_index] = append_row(classic_entries[fixture_index], fixture_row)
    classic_entries[nif_index] = append_row(classic_entries[nif_index], nif_row)
    return classic_entries, nif_row, fixture_row


def install():
    before_zonepoints = zonepoint_snapshot()
    before_navmesh = navmesh_snapshot()
    if len(before_zonepoints) != 3 or not before_navmesh:
        raise ValueError("ZonePoint or navmesh snapshot incomplete")
    prepared = []
    for zone, si_zone, point_id, expected_global, local_xy, model, source_id, facing in SITES:
        record = next(row for row in before_zonepoints if row[0] == point_id)
        if tuple(record[6:9]) != expected_global or record[9] != (1, 100, 200)[(0, 100, 200).index(zone)]:
            raise ValueError(f"ZonePoint {point_id} no longer matches expected classic entrance")
        path, name, original = csv_entries(zone)
        updated, nif_row, fixture_row = portal_rows(zone, si_zone, model, source_id, local_xy, facing)
        if len(updated) != len(original) or any(
            new.content != old.content for new, old in zip(updated, original)
            if new.name.lower() not in ("nifs.csv", "fixtures.csv")
        ):
            raise ValueError(f"Zone {zone:03d}: unrelated archive entry changed")
        packed = pack_mpk(name, updated)
        recovered_name, recovered_entries = unpack_mpk(packed)
        if recovered_name != name or [(e.name, e.content) for e in recovered_entries] != [
            (e.name, e.content) for e in updated
        ]:
            raise ValueError(f"Zone {zone:03d}: final archive verification failed")
        prepared.append((path, packed, nif_row, fixture_row))

    backup = ROOT / "runtime" / "deployment-backups" / (
        "si-classic-portals-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    backup.mkdir(parents=True, exist_ok=False)
    for path, _, _, _ in prepared:
        shutil.copy2(path, backup / path.name)
    print(f"Recoverable original archives: {backup}")
    for path, packed, nif_row, fixture_row in prepared:
        temp = path.with_name(path.name + ".si-portal-tmp")
        if temp.exists():
            raise ValueError(f"Stale temporary archive: {temp}")
        temp.write_bytes(packed)
        if hash_file(temp) != hashlib.sha256(packed).hexdigest():
            raise ValueError(f"Could not verify staged archive {temp}")
        os.replace(temp, path)
        print(f"Installed {path}: NIF={nif_row[:9]}, fixture={fixture_row[:15]}")

    after_zonepoints = zonepoint_snapshot()
    after_navmesh = navmesh_snapshot()
    if before_zonepoints != after_zonepoints or before_navmesh != after_navmesh:
        raise ValueError("ZonePoint or navmesh changed during visual-only installation")
    for path, _, _, _ in prepared:
        unpack_mpk(path.read_bytes())
    print(f"PASS: ZonePoints unchanged; all {len(after_navmesh)} navmesh hashes unchanged;"
          " three new client CSV archives decompress and validate")


def planned_triggers():
    plan = []
    for zone, (left, right, heights, zonepoint_id, label) in TRIGGERS.items():
        path, name, entries = csv_entries(zone)
        jump_index = next(index for index, entry in enumerate(entries)
                          if entry.name.lower() == "zonejump.csv")
        old = entries[jump_index]
        rows = csv_rows(old)
        if any(len(row) > 8 and row[8] == str(zonepoint_id) for row in rows):
            raise ValueError(f"Zone {zone:03d} already has a trigger for {zonepoint_id}")
        existing_ids = {int(row[0]) for row in rows if row and row[0].isdigit()}
        next_id = max(existing_ids) + 1
        if next_id in existing_ids or next_id + 1 in existing_ids:
            raise ValueError(f"Zone {zone:03d} zonejump ID collision")
        if tuple((left[index] + right[index]) / 2 for index in (0, 1)) != {
            0: (16112, 25872), 100: (55166, 53295), 200: (28710, 9491)
        }[zone]:
            raise ValueError(f"Zone {zone:03d} trigger not centered on portal")
        if len(rows) > 0 and not old.content.endswith(b"\r\n"):
            raise ValueError(f"Zone {zone:03d} zonejump lacks final CRLF")
        pair = [
            [str(next_id + index), label, str(a[0]), str(a[1]), str(b[0]), str(b[1]),
             str(heights[0]), str(heights[1]), str(zonepoint_id), "", ""]
            for index, (a, b) in enumerate(((left, right), (right, left)))
        ]
        updated = old
        for row in pair:
            updated = append_row(updated, row)
        updated_entries = entries.copy()
        updated_entries[jump_index] = updated
        if any(before.content != after.content for before, after in zip(entries, updated_entries)
               if before.name.lower() != "zonejump.csv"):
            raise ValueError(f"Zone {zone:03d} unrelated entry changed")
        plan.append((path, name, entries, updated_entries, pair))
    return plan


def show_triggers():
    for path, _, _, _, pair in planned_triggers():
        print(path)
        for row in pair:
            print("  " + ",".join(row))


def install_triggers():
    before_zonepoints = zonepoint_snapshot()
    before_navmesh = navmesh_snapshot()
    if len(before_zonepoints) != 3 or not before_navmesh:
        raise ValueError("ZonePoint or navmesh snapshot incomplete")
    point_by_id = {row[0]: row for row in before_zonepoints}
    for zone, (_, _, heights, point_id, _) in TRIGGERS.items():
        point = point_by_id[point_id]
        if point[9] != {0: 1, 100: 100, 200: 200}[zone] or not heights[0] < point[8] < heights[1]:
            raise ValueError(f"ZonePoint {point_id} does not match planned trigger")
    plan = planned_triggers()
    prepared = []
    for path, name, original, updated, pair in plan:
        binary = pack_mpk(name, updated)
        recovered_name, recovered_entries = unpack_mpk(binary)
        if recovered_name != name or [(e.name, e.content) for e in recovered_entries] != [
            (e.name, e.content) for e in updated
        ]:
            raise ValueError(f"Failed archive round-trip: {path}")
        before_jumps = next(e.content for e in original if e.name.lower() == "zonejump.csv")
        after_jumps = next(e.content for e in updated if e.name.lower() == "zonejump.csv")
        appended = after_jumps[len(before_jumps):]
        if not after_jumps.startswith(before_jumps) or appended != b"".join(
            ",".join(row).encode("latin1") + b"\r\n" for row in pair
        ):
            raise ValueError(f"Unexpected zonejump modification: {path}")
        prepared.append((path, binary, pair))

    backup = ROOT / "runtime" / "deployment-backups" / (
        "si-classic-zonejumps-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    backup.mkdir(parents=True, exist_ok=False)
    for path, _, _ in prepared:
        shutil.copy2(path, backup / path.name)
    print(f"Recoverable pre-trigger archives: {backup}")
    for path, binary, pair in prepared:
        temporary = path.with_name(path.name + ".si-zonejump-tmp")
        if temporary.exists():
            raise ValueError(f"Stale temporary archive: {temporary}")
        temporary.write_bytes(binary)
        if hash_file(temporary) != hashlib.sha256(binary).hexdigest():
            raise ValueError(f"Staged archive could not be verified: {temporary}")
        os.replace(temporary, path)
        print(f"Installed {path.name}: {pair[0][0]}/{pair[1][0]} -> ZonePoint {pair[0][8]}")
    if zonepoint_snapshot() != before_zonepoints or navmesh_snapshot() != before_navmesh:
        raise ValueError("Server ZonePoint or bot navmesh changed during client trigger install")
    for path, _, _ in prepared:
        unpack_mpk(path.read_bytes())
    print(f"PASS: three bidirectional client triggers; three ZonePoints and"
          f" {len(before_navmesh)} navmesh files unchanged")


def inspect():
    local_sites = {
        0: (16112, 25872),
        100: (55166, 53295),
        200: (28710, 9491),
        51: (34298, 51138),
        151: (48446, 44673),
        181: (30587, 46694),
    }
    for zone in (0, 100, 200, 51, 151, 181):
        path, name, entries = csv_entries(zone)
        print(f"ZONE {zone:03d} {path} entries={[(e.name,len(e.content),e.memory_offset) for e in entries]}")
        for entry in entries:
            if entry.name.lower() not in ("nifs.csv", "fixtures.csv", "zonejump.csv"):
                continue
            lines = entry.content.decode("latin1").splitlines()
            print(f"  {entry.name} header: {lines[:3]}")
            for line in lines:
                if "portal" in line.lower():
                    print(f"    {line}")
            if entry.name.lower() == "fixtures.csv":
                rows = list(csv.reader(io.StringIO(entry.content.decode("latin1"))))[2:]
                cx, cy = local_sites[zone]
                nearby = sorted(
                    ((int(row[3])-cx)**2 + (int(row[4])-cy)**2, row)
                    for row in rows if len(row) >= 13 and row[3].isdigit() and row[4].isdigit()
                )[:15]
                print(f"    Near target {cx},{cy}:")
                for dist2, row in nearby:
                    print(f"      {dist2**0.5:.0f} {row}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("inspect", "install", "plan-triggers", "install-triggers"))
    args = parser.parse_args()
    if args.command == "inspect":
        inspect()
    elif args.command == "install":
        install()
    elif args.command == "plan-triggers":
        show_triggers()
    elif args.command == "install-triggers":
        install_triggers()
