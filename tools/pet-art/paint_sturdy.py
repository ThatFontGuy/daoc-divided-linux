"""Sturdy Zombie body atlas: a cairn-bound bog labourer (low-level, no heavy armor).

Private copy of the Briton undead male (b_band01 / b_unde01m). Painted in model
space like the guardian: symmetric, seamless, head/face kept from the original
but chilled to the Sluagh grave pallor.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from armorpaint import (DARK_LEATHER, band_coordinate, cloth, edge_profile, fbm3, fur, lerp,
                        metal, rope, smoothstep, spiral_mark, sym)
from regions import classify
from texelmap import bake, render_views

NIF = "B_Band01.NIF"


def grave_pallor(rgb):
    """Desaturate living tones toward a cold, bluish corpse grey."""
    grey = rgb.mean(-1, keepdims=True)
    cold = grey * np.array([0.86, 0.96, 1.02]) + np.array([4, 8, 12.0])
    return lerp(rgb, cold, 0.55)


def paint(out_png: Path):
    tm, _ = bake(NIF)
    region, L = classify(tm)
    base = np.asarray(Image.open(HERE / "originals" / "b_unde01m.png").convert("RGB")).astype(float)
    atlas = base.copy()

    p, n = tm.pos, tm.nrm
    ps = sym(p)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ax = np.abs(x)
    front = y < 0.3
    cov = tm.covered
    shoulder, neck, waist, hip, knee, ankle = (L["shoulder_z"], L["neck_z"], L["waist_z"],
                                               L["hip_z"], L["knee_z"], L["ankle_z"])

    def apply(mask, color, amount=1.0):
        nonlocal atlas
        m = mask.astype(float) * amount
        atlas = atlas * (1 - m[..., None]) + np.asarray(color, float) * m[..., None]

    head = (region == "head") & cov
    hands = (region == "hand") & cov
    torso = np.isin(region, ["neck", "chest", "back", "belly", "hips"]) & cov
    arm = np.isin(region, ["upperarm", "forearm"]) & cov
    leg = np.isin(region, ["thigh", "shin", "foot"]) & cov

    # Face, scalp and hands: keep the original painting, chilled to grave pallor.
    apply(head | hands | ((region == "neck") & cov), grave_pallor(base))

    # ---------------------------------------------------------------- tunic
    neckline = np.where(front, shoulder + 1.2 + 0.05 * ax ** 2, shoulder + 2.4)
    hem = hip - 4.0 + 1.2 * (fbm3(ps * np.array([1, 1, 0.1]), 1.3, 3, 81) - 0.5)
    tunic = (torso | ((region == "thigh") & cov)) & (z <= neckline) & (z >= hem)
    wool = cloth(ps, (74, 84, 58), weave=0.20, wear=0.45, seed=83)
    # Vertical fold shading so the wool hangs rather than reading flat.
    folds = 0.86 + 0.14 * np.sin(ax * 1.9 + 0.8 * fbm3(ps, 2.0, 2, 85))
    wool = wool * folds[..., None] * (0.78 + 0.22 * smoothstep(hem, hem + 3, z))[..., None]
    apply(tunic, wool)
    # Frayed dark hem and neckline edge.
    apply(tunic & (z < hem + 0.55), wool * 0.55)
    apply(tunic & (z > neckline - 0.5), wool * 0.6)
    # Sleeves: the same wool to the elbow, rolled cuff.
    sleeve = arm & (ax < L["elbow_x"] + 1.0)
    apply(sleeve, wool * (0.9 + 0.1 * np.sin(ax * 2.7))[..., None])
    apply(sleeve & (np.abs(ax - (L["elbow_x"] + 0.4)) < 0.6), wool * 0.65)

    # Chalk cairn on the chest: three stacked stones, the Sluaghbinder's mark
    # (the class's wards and spells are all cairn-named).
    cz = shoulder - 7.2
    stones = [(0.0, cz - 1.9, 2.3, 0.95), (0.15, cz - 0.25, 1.65, 0.78), (-0.1, cz + 1.05, 1.05, 0.6)]
    outline = np.zeros_like(z)
    for sx, sz, rx, rz in stones:
        e = np.sqrt(((x - sx) / rx) ** 2 + ((z - sz) / rz) ** 2)
        outline = np.maximum(outline, 1 - smoothstep(0.10, 0.22, np.abs(e - 1.0) * min(rx, rz)))
    rough = smoothstep(0.30, 0.55, fbm3(p, 0.6, 3, 89) + 0.25)
    chalk = np.array([192, 192, 180.0]) * (0.8 + 0.25 * fbm3(p, 0.4, 2, 87))[..., None]
    mark = (outline > 0.02) & front & tunic
    apply(mark, chalk, 0.85 * outline * rough)

    # ------------------------------------------------------------ hide mantle
    mantle_top = shoulder + 2.6
    mantle_bottom = shoulder - 4.5 - 1.3 * fbm3(ps * np.array([1, 1, 0.2]), 1.2, 3, 91)
    mantle = (torso | arm) & (z >= mantle_bottom) & (z <= mantle_top) & (ax < L["shoulder_x"] + 2.2 + 1.2 * fbm3(ps, 1.0, 2, 92))
    mantle &= ~(front & (ax < 2.8 + 0.25 * (mantle_top - z)))   # open at the throat
    hide = fur(ps, n, (92, 80, 66), seed=93)
    hide = hide * (0.8 + 0.35 * smoothstep(0.35, 0.75, fbm3(ps, 0.7, 3, 94)))[..., None]
    apply(mantle, hide)
    apply(mantle & (z < mantle_bottom + 0.6), hide * 0.6)
    # Rope tie across the chest holding the mantle.
    tie = front & torso & (np.abs(z - (shoulder - 1.4)) < 0.45) & (ax < 3.4)
    apply(tie, rope(x, (z - (shoulder - 1.85)) / 0.9))

    # ------------------------------------------------------------- rope belt
    belt_z = waist - 1.0
    belt = torso & (np.abs(z - belt_z) < 0.75)
    apply(belt, rope(ax * 1.0 + y * 0.5, (z - (belt_z - 0.75)) / 1.5, (118, 100, 70)))
    knot = torso & front & (np.abs(x + 1.2) < 0.9) & (z < belt_z) & (z > belt_z - 4.0)
    apply(knot & (np.abs(x + 1.2) < 0.45 + 0.1 * np.sin(z * 3)), rope(z, (x + 1.65) / 0.9, (112, 94, 66)))

    # ------------------------------------------------------ burial wrappings
    wrap = arm & (ax >= L["elbow_x"] + 1.0)
    iw, fw = band_coordinate(ax + 0.35 * np.arctan2(z - np.median(z[arm]), y), 1.1)
    linen = np.array([150, 142, 120.0]) * (0.72 + 0.35 * fbm3(p, 0.8, 3, 95))[..., None]
    linen = linen * (0.72 + 0.28 * edge_profile(fw, 0.18))[..., None]
    stain = smoothstep(0.6, 0.85, fbm3(p, 1.3, 3, 97))
    linen = lerp(linen, np.array([88, 76, 58.0]), 0.6 * stain)
    apply(wrap, linen)

    # --------------------------------------------------- trousers and boots
    trousers = leg & (z < hem + 0.2) & (z > ankle + 4.5)
    breeks = cloth(ps, (64, 54, 44), weave=0.18, wear=0.4, seed=101)
    patch = (np.abs(z - knee) < 1.6) & front & (np.abs(ax - 5.3) < 1.5)
    apply(trousers, breeks)
    apply(trousers & patch, cloth(ps + 3, (86, 76, 58), weave=0.14, wear=0.2, seed=103))
    boot = leg & (z <= ankle + 4.5)
    apply(boot, metal(ps, n, 0.6, DARK_LEATHER, 0.35, 105))
    # Rag bindings criss-crossing the boot shafts.
    t = np.arctan2(y, x - np.sign(x) * 5.3)
    cross = np.minimum(np.abs(np.sin((z * 1.6 + t * 1.2))), np.abs(np.sin((z * 1.6 - t * 1.2))))
    binding = boot & (z > ankle + 0.8) & (cross < 0.22)
    apply(binding, linen * 0.85)

    Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8)).save(out_png)
    return out_png


if __name__ == "__main__":
    out = HERE / "work" / "sturdy_v2.png"
    out.parent.mkdir(exist_ok=True)
    paint(out)
    render_views(NIF, Image.open(out), views=[("front", (0, -1, 0)), ("back", (0, 1, 0)),
                                              ("3/4 front", (0.7, -0.7, 0.15)), ("3/4 back", (-0.6, 0.8, 0.1))],
                 width=460, height=720, label="Sturdy Zombie v2 (Claude)").save(HERE / "work" / "sturdy_v2_render.png")
    print("wrote", out)
