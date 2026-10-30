"""Cairnbreaker v2: the Hibernian DragonSlayer mace, recoloured to match the Cairnfire Aegis.

Same stock atlas as the shield base, so the pair reads as one set: silver -> blackened iron,
the faceted crystal -> grave-green ghost light (like the skull's eyes), navy -> deep ghost-green glass. The flanged head is made ~18% bulkier. UVs are unchanged; the whole atlas is recoloured
into a private texture so every island keeps its hand-painted detail.

Outputs: wout/mace.nif, wout/mace.png, wout/mace.obj
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import nif4_append  # noqa: E402
import wgeom  # noqa: E402
import paint_sluagh_armor as M  # noqa: E402
from armorpaint import lerp  # noqa: E402

OUT = HERE / "wout"
BASE = "ADR_DragonSlayer_Hib_1h_hammer_blunt_mainhand"
BASE_TEX = "ADR_DragonSlayer_Hibernia_Weapons.dds"
PRIVATE_TEX = "slu_cairnbreaker_mace_ghostiron01.dds"
assert len(PRIVATE_TEX) == len(BASE_TEX), (len(PRIVATE_TEX), len(BASE_TEX))
OXBLOOD = np.array([58, 16, 14.0])
FIRE_HOT = np.array([170, 255, 190.0])


def recolour_atlas():
    a = np.asarray(Image.open(wgeom.FILES[BASE_TEX.lower()]).convert("RGB")).astype(float) / 255
    lum = a @ np.array([0.30, 0.55, 0.15])
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    bdom = (a[..., 2] >= mx - 1e-6)
    # the stock steel is a cool silver (low saturation); navy cloth and the cyan crystal are saturated
    crystal = bdom & (sat > 0.38) & (lum > 0.55) & (a[..., 1] > 0.55)
    navy = bdom & (sat > 0.42) & (lum < 0.40)
    iron = lerp(M.STEEL_DARK * 0.85, M.STEEL_HI * 1.2, np.clip(lum ** 1.6 * 1.15, 0, 1)[..., None])
    # dark facets / wraps -> deep ghost-green glass, so the crystal face reads as one glowing stone
    leather = lerp(np.array([4, 12, 9.0]), M.GHOST * 0.75, np.clip(lum * 2.4, 0, 1)[..., None])
    glow = lerp(M.GHOST * 0.6, FIRE_HOT, np.clip((lum - 0.45) * 2.0, 0, 1)[..., None])
    col = np.where(crystal[..., None], glow, np.where(navy[..., None], leather, iron))
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))


def mace_shape(v):
    v = v.copy()
    base = v[:, 2].max() - 9.0
    head = v[:, 2] > base
    t = np.clip((v[head, 2] - base) / 2.0, 0, 1)            # blend in over the collar
    s = 1 + 0.18 * t
    v[head, 0] *= s; v[head, 1] *= s
    v[head, 2] = base + (v[head, 2] - base) * (1 + 0.10 * t)
    return v


def main():
    w = wgeom.load(BASE)
    nv = mace_shape(w.verts)
    recolour_atlas().save(OUT / "mace.png")
    tmp = OUT / "mace_base.nif"
    wgeom.write(w, nv, tmp, texture_rename=(BASE_TEX, PRIVATE_TEX))
    raw = nif4_append.fix_bounds(tmp.read_bytes())
    (OUT / "mace.nif").write_bytes(raw)
    tmp.unlink()
    wgeom.obj(nv, w.uvs, w.faces, OUT / "mace.png", OUT / "mace.obj")
    print("built mace:", len(nv), "verts")


if __name__ == "__main__":
    main()
