"""Walking Dead (Sluaghbinder level 4 pet): subtle recolour of the stock zombie.

Source: stock zomtex01.dds (model 110 / Zombie.NIF, 256x256). The stock
texture is never modified; this writes a private copy for model 2499.
Zombie.NIF is too old for pyffi, so the work is done in texture space as pure
colour shifts that keep every pixel's original brightness (all painted detail,
shading and seams stay exactly where they were):

  skin     olive-green  -> muted purple-grey, with faint bruise mottling
  eye      yellow glint -> pale lilac glint
  wounds   crimson      -> slightly deeper wine/plum
  rags     cool grey    -> a touch warmer grey-brown, so they read against the skin
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / "originals" / "zomtex01.png"
OUT = HERE / "work" / "walkingdead_v1.png"


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def value_noise(shape, cells, seed):
    rng = np.random.default_rng(seed)
    grid = rng.random((cells + 1, cells + 1))
    img = Image.fromarray((grid * 255).astype(np.uint8)).resize(shape[::-1], Image.BICUBIC)
    return np.asarray(img).astype(float) / 255.0


def paint(src=SRC):
    a = np.asarray(Image.open(src).convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]

    # Masks (soft).
    olive = (r + g) / 2 - b                                      # >0 on skin, <=0 on the cool-grey rags
    eye = (smoothstep(30, 45, g - b) * smoothstep(25, 38, r - b) *
           (np.hypot(xx - 54, yy - 37) < 4.5))                     # the yellow glint of the eye only
    skin = smoothstep(2, 12, olive) * (1 - eye)
    wound = smoothstep(30, 50, r - g)
    # Small green-cyan specks on the skin fail the olive test; treat them as
    # skin where they sit inside a skin area (not in the rag tiles).
    around = np.asarray(Image.fromarray((skin * 255).astype(np.uint8)).resize((32, 32), Image.BILINEAR)
                        .resize((w, h), Image.BILINEAR)).astype(float) / 255.0
    speck = smoothstep(4, 12, g - r) * smoothstep(0.55, 0.8, around) * (1 - wound)
    skin = np.maximum(skin, speck)
    teeth = ((xx < 76) & (yy > 200)).astype(float) * skin     # mouth tile: keep bone, not skin
    skin = skin * (1 - teeth)
    rags = smoothstep(-2, -10, olive) * (1 - wound) * (1 - speck)

    out = a.copy()

    # Skin: same brightness, muted purple-grey hue. Low-frequency mottling
    # varies the tint a little (bruising) without adding hard edges.
    mottle = 0.75 * value_noise((h, w), 6, 7) + 0.25 * value_noise((h, w), 14, 11)
    tint = np.stack([1.00, 0.95, 1.07])                          # grey with a violet cast, low chroma
    bruise = np.stack([0.98, 0.89, 1.10])                        # slightly deeper violet
    k = smoothstep(0.45, 0.85, mottle)[..., None] * 0.55
    hue = tint * (1 - k) + bruise * k
    target = lum[..., None] * hue * 0.94                         # the olive read darker than its luminance
    target = target * (1 - 0.06 * k)                             # bruises a touch darker
    keep = 0.12                                                  # a trace of the old tone in the crevices
    skin_rgb = target * (1 - keep) + a * keep
    out = out * (1 - skin[..., None]) + skin_rgb * skin[..., None]

    # Teeth: aged bone instead of the old green-yellow.
    bone = lum[..., None] * np.stack([1.07, 1.02, 0.88])
    out = out * (1 - teeth[..., None]) + bone * teeth[..., None]

    # Eye: pale lilac glint instead of yellow.
    eye_rgb = np.clip(lum[..., None] * np.stack([1.25, 1.12, 1.55]) + 18, 0, 255)
    out = out * (1 - eye[..., None]) + eye_rgb * eye[..., None]

    # Wounds: crimson nudged toward wine/plum.
    wound_rgb = a * np.stack([0.90, 0.95, 1.18])
    out = out * (1 - wound[..., None]) + wound_rgb * wound[..., None]

    # Rags and belt: slightly warmer grey-brown.
    rag_rgb = lum[..., None] * np.stack([1.05, 0.99, 0.90])
    out = out * (1 - 0.7 * rags[..., None]) + rag_rgb * (0.7 * rags[..., None])

    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT)
    return img


def compare(img):
    before = Image.open(SRC).convert("RGB").resize((512, 512), Image.NEAREST)
    after = img.resize((512, 512), Image.NEAREST)
    sheet = Image.new("RGB", (1040, 540), (24, 24, 28))
    sheet.paste(before, (8, 20)); sheet.paste(after, (528, 20))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    d.text((10, 4), "walking dead - stock zombie texture (unchanged)", fill=(220, 220, 220))
    d.text((530, 4), "walking dead - new private texture", fill=(220, 220, 220))
    path = HERE / "work" / "WALKINGDEAD_before_after.png"
    sheet.save(path)
    return path


if __name__ == "__main__":
    print("wrote", OUT, compare(paint()))
