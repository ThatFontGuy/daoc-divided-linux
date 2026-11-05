"""Private fishing rod for the modern test client (fishing poles, server FishingCraft.PoleModel).

  plan    : python -B install_fishing_rod.py plan              (builds the mesh, writes an OBJ preview, changes nothing)
  install : python -B install_fishing_rod.py install
  rollback: python -B install_fishing_rod.py rollback <backup-folder>

Run with a Python that has numpy (Blender's bundled python.exe works) and with the launcher, client and server CLOSED.
OFFLINE_DAOC_RUNTIME points at the runtime folder (default: the modern test install).

Client (private additions only; no stock file or row changes):
  items\\offline_fishrod01.nif  byte copy of b_st_quarterstaff01.nif (the stock B_weapons01 wood texture is kept) with
                               only the vertex positions and the bounding sphere changed: a long rod that tapers from a
                               thick handle to a thin tip, butt 19 units behind the hand like the stock spears.
  gamedata objects.csv 4927 and items.csv 3085, cloned from the Quarterstaff rows (442 / 198). The object row takes the
  two-handed spear stance (Combat 3, Left 2, like the Pike 69 and Norse Simple Spear 328), so the rod is held out in front,
  and the stock "fishing pole" bag icon 530. objects.csv 4928 is the same rod in the staff stance (Combat 4, Left 1).
Server: set the craft setting fishing_pole_model to 4927 (or 4928) and restart; every client needs these rows.
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import PIL  # noqa: F401
except ImportError:
    # install_blood_shield imports PIL for its own painting only; the helpers used here never touch it, and Blender's
    # bundled Python (the one with numpy) has no PIL.
    import types
    pil = types.ModuleType("PIL")
    pil.Image = pil.ImageDraw = pil.ImageFont = types.ModuleType("PIL.stub")
    sys.modules["PIL"] = pil
import install_blood_shield as bs  # noqa: E402  (guarded helpers: process check, catalogs, add_row)
import nif4_geom  # noqa: E402
from daoc_catalog import archive  # noqa: E402

RUNTIME = Path(os.environ.get("OFFLINE_DAOC_RUNTIME",
                              r"C:\Users\natex\Desktop\DAoC Offline\Source\artifacts\modern-client-test\runtime"))
bs.ROOT = RUNTIME.parent
bs.CLIENT = RUNTIME / "client-modern" / "app"
bs.DB = RUNTIME / "data" / "opendaoc.sqlite3.db"
ITEMS = bs.CLIENT / "items"
WORK = HERE / "work" / "fishing-rod"

SOURCE_NIF = "b_st_quarterstaff01.nif"
PRIVATE_NIF = "offline_fishrod01.nif"
OBJECT_ID, SOURCE_OBJECT = 4927, 442
STAFF_OBJECT_ID = 4928      # the same rod held in the staff stance, to compare in game
ITEM_ID, SOURCE_ITEM = 3085, 198
LABEL = "Offline Fishing Rod"
SPEAR_STANCE = ("3", "2")   # objects.csv Combat, Left
POLE_ICON = "530"           # the bag icon of the stock "fishing pole" row 580 (which has no mesh)

# The staff is seven 4- or 8-sided rings plus a point at each end. Each stock ring height maps to a new height and
# radius along the rod (units as the stock spears: the hand at 0, the butt behind it).
RINGS = [  # (stock z, new z, new radius)
    (-29.65, -19.0, 0.0),
    (-28.86, -18.5, 1.15),
    (-21.31, -12.0, 1.10),
    (-14.90, 4.0, 0.95),
    (5.29, 30.0, 0.60),
    (24.94, 62.0, 0.38),
    (31.33, 84.0, 0.25),
    (38.89, 104.0, 0.15),
    (39.68, 105.0, 0.0),
]


def reshape(verts):
    out = verts.copy()
    for i, (x, y, z) in enumerate(verts):
        stock_z, new_z, new_r = min(RINGS, key=lambda ring: abs(ring[0] - z))
        bs.require(abs(stock_z - z) < 0.05, f"vertex {i} at z={z:.2f} is not on a known ring")
        r = float(np.hypot(x, y))
        scale = 0.0 if r < 0.05 else new_r / r
        out[i] = (x * scale, y * scale, new_z)
    return out


def build():
    data = (ITEMS / SOURCE_NIF).read_bytes()
    geoms = nif4_geom.load(ITEMS / SOURCE_NIF)
    bs.require(len(geoms) == 1, f"{SOURCE_NIF}: expected one shape, found {len(geoms)}")
    geom = geoms[0]
    count = len(geom.vertices)
    head = geom.offset
    bs.require(struct.unpack_from("<H", data, head)[0] == count, "vertex count not where expected")
    # count, has-vertices flag (1 or 4 bytes), positions, has-normals flag, normals, centre + radius
    for flag_width in (1, 4):
        start = head + 2 + flag_width
        stored = np.frombuffer(data, "<f4", 3 * count, start).reshape(count, 3)
        if np.allclose(stored, geom.vertices, atol=1e-4):
            break
    else:
        raise SystemExit("vertex block not found")
    normals_flag = start + 12 * count
    bounds = normals_flag + flag_width + (12 * count if data[normals_flag] else 0)

    new = reshape(geom.vertices)
    centre = (new.min(0) + new.max(0)) / 2
    radius = float(np.linalg.norm(new - centre, axis=1).max())
    patched = bytearray(data)
    patched[start:start + 12 * count] = new.astype("<f4").tobytes()
    patched[bounds:bounds + 16] = struct.pack("<4f", *centre, radius)
    patched = bytes(patched)

    changed = [i for i in range(len(data)) if data[i] != patched[i]]
    bs.require(all(start <= i < start + 12 * count or bounds <= i < bounds + 16 for i in changed),
               "bytes outside the vertex block and bounding sphere changed")
    check = nif4_geom.load_bytes(patched) if hasattr(nif4_geom, "load_bytes") else None
    if check is not None:
        bs.require(np.allclose(check[0].vertices, new, atol=1e-3), "re-read vertices differ")
    return patched, new, geom


def write_obj(path, verts, geom):
    lines = [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in verts]
    lines += [f"vt {u:.5f} {1 - v:.5f}" for u, v in geom.uvs]
    lines += [f"f {a + 1}/{a + 1} {b + 1}/{b + 1} {c + 1}/{c + 1}" for a, b, c in geom.faces]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def new_rows(objects_csv, items_csv):
    """The rod's catalog rows ({"objects.csv": [spear hold, staff hold], "items.csv": [item]}) for these stock catalogs.
    make_client_patch.py builds the players' client patch from the same rows."""
    obj_rows = {r[0].strip(): r for r in bs.rows_of(objects_csv) if r and r[0].strip().isdigit()}
    item_rows = {r[0].strip(): r for r in bs.rows_of(items_csv) if r and r[0].strip().isdigit()}
    bs.require(str(OBJECT_ID) not in obj_rows and str(ITEM_ID) not in item_rows, f"ID {OBJECT_ID}/{ITEM_ID} already used")
    bs.require(obj_rows[str(SOURCE_OBJECT)][1] == "Quarterstaff", "objects.csv 442 is not the Quarterstaff")
    orow = list(obj_rows[str(SOURCE_OBJECT)])
    orow[0], orow[1], orow[2] = str(OBJECT_ID), LABEL, str(ITEM_ID)
    bs.require(str(STAFF_OBJECT_ID) not in obj_rows, f"ID {STAFF_OBJECT_ID} already used")
    orow[3] = POLE_ICON
    staff = list(orow)
    staff[0], staff[1] = str(STAFF_OBJECT_ID), LABEL + " (staff hold)"
    orow[19], orow[20] = SPEAR_STANCE
    irow = list(item_rows[str(SOURCE_ITEM)])
    irow[0], irow[1], irow[2] = str(ITEM_ID), LABEL, PRIVATE_NIF.rsplit(".", 1)[0]
    return {"objects.csv": [orow, staff], "items.csv": [irow]}


