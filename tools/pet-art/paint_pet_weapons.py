"""Paint private themed copies of the Necroservant and Zombie Guardian weapon textures.

Sources are the stock textures (read only). Output: work/weapons/*_next.png.
Necroservant: blackened old bone/iron, faded dried-crimson accents, rotten wood.
Zombie Guardian: rusted cairn iron matching its plate, worn painted skull.
Low-resolution DAoC look: broad value changes, 1-2px detail, no glow.
"""
from __future__ import annotations

import colorsys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import weapon_texel

HERE = Path(__file__).resolve().parent
ITEMS = HERE.parents[1] / "runtime" / "client-opendaoc" / "app" / "items"
W = HERE / "work" / "weapons"


def load(name):
    return np.asarray(Image.open(W / name).convert("RGB")).astype(float)


def save(arr, name):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(W / name)


def noise(shape, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, shape[0] // scale), max(2, shape[1] // scale)))
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.BICUBIC)
    return np.asarray(img).astype(float) / 255


def hsv(arr):
    flat = arr.reshape(-1, 3) / 255
    out = np.array([colorsys.rgb_to_hsv(*p) for p in flat])
    return out.reshape(arr.shape)


def lum(arr):
    return arr @ [0.299, 0.587, 0.114]


def blur(arr, radius):
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius))).astype(float)


def mix(a, b, t):
    t = np.clip(t, 0, 1)[..., None] if np.ndim(t) == a.ndim - 1 else t
    return a * (1 - t) + np.asarray(b, float) * t


def grade(arr, target, keep=0.35):
    """Recolour to a palette while keeping the original value structure (the old art)."""
    value = lum(arr)[..., None] / 255
    return mix(np.asarray(target, float) * value * 2.0, arr, keep)


# ---------- Necroservant ----------
def necro_hammer():
    src = load("src_hammer.png")
    h = hsv(src)
    value = lum(src)[..., None]
    bone = grade(src, (128, 118, 104), keep=0.15) * 0.62          # blackened ash-grey old bone
    iron = np.repeat(value, 3, axis=2) * [0.55, 0.53, 0.52]         # banded grip -> blackened iron
    metallic = (h[..., 1] > 0.35) & (h[..., 0] > 0.03) & (h[..., 0] < 0.14)
    out = np.where(metallic[..., None], iron, bone)
    # soot in recesses: darker than the local mean gets darker still
    recess = np.clip((blur(out, 3).mean(2) - out.mean(2)) / 40, 0, 1)
    out = out * (1 - 0.6 * recess[..., None])
    # faded dried crimson settled in cracks and low spots
    crimson = np.clip(recess * 1.6 + (noise(out.shape[:2], 14, 7) - 0.5) * 1.8, 0, 1) * (~metallic)
    out = mix(out, (96, 24, 20), crimson * 0.6)
    out *= (0.9 + 0.2 * noise(out.shape[:2], 6, 3))[..., None]
    return out


def necro_shield():
    src = load("src_wood.png")
    h = hsv(src)
    value = lum(src)[..., None]
    metal = (h[..., 1] < 0.12) & (value[..., 0] > 70)
    wood = grade(src, (70, 60, 44), keep=0.2) * 0.62                # dark rotted wood
    rot = noise(src.shape[:2], 10, 11)
    wood = mix(wood, (34, 38, 28), np.clip((rot - 0.5) * 1.6, 0, 0.55))  # green-black rot
    iron = np.repeat(value, 3, axis=2) * [0.72, 0.7, 0.68]
    iron = mix(iron, (74, 46, 32), np.clip((noise(src.shape[:2], 5, 12) - 0.6) * 2.0, 0, 0.5))
    out = np.where(metal[..., None], iron, wood)
    out *= (0.9 + 0.2 * noise(out.shape[:2], 4, 13))[..., None]
    # faded crimson Arawn-like mark on the shield face, painted in model space
    t = weapon_texel.bake(ITEMS / "M_Shield_Grave.NIF", out.shape[1], out.shape[0])
    face = t.covered & (np.abs(t.normal[..., 2]) > 0.8) & (t.position[..., 2] > 1.5)
    x, y = t.position[..., 0] - 5.9, t.position[..., 1] + 1.0      # face centre, shield up = +y
    r = np.hypot(x, y * 0.85)
    ring = np.abs(r - 6.0) < 1.1                                    # a circle
    spine = (np.abs(x) < 0.9) & (y > -9.5) & (y < 8.5)              # a vertical stroke through it
    horns = (np.abs(np.hypot(np.abs(x) - 3.5, y - 8.0) - 3.2) < 0.8) & (y > 8.0)  # two upturned hooks
    mark = face & (ring | spine | horns)
    wear = noise(out.shape[:2], 3, 21) > 0.35
    out = mix(out, (104, 30, 26), (mark & wear) * 0.55)
    return out, mark


