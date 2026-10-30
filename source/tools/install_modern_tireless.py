"""Install free level-one Tireless without replacing the world or touching trainer/armor rows."""
import argparse
from contextlib import closing
import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from modern_tireless import apply as migrate
sys.path.insert(0,str(Path(__file__).resolve().parent/'sovereign'))
from install_instant_decrees import REPO,sha,progress,stopped

def install(root,apply=False,rollback=None,build_dir=None,*,migration=migrate,backup_prefix="free-tireless"):
 root=root.resolve(strict=True)
 if root!=(REPO/'artifacts/modern-client-test').resolve():raise ValueError('Only the selected modern test installation is supported')
 database=(root/'runtime/data/opendaoc.sqlite3.db').resolve(strict=True)
 if not database.is_relative_to(root):raise ValueError('Database path leaves installation')
 def target(rel):
  p=(root/rel).resolve(strict=True)
  if not p.is_relative_to(root):raise ValueError('Path leaves installation')
  return p
 if rollback:
  stopped(root);saved=rollback.resolve(strict=True)
  if not saved.is_relative_to(root/'backups'):raise ValueError('Backup outside installation')
  if Path(str(database)+'-wal').exists() and Path(str(database)+'-wal').stat().st_size:raise ValueError('Database has later WAL writes; preserve newer changes')
  record=json.loads((saved/'manifest.json').read_text())
  if record['installation']!=str(root):raise ValueError('Wrong installation')
  for row in record['files']:
   b=(saved/row['backup']).resolve(strict=True)
   if not b.is_relative_to(saved) or sha(b)!=row['original_sha256']:raise ValueError('Backup hash mismatch')
   if sha(target(row['path']))!=row['installed_sha256']:raise ValueError('Files or progress changed; preserve newer data')
  for row in record['files']:shutil.copy2(saved/row['backup'],target(row['path']))
  return dict(rolled_back=True,backup=str(saved))
 if not apply:
  with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(':memory:')) as db:
   source.backup(db);before=progress(db)
   with db:summary=migration(db)
   if progress(db)!=before:raise ValueError('Migration changed saved progress')
   return dict(preview=True,progress_tables_verified=len(before),**summary)
 stopped(root)
 build=(build_dir or REPO/'source/server/Release/lib')/'GameServer.dll'
 # A concurrent class/client integration may have changed the shared source after this build.
 source_root=REPO/'source/server/GameServer'
 def fresh():
  if source_root.is_dir() and any(p.stat().st_mtime_ns>build.stat().st_mtime_ns for p in source_root.rglob('*.cs')):
   raise ValueError('Server source changed after this build; rebuild and retest before installing')
 fresh()
 files=[]
 for directory in ('runtime/server','runtime/server/lib','runtime/server/win-x64'):
  files.append((directory+'/GameServer.dll',build))
  if (root/directory/'GameServer.pdb').is_file():files.append((directory+'/GameServer.pdb',build.with_suffix('.pdb')))
 expected={rel:sha(src) for rel,src in files};old={rel:sha(target(rel)) for rel,_ in files}
 saved=root/'backups'/(backup_prefix+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));saved.mkdir()
 record=dict(installation=str(root),files=[],committed=False)
 for i,(rel,_) in enumerate(files):
  backup=str(i)+'-'+Path(rel).name;shutil.copy2(target(rel),saved/backup)
  record['files'].append(dict(path=rel,backup=backup,original_sha256=old[rel],installed_sha256=expected[rel]))
 committed=False
 try:
  with closing(sqlite3.connect(database,timeout=10)) as db:
   db.execute('BEGIN IMMEDIATE')
   # The write lock prevents another migration from changing definitions between backup and commit.
   with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(saved/'world-before.db')) as dest:source.backup(dest)
   record['files'].insert(0,dict(path='runtime/data/opendaoc.sqlite3.db',backup='world-before.db',original_sha256=sha(saved/'world-before.db'),installed_sha256=None))
   (saved/'manifest.json').write_text(json.dumps(record,indent=2))
   before=progress(db)
   summary=migration(db)
   if progress(db)!=before or db.execute('pragma quick_check').fetchone()[0]!='ok':raise ValueError('Migration failed integrity/progress checks')
   stopped(root);fresh()
   for rel,src in files:
    if sha(target(rel))!=old[rel] or sha(src)!=expected[rel]:raise ValueError('Build or installed server changed during preparation')
   for rel,src in files:shutil.copy2(src,target(rel))
   for rel,_ in files:
    if sha(target(rel))!=expected[rel]:raise ValueError('Installed server hash mismatch')
   db.commit();committed=True
   db.execute('pragma wal_checkpoint(TRUNCATE)')
  record['files'][0]['installed_sha256']=sha(database);record['committed']=True
  (saved/'manifest.json').write_text(json.dumps(record,indent=2))
 except BaseException:
  if not committed:
   for row in record['files']:
    if row['path']!='runtime/data/opendaoc.sqlite3.db':shutil.copy2(saved/row['backup'],target(row['path']))
  raise
 return dict(preview=False,backup=str(saved),progress_tables_verified=len(before),server_sha256=sha(build),verified=True,**summary)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('game',type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',type=Path);p.add_argument('--build-dir',type=Path);a=p.parse_args()
 if a.apply and a.rollback:p.error('Choose apply or rollback')
 print(json.dumps(install(a.game,a.apply,a.rollback,a.build_dir),indent=2))
