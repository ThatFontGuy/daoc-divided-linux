"""Detail painting for the Dubh Sluagh set: plate edges, rivets, straps, stitching, lacing.

All functions are symmetric: callers pass mirrored positions (|x|) for noise, and edge
distances computed from |x|, so the left and right halves match like stock DAoC armor.
"""
import numpy as np
from armorpaint import fbm3, smoothstep, lerp
import paint_sluagh_armor as M


def mirror(p):
    q = p.copy()
    q[..., 0] = np.abs(q[..., 0])
    return q


def plate(col, p, n, inside, d, seed, base_relief=0.62, rivet_u=None, rivet_spacing=1.7,
          engrave=True, rim=0.55):
    """Paint a plate where `inside`, d = distance (model units) from the plate's border.

    Rolled silver rim, dark groove, an engraved inner border line, and rivets just inside
    the rim when rivet_u (coordinate along the border) is given.
    """
    rel = base_relief + 0.25 * smoothstep(0.6, 2.6, d)
    groove = smoothstep(rim, rim + 0.12, d) * (1 - smoothstep(rim + 0.12, rim + 0.30, d))
    rel = np.clip(rel - 0.55 * groove, 0, 1)
    pc = M.steel(p, n, rel, seed)
    if engrave:
        line = 1 - smoothstep(0.0, 0.07, np.abs(d - 1.25))
        lite = 1 - smoothstep(0.0, 0.07, np.abs(d - 1.36))
        pc = lerp(pc, M.STEEL_DARK * 0.8, 0.75 * line)
        pc = lerp(pc, M.STEEL_HI * 0.8, 0.35 * lite)
    rim_m = 1 - smoothstep(rim - 0.06, rim, d)
    pc = M.trim(pc, p, n, rim_m)
    # rolled-rim highlight on the inner half of the rim
    pc = lerp(pc, M.STEEL_HI, 0.35 * rim_m * smoothstep(0.15, 0.4, d) * M.lit(n))
    if rivet_u is not None:
        fu = rivet_u / rivet_spacing
        fu = fu - np.floor(fu) - 0.5
        dist = np.sqrt((fu * rivet_spacing) ** 2 + (d - (rim + 0.42)) ** 2)
        head = smoothstep(0.26, 0.10, dist)
        shadow = smoothstep(0.34, 0.18, np.sqrt((fu * rivet_spacing + 0.07) ** 2 + (d - (rim + 0.42) + 0.08) ** 2))
        pc = lerp(pc, M.STEEL_DARK, 0.6 * shadow * (1 - head))
        pc = lerp(pc, lerp(M.PEWTER_DARK, M.STEEL_HI, 0.35 + 0.6 * M.lit(n)), head)
    return np.where(inside[..., None], pc, col)


def stitch_row(u, v, row_v, spacing=0.42, length=0.22, width=0.05):
    fu = (u / spacing) - np.floor(u / spacing)
    on = (fu < length / spacing * 1.0)
    return on & (np.abs(v - row_v) < width)


def strap(col, p, n, inside, d_across, u_along, seed, width=0.9, buckle_at=None):
    """Leather strap where `inside`; d_across = signed distance from strap centre."""
    s = M.leather(p, n, seed)
    edge = smoothstep(width * 0.5 - 0.12, width * 0.5, np.abs(d_across))
    s = lerp(s, M.LEATHER * 0.35, 0.7 * edge)
    st = stitch_row(u_along, np.abs(d_across), width * 0.5 - 0.2, width=0.045)
    s = lerp(s, M.LEATHER_HI * 1.25, 0.8 * st)
    if buckle_at is not None:
        bu = np.abs(u_along - buckle_at)
        frame = (bu < 0.75) & (np.abs(d_across) < width * 0.5 + 0.18)
        ring = frame & ((bu > 0.52) | (np.abs(d_across) > width * 0.5 - 0.02))
        tongue = (bu < 0.6) & (np.abs(d_across) < 0.07)
        metal = lerp(M.PEWTER_DARK, M.PEWTER, 0.45 + 0.5 * M.lit(n))
        s = np.where((ring | tongue)[..., None], M.shade(metal, n, np.full(bu.shape, 0.9)), s)
    return np.where(inside[..., None], s, col)


def lacing(col, p, n, inside, u, v, seed, spacing=0.9, width=1.0):
    """Criss-cross leather lacing over a dark gap (back of calf / side of thigh)."""
    gap = M.LEATHER * 0.25
    fv = (v / spacing) - np.floor(v / spacing)
    a = np.abs(u - (fv - 0.5) * width) < 0.12
    b = np.abs(u + (fv - 0.5) * width) < 0.12
    cord = lerp(M.LEATHER_HI, M.LEATHER, 0.4)
    c = np.where((a | b)[..., None], M.shade(cord, n, np.full(u.shape, 0.8)), gap)
    eyelet = (np.abs(np.abs(u) - width * 0.5) < 0.12) & (np.abs(fv - 0.5) < 0.1) | (np.abs(np.abs(u) - width * 0.5) < 0.12) & ((fv < 0.08) | (fv > 0.92))
    c = np.where(eyelet[..., None], M.PEWTER, c)
    return np.where(inside[..., None], c, col)


def scale_field(col, p, n, inside, u, v, size, seed):
    """Scales with a central rib, a rivet at the top of each and per-scale variation."""
    rel = np.zeros(u.shape)
    M.scales(u, v, size, rel)
    tint = M.scales.tint
    rowh = size * 0.62
    row = np.floor(v / rowh)
    uu = u / size + 0.5 * (row % 2)
    fu = uu - np.floor(uu) - 0.5
    fv = v / rowh - row
    sc = M.steel(p, n, 0.22 + 0.78 * rel, seed)
    sc = sc * (0.80 + 0.22 * tint)[..., None]
    rib = (np.abs(fu) < 0.05) & (fv > 0.18) & (fv < 0.8)
    sc = lerp(sc, M.STEEL_HI * 0.8, 0.22 * rib * rel)
    riv = np.sqrt((fu * size) ** 2 + ((fv - 0.8) * rowh) ** 2) < 0.16
    sc = lerp(sc, lerp(M.PEWTER_DARK, M.PEWTER, 0.6), 0.85 * riv)
    sc = lerp(sc, M.STEEL_DARK * 0.6, 0.65 * (1 - smoothstep(0.02, 0.22, rel)))
    return np.where(inside[..., None], sc, col)
