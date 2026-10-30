"""Install Codex's approved v-next art for three pets (private assets only).

  install : python install_vnext.py install
  rollback: python install_vnext.py rollback <backup-folder>

Changes, with backups and hashes first:
  figures\\skins\\skin099.mpk  sluagh_sturdy_zombie_body.dds, sluagh_zombie_magician_body.dds,
                              sluagh_zombie_defender_body.dds (Zombie Guardian)
  figures\\Sluaghbinder_ZombieMagician.NIF  shoulder spikes folded (64 vertices moved)
Every other skin099 entry is verified byte-identical. The priest, Dullahan,
walking dead and all stock assets are untouched. Run with the launcher, client
and server CLOSED.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import update_skins  # noqa: E402
from daoc_catalog import CLIENT  # noqa: E402

VNEXT = HERE / "work" / "v-next"
NIF = "Sluaghbinder_ZombieMagician.NIF"
SKINS = [
    ("skin099.mpk", "sluagh_sturdy_zombie_body.dds", "work/v-next/sturdy_next.png", "Sluaghbinder_SturdyZombie.NIF"),
    ("skin099.mpk", "sluagh_zombie_magician_body.dds", "work/v-next/magician_next.png", NIF),
    ("skin099.mpk", "sluagh_zombie_defender_body.dds", "work/v-next/guardian_next.png", "Sluaghbinder_ZombieDefender.NIF"),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def install():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = HERE / "install-backups" / f"vnext-{stamp}"
    backup.mkdir(parents=True)
    target = CLIENT / "figures" / NIF
    shutil.copy2(target, backup / NIF)
    manifest = {"created": stamp, "nif": {NIF: sha(target.read_bytes())}}
    shutil.copy2(VNEXT / NIF, target)
    if sha(target.read_bytes()) != sha((VNEXT / NIF).read_bytes()):
        raise SystemExit("NIF copy mismatch")
    update_skins.SKINS = SKINS
    update_skins.install()
    skins_backup = max((HERE / "install-backups").glob("skins-*"), key=lambda p: p.stat().st_mtime)
    manifest["skins_backup"] = str(skins_backup)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nInstalled v-next. Rollback with:\n  python install_vnext.py rollback \"{backup}\"")


def rollback(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text())
    for name, digest in manifest["nif"].items():
        target = CLIENT / "figures" / name
        shutil.copy2(folder / name, target)
        if sha(target.read_bytes()) != digest:
            raise SystemExit(f"rollback hash mismatch: {name}")
    update_skins.rollback(Path(manifest["skins_backup"]))
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    else:
        print(__doc__)
