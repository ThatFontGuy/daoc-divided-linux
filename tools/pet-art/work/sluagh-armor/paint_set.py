"""Dubh Sluagh armor set, detailed pass. Materials from paint_sluagh_armor, details from detail_parts.

Usage: python paint_set.py [body_m body_f arms legs gloves boots]
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import texelmap  # noqa: E402
import paint_sluagh_armor as M  # noqa: E402
import detail_parts as D  # noqa: E402
from armorpaint import fbm3, smoothstep, lerp  # noqa: E402


def bake_union(names, size, pad=4, uv_set=0):
    """Bake several meshes that share one texture (all body / glove / boot / cloak variants).

    The client may draw any of them, so every texel any variant uses must be painted; a texel
    takes its surface point from the first mesh in `names` that covers it."""
    tm = None
    for name in names:
        t, _ = texelmap.bake(M.NIF / f"{name}.nif", size=size, pad=0, uv_set=uv_set)
        if tm is None:
            tm = t
            continue
        new = t.covered & ~tm.covered
        for field in ("pos", "nrm", "pos2"):
            getattr(tm, field)[new] = getattr(t, field)[new]
        tm.mirror[new] = t.mirror[new]
        tm.shape[new] = t.shape[new]
        tm.covered |= new
    S = tm.size
    for _ in range(pad):
        grow = ~tm.covered
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(np.roll(tm.covered, dy, 0), dx, 1) & grow
            ys, xs = np.nonzero(src)
            sy, sx = (ys - dy) % S, (xs - dx) % S
            tm.pos[ys, xs] = tm.pos[sy, sx]; tm.nrm[ys, xs] = tm.nrm[sy, sx]; tm.shape[ys, xs] = tm.shape[sy, sx]
        tm.covered = tm.shape >= 0
    return tm


def gem(col, n, dist, radius):
    """A small cabochon of grave-green stone in a dark iron setting."""
    setting = dist < radius * 1.45
    col = np.where(setting[..., None], M.shade(M.PEWTER_DARK, n, np.full(dist.shape, 0.8)), col)
    stone = np.clip(1 - dist / radius, 0, 1)
    glow = lerp(M.GHOST * 0.55, np.array([200, 255, 215.0]), stone ** 2.5)
    return np.where((dist < radius)[..., None], glow, col)


def mail(col, p, n, inside, u, v):
    """Fine riveted mail where plates part (joints)."""
    row = np.floor(v / 0.42)
    uu = u / 0.42 + 0.5 * (row % 2)
    d = np.hypot(uu - np.floor(uu) - 0.5, v / 0.42 - row - 0.5)
    ring = smoothstep(0.16, 0.26, d) * (1 - smoothstep(0.38, 0.48, d))
    c = lerp(M.STEEL_DARK * 0.6, M.STEEL_HI * 0.55, ring * (0.6 + 0.4 * M.lit(n)))
    return np.where(inside[..., None], c, col)


def body(tm):
    n = tm.nrm
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    p = D.mirror(tm.pos)
    ax = np.abs(x)
    front = y < 0.4
    u = np.abs(np.arctan2(x, -y)) * 7.5            # mirrored distance around the torso
    col = M.leather(p, n)

    torso = z > 36.5
    col = D.scale_field(col, p, n, torso, u, z, 2.0, seed=11)

    # breastplate / backplate with a raised centre ridge
    low = 46.6 - 2.2 * (ax / 9.0) ** 2
    bp = torso & (z > low) & (z < 59.6) & (ax < 9.6)
    d_bp = np.minimum.reduce([z - low, 59.6 - z, 9.6 - ax])
    col = D.plate(col, p, n, bp, d_bp, seed=21, rivet_u=np.where(z - low < 1.2, u, z))
    flute = bp & (d_bp > 1.6)
    fx = (ax / 1.45) - np.floor(ax / 1.45)
    groove = 1 - smoothstep(0.0, 0.10, np.abs(fx - 0.5))
    col = lerp(col, M.STEEL_DARK, 0.45 * groove * flute * smoothstep(low + 1.6, low + 6.0, z))
    col = lerp(col, M.STEEL_HI, 0.18 * (1 - smoothstep(0.0, 0.10, np.abs(fx - 0.62))) * flute)
    ridge = bp & (ax < 0.35) & (d_bp > 1.0)
    col = M.trim(col, p, n, ridge.astype(float) * 0.55)
    # a lower plate (fauld) between breastplate and belt
    fz = torso & (z <= low) & (z > 37.0) & (ax < 9.0) & front
    d_f = np.minimum.reduce([low - z, z - 37.0, 9.0 - ax])
    col = D.plate(col, p, n, fz, d_f, seed=23, base_relief=0.55, engrave=False, rivet_u=u)

    # gorget: two lames
    gor = z > 59.6
    gl = ((z - 59.6) / 1.25)
    d_g = np.minimum((gl - np.floor(gl)) * 1.25, 99)
    col = D.plate(col, p, n, gor, d_g, seed=31, engrave=False, rim=0.32)

    # pauldrons: three lames, rolled edges, rivets along each lame
    arch = 0.32 * np.clip(ax - 10.4, 0, 6.0)          # lames rise toward the shoulder tip
    sh = (ax > 10.4) & (z > 50.0 + 0.6 * arch)
    lame = (z - 50.0 + arch) / 2.3
    d_l = (lame - np.floor(lame)) * 2.3
    col = D.plate(col, p, n, sh, np.minimum(d_l, (ax - 10.4) * 1.6 + 0.25), seed=41, engrave=False,
                  rivet_u=u, rivet_spacing=1.5)
    # leather strap under the pauldron where it meets the arm
    shs = (ax > 9.9) & (ax <= 10.4) & (z > 50.0)
    col = D.strap(col, p, n, shs, ax - 10.15, z, seed=43, width=0.5)

    # belt: stitched leather, steel studs, buckle at the front
    belt = (z > 33.8) & (z < 36.5)
    col = D.strap(col, p, n, belt, z - 35.15, u, seed=51, width=2.7,
                  buckle_at=np.where(front, 0.0, 99.0))
    stud = belt & (np.sqrt((((u / 2.2) - np.floor(u / 2.2) - 0.5) * 2.2) ** 2 + (z - 35.15) ** 2) < 0.32) & (u > 1.4)
    col = np.where(stud[..., None], lerp(M.PEWTER_DARK, M.STEEL_HI, 0.3 + 0.6 * M.lit(n)), col)

    # below the belt: three riveted fauld lames around the hips, open at the front and back
    lowz = z <= 33.8
    cl = M.cloth(p, n)
    rag = fbm3(p * np.array([4.0, 4.0, 0.3]), 1.0, 2, 71)
    hem = z < 28.6 + 1.6 * rag
    cl = lerp(cl, M.GHOST * 0.45, 0.30 * hem * smoothstep(0.55, 0.85, rag))
    col = np.where(lowz[..., None], cl, col)
    opening = (ax < 1.6 + 0.35 * (33.8 - z)) & (np.abs(y) > 2.0)
    lame_h = 2.05
    li = np.floor((33.8 - z) / lame_h)
    fz = (33.8 - z) / lame_h - li                    # 0 at a lame's top .. 1 at its bottom edge
    skirt = lowz & ~opening                          # lamellar skirt all the way to the hem
    d_s = np.minimum((1 - fz) * lame_h, 99.0)        # distance up from each lame's bottom edge
    d_side = (ax - (1.6 + 0.35 * (33.8 - z)))
    col = D.plate(col, p, n, skirt, np.minimum(d_s, np.where(np.abs(y) > 2.0, d_side, 99.0)), seed=61,
                  engrave=False, rivet_u=u, rivet_spacing=1.5, rim=0.42)
    # painted light: each lame brighter at its top, shadowed under the lame above
    col = lerp(col, M.STEEL_DARK * 0.6, 0.45 * skirt * (1 - smoothstep(0.0, 0.22, fz)))
    # every third lame is a dark leather band with stitching, so the skirt does not read as stripes
    band3 = skirt & (li % 3 == 2)
    col = np.where(band3[..., None], M.leather(p, n, seed=64), col)
    col = lerp(col, M.LEATHER_HI * 1.2, 0.55 * band3 * D.stitch_row(u, (33.8 - z) - li * lame_h, 1.0, spacing=0.45))
    # mail showing through the front/back opening
    col = mail(col, p, n, lowz & opening, u, z)
    # leather hanger straps at the hips
    hang = lowz & (np.abs(np.abs(x) - 7.6) < 0.5) & (z > 30.2)
    col = D.strap(col, p, n, hang, np.abs(x) - 7.6, z, seed=63, width=1.0)
    # focal points: a grave-green stone at the gorget and on the belt buckle (front only)
    col = gem(col, n, np.where(front, np.hypot(x, z - 59.0), 99.0), 0.55)
    col = gem(col, n, np.where(front, np.hypot(x, z - 35.15), 99.0), 0.38)
    # raised centre ridge along each pauldron lame
    lr = sh & (np.abs(d_l - 1.35) < 0.10)
    col = lerp(col, M.STEEL_HI * 0.8, 0.35 * lr * M.lit(n))
    return col


def arms(tm):
    n = tm.nrm
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    p = D.mirror(tm.pos)
    ax = np.abs(x)
    ang = np.arctan2(z - 50.5, -y)
    u = np.abs(ang) * 3.4
    allm = np.ones(x.shape, bool)
    col = D.scale_field(M.leather(p, n), p, n, allm, u, ax, 1.5, seed=81)
    # outer plate (rerebrace) with lames
    outer = (z > 50.9) & (ax > 11.2) & (ax < 15.4)
    lm = (ax - 11.2) / 1.4
    d_o = np.minimum((lm - np.floor(lm)) * 1.4, (z - 50.9) * 1.5)
    col = D.plate(col, p, n, outer, d_o, seed=82, engrave=False, rivet_u=u * 1.4, rivet_spacing=1.3)
    # elbow cop with a side wing
    r = np.sqrt((ax - 16.8) ** 2 + (ang * 2.2) ** 2)
    cop = r < 1.6
    col = D.plate(col, p, n, cop, 1.6 - r, seed=83, engrave=True)
    centre = r < 0.24
    col = np.where(centre[..., None], lerp(M.PEWTER_DARK, M.STEEL_HI, 0.4 + 0.5 * M.lit(n)), col)
    # mail where the arm bends behind the elbow cop
    col = mail(col, p, n, (np.abs(ax - 16.8) < 2.0) & (np.abs(ang) > 1.9), u, ax)
    # strap with buckle around the upper arm
    st = np.abs(ax - 12.0) < 0.45
    col = D.strap(col, p, n, st & ~outer, ax - 12.0, u, seed=84, width=0.9, buckle_at=1.5)
    return col


def legs(tm):
    n = tm.nrm
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    p = D.mirror(tm.pos)
    ax = np.abs(x)
    ang = np.arctan2(ax - 3.6, -y)
    u = np.abs(ang) * 3.2
    allm = np.ones(x.shape, bool)
    col = D.scale_field(M.leather(p, n), p, n, allm, u, z, 1.35, seed=91)
    # cuisse: three lames on the front of the thigh
    cu = (np.abs(ang) < 1.0) & (z > 22.0) & (z < 34.0)
    lm = (34.0 - z) / 4.0
    d_c = np.minimum((lm - np.floor(lm)) * 4.0, (1.0 - np.abs(ang)) * 3.2)
    col = D.plate(col, p, n, cu, d_c, seed=92, engrave=True, rivet_u=u * 1.0, rivet_spacing=1.2)
    # knee cop with a fan
    r = np.sqrt((z - 19.7) ** 2 + (ang * 3.2) ** 2)
    knee = (r < 2.1) & (np.abs(ang) < 1.4)
    col = D.plate(col, p, n, knee, 2.1 - r, seed=93, engrave=True)
    col = np.where((knee & (r < 0.28))[..., None], lerp(M.PEWTER_DARK, M.STEEL_HI, 0.4 + 0.5 * M.lit(n)), col)
    # mail behind the knee
    col = mail(col, p, n, (np.abs(z - 19.7) < 2.2) & (np.abs(ang) > 2.3), u, z)
    # side lacing up the outer thigh
    lace = (np.abs(np.abs(ang) - 1.55) < 0.22) & (z > 22.0)
    col = D.lacing(col, p, n, lace, (np.abs(ang) - 1.55) * 3.2, z, seed=94, spacing=1.0, width=1.1)
    # thigh strap with buckle on the outside
    st = np.abs(z - 27.6) < 0.45
    col = D.strap(col, p, n, st & ~cu, z - 27.6, u, seed=95, width=0.9, buckle_at=4.6)
    return col


def gloves(tm):
    n = tm.nrm
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    p = D.mirror(tm.pos)
    ax = np.abs(x)
    u = np.abs(np.arctan2(z - 45.5, -y)) * 1.8
    col = M.leather(p, n, seed=101)
    # stitched seams along the leather fingers/palm
    seam = D.stitch_row(ax * 2.0, u, 1.1, spacing=0.4, length=0.2, width=0.05)
    col = lerp(col, M.LEATHER_HI * 1.2, 0.6 * seam)
    back = n[..., 2] > 0.2
    # flared cuff: lames with rivets
    cuff = (ax > 17.4) & (ax < 21.2)
    lm = (ax - 17.4) / 1.27
    d_c = (lm - np.floor(lm)) * 1.27
    col = D.plate(col, p, n, cuff, d_c, seed=102, engrave=False, rivet_u=u * 2.0, rivet_spacing=1.1)
    # hand plate with rivets, finger lames
    hand = back & (ax >= 21.2) & (ax < 23.5)
    col = D.plate(col, p, n, hand, np.minimum(ax - 21.2, 23.5 - ax) * 1.6, seed=103, engrave=True,
                  rivet_u=u * 2.0, rivet_spacing=1.0)
    knuckle = back & (np.abs(ax - 23.35) < 0.22) & (np.abs(((u * 2.0) / 0.9) - np.floor((u * 2.0) / 0.9) - 0.5) < 0.22)
    col = np.where(knuckle[..., None], lerp(M.PEWTER_DARK, M.STEEL_HI, 0.35 + 0.5 * M.lit(n)), col)
    fing = back & (ax >= 23.5)
    fl = (ax - 23.5) / 0.55
    col = D.plate(col, p, n, fing, (fl - np.floor(fl)) * 0.55 * 2.0, seed=104, engrave=False, rim=0.25)
    return col


def boots(tm):
    n = tm.nrm
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    p = D.mirror(tm.pos)
    ax = np.abs(x)
    ang = np.arctan2(ax - 3.8, -y)
    u = np.abs(ang) * 3.0
    # same scale shirt as the leggings so boots and legs read as one suit
    allm = np.ones(x.shape, bool)
    col = D.scale_field(M.leather(p, n, seed=111), p, n, allm, u, z, 1.35, seed=91)
    # greave: front plate in lames like the cuisses, rolled top, rivets down the sides
    gr = (np.abs(ang) < 1.25) & (z > 4.4) & (z < 23.4)
    gl = (23.4 - z) / 4.75
    d_g = np.minimum.reduce([(1.25 - np.abs(ang)) * 3.0, z - 4.4, (gl - np.floor(gl)) * 4.75])
    col = D.plate(col, p, n, gr, d_g, seed=113, engrave=True, rivet_u=u, rivet_spacing=1.2)
    col = M.trim(col, p, n, (gr & (np.abs(ang) < 0.06) & (d_g > 0.9)).astype(float) * 0.6)
    # ankle strap with buckle
    st = (np.abs(z - 4.0) < 0.42)
    col = D.strap(col, p, n, st, z - 4.0, u, seed=114, width=0.84, buckle_at=4.5)
    # sabaton lames over the foot
    foot = (z < 3.6) & (y < -1.2)
    fl = (-y - 1.2) / 1.05
    col = D.plate(col, p, n, foot, (fl - np.floor(fl)) * 1.05 * 1.4, seed=115, engrave=False, rim=0.3)
    sole = z < 0.6
    col = np.where(sole[..., None], M.LEATHER * 0.5, col)
    return col


def helm(tm):
    n = tm.nrm
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    p = D.mirror(tm.pos)
    ax = np.abs(x)
    zr = (z - 58.7) / 14.9
    front = y < -2.6
    col = M.steel(p, n, np.full(x.shape, 0.6), seed=121)
    # layered fins on the sides
    fin = (ax > 3.6) & (zr > 0.55)
    fl = (zr - 0.55) / 0.11
    col = D.plate(col, p, n, fin, (fl - np.floor(fl)) * 1.6, seed=122, engrave=False, rim=0.3)
    # crest ridge over the top and down the face
    ridge = (ax < 0.32) & (zr > 0.66)                  # crest only, never a cross down the face
    col = M.trim(col, p, n, ridge.astype(float) * 0.7)
    # brow band with rivets
    brow = front & (zr > 0.58) & (zr < 0.66)
    col = D.plate(col, p, n, brow, np.minimum(zr - 0.58, 0.66 - zr) * 14.9, seed=123, engrave=False, rim=0.22,
                  rivet_u=ax, rivet_spacing=1.1)
    # eye slits: deep shadow with a faint grave-green glow in the middle
    eye = front & (zr > 0.50) & (zr < 0.565) & (ax > 0.55) & (ax < 2.7)
    col = M.trim(col, p, n, (front & (np.abs(zr - 0.495) < 0.012) & (ax > 0.5) & (ax < 2.8)).astype(float) * 0.7)
    # breathing holes on the lower face plate
    bh = front & (zr > 0.22) & (zr < 0.42) & (ax > 0.7) & (ax < 2.3)
    gx = (ax / 0.42) - np.floor(ax / 0.42) - 0.5
    gz = (zr / 0.045) - np.floor(zr / 0.045) - 0.5
    hole = bh & (np.sqrt(gx ** 2 + gz ** 2) < 0.22)
    col = np.where(hole[..., None], M.STEEL_DARK * 0.25, col)
    # rolled bottom rim
    col = M.trim(col, p, n, (zr < 0.06).astype(float) * 0.9)
    # two burning grave-green eyes, painted only where every surface sharing the texel is inside the slit
    def slit(q):
        qx, qy, qz = np.abs(q[..., 0]), q[..., 1], (q[..., 2] - 58.7) / 14.9
        return (qy < -2.6) & (qz > 0.505) & (qz < 0.558) & (qx > 0.75) & (qx < 2.55)
    inside = slit(tm.pos) & (~tm.mirror | slit(tm.pos2))
    de = np.sqrt(((ax - 1.6) / 0.55) ** 2 + ((zr - 0.531) / 0.024) ** 2)
    core = np.clip(1 - de / 0.75, 0, 1) ** 0.8
    halo = np.clip(1 - de / 1.6, 0, 1)
    glow = lerp(M.GHOST * 0.9, np.array([235, 255, 240.0]), core)
    col = np.where(inside[..., None], lerp(M.STEEL_DARK * 0.15, glow, np.clip(halo + core, 0, 1)[..., None]), col)
    return col


def interlace(s, w, period=2.4):
    """Two-strand Celtic plait along a band: s runs along the band, w in [0,1] across it.

    Returns (strand mask, shade). Strands cross every half period, alternating over/under,
    with a dark gap where one passes beneath the other.
    """
    phase = 2 * np.pi * s / period
    a = 0.5 + 0.30 * np.sin(phase)
    b = 0.5 - 0.30 * np.sin(phase)
    width = 0.13
    da, db = np.abs(w - a), np.abs(w - b)
    on_a, on_b = da < width, db < width
    a_over = np.cos(phase) > 0                     # which strand is on top alternates each crossing
    top = np.where(a_over, on_a, on_b)
    under = np.where(a_over, on_b, on_a) & ~top
    near_cross = np.abs(np.sin(phase)) < 0.22
    gap = under & near_cross & (np.minimum(np.where(a_over, da, db), 1) < width + 0.07)
    strand = (top | (under & ~gap))
    rib = 1 - np.minimum(np.where(top, np.where(a_over, da, db), np.where(a_over, db, da)) / width, 1)
    return strand, rib, gap


def cloak(tm):
    """Midnight-black wool, a U-shaped ancient Celtic interlace border, fur on the outer edges."""
    n = tm.nrm
    x, y, z = tm.pos[..., 0], tm.pos[..., 1], tm.pos[..., 2]
    p = D.mirror(tm.pos)
    ax = np.abs(x)
    cov = tm.covered
    # the cloak's own outline: outer edge per height and hem per width, measured from the mesh
    zb = np.clip(((z - 6.0) / 0.5).astype(int), 0, 140)
    edge_by_z = np.zeros(141)
    np.maximum.at(edge_by_z, zb[cov], ax[cov])
    edge_by_z = np.maximum.accumulate(edge_by_z[::-1])[::-1] * 0 + np.array(
        [edge_by_z[max(0, i - 3):i + 4].max() for i in range(141)])
    d_edge = edge_by_z[zb] - ax
    xb = np.clip((ax / 0.5).astype(int), 0, 30)
    hem_by_x = np.full(31, 99.0)
    np.minimum.at(hem_by_x, xb[cov], z[cov])
    d_hem = z - hem_by_x[xb]

    wool = np.array([10, 10, 13.0])                     # midnight-black leather
    sheen = np.array([46, 46, 54.0])                    # dull, slightly cold sheen
    g = fbm3(p * np.array([1, 1, 2.0]), 1.4, 4, 131)
    fold = fbm3(p * np.array([2.0, 2.0, 0.25]), 1.0, 2, 132)
    col = lerp(wool * 0.75, wool * 1.7, 0.40 * g)
    # broad soft sheen on the folds (dull, never glossy)
    col = lerp(col, sheen, 0.38 * smoothstep(0.5, 0.9, fold) * (0.3 + 0.7 * M.lit(n) ** 2))
    # weathering: fine creases, cracked grain, pale scuffs on raised areas, darker grime in the folds
    crease = np.abs(np.sin((p[..., 2] * 2.4 + 5.0 * fbm3(p, 0.9, 2, 141)) * 2.0))
    col = lerp(col, wool * 0.45, 0.45 * smoothstep(0.96, 1.0, crease))
    crack = fbm3(p * np.array([3.0, 3.0, 3.0]), 2.6, 3, 142)
    col = lerp(col, wool * 0.4, 0.35 * smoothstep(0.62, 0.70, crack) * (1 - smoothstep(0.70, 0.78, crack)))
    scuff = smoothstep(0.66, 0.82, fbm3(p, 3.2, 3, 143)) * smoothstep(0.55, 0.9, fold)
    col = lerp(col, np.array([62, 58, 56.0]), 0.30 * scuff)
    col = lerp(col, wool * 0.5, 0.30 * (1 - smoothstep(0.2, 0.5, fold)))
    col = M.shade(col, n, 0.55 + 0.3 * g)

    # faint spectral mist only near the hem
    wisp = fbm3(p * np.array([1.4, 1.4, 0.45]), 1.0, 4, 133)
    mist = (1 - smoothstep(0.0, 9.0, d_hem)) * smoothstep(0.35, 0.85, wisp)
    col = lerp(col, M.GHOST * 0.45, 0.35 * mist)

    # U-shaped interlace border: down both sides and across the bottom, inside the fur/hem
    bw = 1.9
    band_top = 47.5
    side = (d_edge > 1.2) & (d_edge < 1.2 + bw) & (z > 9.0) & (z < band_top)
    bottom = (d_hem > 2.2) & (d_hem < 2.2 + bw) & (d_edge > 1.2)
    w_side = (d_edge - 1.2) / bw
    w_bot = (d_hem - 2.2) / bw
    band = side | bottom
    s_band = np.where(side & ~bottom, z, ax + 60.0)
    w_band = np.where(side & ~bottom, w_side, w_bot)
    strand, rib, gap = interlace(s_band, w_band)
    thread = lerp(M.PEWTER_DARK * 1.0, M.PEWTER * 0.95, 0.35 + 0.65 * rib)
    worn = fbm3(p, 3.5, 3, 138)
    thread = lerp(thread, wool * 2.0, 0.35 * smoothstep(0.6, 0.85, worn))
    col = np.where((band & strand)[..., None], M.shade(thread, n, np.full(z.shape, 0.85)), col)
    col = np.where((band & gap)[..., None], wool * 0.35, col)
    rail = band & ((w_band < 0.07) | (w_band > 0.93))
    cap = (d_edge > 1.2) & (d_edge < 1.2 + bw) & (np.abs(z - band_top) < 0.18)
    rail = rail | cap
    col = np.where(rail[..., None], M.shade(lerp(M.LEATHER, M.LEATHER_HI, 0.5), n, np.full(z.shape, 0.8)), col)

    # layered tatters along the hem
    fray = fbm3(p * np.array([5.0, 5.0, 0.4]), 1.0, 2, 135)
    col = lerp(col, wool * 0.4, 0.75 * (d_hem < 1.4 + 1.2 * fray))

    # fur along the outer edges and the shoulder mantle: dark, clumped, light catching the tips
    fur_w = 1.1 + 1.4 * smoothstep(band_top, 56.2, z)    # edge fur widens into the mantle
    fur_zone = ((d_edge < fur_w) & (z > 9.0)) | (z > 56.2)
    fu = fbm3(p * np.array([7.0, 7.0, 2.2]), 1.0, 3, 139)
    strands = np.abs(np.sin((p[..., 0] * 3.1 + p[..., 2] * 0.6 + 4.0 * fu) * 5.0))
    fur = lerp(np.array([16, 14, 13.0]), np.array([70, 64, 58.0]), 0.25 * fu + 0.45 * smoothstep(0.75, 1.0, strands))
    fur = M.shade(fur, n, 0.5 + 0.4 * fu)
    col = np.where(fur_zone[..., None], fur, col)
    # silver clasp on the mantle
    clasp = (z > 57.6) & (z < 60.2) & (ax > 6.0) & (ax < 8.0)
    col = np.where(clasp[..., None], M.shade(lerp(M.PEWTER_DARK, M.PEWTER, 0.7), n, np.full(z.shape, 0.9)), col)
    return col

def variants(part, sex, order):
    return [f"{part}{i:02d}_BC_{sex}" for i in order]


# Every variant the client might pick shares the texture: paint them all (see bake_union).
JOBS = {
    "body_m": (variants("Body", "m", (5, 6, 3, 4, 2, 1, 8, 7)), body, 1024, (512, 1024)),
    "body_f": (variants("Body", "f", (5, 6, 3, 4, 2, 1, 8, 7)), body, 1024, (512, 1024)),
    "arms": (["Arms01_BC_m"], arms, 512, (256, 512)),
    "legs": (["Legs01_BC_m"], legs, 512, (256, 512)),
    "gloves": (variants("Gloves", "m", (4, 5, 6, 1, 2, 3, 7, 8)), gloves, 512, (256, 256)),
    "boots": (variants("Boots", "m", (4, 5, 6, 1, 2, 3, 7, 8)), boots, 512, (256, 256)),
    "helm": (["ADR_Dragonsworn_Helm_Heavy_BC_m"], helm, 512, (256, 256)),
    # cloaks: Cloak01 (hood down) first, Cloak02 (hood up), Cloak03; painted on UV set 1 (see bake_union call)
    "cloak": (["Cloak01_cel_m", "Cloak02_cel_m", "Cloak03_cel_m"], cloak, 1024, (512, 1024)),
}

if __name__ == "__main__":
    for key in (sys.argv[1:] or JOBS):
        nifs, fn, bake, size = JOBS[key]
        tm = bake_union(nifs, bake, uv_set=1 if key == "cloak" else 0)   # cata cloak skin uses UV set 1
        atlas = fn(tm)
        atlas[~tm.covered] = atlas[tm.covered].mean(0)
        M.finish(atlas, tm.covered, size).save(M.OUT / f"sluagh_{key}.png")
        print("painted", key, flush=True)
