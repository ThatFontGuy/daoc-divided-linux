"""TEMPORARY diagnostic: labelled grid textures for the cloak, to learn how the client maps it.

cata  (objects col 72): 8x8 cells, columns A-H by hue, rows 1-8 by brightness, white labels.
classic (col 11, 256): 4x4 cells, grey checker with big red labels W-Z / 1-4.
Install with SLUAGH_CLOAK_DEBUG=1 python -B install_sluagh_armor.py install; reinstall without it afterwards.
"""
from pathlib import Path
import colorsys
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "out"


def font(size):
    for name in ("arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def cata(size=512, n=8):
    im = Image.new("RGB", (size, size)); d = ImageDraw.Draw(im); c = size // n; f = font(int(c * 0.55))
    for col in range(n):
        for row in range(n):
            r, g, b = colorsys.hsv_to_rgb(col / n, 0.85, 0.35 + 0.65 * (n - row) / n)
            d.rectangle((col * c, row * c, col * c + c - 1, row * c + c - 1), fill=(int(r * 255), int(g * 255), int(b * 255)), outline=(0, 0, 0))
            d.text((col * c + c * 0.12, row * c + c * 0.15), f"{'ABCDEFGH'[col]}{row + 1}", fill=(255, 255, 255), font=f,
                   stroke_width=2, stroke_fill=(0, 0, 0))
    return im


def classic(size=256, n=4):
    im = Image.new("RGB", (size, size)); d = ImageDraw.Draw(im); c = size // n; f = font(int(c * 0.5))
    for col in range(n):
        for row in range(n):
            v = 200 if (col + row) % 2 == 0 else 120
            d.rectangle((col * c, row * c, col * c + c - 1, row * c + c - 1), fill=(v, v, v))
            d.text((col * c + c * 0.15, row * c + c * 0.2), f"{'WXYZ'[col]}{row + 1}", fill=(220, 0, 0), font=f)
    return im


if __name__ == "__main__":
    cata().save(OUT / "debug_cloak_cata.png"); classic().save(OUT / "debug_cloak_classic.png"); print("ok")
