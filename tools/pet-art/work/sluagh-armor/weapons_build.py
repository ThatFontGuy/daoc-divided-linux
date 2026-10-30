"""Reshape + paint the Sluaghbinder showcase weapons (private copies of stock item NIFs).

  shield  "Cairnfire Aegis"   from sh_rounda      bone skull boss, grave-green flames, flame-point rim
  mace    "Cairnbreaker"      from the Celtic mace   six-flanged cold-steel head, bone grip
  scythe  "Reaper of the Host" from the Valewalker epic scythe       longer hooked pale blade, black haft

Each weapon gets its own colours so it stands out from the blackened armor:
bone + iron + green fire (shield), polished cold steel + bone + oxblood (mace), pale silver + black + green edge (scythe).
Outputs: wout/<key>.png (texture), wout/<key>.nif (reshaped copy), wout/<key>.obj (preview).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import wgeom  # noqa: E402
import paint_sluagh_armor as M  # noqa: E402
from armorpaint import fbm3, smoothstep, lerp  # noqa: E402

OUT = HERE / "wout"
OUT.mkdir(exist_ok=True)

BONE = np.array([206, 196, 170.0])
BONE_DARK = np.array([96, 84, 64.0])
IRON = np.array([58, 56, 54.0])
COLD = np.array([150, 160, 172.0])
SILVER = np.array([196, 200, 204.0])
BLACK = np.array([20, 20, 22.0])


def bake(verts, uvs, faces, size, wrap=False):
    """Texel -> surface position/normal for arbitrary geometry (square atlas).
    wrap=True tiles UVs outside 0..1 back into the square, as the client does."""
    S = size
    pos = np.zeros((S, S, 3)); nrm = np.zeros((S, S, 3)); cov = np.zeros((S, S), bool)
    vn = wgeom.normals(verts, faces)
    px = uvs * (S - 1)
    for tri in faces:
        a, b, c = px[tri]
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        x0 = int(math.floor(min(a[0], b[0], c[0]))) - 1; x1 = int(math.ceil(max(a[0], b[0], c[0]))) + 1
        y0 = int(math.floor(min(a[1], b[1], c[1]))) - 1; y1 = int(math.ceil(max(a[1], b[1], c[1]))) + 1
        if not wrap:
            x0, x1, y0, y1 = max(0, x0), min(S - 1, x1), max(0, y0), min(S - 1, y1)
        gy, gx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
        w2 = 1 - w0 - w1
        e = 0.6 / max(1.0, abs(den)) ** 0.5
        ins = (w0 >= -e) & (w1 >= -e) & (w2 >= -e)
        if not ins.any():
            continue
        p = w0[..., None] * verts[tri[0]] + w1[..., None] * verts[tri[1]] + w2[..., None] * verts[tri[2]]
        nn = w0[..., None] * vn[tri[0]] + w1[..., None] * vn[tri[1]] + w2[..., None] * vn[tri[2]]
        ys, xs = gy[ins] % S, gx[ins] % S
        first = ~cov[ys, xs]
        pos[ys[first], xs[first]] = p[ins][first]; nrm[ys[first], xs[first]] = nn[ins][first]; cov[ys[first], xs[first]] = True
    for _ in range(4):
        grow = ~cov
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(np.roll(cov, dy, 0), dx, 1) & grow
            ys, xs = np.nonzero(src)
            pos[ys, xs] = pos[(ys - dy) % S, (xs - dx) % S]; nrm[ys, xs] = nrm[(ys - dy) % S, (xs - dx) % S]
        cov = cov | (np.linalg.norm(nrm, axis=2) > 0)
    l = np.linalg.norm(nrm, axis=2, keepdims=True)
    return pos, nrm / np.maximum(l, 1e-9), cov


def save(col, size, key):
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    soft = img.filter(ImageFilter.GaussianBlur(0.6))
    arr = np.asarray(img).astype(float) * 0.65 + np.asarray(soft).astype(float) * 0.35
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS).save(OUT / f"{key}.png")
    return OUT / f"{key}.png"


# ------------------------------------------------------------------ shield
def shield_shape(v):
    v = v.copy()
    r = np.hypot(v[:, 0], v[:, 1])
    theta = np.arctan2(np.abs(v[:, 0]), v[:, 1])          # 0 at the top, mirrored left/right
    rim = r > 9.4
    flame = np.maximum(0, np.cos(theta * 8)) ** 2.5
    scale = np.where(rim, 1 + 0.07 * flame, 1.0)
    v[:, 0] *= scale; v[:, 1] *= scale
    v[:, 2] += 1.1 * (1 - np.clip(r / 10.7, 0, 1) ** 2)    # dished face
    boss = r < 3.2
    v[boss, 0] *= 1.45; v[boss, 1] *= 1.45
    v[boss, 2] += 1.5 * (1 - r[boss] / 3.2)
    return v


def shield_paint(p, n, cov):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    r = np.hypot(x, y)
    th = np.arctan2(ax, y)
    face = n[..., 2] > 0.15
    q = np.stack([ax, y, z], -1)
    g = fbm3(q, 1.4, 3, 301)
    col = lerp(IRON * 0.55, IRON * 1.25, 0.5 * g)
    col = M.shade(col, n, np.full(x.shape, 0.6))
    # grave-green flames licking outward from the skull boss
    tongue = fbm3(np.stack([th * 2.2, r * 0.18, z * 0.1], -1), 1.6, 4, 302)
    reach = 3.2 + 6.2 * tongue
    fl = face & (r < reach) & (r > 3.0)
    heat = 1 - np.clip((r - 3.0) / np.maximum(reach - 3.0, 1e-3), 0, 1)
    fire = lerp(M.GHOST * 0.55, np.array([200, 245, 210.0]), heat ** 2)
    col = np.where(fl[..., None], lerp(col, fire, 0.25 + 0.6 * heat), col)
    # bone skull on the boss
    boss = r < 4.4
    sk = lerp(BONE_DARK, BONE, 0.45 + 0.45 * fbm3(q, 3.0, 3, 303))
    sk = M.shade(sk, n, 0.55 + 0.4 * np.clip(1 - r / 4.4, 0, 1))
    col = np.where(boss[..., None], sk, col)
    eye = boss & (np.hypot(ax - 1.45, y - 0.55) < 0.85)
    col = np.where(eye[..., None], lerp(BLACK, M.GHOST, 0.45 * (1 - np.hypot(ax - 1.45, y - 0.55) / 0.85)), col)
    nose = boss & (ax < 0.35 + 0.25 * np.clip(-(y + 0.3), 0, 1)) & (y < -0.25) & (y > -1.2)
    col = np.where(nose[..., None], BLACK, col)
    teeth = boss & (y < -1.6) & (y > -2.6) & (ax < 1.7)
    tw = ((ax / 0.42) - np.floor(ax / 0.42)) < 0.18
    col = np.where((teeth & tw)[..., None], BONE_DARK * 0.5, col)
    # blackened steel rim with silver studs
    rimz = r > 9.2
    col = np.where(rimz[..., None], M.steel(q, n, np.full(x.shape, 0.65), seed=304), col)
    col = M.trim(col, q, n, ((r > 9.1) & (r < 9.5)).astype(float) * 0.9)
    stud = (np.abs(r - 9.95) < 0.5) & (np.cos(th * 16) > 0.86)
    col = np.where(stud[..., None], lerp(M.PEWTER_DARK, M.STEEL_HI, 0.35 + 0.6 * M.lit(n)), col)
    back = n[..., 2] < -0.15
    col = np.where(back[..., None], M.leather(q, n, seed=305), col)
    return col


# ------------------------------------------------------------------ mace
def mace_shape(v):
    """Celtic mace: grow the square head into six flanges, slightly larger overall."""
    v = v.copy()
    r = np.hypot(v[:, 0], v[:, 1])
    head = v[:, 2] > 27.5
    phi = np.arctan2(v[head, 1], v[head, 0])
    w_ = smoothstep(27.5, 30.0, v[head, 2]) * (1 - 0.5 * smoothstep(34.5, 35.7, v[head, 2]))
    flange = 1 + w_ * (0.25 + 0.85 * np.maximum(0, np.cos(phi * 3)) ** 4)
    v[head, 0] *= flange; v[head, 1] *= flange
    return v


def mace_paint(p, n, cov):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    q = np.stack([np.abs(x), np.abs(y), z], -1)
    g = fbm3(q, 2.0, 3, 401)
    steel = lerp(COLD * 0.5, COLD, 0.4 + 0.4 * g)
    steel = M.shade(steel, n, np.full(x.shape, 0.75))
    steel = lerp(steel, np.array([235, 240, 248.0]), 0.6 * M.lit(n) ** 8)
    head = z > 27.5
    col = np.where(head[..., None], steel, 0)
    # haft: bone with oxblood wraps on the grip, silver collars
    bone = M.shade(lerp(BONE_DARK, BONE, 0.5 + 0.35 * fbm3(q, 3.0, 3, 402)), n, np.full(x.shape, 0.65))
    wrap = ((z / 1.0) - np.floor(z / 1.0)) < 0.5
    grip = (z > 7.5) & (z < 17.0)
    hc = np.where((grip & wrap)[..., None], M.leather(q, n, seed=403), bone)
    col = np.where(head[..., None], col, hc)
    collar = (np.abs(z - 17.4) < 0.5) | (np.abs(z - 27.2) < 0.6) | (z < 7.6)
    col = np.where(collar[..., None], lerp(M.PEWTER_DARK, SILVER, 0.4 + 0.5 * M.lit(n)), col)
    # a dark band etched around the middle of the head with a faint green glow in it
    band = head & (np.abs(z - 31.6) < 0.35)
    col = np.where(band[..., None], lerp(BLACK, M.GHOST, 0.5), col)
    return col


# ------------------------------------------------------------------ scythe
def scythe_shape(v):
    v = v.copy()
    blade = (v[:, 2] > 33.0) & (v[:, 0] < -1.5)
    x0 = -1.5
    t = np.clip((x0 - v[blade, 0]) / 12.5, 0, 1.5)
    v[blade, 0] = x0 - (x0 - v[blade, 0]) * 1.32            # longer reach
    v[blade, 2] -= 5.0 * t ** 2                               # deeper hook
    return v


def scythe_paint(p, n, cov):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    q = np.stack([x, np.abs(y), z], -1)
    g = fbm3(q, 1.8, 3, 501)
    ang = np.arctan2(y, x)
    # haft: black-stained ash with a slow spiral grain
    grain = np.abs(np.sin(z * 1.7 + ang * 2.0 + 3.0 * fbm3(q * np.array([1, 1, 0.2]), 1.0, 2, 503)))
    haft = M.shade(lerp(BLACK, BLACK * 2.8, 0.35 * g + 0.25 * smoothstep(0.85, 1.0, grain)), n, np.full(x.shape, 0.6))
    # two leather-wrapped grips with stitched spiral bands
    grip = ((z > -8.5) & (z < -1.0)) | ((z > 8.0) & (z < 15.0))
    wrap = ((z * 1.25 + ang / np.pi) % 1.0)
    leather = lerp(np.array([62, 36, 26.0]), np.array([112, 74, 52.0]), 0.3 + 0.45 * g[..., None])
    leather = M.shade(leather, n, np.full(x.shape, 0.7))
    seam = smoothstep(0.40, 0.47, np.abs(wrap - 0.5))              # dark gap between wraps
    leather = lerp(leather, leather * 0.35, seam[..., None])
    haft = np.where(grip[..., None], leather, haft)
    # iron bands with rivets at each section, bone rings between them
    bands = np.array([-21.2, -9.0, -0.4, 7.4, 15.6, 28.3])
    db = np.min(np.abs(z[..., None] - bands), -1)
    band = db < 0.45
    iron = lerp(M.PEWTER_DARK, M.STEEL_HI, 0.25 + 0.55 * M.lit(n))
    haft = np.where(band[..., None], M.shade(iron, n, np.full(x.shape, 0.8)), haft)
    rivet = band & (np.abs(((ang / (2 * np.pi)) * 8) % 1.0 - 0.5) < 0.12) & (db < 0.2)
    haft = np.where(rivet[..., None], lerp(M.STEEL_HI, np.array([235, 238, 240.0]), 0.5 * M.lit(n)), haft)
    rings = np.min(np.abs(z[..., None] - np.array([-15.0, 3.5, 21.5])), -1) < 0.28
    haft = np.where(rings[..., None], M.shade(lerp(BONE_DARK, BONE, 0.7), n, np.full(x.shape, 0.8)), haft)
    # butt cap: iron ferrule ending in a short point
    cap = z < -20.6
    haft = np.where(cap[..., None], M.steel(q, n, np.full(x.shape, 0.7), seed=505), haft)
    col = haft
    # blade: pale silver, dark spine, fuller groove with a grave-green hairline, nicked bright tip
    blade = (z > 29.0) & (x < -1.0)
    pale = lerp(SILVER * 0.55, SILVER, 0.35 + 0.45 * g)
    pale = M.shade(pale, n, np.full(x.shape, 0.75))
    pale = lerp(pale, np.array([240, 244, 246.0]), 0.55 * M.lit(n) ** 8)
    col = np.where(blade[..., None], pale, col)
    if blade.any():
        zb = z[blade]
        top_z = np.percentile(zb, 70); low_z = np.percentile(zb, 22)
        top = blade & (z > top_z)
        col = np.where(top[..., None], lerp(col, BLACK * 1.5, 0.42), col)
        edge = blade & (z < low_z)
        col = np.where(edge[..., None], lerp(col, M.GHOST * 1.1, 0.55), col)
        mid = 0.5 * (top_z + low_z) + 0.25 * (x + 1.0) * 0.05
        fuller = blade & (np.abs(z - mid) < 0.32) & (x < -3.0) & (x > -17.5)
        col = np.where(fuller[..., None], lerp(BLACK * 1.2, M.GHOST * 1.3, 0.35 + 0.4 * (np.abs(z - mid) < 0.1)), col)
        tip = blade & (x < -17.5)
        nick = smoothstep(0.72, 0.8, fbm3(q, 4.5, 2, 506))
        col = np.where(tip[..., None], lerp(col, np.array([246, 248, 250.0]), 0.25 + 0.3 * M.lit(n) - 0.4 * nick), col)
    # socket and collar: riveted steel; the back fluke is bone like the shield's horns
    head = (z > 29.0) & (x >= -1.0)
    col = np.where(head[..., None], M.steel(q, n, np.full(x.shape, 0.7), seed=502), col)
    fluke = head & (x > 3.0)
    bone = M.shade(lerp(BONE_DARK, BONE, 0.45 + 0.4 * fbm3(q, 3.0, 3, 507)), n, np.full(x.shape, 0.7))
    groove = np.abs(np.sin((x - z * 0.3) * 1.1)) > 0.975
    bone = lerp(bone, BONE_DARK * 0.7, 0.35 * groove)
    col = np.where(fluke[..., None], bone, col)
    sock_rivet = head & ~fluke & (np.abs(((z - 29.0) / 1.6) % 1.0 - 0.5) < 0.12) & (np.abs(x - 1.0) < 0.35)
    col = np.where(sock_rivet[..., None], lerp(M.STEEL_HI, np.array([235, 238, 240.0]), 0.5), col)
    return col


# The round shield carries three UV sets: 0 = emblem pattern, 1 = emblem symbol, 2 = the
# surface texture that objects.csv "Apply Texture" replaces. Paint the shield in set 2.
# (The shipped Cairnfire Aegis is now built by shield_build.py; this job is kept for reference.)
UV_SET = {"shield": 2}

JOBS = {
    "shield": ("sh_rounda", shield_shape, shield_paint, 512),
    "mace": ("H_bl_CelticMace01", mace_shape, mace_paint, 512),
    "scythe": ("epic_wpn_valewalker_sy", scythe_shape, scythe_paint, 512),
}

if __name__ == "__main__":
    for key in (sys.argv[1:] or JOBS):
        src, shape_fn, paint_fn, size = JOBS[key]
        w = wgeom.load(src, UV_SET.get(key, 0))
        nv = shape_fn(w.verts)
        wrap = key in UV_SET
        pos, _, cov = bake(w.verts, w.uvs, w.faces, 1024, wrap)      # patterns follow the original shape
        _, nrm, _ = bake(nv, w.uvs, w.faces, 1024, wrap)              # lighting follows the new shape
        col = paint_fn(pos, nrm, cov)
        png = save(col, size, key)
        ok = wgeom.write(w, nv, OUT / f"{key}.nif")
        view = nv[:, [0, 2, 1]] * np.array([1, -1, 1]) if key == "shield" else nv   # shield face toward the camera
        wgeom.obj(view, w.uvs, w.faces, png, OUT / f"{key}.obj")
        print("built", key, "normals patched" if ok else "normals not found", flush=True)
