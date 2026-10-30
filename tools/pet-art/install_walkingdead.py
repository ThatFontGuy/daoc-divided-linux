"""Give the Walking Dead pet (template 60170002) its own subtly recoloured model.

  install : python install_walkingdead.py install
  rollback: python install_walkingdead.py rollback <backup-folder>

The Walking Dead and the Shambling Dead (and hundreds of ordinary monsters)
share stock model 110 (Zombie.NIF + zomtex01). Nothing stock is changed:
  client figures\\Sluaghbinder_WalkingDead.NIF   byte copy of Zombie.NIF
  client figures\\skins\\skin099.mpk             adds sluagh_walking_dead_body.dds
  client gamedata.mpk                            model 2499, NIF row 992 (before
                                                 the MAX MONNIFS terminator), skin 7133,
                                                 each cloned from the stock row
  server NpcTemplate 60170002 Model 110 -> 2499  (Shambling Dead stays on 110)
Run with the launcher, client and server CLOSED.
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
from install_pet_art import (CLIENT, DB, archive, check_catalog_order, csv_table, append_rows,  # noqa: E402
                             encode_dds, insert_before_terminator, require, sha)

PET = dict(template=60170002, stock_model="110", model="2499", nif_id="992", skin="7133",
           nif_src="Zombie.NIF", nif="Sluaghbinder_WalkingDead", dds="sluagh_walking_dead_body.dds",
           label="Sluaghbinder Walking Dead", art="work/walkingdead_v1.png", ref="originals/zomtex01.dds")


def install():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = HERE / "install-backups" / f"walkingdead-{stamp}"
    backup.mkdir(parents=True)
    gamedata_path = CLIENT / "gamedata.mpk"
    skin_path = CLIENT / "figures" / "skins" / "skin099.mpk"
    nif_target = CLIENT / "figures" / f"{PET['nif']}.NIF"
    require(not nif_target.exists(), f"{nif_target.name} already exists; roll back first")
    manifest = {"created": stamp, "files": {}, "new_files": [], "templates": {}}
    for path in (gamedata_path, skin_path):
        shutil.copy2(path, backup / path.name)
        manifest["files"][str(path.relative_to(CLIENT))] = sha(path.read_bytes())

    # --- skin099: add the private texture (every other entry verified identical)
    name, entries = archive.read(skin_path.read_bytes())
    require(all(e.name.lower() != PET["dds"] for e in entries), f"{PET['dds']} already in skin099.mpk")
    art = Image.open(HERE / PET["art"]).convert("RGB")
    require(art.size == (256, 256), "walking dead art must stay 256x256 like the stock texture")
    dds = encode_dds(art, (HERE / PET["ref"]).read_bytes())
    stamp_entry = entries[0]
    new_entries = sorted(entries + [archive.Entry(PET["dds"], dds, stamp_entry.timestamp, stamp_entry.flags)],
                         key=lambda e: e.name.lower())
    skin_blob = archive.write(name, new_entries)
    archive.verify_memory_image(skin_blob)
    old_by = {e.name.lower(): e for e in entries}
    for e in archive.read(skin_blob)[1]:
        if e.name.lower() != PET["dds"]:
            require(old_by[e.name.lower()] == e, f"unrelated skin entry changed: {e.name}")

    # --- gamedata catalogs (rows cloned from the stock zombie)
    gname, gentries = archive.read(gamedata_path.read_bytes())
    gfiles = {e.name.lower(): e for e in gentries}
    tables = {n: csv_table(gfiles[n].data) for n in ("monsters.csv", "monnifs.csv", "skins.csv")}
    by = {n: {r[0]: r for r in t if r and r[0].isdigit()} for n, t in tables.items()}
    require(PET["model"] not in by["monsters.csv"], "model id taken")
    require(PET["nif_id"] not in by["monnifs.csv"], "NIF row id taken")
    require(PET["skin"] not in by["skins.csv"], "skin id taken")
    stock = by["monsters.csv"][PET["stock_model"]]
    nrow = list(by["monnifs.csv"][stock[2]]); nrow[0], nrow[1], nrow[2] = PET["nif_id"], PET["label"], PET["nif"]
    srow = list(by["skins.csv"][stock[3]]); srow[0], srow[1], srow[2], srow[4] = PET["skin"], PET["label"] + " Body", PET["dds"], "99"
    mrow = list(stock); mrow[0], mrow[1], mrow[2], mrow[3] = PET["model"], PET["label"], PET["nif_id"], PET["skin"]
    replaced = {"monsters.csv": append_rows(gfiles["monsters.csv"].data, [mrow]),
                "monnifs.csv": insert_before_terminator(gfiles["monnifs.csv"].data, [nrow], "1000"),
                "skins.csv": append_rows(gfiles["skins.csv"].data, [srow])}
    check_catalog_order(replaced["monsters.csv"], None)
    check_catalog_order(replaced["monnifs.csv"], "1000")
    check_catalog_order(replaced["skins.csv"], None)
    gout = [archive.Entry(e.name, replaced.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in gentries]
    gblob = archive.write(gname, gout)
    archive.verify_memory_image(gblob)
    for old, fresh in zip(gentries, archive.read(gblob)[1]):
        if old.name.lower() not in replaced:
            require(old == fresh, f"unrelated gamedata entry changed: {old.name}")

    con = sqlite3.connect(DB)
    old_model = con.execute("SELECT Model FROM NpcTemplate WHERE TemplateId = ?", (PET["template"],)).fetchone()[0]
    require(str(old_model) == PET["stock_model"], f"template model is {old_model}, expected {PET['stock_model']}")

    # --- write
    skin_path.write_bytes(skin_blob)
    gamedata_path.write_bytes(gblob)
    shutil.copy2(CLIENT / "figures" / PET["nif_src"], nif_target)
    manifest["new_files"].append(str(nif_target.relative_to(CLIENT)))
    with con:
        con.execute("UPDATE NpcTemplate SET Model = ? WHERE TemplateId = ?", (PET["model"], PET["template"]))
    con.close()
    manifest["templates"][str(PET["template"])] = str(old_model)
    manifest["after"] = {"gamedata.mpk": sha(gblob), "figures/skins/skin099.mpk": sha(skin_blob)}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"\nInstalled. Rollback with:\n  python install_walkingdead.py rollback \"{backup}\"")


def rollback(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text())
    shutil.copy2(folder / "gamedata.mpk", CLIENT / "gamedata.mpk")
    shutil.copy2(folder / "skin099.mpk", CLIENT / "figures" / "skins" / "skin099.mpk")
    for relative in manifest["new_files"]:
        path = CLIENT / relative
        if path.exists():
            path.unlink()
    con = sqlite3.connect(DB)
    with con:
        for template, model in manifest["templates"].items():
            con.execute("UPDATE NpcTemplate SET Model = ? WHERE TemplateId = ?", (model, int(template)))
    con.close()
    for relative, digest in manifest["files"].items():
        require(sha((CLIENT / relative).read_bytes()) == digest, f"rollback hash mismatch: {relative}")
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    else:
        print(__doc__)
