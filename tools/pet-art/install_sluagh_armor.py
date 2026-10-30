"""Install the Dubh Sluagh set (Sluaghbinder level 50 reward) into the client.

  plan    : python -B install_sluagh_armor.py plan
  install : python -B install_sluagh_armor.py install
  rollback: python -B install_sluagh_armor.py rollback <backup-folder>

Private data only; no stock row, archive or file is changed:
  items\\pskins\\pskin098.mpk          NEW: 11 textures (armor + Catacombs body skins, helm, cloak)
  items\\slu_*.nif / slu*.dds          NEW: reshaped mace / scythe / shield models, mace + scythe textures
  pskins.csv   5771-5776, 5778-5787      NEW rows (archive 98)
  items.csv    2903-2905                NEW rows (mace, scythe, shield models)
  objects.csv  4826-4835                NEW rows (7 armor pieces, shield, mace, scythe)
  mskins.csv   2697-2702               NEW rows -> figures\Mskins\mskin070.mpk (cata armour skins)
Run with launcher, client and server CLOSED.
"""
from __future__ import annotations

import io
import json
import os
import struct
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install_blood_shield as bs  # noqa: E402
from daoc_catalog import archive  # noqa: E402
from install_pet_art import encode_dds  # noqa: E402

CLIENT = bs.CLIENT
ITEMS = CLIENT / "items"
ARCHIVE = ITEMS / "pskins" / "pskin098.mpk"
# Catacombs armour skins are drawn from mskins.csv: pskins.csv "Material BaseTex" (col 6) names an
# mskins.csv row, which names a texture in figures/Mskins/mskinNNN.mpk. With BaseTex 0 the normal
# view falls back to the pskins texture, but /hood uses the mskins lookup only and drew white.
MSKIN_ARCHIVE = CLIENT / "figures" / "Mskins" / "mskin070.mpk"
MSKIN_NUM = "70"
ART = HERE / "work" / "sluagh-armor" / "out"
WOUT = HERE / "work" / "sluagh-armor" / "wout"

# pskin id, texture name, source image (PIL), stock pskins row cloned
def _half(path, top):
    im = Image.open(path).convert("RGB")
    h = im.height // 2
    return im.crop((0, 0 if top else h, im.width, h if top else im.height))


DEBUG_CLOAK = os.environ.get("SLUAGH_CLOAK_DEBUG") == "1"      # TEMPORARY mapping test (cloak_debug_grid.py)
STYLE_TEST = os.environ.get("SLUAGH_STYLE_TEST") == "1"        # TEMPORARY: rows 4836-4856 for /sluaghstyle
HAUBERK_STYLE = "18"


def _cloak(debug_name, size=None):
    if DEBUG_CLOAK:
        return lambda: Image.open(ART / debug_name).convert("RGB")
    def art():
        im = Image.open(ART / "sluagh_cloak.png").convert("RGB")
        return im.resize((size, size), Image.LANCZOS) if size else im
    return art


PSKINS = [
    # Cata skins are cloned from the stock Hibernian hero scale cata rows so they keep the
    # "Material BaseTex" value every stock cata body skin has (without it /hood drew the chest white).
    (5771, "slu_dubh_arm1.dds", lambda: Image.open(ART / "sluagh_arms.png").convert("RGB"), "4387"),
    (5772, "slu_dubh_leg1.dds", lambda: Image.open(ART / "sluagh_legs.png").convert("RGB"), "4389"),
    (5773, "slu_dubh_glov1.dds", lambda: Image.open(ART / "sluagh_gloves.png").convert("RGB"), "4388"),
    (5774, "slu_dubh_boot1.dds", lambda: Image.open(ART / "sluagh_boots.png").convert("RGB"), "4390"),
    (5775, "slu_dubh_helm.dds", lambda: Image.open(ART / "sluagh_helm.png").convert("RGB"), "5521"),
    (5776, "slu_dubh_cloak.dds", _cloak("debug_cloak_cata.png"), "362"),            # cata cloak skin (UV set 1)
    # Catacombs body skins: ONE texture for body + lower body (the whole composite)
    (5778, "slu_dubh_cbody_m.dds", lambda: Image.open(ART / "sluagh_body_m.png").convert("RGB"), "4385"),
    (5779, "slu_dubh_cbody_f.dds", lambda: Image.open(ART / "sluagh_body_f.png").convert("RGB"), "4386"),
]


def _fit(src, size):
    return lambda: src().resize(size, Image.LANCZOS)


