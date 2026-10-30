"""Give the classic client Abermenai's terrain (zone 253), so the 15-19 battleground loads.

The stock client ships zone253 with only csv253/dat253/sounds.dat: no ter253.mpk or lod253.mpk, which every
outdoor zone the client renders has. Entering Abermenai showed a red screen and dropped the player to character
select (tester report 2026-10-27, Hibernian side; every realm is affected). Abermenai is a copy of Thidranki:
dat253's terrain.pcx and offset.pcx are byte-identical to dat252's, so Thidranki's terrain archives fit it.
ter253.mpk / lod253.mpk are ter252.mpk / lod252.mpk with only the archive's own name changed; every file entry,
the directory and its CRC are kept byte for byte.

    python add_abermenai_terrain.py install <client app folder> [--from <classic client app folder>] [--apply]
    python add_abermenai_terrain.py verify <client app folder>
    python add_abermenai_terrain.py rollback <client app folder> <backup folder> [--apply]

<client app folder> is runtime/client-opendaoc/app. --from takes Thidranki from another client: the modern test
client's dat252 is a later Thidranki whose maps no longer match Abermenai, while the classic client's still do (and
its ter252/lod252 are the same files in both). Close the game first. Without --apply nothing is written.
Backups go to runtime/client-opendaoc/backups/ (never shipped by the release build).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import zlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "asset-tool"))
import archive  # noqa: E402  (the repository's validated MPAK v2 codec)

SOURCE_ZONE, TARGET_ZONE = 252, 253
KINDS = ("ter", "lod")
SAME_MAPS = ("terrain.pcx", "offset.pcx")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def renamed(blob: bytes, name: bytes) -> bytes:
    """The MPAK with only its archive name replaced (the directory CRC covers the directory, not the name)."""
    archive.read(blob)
    checksum, ds, ns, count = struct.unpack("<4I", bytes(v ^ i for i, v in enumerate(blob[5:21])))
    n = zlib.compress(name, 9)
    header = struct.pack("<4I", checksum, ds, len(n), count)
    result = b"MPAK\x02" + bytes(v ^ i for i, v in enumerate(header)) + n + blob[21 + ns:]
    new_name, entries = archive.read(result)
    if new_name != name or entries != archive.read(blob)[1]:
        raise ValueError("renamed archive differs from its source")
    archive.verify_memory_image(result)
    return result


def zone(app: Path, zone_id: int) -> Path:
    return app / "zones" / f"zone{zone_id:03d}"


def maps(dat: Path) -> dict[str, bytes]:
    _, entries = archive.read(dat.read_bytes())
    return {e.name.lower(): e.data for e in entries if e.name.lower() in SAME_MAPS}


def plan(app: Path, source_app: Path | None = None) -> dict[str, bytes]:
    """The files to add, keyed by their path under app. Refuses if the zones don't match."""
    source, target = zone(source_app or app, SOURCE_ZONE), zone(app, TARGET_ZONE)
    dat_source, dat_target = source / f"dat{SOURCE_ZONE}.mpk", target / f"dat{TARGET_ZONE}.mpk"
    for path in [dat_source, dat_target] + [source / f"{k}{SOURCE_ZONE}.mpk" for k in KINDS]:
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    a, b = maps(dat_source), maps(dat_target)
    if set(a) != set(SAME_MAPS) or a != b:
        raise SystemExit(f"zone{TARGET_ZONE}'s terrain maps differ from zone{SOURCE_ZONE}'s; its terrain can't be copied")
    files = {}
    for kind in KINDS:
        name = f"{kind}{TARGET_ZONE}.mpk"
        files[f"zones/zone{TARGET_ZONE}/{name}"] = renamed((source / f"{kind}{SOURCE_ZONE}.mpk").read_bytes(), name.encode())
    return files


def client_running(app: Path) -> bool:
    try:
        import subprocess
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-Process | Where-Object { $_.Path } | ForEach-Object { $_.Path }"],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    root = str(app.resolve()).lower()
    return any(line.strip().lower().startswith(root) for line in out.splitlines())


def install(app: Path, apply: bool, source_app: Path | None = None) -> int:
    files = plan(app, source_app)
    todo = {}
    for rel, data in files.items():
        path = app / rel
        if path.is_file():
            if path.read_bytes() == data:
                print(f"already installed: {rel}")
                continue
            raise SystemExit(f"{rel} exists with other content; roll back or inspect it first")
        todo[rel] = data
    for rel, data in todo.items():
        print(f"add {rel} ({len(data):,} bytes, sha256 {sha(data)})")
    if not todo or not apply:
        print("nothing to do" if not todo else "preview only; pass --apply to write")
        return 0
    if client_running(app):
        raise SystemExit("a program is running from this client folder; close the game first")
    backup = app.parent / "backups" / f"abermenai-terrain-{datetime.now():%Y%m%d-%H%M%S}"
    backup.mkdir(parents=True)
    listing = sorted(p.name for p in zone(app, TARGET_ZONE).iterdir())
    manifest = {"app": str(app.resolve()), "added": {rel: sha(d) for rel, d in todo.items()},
                f"zone{TARGET_ZONE}_before": listing}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for rel, data in todo.items():
        (app / rel).write_bytes(data)
    verify(app, source_app)
    print(f"installed; backup manifest: {backup}")
    return 0


def verify(app: Path, source_app: Path | None = None) -> int:
    files = plan(app, source_app)
    for rel, data in files.items():
        path = app / rel
        if not path.is_file() or path.read_bytes() != data:
            raise SystemExit(f"not installed: {rel}")
        name, _ = archive.read(path.read_bytes())
        print(f"ok {rel} (archive name {name.decode()})")
    return 0


def rollback(app: Path, backup: Path, apply: bool) -> int:
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    for rel, digest in manifest["added"].items():
        path = app / rel
        if not path.is_file():
            print(f"already gone: {rel}")
            continue
        if sha(path.read_bytes()) != digest:
            raise SystemExit(f"{rel} changed since install; not removing it")
        print(f"remove {rel}")
        if apply:
            if client_running(app):
                raise SystemExit("a program is running from this client folder; close the game first")
            path.unlink()
    if not apply:
        print("preview only; pass --apply to remove")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("install"); p.add_argument("app", type=Path); p.add_argument("--apply", action="store_true")
    p.add_argument("--from", dest="source_app", type=Path)
    p = sub.add_parser("verify"); p.add_argument("app", type=Path); p.add_argument("--from", dest="source_app", type=Path)
    p = sub.add_parser("rollback"); p.add_argument("app", type=Path); p.add_argument("backup", type=Path)
    p.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "install":
        return install(args.app, args.apply, args.source_app)
    if args.command == "verify":
        return verify(args.app, args.source_app)
    return rollback(args.app, args.backup, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