# ---------- Zombie Guardian ----------
RUST = [(118, 62, 32), (86, 50, 30), (58, 40, 30)]
GUARD_IRON = (98, 94, 90)


def rusted_iron(src, seed, keep=0.15):
    value = lum(src)[..., None] / 255
    base = mix(np.asarray(GUARD_IRON, float) * value * 1.9, src, keep)
    n1, n2 = noise(src.shape[:2], 9, seed), noise(src.shape[:2], 3, seed + 1)
    out = mix(base, np.asarray(RUST[0]) * (value * 1.7), np.clip((n1 - 0.35) * 2.0, 0, 0.8))
    out = mix(out, RUST[2], np.clip((n2 - 0.7) * 2.5, 0, 0.5))
    return out


def guardian_mace():
    src = load("src_bweapons.png")                     # 512 atlas; only the mace footprint changes
    t = weapon_texel.bake(ITEMS / "b_cr_flangedmace01.nif", src.shape[1], src.shape[0])
    mask = np.asarray(Image.fromarray((t.covered * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))) > 0
    h = hsv(src)
    woodish = (h[..., 0] > 0.03) & (h[..., 0] < 0.13) & (h[..., 1] > 0.3)
    wood = grade(src, (66, 46, 34), keep=0.2) * 0.62                 # old dark haft
    metal = rusted_iron(src, 31)
    painted = np.where(woodish[..., None], wood, metal)
    painted *= (0.9 + 0.2 * noise(src.shape[:2], 5, 33))[..., None]
    out = np.where(mask[..., None], painted, src)
    return out, mask


def guardian_shield():
    src = np.asarray(Image.open(W / "src_towermetal.png").convert("RGB").resize((128, 256), Image.BILINEAR)).astype(float)
    out = rusted_iron(src, 41, keep=0.25) * 0.92
    t = weapon_texel.bake(ITEMS / "Sh_TowerA.NIF", out.shape[1], out.shape[0])
    pos = t.position
    front = t.covered & (np.abs(t.normal[..., 2]) > 0.8)
    # rust streaks running down the face (shield up = +y in model space)
    streak_seed = np.random.default_rng(42)
    for _ in range(9):
        sx = streak_seed.uniform(-8, 8)
        top = streak_seed.uniform(36, 47)
        band = front & (np.abs(pos[..., 0] - sx) < streak_seed.uniform(0.5, 1.0)) & (pos[..., 1] < top) & (pos[..., 1] > top - streak_seed.uniform(6, 16))
        fade = np.clip((pos[..., 1] - (top - 16)) / 16, 0, 1)
        out = mix(out, RUST[1], band * fade * 0.55)
    # dents: small dark/light blotch pairs
    for _ in range(7):
        cx, cy = streak_seed.uniform(-7, 7), streak_seed.uniform(27, 46)
        d = np.hypot(pos[..., 0] - cx, pos[..., 1] - cy)
        out = mix(out, (40, 34, 30), front * (d < 1.0) * 0.45)
        out = mix(out, (150, 140, 128), front * (np.abs(d - 1.2) < 0.3) * (pos[..., 1] > cy) * 0.3)
    # worn painted skull emblem, bone-white paint
    x, y = pos[..., 0], pos[..., 1] - 38.5
    cranium = np.hypot(x / 4.2, (y - 1.0) / 3.8) < 1
    jaw = (np.abs(x) < 2.6) & (y < -1.8) & (y > -4.6)
    eyes = (np.hypot(np.abs(x) - 1.7, y - 0.4) < 1.05)
    nose = (np.abs(x) < 0.5) & (y < -0.6) & (y > -1.9)
    teeth = jaw & (np.abs((x * 2.2) % 2 - 1) < 0.35) & (y > -3.3)
    skull = front & (cranium | jaw) & ~eyes & ~nose & ~teeth
    wear = noise(out.shape[:2], 2, 44) > 0.4
    out = mix(out, (176, 166, 144), (skull & wear) * 0.6)
    return out, skull


if __name__ == "__main__":
    hammer = necro_hammer()
    save(hammer, "necro_hammer_next.png")
    shield, mark = necro_shield()
    save(shield, "necro_shield_next.png")
    mace, mace_mask = guardian_mace()
    save(mace, "guardian_mace_next.png")
    tower, skull = guardian_shield()
    save(tower, "guardian_shield_next.png")
    print("mark texels", int(mark.sum()), "mace footprint", int(mace_mask.sum()), "skull texels", int(skull.sum()))
