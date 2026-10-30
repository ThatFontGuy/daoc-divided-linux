"""Zombie Guardian body atlas: rusted iron plate painted in model space.

Base: the untouched Decaying Marshman atlas (corpse_body). Armor is defined as
functions of the 3D surface point each texel covers, so:
  - it is symmetric (patterns use |x|),
  - the back is continuous where its two UV islands meet at the spine,
  - it stops below the neck (the throat/face stay original skin).
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from armorpaint import (DARK_LEATHER, RUSTED_IRON, band_coordinate, chainmail, edge_profile, fbm3,
                       lerp, metal, rivets, smoothstep, sym, value_noise3)
from regions import classify
from texelmap import bake, render_views

NIF = "Sluaghbinder_ZombieDefender.NIF"


def paint(out_png: Path):
    tm, _ = bake(NIF)
    region, L = classify(tm)
    base = np.asarray(Image.open(HERE / "originals" / "corpse_body.png").convert("RGB")).astype(float)
    atlas = base.copy()

    p = tm.pos
    n = tm.nrm
    ps = sym(p)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    front = y < 0.3
    covered = tm.covered

    shoulder, neck, waist, hip, knee, ankle = (L["shoulder_z"], L["neck_z"], L["waist_z"],
                                               L["hip_z"], L["knee_z"], L["ankle_z"])

    def apply(mask, color, soft=None):
        nonlocal atlas
        m = mask.astype(float) if soft is None else np.clip(soft, 0, 1) * mask
        atlas = atlas * (1 - m[..., None]) + color * m[..., None]

    torso = np.isin(region, ["chest", "back", "belly", "hips"]) & covered
    arm = np.isin(region, ["upperarm", "forearm", "hand"]) & covered
    leg = np.isin(region, ["thigh", "shin", "foot"]) & covered

    # ---------------------------------------------------------------- cuirass
    # Neckline: low and rounded in front (throat stays skin), a little higher
    # behind the neck. Continuous in 3D, so both back islands match.
    neckline = np.where(front, shoulder + 0.2 + 0.030 * ax ** 2, shoulder + 1.6 + 0.015 * ax ** 2)
    neckline = np.minimum(neckline, shoulder + 3.0)
    cuirass = torso & (z <= neckline) & (z >= waist + 1.0)
    # Breastplate: centre ridge, rolled rim at the neckline, pectoral groove,
    # side seams, and articulated lames over the belly.
    ridge = 1 - smoothstep(0.0, 1.8, ax)
    rim_top = smoothstep(0.0, 0.9, neckline - z)
    rolled = 1 - smoothstep(0.9, 1.6, neckline - z)            # raised rolled edge
    pec_line = shoulder - 8.5 + 0.10 * ax ** 1.6                 # curved groove under the chest
    pec_groove = 1 - smoothstep(0.0, 0.55, np.abs(z - pec_line))
    side_seam = 1 - smoothstep(0.0, 0.5, np.abs(ax - (L["shoulder_x"] - 1.8)))
    relief = 0.62 + 0.34 * ridge * front - 0.10 * smoothstep(0, 4, pec_line - z)
    relief = relief + 0.25 * rolled * rim_top - 0.75 * pec_groove * front - 0.55 * side_seam
    _, fr = band_coordinate(z, 3.2, waist + 1.0)
    lames_zone = z < waist + 1.0 + 6.4
    relief = np.where(lames_zone, 0.25 + 0.7 * edge_profile(fr, 0.16) * smoothstep(0, 0.35, fr), relief)
    relief = relief * (0.35 + 0.65 * rim_top)
    plate = metal(ps, n, np.clip(relief, 0, 1), RUSTED_IRON, rust_amount=0.50, seed=11)
    # Soft baked occlusion under the arms and toward the belt.
    occl = 1 - 0.22 * smoothstep(L["shoulder_x"] - 3.0, L["shoulder_x"], ax) - 0.12 * smoothstep(waist + 5, waist + 1, z)
    plate = plate * occl[..., None]
    # Explicit line work so the shaping reads at game distance: dark chest
    # groove with a lit lip above it, and a lit centre ridge front and back.
    groove_line = (np.abs(z - pec_line) < 0.35) & front & (ax < L['shoulder_x'] - 2.2)
    lip_line = (np.abs(z - (pec_line + 0.55)) < 0.25) & front & (ax < L['shoulder_x'] - 2.2)
    ridge_line = (ax < 0.35) & (z > waist + 7.5) & (z < neckline - 1.0)
    plate = np.where(groove_line[..., None], plate * 0.55, plate)
    plate = np.where(lip_line[..., None], plate * 1.25, plate)
    plate = np.where(ridge_line[..., None], plate * 1.22, plate)
    # Rivets: along the neckline and down both side seams (symmetric).
    rv = rivets(x, z, 2.2, neckline - 0.7, 0.42, cuirass & front) + \
         rivets(z, ax, 2.4, L["shoulder_x"] - 1.3, 0.42, cuirass)
    plate = lerp(plate, np.array([150, 140, 128.0]) * (0.7 + 0.3 * n[..., 2:3].clip(0, 1)), np.clip(rv, 0, 1))
    # Torn opening over the original rib wound (chest, left of centre).
    wound_uv = (205, 300)  # atlas pixel of the exposed ribs in corpse_body
    wound = tm.pos[wound_uv[1], wound_uv[0]]
    d = np.sqrt((x - wound[0]) ** 2 + ((z - wound[2]) * 0.8) ** 2)
    ragged = 3.1 + 1.2 * (fbm3(p, 0.9, 3, 5) - 0.5) * 2
    hole = front & (d < ragged)
    lip = front & (d >= ragged) & (d < ragged + 0.6)
    apply(cuirass & ~hole, plate)
    apply(cuirass & lip, np.array([48, 34, 26.0]))       # torn, blackened edge

    # -------------------------------------------------------------------- belt
    belt = torso & (np.abs(z - waist) < 1.1)
    leather = metal(ps, n, 0.8 - 0.35 * (np.abs(z - waist) > 0.8), DARK_LEATHER, 0.2, 21)
    apply(belt, leather)
    buckle = belt & front & (ax < 1.4)
    apply(buckle, metal(ps, n, 0.9 - 0.5 * (ax > 1.0), RUSTED_IRON, 0.3, 23))

    # ----------------------------------------------------------- plate skirt
    skirt_top, skirt_bottom = waist - 1.1, knee + 7.5
    skirt = (torso | leg) & (z < skirt_top) & (z >= skirt_bottom)
    iz, fz = band_coordinate(skirt_top - z, 3.1)
    # Tassets: vertical segments by |x| in front/back; overlapping rows.
    ix, fx = band_coordinate(ax + 0.35 * iz, 3.6)
    overlap = smoothstep(0.0, 0.25, fz) * (0.55 + 0.45 * (1 - fz))
    relief = np.clip(0.25 + 0.75 * overlap * edge_profile(fx, 0.10), 0, 1)
    tasset = metal(ps + np.stack([ix * 3.1, iz * 1.7, 0 * ix], -1), n, relief, RUSTED_IRON, 0.52, 31)
    tasset = tasset * (0.78 + 0.22 * smoothstep(0, 0.35, fz))[..., None]  # shadow under each row
    trv = rivets(ax + 0.35 * iz, fz * 3.1, 3.6, 0.55, 0.32, skirt)
    tasset = lerp(tasset, np.array([118, 110, 100.0]), 0.8 * np.clip(trv, 0, 1))
    # Ragged hem: the bottom row is uneven and a few lames are missing.
    hem = skirt_bottom + 1.4 * fbm3(ps * np.array([1, 1, 0.1]), 1.4, 2, 33)
    # No missing lames (they read as a stripe at this resolution); instead a few
    # dented plates: relief dips in noisy blotches.
    missing = np.zeros_like(skirt)
    dent = smoothstep(0.62, 0.8, fbm3(ps, 1.6, 3, 35))
    tasset = tasset * (1 - 0.28 * dent)[..., None]
    apply(skirt & (z >= hem) & ~missing, tasset)
    # Where a lame is missing, show the dark mail/cloth beneath, not skin.

    # --------------------------------------------------------- shoulders/arms
    pauldron = arm & (ax < L["shoulder_x"] + 6.5) | (torso & (ax > L["shoulder_x"] - 1.2) & (z > shoulder - 3))
    ia, fa = band_coordinate(ax - L["shoulder_x"] + 1.2, 2.3)
    relief = np.clip(0.2 + 0.8 * smoothstep(0, 0.22, fa) * (0.6 + 0.4 * (1 - fa)), 0, 1)
    apply(pauldron & covered, metal(ps, n, relief, RUSTED_IRON, 0.58, 41))
    vambrace = arm & (ax > L["elbow_x"] + 0.5) & (ax < L["wrist_x"] - 0.4)
    iv, fv = band_coordinate(ax, 2.6, L["elbow_x"] + 0.5)
    relief = np.clip(0.3 + 0.7 * edge_profile(fv, 0.14), 0, 1)
    apply(vambrace, metal(ps, n, relief, RUSTED_IRON, 0.55, 43))
    # Chainmail sleeve between the pauldron and the vambrace.
    sleeve = arm & (ax >= L["shoulder_x"] + 6.5) & (ax <= L["elbow_x"] + 0.5)
    zc = np.median(z[arm]); yc = np.median(y[arm])
    around = np.arctan2(z - zc, y - yc) * 1.9
    mail = chainmail(ax, around, 0.55, rust=smoothstep(0.55, 0.8, fbm3(ps, 2.0, 3, 44)) * 0.7)
    apply(sleeve, mail)
    strap = arm & (np.abs(ax - (L["elbow_x"] + 3.2)) < 0.45)
    apply(strap, metal(ps, n, 0.7, DARK_LEATHER, 0.2, 45))
    glove = arm & (ax >= L["wrist_x"] - 0.4)
    apply(glove, metal(ps, n, 0.75 - 0.3 * (fbm3(p, 0.6, 2, 47) > 0.6), DARK_LEATHER, 0.25, 47))

    # -------------------------------------------------------------------- legs
    skirt_painted = skirt & (z >= hem) & ~missing
    trousers = leg & ~skirt_painted & (z > knee + 1.5)
    cloth = np.array([58, 54, 50.0]) * (0.72 + 0.38 * fbm3(p, 0.7, 3, 51))[..., None]
    apply(trousers, cloth, soft=0.94)
    greave = leg & (z <= knee + 1.5) & (z > ankle + 1.2)
    ig, fg = band_coordinate(z, 3.0, ankle + 1.2)
    leg_centre = np.sign(x) * 5.4
    relief = np.where(front, 0.62 + 0.30 * (1 - smoothstep(0, 1.6, np.abs(x - leg_centre))), 0.42)
    relief = np.clip(relief * (0.75 + 0.25 * edge_profile(fg, 0.1)), 0, 1)
    apply(greave & front, metal(ps, n, relief, RUSTED_IRON, 0.52, 53))
    # Calves: the greave is a front plate strapped over a dark leather wrap.
    calf = greave & ~front
    wrap = metal(ps, n, 0.55 + 0.25 * edge_profile(fg, 0.2), DARK_LEATHER, 0.3, 54)
    strap_rows = np.abs(fg - 0.5) < 0.12
    wrap = np.where(strap_rows[..., None], wrap * 0.6, wrap)
    apply(calf, wrap)
    # Knee cop: domed plate with a dark rim, clearly separate from the greave.
    kd = np.abs(z - knee)
    knee_cop = leg & front & (kd < 1.9)
    cop_relief = np.clip(0.95 - 0.35 * smoothstep(0.6, 1.9, kd) - 0.25 * smoothstep(0.8, 2.2, np.abs(x - leg_centre)), 0, 1)
    apply(knee_cop, metal(ps, n, cop_relief, RUSTED_IRON, 0.45, 55))
    apply(leg & front & (np.abs(kd - 1.9) < 0.3), np.array([40, 36, 34.0]))
    sabaton = leg & (z <= ankle + 1.2)
    iss, fss = band_coordinate(-y, 1.6)
    apply(sabaton, metal(ps, n, 0.4 + 0.6 * edge_profile(fss, 0.2), RUSTED_IRON, 0.55, 57))
    apply(sabaton & ~front, metal(ps, n, 0.5, DARK_LEATHER, 0.3, 58))  # leather heel

    # Grime where armor meets exposed flesh, so edges read as worn, not pasted.
    armor = (cuirass & ~hole) | belt | (skirt & (z >= hem) & ~missing) | pauldron | vambrace | glove | greave | sabaton
    grime = (1 - armor) * covered
    img = np.clip(atlas, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(out_png)
    return out_png


if __name__ == "__main__":
    out = HERE / "work" / "guardian_final.png"
    out.parent.mkdir(exist_ok=True)
    paint(out)
    render_views(NIF, Image.open(out), label="Zombie Guardian final (Claude)").save(HERE / "work" / "guardian_final_render.png")
    print("wrote", out)
