"""Build the public modern-test package: this fork's game for the original 1.130 client, without any retail file.

    python build_modern_test_package.py --install <artifacts/modern-client-test> --pristine <pristine 1.130 client>
                                        --repo <this repository> --out <new package folder>
                                        --label "<version> modern test" [--zip]

The install (the developer's modern test, only read) gives the server folder and the world. The package gets:
  * runtime/: the install's server folder (personal, diagnostic and run-state files left out, as build_release_037.py
    does), this repository's Release GameServer and launcher builds, and a clean world (build_release_037.clean_world:
    no account, character, bot or save; default keeps, doors and relics; zero-bot start, GM off, 1x XP, automatic
    account creation). The modern switches (native class slots, modern races, the test classes) stay as installed.
    The world ships as data/world-clean.sqlite3.db, never as data/opendaoc.sqlite3.db: the launcher makes the played
    world from it on first start, so copying a newer release over an older folder can't overwrite anyone's saves.
  * runtime/world-updates: one world update per release (modern_world_updates.py). This release's step, from the
    previous release's clean world (found in release-baselines/modern beside the repository) to this one, is added to
    the repository's chain (source/tools/release-baselines/modern/world-updates; commit it with the release), and this
    clean world is kept there for the next release. The launcher applies the steps a world hasn't had, so a world from
    any earlier release gets this release's fixes and keeps its saves. The version is the label's first word: give
    every published build a new one (building the same label again replaces its step).
  * runtime/client-patch.json (make_client_patch.py, from the pristine client) and modern-client.json: on first start
    the launcher copies the player's own 1.130 client into runtime/client-modern/app and patches the copy.
  * tools/connect-local1130.exe (upstream's connect.exe with its 1.130 edit), tools/dotnet (the .NET runtime), the
    START cmd, READ ME FIRST, the licences and docs.
No retail client file ships (checked), and nothing is started.

Build the server and launcher first without the developer's paths in the binaries (the package check refuses them):
    dotnet build "source/server/Dawn of Light.sln" -c Release --no-incremental -p:PathMap=<repo>=X:\\OfflineDAoC
        -p:Deterministic=true -p:EnableSourceLink=false -p:EnableSourceControlManagerQueries=false
    (and the same for source/tools/OfflineDaoc.Launcher), then python source/tools/world_editor/build_package.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import build_release_037 as release
import make_client_patch
import modern_world_updates
import remove_sluaghbinder

PORT = 10330
CONNECTOR_SHA256 = '18ab2f8a95be682e0f6acbbb6c7332e9ef05f1586872626f63a3122782f6ba70'
CONNECTOR = 'connect-local1130.exe'
# Runtime files of the developer's install that the package writes itself or never ships.
# world-workshop-data holds the developer's editor backups (database snapshots): never shipped. The editor itself
# (world-workshop) is installed from the repository's clean package build instead of the install's copy.
# server-backups holds deploy backups (developer builds), herald the launcher's Herald page written from this game's records.
# world-updates is written from the repository's chain (the install may have an older one).
RUNTIME_SKIP_DIRS = {'client-modern', 'world-workshop', 'world-workshop-data', 'server-backups', 'herald', 'world-updates'}
WORLD_WORKSHOP = 'artifacts/world-workshop-package/WorldWorkshop'
# host-for-friends.json and the firewall script are the developer's Host for Friends state (friends' addresses, local paths).
RUNTIME_SKIP_NAMES = {'modern-client.json', 'modern-profile-verification.json', 'modern-client-setup-error.txt', 'client-patch.json',
                      'host-for-friends.json', 'host-for-friends-firewall.cmd', 'serverconfig.before-host-for-friends.xml'}
LAUNCHER_FILES = ('OfflineDAoC.dll', 'OfflineDAoC.exe', 'OfflineDAoC.pdb', 'OfflineDAoC.deps.json', 'OfflineDAoC.runtimeconfig.json',
                  'Join Friend.cmd')
TEXT_SUFFIXES = {'.json', '.xml', '.txt', '.md', '.cmd', '.config', '.ini', '.csv'}
# Items whose look needs private client art the client patch can't add yet: the developer's world sells them, the
# package's world doesn't. mount_67 rides mount 89, the saddled Chimera (tools/horses/install_chimera_mount.py adds it
# to gamedata.mpk and figures/, neither of which client-patch.json patches).
WITHHELD_MERCHANT_ITEMS = ('mount_67',)

START_CMD = r'''@echo off
setlocal
cd /d "%~dp0"
rem Divided Realms {label} (the original 1.130 client). Uses the .NET runtime bundled in tools\dotnet, so nothing has to
rem be installed except the Windows .NET Framework 3.5 feature (for the client's connector).
if not exist "%~dp0runtime\OfflineDAoC.exe" (
  echo This folder is incomplete. Extract the whole download again, then retry.
  pause
  exit /b 1
)
set "DOTNET_ROOT=%~dp0tools\dotnet"
set "DOTNET_ROOT_X64=%~dp0tools\dotnet"
set "DOTNET_MULTILEVEL_LOOKUP=0"
start "" "%~dp0runtime\OfflineDAoC.exe"
'''

# Join a friend's world without the launcher's dashboard or this folder's server (docs/PLAY-WITH-FRIENDS.md).
JOIN_CMD = r'''@echo off
setlocal
cd /d "%~dp0"
rem Divided Realms {label}: play in a friend's world. Starts only the game client, never this folder's server or save.
if not exist "%~dp0runtime\OfflineDAoC.exe" (
  echo This folder is incomplete. Extract the whole download again, then retry.
  pause
  exit /b 1
)
set "DOTNET_ROOT=%~dp0tools\dotnet"
set "DOTNET_ROOT_X64=%~dp0tools\dotnet"
set "DOTNET_MULTILEVEL_LOOKUP=0"
start "" "%~dp0runtime\OfflineDAoC.exe" --join
'''

READ_ME = '''Divided Realms {label}
{rule}

A single-player Dark Age of Camelot server with gamebots, for the ORIGINAL retail 1.130 client.
This download contains no game client: you use your own.

1. You need Dark Age of Camelot installed (the 1.130 client), and the Windows feature
   ".NET Framework 3.5" turned on (Control Panel > Programs > Turn Windows features on or off).
2. Extract this whole folder somewhere with about 7 GB free.
3. Double-click START DIVIDED REALMS.cmd.
4. On first start the launcher asks for your Dark Age of Camelot folder (the one with game.dll
   and camelot.exe). It copies it into this folder and patches the copy. Your own install is
   not changed. It only accepts the 1.130 client this game is made for.
5. START SERVER, then ENTER REALM. Your account is created on the first login.

Playing with friends: one of you hosts (HOST FOR FRIENDS in the launcher), the others double-click
JOIN FRIEND.cmd (set up your client once with step 4 first). See docs/PLAY-WITH-FRIENDS.md.

Updating from an earlier test build: close the launcher, extract the new download over this
folder and choose to replace every file. Your world and characters are kept: the launcher adds
the new build's world fixes to your world (after a backup in runtime\\backups) and patches your
client copy again (it may ask for your Dark Age of Camelot folder once).

This is a development test build. See docs/PLAY-MODERN-TEST.md and docs/PROGRESS-2026-10.md.
'''


def sha(path: Path) -> str:
    return release.sha(path)


def keep_runtime(relative: Path) -> bool:
    if relative.parts[0] in RUNTIME_SKIP_DIRS or relative.name in RUNTIME_SKIP_NAMES:
        return False
    return release.include(relative)


def latest_dotnet(dotnet: Path) -> str:
    """The newest .NET 10 present for all four bundled parts."""
    parts = ['host/fxr', 'shared/Microsoft.NETCore.App', 'shared/Microsoft.WindowsDesktop.App', 'shared/Microsoft.AspNetCore.App']
    common = set.intersection(*({p.name for p in (dotnet / part).iterdir() if p.name.startswith('10.')} for part in parts))
    if not common:
        raise SystemExit('No .NET 10 runtime with all four parts is installed')
    return max(common, key=lambda v: tuple(int(x) for x in v.split('.')))


def server_config(config: Path):
    """The package's world, relative to the server folder (as the classic packages), automatic account creation, and
    Host for Friends off (loopback, no UPnP, no PublicIP) whatever the developer's install has switched on."""
    text = config.read_text(encoding='utf-8-sig')
    text, count = re.subn(r'Data Source=[^;<]*', 'Data Source=../data/opendaoc.sqlite3.db', text)
    assert count == 1, 'serverconfig.xml has no single Data Source'
    for tag, value in (('IP', '127.0.0.1'), ('UdpIP', '127.0.0.1'), ('EnableUPnP', 'False')):
        text = re.sub(rf'<{tag}>[^<]*</{tag}>', f'<{tag}>{value}</{tag}>', text)
    text = re.sub(r'[ \t]*<PublicIP>[^<]*</PublicIP>\r?\n?', '', text)
    config.write_text(text, encoding='utf-8')
    release.set_auto_account_creation(config)
    assert f'<Port>{PORT}</Port>' in text and '<IP>127.0.0.1</IP>' in text, 'the modern server must listen on loopback 10330'


