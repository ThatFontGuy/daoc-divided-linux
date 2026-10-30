"""Preview/apply the live class updates to the selected modern test world: the hybrid-line spells and class abilities
(hybrid_lines.py), the other classes' live spells (class_lines.py), live archery (archery.py), class proc buffs
(proc_lines.py), totems and other linked spells (linked_lines.py), the assassins' live poisons (envenom_lines.py), the next ten classes' spells (round3_lines.py), the client's own spell art (live_spell_art.py), Codex's audit corrections (audit_corrections.py), live damage-over-time timing (dot_timing.py), live values for existing spells (spell_drift.py) and
the removal of the retired Sluaghbinder (remove_sluaghbinder.py).
Installs the seeded world and the Release GameServer.dll (class abilities need their handlers), with backups and rollback.
Never starts or stops game processes.
"""
import argparse
from contextlib import closing
import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import archery
import audit_corrections
import class_lines
import dot_timing
import envenom_lines
import hybrid_lines
import live_spell_art
import linked_lines
import proc_lines
import remove_sluaghbinder
import round3_lines
import spell_drift
sys.path.insert(0, str(Path(__file__).resolve().parent / 'sovereign'))
from install_instant_decrees import REPO, sha, progress, stopped

DATABASE = 'runtime/data/opendaoc.sqlite3.db'
SERVER_DIRS = ('runtime/server', 'runtime/server/lib', 'runtime/server/win-x64')


def install(root, apply=False, rollback=None, build_dir=None):
    root = root.resolve(strict=True)
    if root != (REPO / 'artifacts/modern-client-test').resolve():
        raise ValueError('Only the selected modern test installation is supported')

    def target(rel):
        path = (root / rel).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError('Path leaves the selected installation')
        return path

    if rollback:
        stopped(root)
        saved = rollback.resolve(strict=True)
        if not saved.is_relative_to(root / 'backups'):
            raise ValueError('Backup must be inside the selected installation')
        record = json.loads((saved / 'manifest.json').read_text())
        for row in record['files']:
            if sha(target(row['path'])) != row['installed_sha256']:
                raise ValueError('Files changed since installation; preserve newer progress and recover manually')
        for row in record['files']:
            shutil.copy2(saved / row['backup'], target(row['path']))
        return dict(rolled_back=True, backup=str(saved))

    database = target(DATABASE)
    build = (build_dir or REPO / 'source/server/Release/lib') / 'GameServer.dll'
    if not build.is_file():
        raise ValueError('Build the Release server first')
    if apply:
        stopped(root)
    with tempfile.TemporaryDirectory(prefix='hybrid-lines-', dir=REPO / 'artifacts') as folder:
        world = Path(folder) / 'world.db'
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as source, closing(sqlite3.connect(world)) as dest:
            source.backup(dest)
        with closing(sqlite3.connect(world)) as db, db:
            before = progress(db)
            summary = dict(remove_sluaghbinder.apply(db), **hybrid_lines.apply(db), **class_lines.apply(db), **archery.apply(db), **proc_lines.apply(db), **linked_lines.apply(db),
                           **envenom_lines.apply(db), **round3_lines.apply(db),
                           **spell_drift.apply(db), **audit_corrections.apply(db), **dot_timing.apply(db),
                           **live_spell_art.apply(db))
            if progress(db) != before:
                raise ValueError('Migration changed saved progress')
            if db.execute('pragma quick_check').fetchone()[0] != 'ok':
                raise ValueError('World integrity failed')
        files = [(DATABASE, world)] + [(d + '/GameServer.dll', build) for d in SERVER_DIRS]
        files += [(d + '/GameServer.pdb', build.with_suffix('.pdb')) for d in SERVER_DIRS if (root / d / 'GameServer.pdb').exists()]
        result = dict(preview=not apply, installation=str(root), progress_tables_verified=len(before), server_sha256=sha(build), **summary)
        if not apply:
            return result
        stopped(root)
        with closing(sqlite3.connect(database)) as live:
            if live.execute('pragma wal_checkpoint(TRUNCATE)').fetchone()[0] != 0:
                raise ValueError('Database busy; close the server')
            if progress(live) != before:
                raise ValueError('Saved progress changed during preparation')
        saved = root / 'backups' / ('hybrid-lines-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        saved.mkdir()
        record = dict(installation=str(root), files=[])
        for index, (rel, src) in enumerate(files):
            backup = f'{index}-{Path(rel).name}'
            shutil.copy2(target(rel), saved / backup)
            record['files'].append(dict(path=rel, backup=backup, original_sha256=sha(saved / backup), installed_sha256=sha(src)))
        (saved / 'manifest.json').write_text(json.dumps(record, indent=2))
        try:
            for rel, src in files:
                shutil.copy2(src, target(rel))
            for row in record['files']:
                if sha(target(row['path'])) != row['installed_sha256']:
                    raise ValueError('Installed hash mismatch')
        except BaseException:
            for row in record['files']:
                shutil.copy2(saved / row['backup'], target(row['path']))
            raise
        return dict(result, verified=True, backup=str(saved))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('game', type=Path); p.add_argument('--apply', action='store_true'); p.add_argument('--rollback', type=Path)
    p.add_argument('--build-dir', type=Path)
    a = p.parse_args()
    if a.apply and a.rollback:
        p.error('Choose apply or rollback')
    print(json.dumps(install(a.game, a.apply, a.rollback, a.build_dir), indent=2))
