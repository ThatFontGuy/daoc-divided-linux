"""Export a pet NIF (via pyffi, read-only) to OBJ+MTL with its installed skin PNG, for Blender.

Usage: python export_obj.py <NIF name> <skin png> <out dir>
Vertex order is preserved per shape so edits can later be written back to the
same NIF vertices without disturbing skin weights.
"""
import sys
from pathlib import Path

import nifmesh


def export(nif_name, skin_png, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(nif_name).stem
    shapes, _ = nifmesh.load(nifmesh.FIGURES / nif_name)
    skin = Path(skin_png).resolve()
    (out_dir / f"{stem}.mtl").write_text(
        f"newmtl skin\nKd 1 1 1\nmap_Kd {skin.as_posix()}\n", encoding="utf-8")
    lines = [f"mtllib {stem}.mtl"]
    base = 1
    for index, shape in enumerate(shapes):
        lines.append(f"o shape{index}_{shape.name.replace(' ', '_').replace(':', '_')}")
        lines += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in shape.vertices]
        # OBJ v=0 is the bottom of the image; nifmesh gives v=0 at the top.
        lines += [f"vt {u:.6f} {1 - v:.6f}" for u, v in shape.uvs]
        lines += [f"vn {x:.5f} {y:.5f} {z:.5f}" for x, y, z in shape.normals]
        lines.append("usemtl skin")
        for a, b, c in shape.faces:
            a, b, c = a + base, b + base, c + base
            lines.append(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}")
        base += len(shape.vertices)
    path = out_dir / f"{stem}.obj"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(export(*sys.argv[1:4]))
