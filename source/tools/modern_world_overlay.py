"""Make a 1.130 client show this server's (OpenDAoC's classic) world instead of live's.

    python modern_world_overlay.py plan     <classic app> <1.130 app> [--manifest out.json]
    python modern_world_overlay.py apply    <classic app> <1.130 app> --backups <folder> [--apply]
    python modern_world_overlay.py verify   <1.130 app> <manifest.json>
    python modern_world_overlay.py rollback <1.130 app> <backup folder> [--apply]

The classic client (1.127) carries OpenDAoC's world data: zone tables, terrain, capital and dungeon pieces,
keep and frontier models, and a Newtowns folder holding only OpenDAoC's own 7 models. The retail 1.130 client
carries live's world: 196 extra New Towns models drawn in classic positions, renumbered buildings (so door IDs
differ), battlegrounds in other regions, no Marfach Caverns. The server, its navmeshes and the bots use the
classic world (docs/MODERN-CLIENT-WORLD-MISMATCH.md).

The overlay touches only the world folders (zones/, Newtowns/, frontiers/): every file there that the classic
client has and the 1.130 client lacks or has differently is copied from the classic client, and every Newtowns
model the classic client doesn't have is removed. game.dll, the UI, items, figures and effects are untouched.

apply and rollback preview unless --apply is given. They refuse while a program runs from the client folder,
check every file against the plan's input hash before changing anything, back up each replaced or removed file
under --backups, and verify every output hash afterwards. Nothing is started.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

FORMAT = 1
WORLD_FOLDERS = ('zones', 'newtowns', 'frontiers')
NEWTOWNS_MODELS = 'newtowns/zones/nifs'
MANIFEST = 'world-overlay.json'


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def world_files(app: Path) -> dict[str, Path]:
    """{lower-case relative path: real path} for every file under the world folders (Windows paths ignore case)."""
    out = {}
    for top in app.iterdir():
        if top.is_dir() and top.name.lower() in WORLD_FOLDERS:
            for path in top.rglob('*'):
                if path.is_file():
                    out[path.relative_to(app).as_posix().lower()] = path
    return out


def target_path(app: Path, relative: str, known: dict[str, Path]) -> Path:
    """Where `relative` lives in `app`: the existing file, else under the existing folders' own spelling."""
    if relative in known:
        return known[relative]
    current = app
    for part in relative.split('/'):
        match = next((p for p in current.iterdir() if p.name.lower() == part), None) if current.is_dir() else None
        current = match if match is not None else current / part
    return current


def selected(relative: str, only: list[str] | None) -> bool:
    return not only or any(relative == p or relative.startswith(p.rstrip('/') + '/') for p in only)


def plan(classic: Path, client: Path, only: list[str] | None = None) -> dict:
    """The overlay as a list of replace/add/remove entries, each with its input and output SHA256. `only` limits it
    to these paths or folders (lower case, relative to the client)."""
    only = [p.lower().replace('\\', '/') for p in only] if only else None
    source = {k: v for k, v in world_files(classic).items() if selected(k, only)}
    target = {k: v for k, v in world_files(client).items() if selected(k, only)}
    entries = []
    for relative in sorted(source):
        new = sha(source[relative])
        if relative in target:
            old = sha(target[relative])
            if old != new:
                entries.append(dict(path=relative, action='replace', before=old, after=new, size=source[relative].stat().st_size))
        else:
            entries.append(dict(path=relative, action='add', before=None, after=new, size=source[relative].stat().st_size))
    for relative in sorted(target):
        if relative.startswith(NEWTOWNS_MODELS + '/') and relative not in source:
            entries.append(dict(path=relative, action='remove', before=sha(target[relative]), after=None, size=0))
    return dict(format=FORMAT, classic=str(classic), entries=entries)


def summary(manifest: dict) -> str:
    counts = {a: sum(e['action'] == a for e in manifest['entries']) for a in ('replace', 'add', 'remove')}
    size = sum(e['size'] for e in manifest['entries']) / 2**20
    return f"{counts['replace']} replaced, {counts['add']} added, {counts['remove']} removed ({size:.1f} MB copied)"


def running_from(folder: Path) -> list[str]:
    """Programs whose executable is inside `folder` (the client keeps world files open while it runs)."""
    script = ("Get-Process | Where-Object { $_.Path } | ForEach-Object { $_.Path }")
    try:
        paths = subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True, text=True,
                               timeout=60).stdout.splitlines()
    except (OSError, subprocess.TimeoutExpired):
        raise SystemExit('Could not list running programs; close the game client and retry.')
    root = str(folder.resolve()).lower().rstrip('\\') + '\\'
    return [p for p in paths if p.lower().startswith(root)]


def check_closed(client: Path):
    if running := running_from(client):
        raise SystemExit(f'Close the game client first ({running[0]}). Nothing was changed.')


