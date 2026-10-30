"""Build one OBJ per character (body, legs, arms, gloves, boots, head, optional cloak) with
per-part textures, for blender_views.py. Usage from other scripts: build(race, sex, textures, out)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import nifmesh
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
NIF = HERE / "nif"
HEADS = {("BC", "m"): "bri_m_head01", ("BC", "f"): "bri_f_head01", ("Fir", "m"): "fir_m_head01", ("Fir", "f"): "fir_f_head01"}
CLOAKS = {("BC", "m"): "Cloak01_cel_m", ("BC", "f"): "Cloak01_cel_f", ("Fir", "m"): "Cloak01_fir_m", ("Fir", "f"): "Cloak01_fir_f"}


def flat(color, path):
    if not path.exists():
        Image.new("RGB", (16, 16), color).save(path)
    return path


def build(race, sex, tex, out_obj, body_variant=2, glove_variant=1, boot_variant=1, cloak=None, extra=(), helm_swap=False):
    """tex: dict slot -> png path for slots body(composite), legs, arms, gloves, boots."""
    out_obj = Path(out_obj); out_obj.parent.mkdir(parents=True, exist_ok=True)
    skin = flat((196, 152, 120), out_obj.parent / "flat_skin.png")
    parts = [
        (f"Body0{body_variant}_{race}_{sex}", tex["body"]),
        (f"Legs01_{race}_{sex}", tex["legs"]),
        (f"Arms01_{race}_{sex}", tex["arms"]),
        (f"Gloves0{glove_variant}_{race}_{sex}", tex["gloves"]),
        (f"Boots0{boot_variant}_{race}_{sex}", tex["boots"]),
    ] + ([] if helm_swap else [(HEADS[(race, sex)], skin)]) + [
    ]
    if cloak:
        parts.append((CLOAKS[(race, sex)], cloak))
    parts += list(extra)
    mtl, obj, base = [], [f"mtllib {out_obj.stem}.mtl"], 1
    for i, (nif, png) in enumerate(parts):
        shapes, _ = nifmesh.load(NIF / f"{nif}.nif")
        mtl.append(f"newmtl m{i}\nKd 1 1 1\nmap_Kd {Path(png).resolve().as_posix()}\n")
        for s in shapes:
            if not np.abs(s.uvs).sum():   # skip biped helper shapes with no UVs
                continue
            obj.append(f"o {nif}")
            verts = s.vertices
            if helm_swap and nif == HEADS[(race, sex)]:
                c = verts.mean(0)
                verts = c + (verts - c) * 0.82      # the client swaps the head under full helms
            obj += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in verts]
            obj += [f"vt {u:.6f} {1 - v:.6f}" for u, v in s.uvs]
            obj += [f"vn {x:.5f} {y:.5f} {z:.5f}" for x, y, z in s.normals]
            obj.append(f"usemtl m{i}")
            for a, b, c in s.faces:
                a, b, c = a + base, b + base, c + base
                obj.append(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}")
            base += len(s.vertices)
    out_obj.with_suffix(".mtl").write_text("\n".join(mtl), encoding="utf-8")
    out_obj.write_text("\n".join(obj) + "\n", encoding="utf-8")
    return out_obj
