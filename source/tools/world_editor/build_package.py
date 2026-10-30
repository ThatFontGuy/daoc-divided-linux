"""Build the World Workshop Windows package: one folder that needs no Python, for the standalone download and for the
launcher's WORLD EDITOR button (<game>/runtime/world-workshop).

    python build_package.py [--out DIR] [--no-buildnav] [--zip]

Run with a Python 3.12 that has NumPy, Pillow and PyInstaller (set PYTHONPATH to a folder holding PyInstaller if it is
not installed). Output: <out>/WorldWorkshop/WorldWorkshop.exe (+ WorldWorkshop-<version>.zip with --zip).
Contents: the editor, its workers and the repository modules they use (new-client pipeline readers, the MPK codec,
modern_world_overlay), Three.js (MIT), an item-name snapshot of the server enums, and optionally the BuildNav
collision exporter (win-x64 natives only). No game files, databases, caches or backups are included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parents[1]
PIPELINE = REPO / 'source/new-client/pipeline'
ASSET_TOOL = REPO / 'tools/asset-tool'
ENUMS = REPO / 'source/server/GameServer/Enums'
BUILDNAV_PROJECT = REPO / 'source/development-tools/OpenDAoC-BuildNav/OpenDAoC-BuildNav.csproj'
VERSION = '1.0.0'
HIDDEN = ['world_editor.editor', 'world_editor.asset_worker', 'world_editor.visual_worker', 'modern_world_overlay',
          'daoc_mpk', 'nif_static', 'nif_character', 'netimmerse', 'build_zone', 'build_races', 'texture_index', 'archive',
          'assets_pipeline', 'tkinter', 'tkinter.filedialog', 'tkinter.messagebox']


def enum_snapshot():
    """The names the Items view shows (object types, bonus properties, damage types, realms, classes, crafting skills)."""
    out = {}
    for key, file in (('objectType', 'eObjectType.cs'), ('property', 'eProperty.cs'), ('damageType', 'eDamageType.cs'),
                      ('realm', 'eRealm.cs'), ('characterClass', 'eCharacterClass.cs'), ('craftingSkill', '../craft/CraftingMgr.cs')):
        names = {}
        path = (ENUMS / file).resolve()
        for name, number in re.findall(r'^\s*(\w+)\s*=\s*(\d+)\s*,?', path.read_text(encoding='utf-8-sig'), re.M):
            if not name.startswith('_') and not name.endswith(('_First', '_Last')) and number not in names:
                names[number] = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name).replace('_', ' ')
        out[key] = names
    out['itemType'] = {'10': 'Right hand', '11': 'Left hand', '12': 'Two-handed', '13': 'Ranged', '21': 'Helm',
                       '22': 'Gloves', '23': 'Boots', '24': 'Jewel', '25': 'Torso', '26': 'Cloak', '27': 'Legs',
                       '28': 'Arms', '29': 'Neck', '32': 'Belt', '33': 'Bracer', '35': 'Ring', '37': 'Mythical',
                       '0': 'Not equipped'}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=REPO / 'artifacts/world-workshop-package')
    ap.add_argument('--no-buildnav', action='store_true')
    ap.add_argument('--zip', action='store_true')
    args = ap.parse_args()
    import PyInstaller.__main__ as pyinstaller   # noqa: E402 (needs PyInstaller in this Python)
    for module in ('numpy', 'PIL'):
        __import__(module)
    out = args.out.resolve()
    dist = out / 'WorldWorkshop'
    if dist.exists():
        shutil.rmtree(dist)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / 'enums.json').write_text(json.dumps(enum_snapshot()), encoding='utf-8')
        sep = ';'
        pyinstaller.run([
            str(HERE / 'app.py'), '--name', 'WorldWorkshop', '--onedir', '--console', '--noconfirm', '--clean',
            '--distpath', str(out), '--workpath', str(tmp / 'build'), '--specpath', str(tmp),
            '--paths', str(TOOLS), '--paths', str(PIPELINE), '--paths', str(ASSET_TOOL),
            '--add-data', f'{HERE / "static"}{sep}world_editor/static',
            '--add-data', f'{tmp / "enums.json"}{sep}world_editor',
            '--add-data', f'{PIPELINE / "spec"}{sep}spec',
            '--exclude-module', 'scipy', '--exclude-module', 'matplotlib', '--exclude-module', 'pyffi',
            *[x for name in HIDDEN for x in ('--hidden-import', name)],
        ])
    if not args.no_buildnav:
        # A fresh build without debug symbols or source paths: a copy of a developer's bin folder embeds the PDB path
        # (the builder's Windows user and folders) in each DLL.
        with tempfile.TemporaryDirectory() as tmp:
            built = Path(tmp) / 'buildnav'
            subprocess.run(['dotnet', 'build', str(BUILDNAV_PROJECT), '-c', 'Release', '-o', str(built), '--nologo', '--no-incremental',
                            '-p:DebugType=None', '-p:DebugSymbols=false', '-p:Deterministic=true',
                            '-p:ContinuousIntegrationBuild=true'], check=True)
            shutil.copytree(built, dist / 'buildnav', ignore=shutil.ignore_patterns('*.pdb', 'win-x86', 'win-arm64', 'linux-*', 'osx*'))
    private = [p for p in dist.rglob('*') if p.is_file() and any(n in p.read_bytes() for n in (str(Path.home()).encode(),
                                                                                                  str(REPO).encode()))]
    if private:
        raise SystemExit('Local paths found in the package: ' + ', '.join(str(p.relative_to(dist)) for p in private))
    shutil.copy2(REPO / 'LICENSE', dist / 'LICENSE.txt')
    shutil.copy2(HERE / 'static/vendor/LICENSE-three.txt', dist / 'LICENSE-three.js.txt')
    (dist / 'README.txt').write_text(README.format(version=VERSION), encoding='utf-8')
    (dist / 'VERSION.txt').write_text(f'World Workshop {VERSION}, built {date.today().isoformat()}\n', encoding='utf-8')
    files = sorted(p for p in dist.rglob('*') if p.is_file())
    manifest = '\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(dist).as_posix()}' for p in files)
    (dist / 'MANIFEST.sha256').write_text(manifest + '\n', encoding='utf-8')
    size = sum(p.stat().st_size for p in files)
    print(f'Built {dist} ({len(files)} files, {size / 1e6:.0f} MB)')
    if args.zip:
        archive = out / f'WorldWorkshop-{VERSION}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in sorted(dist.rglob('*')):
                if p.is_file():
                    z.write(p, Path('WorldWorkshop') / p.relative_to(dist))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (out / f'{archive.name}.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
        print(f'Zipped {archive} ({archive.stat().st_size / 1e6:.0f} MB) sha256 {digest}')


README = """World Workshop {version} - a world, item and data editor for Offline DAoC
=====================================================================

