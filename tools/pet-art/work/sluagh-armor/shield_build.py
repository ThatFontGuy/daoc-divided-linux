"""Cairnfire Aegis v2: a 3D bone skull on a horned, blackened-iron heater over grave-green ghost fire.

Inspired by (not copied from) the Skullflame Shield: spiked crown, thick bevelled rim, a big
snarling skull standing out of a burning field. Our palette: blackened iron, bone, grave-green.

Base shield: ADR_DragonSlayer_Hib_Shield_Large (horned heater, one texture, one UV set).
Skull:       vfx_flaming_skull-green.nif shape 0 with its horns removed and the horn sockets capped.
The skull is appended as a second shape (nif4_append) sharing the shield's texture: the shield's
UVs are stretched into the left half of a new 1024 texture, the skull's into the top-right quarter.

Outputs: wout/shield.nif, wout/shield.png (1024), wout/shield.obj (+ skull) for previews.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import daoc_catalog as d  # noqa: E402
import nif4_geom  # noqa: E402
import nif4_append  # noqa: E402
import wgeom  # noqa: E402
import paint_sluagh_armor as M  # noqa: E402
from armorpaint import fbm3, smoothstep, lerp  # noqa: E402
from weapons_build import bake  # noqa: E402

OUT = HERE / "wout"
BASE = "ADR_DragonSlayer_Hib_Shield_Large"
BASE_TEX = "ADR_DragonSlayer_Hibernia_Weapons.dds"
PRIVATE_TEX = "slu_cairnfire_aegis_skullfire_001.dds"
assert len(PRIVATE_TEX) == len(BASE_TEX)
SIZE = 1024
U_STOCK = 0.19                       # the stock shield only uses u < 0.19 of its atlas
K_SHIELD = 0.49 / U_STOCK            # stretch into the left half of the new texture
SKULL_U, SKULL_V, SKULL_S = 0.51, 0.01, 0.48

BONE = np.array([182, 176, 160.0])
BONE_DARK = np.array([62, 58, 50.0])
FIRE_DARK = np.array([6, 14, 10.0])
FIRE_HOT = np.array([170, 255, 190.0])


def skull_mesh():
    E = {p.name.lower(): p for p in (d.CLIENT / "effects").iterdir()}
    g = nif4_geom.load(E["vfx_flaming_skull-green.nif"])[0]
    v, f, uv = g.vertices, g.faces, g.uvs
    c = uv[f].mean(1)
    f = f[~((c[:, 0] < 0.72) & (c[:, 1] > 0.74))]          # horns live in the bottom-left UV strip
    used = np.unique(f)
    remap = -np.ones(len(v), int); remap[used] = np.arange(len(used))
    v, uv, f = v[used], uv[used], remap[f]
    # cap the horn sockets: fan each open boundary loop around its centre
    edges = {}
    for t in f:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (min(a, b), max(a, b))
            edges.setdefault(key, []).append((a, b))
    nxt = {}
    for key, uses in edges.items():
        if len(uses) == 1:
            a, b = uses[0]
            nxt[b] = a                                       # walk boundary opposite to the face winding
    v, uv, f = list(v), list(uv), list(f)
    seen = set()
    for s in list(nxt):
        if s in seen:
            continue
        loop, cur = [], s
        while cur not in seen and cur in nxt:
            seen.add(cur); loop.append(cur); cur = nxt[cur]
        if len(loop) < 3:
            continue
        ci = len(v)
        v.append(np.mean([v[i] for i in loop], 0))
        uv.append(uv[max(loop, key=lambda i: v[i][2])])        # cap samples the bone of the crown
        for i in range(len(loop)):
            f.append(np.array([loop[i], loop[(i + 1) % len(loop)], ci]))
    return np.array(v), np.array(uv), np.array(f)


def shield_shape(v):
    v = v.copy()
    v[:, 1] *= 1.45                                          # bulkier: thicker plate and rim
    top = (np.abs(v[:, 0]) < 1.3) & (v[:, 2] > 8.0)
    v[top, 2] += 4.0 * (1 - np.abs(v[top, 0]) / 1.3) * np.clip((v[top, 2] - 8.0) / 1.4, 0, 1)   # centre spike
    horn = (np.abs(v[:, 0]) > 3.0) & (v[:, 2] > 6.0)
    v[horn, 2] += 0.18 * (v[horn, 2] - 6.0)                  # taller horns
    return v


def place_skull(sv, shield_v):
    s = 1.38
    front_y = shield_v[(shield_v[:, 2] > -10) & (shield_v[:, 2] < 6), 1].min()   # face plane (front is -y)
    out = np.empty_like(sv)
    out[:, 0] = sv[:, 0] * s
    out[:, 2] = (sv[:, 2] - 1.57) * s + 0.6
    out[:, 1] = (sv[:, 1] - sv[:, 1].max()) * s * 0.58 + front_y + 1.1   # back of the skull sunk into the plate
    return out


def recolour_stock(pos, nrm, cov):
    """Stock hand-painted shield art, recoloured: silver -> blackened iron (horns -> bone), blue -> ghost fire."""
    stock = Image.open(wgeom.FILES[BASE_TEX.lower()]).convert("RGB")
    W, H = stock.size
    strip = stock.crop((0, 0, int(round(U_STOCK * W)), H)).resize((int(round(0.49 * SIZE)), SIZE), Image.LANCZOS)
    a = np.asarray(strip).astype(float) / 255
    lum = a @ np.array([0.30, 0.55, 0.15])
    mx, mn = a.max(-1), a.min(-1)
    blue = ((a[..., 2] - a[..., 0]) > 0.10) & (lum < 0.5)
    w = strip.width
    x, y, z = pos[:, :w, 0], pos[:, :w, 1], pos[:, :w, 2]
    q = np.stack([np.abs(x), y, z], -1)
    # blackened iron that keeps the painted bevels and filigree shading
    g = fbm3(q, 1.6, 3, 701)
    iron = lerp(M.STEEL_DARK * 0.9, M.STEEL_HI * 1.15, np.clip(lum ** 1.5 * 1.1, 0, 1)[..., None])
    iron = lerp(iron, iron * 0.7, 0.35 * g[..., None])
    # bone horns and centre spike
    horn = ((np.abs(x) > 3.0) & (z > 6.2)) | ((np.abs(x) < 1.3) & (z > 8.6))
    bone = lerp(BONE_DARK, BONE, np.clip(lum ** 1.2, 0, 1)[..., None])
    # grave-green ghost fire in the field, hottest behind the skull, licking outward
    r = np.hypot(x / 1.0, (z - 0.6) / 1.35)
    th = np.arctan2(np.abs(x), z - 0.6)
    tongue = fbm3(np.stack([th * 2.5, r * 0.25, np.zeros_like(r)], -1), 1.5, 4, 702)
    heat = np.clip(1.15 - r / (6.0 + 5.0 * tongue), 0, 1) ** 1.3
    fire = lerp(FIRE_DARK, FIRE_HOT, heat[..., None])
    fire = lerp(fire, M.GHOST * 0.9, (0.35 * (1 - heat) * smoothstep(0.45, 0.8, tongue))[..., None])
    fire = fire * (0.75 + 0.5 * lum)[..., None]
    col = np.where(blue[..., None], fire, iron)
    bone = lerp(bone, BONE_DARK * 0.7, (0.5 * blue)[..., None])          # the horns' painted grooves stay darker
    col = np.where(horn[..., None], bone, col)
    back = nrm[:, :w, 1] > 0.35
    col = np.where((back & blue)[..., None], lerp(M.LEATHER * 0.6, M.LEATHER_HI, lum[..., None]), col)
    return col


def recolour_skull():
    E = {p.name.lower(): p for p in (d.CLIENT / "effects").iterdir()}
    src = Image.open(E["flaming_skull01-green.dds"]).convert("RGB")
    n = int(round(SKULL_S * SIZE))
    a = np.asarray(src.resize((n, n), Image.LANCZOS)).astype(float) / 255
    lum = a @ np.array([0.30, 0.55, 0.15])
    green = (a[..., 1] - np.maximum(a[..., 0], a[..., 2])) > 0.12
    bone = lerp(BONE_DARK * 0.8, BONE, np.clip(lum * 1.15, 0, 1)[..., None])
    glow = lerp(M.GHOST, FIRE_HOT, np.clip(lum * 1.4, 0, 1)[..., None])
    return np.where(green[..., None], glow, bone)


def main():
    w = wgeom.load(BASE)
    nv = shield_shape(w.verts)
    uv_new = w.uvs.copy(); uv_new[:, 0] *= K_SHIELD
    pos, nrm, cov = bake(nv, uv_new, w.faces, SIZE)
    tex = np.zeros((SIZE, SIZE, 3)) + np.array([20, 20, 22.0])
    tex[:, :int(round(0.49 * SIZE))] = recolour_stock(pos, nrm, cov)
    sk = recolour_skull()
    u0, v0 = int(round(SKULL_U * SIZE)), int(round(SKULL_V * SIZE))
    tex[v0:v0 + sk.shape[0], u0:u0 + sk.shape[1]] = sk
    img = Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8))
    img.save(OUT / "shield.png")

    # NIF: reshaped shield, stretched UVs, private texture name, plus the skull shape
    tmp = OUT / "shield_base.nif"
    wgeom.write(w, nv, tmp, texture_rename=(BASE_TEX, PRIVATE_TEX))
    raw = bytearray(tmp.read_bytes())
    old_uv = np.asarray(w.uvs, np.float32).tobytes()
    i = bytes(raw).find(old_uv)
    assert i > 0, "shield UV array not found"
    raw[i:i + len(old_uv)] = np.asarray(uv_new, np.float32).tobytes()
    raw = bytearray(nif4_append.fix_bounds(bytes(raw)))
    sv, suv, sf = skull_mesh()
    sw = place_skull(sv, nv)
    R = w.to_world[:3]; t = w.to_world[3]
    s_local = (sw - t) @ np.linalg.inv(R)
    s_nrm = wgeom.normals(s_local, sf)
    if ((s_local - s_local.mean(0)) * s_nrm).sum(1).mean() < 0:
        s_nrm = -s_nrm
    s_uv = np.stack([SKULL_U + suv[:, 0] * SKULL_S, SKULL_V + suv[:, 1] * SKULL_S], 1)
    _, _, blks, _ = nif4_append.blocks(bytes(raw))
    shape = [b.index for b in blks if b.kind == "NiTriShape"][0]
    out = nif4_append.append_shape(bytes(raw), shape, s_local, s_nrm, s_uv, sf)
    (OUT / "shield.nif").write_bytes(out)
    tmp.unlink()
    # preview OBJ: shield + skull in one mesh, face toward the camera
    allv = np.vstack([nv, sw]); alluv = np.vstack([uv_new, s_uv]); allf = np.vstack([w.faces, sf + len(nv)])
    view = allv * np.array([1, 1, 1])
    wgeom.obj(view, alluv, allf, OUT / "shield.png", OUT / "shield.obj")
    print("built shield:", len(nv), "+", len(sw), "verts;", len(out), "bytes")


if __name__ == "__main__":
    main()
