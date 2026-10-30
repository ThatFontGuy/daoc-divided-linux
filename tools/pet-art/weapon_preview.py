"""Preview item weapons (read-only): OBJ export via nif4_geom, UV footprint sheets, Blender render.

python weapon_preview.py <out-prefix> <nif>=<texture png> [...]
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nif4_geom  # noqa: E402

ITEMS = HERE.parents[1] / "runtime" / "client-opendaoc" / "app" / "items"
BLENDER = Path(os.environ.get("OFFLINE_DAOC_BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"))


def export_obj(nif: Path, png: Path, out: Path) -> Path:
    geoms = nif4_geom.load(nif)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".mtl").write_text(f"newmtl m\nKd 1 1 1\nmap_Kd {png.resolve().as_posix()}\n", encoding="utf-8")
    lines, base = [f"mtllib {out.with_suffix('.mtl').name}"], 1
    for index, g in enumerate(geoms):
        # Stand the weapon up along z and centre it, so every item renders alike.
        v = g.vertices - g.vertices.mean(0)
        lines.append(f"o part{index}")
        lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in v]
        lines += [f"vt {u:.5f} {1 - w:.5f}" for u, w in g.uvs]
        lines.append("usemtl m")
        lines += [f"f {a + base}/{a + base} {b + base}/{b + base} {c + base}/{c + base}" for a, b, c in g.faces]
        base += len(v)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def uv_sheet(nif: Path, png: Path, out: Path, scale=2):
    image = Image.open(png).convert("RGB")
    image = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
    draw = ImageDraw.Draw(image)
    for g in nif4_geom.load(nif):
        for a, b, c in g.faces:
            pts = [(g.uvs[i][0] * image.width, g.uvs[i][1] * image.height) for i in (a, b, c)]
            draw.polygon(pts, outline=(255, 230, 0))
    image.save(out)


def footprint_mask(nif: Path, size) -> np.ndarray:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for g in nif4_geom.load(nif):
        for a, b, c in g.faces:
            draw.polygon([(g.uvs[i][0] * size[0], g.uvs[i][1] * size[1]) for i in (a, b, c)], fill=255)
    return np.asarray(mask) > 0


def render(out_png: Path, objs):
    script = HERE / "blender_weapons.py"
    subprocess.run([str(BLENDER), "-b", "--factory-startup", "--python", str(script), "--", str(out_png),
                    *map(str, objs)], check=True, capture_output=True)
    return out_png


if __name__ == "__main__":
    prefix = Path(sys.argv[1]).resolve()
    objs = []
    for arg in sys.argv[2:]:
        nif, png = arg.split("=")
        nif, png = ITEMS / nif, Path(png)
        obj = export_obj(nif, png, prefix.parent / f"{prefix.name}_{nif.stem}.obj")
        uv_sheet(nif, png, prefix.parent / f"{prefix.name}_{nif.stem}_uv.png")
        objs.append(obj)
    print(render(prefix.parent / f"{prefix.name}_render.png", objs))
