"""Install or roll back a server's navmesh folder for fix B (live 1.130 geometry), docs/MODERN-CLIENT-WORLD-MISMATCH.md.

    python live_world_navmesh.py install  <server folder> <staged navmesh folder> --backups <folder> [--apply]
    python live_world_navmesh.py rollback <server folder> <backup folder> [--apply]

The modern test server's navmesh folder is a junction to the Classic game's meshes. install never writes through
it: it records the junction's target, removes only the link, and copies the staged folder in its place. A real
folder is moved into the backup instead. rollback deletes the installed folder (only a real folder this tool put
there) and restores the junction or the moved folder. Both preview unless --apply is given, and refuse while
something listens on the server's port.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
from datetime import datetime
from pathlib import Path

MARKER = 'installed-by-live_world_navmesh.txt'


def listening(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(('127.0.0.1', port)) == 0


def server_port(server: Path) -> int:
    text = (server / 'config' / 'serverconfig.xml').read_text(encoding='utf-8-sig')
    start = text.find('<Port>')
    return int(text[start + 6:text.find('</Port>', start)])


def check_stopped(server: Path):
    if listening(server_port(server)):
        raise SystemExit('The server is running. Stop it first. Nothing was changed.')


def digest(folder: Path) -> dict[str, str]:
    out = {}
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.name != MARKER:
            h = hashlib.sha256()
            with open(path, 'rb') as stream:
                for block in iter(lambda: stream.read(1 << 20), b''):
                    h.update(block)
            out[path.name] = h.hexdigest()
    return out


def install(server: Path, staged: Path, backups: Path, write: bool) -> Path | None:
    navmesh = server / 'navmesh'
    junction = os.path.isjunction(navmesh)
    files = digest(staged)
    print(f'Install {len(files)} files from {staged} into {navmesh} '
          f'(replacing {"the junction to " + os.path.realpath(navmesh) if junction else "a real folder"})')
    if not write:
        print('Preview only. Run again with --apply to install.')
        return None
    check_stopped(server)
    folder = backups / f'navmesh-{datetime.now():%Y%m%d-%H%M%S-%f}'
    folder.mkdir(parents=True)
    record = dict(navmesh=str(navmesh), junction=junction, files=files)
    if junction:
        record['target'] = os.path.realpath(navmesh)
        os.rmdir(navmesh)  # removes the link only; the target folder and its files stay
    elif navmesh.exists():
        shutil.move(str(navmesh), folder / 'navmesh')
    (folder / 'navmesh.json').write_text(json.dumps(record, indent=1), encoding='utf-8')
    shutil.copytree(staged, navmesh)
    (navmesh / MARKER).write_text(f'Installed {datetime.now():%Y-%m-%d %H:%M} from {staged}\n', encoding='utf-8')
    if digest(navmesh) != files:
        raise SystemExit(f'The installed navmesh folder does not match the staged one. Roll back with {folder}.')
    print(f'Installed and verified. Backup record: {folder}')
    return folder


def rollback(server: Path, folder: Path, write: bool):
    record = json.loads((folder / 'navmesh.json').read_text(encoding='utf-8'))
    navmesh = Path(record['navmesh'])
    if os.path.isjunction(navmesh) or not (navmesh / MARKER).exists():
        raise SystemExit(f'{navmesh} is not a folder this tool installed. Nothing was changed.')
    what = f"the junction to {record['target']}" if record['junction'] else 'the moved folder'
    print(f'Rollback: delete the installed {navmesh} and restore {what}')
    if not write:
        print('Preview only. Run again with --apply to roll back.')
        return
    check_stopped(server)
    shutil.rmtree(navmesh)
    if record['junction']:
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(navmesh), record['target']], check=True, capture_output=True)
        if not os.path.isjunction(navmesh):
            raise SystemExit('The junction could not be recreated.')
    else:
        shutil.move(str(folder / 'navmesh'), navmesh)
    print('Rolled back.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    i = sub.add_parser('install'); i.add_argument('server', type=Path); i.add_argument('staged', type=Path)
    i.add_argument('--backups', type=Path, required=True); i.add_argument('--apply', action='store_true')
    r = sub.add_parser('rollback'); r.add_argument('server', type=Path); r.add_argument('backup', type=Path)
    r.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'install':
        install(args.server, args.staged, args.backups, args.apply)
    else:
        rollback(args.server, args.backup, args.apply)


if __name__ == '__main__':
    main()
