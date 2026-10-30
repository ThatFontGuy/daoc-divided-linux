"""Zombie Magician body atlas: a void-touched grave mage.

Private copy of the Hibernian undead male (h_elfmon01 / e_unde01). The pet now
casts the Eldritch Void Bolt visual, so its robe carries the same violet void
glow: trim along the neckline, front opening and hem, a column of void runes
down the chest, and rune bands at the cuffs. Painted in model space.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from armorpaint import (DARK_LEATHER, band_coordinate, cloth, fbm3, lerp, metal,
                        smoothstep, sym)
from paint_sturdy import grave_pallor
from regions import classify
from texelmap import bake, render_views

NIF = "H_ElfMon01.NIF"
VOID = np.array([176, 112, 255.0])      # glow core
VOID_DEEP = np.array([74, 36, 120.0])   # glow falloff
SILVER = dict(base=np.array([150, 150, 158.0]), dark=np.array([70, 70, 80.0]),
              rust=np.array([90, 88, 96.0]), rust_dark=np.array([50, 48, 56.0]),
              highlight=np.array([210, 210, 220.0]))


def glow_line(distance, width):
    """Bright core with a soft halo, from a distance-to-line field."""
    core = 1 - smoothstep(width * 0.35, width * 0.6, distance)
    halo = 1 - smoothstep(width * 0.6, width * 2.2, distance)
    return core, halo


def rune(a, b, size, kind):
    """Simple angular void runes in a local (a, b) cell; returns line mask 0..1."""
    w = size * 0.13
    lines = []
    if kind == 0:   # diamond with a dot
        lines.append(np.abs(np.abs(a) + np.abs(b) - size * 0.45))
        lines.append(np.sqrt(a * a + b * b) - size * 0.05)
    elif kind == 1:  # vertical stroke with two branches (ogham-like)
        lines.append(np.abs(a))
        lines.append(np.where(b > 0, np.abs(a - b * 0.8), 9.0))
        lines.append(np.where(b < 0, np.abs(a + b * 0.8), 9.0))
    else:            # ring with a bar
        lines.append(np.abs(np.sqrt(a * a + b * b) - size * 0.35))
        lines.append(np.where(np.abs(a) < size * 0.45, np.abs(b), 9.0))
    d = np.min(np.stack(lines), axis=0)
    inside = (np.abs(a) < size * 0.5) & (np.abs(b) < size * 0.5)
    return (1 - smoothstep(w * 0.5, w, d)) * inside


def paint(out_png: Path):
    tm, _ = bake(NIF)
    region, L = classify(tm)
    base = np.asarray(Image.open(HERE / "originals" / "e_unde01.png").convert("RGB")).astype(float)
    atlas = base.copy()

    p, n = tm.pos, tm.nrm
    ps = sym(p)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    front = y < 0.3
    cov = tm.covered
    shoulder, waist, hip, knee, ankle = (L["shoulder_z"], L["waist_z"], L["hip_z"], L["knee_z"], L["ankle_z"])

    def apply(mask, color, amount=1.0):
        nonlocal atlas
        m = np.clip(mask.astype(float) * amount, 0, 1)
        atlas = atlas * (1 - m[..., None]) + np.asarray(color, float) * m[..., None]

    head = (region == "head") & cov
    hands = (region == "hand") & cov
    torso = np.isin(region, ["neck", "chest", "back", "belly", "hips"]) & cov
    arm = np.isin(region, ["upperarm", "forearm"]) & cov
    leg = np.isin(region, ["thigh", "shin", "foot"]) & cov

    apply(head | hands, grave_pallor(base))

    # ----------------------------------------------------------------- robe
    neckline = np.where(front, shoulder + 1.0 + 0.06 * ax ** 2, shoulder + 3.0)
    hem = knee + 6.0 + 0.8 * (fbm3(ps * np.array([1, 1, 0.1]), 1.3, 3, 111) - 0.5)
    robe = (torso | ((region == "thigh") & cov)) & (z <= neckline) & (z >= hem)
    wool = cloth(ps, (40, 42, 62), weave=0.18, wear=0.30, seed=113)
    folds = 0.82 + 0.18 * np.sin(ax * 2.2 + 1.1 * fbm3(ps, 2.0, 2, 115))
    wool = wool * folds[..., None]
    apply(robe, wool)
    sleeve = arm
    sleeve_folds = 0.84 + 0.2 * fbm3(ps * np.array([0.6, 2.5, 2.5]), 1.2, 3, 114)
    sleeve_cloth = cloth(ps, (40, 42, 62), weave=0.12, wear=0.30, seed=114)
    apply(sleeve, sleeve_cloth * sleeve_folds[..., None])

    # Glowing void trim: neckline, the front opening (centre line) and hem.
    d_neck = np.abs(z - (neckline - 0.35))
    d_open = np.where(front & (z < neckline) & (z > hem), ax, 99.0)
    d_hem = np.abs(z - (hem + 0.35))
    trim_d = np.minimum(np.minimum(d_neck, d_open), d_hem)
    core, halo = glow_line(trim_d, 0.55)
    apply(robe & (halo > 0.01), VOID_DEEP, 0.55 * halo)
    apply(robe & (core > 0.01), VOID, core)

    # Column of void runes down the chest, either side of the glowing opening.
    rune_zone = robe & front & (z < shoulder - 2.0) & (z > waist - 1.5)
    cell = 2.3
    iz, fz = band_coordinate(z, cell, waist - 1.5)
    a = ax - 1.5
    b = (fz - 0.5) * cell
    kinds = (iz.astype(int) % 3)
    marks = np.zeros_like(z)
    for k in range(3):
        marks = np.where(kinds == k, rune(a, b, cell * 0.62, k), marks)
    flicker = 0.55 + 0.45 * smoothstep(0.3, 0.7, fbm3(p, 1.5, 2, 116))
    apply(rune_zone & (marks > 0.02), VOID_DEEP, 0.9 * marks)
    apply(rune_zone & (marks > 0.02), VOID, 0.65 * marks * flicker)
    apply(rune_zone & (marks > 0.02), VOID_DEEP, 0.0)

    # Faint void sigil between the shoulder blades: ring and inner triangle.
    bz = shoulder - 7.0
    rb = np.sqrt(x ** 2 + (z - bz) ** 2)
    tri = np.maximum(np.maximum(-(z - bz) - 1.1, (z - bz) * 0.5 + ax * 0.866 - 1.1), 0)
    ring_d = np.abs(rb - 2.6)
    tri_d = np.abs(np.maximum((z - bz) * 0.5 + ax * 0.866, -(z - bz)) - 1.2)
    sig = (1 - smoothstep(0.12, 0.3, np.minimum(ring_d, tri_d))) * (rb < 3.0)
    back_zone = robe & ~front
    apply(back_zone & (sig > 0.02), VOID_DEEP, 0.85 * sig)
    apply(back_zone & (sig > 0.02), VOID, 0.45 * sig)

    # Cuff rune bands.
    cuff_x = L["wrist_x"] - 1.6
    cuff = sleeve & (np.abs(ax - cuff_x) < 1.2)
    ccore, chalo = glow_line(np.abs(ax - cuff_x), 0.9)
    apply(cuff, VOID_DEEP, 0.6 * chalo)
    apply(cuff, VOID, 0.9 * ccore * (0.6 + 0.4 * (np.sin(np.arctan2(z - np.median(z[arm]), y) * 6) > 0)))

    # ---------------------------------------------------------- hooded mantle
    mantle = (torso | arm) & (z > shoulder - 3.2 - 0.8 * fbm3(ps, 1.1, 2, 117)) & \
             (ax < L["shoulder_x"] + 2.8) & (z <= neckline + 2.5)
    mantle &= ~(front & (ax < 1.2 + 0.35 * (shoulder + 2.5 - z)))
    dark = cloth(ps, (26, 26, 36), weave=0.16, wear=0.25, seed=119)
    apply(mantle, dark)
    apply(mantle & (np.abs(z - (shoulder - 3.2)) < 0.35), VOID_DEEP * 0.8)
    clasp = front & torso & (np.abs(ax - 2.2) < 0.55) & (np.abs(z - (shoulder - 0.2)) < 0.55)
    apply(clasp, metal(ps, n, 0.9, SILVER, 0.1, 121))

    # --------------------------------------------------------- legs and feet
    legs = leg & (z < hem + 0.1) & (z > ankle + 3.2)
    apply(legs, cloth(ps, (32, 30, 36), weave=0.16, wear=0.3, seed=123))
    boot = leg & (z <= ankle + 3.2)
    apply(boot, metal(ps, n, 0.6, DARK_LEATHER, 0.3, 125) * 0.8)

    Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8)).save(out_png)
    return out_png


if __name__ == "__main__":
    out = HERE / "work" / "magician_v3.png"
    out.parent.mkdir(exist_ok=True)
    paint(out)
    render_views(NIF, Image.open(out), views=[("front", (0, -1, 0)), ("back", (0, 1, 0)),
                                              ("3/4 front", (0.7, -0.7, 0.15)), ("3/4 back", (-0.6, 0.8, 0.1))],
                 width=460, height=720, label="Zombie Magician v3 (Claude)").save(HERE / "work" / "magician_v3_render.png")
    print("wrote", out)
