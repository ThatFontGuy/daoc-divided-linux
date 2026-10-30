"""Extract pet skin DDS entries from the Claude-version client and save PNG previews."""
import io
from pathlib import Path
from PIL import Image
from daoc_catalog import CLIENT, mpk

OUT = Path(__file__).parent / "originals"
OUT.mkdir(parents=True, exist_ok=True)

WANTED = {
    "skin008.mpk": ["b_unde01m.dds", "e_unde01.dds", "a_unde01f.dds"],
    "skin099.mpk": ["sluagh_zombie_defender_body.dds"],
    "skin106.mpk": ["corpse_body.dds", "sluagh_dullahan_body.dds"],
}

for archive_name, names in WANTED.items():
    _, entries = mpk(CLIENT / "figures" / "skins" / archive_name)
    by_name = {e.name.lower(): e for e in entries}
    for name in names:
        entry = by_name.get(name.lower())
        if not entry:
            close = [n for n in by_name if n.startswith(name.lower()[:6])][:8]
            print(f"{archive_name}/{name}: MISSING (similar: {close})")
            continue
        data = entry.data
        (OUT / name).write_bytes(data)
        fourcc = data[84:88]
        height, width = int.from_bytes(data[12:16], "little"), int.from_bytes(data[16:20], "little")
        mips = int.from_bytes(data[28:32], "little")
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
            image.convert("RGBA").save(OUT / (Path(name).stem + ".png"))
            alpha = image.convert("RGBA").getchannel("A").getextrema()
            print(f"{archive_name}/{name}: {width}x{height} {fourcc} mips={mips} mode={image.mode} alpha={alpha} bytes={len(data)}")
        except Exception as exc:
            print(f"{archive_name}/{name}: {width}x{height} {fourcc} mips={mips} decode failed: {exc}")
