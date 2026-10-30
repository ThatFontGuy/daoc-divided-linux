"""World Workshop entry point for the packaged program (standalone download and the launcher's WORLD EDITOR button).

    WorldWorkshop.exe                      opens the game this copy sits in (<game>/runtime/world-workshop), else the
                                           last game used, else asks for an Offline DAoC folder
    WorldWorkshop.exe --game PATH          an Offline DAoC game folder (or its runtime folder)
    WorldWorkshop.exe --worker NAME ...    internal: the preview / custom-look workers run in this same program

Saved state (backups, previews, caches) goes to <game>/runtime/world-workshop-data unless --state is given.
The workspace's own START WORLD EDITOR.cmd keeps using launch.py.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, 'frozen', False)
PROGRAM = Path(sys.executable if FROZEN else __file__).resolve().parent
SETTINGS = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'WorldWorkshop' / 'settings.json'


def runtime_of(path):
    """An Offline DAoC game folder or its runtime folder -> (runtime, database, client), or None."""
    path = Path(path).resolve()
    for runtime in (path / 'runtime', path):
        db = runtime / 'data' / 'opendaoc.sqlite3.db'
        if not db.is_file():
            continue
        # The modern test package names its client in modern-client.json; the playable games use client-opendaoc.
        profile = runtime / 'modern-client.json'
        candidates = []
        if profile.is_file():
            try:
                candidates.append(runtime / json.loads(profile.read_text(encoding='utf-8-sig'))['ClientDirectory'])
            except (OSError, ValueError, KeyError):
                pass
        candidates.append(runtime / 'client-opendaoc' / 'app')
        client = next((c.resolve() for c in candidates if (c / 'zones' / 'zones.mpk').is_file()), None)
        if client:
            return runtime, db, client
    return None


def remembered():
    try:
        return json.loads(SETTINGS.read_text(encoding='utf-8')).get('game')
    except (OSError, ValueError):
        return None


def remember(game):
    try:
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text(json.dumps({'game': str(game)}), encoding='utf-8')
    except OSError:
        pass


def ask_for_game():
    """Folder picker until the player chooses an Offline DAoC game folder (or cancels)."""
    import tkinter
    from tkinter import filedialog, messagebox
    root = tkinter.Tk()
    root.withdraw()
    while True:
        folder = filedialog.askdirectory(title='Choose your Offline DAoC game folder (the one with START OFFLINE DAOC.cmd)')
        if not folder:
            return None
        if runtime_of(folder):
            return folder
        messagebox.showwarning('World Workshop', 'That folder has no runtime\\data\\opendaoc.sqlite3.db and game client.\n'
                                                 'Choose the Offline DAoC folder you play from.')


def run_worker(name, argv):
    from world_editor import asset_worker, visual_worker
    module = {'asset_worker': asset_worker, 'visual_worker': visual_worker}[name]
    sys.argv = [f'{name}.py', *argv]
    module.main()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['--worker']:
        return run_worker(argv[1], argv[2:])
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--game', type=Path, help='Offline DAoC game folder or its runtime folder')
    parser.add_argument('--state', type=Path)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    game = args.game
    if game is None and runtime_of(PROGRAM.parent):          # installed at <game>/runtime/world-workshop
        game = PROGRAM.parent
    if game is None and remembered() and runtime_of(remembered()):
        game = Path(remembered())
    if game is None:
        game = ask_for_game()
        if game is None:
            return 1
    found = runtime_of(game)
    if not found:
        raise SystemExit(f'{game} is not an Offline DAoC game folder (no runtime/data/opendaoc.sqlite3.db and client).')
    runtime, db, client = found
    remember(runtime.parent)
    # The collision exporter is a .NET 10 program: every Offline DAoC game ships that runtime in tools/dotnet.
    dotnet = runtime.parent / 'tools' / 'dotnet'
    if 'DOTNET_ROOT' not in os.environ and (dotnet / 'dotnet.exe').is_file():
        os.environ['DOTNET_ROOT'] = str(dotnet)
    from world_editor import editor
    exporter = PROGRAM / 'buildnav' / 'OpenDAoC-BuildNav.exe'
    forwarded = ['--db', str(db), '--client', str(client), '--state', str(args.state or runtime / 'world-workshop-data'),
                 '--port', str(args.port)]
    if exporter.is_file():
        forwarded += ['--exporter', str(exporter)]
    if args.no_browser:
        forwarded.append('--no-browser')
    print(f'\n  WORLD WORKSHOP\n  Game: {runtime.parent}\n  Client: {client}\n')
    editor.main(forwarded)
    return 0


if __name__ == '__main__':
    if not FROZEN:
        sys.path.insert(0, str(PROGRAM.parent))
    sys.exit(main())