def PATH_NEEDLES(user):
    """The user name as a path folder (backslash or slash on both sides), in UTF-8 and UTF-16: not the bare word, which also turns
    up inside unrelated data (a compression dictionary holds "buenatexto")."""
    forms = [f'{sep}{user}{sep}' for sep in ('\\', '/')]
    return [f.encode(enc) for f in forms for enc in ('utf-8', 'utf-16-le')]


def check_package(out: Path, pristine: Path):
    """Nothing personal, diagnostic or retail ships."""
    runtime = out / 'runtime'
    bad = [p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and (
        p.name.lower() in release.FORBIDDEN_NAMES or p.name.lower().endswith(release.FORBIDDEN_SUFFIXES))]
    bad = [b for b in bad if not b.startswith('tools/dotnet/')]
    assert not bad, f'files that must not ship: {bad[:20]}'
    assert not (runtime / 'client-modern').exists(), 'a client folder would ship'
    for name in ('server/GameServer.dll', 'server/CoreServer.exe', 'server/navmesh/roads.json', 'data/world-clean.sqlite3.db',
                 'world-updates/world-updates.json', 'OfflineDAoC.exe', 'client-patch.json', 'modern-client.json'):
        assert (runtime / name).is_file(), f'required file missing: {name}'
    assert not (runtime / 'data/opendaoc.sqlite3.db').exists(), 'a played-world file would ship and overwrite saves when copied over'
    retail = {sha(pristine / name) for name in ('game.dll', 'camelot.exe', 'pregame/character_creation.xml')}
    shipped = [p for p in out.rglob('*') if p.is_file() and p.stat().st_size in {(pristine / n).stat().st_size for n in
               ('game.dll', 'camelot.exe', 'pregame/character_creation.xml')}]
    assert not [p for p in shipped if sha(p) in retail], 'a retail client file would ship'
    personal = re.compile(r'C:\\Users\\|C:/Users/|natex', re.I)
    leaks = [p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES
             and p.stat().st_size < 8 << 20 and not p.relative_to(out).as_posix().startswith('tools/dotnet/')
             and personal.search(p.read_text(encoding='utf-8', errors='ignore'))]
    assert not leaks, f'files naming the developer\'s machine: {leaks[:20]}'
    # Binaries too (a developer build embeds its PDB and source paths): the user name must not appear in them.
    user = Path.home().name
    binary = [p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and p.stat().st_size < 64 << 20
              and p.suffix.lower() in ('.dll', '.exe', '.pdb', '.json', '.db')
              and not p.relative_to(out).as_posix().startswith('tools/dotnet/')
              and any(n in p.read_bytes() for n in PATH_NEEDLES(user))]
    assert not binary, f'binaries naming the developer: {binary[:20]}'