def catalog():
    name, entries, files, tables = bs.catalogs()
    added = new_rows(files["objects.csv"], files["items.csv"])
    (orow, staff), (irow,) = added["objects.csv"], added["items.csv"]
    objects = bs.add_row(bs.add_row(files["objects.csv"], orow), staff)
    updates = {"objects.csv": objects, "items.csv": bs.add_row(files["items.csv"], irow)}
    blob = archive.write(name, [archive.Entry(e.name, updates.get(e.name.lower(), e.data), e.timestamp, e.flags)
                                for e in entries])
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    bs.require([e.name for e in decoded] == [e.name for e in entries], "Archive entry order changed")
    for old, new in zip(entries, decoded):
        bs.require((old.timestamp, old.flags) == (new.timestamp, new.flags), "Archive metadata changed")
        key = old.name.lower()
        if key not in updates:
            bs.require(old.data == new.data, f"Unrelated archive entry changed: {old.name}")
        else:
            rows = bs.rows_of(new.data)
            bs.require([r for r in rows if r not in added[key]] == bs.rows_of(old.data), f"Stock {key} row changed")
            bs.require(all(r in rows for r in added[key]), f"New {key} rows missing")
            text = new.data.decode("latin-1").replace("\r\n", "\n").strip("\n")
            bs.require("\n\n" not in text, f"{key} has a blank line")
    return blob, added


