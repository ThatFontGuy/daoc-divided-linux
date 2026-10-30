"""Fix the pink private pet shields: give them private pskins like their stock originals.

  install : python -B install_pet_shield_skins.py install
  rollback: python -B install_pet_shield_skins.py rollback <backup-folder>

Emblem shields (cloakpattern/symbol layers in the NIF) take their base texture
from a pskins override; with no override the client had no base and drew pink.
This mirrors the stock grave/tower shield rows exactly, with private data:
  items\\pskins\\pskin099.mpk   NEW private archive: SluNShield1.dds, sluGTwr01a.dds
  pskins.csv 5766, 5767        NEW private rows (archive 99), cloned from 2050 / 761
  objects.csv 4823, 4825       (private rows) Apply Texture 0 -> 5766 / 5767
  items.csv 2900, 2902         (private rows) Strip Textures 0 -> 1, as stock
Stock archives and rows are untouched. Run with launcher, client and server CLOSED.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install_blood_shield as bs  # noqa: E402
from daoc_catalog import archive  # noqa: E402

CLIENT = bs.CLIENT
ITEMS = CLIENT / "items"
ARCHIVE = ITEMS / "pskins" / "pskin099.mpk"
# (pskin id, stock pskin row, texture file, object id, item id)
SHIELDS = [(5766, 2050, "SluNShield1.dds", 4823, 2900),
           (5767, 761, "sluGTwr01a.dds", 4825, 2902)]


def replace_line(data, ident, column, old, new):
    lines = data.decode("latin1").split("\r\n")
    hits = [i for i, line in enumerate(lines) if line.split(",", 1)[0].strip() == str(ident)]
    bs.require(len(hits) == 1, f"row {ident} not unique")
    row = next(iter(bs.rows_of(lines[hits[0]].encode("latin1"))))
    bs.require(row[column] == old, f"row {ident} column {column} is {row[column]!r}, expected {old!r}")
    row[column] = new
    lines[hits[0]] = bs.line_of(row)
    return "\r\n".join(lines).encode("latin1")


def catalog():
    name, entries, files, _ = bs.catalogs()
    pskins = {r[0].strip(): r for r in bs.rows_of(files["pskins.csv"]) if r and r[0].strip().isdigit()}
    objects, items, skins = files["objects.csv"], files["items.csv"], files["pskins.csv"]
    added = []
    for pid, stock, texture, oid, iid in SHIELDS:
        bs.require(str(pid) not in pskins, f"pskins {pid} already used")
        row = list(pskins[str(stock)])
        row[0], row[1], row[2], row[4] = str(pid), "Sluagh pet shield " + texture.rsplit(".", 1)[0], texture, "99"
        skins = bs.add_row(skins, row)
        added.append(row)
        objects = replace_line(objects, oid, 22, "0", str(pid))
        items = replace_line(items, iid, 3, "0", "1")
    updates = {"objects.csv": objects, "items.csv": items, "pskins.csv": skins}
    blob = archive.write(name, [archive.Entry(e.name, updates.get(e.name.lower(), e.data), e.timestamp, e.flags)
                                for e in entries])
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    bs.require([e.name for e in decoded] == [e.name for e in entries], "Archive entry order changed")
    for old, new in zip(entries, decoded):
        bs.require((old.timestamp, old.flags) == (new.timestamp, new.flags), "Archive metadata changed")
        if old.name.lower() not in updates:
            bs.require(old.data == new.data, f"Unrelated archive entry changed: {old.name}")
    # Only private rows may differ: pskins gains two rows; objects/items change only their private rows.
    for key, private in (("objects.csv", {"4823", "4825"}), ("items.csv", {"2900", "2902"}), ("pskins.csv", set())):
        old_rows = [r for r in bs.rows_of(files[key]) if not (r and r[0].strip() in private)]
        new_rows = [r for r in bs.rows_of(updates[key]) if not (r and r[0].strip() in private) and r not in added]
        bs.require(old_rows == new_rows, f"Stock {key} row changed")
    return blob


def private_archive():
    textures = sorted(((t, (ITEMS / t).read_bytes()) for _, _, t, _, _ in SHIELDS), key=lambda x: x[0].lower())
    stamp = int(time.time())
    blob = archive.write(b"pskin099.mpk", [archive.Entry(n, d, stamp, 4) for n, d in textures])
    archive.verify_memory_image(blob)
    name, decoded = archive.read(blob)
    bs.require([(e.name, e.data) for e in decoded] == textures, "Private archive round trip failed")
    return blob


def install():
    bs.stopped()
    game = CLIENT / "gamedata.mpk"
    bs.require(not ARCHIVE.exists(), "pskin099.mpk already exists")
    blob, pak = catalog(), private_archive()
    backup = HERE / "install-backups" / ("pet-shield-skins-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(game, backup / "gamedata.mpk")
    manifest = {"before_gamedata_sha256": bs.file_sha(game), "after_gamedata_sha256": bs.sha(blob),
                "archive_sha256": bs.sha(pak)}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bs.atomic_write(ARCHIVE, pak)
    bs.atomic_write(game, blob)
    bs.require(bs.file_sha(game) == manifest["after_gamedata_sha256"], "Installed catalog differs")
    bs.require(bs.file_sha(ARCHIVE) == manifest["archive_sha256"], "Installed archive differs")
    print(f'Installed. Rollback:\n  python -B "{Path(__file__).resolve()}" rollback "{backup}"')


def rollback(folder: Path):
    bs.stopped()
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    game = CLIENT / "gamedata.mpk"
    bs.require(bs.file_sha(game) in (m["before_gamedata_sha256"], m["after_gamedata_sha256"]),
               "Later catalog changes detected; refuse to overwrite them")
    bs.require(not ARCHIVE.exists() or bs.file_sha(ARCHIVE) == m["archive_sha256"], "pskin099.mpk changed")
    bs.atomic_write(game, (folder / "gamedata.mpk").read_bytes())
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "plan":
        catalog()
        private_archive()
        print("plan ok")
    else:
        print(__doc__)
