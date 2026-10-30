"""Private themed weapons for the Necroservant (Necromancer level 20 pet) and the Zombie Guardian.

  install : python -B install_pet_weapons.py install
  rollback: python -B install_pet_weapons.py rollback <backup-folder>

Client (CLAUDE VERSION only, private additions; no stock file or row changes):
  items\\slu_necro_hammer.nif       byte copy of bonedancerhammer_1h.nif  -> SluNecroHammer1a.dds
  items\\slu_necro_graveshield.nif  byte copy of M_Shield_Grave.NIF       -> SluNShield1.tga/.dds
  items\\slu_guard_mace.nif         byte copy of b_cr_flangedmace01.nif   -> SluGMace01a.tga/.dds
  items\\slu_guard_tower.nif        byte copy of Sh_TowerA.NIF            -> sluGTwr01a.tga/.dds
  gamedata objects.csv 4822-4825 and items.csv 2899-2902 (cloned rows; the
  shields use their own NIF texture: Strip Textures 0 and Apply Texture 0,
  like the stock Dragonsworn/DragonSlayer/Pict emblem shields; emblem kept)
Server DB: NPCEquipment 'sluagh_zombie_guardian_mace_shield' (only the zombie
  guardian uses it) slot 10 Model 14 -> 4824, slot 11 Model 79 -> 4825.
The Necroservant models are constants in NecromancerPetAppearance.cs (server build).
Run with the launcher, client and server CLOSED.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install_blood_shield as bs  # noqa: E402  (guarded helpers: process check, catalogs, add_row)
from daoc_catalog import archive  # noqa: E402
from install_pet_art import encode_dds  # noqa: E402

CLIENT, DB = bs.CLIENT, bs.DB
ITEMS = CLIENT / "items"
WORK = HERE / "work" / "weapons"
EQUIPMENT_TEMPLATE = "sluagh_zombie_guardian_mace_shield"

# (object id, source object, item id, source item, name, source NIF, private NIF,
#  (old texture, new texture), painted PNG, reference DDS for header, write TGA?, is shield)
WEAPONS = [
    (4822, 3466, 2899, 1823, "Sluagh Necroservant Hammer", "bonedancerhammer_1h.nif", "slu_necro_hammer.nif",
     (b"BoneDancerHammer.dds", b"SluNecroHammer1a.dds"), "necro_hammer_next.png", "bonedancerhammer.dds", False, False),
    (4823, 1128, 2900, 476, "Sluagh Necroservant Grave Shield", "M_Shield_Grave.NIF", "slu_necro_graveshield.nif",
     (b"Shield_Wood.tga", b"SluNShield1.tga"), "necro_shield_next.png", "shield_wood.dds", True, True),
    (4824, 14, 2901, 175, "Sluagh Guardian Mace", "b_cr_flangedmace01.nif", "slu_guard_mace.nif",
     (b"B_weapons01.tga", b"SluGMace01a.tga"), "guardian_mace_next.png", "B_weapons01.dds", True, False),
    (4825, 79, 2902, 31, "Sluagh Guardian Tower Shield", "Sh_TowerA.NIF", "slu_guard_tower.nif",
     (b"sh_metal01.tga", b"sluGTwr01a.tga"), "guardian_shield_next.png", "bonedancerhammer.dds", True, True),
]
EQUIPMENT = {10: (14, 4824), 11: (79, 4825)}


def private_nif(source, old, new):
    data = (ITEMS / source).read_bytes()
    bs.require(len(old) == len(new), f"rename length differs: {old}")
    bs.require(data.count(old) == 1, f"{source}: expected exactly one {old!r}")
    patched = data.replace(old, new)
    bs.require(patched.replace(new, old) == data, f"{source}: rename is not reversible")
    return patched


def textures(weapon):
    *_, (old, new), png, reference, write_tga, _ = weapon
    art = Image.open(WORK / png).convert("RGB")
    stem = new.decode().rsplit(".", 1)[0]
    files = {f"{stem}.dds": encode_dds(art, (ITEMS / reference).read_bytes())}
    if write_tga:
        import io
        size = (256, 256) if stem == "SluGMace01a" else art.size   # stock b_weapons01.tga is 256x256
        out = io.BytesIO()
        art.resize(size, Image.Resampling.LANCZOS).save(out, format="TGA")
        files[f"{stem}.tga"] = out.getvalue()
    return files


def catalog():
    name, entries, files, tables = bs.catalogs()
    obj_rows = {r[0].strip(): r for r in bs.rows_of(files["objects.csv"]) if r and r[0].strip().isdigit()}
    item_rows = {r[0].strip(): r for r in bs.rows_of(files["items.csv"]) if r and r[0].strip().isdigit()}
    objects, items = files["objects.csv"], files["items.csv"]
    added = {"objects.csv": [], "items.csv": []}
    for oid, src_obj, iid, src_item, label, _, nif, _, _, _, _, shield in WEAPONS:
        bs.require(str(oid) not in obj_rows and str(iid) not in item_rows, f"ID {oid}/{iid} already used")
        orow = list(obj_rows[str(src_obj)])
        orow[0], orow[1], orow[2] = str(oid), label, str(iid)
        if shield:
            orow[22] = "0"          # no pskins override: use the private NIF texture
        irow = list(item_rows[str(src_item)])
        irow[0], irow[1], irow[2] = str(iid), label, nif.rsplit(".", 1)[0]
        if shield:
            irow[3] = "0"           # do not strip the NIF's own textures
        objects, items = bs.add_row(objects, orow), bs.add_row(items, irow)
        added["objects.csv"].append(orow)
        added["items.csv"].append(irow)
    updates = {"objects.csv": objects, "items.csv": items}
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
    return blob, added


def install():
    bs.stopped()
    game = CLIENT / "gamedata.mpk"
    blob, added = catalog()
    private = {}
    for weapon in WEAPONS:
        private[weapon[6]] = private_nif(weapon[5], *weapon[7])
        private.update(textures(weapon))
    existing = {p.name.lower() for p in ITEMS.rglob("*")}
    bs.require(not any(n.lower() in existing for n in private), "A private item file already exists")
    with bs.read_db() as con:
        rows = {r["Slot"]: r["Model"] for r in con.execute(
            "SELECT Slot, Model FROM NPCEquipment WHERE TemplateID=?", (EQUIPMENT_TEMPLATE,))}
        users = con.execute("SELECT COUNT(*) FROM NpcTemplate WHERE EquipmentTemplateID=?", (EQUIPMENT_TEMPLATE,)).fetchone()[0]
    bs.require(rows == {slot: old for slot, (old, _) in EQUIPMENT.items()}, f"Unexpected guardian equipment {rows}")
    bs.require(users == 1, "Guardian equipment template is shared; re-review")

    backup = HERE / "install-backups" / ("pet-weapons-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(game, backup / "gamedata.mpk")
    with bs.db_session(DB) as con, bs.db_session(backup / "opendaoc.sqlite3.db") as destination:
        con.backup(destination)
        bs.require(destination.execute("PRAGMA quick_check").fetchone()[0] == "ok", "DB backup invalid")
    manifest = {"root": str(bs.ROOT), "created": datetime.now().astimezone().isoformat(),
                "before_gamedata_sha256": bs.file_sha(game), "after_gamedata_sha256": bs.sha(blob),
                "private_files": {n: bs.sha(d) for n, d in private.items()},
                "equipment": {str(s): list(v) for s, v in EQUIPMENT.items()}}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    for name, data in private.items():
        bs.atomic_write(ITEMS / name, data)
    bs.atomic_write(game, blob)
    with bs.db_session(DB) as con:
        for slot, (old, new) in EQUIPMENT.items():
            con.execute("UPDATE NPCEquipment SET Model=? WHERE TemplateID=? AND Slot=? AND Model=?",
                        (new, EQUIPMENT_TEMPLATE, slot, old))
        after = {r[0]: r[1] for r in con.execute("SELECT Slot, Model FROM NPCEquipment WHERE TemplateID=?",
                                                 (EQUIPMENT_TEMPLATE,))}
        bs.require(after == {slot: new for slot, (_, new) in EQUIPMENT.items()}, "Guardian equipment update failed")
        bs.require(con.execute("PRAGMA quick_check").fetchone()[0] == "ok", "DB quick_check failed")
    bs.require(bs.file_sha(game) == manifest["after_gamedata_sha256"], "Installed catalog differs")
    for name, digest in manifest["private_files"].items():
        bs.require(bs.file_sha(ITEMS / name) == digest, f"Installed {name} differs")
    print("Installed:", ", ".join(sorted(private)))
    print(f'Rollback:\n  python -B "{Path(__file__).resolve()}" rollback "{backup}"')


def rollback(folder: Path):
    bs.stopped()
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    game = CLIENT / "gamedata.mpk"
    bs.require(bs.file_sha(game) in (m["before_gamedata_sha256"], m["after_gamedata_sha256"]),
               "Later catalog changes detected; refuse to overwrite them")
    for name, digest in m["private_files"].items():
        path = ITEMS / name
        bs.require(not path.exists() or bs.file_sha(path) == digest, f"{name} changed since install")
    with bs.db_session(DB) as con:
        for slot, (old, new) in m["equipment"].items():
            con.execute("UPDATE NPCEquipment SET Model=? WHERE TemplateID=? AND Slot=? AND Model IN (?, ?)",
                        (old, EQUIPMENT_TEMPLATE, int(slot), old, new))
    bs.atomic_write(game, (folder / "gamedata.mpk").read_bytes())
    for name in m["private_files"]:
        if (ITEMS / name).exists():
            (ITEMS / name).unlink()
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "plan":
        _, added = catalog()
        for key, rows in added.items():
            for r in rows:
                print(key, r[:27] if key == "objects.csv" else r[:6])
        for w in WEAPONS:
            private_nif(w[5], *w[7])
            print(w[6], "->", w[7][1].decode(), {k: len(v) for k, v in textures(w).items()})
    else:
        print(__doc__)
