"""Preview/apply Eve of Darkness expansion trainers to the selected modern test world, with backups and rollback."""
import argparse
from contextlib import closing
import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from import_expansion_trainers import apply as migrate
sys.path.insert(0,str(Path(__file__).resolve().parent/'sovereign'))
from install_instant_decrees import REPO,sha,progress,stopped

def install(root,apply=False,rollback=None):
 root=root.resolve(strict=True)
 if root!=(REPO/'artifacts/modern-client-test').resolve():raise ValueError('Only the selected modern test installation is supported')
 def target(rel):
  p=(root/rel).resolve(strict=True)
  if not p.is_relative_to(root):raise ValueError('Path leaves selected installation')
  return p
 if rollback:
  stopped(root);saved=rollback.resolve(strict=True)
  if not saved.is_relative_to(root/'backups'):raise ValueError('Backup must be inside selected installation')
  record=json.loads((saved/'manifest.json').read_text())
  if record['installation']!=str(root):raise ValueError('Wrong installation')
  for row in record['files']:
   b=(saved/row['backup']).resolve(strict=True)
   if not b.is_relative_to(saved) or sha(b)!=row['original_sha256']:raise ValueError('Invalid backup')
   if sha(target(row['path']))!=row['installed_sha256']:raise ValueError('Files or progress changed since installation; preserve newer progress')
  for row in record['files']:shutil.copy2(saved/row['backup'],target(row['path']))
  return dict(rolled_back=True,backup=str(saved))
 database=target('runtime/data/opendaoc.sqlite3.db')
 if apply:stopped(root)
 with tempfile.TemporaryDirectory(prefix='eod-trainers-',dir=REPO/'artifacts') as folder:
  world=Path(folder)/'world.db'
  with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(world)) as dest:source.backup(dest)
  with closing(sqlite3.connect(world)) as db,db:
   before=progress(db);summary=migrate(db)
   if before!=progress(db):raise ValueError('Migration changed saved progress')
   if db.execute('pragma quick_check').fetchone()[0]!='ok':raise ValueError('World integrity failed')
  files=[('runtime/data/opendaoc.sqlite3.db',world)]
  original={rel:sha(target(rel)) for rel,_ in files}
  installed={rel:sha(src) for rel,src in files}
  result=dict(preview=not apply,installation=str(root),progress_tables_verified=len(before),**summary)
  if not apply:return result
  stopped(root)
  with closing(sqlite3.connect(database)) as live:
   if live.execute('pragma wal_checkpoint(TRUNCATE)').fetchone()[0]!=0:raise ValueError('Database busy')
   if progress(live)!=before:raise ValueError('Saved progress changed during preparation')
  for rel,src in files:
   if sha(target(rel))!=original[rel] or sha(src)!=installed[rel]:raise ValueError('Installation/build changed during preparation')
  saved=root/'backups'/('eod-expansion-trainers-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));saved.mkdir()
  record=dict(installation=str(root),files=[])
  for i,(rel,src) in enumerate(files):
   backup=str(i)+'-'+Path(rel).name;shutil.copy2(target(rel),saved/backup)
   record['files'].append(dict(path=rel,backup=backup,original_sha256=original[rel],installed_sha256=installed[rel]))
  (saved/'manifest.json').write_text(json.dumps(record,indent=2))
  try:
   for rel,src in files:shutil.copy2(src,target(rel))
   for row in record['files']:
    if sha(target(row['path']))!=row['installed_sha256']:raise ValueError('Installed hash mismatch')
   with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as db:
    if progress(db)!=before:raise ValueError('Installed saved progress mismatch')
  except BaseException:
   for row in record['files']:shutil.copy2(saved/row['backup'],target(row['path']))
   raise
  return dict(result,verified=True,backup=str(saved))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('game',type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',type=Path);a=p.parse_args()
 if a.apply and a.rollback:p.error('Choose apply or rollback')
 print(json.dumps(install(a.game,a.apply,a.rollback),indent=2))
