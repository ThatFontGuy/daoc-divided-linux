"""Replace the private pet skin entries with the current artwork (edge-padded).

  install : python update_skins.py install
  rollback: python update_skins.py rollback <backup-folder>

Replaces ONLY these private entries (every other archive entry is verified
byte-identical afterwards):
  skin099.mpk  sluagh_zombie_defender_body.dds, sluagh_sturdy_zombie_body.dds,
               sluagh_zombie_magician_body.dds, sluagh_zombie_priest_body.dds
  skin106.mpk  sluagh_dullahan_body.dds   (Codex's private Dullahan entry)
Edge padding fills the space around each UV island with the island's own
colour so texture filtering / mipmaps never pull the light atlas background
into a seam (a pale line in game).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from daoc_catalog import CLIENT, archive  # noqa: E402
from install_pet_art import encode_dds  # noqa: E402
from refine_dullahan import pad_islands  # noqa: E402
from texelmap import bake  # noqa: E402

SKINS = [
    ("skin099.mpk", "sluagh_zombie_defender_body.dds", "work/guardian_final.png", "Sluaghbinder_ZombieDefender.NIF"),
    ("skin099.mpk", "sluagh_sturdy_zombie_body.dds", "work/sturdy_v2.png", "Sluaghbinder_SturdyZombie.NIF"),
    ("skin099.mpk", "sluagh_zombie_magician_body.dds", "work/magician_v3.png", "Sluaghbinder_ZombieMagician.NIF"),
    ("skin099.mpk", "sluagh_zombie_priest_body.dds", "work/priest_v2.png", "Sluaghbinder_ZombiePriest.NIF"),
    ("skin106.mpk", "sluagh_dullahan_body.dds", "work/dullahan_final.png", "Sluaghbinder_Dullahan.NIF"),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def padded(png: str, nif: str) -> Image.Image:
    tm, _ = bake(nif)
    rgb = np.asarray(Image.open(HERE / png).convert("RGB")).astype(float)
    return Image.fromarray(np.clip(pad_islands(rgb, tm.covered), 0, 255).astype(np.uint8))


def install():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = HERE / "install-backups" / f"skins-{stamp}"
    backup.mkdir(parents=True)
    manifest = {"created": stamp, "archives": {}}
    by_archive = {}
    for archive_name, entry, png, nif in SKINS:
        by_archive.setdefault(archive_name, []).append((entry, png, nif))
    blobs = {}
    for archive_name, items in by_archive.items():
        path = CLIENT / "figures" / "skins" / archive_name
        original = path.read_bytes()
        shutil.copy2(path, backup / archive_name)
        manifest["archives"][archive_name] = sha(original)
        name, entries = archive.read(original)
        replacements = {}
        for entry_name, png, nif in items:
            current = next(e for e in entries if e.name.lower() == entry_name)
            art = padded(png, nif)
            art.save(HERE / "work" / f"final_{entry_name.replace('.dds', '.png')}")
            replacements[entry_name] = encode_dds(art, current.data)
        new = [archive.Entry(e.name, replacements.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in entries]
        blob = archive.write(name, new)
        archive.verify_memory_image(blob)
        for old, fresh in zip(entries, archive.read(blob)[1]):
            if old.name.lower() not in replacements and old != fresh:
                raise SystemExit(f"unrelated entry changed: {old.name}")
        blobs[path] = blob
    for path, blob in blobs.items():
        path.write_bytes(blob)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"\nInstalled. Rollback with:\n  python update_skins.py rollback \"{backup}\"")


def rollback(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text())
    for archive_name, digest in manifest["archives"].items():
        target = CLIENT / "figures" / "skins" / archive_name
        shutil.copy2(folder / archive_name, target)
        if sha(target.read_bytes()) != digest:
            raise SystemExit(f"rollback hash mismatch: {archive_name}")
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    else:
        print(__doc__)
