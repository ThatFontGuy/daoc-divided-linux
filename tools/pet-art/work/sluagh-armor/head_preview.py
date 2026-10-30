"""OBJ of a head (+ optional hair) with a helm on top, for close-up renders."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import nifmesh
from armor_preview import NIF, HEADS, flat


def build(race, sex, helm_nif, helm_png, out_obj):
    out_obj = Path(out_obj)
    skin = flat((196, 152, 120), out_obj.parent / "flat_skin.png")
    parts = [(HEADS[(race, sex)], skin), (helm_nif, helm_png)]
    mtl, obj, base = [], [f"mtllib {out_obj.stem}.mtl"], 1
    for i, (nif, png) in enumerate(parts):
        shapes, _ = nifmesh.load(NIF / f"{nif}.nif")
        mtl.append(f"newmtl m{i}\nKd 1 1 1\nmap_Kd {Path(png).resolve().as_posix()}\n")
        for s in shapes:
            if not np.abs(s.uvs).sum():
                continue
            obj += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in s.vertices]
            obj += [f"vt {u:.6f} {1 - v:.6f}" for u, v in s.uvs]
            obj += [f"vn {x:.5f} {y:.5f} {z:.5f}" for x, y, z in s.normals]
            obj.append(f"usemtl m{i}")
            obj += [f"f {a + base}/{a + base}/{a + base} {b + base}/{b + base}/{b + base} {c + base}/{c + base}/{c + base}" for a, b, c in s.faces]
            base += len(s.vertices)
    out_obj.with_suffix(".mtl").write_text("\n".join(mtl), encoding="utf-8")
    out_obj.write_text("\n".join(obj) + "\n", encoding="utf-8")
    return out_obj