def plan():
    nif, verts, geom = build()
    WORK.mkdir(parents=True, exist_ok=True)
    write_obj(WORK / "fishing_rod.obj", verts, geom)
    write_obj(WORK / "quarterstaff.obj", geom.vertices, geom)
    _, added = catalog()
    for key, rows in added.items():
        for r in rows:
            print(key, r[:27] if key == "objects.csv" else r[:6])
    lo, hi = verts.min(0), verts.max(0)
    print(PRIVATE_NIF, len(nif), "bytes; rod from z", round(float(lo[2]), 1), "to", round(float(hi[2]), 1))
    print("Preview OBJs in", WORK)


def install():
    bs.stopped()
    game = bs.CLIENT / "gamedata.mpk"
    blob, _ = catalog()
    nif, _, _ = build()
    bs.require(not (ITEMS / PRIVATE_NIF).exists(), f"{PRIVATE_NIF} already exists")
    backup = HERE / "install-backups" / ("fishing-rod-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(game, backup / "gamedata.mpk")
    manifest = {"runtime": str(RUNTIME), "created": datetime.now().astimezone().isoformat(),
                "before_gamedata_sha256": bs.file_sha(game), "after_gamedata_sha256": bs.sha(blob),
                "private_files": {PRIVATE_NIF: bs.sha(nif)}}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bs.atomic_write(ITEMS / PRIVATE_NIF, nif)
    bs.atomic_write(game, blob)
    bs.require(bs.file_sha(game) == manifest["after_gamedata_sha256"], "Installed catalog differs")
    bs.require(bs.file_sha(ITEMS / PRIVATE_NIF) == manifest["private_files"][PRIVATE_NIF], "Installed rod differs")
    print("Installed", PRIVATE_NIF, f"objects.csv {OBJECT_ID} and {STAFF_OBJECT_ID}, items.csv {ITEM_ID}")
    print(f'Rollback:\n  python -B "{Path(__file__).resolve()}" rollback "{backup}"')


def rollback(folder: Path):
    bs.stopped()
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    game = bs.CLIENT / "gamedata.mpk"
    bs.require(bs.file_sha(game) in (m["before_gamedata_sha256"], m["after_gamedata_sha256"]),
               "Later catalog changes detected; refuse to overwrite them")
    for name, digest in m["private_files"].items():
        path = ITEMS / name
        bs.require(not path.exists() or bs.file_sha(path) == digest, f"{name} changed since install")
    bs.atomic_write(game, (folder / "gamedata.mpk").read_bytes())
    for name in m["private_files"]:
        if (ITEMS / name).exists():
            (ITEMS / name).unlink()
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        plan()
    elif len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    else:
        print(__doc__)
