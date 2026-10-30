"""Zombie Magician: black-purple "Sun Blast" nuke + zombie body with the caster cast.

  install : python install_void_sun.py install
  rollback: python install_void_sun.py rollback <backup-folder>

Everything here is PRIVATE to the Zombie Magician; no stock spell, effect,
texture or animation set is changed.

Client (CLAUDE VERSION only):
  effects\\  q*.dds / q*.tga            recoloured copies of the Sun Blast textures
  effects\\  slu_mana_sum.NIF, slu_mbeam4_cst.NIF, slu_mexplo4_hit.NIF
             byte copies of hib_mana_sum / hib_mbeam4_cst / hib_mexplo4_hit
             whose texture names point at the q* copies (same-length rename)
  gamedata.mpk
    spnifs.csv   1402-1404  the three private effect NIFs
    speffects.csv 628-631   hand glow L/R, hand burst, target explosion
    spells.csv   4560       "Sluagh Void Blast" (copy of Sun Blast 4109)
    anims.csv    434        undead anim set 46, with the caster cast slots
                            50-52 taken from the Celt/Elf male set 48 (the same
                            H_ElfMon01 mesh already uses set 48 as the stock
                            "Sea Elf/Wood Elf Male", so the skeleton matches)
    monnifs.csv  990        Zombie Magician private NIF row: anim set 46 -> 434
Server:
  Spell 59031 (Rotting Gloom Blast) ClientEffect -> 4560. Damage, type,
  target, range and cast time are unchanged.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import sqlite3
import struct
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLIENT = ROOT / "runtime" / "client-opendaoc" / "app"
EFFECTS = CLIENT / "effects"
DB = ROOT / "runtime" / "data" / "opendaoc.sqlite3.db"
sys.path.insert(0, str(HERE))
from daoc_catalog import archive  # noqa: E402

TEXTURES = ["elecglow", "whtheat2", "orncomet", "orncore", "ornflare", "orniris",
            "blufl04", "blufl06", "blufl08", "blufl10", "hotring"]
NIFS = {"hib_mana_sum": "slu_mana_sum", "hib_mbeam4_cst": "slu_mbeam4_cst", "hib_mexplo4_hit": "slu_mexplo4_hit"}
SPNIF = {"slu_mana_sum": ("1402", "209"), "slu_mbeam4_cst": ("1403", "237"), "slu_mexplo4_hit": ("1404", "197")}
SPEFFECT = [("628", "218", "1402", "Sluagh void handglow left"),
            ("629", "219", "1402", "Sluagh void handglow right"),
            ("630", "247", "1403", "Sluagh void hand burst"),
            ("631", "206", "1404", "Sluagh void explosion")]
SPELL_ROW = ("4560", "4109", "Sluagh Void Blast")
ANIM_SET = ("434", "46", "48", (50, 51, 52))
MAGICIAN_NIF_ROW = "990"
SERVER_SPELL = 59031


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def private(name: str) -> str:
    return "q" + name[1:]


# ------------------------------------------------------------- recolour ---
STOPS = np.array([[0.00, 0, 0, 0], [0.32, 18, 2, 30], [0.58, 58, 12, 104],
                  [0.80, 122, 44, 204], [1.00, 204, 172, 250]], float)


def void_palette(rgb: np.ndarray) -> np.ndarray:
    """Map brightness onto a black -> deep purple -> violet -> lavender ramp."""
    lum = rgb.max(-1) / 255.0 * 0.65 + (rgb.mean(-1) / 255.0) * 0.35
    out = np.zeros(rgb.shape, float)
    for c in range(3):
        out[..., c] = np.interp(lum, STOPS[:, 0], STOPS[:, c + 1])
    return out


def recolour_image(image: Image.Image) -> Image.Image:
    rgba = np.asarray(image.convert("RGBA")).astype(float)
    rgb = void_palette(rgba[..., :3])
    out = np.dstack([rgb, rgba[..., 3]])
    mode = "RGBA" if image.mode in ("RGBA", "LA", "P") or "A" in image.getbands() else "RGB"
    result = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    return result if mode == "RGBA" else result.convert("RGB")


def encode_dds_like(image: Image.Image, reference: bytes) -> bytes:
    codec = reference[84:88]
    mips = max(1, struct.unpack_from("<I", reference, 28)[0])
    if codec == bytes(4):
        return encode_raw_dds_like(image, reference, mips)
    if codec not in (b"DXT1", b"DXT3", b"DXT5"):
        raise SystemExit(f"unsupported DDS codec {codec!r}")
    fmt = "DXT1" if codec == b"DXT1" else "DXT5"
    working = image.convert("RGBA" if fmt == "DXT5" else "RGB")
    header, blocks = None, []
    for level in range(mips):
        out = io.BytesIO()
        working.save(out, format="DDS", pixel_format=fmt)
        data = out.getvalue()
        header = bytearray(data[:128]) if header is None else header
        blocks.append(data[128:])
        if working.size == (1, 1):
            break
        working = working.resize((max(1, working.width // 2), max(1, working.height // 2)), Image.Resampling.LANCZOS)
    if len(blocks) > 1:
        struct.pack_into("<I", header, 8, (struct.unpack_from("<I", header, 8)[0] | 0xA0000) & ~0x8)
        struct.pack_into("<I", header, 108, 0x1000 | 0x8 | 0x400000)
    struct.pack_into("<I", header, 20, len(blocks[0]))
    struct.pack_into("<I", header, 28, len(blocks))
    result = bytes(header) + b"".join(blocks)
    Image.open(io.BytesIO(result)).load()
    return result


def encode_raw_dds_like(image: Image.Image, reference: bytes, mips: int) -> bytes:
    """Uncompressed 32-bit DDS: keep the reference header and channel masks."""
    bits = struct.unpack_from("<I", reference, 88)[0]
    masks = struct.unpack_from("<4I", reference, 92)
    require(bits == 32, f"unsupported raw DDS bit depth {bits}")
    shifts = [(m & -m).bit_length() - 1 if m else None for m in masks]
    working = image.convert("RGBA")
    blocks = []
    for level in range(mips):
        px = np.asarray(working).astype(np.uint32)
        word = np.zeros(px.shape[:2], np.uint32)
        for channel, shift in enumerate(shifts):
            if shift is not None:
                word |= px[..., channel] << np.uint32(shift)
        blocks.append(word.astype('<u4').tobytes())
        if working.size == (1, 1):
            break
        working = working.resize((max(1, working.width // 2), max(1, working.height // 2)), Image.Resampling.LANCZOS)
    result = reference[:128] + b"".join(blocks)
    require(len(result) == len(reference), "raw DDS size changed")
    Image.open(io.BytesIO(result)).load()
    return result


def build_textures():
    outputs = {}
    for name in TEXTURES:
        sources = sorted(EFFECTS.glob(name + ".*"))
        require(sources, f"missing texture {name}")
        for src in sources:
            target = EFFECTS / (private(name) + src.suffix)
            if src.suffix.lower() == ".dds":
                raw = src.read_bytes()
                outputs[target] = encode_dds_like(recolour_image(Image.open(io.BytesIO(raw))), raw)
            elif src.suffix.lower() == ".tga":
                buf = io.BytesIO()
                img = Image.open(src)
                recolour_image(img).save(buf, format="TGA", rle=bool(img.info.get("compression")))
                outputs[target] = buf.getvalue()
    return outputs


def build_nifs():
    outputs = {}
    for src_name, dst_name in NIFS.items():
        src = next(EFFECTS.glob(src_name + ".*"))
        data = src.read_bytes()
        for tex in TEXTURES:
            for ext in (b".tga", b".dds", b".TGA", b".DDS"):
                old = tex.encode() + ext
                data = data.replace(old, private(tex).encode() + ext)
        require(len(data) == src.stat().st_size, "NIF size changed")
        outputs[EFFECTS / (dst_name + src.suffix)] = data
    return outputs


# ------------------------------------------------------------ catalogs ---
def rows_of(data):
    return list(csv.reader(io.StringIO(data.decode("latin1"))))


def to_line(row):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(row)
    return buf.getvalue()


def insert_after_id(data: bytes, after_id: str, new_rows) -> bytes:
    lines = data.decode("latin1").split("\r\n")
    index = next(i for i, line in enumerate(lines) if line.split(",", 1)[0].strip() == after_id)
    return "\r\n".join(lines[:index + 1] + [to_line(r) for r in new_rows] + lines[index + 1:]).encode("latin1")


def replace_row(data: bytes, row_id: str, new_row) -> bytes:
    lines = data.decode("latin1").split("\r\n")
    hits = [i for i, line in enumerate(lines) if line.split(",", 1)[0].strip() == row_id]
    require(len(hits) == 1, f"row {row_id} not unique")
    lines[hits[0]] = to_line(new_row)
    return "\r\n".join(lines).encode("latin1")


def catalogs(gfiles):
    by = {name: {r[0]: r for r in rows_of(gfiles[name]) if r and r[0].strip().isdigit()}
          for name in ("spnifs.csv", "speffects.csv", "spells.csv", "anims.csv", "monnifs.csv")}
    out = {}

    # spnifs: append after the current last row (1401), well under the 1500 limit.
    last_spnif = max(by["spnifs.csv"], key=int)
    new = []
    for nif, (new_id, src_id) in SPNIF.items():
        require(new_id not in by["spnifs.csv"], f"spnifs {new_id} taken")
        row = list(by["spnifs.csv"][src_id]); row[0] = new_id; row[1] = f"Sluagh void {nif}"; row[2] = nif
        new.append(row)
    out["spnifs.csv"] = insert_after_id(gfiles["spnifs.csv"], last_spnif, new)

    last_eff = max(by["speffects.csv"], key=int)
    new = []
    for new_id, src_id, nif_id, label in SPEFFECT:
        require(new_id not in by["speffects.csv"], f"speffects {new_id} taken")
        row = list(by["speffects.csv"][src_id]); row[0] = new_id; row[1] = label; row[2] = nif_id
        new.append(row)
    out["speffects.csv"] = insert_after_id(gfiles["speffects.csv"], last_eff, new)

    new_id, src_id, label = SPELL_ROW
    require(new_id not in by["spells.csv"], f"spells {new_id} taken")
    row = list(by["spells.csv"][src_id])
    row[0], row[1] = new_id, label
    row[6], row[7] = SPEFFECT[0][0], SPEFFECT[1][0]      # Effect1A / Effect1B: hand glows
    row[9] = SPEFFECT[2][0]                              # Effect3: hand burst
    row[11] = SPEFFECT[3][0]                             # target effect: explosion
    out["spells.csv"] = insert_after_id(gfiles["spells.csv"], "4559", [row])

    set_id, base_set, cast_set, slots = ANIM_SET
    require(set_id not in by["anims.csv"], f"anim set {set_id} taken")
    row = list(by["anims.csv"][base_set]); caster = by["anims.csv"][cast_set]
    row[0] = set_id; row[1] = "Sluagh Zombie Magician (undead + caster cast)"
    for slot in slots:
        row[2 + slot] = caster[2 + slot]
    last_anim = max(by["anims.csv"], key=int)
    out["anims.csv"] = insert_after_id(gfiles["anims.csv"], last_anim, [row])

    nif_row = list(by["monnifs.csv"][MAGICIAN_NIF_ROW])
    require(nif_row[2] == "Sluaghbinder_ZombieMagician", "unexpected magician NIF row")
    nif_row[3] = set_id
    out["monnifs.csv"] = replace_row(gfiles["monnifs.csv"], MAGICIAN_NIF_ROW, nif_row)
    return out


# ------------------------------------------------------------- install ---
def install():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = HERE / "install-backups" / f"void-sun-{stamp}"
    backup.mkdir(parents=True)
    gamedata_path = CLIENT / "gamedata.mpk"
    shutil.copy2(gamedata_path, backup / "gamedata.mpk")
    manifest = {"created": stamp, "gamedata_sha": sha(gamedata_path.read_bytes()), "new_files": []}

    textures = build_textures()
    nifs = build_nifs()
    for path in list(textures) + list(nifs):
        require(not path.exists(), f"{path.name} already exists; roll back first")

    gname, gentries = archive.read(gamedata_path.read_bytes())
    gfiles = {e.name.lower(): e.data for e in gentries}
    changed = catalogs(gfiles)
    gout = [archive.Entry(e.name, changed.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in gentries]
    gblob = archive.write(gname, gout)
    archive.verify_memory_image(gblob)

    con = sqlite3.connect(DB)
    old_effect = con.execute("SELECT ClientEffect FROM Spell WHERE SpellID = ?", (SERVER_SPELL,)).fetchone()[0]
    require(old_effect in (4552, int(SPELL_ROW[0])), f"spell {SERVER_SPELL} effect is {old_effect}")
    manifest["server_old_effect"] = old_effect

    for path, data in {**textures, **nifs}.items():
        path.write_bytes(data)
        manifest["new_files"].append(str(path.relative_to(CLIENT)))
    gamedata_path.write_bytes(gblob)
    with con:
        con.execute("UPDATE Spell SET ClientEffect = ? WHERE SpellID = ?", (int(SPELL_ROW[0]), SERVER_SPELL))
    con.close()
    manifest["after_gamedata_sha"] = sha(gblob)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"\nInstalled. Rollback with:\n  python install_void_sun.py rollback \"{backup}\"")


def rollback(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text())
    shutil.copy2(folder / "gamedata.mpk", CLIENT / "gamedata.mpk")
    for relative in manifest["new_files"]:
        path = CLIENT / relative
        if path.exists():
            path.unlink()
    con = sqlite3.connect(DB)
    with con:
        con.execute("UPDATE Spell SET ClientEffect = ? WHERE SpellID = ?", (manifest["server_old_effect"], SERVER_SPELL))
    con.close()
    require(sha((CLIENT / "gamedata.mpk").read_bytes()) == manifest["gamedata_sha"], "rollback hash mismatch")
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "preview":
        out = HERE / "work" / "void_sun_textures.png"
        tiles = []
        for name in TEXTURES:
            src = sorted(EFFECTS.glob(name + ".*"))[0]
            before = Image.open(src).convert("RGBA").resize((96, 96))
            after = recolour_image(Image.open(src)).convert("RGBA").resize((96, 96))
            tile = Image.new("RGBA", (200, 110), (20, 20, 24, 255))
            tile.alpha_composite(before, (2, 12)); tile.alpha_composite(after, (102, 12))
            tiles.append(tile)
        sheet = Image.new("RGBA", (200 * 4, 110 * ((len(tiles) + 3) // 4)), (20, 20, 24, 255))
        for i, t in enumerate(tiles):
            sheet.alpha_composite(t, ((i % 4) * 200, (i // 4) * 110))
        sheet.convert("RGB").save(out)
        print("wrote", out)
    else:
        print(__doc__)