def apply(classic: Path, client: Path, backups: Path, write: bool, only: list[str] | None = None) -> Path | None:
    manifest = plan(classic, client, only)
    if not manifest['entries']:
        print('The client already shows the classic world. Nothing to do.')
        return None
    print(f'Plan: {summary(manifest)}')
    if not write:
        print('Preview only. Run again with --apply to change the client.')
        return None
    check_closed(client)
    source, target = world_files(classic), world_files(client)
    for entry in manifest['entries']:  # nothing changed since the plan, on either side
        if entry['before'] is not None and sha(target[entry['path']]) != entry['before']:
            raise SystemExit(f"{entry['path']} changed while planning. Nothing was changed.")
    folder = backups / f"world-overlay-{datetime.now():%Y%m%d-%H%M%S-%f}"
    folder.mkdir(parents=True)
    (folder / MANIFEST).write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    done = []
    try:
        for entry in manifest['entries']:
            path = target_path(client, entry['path'], target)
            if entry['action'] in ('replace', 'remove'):
                saved = folder / 'files' / entry['path']
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, saved)
            if entry['action'] == 'remove':
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source[entry['path']], path)
            done.append(entry)
        problems = verify(client, manifest)
        if problems:
            raise RuntimeError('; '.join(problems[:5]))
    except BaseException:
        print(f'Failed after {len(done)} of {len(manifest["entries"])} changes; restoring the client from {folder}.')
        restore(client, folder, done)
        raise
    (folder / 'applied.txt').write_text(f'Applied {summary(manifest)} to {client}\n', encoding='utf-8')
    print(f'Applied and verified: {summary(manifest)}. Backup and manifest: {folder}')
    return folder


def verify(client: Path, manifest: dict) -> list[str]:
    """Every entry's output: a removed file is gone, every other file has its output hash."""
    files = world_files(client)
    problems = []
    for entry in manifest['entries']:
        if entry['action'] == 'remove':
            if entry['path'] in files:
                problems.append(f"{entry['path']} still present")
        elif entry['path'] not in files:
            problems.append(f"{entry['path']} missing")
        elif sha(files[entry['path']]) != entry['after']:
            problems.append(f"{entry['path']} has the wrong contents")
    return problems


def restore(client: Path, folder: Path, entries: list[dict]):
    """Undo `entries`: put back replaced and removed files from the backup, delete added files."""
    files = world_files(client)
    for entry in reversed(entries):
        path = target_path(client, entry['path'], files)
        if entry['action'] == 'add':
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / 'files' / entry['path'], path)


def rollback(client: Path, folder: Path, write: bool):
    manifest = json.loads((folder / MANIFEST).read_text(encoding='utf-8'))
    print(f'Rollback of {summary(manifest)} from {folder}')
    files = world_files(client)
    for entry in manifest['entries']:  # the client still holds exactly what the overlay wrote
        if entry['action'] == 'remove':
            if entry['path'] in files:
                raise SystemExit(f"{entry['path']} came back after the overlay; not rolling back.")
        elif entry['path'] not in files or sha(files[entry['path']]) != entry['after']:
            raise SystemExit(f"{entry['path']} changed after the overlay; not rolling back.")
    if not write:
        print('Preview only. Run again with --apply to restore the client.')
        return
    check_closed(client)
    restore(client, folder, manifest['entries'])
    files = world_files(client)
    bad = [e['path'] for e in manifest['entries'] if
           (e['action'] == 'add' and e['path'] in files) or
           (e['action'] != 'add' and (e['path'] not in files or sha(files[e['path']]) != e['before']))]
    if bad:
        raise SystemExit(f'Rollback left {len(bad)} files wrong, e.g. {bad[0]}')
    (folder / 'rolled-back.txt').write_text(f'Rolled back {client}\n', encoding='utf-8')
    print('Rolled back and verified: the client has its original world files again.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan'); p.add_argument('classic', type=Path); p.add_argument('client', type=Path)
    p.add_argument('--manifest', type=Path)
    a = sub.add_parser('apply'); a.add_argument('classic', type=Path); a.add_argument('client', type=Path)
    a.add_argument('--backups', type=Path, required=True); a.add_argument('--apply', action='store_true')
    a.add_argument('--only', action='append', help='limit to this path or folder (repeatable), e.g. zones/zones.mpk')
    p.add_argument('--only', action='append')
    v = sub.add_parser('verify'); v.add_argument('client', type=Path); v.add_argument('manifest', type=Path)
    r = sub.add_parser('rollback'); r.add_argument('client', type=Path); r.add_argument('backup', type=Path)
    r.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    for name in ('classic', 'client'):
        if hasattr(args, name) and not (getattr(args, name) / 'game.dll').is_file():
            raise SystemExit(f'{getattr(args, name)} is not a client folder (no game.dll).')
    if args.command == 'plan':
        manifest = plan(args.classic, args.client, args.only)
        print(summary(manifest))
        if args.manifest:
            args.manifest.write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    elif args.command == 'apply':
        apply(args.classic, args.client, args.backups, args.apply, args.only)
    elif args.command == 'verify':
        problems = verify(args.client, json.loads(args.manifest.read_text(encoding='utf-8')))
        print('\n'.join(problems[:20]) if problems else 'The client matches the overlay.')
        sys.exit(1 if problems else 0)
    else:
        rollback(args.client, args.backup, args.apply)


if __name__ == '__main__':
    main()
