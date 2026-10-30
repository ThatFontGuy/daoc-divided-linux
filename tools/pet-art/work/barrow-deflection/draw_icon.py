"""Barrow Deflection icon: 32x32 on the stock stone frame, unholy parry glyph."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

S = 8
N = 32 * S
SHEETS = Path(__file__).resolve().parents[4] / "runtime/client-opendaoc/app/icons"
FRAME_CELL = 137  # stock skull icon: grey stone frame used across the spell sheets

def stock_cell(base):
    sheet = Image.open(SHEETS / f"spl_{(base // 100) * 100}.bmp").convert("RGB")
    i = base % 100
    return sheet.crop(((i % 10) * 32, (i // 10) * 32, (i % 10) * 32 + 32, (i // 10) * 32 + 32))

def blade(d, p0, p1, width, edge, core):
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    nx, ny = -math.sin(ang) * width / 2, math.cos(ang) * width / 2
    tip = (p1[0] + math.cos(ang) * width * 1.4, p1[1] + math.sin(ang) * width * 1.4)
    d.polygon([(p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny), tip,
               (p1[0] - nx, p1[1] - ny), (p0[0] - nx, p0[1] - ny)], fill=edge)
    d.polygon([(p0[0] + nx * .3, p0[1] + ny * .3), (p1[0] + nx * .3, p1[1] + ny * .3),
               (p1[0] - nx * .3, p1[1] - ny * .3), (p0[0] - nx * .3, p0[1] - ny * .3)], fill=core)

def stone_interior():
    """Grey stone like the stock icons: sampled from the frame cell's plain border band."""
    frame = stock_cell(FRAME_CELL)
    samples = [frame.getpixel((x, y)) for x in range(3, 29) for y in (3, 4, 27, 28)] +               [frame.getpixel((x, y)) for y in range(3, 29) for x in (3, 4, 27, 28)]
    base = Image.new("RGB", (26, 26))
    import random
    rnd = random.Random(4569)
    for y in range(26):
        for x in range(26):
            base.putpixel((x, y), samples[rnd.randrange(len(samples))])
    return base.filter(ImageFilter.SMOOTH).resize((N, N), Image.BICUBIC)

def glyph():
    img = stone_interior()
    halo = Image.new("L", (N, N), 0)
    hd = ImageDraw.Draw(halo)
    hd.line((N * .22, N * .82, N * .80, N * .16), fill=255, width=int(S * 6))
    hd.line((N * .08, N * .24, N * .50, N * .47), fill=160, width=int(S * 5))
    halo = halo.filter(ImageFilter.GaussianBlur(S * 3))
    img = Image.composite(Image.new("RGB", (N, N), (70, 200, 80)), img, halo.point(lambda v: int(v * .55)))
    d = ImageDraw.Draw(img)
    ol = (8, 8, 10)
    # Dark outlines first, like the stock glyphs.
    blade(d, (N * .07, N * .235), (N * .475, N * .455), S * 5.4, ol, ol)
    d.arc((N * .26, N * .16, N * .82, N * .72), 188, 332, fill=ol, width=int(S * 5.0))
    blade(d, (N * .21, N * .83), (N * .765, N * .195), S * 6.4, ol, ol)
    d.line((N * .15, N * .64, N * .40, N * .89), fill=ol, width=int(S * 4.6))
    # The blow being turned aside: dark iron blade from the upper left.
    blade(d, (N * .08, N * .24), (N * .47, N * .45), S * 3.6, (70, 74, 84), (150, 156, 168))
    # Blood-red deflection arc.
    d.arc((N * .26, N * .16, N * .82, N * .72), 190, 330, fill=(110, 0, 10), width=int(S * 3.4))
    d.arc((N * .29, N * .19, N * .79, N * .69), 195, 325, fill=(235, 36, 36), width=int(S * 1.5))
    # The Sluaghbinder's bone blade rising from the lower left.
    blade(d, (N * .22, N * .82), (N * .76, N * .20), S * 4.4, (176, 162, 124), (250, 244, 224))
    d.line((N * .15, N * .64, N * .40, N * .89), fill=(120, 104, 74), width=int(S * 2.8))   # crossguard
    d.line((N * .09, N * .95, N * .24, N * .80), fill=(70, 30, 26), width=int(S * 3.0))     # grip
    d.ellipse((N * .04, N * .90, N * .14, N * 1.0), fill=(220, 212, 186))                     # bone pommel
    cx, cy = N * .47, N * .46
    for a in range(0, 360, 45):
        r = S * (4.2 if a % 90 == 0 else 2.4)
        d.line((cx, cy, cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r),
               fill=(255, 220, 170), width=int(S * 1.0))
    d.ellipse((cx - S * 1.2, cy - S * 1.2, cx + S * 1.2, cy + S * 1.2), fill=(255, 250, 235))
    return img.resize((32, 32), Image.LANCZOS)

def draw():
    frame = stock_cell(FRAME_CELL)
    inner = glyph().crop((3, 3, 29, 29))
    icon = frame.copy()
    icon.paste(inner, (3, 3))
    return icon

if __name__ == "__main__":
    icon = draw()
    icon.save("barrow_deflection_32.png")
    icon.resize((256, 256), Image.NEAREST).save("barrow_deflection_preview.png")
    # In context: stock Sluaghbinder icons at 1x and 4x.
    neighbours = [110, 81, 20, 169, 155, 137]
    row = Image.new("RGB", (36 * (len(neighbours) + 1) + 4, 40), (24, 24, 24))
    for n, b in enumerate(neighbours):
        row.paste(stock_cell(b), (4 + n * 36, 4))
    row.paste(icon, (4 + len(neighbours) * 36, 4))
    row.save("context_1x.png")
    row.resize((row.width * 4, row.height * 4), Image.NEAREST).save("context_4x.png")
