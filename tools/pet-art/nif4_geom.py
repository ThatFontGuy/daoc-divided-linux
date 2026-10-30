"""READ-ONLY geometry reader for NetImmerse 4.1/4.2 item NIFs (pyffi cannot parse them).

Finds each length-prefixed NiTriShapeData / NiTriStripsData block and decodes
vertices, UVs and triangles, trying the few bool/UV-flag layouts these
versions use and keeping the one whose indices and floats validate. It never
writes NIFs; private weapon copies are byte patches of the originals.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Geom:
    offset: int
    kind: str
    vertices: np.ndarray
    uvs: np.ndarray
    faces: np.ndarray


class _Reader:
    def __init__(self, data, pos):
        self.data, self.pos = data, pos

    def take(self, fmt):
        size = struct.calcsize(fmt)
        value = struct.unpack_from("<" + fmt, self.data, self.pos)
        self.pos += size
        return value

    def boolean(self, width):
        return self.take("I" if width == 4 else "B")[0] != 0


def _geometry(data, pos, strips, bool_width, has_uv_flag, uv_set=0):
    r = _Reader(data, pos)
    count = r.take("H")[0]
    if not 0 < count < 20000:
        raise ValueError
    if not r.boolean(bool_width):
        raise ValueError
    verts = np.array(r.take(f"{3 * count}f"), dtype=np.float64).reshape(count, 3)
    if r.boolean(bool_width):
        r.take(f"{3 * count}f")
    r.take("4f")  # center, radius
    if r.boolean(bool_width):
        r.take(f"{4 * count}f")
    uv_sets = r.take("H")[0]
    if uv_sets > 4:
        raise ValueError
    if has_uv_flag:
        r.boolean(bool_width)
    uvs = np.zeros((count, 2))
    for index in range(uv_sets):
        values = np.array(r.take(f"{2 * count}f")).reshape(count, 2)
        if index == min(uv_set, uv_sets - 1):
            uvs = values
    triangles = r.take("H")[0]
    if strips:
        strip_count = r.take("H")[0]
        lengths = r.take(f"{strip_count}H")
        faces = []
        for length in lengths:
            points = r.take(f"{length}H")
            for i in range(length - 2):
                a, b, c = points[i], points[i + 1], points[i + 2]
                if len({a, b, c}) == 3:
                    faces.append((a, b, c) if i % 2 == 0 else (a, c, b))
        faces = np.array(faces, dtype=np.int64)
    else:
        r.take("I")  # num triangle points
        faces = np.array(r.take(f"{3 * triangles}H"), dtype=np.int64).reshape(triangles, 3)
    if len(faces) == 0 or faces.max() >= count or not np.isfinite(verts).all() or np.abs(verts).max() > 1e5:
        raise ValueError
    if uv_sets and (not np.isfinite(uvs).all() or np.abs(uvs).max() > 64):
        raise ValueError
    return verts, uvs, faces


def load(path, uv_set=0) -> list[Geom]:
    data = Path(path).read_bytes()
    result = []
    for match in re.finditer(rb"NiTri(Shape|Strips)Data", data):
        start = match.start() - 4
        if start < 0 or struct.unpack_from("<I", data, start)[0] != len(match.group(0)):
            continue
        pos = match.end()
        strips = match.group(1) == b"Strips"
        for bool_width, uv_flag in ((1, False), (4, False), (1, True), (4, True)):
            try:
                verts, uvs, faces = _geometry(data, pos, strips, bool_width, uv_flag, uv_set)
            except (ValueError, struct.error):
                continue
            result.append(Geom(pos, "strips" if strips else "shape", verts, uvs, faces))
            break
    return result


def texture_names(path):
    data = Path(path).read_bytes()
    return [(m.start(), m.group(0).decode("latin1"))
            for m in re.finditer(rb"[A-Za-z0-9_\-]{2,40}\.(?:dds|tga|bmp)", data, re.I)]
