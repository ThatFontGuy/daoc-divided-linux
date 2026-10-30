"""Bake a texel -> surface map: for every atlas pixel, the 3D position/normal it covers.

Also records how many distinct surface points share a texel (mirrored UVs) and
renders the model with any texture from several views for review.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from nifmesh import load


@dataclass
class TexelMap:
    size: int
    pos: np.ndarray      # (S,S,3) model-space position (first writer)
    nrm: np.ndarray      # (S,S,3)
    covered: np.ndarray  # (S,S) bool
    shape: np.ndarray    # (S,S) int shape index, -1 empty
    mirror: np.ndarray   # (S,S) bool: texel reused by a surface point far from the first
    pos2: np.ndarray     # (S,S,3) position of the mirrored reuse (if any)


def combined(shapes):
    verts, norms, uvs, faces, owner = [], [], [], [], []
    offset = 0
    for index, s in enumerate(shapes):
        verts.append(s.vertices); norms.append(s.normals); uvs.append(s.uvs)
        faces.append(s.faces + offset); owner.append(np.full(len(s.faces), index))
        offset += len(s.vertices)
    return (np.concatenate(verts), np.concatenate(norms), np.concatenate(uvs),
            np.concatenate(faces), np.concatenate(owner))


def bake(nif, size=512, pad=3, uv_set=0):
    shapes, _ = load(nif, uv_set)
    v, n, uv, f, owner = combined(shapes)
    pos = np.zeros((size, size, 3)); nrm = np.zeros((size, size, 3))
    pos2 = np.zeros((size, size, 3))
    covered = np.zeros((size, size), bool); mirror = np.zeros((size, size), bool)
    shape = np.full((size, size), -1, np.int32)
    px = uv * (size - 1)
    for tri, who in zip(f, owner):
        a, b, c = px[tri]
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        x0 = max(0, int(math.floor(min(a[0], b[0], c[0]))) - 1)
        x1 = min(size - 1, int(math.ceil(max(a[0], b[0], c[0]))) + 1)
        y0 = max(0, int(math.floor(min(a[1], b[1], c[1]))) - 1)
        y1 = min(size - 1, int(math.ceil(max(a[1], b[1], c[1]))) + 1)
        if x1 < x0 or y1 < y0:            # triangle entirely outside the texture
            continue
        gy, gx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        qx, qy = gx.astype(float), gy.astype(float)
        w0 = ((b[1] - c[1]) * (qx - c[0]) + (c[0] - b[0]) * (qy - c[1])) / den
        w1 = ((c[1] - a[1]) * (qx - c[0]) + (a[0] - c[0]) * (qy - c[1])) / den
        w2 = 1 - w0 - w1
        eps = 0.6 / max(1.0, abs(den)) ** 0.5  # small conservative dilation at edges
        inside = (w0 >= -eps) & (w1 >= -eps) & (w2 >= -eps)
        if not inside.any():
            continue
        p = (w0[..., None] * v[tri[0]] + w1[..., None] * v[tri[1]] + w2[..., None] * v[tri[2]])
        nn = (w0[..., None] * n[tri[0]] + w1[..., None] * n[tri[1]] + w2[..., None] * n[tri[2]])
        ys, xs = gy[inside], gx[inside]
        first = ~covered[ys, xs]
        pos[ys[first], xs[first]] = p[inside][first]
        nrm[ys[first], xs[first]] = nn[inside][first]
        shape[ys[first], xs[first]] = who
        covered[ys[first], xs[first]] = True
        # Mirrored reuse: an already-covered texel mapped again far away in 3D.
        again = ~first
        if again.any():
            far = np.linalg.norm(pos[ys[again], xs[again]] - p[inside][again], axis=1) > 2.0
            mirror[ys[again][far], xs[again][far]] = True
            pos2[ys[again][far], xs[again][far]] = p[inside][again][far]
    lens = np.linalg.norm(nrm, axis=2, keepdims=True)
    nrm = np.where(lens > 1e-9, nrm / np.maximum(lens, 1e-9), nrm)
    # Pad islands a few pixels by nearest-neighbour so mip filtering never pulls background in.
    if pad:
        for _ in range(pad):
            grow = ~covered
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                src = np.roll(np.roll(covered, dy, 0), dx, 1) & grow
                ys, xs = np.nonzero(src)
                sy, sx = (ys - dy) % size, (xs - dx) % size
                pos[ys, xs] = pos[sy, sx]; nrm[ys, xs] = nrm[sy, sx]; shape[ys, xs] = shape[sy, sx]
            covered = shape >= 0
    return TexelMap(size, pos, nrm, covered, shape, mirror, pos2), shapes


def render_views(nif, texture: Image.Image, views=None, width=460, height=620, label=None):
    shapes, _ = load(nif)
    v, n, uv, f, _ = combined(shapes)
    tex = np.asarray(texture.convert("RGBA").resize((512, 512)))
    views = views or [("front", (0, -1, 0)), ("back", (0, 1, 0)),
                      ("left", (-1, 0, 0)), ("3/4 front", (0.7, -0.7, 0.15))]
    pics = []
    for name, direction in views:
        view = np.asarray(direction, float); view /= np.linalg.norm(view)
        up = np.array((0, 0, 1.0))
        right = np.cross(-view, up); right /= np.linalg.norm(right)
        up2 = np.cross(right, -view)
        proj = np.stack((v @ right, v @ up2), 1)
        mid = (proj.min(0) + proj.max(0)) / 2; ext = proj.max(0) - proj.min(0)
        scale = min((width - 30) / max(ext[0], 1e-6), (height - 40) / max(ext[1], 1e-6))
        scr = np.stack(((proj[:, 0] - mid[0]) * scale + width / 2, height / 2 - (proj[:, 1] - mid[1]) * scale), 1)
        depth = v @ view
        zb = np.full((height, width), -np.inf); rgb = np.zeros((height, width, 3), np.uint8)
        light = view + np.array((0.4, -0.1, 0.8)); light /= np.linalg.norm(light)
        for tri in f:
            xy = scr[tri]; (x0, y0), (x1, y1), (x2, y2) = xy
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9:
                continue
            l = max(0, int(math.floor(xy[:, 0].min()))); r = min(width - 1, int(math.ceil(xy[:, 0].max())))
            t = max(0, int(math.floor(xy[:, 1].min()))); b = min(height - 1, int(math.ceil(xy[:, 1].max())))
            if l > r or t > b:
                continue
            gy, gx = np.mgrid[t:b + 1, l:r + 1]
            pxx, pyy = gx + 0.5, gy + 0.5
            w0 = ((y1 - y2) * (pxx - x2) + (x2 - x1) * (pyy - y2)) / den
            w1 = ((y2 - y0) * (pxx - x2) + (x0 - x2) * (pyy - y2)) / den
            w2 = 1 - w0 - w1
            ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            z = w0 * depth[tri[0]] + w1 * depth[tri[1]] + w2 * depth[tri[2]]
            pz = zb[t:b + 1, l:r + 1]
            vis = ins & (z > pz)
            if not vis.any():
                continue
            suv = np.clip(w0[vis, None] * uv[tri[0]] + w1[vis, None] * uv[tri[1]] + w2[vis, None] * uv[tri[2]], 0, 1)
            tx = np.rint(suv[:, 0] * 511).astype(int); ty = np.rint(suv[:, 1] * 511).astype(int)
            col = tex[ty, tx, :3].astype(float)
            nn = w0[vis, None] * n[tri[0]] + w1[vis, None] * n[tri[1]] + w2[vis, None] * n[tri[2]]
            nn /= np.maximum(np.linalg.norm(nn, axis=1)[:, None], 1e-9)
            shade = 0.55 + 0.45 * np.abs(nn @ light)
            pz[vis] = z[vis]
            rgb[t:b + 1, l:r + 1][vis] = np.clip(col * shade[:, None], 0, 255).astype(np.uint8)
        pic = Image.fromarray(rgb)
        mask = Image.fromarray((np.isfinite(zb) * 255).astype(np.uint8))
        bg = Image.new("RGB", (width, height), (32, 36, 40)); bg.paste(pic, (0, 0), mask)
        d = ImageDraw.Draw(bg); d.text((8, 6), name, fill=(235, 230, 200))
        pics.append(bg)
    sheet = Image.new("RGB", (width * len(pics) + 6 * (len(pics) - 1), height + (26 if label else 0)), (18, 20, 22))
    y = 0
    if label:
        ImageDraw.Draw(sheet).text((8, 6), label, fill=(255, 255, 220)); y = 26
    for i, p in enumerate(pics):
        sheet.paste(p, (i * (width + 6), y))
    return sheet


if __name__ == "__main__":
    import sys
    from pathlib import Path
    nif, texture, out = sys.argv[1], sys.argv[2], sys.argv[3]
    render_views(nif, Image.open(texture), label=Path(texture).name).save(out)
    print("wrote", out)
