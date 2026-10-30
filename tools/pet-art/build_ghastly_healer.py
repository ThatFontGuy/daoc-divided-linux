"""Ghastly healer art: a private haunting variant of the badh (Classic Bainshee).

  python -B build_ghastly_healer.py      builds work/ghastly-healer/ (skin, NIF, OBJs, renders)

Nothing in the client or database is touched here; install_ghastly_healer_art.py
installs the reviewed result. The stock badh NIF, skin and model rows stay as
they are, so world badh mobs keep their look.

Mesh (in-place vertex edits of a byte copy; vertex count, faces, UVs, skin
weights and every other byte unchanged):
  * the gown tapers into a longer, ragged ghost tail instead of a floor-length hem
  * the waist is slightly gaunter
  * the hair falls further down the back
  * the crown's spikes are broken down to a low, jagged circlet
  * the fingers are longer and thinner, claw-like
Skin: corpse-pale grey-green flesh with sunken eyes and a faint spectral glow
in them, dark lips, a blackened iron circlet, bone-white hair, and a dark
grave-shroud gown with mildew and grave dirt toward the hem and a pale green
Celtic band on the belt.
"""
from __future__ import annotations

import io
import math
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nif4_geom  # noqa: E402
from daoc_catalog import archive  # noqa: E402

ROOT = HERE.parents[1]
CLIENT = ROOT / "runtime" / "client-opendaoc" / "app"
SOURCE_NIF = CLIENT / "figures" / "bainsheesi.nif"
SOURCE_SKIN = (CLIENT / "figures" / "skins" / "skin135.mpk", "bainshee_classic_f.dds")
OUT = HERE / "work" / "ghastly-healer"
BLENDER = Path(os.environ.get("OFFLINE_DAOC_BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"))
RNG = np.random.default_rng(6017006)


def require(ok, message):
    if not ok:
        raise SystemExit(message)


