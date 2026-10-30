"""Bundle a private modern client into the existing test installation.

Copies assets, patches only the copy, verifies every copied file, then switches
the launcher profile. Existing accounts/database are never read or changed.
This is local staging, not a sanitized public release builder.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
from stormforged.patch_modern_client import patch, SUPPORTED


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bundle(source, install):
    source, install = source.resolve(), install.resolve()
    runtime = install/'runtime'
    profile_path = runtime/'modern-client.json'
    profile = json.loads(profile_path.read_text(encoding='utf-8-sig'))
    target = runtime/'client-modern'/'app'
    if target.exists() or source == target or source in target.parents or target in source.parents:
        raise ValueError('Destination exists or overlaps source; refusing to overwrite')
    with socket.socket() as check:
        if check.connect_ex(('127.0.0.1', profile['Port'])) == 0:
            raise ValueError('Close the modern test server before bundling')
    original = (source/'game.dll').read_bytes()
    patched = patch(original)
    connector = Path(profile['ConnectorPath'])
    if not connector.is_absolute():
        connector = runtime/connector
    if digest(connector).lower() != profile['ConnectorSha256'].lower():
        raise ValueError('Connector hash mismatch')
    target.mkdir(parents=True)
    excluded_dirs = {'logs', 'screenshots', 'backups', 'cache'}
    excluded_names = {'game.laa.dll', 'user.dat', 'login.dat', 'account.txt', 'd3d9.dll', 'dxvk.conf', 'dev_mode.txt'}
    manifest = {}
    for directory, dirs, files in os.walk(source, followlinks=False):
        parent = Path(directory)
        dirs[:] = [n for n in dirs if n.lower() not in excluded_dirs and not (parent/n).is_symlink()]
        for name in files:
            path = parent/name
            if path.is_symlink() or name.lower() in excluded_names or path.suffix.lower() in {'.log', '.bak', '.dmp'}:
                continue
            relative = path.relative_to(source)
            dest = target/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if relative.as_posix().lower() == 'game.dll':
                dest.write_bytes(patched)
            else:
                before = digest(path)
                shutil.copy2(path, dest)
                if digest(dest) != before:
                    raise ValueError(f'Copy verification failed: {relative}')
            manifest[relative.as_posix()] = digest(dest)
    report = {
        'client_version': '1.130', 'custom_classes': ['Stormforged'],
        'original_game_sha256': SUPPORTED, 'patched_game_sha256': digest(target/'game.dll'),
        'races': ['Norseman', 'Troll', 'Dwarf', 'Kobold', 'Valkyn', 'Frostalf', 'Deifrang'],
        'files': manifest, 'server_started': False, 'gameplay_verified': False,
    }
    (install/'bundled-modern-client.json').write_text(json.dumps(report, indent=2))
    # Keep the pristine bytes for future deterministic patches and rollback.
    backup = install/'backups'/('client-bundle-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True)
    shutil.copy2(profile_path, backup/'modern-client.json')
    (backup/'game.original.dll').write_bytes(original)
    profile['ClientDirectory'] = 'client-modern/app'
    profile['ConnectorPath'] = os.path.relpath(connector, runtime)
    profile['GameSha256'] = report['patched_game_sha256'].upper()
    pending = profile_path.with_suffix('.json.tmp')
    pending.write_text(json.dumps(profile, indent=2))
    pending.replace(profile_path)
    print(f'Bundled and hash-verified {len(manifest)} files at {target}')
    print(f'Previous profile and pristine binary: {backup}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('client', type=Path)
    parser.add_argument('install', type=Path)
    args = parser.parse_args()
    bundle(args.client, args.install)
