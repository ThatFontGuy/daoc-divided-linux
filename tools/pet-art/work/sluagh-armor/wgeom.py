"""Load / reshape / write private copies of item weapon NIFs (4.x via nif4_geom, 10.x via pyffi)."""
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import daoc_catalog as d  # noqa: E402
import nif4_geom  # noqa: E402
import nifmesh  # noqa: E402

ITEMS = d.CLIENT / "items"
FILES = {p.name.lower(): p for p in ITEMS.iterdir()}


@dataclass
class Weapon:
    name: str
    raw: bytes
    verts: np.ndarray      # model space (world for pyffi files)
    uvs: np.ndarray
    faces: np.ndarray
    voff: int              # byte offset of the local vertex float array
    to_world: np.ndarray   # 4x3 affine local->world
    local: np.ndarray
    lnormals: np.ndarray = None


def load(name, uv_set=0):
    path = FILES[name.lower() + ".nif"]
    raw = path.read_bytes()
    try:
        g = nif4_geom.load(path, uv_set)
        if not g:
            raise ValueError
        g = g[0]
        local = g.vertices
        verts, uvs, faces = g.vertices, g.uvs, g.faces
        lnormals = None
    except Exception:
        shapes, data = nifmesh.load(path)
        s = shapes[0]
        blk = [b for b in data.blocks if type(b).__name__ == "NiTriShapeData"][0]
        local = np.array([(v.x, v.y, v.z) for v in blk.vertices], float)
        lnormals = np.array([(q.x, q.y, q.z) for q in blk.normals], float) if blk.has_normals else None
        verts, uvs, faces = s.vertices, s.uvs, s.faces
    voff = raw.find(np.asarray(local, np.float32).tobytes())
    assert voff > 0, name
    A = np.hstack([local, np.ones((len(local), 1))])
    to_world, *_ = np.linalg.lstsq(A, verts, rcond=None)
    return Weapon(name, raw, np.asarray(verts, float), np.asarray(uvs, float), np.asarray(faces), voff, to_world, local, lnormals)


def normals(verts, faces):
    n = np.zeros_like(verts)
    tri = verts[faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    for k in range(3):
        np.add.at(n, faces[:, k], fn)
    l = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(l, 1e-9)


def write(w: Weapon, new_world, out_path, texture_rename=None):
    """Patch the vertex (and normal, when found) arrays into a copy of the NIF."""
    R = w.to_world[:3]; t = w.to_world[3]
    local = (new_world - t) @ np.linalg.inv(R)
    raw = bytearray(w.raw)
    count = len(local)
    raw[w.voff:w.voff + 12 * count] = np.asarray(local, np.float32).tobytes()
    end = w.voff + 12 * count
    old_n = None
    for bw in (4, 1):
        flag = raw[end] if bw == 1 else int.from_bytes(raw[end:end + 4], "little")
        if flag == 1:
            cand = np.frombuffer(bytes(raw[end + bw:end + bw + 12 * count]), np.float32).reshape(count, 3)
            if np.allclose(np.linalg.norm(cand, axis=1), 1.0, atol=0.05):
                old_n = (end + bw, cand)
                break
    if old_n is None and w.lnormals is not None:
        noff = bytes(raw).find(np.asarray(w.lnormals, np.float32).tobytes())
        if noff > 0:
            old_n = (noff, w.lnormals)
    if old_n:
        nl = normals(local, w.faces)
        # keep the original winding convention: flip if most new normals oppose the old ones
        if (nl * old_n[1]).sum(1).mean() < 0:
            nl = -nl
        raw[old_n[0]:old_n[0] + 12 * count] = np.asarray(nl, np.float32).tobytes()
    if texture_rename:
        old, new = texture_rename
        assert len(old) == len(new)
        i = bytes(raw).lower().find(old.lower().encode())
        assert i > 0, old
        raw[i:i + len(new)] = new.encode()
    Path(out_path).write_bytes(bytes(raw))
    return bool(old_n)


def obj(w_verts, uvs, faces, png, out_obj):
    out_obj = Path(out_obj)
    out_obj.with_suffix(".mtl").write_text(f"newmtl m\nKd 1 1 1\nmap_Kd {Path(png).resolve().as_posix()}\n", encoding="utf-8")
    v = w_verts - w_verts.mean(0)
    lines = [f"mtllib {out_obj.with_suffix('.mtl').name}", "o w"]
    lines += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in v]
    lines += [f"vt {a:.6f} {1 - b:.6f}" for a, b in uvs]
    lines.append("usemtl m")
    lines += [f"f {a + 1}/{a + 1} {b + 1}/{b + 1} {c + 1}/{c + 1}" for a, b, c in faces]
    out_obj.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_obj