# mskins.csv id, cata pskins row it serves, texture name, source (stock cata sizes: body 256x512)
MSKINS = [
    (2697, 5778, "slu_dubh_mbody_m.dds", _fit(lambda: Image.open(ART / "sluagh_body_m.png"), (256, 512))),
    (2698, 5779, "slu_dubh_mbody_f.dds", _fit(lambda: Image.open(ART / "sluagh_body_f.png"), (256, 512))),
    (2699, 5771, "slu_dubh_marm1.dds", _fit(lambda: Image.open(ART / "sluagh_arms.png"), (256, 512))),
    (2700, 5772, "slu_dubh_mleg1.dds", _fit(lambda: Image.open(ART / "sluagh_legs.png"), (256, 512))),
    (2701, 5773, "slu_dubh_mglov1.dds", _fit(lambda: Image.open(ART / "sluagh_gloves.png"), (256, 256))),
    (2702, 5774, "slu_dubh_mboot1.dds", _fit(lambda: Image.open(ART / "sluagh_boots.png"), (256, 256))),
]


# CLASSIC skins (objects cols 4-11): DXT3 at the stock sizes of the Hibernian hero scale set.
# The hauberk renders through the classic path (Cata Status off) so it gets the Body05 pauldron mesh.
CLASSIC = [
    (5780, "slu_dubh_cloak256.dds", _cloak("debug_cloak_classic.png", 256), "362"),
    (5781, "slu_dubh_c_body1m.dds", _fit(lambda: _half(ART / "sluagh_body_m.png", True), (256, 256)), "835"),
    (5782, "slu_dubh_c_body1f.dds", _fit(lambda: _half(ART / "sluagh_body_f.png", True), (256, 256)), "835"),
    (5783, "slu_dubh_c_lbody1.dds", _fit(lambda: _half(ART / "sluagh_body_m.png", False), (256, 256)), "835"),
    (5784, "slu_dubh_c_arm1.dds", _fit(lambda: Image.open(ART / "sluagh_arms.png"), (128, 256)), "835"),
    (5785, "slu_dubh_c_leg1.dds", _fit(lambda: Image.open(ART / "sluagh_legs.png"), (128, 256)), "835"),
    (5786, "slu_dubh_c_glov1.dds", _fit(lambda: Image.open(ART / "sluagh_gloves.png"), (128, 128)), "835"),
    (5787, "slu_dubh_c_boot1.dds", _fit(lambda: Image.open(ART / "sluagh_boots.png"), (128, 128)), "835"),
]

# loose item files: (source, target name, texture rename inside the NIF or None)
# shield_build.py / mace_build.py already write their private texture names into the NIFs
LOOSE_NIFS = [
    (WOUT / "mace.nif", "slu_cairnbreaker.nif", None),
    (WOUT / "scythe.nif", "slu_reaper_host.nif", ("epic_wpn_Valewalker_Sy.tga", "sluagh_reaperhost_sy01.tga")),
    (WOUT / "shield.nif", "slu_cairnfire_aegis.nif", None),
]
LOOSE_TEXTURES = [(WOUT / "mace.png", "slu_cairnbreaker_mace_ghostiron01.dds"),
                  (WOUT / "scythe.png", "sluagh_reaperhost_sy01.dds"),
                  (WOUT / "shield.png", "slu_cairnfire_aegis_skullfire_001.dds")]

# items.csv: id, clone of, NIF name (bases: Hib DragonSlayer mace and large shield, Valewalker epic scythe)
ITEM_ROWS = [(2903, "2052", "slu_cairnbreaker"), (2904, "1759", "slu_reaper_host"), (2905, "2057", "slu_cairnfire_aegis")]

# objects.csv: id, clone of, name, {column: value}
# Player (fig3) bodies draw the CATACOMBS skin columns (65 = Cata Status 1, 66 Body, 67 Fbody,
# 68 Arms, 69 Gloves, 70 Legs, 71 Boots, 72 Cloak) and ignore classic columns 4-12 there, so
# both are set. Cloaks always use column 72. Helms use classic column 12 only.
OBJECT_ROWS = [
    # Cata Body# / Gloves# / Boots# are armour-style indices: 12/4/4 = plate (pauldrons, heavy gauntlets
    # and sabatons); the stock scale rows we cloned use 18/6/6 (no pauldrons).
    # Hauberk: Cata Status must stay ON (with it off the client draws the default tunic). Cata Body#
    # (col 73) is an armour style: 18 = scale (the stock row we cloned); 12 = plate gave no pauldrons
    # on a Celt. HAUBERK_STYLE is the owner's pick from the /sluaghstyle preview.
    (4826, "708", "Hauberk of the Dubh Sluagh", {4: "5781", 5: "5782", 8: "5783", 14: "5", 15: "1", 37: "5", 38: "1",
                                                 66: "5778", 67: "5779", 73: HAUBERK_STYLE}),
    (4827, "709", "Greaves of the Barrow Road", {9: "5785", 70: "5772"}),
    (4828, "710", "Vambraces of the Restless Host", {6: "5784", 68: "5771"}),
    (4829, "711", "Gauntlets of the Grave-Grip", {7: "5786", 33: "4", 40: "4", 69: "5773", 74: "4"}),
    (4830, "712", "Sabatons of the Silent March", {10: "5787", 35: "4", 42: "4", 71: "5774", 75: "4"}),
    (4831, "3867", "Cairnwarden's Helm", {12: "5775"}),
    (4832, "4641", "Mantle of the Sluagh Host", {11: "5780", 16: "1", 72: "5776"}),
    (4833, "3890", "Cairnfire Aegis", {2: "2905"}),
    (4834, "3897", "Cairnbreaker", {2: "2903"}),
    (4835, "3231", "Reaper of the Host", {2: "2904"}),
]
if STYLE_TEST:   # hauberk copies with Cata Body# 1-21 (TEMPORARY, reinstall without SLUAGH_STYLE_TEST)
    _h = dict(OBJECT_ROWS[0][3])
    OBJECT_ROWS += [(4835 + n, "708", f"Sluagh style test {n}", {**_h, 73: str(n)}) for n in range(1, 22)]

