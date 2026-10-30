"""List printable names embedded in old NetImmerse NIFs (texture refs, node names)."""
import re
import sys
from pathlib import Path

TEX = re.compile(rb"[A-Za-z0-9_\-./]{2,64}\.(?:dds|tga|bmp)", re.IGNORECASE)
WORD = re.compile(rb"[ -~]{4,}")

for arg in sys.argv[1:]:
    path = Path(arg)
    data = path.read_bytes()
    textures = sorted({m.group().decode("latin1") for m in TEX.finditer(data)})
    print(f"== {path.name} ({len(data)} bytes) textures: {textures}")
    if "--all" in sys.argv:
        words = sorted({m.group().decode("latin1") for m in WORD.finditer(data)})
        print("   ", [w for w in words if not w.startswith("Ni")][:60])
