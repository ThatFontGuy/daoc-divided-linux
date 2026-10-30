"""Paint the "Dubh Sluagh" Sluaghbinder armor set in 3D and bake it into the client's UV layouts.

Every pattern is a function of the surface point a texel covers (texelmap.bake), so plates,
scales and trims line up across UV seams and stay left/right symmetric (arms and legs share
mirrored texels). Output PNGs go to out/ at the client's texture proportions:
  body composite 512x1024 (top half = body texture, bottom half = lower-body texture)
  arms / legs 256x512, gloves / boots 256x256
Palette: blackened steel, dark leather, muted pewter trim, a faint grave-green at a few seams.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import texelmap  # noqa: E402
from armorpaint import fbm3, smoothstep, lerp  # noqa: E402

NIF = HERE / "nif"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------------ palette
STEEL = np.array([22, 23, 28.0])        # blackened steel face
STEEL_DARK = np.array([8, 9, 11.0])   # grooves / shadow
STEEL_HI = np.array([104, 108, 116.0])  # polished edge / painted shine
PEWTER = np.array([98, 99, 97.0])    # aged silver trim
PEWTER_DARK = np.array([36, 36, 35.0])
LEATHER = np.array([32, 12, 12.0])      # oxblood leather
LEATHER_HI = np.array([64, 30, 27.0])
CLOTH = np.array([14, 24, 21.0])        # grave-green shroud cloth
GHOST = np.array([110, 170, 132.0])     # grave-green, used sparingly
LIGHT = np.array([0.35, -0.55, 0.76]) / np.linalg.norm([0.35, -0.55, 0.76])


def lit(n):
    return np.clip((n * LIGHT).sum(-1), 0, 1)


def shade(col, n, relief):
    up = np.clip(n[..., 2] * 0.5 + 0.5, 0, 1)
    return col * (0.42 + 0.36 * relief + 0.34 * lit(n) + 0.10 * (up - 0.5))[..., None]


def steel(p, n, relief, seed=1):
    """Hand-painted blackened steel: dents, grime in low spots, chipped edges, scratches."""
    dent = fbm3(p, 0.9, 3, seed + 31)                      # broad hammered unevenness
    relief = np.clip(relief + 0.22 * (dent - 0.5), 0, 1)
    grain = fbm3(p, 1.6, 3, seed)
    brush = fbm3(p * np.array([5.0, 5.0, 0.5]), 0.9, 3, seed + 41)   # vertical streaky strokes
    grime = fbm3(p, 4.0, 3, seed + 17)
    col = lerp(STEEL, STEEL_DARK, np.clip(0.60 * (1 - relief) + 0.16 * (1 - grain)
                                          + 0.16 * grime + 0.12 * (brush - 0.5), 0, 1))
    col = shade(col, n, relief)
    # chipped paint/blackening on raised edges shows bare bright steel in ragged flecks
    chip_n = fbm3(p, 9.0, 2, seed + 53)
    edge = smoothstep(0.55, 0.9, relief) * (1 - smoothstep(0.93, 1.0, relief))
    chips = smoothstep(0.58, 0.70, chip_n) * smoothstep(0.45, 0.85, relief)
    # sparse fine scratches: thin warped lines
    sw = fbm3(p, 2.0, 2, seed + 61)
    lines = np.abs(np.sin((p[..., 0] * 1.7 + p[..., 2] * 2.9 + 6.0 * sw) * 3.1))
    scratch = smoothstep(0.985, 0.999, lines) * smoothstep(0.5, 0.75, fbm3(p, 1.3, 2, seed + 67))
    shine = lit(n) ** 7 * smoothstep(0.35, 0.9, relief)
    amt = np.clip(0.28 * edge + 0.32 * shine + 0.38 * chips + 0.30 * scratch, 0, 0.6)
    col = lerp(col, STEEL_HI * (0.85 + 0.3 * grain)[..., None], amt)
    # soot/rust-black blotches settle in the low areas
    soot = smoothstep(0.6, 0.85, fbm3(p, 2.6, 3, seed + 71)) * (1 - relief)
    return lerp(col, STEEL_DARK * 0.7, 0.55 * soot)


def warp(p, x, amount, scale=1.4, seed=0):
    """Offset a pattern coordinate by smooth noise so painted edges wobble like brushwork."""
    return x + amount * (fbm3(p, scale, 3, seed) - 0.5) * 2.0


def leather(p, n, seed=5):
    g = fbm3(p, 2.4, 4, seed)
    crease = fbm3(p * np.array([1, 1, 4.0]), 3.0, 2, seed + 3)
    col = lerp(LEATHER, LEATHER_HI, 0.30 * g + 0.25 * lit(n) ** 3)
    col = lerp(col, LEATHER * 0.45, 0.35 * smoothstep(0.55, 0.8, crease))
    return shade(col, n, 0.6 + 0.2 * g)


def cloth(p, n, seed=7):
    g = fbm3(p * np.array([1, 1, 3.0]), 2.0, 3, seed)
    fold = fbm3(p * np.array([2.5, 2.5, 0.25]), 1.0, 2, seed + 5)
    col = lerp(CLOTH * 0.6, CLOTH * 2.0, 0.25 * g + 0.45 * fold)
    return shade(col, n, 0.5 + 0.3 * g)


def trim(col, p, n, mask, seed=3):
    """Paint an aged-silver trim band where mask in [0,1]."""
    g = fbm3(p, 3.0, 3, seed)
    t = lerp(PEWTER_DARK, PEWTER, 0.45 + 0.35 * g)
    t = shade(t, n, 0.85)
    t = lerp(t, STEEL_HI, 0.5 * lit(n) ** 6)
    return lerp(col, t, np.clip(mask, 0, 1))


def _hash2(a, b):
    h = np.sin(a * 127.1 + b * 311.7) * 43758.5453
    return h - np.floor(h)


def scales(u, v, size, relief_out):
    """Rows of round-bottomed scales on surface coordinates (u around, v up).

    Each scale is lit on its lower face and tucks darker under the row above.
    Returns relief in [0,1]; relief_out also gets a per-scale tint in [0,1] via .tint.
    """
    rowh = size * 0.62
    row = np.floor(v / rowh)
    uu = u / size + 0.5 * (row % 2)
    cell = np.floor(uu)
    fu = uu - cell - 0.5
    fv = v / rowh - row
    edge = 0.5 * (1 - np.sqrt(np.clip(1 - (2 * fu) ** 2, 0, 1)))
    inside = smoothstep(edge, edge + 0.10, fv)
    relief = inside * (1 - 0.55 * np.abs(2 * fu)) * (1 - 0.55 * smoothstep(0.55, 1.0, fv))
    relief_out[...] = relief
    scales.tint = _hash2(cell, row)
    return relief


def rivet_row(u, v, spacing, row_v, radius):
    fu = (u / spacing) - np.floor(u / spacing) - 0.5
    d = np.sqrt((fu * spacing) ** 2 + (v - row_v) ** 2)
    return smoothstep(radius, radius * 0.35, d)


def finish(atlas, covered, size_xy):
    img = Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8))
    soft = img.filter(ImageFilter.GaussianBlur(0.7))
    arr = np.asarray(img).astype(float) * 0.6 + np.asarray(soft).astype(float) * 0.4
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return img.resize(size_xy, Image.LANCZOS)


# -------------------------------------------------------------- body (torso + skirt)
def paint_body(tm):
    p, n, cov = tm.pos, tm.nrm, tm.covered
    x, y, z0 = p[..., 0], p[..., 1], p[..., 2]
    ax0 = np.abs(x)
    front = y < 0.4
    ang = np.arctan2(x, -y)               # 0 = centre front
    u = ang * 7.5                          # ~ surface distance around the torso
    z = z0
    ax = ax0
    col = leather(p, n)

    # scale shirt everywhere on the torso first
    rel = np.zeros(x.shape)
    scales(u, z, 2.1, rel)
    sc = steel(p, n, 0.25 + 0.75 * rel, seed=11)
    sc = sc * (0.86 + 0.24 * scales.tint)[..., None]
    sc = lerp(sc, STEEL_DARK, 0.55 * (1 - smoothstep(0.02, 0.25, rel)))
    torso = (z > 36.5)
    col = np.where(torso[..., None], sc, col)

    # breastplate / back plate: smooth plate with a centre ridge and a curved lower edge
    plate_low = 46.5 - 2.2 * (ax / 9.0) ** 2
    plate = torso & (z > plate_low) & (z < 60.0) & (ax < 9.6)
    ridge = 1 - smoothstep(0.0, 1.4, ax)
    prel = 0.55 + 0.25 * ridge + 0.20 * smoothstep(plate_low, plate_low + 2.5, z)
    pl = steel(p, n, np.clip(prel, 0, 1), seed=21)
    col = np.where(plate[..., None], pl, col)
    edge = plate & ((z - plate_low) < 0.9) | (torso & (np.abs(ax - 9.6) < 0.5) & (z > plate_low) & (z < 60))
    col = trim(col, p, n, edge.astype(float) * 0.95)
    # two small rivets either side of the ridge, no symbols
    rv = rivet_row(u, z, 3.2, 55.0, 0.32) * plate * (ax > 2.5) * (ax < 7)
    col = lerp(col, STEEL_HI, 0.75 * rv)

    # gorget collar
    collar = (z > 59.5)
    crel = smoothstep(59.5, 61.2, z)
    col = np.where(collar[..., None], steel(p, n, 0.5 + 0.4 * crel, seed=31), col)
    col = trim(col, p, n, ((z > 59.5) & (z < 60.3)).astype(float) * 0.9)

    # pauldrons (variant 5 shoulder geometry): stacked lames with pewter edges
    should = (ax > 10.5) & (z > 50.0)
    lame = (z - 50.0) / 2.4
    lf = lame - np.floor(lame)
    lrel = smoothstep(0.0, 0.25, lf) * (1 - 0.35 * smoothstep(0.75, 1.0, lf))
    pd = steel(p, n, 0.35 + 0.6 * lrel, seed=41)
    col = np.where(should[..., None], pd, col)
    col = trim(col, p, n, (should & (lf < 0.16)).astype(float) * 0.85)
    col = lerp(col, STEEL_HI, 0.7 * rivet_row(u, z, 2.6, 50.0 + 2.4 * np.floor(lame) + 1.2, 0.28) * should)

    # belt: dark leather with square steel plates; plain buckle
    belt = (z > 33.8) & (z < 36.5)
    bl = leather(p, n, seed=51)
    bp = ((np.abs(((u / 3.0) - np.floor(u / 3.0)) - 0.5) < 0.30) & (z > 34.2) & (z < 36.1))
    bl = np.where(bp[..., None], steel(p, n, np.full(z.shape, 0.75), seed=52), bl)
    buckle = front & (ax < 1.5) & (z > 34.0) & (z < 36.3)
    bl = np.where(buckle[..., None], shade(lerp(PEWTER_DARK, PEWTER, 0.7), n, np.full(z.shape, 0.9)), bl)
    col = np.where(belt[..., None], bl, col)
    col = trim(col, p, n, ((np.abs(z - 33.9) < 0.25) | (np.abs(z - 36.4) < 0.25)).astype(float) * 0.6)

    # below the belt: plate tassets over tattered shroud cloth, a faint green hem
    low = z <= 33.8
    tas_u = u / 4.2
    tf = tas_u - np.floor(tas_u)
    half = np.clip(np.abs(tf - 0.5) / 0.38, 0, 1)
    tasset = low & (half < 1) & (z > 27.2 + 2.2 * (1 - np.sqrt(np.clip(1 - half ** 2, 0, 1))))
    trl = smoothstep(0.36, 0.20, np.abs(tf - 0.5))
    tas = steel(p, n, 0.4 + 0.5 * trl, seed=61)
    tlame = ((33.8 - z) / 2.2) % 1.0
    tas = lerp(tas, STEEL_DARK, 0.6 * (tlame < 0.10))
    tas = trim(tas, p, n, ((tlame > 0.10) & (tlame < 0.20)).astype(float) * 0.55)
    cl = cloth(p, n)
    rag = fbm3(p * np.array([4.0, 4.0, 0.3]), 1.0, 2, 71)
    hem = low & (z < 29.5 + 2.0 * rag)
    cl = lerp(cl, GHOST * 0.45, 0.35 * hem * smoothstep(0.55, 0.85, rag))
    col = np.where(low[..., None], np.where(tasset[..., None], tas, cl), col)
    return col


# -------------------------------------------------------------- arms (upper arms)
def paint_arms(tm):
    p, n = tm.pos, tm.nrm
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    ang = np.arctan2(z - 50.5, -y)
    u = ang * 2.6
    rel = np.zeros(x.shape)
    scales(u, ax, 1.25, rel)              # scales run down the arm
    col = steel(p, n, 0.35 + 0.65 * rel, seed=81)
    col = lerp(col, STEEL_DARK, 0.5 * (1 - smoothstep(0.02, 0.25, rel)))
    # elbow cop near the outer end, banded lames on the outer arm
    cop = np.abs(ax - 16.8) < 1.4
    crel = 1 - smoothstep(0.0, 1.4, np.abs(ax - 16.8))
    col = np.where(cop[..., None], steel(p, n, 0.5 + 0.45 * crel, seed=82), col)
    col = trim(col, p, n, (np.abs(np.abs(ax - 16.8) - 1.3) < 0.25).astype(float) * 0.85)
    outer = (z > 51.0) & (ax < 15.0) & (ax > 11.5)
    lame = (ax - 11.5) / 1.7
    lf = lame - np.floor(lame)
    col = np.where(outer[..., None], steel(p, n, 0.4 + 0.5 * smoothstep(0, 0.3, lf), seed=83), col)
    col = trim(col, p, n, (outer & (lf < 0.14)).astype(float) * 0.8)
    return col


# -------------------------------------------------------------- legs
def paint_legs(tm):
    p, n = tm.pos, tm.nrm
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    xc = 3.6
    ang = np.arctan2(ax - xc, -y)
    u = ang * 3.2
    rel = np.zeros(x.shape)
    scales(u, z, 1.35, rel)
    col = steel(p, n, 0.35 + 0.65 * rel, seed=91)
    col = lerp(col, STEEL_DARK, 0.5 * (1 - smoothstep(0.02, 0.25, rel)))
    # cuisse plate on the front of the thigh, knee cop
    front = np.abs(ang) < 0.95
    cuisse = front & (z > 21.5) & (z < 33.5)
    crel = 0.55 + 0.3 * (1 - smoothstep(0, 0.95, np.abs(ang)))
    col = np.where(cuisse[..., None], steel(p, n, crel, seed=92), col)
    col = trim(col, p, n, (cuisse & (np.abs(np.abs(ang) - 0.9) < 0.07)).astype(float) * 0.8)
    knee = front & (np.abs(z - 19.6) < 2.1)
    krel = 1 - smoothstep(0, 2.1, np.sqrt((z - 19.6) ** 2 + (ang * 3.0) ** 2))
    col = np.where(knee[..., None], steel(p, n, 0.45 + 0.5 * krel, seed=93), col)
    col = trim(col, p, n, (knee & (np.abs(np.sqrt((z - 19.6) ** 2 + (ang * 3.0) ** 2) - 1.9) < 0.22)).astype(float) * 0.85)
    # leather side lacing strip, plain
    lace = np.abs(np.abs(ang) - 1.75) < 0.12
    col = np.where(lace[..., None], leather(p, n, seed=94), col)
    return col


# -------------------------------------------------------------- gloves (gauntlets)
def paint_gloves(tm):
    p, n = tm.pos, tm.nrm
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    col = leather(p, n, seed=101)
    back = n[..., 2] > 0.25                   # back of hand (palms face down in T-pose)
    # cuff: flared plate over the wrist
    cuff = (ax > 17.5) & (ax < 21.2)
    cf = (ax - 17.5) / 1.25
    lf = cf - np.floor(cf)
    col = np.where(cuff[..., None], steel(p, n, 0.4 + 0.5 * smoothstep(0, 0.3, lf), seed=102), col)
    col = trim(col, p, n, (cuff & (lf < 0.14)).astype(float) * 0.85)
    # hand plate and knuckle lames on the back of the hand
    hand = back & (ax >= 21.2) & (ax < 23.6)
    col = np.where(hand[..., None], steel(p, n, np.full(x.shape, 0.7), seed=103), col)
    fingers = back & (ax >= 23.6)
    fl = ((ax - 23.6) / 0.55) % 1.0
    col = np.where(fingers[..., None], steel(p, n, 0.35 + 0.55 * smoothstep(0, 0.35, fl), seed=104), col)
    return col


# -------------------------------------------------------------- boots (greaves + sabatons)
def paint_boots(tm):
    p, n = tm.pos, tm.nrm
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    ang = np.arctan2(ax - 3.8, -y)
    col = leather(p, n, seed=111)
    greave = (z > 4.0)
    grel = 0.5 + 0.35 * (1 - smoothstep(0, 1.6, np.abs(ang)))
    col = np.where(greave[..., None], steel(p, n, grel, seed=112), col)
    col = trim(col, p, n, ((np.abs(z - 4.2) < 0.3) | (z > 22.8)).astype(float) * 0.85)
    col = trim(col, p, n, (greave & (np.abs(ang) < 0.08)).astype(float) * 0.5)   # centre ridge
    foot = (z <= 4.0) & (y < -1.0)
    sl = ((-y - 1.0) / 1.1) % 1.0
    col = np.where(foot[..., None], steel(p, n, 0.35 + 0.55 * smoothstep(0, 0.3, sl), seed=113), col)
    sole = z < 0.6
    col = np.where(sole[..., None], LEATHER * 0.6, col)
    return col


JOBS = {
    "body_m": ("Body05_BC_m", paint_body, 1024, (512, 1024)),
    "body_f": ("Body05_BC_f", paint_body, 1024, (512, 1024)),
    "arms": ("Arms01_BC_m", paint_arms, 512, (256, 512)),
    "legs": ("Legs01_BC_m", paint_legs, 512, (256, 512)),
    "gloves": ("Gloves04_BC_m", paint_gloves, 512, (256, 256)),
    "boots": ("Boots04_BC_m", paint_boots, 512, (256, 256)),
}

if __name__ == "__main__":
    for key in (sys.argv[1:] or JOBS):
        nif, fn, bake, size = JOBS[key]
        tm, _ = texelmap.bake(NIF / f"{nif}.nif", size=bake, pad=4)
        atlas = fn(tm)
        atlas[~tm.covered] = (atlas[tm.covered].mean(0) if tm.covered.any() else 0)
        finish(atlas, tm.covered, size).save(OUT / f"sluagh_{key}.png")
        print("painted", key)
