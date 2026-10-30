"""Reversible client-only test for open-face Hibernian scale coifs.

This changes only objects.csv Head # for object models 839 and 840. The
original gamedata.mpk is saved before installation. No item stats, server
records, or bot equipment selection are touched.
"""

import argparse
import datetime
import hashlib
import os
import pathlib
import shutil

from si_portal_visuals import Entry, pack_mpk, unpack_mpk


ROOT = pathlib.Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "runtime" / "client-opendaoc" / "app" / "gamedata.mpk"
BACKUPS = ROOT / "runtime" / "deployment-backups"
MODELS = {"839", "840"}
HEAD_FIELD = 13


def patch_objects(content: bytes) -> bytes:
    lines = content.splitlines(keepends=True)
    changed = set()
    for index, raw in enumerate(lines):
        line = raw.rstrip(b"\r\n")
        fields = line.split(b",")
        if fields[0].decode("ascii", errors="ignore") not in MODELS:
            continue
        model = fields[0].decode("ascii")
        if model in changed or len(fields) <= HEAD_FIELD or fields[HEAD_FIELD] != b"4":
            raise ValueError(f"Unexpected or duplicate coif row {model}")
        fields[HEAD_FIELD] = b"2"
        lines[index] = b",".join(fields) + raw[len(line):]
        changed.add(model)
    if changed != MODELS:
        raise ValueError(f"Expected coif rows {MODELS}; found {changed}")
    return b"".join(lines)


def install() -> None:
    original_bytes = ARCHIVE.read_bytes()
    archive_name, entries = unpack_mpk(original_bytes)
    names = [entry.name for entry in entries]
    if names != sorted(names, key=str.casefold):
        raise ValueError("MPK entry order is not case-insensitively sorted")
    matches = [index for index, entry in enumerate(entries) if entry.name.lower() == "objects.csv"]
    if len(matches) != 1:
        raise ValueError("Expected one objects.csv entry")
    index = matches[0]
    old = entries[index]
    updated = Entry(old.name, patch_objects(old.content), old.timestamp, old.flags, old.memory_offset)
    entries[index] = updated
    packed = pack_mpk(archive_name, entries)
    _, recovered = unpack_mpk(packed)
    if len(recovered) != len(entries) or any(
        a.name != b.name or a.content != b.content or a.timestamp != b.timestamp or a.flags != b.flags
        for a, b in zip(entries, recovered)
    ):
        raise ValueError("MPK round-trip changed an unrelated entry or its metadata")
    if any(entry.content != before.content for entry, before in zip(entries, unpack_mpk(original_bytes)[1])
           if entry.name.lower() != "objects.csv"):
        raise ValueError("Unrelated client data changed")

    backup = BACKUPS / ("coif-head-mode-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True, exist_ok=False)
    backup_archive = backup / ARCHIVE.name
    shutil.copy2(ARCHIVE, backup_archive)
    if hashlib.sha256(backup_archive.read_bytes()).digest() != hashlib.sha256(original_bytes).digest():
        raise ValueError("Backup hash mismatch; refusing installation")
    staged = ARCHIVE.with_name(ARCHIVE.name + ".coif-test-tmp")
    if staged.exists():
        raise ValueError(f"Stale staged archive: {staged}")
    staged.write_bytes(packed)
    if hashlib.sha256(staged.read_bytes()).digest() != hashlib.sha256(packed).digest():
        raise ValueError("Staged archive hash mismatch")
    os.replace(staged, ARCHIVE)
    _, installed = unpack_mpk(ARCHIVE.read_bytes())
    if installed[index].content != updated.content:
        raise ValueError("Installed coif catalog does not match prepared bytes")
    print(f"Installed reversible coif head-mode test; original: {backup_archive}")
    print(f"Only object models {', '.join(sorted(MODELS))} changed Head # 4 to 2")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="install the reversible test")
    arguments = parser.parse_args()
    if not arguments.install:
        parser.error("Use --install after closing the game client")
    install()