def server_stopped():
    bs.stopped()
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    bs.require("coreserver.exe" not in out, "Close the server (CoreServer.exe) first")


def table(files, name):
    return {r[0].strip(): r for r in bs.rows_of(files[name]) if r and r[0].strip().isdigit()}


def reference_dds():
    _, entries = archive.read((ITEMS / "pskins" / "pskin008.mpk").read_bytes())
    return next(e.data for e in entries if e.name.lower().endswith(".dds") and e.data[84:88] == b"DXT1")


def reference_dxt3():
    _, entries = archive.read((ITEMS / "pskins" / "pskin001.mpk").read_bytes())
    return next(e.data for e in entries if e.name.lower() == "cloak.dds")


def encode_dxt3(image, reference):
    """DXT3 with a full mip chain, header fields from a stock DXT3 skin. Classic (composited)
    armour/cloak skins are DXT3 at stock sizes; our 512 DXT1 skins rendered white there."""
    working = image.convert("RGBA")
    header, blocks = None, []
    while True:
        out = io.BytesIO()
        working.save(out, format="DDS", pixel_format="DXT3")
        data = out.getvalue()
        bs.require(data[84:88] == b"DXT3", "Pillow did not produce DXT3")
        header = bytearray(data[:128]) if header is None else header
        blocks.append(data[128:])
        if working.size == (1, 1):
            break
        working = working.resize((max(1, working.width // 2), max(1, working.height // 2)), Image.Resampling.LANCZOS)
    final = bytearray(reference[:128])
    struct.pack_into("<I", final, 12, image.height)
    struct.pack_into("<I", final, 16, image.width)
    struct.pack_into("<I", final, 20, len(blocks[0]))
    struct.pack_into("<I", final, 28, len(blocks))
    result = bytes(final) + b"".join(blocks)
    w, h = image.size
    size = 128 + sum(max(1, (max(1, w >> i) + 3) // 4) * max(1, (max(1, h >> i) + 3) // 4) * 16 for i in range(len(blocks)))
    bs.require(len(result) == size and result[84:88] == b"DXT3", "DXT3 payload mismatch")
    Image.open(io.BytesIO(result)).load()
    return result


def catalog():
    name, entries, files, _ = bs.catalogs()
    names = ("pskins.csv", "items.csv", "objects.csv", "mskins.csv")
    pskins, items, objects, mskins = (table(files, n) for n in names)
    upd = {k: files[k] for k in names}
    base_tex = {pid: str(mid) for mid, pid, _, _ in MSKINS}
    for mid, _, tex, _ in MSKINS:
        row = list(mskins["977"])
        row[0], row[1], row[2], row[4], row[5] = str(mid), tex, tex, MSKIN_NUM, "0"
        upd["mskins.csv"] = bs.add_row(upd["mskins.csv"], row)
    for pid, tex, _, stock in sorted(PSKINS + CLASSIC):
        row = list(pskins[stock])
        row[0], row[1], row[2], row[4] = str(pid), "Dubh Sluagh " + tex.rsplit(".", 1)[0], tex, "98"
        if len(row) > 5:
            row[5] = "0"                          # never "Expansion Only" on private rows
        if len(row) > 6:
            row[6] = base_tex.get(pid, "0")        # Material BaseTex -> our mskins row (never a stock one)
        upd["pskins.csv"] = bs.add_row(upd["pskins.csv"], row)
    for iid, stock, nif in ITEM_ROWS:
        row = list(items[stock])
        row[0], row[1], row[2] = str(iid), nif, nif
        row[4] = "0"                              # never "Expansion Only" on private rows
        upd["items.csv"] = bs.add_row(upd["items.csv"], row)
    for oid, stock, label, changes in OBJECT_ROWS:
        row = list(objects[stock])
        row += [""] * (98 - len(row))
        row[0], row[1] = str(oid), label
        for col, value in changes.items():
            row[col] = value
        upd["objects.csv"] = bs.add_row(upd["objects.csv"], row)
    blob = archive.write(name, [archive.Entry(e.name, upd.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in entries])
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    for old, new in zip(entries, decoded):
        if old.name.lower() not in upd:
            bs.require(old.data == new.data, f"Unrelated archive entry changed: {old.name}")
    for key in upd:
        old_rows = bs.rows_of(files[key])
        new_rows = bs.rows_of(upd[key])
        bs.require([r for r in new_rows if r in old_rows] == old_rows, f"Stock {key} row changed")
        bs.require(not any(not line.strip() for line in upd[key].decode("latin1").split("\r\n")[2:-1]), f"Blank line in {key}")
    return blob


def private_archive():
    ref = reference_dds()
    stamp = int(time.time())
    ref3 = reference_dxt3()
    textures = [(tex, encode_dds(src(), ref)) for _, tex, src, _ in PSKINS]
    textures += [(tex, encode_dxt3(src(), ref3)) for _, tex, src, _ in CLASSIC]
    textures = sorted(textures, key=lambda x: x[0].lower())
    blob = archive.write(b"pskin098.mpk", [archive.Entry(n, d, stamp, 4) for n, d in textures])
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    bs.require([(e.name, e.data) for e in decoded] == textures, "Private archive round trip failed")
    return blob


def mskin_archive():
    ref = reference_dds()
    stamp = int(time.time())
    textures = sorted(((tex, encode_dds(src(), ref)) for _, _, tex, src in MSKINS), key=lambda x: x[0].lower())
    blob = archive.write(MSKIN_ARCHIVE.name.encode(), [archive.Entry(n, d, stamp, 4) for n, d in textures])
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    bs.require([(e.name, e.data) for e in decoded] == textures, "Mskin archive round trip failed")
    return blob


def loose_files():
    ref = reference_dds()
    files = {}
    for src, target, rename in LOOSE_NIFS:
        raw = bytearray(src.read_bytes())
        if rename:
            old, new = rename
            bs.require(len(old) == len(new), f"rename length {old}")
            i = bytes(raw).lower().find(old.lower().encode())
            bs.require(i > 0, f"{old} not in {src.name}")
            raw[i:i + len(new)] = new.encode()
        files[target] = bytes(raw)
    for src, target in LOOSE_TEXTURES:
        files[target] = encode_dds(Image.open(src).convert("RGB"), ref)
    for target in files:
        bs.require(not (ITEMS / target).exists(), f"{target} already exists")
    return files


def install():
    server_stopped()
    game = CLIENT / "gamedata.mpk"
    bs.require(not ARCHIVE.exists(), "pskin098.mpk already exists")
    bs.require(not MSKIN_ARCHIVE.exists(), f"{MSKIN_ARCHIVE.name} already exists")
    blob, pak, mpak, loose = catalog(), private_archive(), mskin_archive(), loose_files()
    backup = HERE / "install-backups" / ("sluagh-armor-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(game, backup / "gamedata.mpk")
    manifest = {"before_gamedata_sha256": bs.file_sha(game), "after_gamedata_sha256": bs.sha(blob),
                "archive_sha256": bs.sha(pak), "mskin_archive_sha256": bs.sha(mpak),
                "loose": {k: bs.sha(v) for k, v in loose.items()}}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bs.atomic_write(ARCHIVE, pak)
    bs.atomic_write(MSKIN_ARCHIVE, mpak)
    for target, data in loose.items():
        bs.atomic_write(ITEMS / target, data)
    bs.atomic_write(game, blob)
    bs.require(bs.file_sha(game) == manifest["after_gamedata_sha256"], "Installed catalog differs")
    print(f'Installed. Rollback:\n  python -B "{Path(__file__).resolve()}" rollback "{backup}"')


def rollback(folder: Path):
    server_stopped()
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    game = CLIENT / "gamedata.mpk"
    bs.require(bs.file_sha(game) in (m["before_gamedata_sha256"], m["after_gamedata_sha256"]),
               "Later catalog changes detected; refuse to overwrite them")
    bs.atomic_write(game, (folder / "gamedata.mpk").read_bytes())
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    if MSKIN_ARCHIVE.exists():
        MSKIN_ARCHIVE.unlink()
    for target in m["loose"]:
        if (ITEMS / target).exists():
            (ITEMS / target).unlink()
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "plan":
        catalog(); private_archive(); mskin_archive(); loose_files()
        print("plan ok")
    else:
        print(__doc__)
