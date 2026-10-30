"""Add a second triangle shape to a NetImmerse 4.2.x item NIF (pyffi cannot read these files).

Used for the Cairnfire Aegis: a 3D skull mesh is appended to a stock shield. The new shape is a
byte copy of an existing NiTriShape (same transform, same texture/material properties) that
points at a new NiTriShapeData; the parent NiNode gets one more child. Every parse is checked to
end exactly at the next block, so a layout surprise stops the build instead of writing a bad file.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass

import numpy as np


@dataclass
class Block:
    index: int
    kind: str
    start: int      # offset of the type-name string
    body: int       # offset of the block data
    end: int        # offset of the next block (or the footer)


def blocks(raw: bytes):
    head = raw.index(b"\n") + 1
    version, count = struct.unpack_from("<II", raw, head)
    found = []
    for m in re.finditer(rb"Ni[A-Za-z]{2,40}", raw):
        s = m.start() - 4
        if s < head + 8:
            continue
        n = struct.unpack_from("<I", raw, s)[0]
        # the bytes after a name can themselves be letters (e.g. a vertex count of 0x150 = "P")
        if 4 <= n <= len(m.group()):
            found.append((s, m.group()[:n].decode()))
    assert len(found) == count, f"found {len(found)} block names, header says {count}"
    footer = len(raw) - 4 - 4 * struct.unpack_from("<I", raw, len(raw) - 8)[0]
    footer = len(raw) - 8   # one root: count + ref
    assert struct.unpack_from("<I", raw, footer)[0] == 1, "expected exactly one root"
    out = []
    for i, (s, kind) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else footer
        out.append(Block(i, kind, s, s + 4 + len(kind), end))
    return version, head, out, footer


class Reader:
    def __init__(self, raw, pos):
        self.raw, self.pos = raw, pos

    def take(self, fmt):
        v = struct.unpack_from("<" + fmt, self.raw, self.pos)
        self.pos += struct.calcsize("<" + fmt)
        return v


def av_object(raw, b: Block):
    """Parse NiObjectNET + NiAVObject (4.2.x). Returns a dict of field offsets."""
    r = Reader(raw, b.body)
    (nlen,) = r.take("I"); r.pos += nlen
    r.take("i")             # extra data
    r.take("i")             # controller
    r.take("H")             # flags
    r.take("3f9ff3f")       # translation, rotation, scale, velocity
    (nprop,) = r.take("I")
    props = list(r.take(f"{nprop}i")) if nprop else []
    (has_bb,) = r.take("B")
    if has_bb:
        r.take("I3f9f3f")
    return {"props": props, "after": r.pos}


def node_children(raw, b: Block):
    info = av_object(raw, b)
    r = Reader(raw, info["after"])
    count_at = r.pos
    (n,) = r.take("I")
    kids = list(r.take(f"{n}i")) if n else []
    (ne,) = r.take("I")
    if ne:
        r.take(f"{ne}i")
    assert r.pos == b.end, f"NiNode {b.index} parse ended at {r.pos}, block ends at {b.end}"
    return count_at, kids


def shape_refs(raw, b: Block):
    info = av_object(raw, b)
    r = Reader(raw, info["after"])
    data_at = r.pos
    data, skin = r.take("ii")
    assert r.pos == b.end, f"NiTriShape {b.index} parse ended at {r.pos}, block ends at {b.end}"
    return data_at, data, skin


def shape_data_layout(raw, b: Block):
    """Parse a 4.2.x NiTriShapeData and return its layout; rebuilding it must give the same bytes."""
    for uv_flag in (False, True):
        try:
            return _layout(raw, b, uv_flag)
        except (AssertionError, struct.error):
            continue
    raise AssertionError(f"NiTriShapeData {b.index}: unknown layout")


def _layout(raw, b, uv_flag):
    r = Reader(raw, b.body)
    (n,) = r.take("H")
    (hv,) = r.take("B"); assert hv == 1
    verts = np.array(r.take(f"{3 * n}f")).reshape(n, 3)
    (hn,) = r.take("B")
    norms = np.array(r.take(f"{3 * n}f")).reshape(n, 3) if hn else None
    bound_at = r.pos
    bound = r.take("4f")
    (hc,) = r.take("B")
    cols = np.array(r.take(f"{4 * n}f")).reshape(n, 4) if hc else None
    (nuv,) = r.take("H")
    assert nuv <= 4
    huv = r.take("B")[0] if uv_flag else None
    uvs = [np.array(r.take(f"{2 * n}f")).reshape(n, 2) for _ in range(nuv)]
    (ntri,) = r.take("H")
    (npts,) = r.take("I")
    assert npts == 3 * ntri
    tris = np.array(r.take(f"{3 * ntri}H")).reshape(ntri, 3)
    groups_at = r.pos
    (ngroups,) = r.take("H")
    for _ in range(ngroups):
        (k,) = r.take("H"); r.take(f"{k}H")
    assert r.pos == b.end, f"NiTriShapeData parse ended at {r.pos}, block ends at {b.end}"
    layout = {"normals": bool(hn), "colors": bool(hc), "uv_sets": nuv, "has_uv": huv}
    rebuilt = shape_data(verts, norms, uvs[0] if uvs else None, tris, layout, colors=cols, extra_uvs=uvs[1:],
                         bound=bound, groups=raw[groups_at:r.pos])
    assert rebuilt == raw[b.body:b.end], "NiTriShapeData rebuild differs from the original bytes"
    layout["verts"], layout["uvs"], layout["tris"], layout["colors_data"] = verts, uvs, tris, cols
    layout["bound_at"] = bound_at
    return layout


def shape_data(verts, norms, uv, tris, layout, colors=None, extra_uvs=(), bound=None, groups=b"\x00\x00"):
    n = len(verts)
    assert n < 65536 and len(tris) < 65536
    out = bytearray()
    out += struct.pack("<HB", n, 1) + np.asarray(verts, "<f4").tobytes()
    out += struct.pack("<B", 1 if layout["normals"] else 0)
    if layout["normals"]:
        out += np.asarray(norms, "<f4").tobytes()
    out += struct.pack("<4f", *(bound if bound is not None else sphere(verts)))
    out += struct.pack("<B", 1 if layout["colors"] else 0)
    if layout["colors"]:
        c = colors if colors is not None else np.tile(layout.get("fill_colour", (1.0, 1.0, 1.0, 1.0)), (n, 1))
        out += np.asarray(c, "<f4").tobytes()
    out += struct.pack("<H", layout["uv_sets"])
    if layout["has_uv"] is not None:
        out += struct.pack("<B", layout["has_uv"])
    sets = [uv] + list(extra_uvs) if layout["uv_sets"] else []
    while len(sets) < layout["uv_sets"]:
        sets.append(uv)
    for s in sets[:layout["uv_sets"]]:
        out += np.asarray(s, "<f4").tobytes()
    out += struct.pack("<HI", len(tris), 3 * len(tris)) + np.asarray(tris, "<u2").tobytes()
    out += groups                      # match groups (vertices sharing a position); none for new shapes
    return bytes(out)


def sphere(verts):
    v = np.asarray(verts, float)
    centre = (v.min(0) + v.max(0)) / 2
    return (*centre, float(np.linalg.norm(v - centre, axis=1).max()))


def fix_bounds(raw: bytes) -> bytes:
    """Recompute the bounding sphere of every NiTriShapeData (after vertices were moved)."""
    out = bytearray(raw)
    _, _, blks, _ = blocks(raw)
    for b in blks:
        if b.kind == "NiTriShapeData":
            lay = shape_data_layout(bytes(out), b)
            struct.pack_into("<4f", out, lay["bound_at"], *sphere(lay["verts"]))
    return bytes(out)


def sized(name: str) -> bytes:
    return struct.pack("<I", len(name)) + name.encode()


def append_shape(raw: bytes, template_shape: int, verts, norms, uv, tris) -> bytes:
    """Return a copy of raw with one more NiTriShape (copied from template_shape) + its data."""
    version, head, blks, footer = blocks(raw)
    src = blks[template_shape]
    assert src.kind == "NiTriShape"
    data_at, data_ref, skin = shape_refs(raw, src)
    data_blk = blks[data_ref]
    assert data_blk.kind == "NiTriShapeData"
    layout = shape_data_layout(raw, data_blk)
    if layout["colors_data"] is not None:
        layout["fill_colour"] = tuple(np.median(layout["colors_data"], 0))
    parent = [b for b in blks if b.kind == "NiNode" and template_shape in node_children(raw, b)[1]]
    assert len(parent) == 1, "template shape must have exactly one parent node"
    count_at, kids = node_children(raw, parent[0])
    new_shape, new_data = len(blks), len(blks) + 1
    shape_body = bytearray(raw[src.body:src.end])
    rel = data_at - src.body
    shape_body[rel:rel + 4] = struct.pack("<i", new_data)
    new_blocks = sized("NiTriShape") + bytes(shape_body) + sized("NiTriShapeData") + shape_data(verts, norms, uv, tris, layout)
    out = bytearray(raw[:footer]) + new_blocks + raw[footer:]
    # parent gets one more child: bump the count and insert the ref after the existing ones
    insert_at = count_at + 4 + 4 * len(kids)
    out[count_at:count_at + 4] = struct.pack("<I", len(kids) + 1)
    out[insert_at:insert_at] = struct.pack("<i", new_shape)
    struct.pack_into("<I", out, head + 4, len(blks) + 2)
    out = bytes(out)
    # verify the result parses and the new shape/data are where we expect
    _, _, check, _ = blocks(out)
    assert [b.kind for b in check][-2:] == ["NiTriShape", "NiTriShapeData"]
    assert new_shape in node_children(out, check[parent[0].index])[1]
    assert shape_refs(out, check[new_shape])[1] == new_data
    shape_data_layout(out, check[new_data])
    return out
