"""Give the Zombie Magician's private anim set 434 its combat animations.

The client keeps an anim set's animations in TWO tables keyed by the same set id:
  anims.csv   movement, idle, death, spell-cast gestures, emotes
  canims.csv  melee swings (incl. staff), combat stance, flinch, parry, styles
install_void_sun.py added set 434 to anims.csv only, so in melee the magician had
no swing / combat-idle animation and froze in place. This adds canims row 434 as an
exact copy of undead set 46 (what the magician used before), so its melee is
unchanged from the stock zombie. No other row is touched.

  install : python add_magician_combat_anims.py install
  rollback: python add_magician_combat_anims.py rollback <backup-folder>
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from daoc_catalog import CLIENT, archive  # noqa: E402
from install_void_sun import insert_after_id, require, rows_of  # noqa: E402

SET_ID, BASE_SET = "434", "46"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patched_canims(data: bytes) -> bytes:
    by = {r[0].strip(): r for r in rows_of(data) if r and r[0].strip().isdigit()}
    require(SET_ID not in by, f"canims {SET_ID} already present")
    row = list(by[BASE_SET])
    row[0], row[1] = SET_ID, "Sluagh Zombie Magician (undead combat)"
    out = insert_after_id(data, max(by, key=int), [row])
    after = {r[0].strip(): r for r in rows_of(out) if r and r[0].strip().isdigit()}
    require(after[SET_ID][2:] == by[BASE_SET][2:], "copied row differs")
    require(all(after[k] == v for k, v in by.items()), "an existing canims row changed")
    ids = [int(r[0]) for r in rows_of(out) if r and r[0].strip().isdigit()]
    require(ids == sorted(ids), "canims ids out of order")
    return out


def install():
    path = CLIENT / "gamedata.mpk"
    original = path.read_bytes()
    gname, entries = archive.read(original)
    anims = next(e for e in entries if e.name.lower() == "anims.csv").data
    require(any(r and r[0].strip() == SET_ID for r in rows_of(anims)), "anim set 434 not installed")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = HERE / "install-backups" / f"magician-canims-{stamp}"
    backup.mkdir(parents=True)
    shutil.copy2(path, backup / "gamedata.mpk")
    new = [archive.Entry(e.name, patched_canims(e.data) if e.name.lower() == "canims.csv" else e.data,
                         e.timestamp, e.flags) for e in entries]
    blob = archive.write(gname, new)
    archive.verify_memory_image(blob)
    for old, fresh in zip(entries, archive.read(blob)[1]):
        if old.name.lower() != "canims.csv" and old != fresh:
            raise SystemExit(f"unrelated entry changed: {old.name}")
    path.write_bytes(blob)
    manifest = {"created": stamp, "gamedata_sha": sha(original), "after_gamedata_sha": sha(blob)}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"\nInstalled. Rollback with:\n  python add_magician_combat_anims.py rollback \"{backup}\"")


def rollback(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text())
    shutil.copy2(folder / "gamedata.mpk", CLIENT / "gamedata.mpk")
    require(sha((CLIENT / "gamedata.mpk").read_bytes()) == manifest["gamedata_sha"], "rollback hash mismatch")
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    else:
        print(__doc__)