# ---------------------------------------------------------------- skin
def stock_skin() -> Image.Image:
    _, entries = archive.read(SOURCE_SKIN[0].read_bytes())
    entry = next(e for e in entries if e.name.lower() == SOURCE_SKIN[1])
    return Image.open(io.BytesIO(entry.data)).convert("RGB")


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def paint(skin: Image.Image) -> Image.Image:
    """Recolour by region while keeping the stock shading (folds, strands, bones):
    every region is target colour x its own luminance, never a flat fill."""
    src = np.asarray(skin).astype(np.float64)
    h, w, _ = src.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r, g, b = src[..., 0], src[..., 1], src[..., 2]
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    right = xx >= 133
    flesh = (r - b > 14) & (r > 110) & (yy >= 60)
    crown = right & (xx >= 168) & (yy >= 60) & (yy <= 146) & ~flesh & (np.abs(r - b) < 16) & (lum > 0.28)
    hair = right & (yy >= 190) & (yy < 374) & ~flesh
    hands = right & (yy >= 374) & flesh
    face = flesh & ~hands
    cloth = ~(flesh | crown | hair)
    noise = np.asarray(Image.fromarray((RNG.random((h // 16, w // 16)) * 255).astype(np.uint8))
                       .resize((w, h), Image.Resampling.BICUBIC)).astype(np.float64) / 255

    def tint(colour, low, gain):
        return np.array(colour, dtype=np.float64) * (low + gain * lum)[..., None]

    out = src.copy()
    # Grave-shroud gown: dark grey-green, the same folds, grimier toward the hem.
    hem = smoothstep(330, 511, yy) * (xx < 133)
    shroud = tint((84, 100, 92), 0.30, 1.05) * ((1 - 0.38 * hem) * (0.95 + 0.10 * noise))[..., None]
    shroud += np.stack([-5 * hem, 6 * hem, -3 * hem], -1) * noise[..., None]
    out[cloth] = shroud[cloth]
    for x in RNG.integers(2, 130, 9):  # faint torn streaks rising from the hem
        length, width = int(RNG.integers(40, 120)), int(RNG.integers(1, 3))
        streak = (xx >= x) & (xx < x + width) & (yy >= 512 - length)
        out[streak] *= (1 - 0.35 * smoothstep(512 - length, 511, yy[streak]))[..., None]

    # Belt: dark bronze carrying a pale green interlace.
    belt = (xx < 133) & (yy >= 254) & (yy <= 268)
    out[belt] = tint((96, 86, 62), 0.30, 0.85)[belt]
    wave = np.sin(xx / 133 * 2 * math.pi * 6) * 4.0
    knot = belt & ((np.abs(wave + 261 - yy) < 0.9) | (np.abs(-wave + 261 - yy) < 0.9))
    out[knot] = (146, 190, 152)

    # Chest brooch: tarnished verdigris bronze.
    brooch = (xx < 60) & (yy > 105) & (yy < 160) & cloth & (lum < 0.45)
    out[brooch] = tint((92, 140, 120), 0.35, 1.0)[brooch]

    # Corpse-pale, faintly green flesh keeping every shadow of the face and bony hands.
    out[face | hands] = tint((176, 196, 188), 0.32, 0.80)[face | hands]
    eye = np.hypot((xx - 221) / 1.3, yy - 128)
    socket = face & (eye < 8.5)
    out[socket] *= (0.58 + 0.42 * smoothstep(2.5, 8.5, eye[socket]))[..., None]
    glint = face & (eye < 1.8)
    out[glint] = (196, 250, 210)
    lips = face & (xx > 228) & (yy > 153) & (yy < 162) & (r - b > 40)
    out[lips] = tint((96, 100, 118), 0.4, 0.6)[lips]

    # Blackened iron circlet with verdigris in its recesses.
    out[crown] = tint((92, 98, 96), 0.15, 0.90)[crown]
    verd = crown & (lum < 0.55) & (noise > 0.6)
    out[verd] = tint((80, 140, 118), 0.3, 0.8)[verd]

    # Bone-white hair, the same strands, greying toward dark tips.
    tips = smoothstep(240, 374, yy)
    out[hair] = (tint((222, 230, 220), 0.32, 0.80) * (1 - 0.40 * tips)[..., None])[hair]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- mesh
def body_layout(data: bytes):
    shapes = nif4_geom.load(SOURCE_NIF)
    body = max(shapes, key=lambda s: len(s.vertices))
    pos = body.offset
    count = struct.unpack_from("<H", data, pos)[0]
    for width in (1, 4):
        start = pos + 2 + width
        verts = np.array(struct.unpack_from(f"<{3 * count}f", data, start)).reshape(count, 3)
        if np.allclose(verts, body.vertices):
            cursor = start + 12 * count
            has_normals = (data[cursor] if width == 1 else struct.unpack_from("<I", data, cursor)[0]) != 0
            cursor += width + (12 * count if has_normals else 0)
            return body, start, cursor  # cursor -> bounding centre (3f) + radius (f)
    raise SystemExit("Could not locate the body vertex array")


def reshape(body) -> np.ndarray:
    v = body.vertices.copy()
    u, t = body.uvs[:, 0], body.uvs[:, 1]
    gown = u < 0.52
    hair = (u >= 0.52) & (t >= 0.37) & (t < 0.74)
    hands = (u >= 0.52) & (t >= 0.74)
    crown = (u >= 0.65) & (t >= 0.11) & (t < 0.29)

    # Ghost tail: taper the lower gown toward its axis and draw it down, jagged.
    ring = gown & (v[:, 2] > -34) & (v[:, 2] < -26)
    cx, cy = v[ring, 0].mean(), v[ring, 1].mean()
    k = np.clip((-28 - v[:, 2]) / 20.5, 0, 1) * gown
    v[:, 0] = cx + (v[:, 0] - cx) * (1 - 0.48 * k)
    v[:, 1] = cy + (v[:, 1] - cy) * (1 - 0.34 * k)
    v[:, 2] -= 6 * k + 3.5 * (k > 0.92) * RNG.random(len(v))

    # Gaunt waist.
    waist = gown & (np.abs(v[:, 2] + 9) < 7)
    squeeze = 1 - 0.07 * np.cos((v[:, 2] + 9) / 7 * math.pi / 2) * waist
    v[:, 0] = cx + (v[:, 0] - cx) * squeeze
    v[:, 1] = cy + (v[:, 1] - cy) * squeeze

    # Longer hair down the back (the back is the side the hair already sits on).
    back = np.sign(v[hair, 1].mean() - v[~hair & ~gown & ~hands, 1].mean()) or 1.0
    nape = 8.0
    drop = np.clip(nape - v[:, 2], 0, None) * hair
    v[:, 2] -= 0.75 * drop
    v[:, 1] += back * 0.10 * drop

    # Broken crown: spikes cut down to a low jagged circlet.
    if crown.any():
        base = np.percentile(v[crown, 2], 45)
        tall = crown & (v[:, 2] > base)
        v[tall, 2] = base + (v[tall, 2] - base) * (0.32 + 0.12 * RNG.random(tall.sum()))

    # Long thin fingers.
    reach = np.abs(v[:, 0])
    fingers = hands & (reach > 18)
    v[fingers, 0] = np.sign(v[fingers, 0]) * (18 + (reach[fingers] - 18) * 1.38)
    v[fingers, 1] *= 0.85
    return v


def build_nif():
    data = SOURCE_NIF.read_bytes()
    body, start, bounds = body_layout(data)
    new = reshape(body)
    blob = bytearray(data)
    struct.pack_into(f"<{new.size}f", blob, start, *new.ravel())
    centre = np.array(struct.unpack_from("<3f", data, bounds))
    radius = struct.unpack_from("<f", data, bounds + 12)[0]
    needed = float(np.linalg.norm(new - centre, axis=1).max())
    if needed > radius:
        struct.pack_into("<f", blob, bounds + 12, needed * 1.02)
    changed = [i for i in range(len(data)) if data[i] != blob[i]]
    allowed = set(range(start, start + 12 * len(new))) | set(range(bounds + 12, bounds + 16))
    require(len(blob) == len(data) and all(i in allowed for i in changed), "NIF edit touched bytes outside the body vertices")
    return bytes(blob), body, new


# ---------------------------------------------------------------- review
def write_obj(path: Path, body, vertices, skin_png: Path):
    lines = [f"mtllib {path.stem}.mtl", "o body"]
    lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in vertices]
    lines += [f"vt {u:.6f} {1 - t:.6f}" for u, t in body.uvs]
    lines.append("usemtl skin")
    lines += [f"f {a + 1}/{a + 1} {b + 1}/{b + 1} {c + 1}/{c + 1}" for a, b, c in body.faces]
    path.write_text("\n".join(lines) + "\n")
    path.with_suffix(".mtl").write_text(f"newmtl skin\nKd 1 1 1\nmap_Kd {skin_png.resolve().as_posix()}\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skin = stock_skin()
    skin.save(OUT / "badh_stock_skin.png")
    new_skin = paint(skin)
    new_skin.save(OUT / "ghastly_healer_skin.png")
    blob, body, new = build_nif()
    (OUT / "Sluaghbinder_GhastlyHealer.NIF").write_bytes(blob)
    write_obj(OUT / "badh_stock.obj", body, body.vertices, OUT / "badh_stock_skin.png")
    write_obj(OUT / "ghastly_healer.obj", body, new, OUT / "ghastly_healer_skin.png")
    if BLENDER.exists():
        subprocess.run([str(BLENDER), "-b", "--factory-startup", "--python", str(HERE / "blender_views.py"), "--",
                        str(OUT / "ghastly_healer_views.png"), str(OUT / "badh_stock.obj"),
                        str(OUT / "ghastly_healer.obj")], check=True, capture_output=True)
    side = Image.new("RGB", (512, 512), (20, 20, 22))
    side.paste(skin, (0, 0))
    side.paste(new_skin, (256, 0))
    side.save(OUT / "ghastly_healer_skin_compare.png")
    print("Built", OUT)


if __name__ == "__main__":
    main()