def build(install: Path, pristine: Path, repo: Path, out: Path, label: str) -> dict:
    if out.exists():
        raise SystemExit(f'{out} exists; refusing to overwrite a package folder')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', PORT)) == 0:
            raise SystemExit('Close the modern test server first')
    server_build = repo / 'source/server/Release/lib'
    launcher_build = repo / 'source/tools/OfflineDaoc.Launcher/bin/Release/net10.0-windows'
    for path in [server_build / 'GameServer.dll'] + [launcher_build / n for n in LAUNCHER_FILES]:
        if not path.is_file():
            raise SystemExit(f'Build the Release server and launcher first: {path} is missing')
    if not (repo / WORLD_WORKSHOP / 'WorldWorkshop.exe').is_file():
        raise SystemExit('Build World Workshop first: python source/tools/world_editor/build_package.py')
    connector = install / 'tools' / CONNECTOR
    if sha(connector) != CONNECTOR_SHA256:
        raise SystemExit('The install\'s 1.130 connector is not the expected one')
    chain = repo / 'source/tools/release-baselines/modern/world-updates'
    release_version = label.split()[0]
    previous = modern_world_updates.previous_release(chain, release_version)
    previous_world = modern_world_updates.baseline(previous)
    installed_profile = json.loads((install / 'runtime/modern-client.json').read_text(encoding='utf-8-sig'))
    policy = json.loads((repo / 'source/tools/OfflineDaoc.ProgressImport/progress-policy.json').read_text())
    defaults = json.loads((repo / 'source/tools/release-world-defaults.json').read_text(encoding='utf-8'))

    print('Making the client patch from the pristine client...', flush=True)
    patch = make_client_patch.build(pristine)
    game = next(f for f in patch['Files'] if f['Path'] == 'game.dll')
    if game['OutputSha256'].lower() != installed_profile['GameSha256'].lower():
        raise SystemExit('The client patch does not rebuild the client the test install runs')

    print('Copying the runtime (personal, diagnostic, run-state and client files left out)...', flush=True)
    runtime = out / 'runtime'
    copied = release.copy_tree(install / 'runtime', runtime, keep_runtime)

    print('Building the clean world...', flush=True)
    database = runtime / 'data/opendaoc.sqlite3.db'
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect((install / 'runtime/data/opendaoc.sqlite3.db').as_uri() + '?mode=ro', uri=True) as src, \
            sqlite3.connect(database) as dst:
        src.backup(dst)
    src.close()
    dst.close()
    world = release.clean_world(database, policy, defaults)
    with sqlite3.connect(database) as con:
        # clean_world switches upstream's Sluaghbinder on; this fork has retired it (build_custom_release_037.py).
        release.set_edition(con, False)
        sluaghbinder = remove_sluaghbinder.apply(con)
        withheld = {item: con.execute('DELETE FROM MerchantItem WHERE ItemTemplateID = ?', (item,)).rowcount
                    for item in WITHHELD_MERCHANT_ITEMS}
        con.commit()
        world = release.verify_clean(con, policy, defaults)
    con.close()     # the world file is renamed below
    world_data = release.check_world_data(database, repo)

    print("Adding this release's world update...", flush=True)
    world_update = modern_world_updates.add_step(chain, release_version, previous, previous_world, database)
    modern_world_updates.stamp(database, chain)
    modern_world_updates.install(chain, runtime)
    database.rename(runtime / 'data' / modern_world_updates.CLEAN_WORLD)

    server_config(runtime / 'server/config/serverconfig.xml')

    print('Installing the Release server and launcher builds...', flush=True)
    replaced = {}
    # Every server assembly this repository builds, not only GameServer: the install's older Core* copies were built
    # with the developer's paths (0.38-dev2 shipped them). Build with PathMap and SourceLink off (see the docstring).
    for folder in ('server', 'server/lib', 'server/win-x64'):
        for name in [f'{a}.{e}' for a in ('CoreBase', 'CoreDatabase', 'CoreServer', 'GameServer') for e in ('dll', 'pdb')]:
            target = runtime / folder / name
            source = server_build / name if (server_build / name).is_file() else server_build.parent / name
            if target.exists() and source.is_file():
                shutil.copy2(source, target)
                replaced[f'{folder}/{name}'] = sha(target)
    for name in LAUNCHER_FILES:
        shutil.copy2(launcher_build / name, runtime / name)
        replaced[name] = sha(runtime / name)

    # World Workshop for the launcher's WORLD EDITOR button (runtime/world-workshop; it keeps its state beside it).
    shutil.copytree(repo / WORLD_WORKSHOP, runtime / 'world-workshop')
    replaced['world-workshop/WorldWorkshop.exe'] = sha(runtime / 'world-workshop/WorldWorkshop.exe')

    (runtime / 'client-patch.json').write_text(json.dumps(patch, indent=1), encoding='utf-8')
    profile = dict(ClientDirectory='client-modern/app', ConnectorPath='..\\tools\\' + CONNECTOR,
                   GameSha256=game['OutputSha256'].upper(), ConnectorSha256=CONNECTOR_SHA256.upper(), Port=PORT)
    (runtime / 'modern-client.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')
    (out / 'tools').mkdir(parents=True, exist_ok=True)
    shutil.copy2(connector, out / 'tools' / CONNECTOR)

    print('Bundling the .NET runtime...', flush=True)
    dotnet = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'dotnet'
    version = latest_dotnet(dotnet)
    for sub in (f'host/fxr/{version}', f'shared/Microsoft.NETCore.App/{version}', f'shared/Microsoft.WindowsDesktop.App/{version}',
                f'shared/Microsoft.AspNetCore.App/{version}'):
        release.copy_tree(dotnet / sub, out / 'tools/dotnet' / sub)
    for name in ('dotnet.exe', 'LICENSE.txt', 'ThirdPartyNotices.txt'):
        if (dotnet / name).exists():
            shutil.copy2(dotnet / name, out / 'tools/dotnet' / name)

    print('Writing the start file, read-me, licences and docs...', flush=True)
    (out / 'START DIVIDED REALMS.cmd').write_text(START_CMD.format(label=label).replace('\n', '\r\n'), encoding='ascii')
    (out / 'JOIN FRIEND.cmd').write_text(JOIN_CMD.format(label=label).replace('\n', '\r\n'), encoding='ascii')
    title = f'Divided Realms {label}'
    (out / 'READ ME FIRST.txt').write_text(READ_ME.format(label=label, rule='=' * len(title)).replace('\n', '\r\n'), encoding='utf-8')
    (out / 'EDITION.txt').write_text(f'{title}: the original 1.130 client (bring your own), modern test classes.\r\n', encoding='utf-8')
    for name in ('LICENSE', 'THIRD_PARTY.md'):
        shutil.copy2(repo / name, out / name)
    # Only the docs the repository tracks: the developer's local hand-off and research notes never ship.
    tracked = set(subprocess.run(['git', '-C', str(repo), 'ls-files', 'docs'], capture_output=True, text=True, check=True).stdout.split())
    release.copy_tree(repo / 'docs', out / 'docs', lambda rel: rel.parts[0] != 'history' and rel.suffix.lower() == '.md'
                      and ('docs/' + rel.as_posix()) in tracked)

    check_package(out, pristine)
    modern_world_updates.keep_baseline(release_version, runtime / 'data' / modern_world_updates.CLEAN_WORLD)
    files = {p.relative_to(out).as_posix(): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out / 'PACKAGE MANIFEST.sha256').write_text(''.join(f'{h}  {n}\n' for n, h in files.items()), encoding='utf-8')
    report = dict(built_utc=datetime.now(timezone.utc).isoformat(), label=label, runtime_files_copied=len(copied),
                  world=world, world_data=world_data, world_update={f'{previous} -> {release_version}': world_update}, sluaghbinder=sluaghbinder, withheld_merchant_items=withheld, replaced=replaced, dotnet=version,
                  client_patch={f['Path']: [f['InputSha256'], f['OutputSha256']] for f in patch['Files']}, files=len(files))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--pristine', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--label', default='0.38-dev modern test')
    parser.add_argument('--zip', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    report = build(args.install.resolve(), args.pristine.resolve(), args.repo.resolve(), out, args.label)
    (out.parent / (out.name + '-build-report.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.zip:
        print('Zipping...', flush=True)
        archive = shutil.make_archive(str(out), 'zip', out.parent, out.name)
        report['zip'] = dict(path=archive, sha256=sha(Path(archive)), bytes=Path(archive).stat().st_size)
        (out.parent / (out.name + '-build-report.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('replaced',)}, indent=2)[:3000])
