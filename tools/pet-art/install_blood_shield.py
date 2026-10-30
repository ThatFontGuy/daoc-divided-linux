"""Sluagh Blood Shield: preparation first, never install by default.

Owner requested DRAFT ONLY for Claude's independent review. `prepare` writes
only work/blood-shield-review. No client/database activation is authorized yet.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import struct
import sys
import shutil
import subprocess
import tempfile
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLIENT = ROOT / "runtime/client-opendaoc/app"
EFFECTS = CLIENT / "effects"
DB = ROOT / "runtime/data/opendaoc.sqlite3.db"
OUT = HERE / "work/blood-shield-review"
sys.path.insert(0, str(HERE))

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from daoc_catalog import archive

SCOPED = (59024, 59025, 59026, 59032, 59050, 59051, 59052, 59053, 59054)
EXPECTED = {59024: 1701, 59025: 1704, 59026: 1706, 59032: 3154,
            59050: 3154, 59051: 3154, 59052: 3154, 59053: 3154, 59054: 3154}
SOURCE_NIF = "alb_eshield1_hit.NIF"
PRIVATE_NIF = "slu_bldshld_hit.NIF"
RENAMES = {b"amethmap.tga": b"slbldmap.tga", b"prpspike.tga": b"slbspike.tga"}
SPNIF_ID, EFFECT_ID, CLIENT_ID = 1405, 632, 4569
PRIVATE_FILES = (PRIVATE_NIF, "slbldmap.tga", "slbspike.tga")


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


@contextmanager
def read_db():
    con = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


@contextmanager
def db_session(path):
    con = sqlite3.connect(path)
    try:
        with con:
            yield con
    finally:
        con.close()


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def rows_of(data):
    return list(csv.reader(io.StringIO(data.decode("latin1"))))


def catalogs():
    name, entries = archive.read((CLIENT / "gamedata.mpk").read_bytes())
    files = {e.name.lower(): e.data for e in entries}
    tables = {n: {r[0]: r for r in rows_of(files[n]) if r and r[0].strip().isdigit()}
              for n in ("spells.csv", "spnifs.csv", "speffects.csv")}
    return name, entries, files, tables


def inspect():
    _, _, files, tables = catalogs()
    facts = {"created": datetime.now().astimezone().isoformat(), "catalogs": {}}
    wanted = {"spells.csv": (2, 1701, 1704, 1706, 3154, 4561, 4765),
              "speffects.csv": (191, 471, 472, 632), "spnifs.csv": (182, 1405)}
    for table, ids in wanted.items():
        facts["catalogs"][table] = {"headers": rows_of(files[table])[:2],
            "max_id": max(map(int, tables[table])), "rows": {str(i): tables[table].get(str(i)) for i in ids}}
    with read_db() as con:
        facts["spells"] = [dict(r) for r in con.execute(
            "SELECT * FROM Spell WHERE SpellID IN (" + ",".join("?" for _ in (2, *SCOPED)) + ")", (2, *SCOPED))]
        schemas = {row[0]: [dict(r) for r in con.execute("PRAGMA table_info("+quote(row[0])+")")]
                   for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        facts["related_schemas"] = {t: cols for t, cols in schemas.items() if
            any("spell" in c["name"].lower() for c in cols) or t == "NpcTemplate"}
        refs = []
        id_strings = set(map(str, SCOPED))
        for table, cols in schemas.items():
            relevant = [c["name"] for c in cols if "spell" in c["name"].lower()
                        and not (table == "Spell" and c["name"].lower() == "spellid")]
            for col in relevant:
                for row in con.execute("SELECT * FROM "+quote(table)+" WHERE "+quote(col)+" IS NOT NULL"):
                    value = str(row[col])
                    matched = sorted(id_strings.intersection(re.findall(r"\d+", value)), key=int)
                    if matched:
                        refs.append({"table": table, "column": col, "matches": matched, "row": dict(row)})
        facts["references"] = refs
        facts["pet_templates"] = [dict(r) for r in con.execute("SELECT * FROM NpcTemplate WHERE TemplateId IN (30000,60170005,60170007)")]
    source = (EFFECTS / SOURCE_NIF).read_bytes()
    needles = (b"amethmap.tga", b"prpspike.tga", b"black.tga", b"alb_eshield1_hit",
               b"NiMaterialProperty", b"NiSourceTexture")
    facts["nif"] = {"bytes": len(source), "sha256": sha(source), "header": repr(source[:60]),
        "strings": {n.decode(): {"count": source.count(n), "offsets": [m.start() for m in re.finditer(re.escape(n), source)]}
                    for n in needles}}
    textures = {}
    for name in ("amethmap", "prpspike"):
        for path in sorted(EFFECTS.glob(name + ".*")):
            image = Image.open(path)
            textures[path.name] = {"size": list(image.size), "mode": image.mode,
                                  "info": image.info, "bytes": path.stat().st_size,
                                  "sha256": sha(path.read_bytes())}
    facts["textures"] = textures
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "inspection.json").write_text(json.dumps(facts, indent=2, default=str)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in facts.items() if k not in ("related_schemas", "references", "pet_templates")},
                     indent=2, default=str))
    print("REFERENCES", json.dumps(refs, indent=2, default=str))
    return facts


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def effect_inventory():
    return {str(p.relative_to(EFFECTS)).replace("\\", "/"): file_sha(p)
            for p in sorted(EFFECTS.rglob("*")) if p.is_file()}


def materials(blob):
    result = []
    for match in re.finditer(b"NiMaterialProperty", blob):
        off = match.start()
        require(struct.unpack_from("<I", blob, off - 4)[0] == 18, "Material type length mismatch")
        cursor = off + 18
        name_length = struct.unpack_from("<I", blob, cursor)[0]
        require(name_length < 256, "Unexpected material name length")
        cursor += 4 + name_length
        extra, controller, flags = struct.unpack_from("<iiH", blob, cursor)
        cursor += 10
        values = list(struct.unpack_from("<14f", blob, cursor))
        end = cursor + 56
        next_length = struct.unpack_from("<I", blob, end)[0]
        require(2 <= next_length <= 80 and blob[end + 4:end + 6] == b"Ni",
                "Material boundary does not end at next named NIF block")
        result.append({"type_offset": off, "float_offset": cursor, "flags": flags,
                       "extra": extra, "controller": controller, "values": values})
    require(len(result) == 5, "Expected five source materials")
    return result


def build_nif():
    original = (EFFECTS / SOURCE_NIF).read_bytes()
    require(original.startswith(b"NetImmerse File Format, Version 4.1.0.12\n"), "Unexpected NIF version")
    blob = bytearray(original)
    edits = []
    for before, after in RENAMES.items():
        require(len(before) == len(after) and original.count(before) == 1,
                "Texture reference count/length changed")
        off = original.index(before)
        blob[off:off + len(before)] = after
        edits.append({"kind": "texture_name", "offset": off,
                      "before_hex": before.hex(), "after_hex": after.hex()})
    # The source has THREE purple AMBIENT triples, not purple diffuse/emissive.
    # Recolour those in the private copy as well; white diffuse/emissive and
    # all controllers, opacity, geometry and black.tga stay byte-identical.
    for material in materials(original):
        for name, index in (("ambient", 0), ("diffuse", 3), ("emissive", 9)):
            rgb = material["values"][index:index + 3]
            if rgb[0] > rgb[1] * 1.5 and rgb[2] > rgb[1] * 1.5:
                off = material["float_offset"] + index * 4
                new = (rgb[0], rgb[0] * 0.08, rgb[0] * 0.10)
                before, after = original[off:off + 12], struct.pack("<3f", *new)
                blob[off:off + 12] = after
                edits.append({"kind": "material_" + name, "offset": off,
                              "before_rgb": rgb, "after_rgb": list(new),
                              "before_hex": before.hex(), "after_hex": after.hex()})
    restored = bytearray(blob)
    for edit in edits:
        off, before = edit["offset"], bytes.fromhex(edit["before_hex"])
        restored[off:off + len(before)] = before
    require(bytes(restored) == original and len(blob) == len(original), "NIF reversible-byte audit failed")
    require(bytes(blob).count(b"black.tga") == original.count(b"black.tga") == 1, "Shared black texture changed")
    return bytes(blob), {"source_sha256": sha(original), "private_sha256": sha(blob),
                         "size": len(blob), "patches": edits, "reversal_byte_identical": True,
                         "materials_before": materials(original), "materials_after": materials(blob)}


def recolour_tga(filename):
    original = (EFFECTS / filename).read_bytes()
    blob = bytearray(original)
    image = Image.open(io.BytesIO(original)).convert("RGBA")
    # Edit native TGA palette/pixels in place rather than re-encoding. Keep
    # legacy format, indices, orientation, alpha, header and footer exactly.
    header = struct.unpack_from("<BBBHHBHHHHBB", blob)
    idlen, cmap, kind, first, count, bits, _, _, width, height, depth, _ = header
    start = 18 + idlen
    if filename == "amethmap.tga":
        require(cmap == 1 and kind == 1 and bits == 24 and depth == 8 and (width, height) == (64, 64),
                "Expected uncompressed 24-bit-palette environment TGA")
        for i in range(count):
            off = start + i * 3
            blue, green, red = blob[off:off + 3]
            # Keep highlight/shadow structure without purple colour bleed.
            luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
            sheen = luminance ** 0.90
            rgb = (round(2 + 88 * sheen), round(1 + 9 * sheen), round(1 + 12 * sheen))
            blob[off:off + 3] = bytes(reversed(rgb))
        change_range = (start, start + count * 3)
    else:
        require(cmap == 0 and kind == 2 and depth == 32 and (width, height) == (32, 32),
                "Expected uncompressed RGBA spike TGA")
        for i in range(width * height):
            off = start + i * 4
            blue, green, red, alpha = blob[off:off + 4]
            strength = max(red, green, blue) / 255
            rgb = (round(120 + 50 * strength), round(10 + 15 * strength), round(10 + 15 * strength))
            blob[off:off + 3] = bytes(reversed(rgb))
        change_range = (start, start + width * height * 4)
    after = Image.open(io.BytesIO(blob)).convert("RGBA")
    require(np.array_equal(np.asarray(image)[:, :, 3], np.asarray(after)[:, :, 3]), "Texture alpha changed")
    lo, hi = change_range
    require(blob[:lo] == original[:lo] and blob[hi:] == original[hi:] and len(blob) == len(original),
            "TGA structure outside permitted colour bytes changed")
    if filename == "prpspike.tga":
        require(blob[lo + 3:hi:4] == original[lo + 3:hi:4], "Raw TGA alpha changed")
    return bytes(blob), {"source_sha256": sha(original), "private_sha256": sha(blob),
                         "alpha_identical": True, "format_and_length_preserved": True,
                         "colour_byte_range": [lo, hi], "palette_first_index": first}


def preview(assets):
    sheet = Image.new("RGB", (820, 510), (19, 18, 20))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 19)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    draw.text((20, 12), "Sluagh Blood Shield - TEXTURE DRAFT ONLY / NOT INSTALLED", font=font, fill="white")
    draw.text((20, 44), "Stock purple                         Private black / blood red", font=small, fill=(205, 200, 200))
    for row, (src, dst, title) in enumerate((
            ("amethmap.tga", "slbldmap.tga", "Environment sheen - palette structure preserved"),
            ("prpspike.tga", "slbspike.tga", "Shield spikes - original alpha preserved"))):
        top = 86 + row * 206
        draw.text((20, top - 18), title, font=small, fill=(225, 218, 218))
        tiles = []
        for column, data in enumerate(((EFFECTS / src).read_bytes(), assets[dst])):
            img = Image.open(io.BytesIO(data)).convert("RGBA").resize((170, 170), Image.Resampling.NEAREST)
            tile = Image.new("RGBA", (170, 170), (25, 25, 27, 255))
            # Checkerboard makes transparency visible; retain a black version too.
            if row == 1:
                d = ImageDraw.Draw(tile)
                for yy in range(0, 170, 17):
                    for xx in range(0, 170, 17):
                        if (xx // 17 + yy // 17) % 2:
                            d.rectangle((xx, yy, xx + 16, yy + 16), fill=(53, 50, 51, 255))
            tile.alpha_composite(img)
            sheet.paste(tile.convert("RGB"), (20 + column * 230, top))
            tiles.append(tile)
        swatch = Image.new("RGB", (350, 170), (19, 18, 20))
        for i, tile in enumerate(tiles):
            swatch.paste(tile.convert("RGB"), (i * 180, 0))
        swatch.save(OUT / (src.removesuffix(".tga") + "_before_after.png"))
    draw.text((20, 484), "Swatches do not prove the final in-game particle appearance. Claude must review before install.",
              font=small, fill=(200, 190, 190))
    for i, note in enumerate(("PLANNED PRIVATE EFFECT", "spnifs 1405 / speffects 632", "client spell 4569 (4561 is occupied)",
                              "Stock red hand glows: 471 / 472", "No buildup halo / no visual pulse", "Nine armor-buff ClientEffect fields",
                              "", "Preserved:", "- original shield effect and textures", "- texture alpha / legacy TGA formats",
                              "- NIF geometry and controllers", "- server spell icons and mechanics", "", "Animation set needs Claude review.",
                              "No game assets installed.")):
        draw.text((480, 86 + i * 23), note, font=small, fill=(210, 200, 200))
    sheet.save(OUT / "blood_shield_contact_sheet.png")


def line_of(row):
    stream = io.StringIO()
    csv.writer(stream, lineterminator="").writerow(row)
    return stream.getvalue()


def add_row(data, row):
    # Insert an ADDITION in numeric position before the 14999 sentinel;
    # no original line is reserialized, changed, removed or reordered.
    lines = data.decode("latin1").split("\r\n")
    numeric = [(i, int(line.split(",", 1)[0].strip())) for i, line in enumerate(lines)
               if line.split(",", 1)[0].strip().isdigit()]
    require(not any(n == int(row[0]) for _, n in numeric), "Catalog ID already occupied")
    before = next((i for i, n in numeric if n > int(row[0])), numeric[-1][0] + 1)
    addition = line_of(row)
    updated = lines[:before] + [addition] + lines[before:]
    require(updated[:before] + updated[before + 1:] == lines, "Original catalog lines changed")
    return "\r\n".join(updated).encode("latin1")


def catalog_draft(animation):
    name, entries, files, tables = catalogs()
    require(str(SPNIF_ID) not in tables["spnifs.csv"] and str(EFFECT_ID) not in tables["speffects.csv"]
            and str(CLIENT_ID) not in tables["spells.csv"], "Reserved draft IDs were taken; re-review needed")
    nif = list(tables["spnifs.csv"]["182"])
    nif[:3] = [str(SPNIF_ID), "Sluagh Blood Shield", Path(PRIVATE_NIF).stem]
    effect = list(tables["speffects.csv"]["191"])
    effect[:4] = [str(EFFECT_ID), "Sluagh Blood Shield", str(SPNIF_ID), "rootnode"]
    spell = list(tables["spells.csv"]["2"])
    spell[0:2] = [str(CLIENT_ID), "Sluagh Blood Shield"]
    spell[3:6] = list(map(str, (animation, animation + 1, animation + 2)))
    spell[6:8] = ["471", "472"]
    spell[11:14] = [str(EFFECT_ID), "0", "0"]
    additions = {"spnifs.csv": nif, "speffects.csv": effect, "spells.csv": spell}
    updates = {key: add_row(files[key], row) for key, row in additions.items()}
    new_entries = [archive.Entry(e.name, updates.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in entries]
    blob = archive.write(name, new_entries)
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    require([e.name for e in decoded] == [e.name for e in entries], "Archive entry names/order changed")
    for old, new in zip(entries, decoded):
        require((old.timestamp, old.flags) == (new.timestamp, new.flags), "Archive entry metadata changed")
        if old.name.lower() not in updates:
            require(old.data == new.data, "Unrelated archive entry changed")
        else:
            old_rows, new_rows = rows_of(old.data), rows_of(new.data)
            matching = [r for r in new_rows if r and r[0] == additions[old.name.lower()][0]]
            require(matching == [additions[old.name.lower()]], "New catalog row mismatch")
            require([r for r in new_rows if r not in matching] == old_rows, "Stock row changed")
    return blob, additions, len(entries)


def spell_snapshot(con):
    return {int(r["SpellID"]): dict(r) for r in con.execute("SELECT * FROM Spell ORDER BY SpellID")}


def assert_spell_delta(before, after, effects):
    require(before.keys() == after.keys(), "Spell definitions added/removed")
    for ident, row in before.items():
        expected = dict(row)
        if ident in effects:
            expected["ClientEffect"] = effects[ident]
        require(after[ident] == expected, f"Unexpected spell change {ident}")


def assert_references():
    facts = json.loads((OUT / "inspection.json").read_text(encoding="utf-8"))
    for ref in facts["references"]:
        table, col, row = ref["table"], ref["column"], ref["row"]
        if table == "Spell" and col == "Spell_ID" and int(row["SpellID"]) in SCOPED:
            continue
        if table == "LineXSpell" and col in ("SpellID", "LineXSpell_ID"):
            require(row["LineName"] in ("Cairn Oath", "Sluagh Covenant", "Dullahan's Bulwark"),
                    "Spell reused by outside spell line")
            continue
        if table == "NpcTemplate" and col == "Spells":
            require(int(row["TemplateId"]) in (60170005, 60170007) and ref["matches"] == ["59032"],
                    "Spell reused by an unrelated NPC")
            continue
        raise RuntimeError("Unexpected spell reference requires Claude review: " + json.dumps(ref))
    with read_db() as con:
        require(not con.execute("SELECT 1 FROM Mob WHERE NPCTemplateID IN (60170005,60170007)").fetchone(),
                "Pet template also used by world NPC")
        require(not con.execute("SELECT 1 FROM Spell WHERE ClientEffect=? OR Icon=?", (CLIENT_ID, CLIENT_ID)).fetchone(),
                "Client ID already referenced by database")
        require(not con.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND lower(tbl_name)='spell'").fetchone(),
                "Spell UPDATE has triggers requiring review")
        lines = con.execute("SELECT KeyName,ClassIDHint FROM SpellLine WHERE KeyName IN (?,?,?)",
                            ("Cairn Oath", "Sluagh Covenant", "Dullahan's Bulwark")).fetchall()
        require(len(lines) == 3 and all(r["ClassIDHint"] == 63 for r in lines), "Unexpected class ownership")


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    effects_before = effect_inventory()
    game_before, db_before = file_sha(CLIENT / "gamedata.mpk"), file_sha(DB)
    print("Reading references and preparing PRIVATE REVIEW FILES only...", flush=True)
    # Inspection is always refreshed; never trust an earlier DB reference scan.
    with io.StringIO() as sink:
        from contextlib import redirect_stdout
        with redirect_stdout(sink):
            inspect()
    assert_references()
    with read_db() as con:
        before = spell_snapshot(con)
        require(all(before[i]["ClientEffect"] == EXPECTED[i] for i in SCOPED), "Live spell baseline differs")
        schema = con.execute("SELECT sql FROM sqlite_master WHERE name='Spell'").fetchone()[0]
    assets, checks = {}, {}
    assets[PRIVATE_NIF], checks[PRIVATE_NIF] = build_nif()
    for source, target in (("amethmap.tga", "slbldmap.tga"), ("prpspike.tga", "slbspike.tga")):
        assets[target], checks[target] = recolour_tga(source)
    for filename, blob in assets.items():
        require(not (EFFECTS / filename).exists(), "Private destination already exists")
        (OUT / filename).write_bytes(blob)
    preview(assets)
    # Both alternatives are uninstalled. ONE row is used in either alternative.
    choices = {}
    for animation in (32, 35):
        blob, additions, count = catalog_draft(animation)
        filename = f"gamedata.animation-{animation}.mpk"
        (OUT / filename).write_bytes(blob)
        choices[str(animation)] = {"file": filename, "sha256": sha(blob), "new_rows": additions}
    # Run the exact planned DB UPDATE twice, then reverse it, on an in-memory
    # copy of Spell ONLY. All other spell rows/columns must remain identical.
    memory = sqlite3.connect(":memory:")
    memory.row_factory = sqlite3.Row
    memory.execute(schema)
    columns = list(next(iter(before.values())))
    memory.executemany("INSERT INTO Spell (" + ",".join(map(quote, columns)) + ") VALUES (" +
                       ",".join("?" for _ in columns) + ")", [tuple(r[c] for c in columns) for r in before.values()])
    for _ in range(2):
        memory.executemany("UPDATE Spell SET ClientEffect=? WHERE SpellID=?", [(CLIENT_ID, i) for i in SCOPED])
        assert_spell_delta(before, spell_snapshot(memory), {i: CLIENT_ID for i in SCOPED})
    memory.executemany("UPDATE Spell SET ClientEffect=? WHERE SpellID=?", [(EXPECTED[i], i) for i in SCOPED])
    require(spell_snapshot(memory) == before, "In-memory rollback differs")
    memory.close()
    require(effect_inventory() == effects_before, "Live effect directory changed during prepare")
    require(file_sha(CLIENT / "gamedata.mpk") == game_before and file_sha(DB) == db_before,
            "Live DB/client changed concurrently; do not use this review")
    manifest = {"created": datetime.now().astimezone().isoformat(), "status": "DRAFT ONLY - NOT INSTALLED",
        "root": str(ROOT), "ids": {"spnif": SPNIF_ID, "speffect": EFFECT_ID, "client_spell": CLIENT_ID},
        "baseline_gamedata_sha256": game_before, "baseline_db_sha256": db_before,
        "baseline_effects": effects_before, "spell_baselines": {str(i): before[i] for i in SCOPED},
        "assets": {n: {"sha256": sha(b), "checks": checks[n]} for n, b in assets.items()},
        "animation_choices": choices, "verification": {"stock_archive_entries": count,
        "stock_rows_byte_identical": True, "unrelated_entries_byte_identical": True,
        "nif_reversible_byte_copy": True, "texture_alpha_identical": True,
        "db_update_idempotent_in_memory": True, "db_rollback_exact_in_memory": True,
        "spell_definitions_checked": len(before), "live_files_unchanged": True,
        "effect_files_checked": len(effects_before)}}
    (OUT / "review_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"draft": str(OUT), "ids": manifest["ids"], "verification": manifest["verification"]}, indent=2))
    print("NOT INSTALLED. Animation choice and owner approval required before Claude runs install.")


def stopped():
    require(sys.platform == "win32", "Process guard currently supports Windows only")
    result = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process | Select-Object Name,ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    processes = json.loads(result.stdout or "[]")
    if isinstance(processes, dict):
        processes = [processes]
    blockers = []
    for p in processes:
        name = (p.get("Name") or "").lower()
        command = (p.get("CommandLine") or "").lower()
        if name in ("offlinedaoc.exe", "gameserver.exe", "dolserver.exe", "camelot.exe", "game.dll", "daoc.exe") or (
                "gameserver.dll" in command and name in ("dotnet.exe", "gameserver.exe")) or (
                ("launcher.py" in command or "launcher.pyw" in command) and str(ROOT).lower() in command):
            blockers.append(p)
    require(not blockers, "Close client, server and launcher first: " + json.dumps(blockers))


def atomic_write(path, blob):
    # Write in the same directory, then atomically replace the exact target.
    with tempfile.NamedTemporaryFile(prefix="blood-shield-", suffix=".tmp", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(blob)
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def rollback(folder):
    stopped()
    folder = folder.resolve()
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    require(m["root"] == str(ROOT), "Backup belongs to another installation")
    game = CLIENT / "gamedata.mpk"
    require(file_sha(game) in (m["before_gamedata_sha256"], m["after_gamedata_sha256"]),
            "Later catalog changes detected; refuse to overwrite them")
    require(file_sha(folder / "gamedata.mpk") == m["before_gamedata_sha256"], "Catalog backup corrupted")
    for filename, expected_hash in m["new_files"].items():
        require(filename in PRIVATE_FILES, "Unsafe rollback filename")
        path = EFFECTS / filename
        require(not path.exists() or file_sha(path) == expected_hash, "Private asset changed since install")
    existing_stock = effect_inventory()
    for filename in PRIVATE_FILES:
        existing_stock.pop(filename, None)
    require(existing_stock == m["stock_effects"], "Other effect changes detected; refuse stale rollback")
    with db_session(DB) as con:
        con.row_factory = sqlite3.Row
        before = spell_snapshot(con)
        require(all(before[i]["ClientEffect"] in (EXPECTED[i], CLIENT_ID) for i in SCOPED),
                "Later DB effect changes detected")
        con.executemany("UPDATE Spell SET ClientEffect=? WHERE SpellID=?", [(EXPECTED[i], i) for i in SCOPED])
        assert_spell_delta(before, spell_snapshot(con), EXPECTED)
    atomic_write(game, (folder / "gamedata.mpk").read_bytes())
    for filename in m["new_files"]:
        path = EFFECTS / filename
        if path.exists():
            path.unlink()
    require(effect_inventory() == m["stock_effects"], "Stock effects differ; investigate separately")
    require(file_sha(game) == m["before_gamedata_sha256"], "Rollback catalog mismatch")
    print("Rolled back nine ClientEffect fields and private assets. Unrelated DB progress retained. Backup kept:", folder)


def install(animation):
    stopped()
    m = json.loads((OUT / "review_manifest.json").read_text(encoding="utf-8"))
    require(m["root"] == str(ROOT), "Review belongs to another installation")
    choice = m["animation_choices"][str(animation)]
    game, blob = CLIENT / "gamedata.mpk", (OUT / choice["file"]).read_bytes()
    require(sha(blob) == choice["sha256"], "Draft catalog changed after review")
    for filename, info in m["assets"].items():
        require(filename in PRIVATE_FILES and file_sha(OUT / filename) == info["sha256"], "Draft asset changed")
    with read_db() as con:
        before = spell_snapshot(con)
    if file_sha(game) == choice["sha256"] and all(before[i]["ClientEffect"] == CLIENT_ID for i in SCOPED):
        require(all((EFFECTS / n).exists() and file_sha(EFFECTS / n) == v["sha256"] for n, v in m["assets"].items()),
                "Installed private assets do not match")
        actual = effect_inventory()
        for n in PRIVATE_FILES:
            actual.pop(n)
        require(actual == m["baseline_effects"], "Installed stock effects differ")
        print("Already installed exactly; no changes made.")
        return
    require(file_sha(game) == m["baseline_gamedata_sha256"] and effect_inventory() == m["baseline_effects"],
            "Live client baseline changed; regenerate/review the draft")
    require(all(before[i] == m["spell_baselines"][str(i)] for i in SCOPED), "Scoped spell definition changed since review")
    require(all(not (EFFECTS / n).exists() for n in PRIVATE_FILES), "Private asset already exists")
    # Revalidate fresh references now, not only the earlier preparation scan.
    with io.StringIO() as sink:
        from contextlib import redirect_stdout
        with redirect_stdout(sink):
            inspect()
    assert_references()
    backup = HERE / "install-backups" / ("blood-shield-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup.mkdir(parents=True)
    shutil.copy2(game, backup / "gamedata.mpk")
    with db_session(DB) as con, db_session(backup / "opendaoc.sqlite3.db") as destination:
        con.backup(destination)
        require(destination.execute("PRAGMA quick_check").fetchone()[0] == "ok", "DB backup invalid")
    incoming = backup / "incoming-private-assets"
    incoming.mkdir()
    for filename in PRIVATE_FILES:
        shutil.copy2(OUT / filename, incoming / filename)
    record = {"root": str(ROOT), "created": datetime.now().astimezone().isoformat(), "animation": animation,
              "before_gamedata_sha256": file_sha(game), "after_gamedata_sha256": sha(blob),
              "backup_db_sha256": file_sha(backup / "opendaoc.sqlite3.db"),
              "old_effects": EXPECTED, "new_files": {n: m["assets"][n]["sha256"] for n in PRIVATE_FILES},
              "stock_effects": m["baseline_effects"], "private_files_previously_absent": True}
    (backup / "manifest.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    try:
        for filename in PRIVATE_FILES:
            atomic_write(EFFECTS / filename, (OUT / filename).read_bytes())
        atomic_write(game, blob)
        with db_session(DB) as con:
            con.row_factory = sqlite3.Row
            current = spell_snapshot(con)
            require(current == before, "Spell DB changed during install")
            con.executemany("UPDATE Spell SET ClientEffect=? WHERE SpellID=?", [(CLIENT_ID, i) for i in SCOPED])
            assert_spell_delta(before, spell_snapshot(con), {i: CLIENT_ID for i in SCOPED})
        after_effects = effect_inventory()
        for n in PRIVATE_FILES:
            require(after_effects.pop(n) == m["assets"][n]["sha256"], "Installed private asset differs")
        require(after_effects == m["baseline_effects"], "Stock effect file changed")
        require(file_sha(game) == choice["sha256"], "Installed catalog differs")
        record["after_db_sha256"] = file_sha(DB)
        record["verified"] = True
        (backup / "manifest.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    except Exception:
        print("Install did not finish. Exact guarded recovery command:", flush=True)
        print(f'& "{sys.executable}" -B "{Path(__file__).resolve()}" rollback "{backup}" --approve-install', flush=True)
        raise
    print("Installed private shield visuals only. Existing Icon and all other DB columns preserved.")
    print(f'Rollback:\n& "{sys.executable}" -B "{Path(__file__).resolve()}" rollback "{backup}" --approve-install')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "prepare", "install", "rollback"), nargs="?", default="prepare")
    parser.add_argument("backup", nargs="?", type=Path)
    parser.add_argument("--approve-install", action="store_true", help="Explicit future owner approval; NOT authorized by this task")
    parser.add_argument("--animation", type=int, choices=(32, 35), help="Claude must review the ONE-row animation compromise")
    args = parser.parse_args()
    if args.mode == "inspect":
        inspect()
    elif args.mode == "prepare":
        prepare()
    else:
        require(args.approve_install, "DRAFT ONLY. Future explicit owner approval required before live writes.")
        if args.mode == "install":
            require(args.animation is not None, "Explicit animation review/choice required (32 or 35)")
            install(args.animation)
        else:
            require(args.backup is not None, "Exact backup directory required")
            rollback(args.backup)
