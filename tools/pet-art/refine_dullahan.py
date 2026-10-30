"""Dullahan: keep Codex's black scale armor, fix symmetry and the back seam.

1. Mirror in 3D: every armor texel on one side takes the colour of the texel
   covering the mirrored surface point (-x, y, z) on the other side, so both
   sides match. The neck stump / rib wound (reddish flesh) is never copied or
   overwritten, so it is not duplicated.
2. Seam: the two back UV islands meet at the spine; after mirroring both
   sides sample the same source there, so the spine is continuous.
3. Edge padding (also used for the other pets): uncovered atlas background
   is filled from the nearest island colour so texture filtering and mipmaps
   never pull the light background into a seam as a pale line.
4. Subtle refinement: pull stray teal/green speckle on the armor toward the
   armor's own dark steel, and even out the scale shading a little.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from texelmap import bake, render_views

NIF = "Sluaghbinder_Dullahan.NIF"


def pad_islands(rgb: np.ndarray, covered: np.ndarray, iterations: int = 24) -> np.ndarray:
    """Grow island colours outward into uncovered texels (edge padding)."""
    out = rgb.copy()
    filled = covered.copy()
    for _ in range(iterations):
        grow = ~filled
        if not grow.any():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros(filled.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            src = np.roll(np.roll(filled, dy, 0), dx, 1)
            col = np.roll(np.roll(out, dy, 0), dx, 1)
            take = grow & src
            acc[take] += col[take]
            cnt[take] += 1
        newly = cnt > 0
        out[newly] = acc[newly] / cnt[newly][:, None]
        filled = filled | newly
    return out


def mirror_lookup(tm, cell=0.6):
    """For each covered texel, the index of the texel covering its mirror point."""
    ys, xs = np.nonzero(tm.covered)
    pts = tm.pos[ys, xs]
    nrm = tm.nrm[ys, xs]
    keys = np.floor(pts / cell).astype(np.int64)
    grid = {}
    for i, k in enumerate(map(tuple, keys)):
        grid.setdefault(k, []).append(i)
    target_pts = pts * np.array([-1, 1, 1])
    target_nrm = nrm * np.array([-1, 1, 1])
    best = np.full(len(pts), -1, np.int64)
    tkeys = np.floor(target_pts / cell).astype(np.int64)
    offsets = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]
    for i in range(len(pts)):
        kx, ky, kz = tkeys[i]
        cand = []
        for a, b, c in offsets:
            cand.extend(grid.get((kx + a, ky + b, kz + c), ()))
        if not cand:
            continue
        cand = np.asarray(cand)
        d = np.linalg.norm(pts[cand] - target_pts[i], axis=1)
        ok = (nrm[cand] @ target_nrm[i]) > 0.2
        if not ok.any():
            continue
        d = np.where(ok, d, np.inf)
        j = int(np.argmin(d))
        if d[j] < cell * 1.2:
            best[i] = cand[j]
    return ys, xs, best


def refine(source_side: int, out_png: Path):
    tm, _ = bake(NIF)
    base = np.asarray(Image.open(HERE / "originals" / "sluagh_dullahan_body.png").convert("RGB")).astype(float)
    r, g, b = base[..., 0], base[..., 1], base[..., 2]
    flesh = (r > g + 16) & (r > b + 12)                         # stump / wound / exposed flesh
    for _ in range(3):                                          # grow a little so edges stay intact
        flesh = flesh | np.roll(flesh, 1, 0) | np.roll(flesh, -1, 0) | np.roll(flesh, 1, 1) | np.roll(flesh, -1, 1)

    # Protect the chest wound and the neck stump entirely (not only its red):
    # the pale ribs and green flesh are part of it and must not be mirrored.
    P = tm.pos
    wound = (P[..., 1] < 0.5) & (np.abs(P[..., 0] - 1.5) < 6.5) & (np.abs(P[..., 2] - 48.5) < 6.5)
    stump = P[..., 2] > 58.5
    flesh = flesh | ((wound | stump) & tm.covered)
    ys, xs, best = mirror_lookup(tm)
    out = base.copy()
    x = tm.pos[ys, xs, 0]
    copy_side = (np.sign(x) == -source_side) & (np.abs(x) > 0.05)
    valid = copy_side & (best >= 0)
    sy, sx = ys[best[valid]], xs[best[valid]]
    ty, tx = ys[valid], xs[valid]
    keep = flesh[sy, sx] | flesh[ty, tx]
    out[ty[~keep], tx[~keep]] = base[sy[~keep], sx[~keep]]

    # Subtle refinement on armor only: tame teal/green speckle, even shading.
    armor = tm.covered & ~flesh
    lum = out.mean(-1, keepdims=True)
    teal = np.clip((out[..., 1:2] + out[..., 2:3]) / 2 - out[..., 0:1] - 6, 0, None) / 40.0
    steel = lum * np.array([0.96, 0.99, 1.04])
    mix = np.clip(teal, 0, 1) * 0.55
    refined = out * (1 - mix) + steel * mix
    local = np.asarray(Image.fromarray(np.clip(refined, 0, 255).astype(np.uint8)).resize((64, 64), Image.BILINEAR)
                       .resize((512, 512), Image.BILINEAR)).astype(float)
    refined = refined + (local.mean(-1, keepdims=True) - local.mean()) * -0.12   # soften blotchy low-frequency shading
    out = np.where(armor[..., None], refined, out)

    out = pad_islands(out, tm.covered)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(out_png)
    return out_png


if __name__ == "__main__":
    (HERE / "work").mkdir(exist_ok=True)
    views = [("front", (0, -1, 0)), ("back", (0, 1, 0)), ("3/4 front", (0.7, -0.7, 0.15)), ("3/4 back", (-0.6, 0.8, 0.1))]
    for side, tag in ((-1, "final"),):
        png = refine(side, HERE / "work" / f"dullahan_{tag}.png")
        render_views(NIF, Image.open(png), views=views, width=460, height=720,
                     label=f"Dullahan refined ({tag})").save(HERE / "work" / f"dullahan_{tag}_render.png")
        print("wrote", png)
