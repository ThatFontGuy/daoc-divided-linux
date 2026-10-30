"""Load DAoC (Gamebryo) NIF geometry with pyffi: shapes, world transforms, UVs, textures.

Skinned DAoC meshes store vertices in the shape's local space; we apply the
node chain transforms (translation/rotation/scale) from the root so all shapes
share one space. Texture names come from each shape's NiTexturingProperty.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

if not hasattr(time, "clock"):
    time.clock = time.perf_counter

import numpy as np
from pyffi.formats.nif import NifFormat

FIGURES = Path(os.environ.get("OFFLINE_DAOC_CLIENT", Path(__file__).resolve().parents[2] / "runtime" / "client-opendaoc" / "app")) / "figures"


@dataclass
class Shape:
    name: str
    kind: str
    texture: str
    vertices: np.ndarray   # (n,3) in model space
    normals: np.ndarray    # (n,3)
    uvs: np.ndarray        # (n,2), v=0 is the TOP of the image
    faces: np.ndarray      # (m,3)
    skinned: bool = False
    bones: list = field(default_factory=list)


def _matrix(node):
    r = node.rotation
    rot = np.array([[r.m_11, r.m_12, r.m_13], [r.m_21, r.m_22, r.m_23], [r.m_31, r.m_32, r.m_33]], dtype=np.float64)
    t = np.array([node.translation.x, node.translation.y, node.translation.z], dtype=np.float64)
    m = np.eye(4)
    # Gamebryo stores row-major rotation used as v * R (row vectors).
    m[:3, :3] = rot * node.scale
    m[3, :3] = t
    return m


def _texture_name(shape):
    for prop in shape.properties:
        if isinstance(prop, NifFormat.NiTexturingProperty) and prop.has_base_texture:
            src = prop.base_texture.source
            if src is not None:
                try:
                    return src.file_name.decode("latin1")
                except Exception:
                    return "?"
    return ""


def load(path, uv_set=0) -> tuple[list[Shape], NifFormat.Data]:
    path = Path(path)
    if not path.is_absolute():
        path = FIGURES / path
    data = NifFormat.Data()
    with path.open("rb") as handle:
        data.read(handle)

    parents = {}
    for block in data.blocks:
        if isinstance(block, NifFormat.NiNode):
            for child in block.children:
                if child is not None:
                    parents[id(child)] = block

    def world(node):
        m = np.eye(4)
        chain = []
        cur = node
        while cur is not None:
            chain.append(cur)
            cur = parents.get(id(cur))
        for n in chain:  # child first: v * M_child * M_parent ...
            m = m @ _matrix(n)
        return m

    shapes = []
    for block in data.blocks:
        if not isinstance(block, (NifFormat.NiTriShape, NifFormat.NiTriStrips)):
            continue
        geom = block.data
        if geom is None or not geom.num_vertices:
            continue
        verts = np.array([(v.x, v.y, v.z) for v in geom.vertices], dtype=np.float64)
        norms = (np.array([(n.x, n.y, n.z) for n in geom.normals], dtype=np.float64)
                 if geom.has_normals else np.zeros_like(verts))
        # Catacombs cloaks carry 3 UV sets; the client maps the cata cloak skin with set 1
        k = min(uv_set, max(0, len(geom.uv_sets) - 1))
        uvs = (np.array([(uv.u, uv.v) for uv in geom.uv_sets[k]], dtype=np.float64)
               if geom.num_uv_sets or getattr(geom, "has_uv", False) else np.zeros((len(verts), 2)))
        faces = np.array(geom.get_triangles(), dtype=np.int32).reshape(-1, 3)
        skinned = block.skin_instance is not None
        m = world(block)
        homog = np.hstack([verts, np.ones((len(verts), 1))]) @ m
        wverts = homog[:, :3]
        wnorms = norms @ m[:3, :3]
        lens = np.linalg.norm(wnorms, axis=1)[:, None]
        wnorms = np.where(lens > 1e-9, wnorms / np.maximum(lens, 1e-9), wnorms)
        bones = []
        if skinned:
            bones = [b.name.decode("latin1") for b in block.skin_instance.bones if b is not None]
        shapes.append(Shape(block.name.decode("latin1"), type(block).__name__, _texture_name(block),
                            wverts, wnorms, uvs, faces, skinned, bones))
    return shapes, data


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        shapes, data = load(arg)
        print(f"== {arg}: {len(shapes)} shapes, {len(data.blocks)} blocks")
        allv = np.concatenate([s.vertices for s in shapes])
        print(f"   bounds min={allv.min(0).round(1)} max={allv.max(0).round(1)}")
        for s in shapes:
            print(f"   {s.kind:12} {s.name!r:28} tex={s.texture!r:34} v={len(s.vertices):4} f={len(s.faces):4} "
                  f"uv=[{s.uvs.min(0).round(2)}..{s.uvs.max(0).round(2)}] skinned={s.skinned} bones={len(s.bones)}")
