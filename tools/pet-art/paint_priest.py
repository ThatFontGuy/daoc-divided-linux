"""Zombie Priest body atlas: a cairn priestess (healer).

Private copy of the Avalonian undead female (b_avmon01f / a_unde01f). Aged
bone-linen vestment over a dark undergown, a moss-green stole with ochre trim
and knotwork, braided cord belt with a cairn-stone amulet, wrapped leggings,
and a faded ochre three-ring sigil on the back. Painted in model space.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from armorpaint import (DARK_LEATHER, band_coordinate, cloth, edge_profile, fbm3, lerp, metal,
                        rope, smoothstep, sym)
from paint_sturdy import grave_pallor
from regions import classify
from texelmap import bake, render_views

NIF = "B_AvMon01F.NIF"
LINEN = (156, 150, 130)
STOLE = (54, 80, 56)
OCHRE = np.array([176, 142, 72.0])
STONE = dict(base=np.array([128, 132, 126.0]), dark=np.array([70, 74, 70.0]),
             rust=np.array([96, 104, 88.0]), rust_dark=np.array([60, 66, 56.0]),
             highlight=np.array([182, 186, 176.0]))


def paint(out_png: Path):
    tm, _ = bake(NIF)
    region, L = classify(tm)
    base = np.asarray(Image.open(HERE / "originals" / "a_unde01f.png").convert("RGB")).astype(float)
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

    # Her original face already reads undead; chill it slightly to match.
    apply(head | hands, lerp(base, grave_pallor(base), 0.5))

    # -------------------------------------------------------------- vestment
    neckline = np.where(front, shoulder + 0.9 + 0.07 * ax ** 2, shoulder + 2.6)
    hem = hip - 3.6 + 0.9 * (fbm3(ps * np.array([1, 1, 0.1]), 1.2, 3, 131) - 0.5)
    vest = (torso | ((region == "thigh") & cov)) & (z <= neckline) & (z >= hem)
    linen = cloth(ps, LINEN, weave=0.16, wear=0.50, seed=133)
    folds = 0.86 + 0.14 * np.sin(ax * 2.1 + 0.9 * fbm3(ps, 2.0, 2, 135))
    grime = smoothstep(hem + 4, hem, z)          # grave soil creeping up the hem
    linen = lerp(linen * folds[..., None], np.array([92, 84, 66.0]), 0.55 * grime)
    apply(vest, linen)
    apply(vest & (z < hem + 0.5), linen * 0.6)
    # Dark undergown showing at the neckline.
    apply(vest & front & (z > neckline - 0.9), cloth(ps, (40, 38, 42), weave=0.14, wear=0.2, seed=137))

    # Sleeves: linen to the forearm, dark cuffs.
    sleeve = arm & (ax < L["wrist_x"] - 1.2)
    sleeve_cloth = cloth(ps, LINEN, weave=0.12, wear=0.45, seed=139)
    sleeve_cloth = sleeve_cloth * (0.86 + 0.18 * fbm3(ps * np.array([0.6, 2.5, 2.5]), 1.2, 3, 140))[..., None]
    apply(sleeve, sleeve_cloth)
    cuff = arm & (ax >= L["wrist_x"] - 1.2)
    apply(cuff, cloth(ps, (44, 40, 40), weave=0.1, wear=0.2, seed=141))

    # ----------------------------------------------------------------- stole
    # Two moss-green bands either side of centre, over the shoulders and down
    # to below the hem, with ochre edging and knotwork at the ends.
    band_in, band_out = 1.1, 2.9
    stole = (torso | ((region == "thigh") & cov)) & (ax > band_in) & (ax < band_out) & \
            (z <= np.where(front, neckline, shoulder + 1.8)) & (z >= hem - 1.6) & (region != 'neck')
    green = cloth(ps, STOLE, weave=0.12, wear=0.25, seed=143)
    apply(stole, green)
    edge = stole & ((np.abs(ax - band_in) < 0.22) | (np.abs(ax - band_out) < 0.22))
    apply(edge, OCHRE * (0.8 + 0.25 * fbm3(p, 0.5, 2, 145))[..., None])
    # Knotwork panel near the bottom of each band: interlaced diagonals.
    kn = stole & (z < hem + 4.5) & (z > hem - 1.2)
    u = (ax - band_in) / (band_out - band_in)
    lattice = np.minimum(np.abs(np.sin((u * 2.0 + z * 0.55) * np.pi)), np.abs(np.sin((u * 2.0 - z * 0.55) * np.pi)))
    apply(kn & (lattice < 0.28) & ~edge, OCHRE * 0.95)

    # ---------------------------------------------- cord belt and cairn amulet
    belt_z = waist - 0.6
    belt = torso & (np.abs(z - belt_z) < 0.55)
    apply(belt, rope(ax * 1.0 + y * 0.6, (z - (belt_z - 0.55)) / 1.1, (132, 112, 76)))
    amulet_c = np.array([0.0, belt_z - 1.9])
    ad = np.sqrt((x - amulet_c[0]) ** 2 + ((z - amulet_c[1]) * 0.8) ** 2)
    amulet = torso & front & (ad < 0.95)
    apply(amulet, metal(ps, n, np.clip(1.0 - ad, 0, 1), STONE, 0.3, 147))
    cordlet = torso & front & (np.abs(x) < 0.12) & (z < belt_z) & (z > amulet_c[1] + 0.9)
    apply(cordlet, np.array([120, 102, 70.0]))

    # --------------------------------------------------- back three-ring sigil
    bz = shoulder - 7.5
    rings = np.zeros_like(z)
    for cx, cz in ((0.0, bz + 1.0), (-0.9, bz - 0.55), (0.9, bz - 0.55)):
        rr = np.sqrt((x - cx) ** 2 + (z - cz) ** 2)
        rings = np.maximum(rings, 1 - smoothstep(0.1, 0.24, np.abs(rr - 1.15)))
    back = vest & ~front & ~stole
    apply(back & (rings > 0.02), OCHRE * 0.85, 0.75 * rings * smoothstep(0.25, 0.6, fbm3(p, 0.8, 3, 149) + 0.3))

    # ------------------------------------------------------------- leggings
    legs = leg & (z < hem + 0.1) & (z > ankle + 5.0)
    iw, fw = band_coordinate(z + 0.4 * np.arctan2(y, x - np.sign(x) * 4.6), 1.2)
    wrap = cloth(ps, (54, 50, 50), weave=0.12, wear=0.3, seed=151) * (0.75 + 0.25 * edge_profile(fw, 0.2))[..., None]
    apply(legs, wrap)
    boot = leg & (z <= ankle + 5.0)
    apply(boot, metal(ps, n, 0.6, DARK_LEATHER, 0.3, 153) * 0.85)

    Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8)).save(out_png)
    return out_png


if __name__ == "__main__":
    out = HERE / "work" / "priest_v2.png"
    out.parent.mkdir(exist_ok=True)
    paint(out)
    render_views(NIF, Image.open(out), views=[("front", (0, -1, 0)), ("back", (0, 1, 0)),
                                              ("3/4 front", (0.7, -0.7, 0.15)), ("3/4 back", (-0.6, 0.8, 0.1))],
                 width=460, height=720, label="Zombie Priest v2 (Claude)").save(HERE / "work" / "priest_v2_render.png")
    print("wrote", out)
