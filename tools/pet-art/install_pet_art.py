"""Install the Claude pet skins into the CLAUDE VERSION client (private assets only).

  install : python install_pet_art.py install
  rollback: python install_pet_art.py rollback <backup-folder>

What install changes (everything is backed up first, with hashes):
  client figures\\skins\\skin099.mpk
      - replaces sluagh_zombie_defender_body.dds (Zombie Guardian)
      - adds sluagh_sturdy_zombie_body.dds, sluagh_zombie_magician_body.dds,
        sluagh_zombie_priest_body.dds
  client gamedata.mpk (monsters.csv / monnifs.csv / skins.csv)
      - appends one private model, NIF and skin row per new pet, cloned from
        the stock row it was copied from (stock rows are never edited)
  client figures\\ Sluaghbinder_SturdyZombie.NIF, _ZombieMagician.NIF,
      _ZombiePriest.NIF : byte copies of B_Band01, H_ElfMon01, B_AvMon01F
  server NpcTemplate Model for sturdy zombie / zombie magician / zombie priest

Stock monster models, NIFs and skins are untouched. Run with the launcher,
client and server CLOSED.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import shutil
import sqlite3
import struct
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                                   # ...\new class test - CLAUDE VERSION
CLIENT = ROOT / "runtime" / "client-opendaoc" / "app"
DB = ROOT / "runtime" / "data" / "opendaoc.sqlite3.db"
sys.path.insert(0, str(HERE))
from daoc_catalog import archive  # Codex's validated MPAK codec  # noqa: E402

PETS = [
    # key, art png, template id, stock model id, new model id, new skin id, NIF source, NIF name, dds name, label
    dict(key="sturdy", art="work/sturdy_v2.png", template=60170003, stock_model="467", model="2496", skin="7130",
         nif_src="B_Band01.NIF", nif="Sluaghbinder_SturdyZombie", dds="sluagh_sturdy_zombie_body.dds",
         label="Sluaghbinder Sturdy Zombie", ref="b_unde01m.dds"),
    dict(key="magician", art="work/magician_v3.png", template=60170004, stock_model="446", model="2497", skin="7131",
         nif_src="H_ElfMon01.NIF", nif="Sluaghbinder_ZombieMagician", dds="sluagh_zombie_magician_body.dds",
         label="Sluaghbinder Zombie Magician", ref="e_unde01.dds"),
    dict(key="priest", art="work/priest_v2.png", template=60170006, stock_model="451", model="2498", skin="7132",
         nif_src="B_AvMon01F.NIF", nif="Sluaghbinder_ZombiePriest", dds="sluagh_zombie_priest_body.dds",
         label="Sluaghbinder Zombie Priest", ref="a_unde01f.dds"),
]
GUARDIAN = dict(art="work/guardian_final.png", dds="sluagh_zombie_defender_body.dds", ref="sluagh_zombie_defender_body.dds")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise SystemExit(message)


# ------------------------------------------------------------------ DDS ---
def encode_dds(image: Image.Image, reference: bytes) -> bytes:
    """DXT1 with a full mip chain; legacy header properties kept from the
    working reference texture (same approach as Codex's Pet Texture Tool)."""
    working = image.convert("RGB")
    header, blocks = None, []
    while True:
        out = io.BytesIO()
        working.save(out, format="DDS", pixel_format="DXT1")
        data = out.getvalue()
        require(data[84:88] == b"DXT1", "Pillow did not produce DXT1")
        header = bytearray(data[:128]) if header is None else header
        blocks.append(data[128:])
        if working.size == (1, 1):
            break
        working = working.resize((max(1, working.width // 2), max(1, working.height // 2)), Image.Resampling.LANCZOS)
    struct.pack_into("<I", header, 8, (struct.unpack_from("<I", header, 8)[0] | 0xA0000) & ~0x8)
    struct.pack_into("<I", header, 20, len(blocks[0]))
    struct.pack_into("<I", header, 88, 0)
    struct.pack_into("<I", header, 28, len(blocks))
    struct.pack_into("<I", header, 108, 0x1000 | 0x8 | 0x400000)
    encoded = bytes(header) + b"".join(blocks)
    final = bytearray(reference[:128])
    for offset in (12, 16, 20, 28):
        final[offset:offset + 4] = encoded[offset:offset + 4]
    result = bytes(final) + encoded[128:]
    validate_dds(result)
    return result


def validate_dds(data: bytes):
    require(data[:4] == b"DDS " and struct.unpack_from("<I", data, 4)[0] == 124, "Not a legacy DDS")
    h, w = struct.unpack_from("<II", data, 12)
    levels = struct.unpack_from("<I", data, 28)[0]
    require(data[84:88] == b"DXT1", "Unexpected codec")
    require(levels == int(math.log2(max(w, h))) + 1, "Incomplete mip chain")
    offset = 128
    for i in range(levels):
        offset += max(1, (max(1, w >> i) + 3) // 4) * max(1, (max(1, h >> i) + 3) // 4) * 8
    require(offset == len(data), "DDS payload length mismatch")
    Image.open(io.BytesIO(data)).load()


# ------------------------------------------------------------ catalogs ---
def csv_table(data: bytes):
    return list(csv.reader(io.StringIO(data.decode("latin1"))))


def append_rows(data: bytes, rows) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    for row in rows:
        writer.writerow(row)
    text = data.decode("latin1")
    if not text.endswith("\r\n"):
        text += "\r\n"
    return (text + buf.getvalue()).encode("latin1")


def insert_before_terminator(data: bytes, rows, terminator_id: str) -> bytes:
    """Insert rows in ID order immediately after the last real row below the
    table's terminator (monnifs.csv ends with '1000, MAX MONNIFS'). The client
    stops reading at that terminator, so rows appended after it are ignored and
    the model is invisible in game."""
    lines = data.decode("latin1").split("\r\n")
    last = None
    for index, line in enumerate(lines):
        head = line.split(",", 1)[0].strip()
        if head.isdigit():
            if int(head) >= int(terminator_id):
                break
            last = index
    require(last is not None, "no data rows before the terminator")
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    for row in sorted(rows, key=lambda r: int(r[0])):
        require(int(row[0]) < int(terminator_id), f"row id {row[0]} must be below {terminator_id}")
        writer.writerow(row)
    new_lines = buf.getvalue().split("\r\n")[:-1]
    return "\r\n".join(lines[:last + 1] + new_lines + lines[last + 1:]).encode("latin1")


def check_catalog_order(data: bytes, terminator_id: str | None):
    """IDs never decrease (stock tables repeat a few IDs) and every real row sits before the terminator."""
    ids = [int(r[0]) for r in csv_table(data) if r and r[0].strip().isdigit()]
    require(all(a <= b for a, b in zip(ids, ids[1:])), "catalog IDs are not in ascending order")
    if terminator_id:
        require(ids[-1] == int(terminator_id), "rows found after the terminator")


def next_free(ids, start):
    i = start
    while str(i) in ids:
        i += 1
    return str(i)


# ------------------------------------------------------------- install ---
def install():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = HERE / "install-backups" / stamp
    backup.mkdir(parents=True)
    gamedata_path = CLIENT / "gamedata.mpk"
    skin_path = CLIENT / "figures" / "skins" / "skin099.mpk"
    manifest = {"created": stamp, "files": {}, "new_files": [], "templates": {}}
    for path in (gamedata_path, skin_path):
        data = path.read_bytes()
        shutil.copy2(path, backup / path.name)
        manifest["files"][str(path.relative_to(CLIENT))] = sha(data)

    # --- skins: build DDS
    name, entries = archive.read(skin_path.read_bytes())
    by_name = {e.name.lower(): e for e in entries}
    originals = HERE / "originals"
    encoded = {}
    for pet in PETS:
        encoded[pet["dds"]] = encode_dds(Image.open(HERE / pet["art"]), (originals / pet["ref"]).read_bytes())
    encoded[GUARDIAN["dds"]] = encode_dds(Image.open(HERE / GUARDIAN["art"]), by_name[GUARDIAN["dds"]].data)

    template_entry = by_name[GUARDIAN["dds"]]
    new_entries = []
    for e in entries:
        if e.name.lower() == GUARDIAN["dds"]:
            new_entries.append(archive.Entry(e.name, encoded[GUARDIAN["dds"]], e.timestamp, e.flags))
        elif e.name.lower() in (p["dds"] for p in PETS):
            raise SystemExit(f"{e.name} already exists in skin099.mpk; roll back first")
        else:
            new_entries.append(e)
    for pet in PETS:
        new_entries.append(archive.Entry(pet["dds"], encoded[pet["dds"]], template_entry.timestamp, template_entry.flags))
    new_entries.sort(key=lambda e: e.name.lower())
    skin_blob = archive.write(name, new_entries)
    archive.verify_memory_image(skin_blob)
    old_by = {e.name.lower(): e for e in entries}
    for e in archive.read(skin_blob)[1]:
        if e.name.lower() in old_by and e.name.lower() != GUARDIAN["dds"]:
            require(old_by[e.name.lower()] == e, f"unrelated skin entry changed: {e.name}")

    # --- gamedata catalogs
    gname, gentries = archive.read(gamedata_path.read_bytes())
    gfiles = {e.name.lower(): e for e in gentries}
    monsters = csv_table(gfiles["monsters.csv"].data)
    monnifs = csv_table(gfiles["monnifs.csv"].data)
    skins = csv_table(gfiles["skins.csv"].data)
    mon_by = {r[0]: r for r in monsters if r and r[0].isdigit()}
    nif_by = {r[0]: r for r in monnifs if r and r[0].isdigit()}
    skin_by = {r[0]: r for r in skins if r and r[0].isdigit()}

    new_mon, new_nif, new_skin = [], [], []
    for pet in PETS:
        require(pet["model"] not in mon_by and pet["skin"] not in skin_by, f"id collision for {pet['key']}")
        stock = mon_by[pet["stock_model"]]
        nif_id = next_free(set(nif_by) | {r[0] for r in new_nif}, 989)
        pet["nif_id"] = nif_id
        nrow = list(nif_by[stock[2]]); nrow[0] = nif_id; nrow[1] = pet["label"]; nrow[2] = pet["nif"]
        srow = list(skin_by[stock[3]]); srow[0] = pet["skin"]; srow[1] = pet["label"] + " Body"
        srow[2] = pet["dds"]; srow[4] = "99"
        mrow = list(stock); mrow[0] = pet["model"]; mrow[1] = pet["label"]; mrow[2] = nif_id; mrow[3] = pet["skin"]
        new_mon.append(mrow); new_nif.append(nrow); new_skin.append(srow)
    replaced = {"monsters.csv": append_rows(gfiles["monsters.csv"].data, new_mon),
                "monnifs.csv": insert_before_terminator(gfiles["monnifs.csv"].data, new_nif, "1000"),
                "skins.csv": append_rows(gfiles["skins.csv"].data, new_skin)}
    check_catalog_order(replaced["monsters.csv"], None)
    check_catalog_order(replaced["monnifs.csv"], "1000")
    check_catalog_order(replaced["skins.csv"], None)
    gout = [archive.Entry(e.name, replaced.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in gentries]
    gblob = archive.write(gname, gout)
    archive.verify_memory_image(gblob)

    # --- NIF copies
    figures = CLIENT / "figures"
    for pet in PETS:
        target = figures / f"{pet['nif']}.NIF"
        require(not target.exists(), f"{target.name} already exists; roll back first")

    # --- write everything
    skin_path.write_bytes(skin_blob)
    gamedata_path.write_bytes(gblob)
    for pet in PETS:
        target = figures / f"{pet['nif']}.NIF"
        shutil.copy2(figures / pet["nif_src"], target)
        manifest["new_files"].append(str(target.relative_to(CLIENT)))

    # --- server templates
    con = sqlite3.connect(DB)
    with con:
        for pet in PETS:
            old = con.execute("SELECT Model FROM NpcTemplate WHERE TemplateId = ?", (pet["template"],)).fetchone()[0]
            require(str(old) == pet["stock_model"], f"template {pet['template']} model is {old}, expected {pet['stock_model']}")
            manifest["templates"][str(pet["template"])] = str(old)
            con.execute("UPDATE NpcTemplate SET Model = ? WHERE TemplateId = ?", (pet["model"], pet["template"]))
    con.close()

    manifest["installed"] = {p["key"]: dict(model=p["model"], nif_id=p["nif_id"], skin=p["skin"], nif=p["nif"], dds=p["dds"]) for p in PETS}
    manifest["after"] = {"gamedata.mpk": sha(gblob), "figures/skins/skin099.mpk": sha(skin_blob)}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"\nInstalled. Rollback with:\n  python install_pet_art.py rollback \"{backup}\"")


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
