"""Green Cairn strength-buff visuals for the Sluaghbinder (0.34b). Cosmetic only.

  preview : python -B install_cairn_green_buff.py            (default, changes nothing)
  install : python -B install_cairn_green_buff.py install
  rollback: python -B install_cairn_green_buff.py rollback <backup-folder>

The Sluaghbinder's strength buffs borrowed Midgard animations with a blue hand
glow and a blue rune emblem on the ground:
  * self buffs Cairn Vigor/Fortitude/Oath (59027-59029) used the Thane's
    Thor's buffs (3535-3537: electric hand glow, blue triswirls, strength runes);
  * pet buffs 59006-59010 used the Bonedancer's Strengthen buffs
    (10041-10047: Spiritmaster hand glow, strength runes).
This adds private GREEN copies of those effects and points only the
ClientEffect field of those eight spells at them. Every other spell column,
every stock effect file and every stock catalog row stays exactly as it was.

Recolour: the green and blue channels are swapped in the private textures,
blue material glows and particle colour keys, so each effect keeps its exact
shape, brightness and timing and turns green. Run with the launcher, client
and server CLOSED.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sqlite3
import struct
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install_blood_shield as bs  # noqa: E402  (shared guarded helpers)
from daoc_catalog import archive  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

CLIENT, DB, EFFECTS = bs.CLIENT, bs.DB, bs.EFFECTS
OUT = HERE / "work/cairn-green-buff"

# New spnifs rows: id -> (stock NIF, private NIF, texture renames, description)
NIFS = {
    1406: ("mid_strbuff1_hit.NIF", "slu_cairnrun_hit.nif",
           {b"blustrkcyl.tga": b"slgstrkcyl.tga"}, "Cairn runes green (ground)"),
    1407: ("blutriswirl_hit.nif", "slu_cairnswl_hit.nif",
           {b"bluspkstrk.tga": b"slgspkstrk.tga"}, "Cairn green triswirls"),
    1408: ("mid_thane1_sum.nif", "slu_cairnhnd_sum.nif",
           {b"elecglow.tga": b"slgrglow.tga", b"bigarc2.tga": b"slgarc2.tga",
            b"plasrng2.tga": b"slgrrng2.tga"}, "Cairn green handglow"),
    1409: ("mid_spirit_sum.NIF", "slu_cairnspr_sum.nif",
           {b"plasrng2.tga": b"slgrrng2.tga"}, "Cairn green pet handglow"),
}
# Private texture -> stock source (TGA recoloured in place, DDS rewritten as TGA)
TEXTURES = {"slgstrkcyl.tga": "blustrkcyl.tga", "slgspkstrk.tga": "bluspkstrk.tga",
            "slgrrng2.tga": "plasrng2.tga", "slgrglow.tga": "elecglow.dds",
            "slgarc2.tga": "bigarc2.dds"}
# New speffects rows: id -> (stock row, private NIF id, name)
EFFECT_ROWS = {633: ("137", 1406, "Cairn runes green (ground)"),
               634: ("305", 1407, "Cairn green triswirls"),
               635: ("145", 1408, "Cairn green handglow left"),
               636: ("146", 1408, "Cairn green handglow right"),
               637: ("160", 1409, "Cairn green pet handglow Right"),
               638: ("161", 1409, "Cairn green pet handglow Left")}
# New client spell rows: id -> (stock row, name, {column: (stock value, new value)})
SELF_ID, PET_ID = 4586, 4587
CLIENT_SPELLS = {
    SELF_ID: ("3535", "Cairn Strength", {6: ("145", "635"), 7: ("146", "636"),
                                         11: ("305", "634"), 12: ("137", "633")}),
    PET_ID: ("10041", "Cairn Pet Strength", {6: ("160", "637"), 7: ("161", "638"),
                                             11: ("137", "633")}),
}
# Server spells: id -> (stock ClientEffect, new ClientEffect)
SPELLS = {59027: (3535, SELF_ID), 59028: (3536, SELF_ID), 59029: (3537, SELF_ID),
          59006: (10041, PET_ID), 59007: (10043, PET_ID), 59008: (10044, PET_ID),
          59009: (10046, PET_ID), 59010: (10047, PET_ID)}
PRIVATE_FILES = tuple(n[1] for n in NIFS.values()) + tuple(TEXTURES)


def stock(name):
    path = EFFECTS / name
    if not path.exists():
        match = [p for p in EFFECTS.iterdir() if p.name.lower() == name.lower()]
        bs.require(len(match) == 1, f"Stock effect file {name} not found")
        path = match[0]
    return path


def swap_gb(rgb):
    r, g, b = rgb
    return (r, b, g)


# --------------------------------------------------------------------- NIFs
def material_edits(blob):
    """Blue-dominant material colours (old NetImmerse 4.x layout)."""
    edits = []
    for match in re.finditer(b"NiMaterialProperty", blob):
        off = match.start()
        bs.require(struct.unpack_from("<I", blob, off - 4)[0] == 18, "Material type length mismatch")
        cursor = off + 18
        name_length = struct.unpack_from("<I", blob, cursor)[0]
        bs.require(name_length < 256, "Unexpected material name length")
        cursor += 4 + name_length + 10
        values = struct.unpack_from("<14f", blob, cursor)
        end = cursor + 56
        next_length = struct.unpack_from("<I", blob, end)[0]
        bs.require(2 <= next_length <= 80 and blob[end + 4:end + 6] == b"Ni",
                   "Material boundary does not end at the next NIF block")
        for index in (0, 3, 6, 9):  # ambient, diffuse, specular, emissive
            rgb = values[index:index + 3]
            if rgb[2] > 0.3 and rgb[2] > rgb[1] * 1.5 and rgb[2] > rgb[0] * 1.5:
                edits.append((cursor + index * 4, struct.pack("<3f", *swap_gb(rgb)), "material", rgb))
    return edits


def colour_key_edits(blob):
    """NiColorData particle colour keys: time + RGBA, linear keys only."""
    edits = []
    for match in re.finditer(b"NiColorData", blob):
        off = match.start()
        bs.require(struct.unpack_from("<I", blob, off - 4)[0] == 11, "NiColorData type length mismatch")
        count, key_type = struct.unpack_from("<II", blob, match.end())
        bs.require(key_type == 1 and 0 < count < 64, "Unexpected colour key layout")
        for i in range(count):
            key = match.end() + 8 + i * 20
            _, r, g, b, a = struct.unpack_from("<5f", blob, key)
            bs.require(all(0 <= v <= 2 for v in (r, g, b, a)), "Colour key out of range")
            edits.append((key + 4, struct.pack("<3f", *swap_gb((r, g, b))), "colour_key", (r, g, b)))
    return edits


def build_nif(source, renames):
    original = stock(source).read_bytes()
    bs.require(original.startswith(b"NetImmerse File Format, Version 4."), f"{source}: unexpected NIF version")
    blob = bytearray(original)
    edits = []
    for before, after in renames.items():
        bs.require(len(before) == len(after) and original.count(before) >= 1, f"{source}: texture {before!r} missing")
        for match in re.finditer(re.escape(before), original):
            edits.append((match.start(), after, "texture", before.decode()))
    edits += material_edits(original) + colour_key_edits(original)
    for off, new, _, _ in edits:
        blob[off:off + len(new)] = new
    restored = bytearray(blob)
    for off, new, _, _ in edits:
        restored[off:off + len(new)] = original[off:off + len(new)]
    bs.require(bytes(restored) == original and len(blob) == len(original), f"{source}: reversible-byte audit failed")
    return bytes(blob), [{"kind": k, "offset": o, "before": str(b)} for o, _, k, b in edits]


# ----------------------------------------------------------------- textures
def recolour_tga(source):
    original = stock(source).read_bytes()
    header = struct.unpack_from("<BBBHHBHHHHBB", original)
    idlen, cmap, kind, _, _, _, _, _, width, height, depth, _ = header
    bs.require(cmap == 0 and kind == 2 and depth == 32, f"{source}: expected uncompressed 32-bit TGA")
    start = 18 + idlen
    blob = bytearray(original)
    for i in range(width * height):
        off = start + i * 4  # stored B, G, R, A
        blob[off], blob[off + 1] = original[off + 1], original[off]
    end = start + width * height * 4
    bs.require(blob[:start] == original[:start] and blob[end:] == original[end:] and
               blob[start + 3:end:4] == original[start + 3:end:4], f"{source}: structure or alpha changed")
    return bytes(blob)


def dds_to_tga(source, template):
    image = Image.open(stock(source)).convert("RGBA")
    width, height = image.size
    template_blob = stock(template).read_bytes()
    header = bytearray(template_blob[:18])
    bs.require(header[2] == 2 and header[16] == 32 and header[17] & 0x20 == 0, "Template TGA layout changed")
    struct.pack_into("<HH", header, 12, width, height)
    footer = template_blob[-26:] if template_blob.endswith(b"TRUEVISION-XFILE.\x00") else b""
    pixels = bytearray()
    for y in range(height - 1, -1, -1):  # bottom-left origin, like the stock TGAs
        for x in range(width):
            r, g, b, a = image.getpixel((x, y))
            pixels += bytes((g, b, r, a))  # B, G, R, A with green and blue swapped
    return bytes(header) + bytes(pixels) + footer


def build_assets():
    assets, nif_report = {}, {}
    for _, (source, private, renames, _) in NIFS.items():
        assets[private], nif_report[private] = build_nif(source, renames)
    for private, source in TEXTURES.items():
        assets[private] = (recolour_tga(source) if source.endswith(".tga")
                           else dds_to_tga(source, "plasrng2.tga"))
        decoded = Image.open(io.BytesIO(assets[private]))
        bs.require(decoded.size == Image.open(stock(source)).size, f"{private}: size changed")
    return assets, nif_report


# ------------------------------------------------------------------ catalog
def plan_client():
    name, entries, files, tables = bs.catalogs()
    nifs, effects, spells = tables["spnifs.csv"], tables["speffects.csv"], tables["spells.csv"]
    additions = {"spnifs.csv": [], "speffects.csv": [], "spells.csv": []}
    for ident, (source, private, _, title) in NIFS.items():
        bs.require(str(ident) not in nifs, f"spnifs {ident} already used")
        stock_row = next(r for r in nifs.values() if r[2].strip().lower() == Path(source).stem.lower())
        row = list(stock_row)
        row[:3] = [str(ident), title, Path(private).stem]
        additions["spnifs.csv"].append(row)
    for ident, (source, nif, title) in EFFECT_ROWS.items():
        bs.require(str(ident) not in effects, f"speffects {ident} already used")
        row = list(effects[source])
        row[:3] = [str(ident), title, str(nif)]
        additions["speffects.csv"].append(row)
    for ident, (source, title, columns) in CLIENT_SPELLS.items():
        bs.require(str(ident) not in spells, f"client spell {ident} already used")
        row = list(spells[source])
        row[:2] = [str(ident), title]
        for column, (before, after) in columns.items():
            bs.require(row[column].strip() == before, f"client spell {source} column {column} is not {before}")
            row[column] = after
        additions["spells.csv"].append(row)
    replaced = {}
    for table, rows in additions.items():
        data = files[table]
        for row in rows:
            data = bs.add_row(data, row)
        replaced[table] = data
    new_entries = [archive.Entry(e.name, replaced.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in entries]
    blob = archive.write(name, new_entries)
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    bs.require([e.name for e in decoded] == [e.name for e in entries], "Archive entry order changed")
    for old, new in zip(entries, decoded):
        bs.require((old.timestamp, old.flags) == (new.timestamp, new.flags), "Archive metadata changed")
        added = additions.get(old.name.lower())
        if added is None:
            bs.require(old.data == new.data, f"Unrelated archive entry changed: {old.name}")
        else:
            rows = bs.rows_of(new.data)
            bs.require(all(r in rows for r in added), f"New rows missing from {old.name}")
            bs.require([r for r in rows if r not in added] == bs.rows_of(old.data), f"Stock row changed in {old.name}")
    return blob, additions


def catalog_installed():
    _, _, _, tables = bs.catalogs()
    return (all(str(i) in tables["spnifs.csv"] for i in NIFS) and
            all(str(i) in tables["speffects.csv"] for i in EFFECT_ROWS) and
            all(str(i) in tables["spells.csv"] for i in CLIENT_SPELLS))


# ----------------------------------------------------------------- database
def plan_database(con):
    spells = bs.spell_snapshot(con)
    updates = {}
    for ident, (old, new) in SPELLS.items():
        current = spells[ident]["ClientEffect"]
        bs.require(current in (old, new), f"{ident} {spells[ident]['Name']} animation is {current}, expected {old}")
        if current != new:
            updates[ident] = new
    used = {r["ClientEffect"] for i, r in spells.items() if i not in SPELLS}
    bs.require(SELF_ID not in used and PET_ID not in used, "Private client spell IDs already used by another spell")
    return spells, updates


def check_database(before, after, updates):
    bs.require(before.keys() == after.keys(), "Spell rows added or removed")
    for ident, row in before.items():
        expected = dict(row)
        if ident in updates:
            expected["ClientEffect"] = updates[ident]
        bs.require(after[ident] == expected, f"Unexpected change to spell {ident}")


# ------------------------------------------------------------------ preview
def contact_sheet(assets):
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (760, 120 + 150 * len(TEXTURES)), (19, 20, 19))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((20, 14), "Cairn strength buff: stock blue (left) -> private green (right)", font=font, fill="white")
    for row, (private, source) in enumerate(TEXTURES.items()):
        top = 60 + row * 150
        draw.text((20, top), f"{source}  ->  {private}", font=small, fill=(210, 220, 210))
        for column, data in enumerate((stock(source).read_bytes(), assets[private])):
            image = Image.open(io.BytesIO(data)).convert("RGBA")
            scale = 120 / max(image.size)
            image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                                 Image.Resampling.NEAREST)
            tile = Image.new("RGBA", (130, 125), (30, 30, 30, 255))
            tile.alpha_composite(image, (5, 2))
            sheet.paste(tile.convert("RGB"), (20 + column * 160, top + 20))
    path = OUT / "cairn_green_textures.png"
    sheet.save(path)
    return path


def preview():
    assets, report = build_assets()
    blob, additions = plan_client() if not catalog_installed() else (None, {})
    with bs.read_db() as con:
        spells, updates = plan_database(con)
    sheet = contact_sheet(assets)
    for private, edits in report.items():
        kinds = {}
        for edit in edits:
            kinds[edit["kind"]] = kinds.get(edit["kind"], 0) + 1
        print(f"  {private}: {kinds}")
    for table, rows in additions.items():
        print(f"  {table}: " + ", ".join(f"{r[0]} {r[1]}" for r in rows))
    for ident, new in updates.items():
        print(f"  {ident} {spells[ident]['Name']}: ClientEffect {spells[ident]['ClientEffect']} -> {new}")
    print(f"Texture preview: {sheet}")
    print("Preview only. Run with 'install' to apply." if blob or updates else "Already installed.")


# ------------------------------------------------------------------ install
def install():
    bs.stopped()
    assets, _ = build_assets()
    game = CLIENT / "gamedata.mpk"
    installed_catalog = catalog_installed()
    blob = None if installed_catalog else plan_client()[0]
    with bs.read_db() as con:
        before, updates = plan_database(con)
    for name, data in assets.items():
        path = EFFECTS / name
        bs.require(not path.exists() or bs.file_sha(path) == bs.sha(data), f"{name} exists with other content")
    if installed_catalog and not updates and all((EFFECTS / n).exists() for n in assets):
        print("Already installed; no changes made.")
        return
    backup = HERE / "install-backups" / ("cairn-green-buff-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(game, backup / "gamedata.mpk")
    with bs.db_session(DB) as con, bs.db_session(backup / "opendaoc.sqlite3.db") as destination:
        con.backup(destination)
        bs.require(destination.execute("PRAGMA quick_check").fetchone()[0] == "ok", "DB backup invalid")
    manifest = {"created": datetime.now().astimezone().isoformat(),
                "gamedata": {"before": bs.file_sha(game), "after": bs.sha(blob) if blob else bs.file_sha(game)},
                "new_files": {n: bs.sha(d) for n, d in assets.items() if not (EFFECTS / n).exists()},
                "updated": {str(i): before[i]["ClientEffect"] for i in updates}}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for name, data in assets.items():
        if not (EFFECTS / name).exists():
            bs.atomic_write(EFFECTS / name, data)
    if blob:
        bs.atomic_write(game, blob)
    with bs.db_session(DB) as con:
        con.row_factory = sqlite3.Row
        con.executemany("UPDATE Spell SET ClientEffect=? WHERE SpellID=?", [(v, i) for i, v in updates.items()])
        check_database(before, bs.spell_snapshot(con), updates)
        bs.require(con.execute("PRAGMA quick_check").fetchone()[0] == "ok", "DB quick_check failed")
    bs.require(bs.file_sha(game) == manifest["gamedata"]["after"], "Installed catalog differs")
    print(f'Installed. Rollback with:\n  python -B "{Path(__file__).resolve()}" rollback "{backup}"')


def rollback(folder: Path):
    bs.stopped()
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    game = CLIENT / "gamedata.mpk"
    bs.require(bs.file_sha(game) in (m["gamedata"]["before"], m["gamedata"]["after"]),
               "Later catalog changes detected; refuse to overwrite them")
    bs.atomic_write(game, (folder / "gamedata.mpk").read_bytes())
    for name, digest in m["new_files"].items():
        bs.require(name in PRIVATE_FILES, "Unsafe rollback filename")
        path = EFFECTS / name
        if path.exists() and bs.file_sha(path) == digest:
            path.unlink()
    with bs.db_session(DB) as con:
        con.executemany("UPDATE Spell SET ClientEffect=? WHERE SpellID=?",
                        [(old, int(i)) for i, old in m["updated"].items()])
    print("Rolled back.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if command == "install":
        install()
    elif command == "rollback" and len(sys.argv) > 2:
        rollback(Path(sys.argv[2]))
    else:
        preview()
