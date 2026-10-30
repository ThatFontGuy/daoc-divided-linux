"""Procedural armor painting in model space, baked into a UV atlas.

Every pattern is a function of the 3D surface point a texel covers, so it is
continuous across UV seams (no back seam) and symmetric when written in |x|.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


# ---------------------------------------------------------------- noise ----
def _hash3(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 144269504) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def value_noise3(p, scale, seed=0):
    """Smooth 3D value noise in [0,1]; p is (...,3)."""
    q = p / scale
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((f[..., 0] if dx else 1 - f[..., 0]) *
                     (f[..., 1] if dy else 1 - f[..., 1]) *
                     (f[..., 2] if dz else 1 - f[..., 2]))
                out = out + w * _hash3(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def fbm3(p, scale, octaves=4, seed=0):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + amp * value_noise3(p, scale / (2 ** o), seed + o * 17)
        norm += amp
        amp *= 0.5
    return total / norm


def sym(p):
    """Mirror to +x so left/right sides get identical patterns."""
    q = p.copy()
    q[..., 0] = np.abs(q[..., 0])
    return q


# -------------------------------------------------------------- helpers ----
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def band_coordinate(value, spacing, offset=0.0):
    """Return (index, fraction) of repeating bands along a coordinate."""
    q = (value - offset) / spacing
    idx = np.floor(q)
    return idx, q - idx


def edge_profile(frac, width):
    """0 at a band border, 1 in the middle; width is fraction of band."""
    return smoothstep(0.0, width, frac) * smoothstep(0.0, width, 1 - frac)


def lerp(a, b, t):
    """Blend colors a->b by t. Colors are (...,3) or (3,); t is (...) or (...,1)."""
    t = np.asarray(t, dtype=float)
    if t.ndim and t.shape[-1] != 1:
        t = t[..., None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


# ------------------------------------------------------------ materials ----
RUSTED_IRON = dict(
    base=np.array([98, 98, 100], float),       # dull blackened iron
    dark=np.array([46, 46, 50], float),
    rust=np.array([112, 72, 48], float),       # brown rust, not copper
    rust_dark=np.array([62, 42, 32], float),
    highlight=np.array([176, 172, 164], float),
)

DARK_LEATHER = dict(
    base=np.array([70, 52, 38], float), dark=np.array([36, 26, 20], float),
    rust=np.array([88, 66, 44], float), rust_dark=np.array([48, 34, 24], float),
    highlight=np.array([108, 84, 60], float),
)


def metal(p, n, relief, material=RUSTED_IRON, rust_amount=0.55, seed=3):
    """Shade metal: relief in [0,1] (0 = groove/edge, 1 = plate face)."""
    m = material
    grain = fbm3(p, 1.2, 3, seed)
    rust_field = fbm3(p, 3.5, 4, seed + 101)
    streak = fbm3(p * np.array([3.0, 3.0, 0.35]), 2.0, 3, seed + 202)  # vertical run-off
    # Rust gathers in grooves and plate edges (low relief) more than on faces.
    field = 0.55 * rust_field + 0.30 * streak + 0.30 * (1 - np.clip(relief, 0, 1))
    rust = smoothstep(1 - rust_amount - 0.10, 1 - rust_amount + 0.30, field)
    col = lerp(m["base"], m["dark"], 0.35 * (1 - grain))
    rusty = lerp(m["rust"], m["rust_dark"], smoothstep(0.3, 0.9, fbm3(p, 0.8, 2, seed + 7)))
    col = lerp(col, rusty, rust)
    # Relief: grooves dark, faces lit from above (baked, gentle), top edges catch light.
    up = np.clip(n[..., 2] * 0.5 + 0.5, 0, 1)
    shade = 0.62 + 0.30 * relief + 0.14 * (up - 0.5)
    col = col * shade[..., None]
    rim = smoothstep(0.55, 0.9, relief) * (1 - smoothstep(0.9, 1.0, relief))
    col = lerp(col, m["highlight"] * (1 - 0.5 * rust)[..., None], 0.18 * rim)
    return col


def rivets(coord_u, coord_v, spacing_u, row_v, radius, active):
    """Soft round rivets along a row at coord_v == row_v, repeating every spacing_u."""
    iu, fu = band_coordinate(coord_u, spacing_u)
    du = (fu - 0.5) * spacing_u
    dv = coord_v - row_v
    d = np.sqrt(du * du + dv * dv)
    head = smoothstep(radius, radius * 0.4, d) * active
    return head


def cloth(p, color, weave=0.22, wear=0.35, seed=61):
    """Coarse woven cloth: fine two-way weave, fbm dirt, frayed wear."""
    color = np.asarray(color, float)
    wx = 0.5 + 0.5 * np.sin((p[..., 0] + p[..., 1]) / weave * np.pi)
    wz = 0.5 + 0.5 * np.sin(p[..., 2] / weave * np.pi)
    weave_v = 0.88 + 0.12 * (wx * wz)
    dirt = fbm3(p, 2.4, 4, seed)
    blotch = smoothstep(0.55, 0.85, fbm3(p, 1.1, 3, seed + 3))
    col = color * (0.70 + 0.45 * dirt)[..., None] * weave_v[..., None]
    col = lerp(col, color * 0.45, wear * blotch)
    return col


def fur(p, n, color, seed=71):
    """Short matted fur/hide: streaky, clumped, darker at the roots."""
    color = np.asarray(color, float)
    streak = fbm3(p * np.array([3.5, 3.5, 0.6]), 1.0, 4, seed)
    clump = fbm3(p, 0.5, 3, seed + 5)
    v = 0.55 + 0.55 * streak * (0.7 + 0.3 * clump)
    return color * v[..., None] * (0.85 + 0.15 * np.clip(n[..., 2:3] * 0.5 + 0.5, 0, 1))


def rope(u, v, color=(122, 104, 74), twist=0.9):
    """Twisted rope along u, v across its width in [0,1]."""
    color = np.asarray(color, float)
    strand = 0.5 + 0.5 * np.sin((u / twist + v * 2.2) * 2 * np.pi)
    edge = 1 - np.abs(v * 2 - 1) ** 2
    return color * (0.45 + 0.55 * strand * edge)[..., None]


def spiral_mark(a, b, radius, turns=2.4, width=0.35):
    """Chalk spiral centred at (0,0) in a local 2D coordinate (a, b); 1 on the line."""
    r = np.sqrt(a * a + b * b)
    theta = np.arctan2(b, a)
    step = radius / turns
    k = np.round((r / step) - (theta + np.pi) / (2 * np.pi))
    arm = step * (k + (theta + np.pi) / (2 * np.pi))
    d = np.abs(r - arm)
    return (1 - smoothstep(width * 0.5, width, d)) * (r < radius)


def chainmail(u, v, ring=0.62, light=np.array([112, 110, 108.0]), dark=np.array([34, 33, 34.0]), rust=None):
    """Interlocking ring pattern on a 2D surface coordinate (u, v) in model units."""
    row = np.floor(v / ring)
    uu = u / ring + 0.5 * (row % 2)
    fu = uu - np.floor(uu) - 0.5
    fv = v / ring - row - 0.5
    d = np.sqrt(fu * fu + fv * fv)
    ring_body = smoothstep(0.18, 0.30, d) * (1 - smoothstep(0.42, 0.52, d))
    top_light = 0.65 + 0.35 * np.clip(-fv * 2, 0, 1)
    col = lerp(dark, light * top_light[..., None], ring_body)
    if rust is not None:
        col = lerp(col, np.array([96, 62, 42.0]) * (0.6 + 0.4 * ring_body)[..., None], rust)
    return col


def finish(atlas: np.ndarray, covered: np.ndarray, blur=0.6):
    img = Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8))
    if blur:
        soft = img.filter(ImageFilter.GaussianBlur(blur))
        arr = np.asarray(img).astype(float) * 0.55 + np.asarray(soft).astype(float) * 0.45
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return img
