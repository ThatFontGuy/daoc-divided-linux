"""Bake a texel -> 3D surface map for a 4.x item NIF (read-only), for painting in model space."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import nif4_geom


@dataclass
class TexelMap:
    covered: np.ndarray   # (h, w) bool
    position: np.ndarray  # (h, w, 3) model-space position
    normal: np.ndarray    # (h, w, 3) face normal


def bake(nif_path, width, height) -> TexelMap:
    covered = np.zeros((height, width), bool)
    position = np.zeros((height, width, 3))
    normal = np.zeros((height, width, 3))
    for g in nif4_geom.load(nif_path):
        uv = g.uvs * [width, height]
        for a, b, c in g.faces:
            p = uv[[a, b, c]]
            n = np.cross(g.vertices[b] - g.vertices[a], g.vertices[c] - g.vertices[a])
            length = np.linalg.norm(n)
            if length == 0:
                continue
            n /= length
            x0, y0 = np.floor(p.min(0)).astype(int)
            x1, y1 = np.ceil(p.max(0)).astype(int)
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, width - 1), min(y1, height - 1)
            if x1 < x0 or y1 < y0:
                continue
            ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            px, py = xs + 0.5, ys + 0.5
            d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
            if abs(d) < 1e-12:
                continue
            w0 = ((p[1, 1] - p[2, 1]) * (px - p[2, 0]) + (p[2, 0] - p[1, 0]) * (py - p[2, 1])) / d
            w1 = ((p[2, 1] - p[0, 1]) * (px - p[2, 0]) + (p[0, 0] - p[2, 0]) * (py - p[2, 1])) / d
            w2 = 1 - w0 - w1
            inside = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
            if not inside.any():
                continue
            pos = (w0[..., None] * g.vertices[a] + w1[..., None] * g.vertices[b] + w2[..., None] * g.vertices[c])
            covered[ys[inside], xs[inside]] = True
            position[ys[inside], xs[inside]] = pos[inside]
            normal[ys[inside], xs[inside]] = n
    return TexelMap(covered, position, normal)
