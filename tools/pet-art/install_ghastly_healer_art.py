"""Install the private ghastly healer model (a haunting badh variant). Cosmetic only.

  preview : python -B install_ghastly_healer_art.py           (default, changes nothing)
  install : python -B install_ghastly_healer_art.py install
  rollback: python -B install_ghastly_healer_art.py rollback <backup-folder>

Build and review first with build_ghastly_healer.py; this installs its output:
  client figures\\Sluaghbinder_GhastlyHealer.NIF : reshaped byte copy of bainsheesi.nif
  client figures\\skins\\skin099.mpk               : + sluagh_ghastly_healer_body.dds
  client gamedata.mpk                              : + monster 2072 (inserted in ID order;
      an unused gap below 2500), monnif 993, skin 7134 (both "Expansion Only" 0)
      (cloned from the stock badh rows 1885 / 661 / 6070; sound set 59 "spectre",
       the ghost wail, instead of 23 "dwarf female")
  server NpcTemplate 60170006 (ghastly healer) Model 1885 -> 2072
Stock badh rows, NIF and skin are untouched, so world badh mobs keep their look
and voice. Run with the launcher, client and server CLOSED.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install_pet_art as pa  # noqa: E402  (DDS encoder and catalog helpers)
from daoc_catalog import archive  # noqa: E402

CLIENT, DB = pa.CLIENT, pa.DB
BUILD = HERE / "work" / "ghastly-healer"
# The private model takes an unused gap ID below 2500, inserted in ID order (a
# precaution: the stock table ends at 2493 and the other private pets sit at 2494-2499).
TEMPLATE, STOCK_MODEL, MODEL, SKIN, NIF_ID = 60170006, "1885", "2072", "7134", "993"
MONSTER_ID_LIMIT = 2500
NIF = "Sluaghbinder_GhastlyHealer"
DDS = "sluagh_ghastly_healer_body.dds"
LABEL = "Sluaghbinder Ghastly Healer"
SOUND_COLUMN, GHOST_SOUND = 15, "59"
EXPANSION_NIF_COLUMN, EXPANSION_SKIN_COLUMN = 9, 5  # "Expansion Only" in monnifs / skins
REFERENCE_DDS = "sluagh_zombie_priest_body.dds"  # DXT1 header template already in skin099
GAMEDATA = CLIENT / "gamedata.mpk"
SKINS = CLIENT / "figures" / "skins" / "skin099.mpk"
TARGET_NIF = CLIENT / "figures" / f"{NIF}.NIF"


def insert_in_order(data: bytes, row) -> bytes:
    """Insert one row right after the last row with a lower ID; no other line changes."""
    newline = chr(13) + chr(10)
    lines = data.decode("latin1").split(newline)
    index = max(i for i, line in enumerate(lines)
                if line.split(",", 1)[0].strip().isdigit() and int(line.split(",", 1)[0]) < int(row[0]))
    # append_rows(b"") starts with a newline; strip both ends or the row lands after a
    # blank line, and the client stops reading monsters.csv at the first blank line.
    added = pa.append_rows(b"", [row]).decode("latin1").strip(newline)
    out = lines[:index + 1] + [added] + lines[index + 1:]
    pa.require(out[:index + 1] + out[index + 2:] == lines, "insert changed other monster rows")
    pa.require(added and all(line.strip() for line in out[:-1]), "blank line inside monsters.csv")
    return newline.join(out).encode("latin1")


def build():
    for name in (f"{NIF}.NIF", "ghastly_healer_skin.png"):
        pa.require((BUILD / name).exists(), f"Run build_ghastly_healer.py first ({name} missing)")
    nif_blob = (BUILD / f"{NIF}.NIF").read_bytes()

    sname, sentries = archive.read(SKINS.read_bytes())
    by_name = {e.name.lower(): e for e in sentries}
    pa.require(DDS not in by_name, f"{DDS} already in skin099.mpk; roll back first")
    reference = by_name[REFERENCE_DDS.lower()]
    dds = pa.encode_dds(Image.open(BUILD / "ghastly_healer_skin.png"), reference.data)
    new_skins = sorted(sentries + [archive.Entry(DDS, dds, reference.timestamp, reference.flags)],
                       key=lambda e: e.name.lower())
    skin_blob = archive.write(sname, new_skins)
    archive.verify_memory_image(skin_blob)
    old = {e.name.lower(): e for e in sentries}
    for e in archive.read(skin_blob)[1]:
        if e.name.lower() in old:
            pa.require(old[e.name.lower()] == e, f"unrelated skin entry changed: {e.name}")

    gname, gentries = archive.read(GAMEDATA.read_bytes())
    files = {e.name.lower(): e for e in gentries}
    monsters = {r[0]: r for r in pa.csv_table(files["monsters.csv"].data) if r and r[0].isdigit()}
    monnifs = {r[0]: r for r in pa.csv_table(files["monnifs.csv"].data) if r and r[0].isdigit()}
    skins = {r[0]: r for r in pa.csv_table(files["skins.csv"].data) if r and r[0].isdigit()}
    pa.require(MODEL not in monsters and NIF_ID not in monnifs and SKIN not in skins, "Private IDs already used")
    stock = monsters[STOCK_MODEL]
    pa.require(stock[2].strip() == "661" and stock[3].strip() == "6070" and stock[SOUND_COLUMN].strip() == "23",
               "Stock badh rows changed; re-review")
    mrow = list(stock)
    mrow[0], mrow[1], mrow[2], mrow[3], mrow[SOUND_COLUMN] = MODEL, LABEL, NIF_ID, SKIN, GHOST_SOUND
    nrow = list(monnifs[stock[2].strip()])
    nrow[0], nrow[1], nrow[2] = NIF_ID, LABEL, NIF
    # The stock badh rows are "Expansion Only" (Shrouded Isles). The private NIF and
    # skin are ordinary loose/skin099 assets like every other Sluaghbinder pet, so the
    # flag must be 0 or the client never finds them and draws nothing.
    nrow[EXPANSION_NIF_COLUMN] = "0"
    srow = list(skins[stock[3].strip()])
    srow[0], srow[1], srow[2], srow[4], srow[EXPANSION_SKIN_COLUMN] = SKIN, LABEL + " Body", DDS, "99", "0"
    pa.require(int(MODEL) < MONSTER_ID_LIMIT, "Keep private monster IDs below 2500")
    replaced = {"monsters.csv": insert_in_order(files["monsters.csv"].data, mrow),
                "monnifs.csv": pa.insert_before_terminator(files["monnifs.csv"].data, [nrow], "1000"),
                "skins.csv": pa.append_rows(files["skins.csv"].data, [srow])}
    pa.check_catalog_order(replaced["monsters.csv"], None)
    pa.check_catalog_order(replaced["monnifs.csv"], "1000")
    pa.check_catalog_order(replaced["skins.csv"], None)
    game_blob = archive.write(gname, [archive.Entry(e.name, replaced.get(e.name.lower(), e.data), e.timestamp, e.flags)
                                      for e in gentries])
    archive.verify_memory_image(game_blob)
    for e in archive.read(game_blob)[1]:
        if e.name.lower() not in replaced:
            pa.require(files[e.name.lower()].data == e.data, f"unrelated gamedata entry changed: {e.name}")
    return nif_blob, skin_blob, game_blob, (mrow, nrow, srow)


def preview():
    _, _, _, rows = build()
    for table, row in zip(("monsters", "monnifs", "skins"), rows):
        print(f"  {table}.csv + {row[:4]}{' sound set ' + row[SOUND_COLUMN] if table == 'monsters' else ''}")
    with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True) as con:
        model = con.execute("SELECT Model FROM NpcTemplate WHERE TemplateId=?", (TEMPLATE,)).fetchone()[0]
    print(f"  NpcTemplate {TEMPLATE} Model {model} -> {MODEL}")
    print(f"  + figures/{TARGET_NIF.name}, skin099.mpk + {DDS}")
    print("Preview only. Run with 'install' to apply.")


def install():
    pa.require(not TARGET_NIF.exists(), f"{TARGET_NIF.name} already exists; roll back first")
    nif_blob, skin_blob, game_blob, _ = build()
    con = sqlite3.connect(DB)
    try:
        model = con.execute("SELECT Model FROM NpcTemplate WHERE TemplateId=?", (TEMPLATE,)).fetchone()[0]
    finally:
        con.close()
    pa.require(str(model) == STOCK_MODEL, f"Template {TEMPLATE} model is {model}, expected {STOCK_MODEL}")
    backup = HERE / "install-backups" / ("ghastly-healer-art-" + time.strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    manifest = {"files": {}, "after": {}}
    for path in (GAMEDATA, SKINS):
        shutil.copy2(path, backup / path.name)
        manifest["files"][path.name] = pa.sha(path.read_bytes())
    manifest["after"] = {GAMEDATA.name: pa.sha(game_blob), SKINS.name: pa.sha(skin_blob), TARGET_NIF.name: pa.sha(nif_blob)}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    TARGET_NIF.write_bytes(nif_blob)
    SKINS.write_bytes(skin_blob)
    GAMEDATA.write_bytes(game_blob)
    con = sqlite3.connect(DB)
    with con:
        con.execute("UPDATE NpcTemplate SET Model=? WHERE TemplateId=?", (MODEL, TEMPLATE))
    con.close()
    for path, key in ((GAMEDATA, GAMEDATA.name), (SKINS, SKINS.name), (TARGET_NIF, TARGET_NIF.name)):
        pa.require(pa.sha(path.read_bytes()) == manifest["after"][key], f"{key} differs after install")
    print(f'Installed. Rollback with:\n  python -B "{Path(__file__).resolve()}" rollback "{backup}"')


def rollback(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for path in (GAMEDATA, SKINS):
        current = pa.sha(path.read_bytes())
        pa.require(current in (manifest["files"][path.name], manifest["after"][path.name]),
                   f"{path.name} changed since install; refuse to overwrite")
        shutil.copy2(folder / path.name, path)
    if TARGET_NIF.exists() and pa.sha(TARGET_NIF.read_bytes()) == manifest["after"][TARGET_NIF.name]:
        TARGET_NIF.unlink()
    con = sqlite3.connect(DB)
    with con:
        con.execute("UPDATE NpcTemplate SET Model=? WHERE TemplateId=? AND Model=?", (STOCK_MODEL, TEMPLATE, MODEL))
    con.close()
    print("Rolled back", folder)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if command == "install":
        install()
    elif command == "rollback" and len(sys.argv) > 2:
        rollback(Path(sys.argv[2]))
    else:
        preview()