Run WorldWorkshop.exe. The first time, choose your Offline DAoC game folder (the one with START OFFLINE DAOC.cmd);
the editor finds its database and game client and remembers the folder. It opens in your web browser at
http://127.0.0.1 (nothing is reachable from other computers). Keep the console window open while you edit.

  3D world      move, add, copy and delete NPCs, objects, doors, zone/bind points, teleports, keeps, NPC walk paths
  Items         every server item and every item appearance in your client, previewed in 3D on a character
                (armour, cloaks, helms, weapon effects); edit stats; create items from unused client art
  Merchants     build merchant lists; pay with coins (or any item, if your server has GameCustomCurrencyMerchant)
  Game data     search and edit NPC templates, loot, spells, quests, server properties and more
  Server files  edit server settings / bot JSON files, with backups
  Custom looks  give NPCs new looks from your own textures

Close the game and the server before saving. Every save keeps a database backup and can be undone
(Restore edits). Backups, previews and caches are stored in <game>\\runtime\\world-workshop-data.
Restart the server to load saved changes.

Other options:  WorldWorkshop.exe --game "D:\\Offline DAoC"     choose the game folder
Collision geometry (exact floors in buildings) uses the bundled exporter and the .NET 10 runtime in your game's
tools\\dotnet folder; without it the editor uses terrain heights.

Licence: GPL v3 (LICENSE.txt). Three.js is MIT (LICENSE-three.js.txt). No game files are included: everything shown
is read from your own installed client.
"""


if __name__ == '__main__':
    main()
