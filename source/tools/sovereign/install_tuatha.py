"""Guarded Tuatha Sovereign installation for the explicitly selected modern test world.
Build/test first. Preview unless --apply. Never starts or stops game processes.

Installs the seeded world, the Release GameServer.dll and the native class-slot client
(source/tools/classslots: Hibernia's slot is class 67), and
updates the launcher profile's GameSha256 to that client.
"""
import argparse
from contextlib import closing
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from seed_tuatha import seed
from install_pendragon import progress, sha
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'classslots'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stormforged'))
from patch_class_slots import patch, SUPPORTED, KNOWN_NATIVE_CLIENTS
from install import stopped
REPO=Path(__file__).resolve().parents[3]
KNOWN_CLIENTS=KNOWN_NATIVE_CLIENTS

def install(root,apply=False,rollback=None):
 root=root.resolve(strict=True)
 def target(rel):
  p=(root/rel).resolve(strict=True)
  if not p.is_relative_to(root): raise ValueError('Path leaves selected installation')
  return p
 if rollback:
  stopped(root)
  saved=rollback.resolve(strict=True)
  record=json.loads((saved/'manifest.json').read_text())
  if record['installation']!=str(root): raise ValueError('Backup belongs to another installation')
  for row in record['files']:
   backup=(saved/row['backup']).resolve(strict=True)
   if not backup.is_relative_to(saved) or sha(backup)!=row['original_sha256']: raise ValueError('Invalid backup')
   if sha(target(row['path']))!=row['installed_sha256']: raise ValueError('Installed file changed; preserve newer gameplay and recover manually')
  for row in record['files']: shutil.copy2(saved/row['backup'],target(row['path']))
  return dict(rolled_back=True,backup=str(saved))
 database=target('runtime/data/opendaoc.sqlite3.db')
 client=target('runtime/client-modern/app/game.dll')
 profile=target('runtime/modern-client.json')
 build=REPO/'source/server/Release/lib/GameServer.dll'
 if not build.is_file(): raise ValueError('Build the Release server first')
 pristine=root/'backups/client-bundle-20261021-165832-708287/game.original.dll'
 original=pristine.read_bytes()
 if hashlib.sha256(original).hexdigest()!=SUPPORTED: raise ValueError('Pristine client hash mismatch')
 new_client,_=patch(original)
 new_hash=hashlib.sha256(new_client).hexdigest()
 if sha(client) not in KNOWN_CLIENTS|{new_hash}: raise ValueError('Unknown current client; no files changed')
 settings=json.loads(profile.read_text())
 if settings['GameSha256'].lower()!=sha(client): raise ValueError('Profile/client hash mismatch')
 if apply: stopped(root)
 with tempfile.TemporaryDirectory(prefix='tuatha-',dir=REPO/'artifacts') as folder:
  temp=Path(folder);world=temp/'world.db'
  with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(world)) as dst: src.backup(dst)
  with closing(sqlite3.connect(world)) as db,db:
   before=progress(db)
   if db.execute("select Value from ServerProperty where Key='native_custom_class_slots'").fetchone()!=('True',):
    raise ValueError('The Tuatha Sovereign needs classes/native_custom_class_slots=True')
   summary=seed(db)
   if progress(db)!=before: raise ValueError('Migration changed player progress')
   if db.execute('pragma quick_check').fetchone()[0]!='ok': raise ValueError('World integrity check failed')
  (temp/'game.dll').write_bytes(new_client)
  settings['GameSha256']=new_hash.upper()
  (temp/'modern-client.json').write_text(json.dumps(settings,indent=2)+'\n')
  files=[('runtime/data/opendaoc.sqlite3.db',world),('runtime/client-modern/app/game.dll',temp/'game.dll'),('runtime/modern-client.json',temp/'modern-client.json')]
  for directory in ('runtime/server','runtime/server/lib','runtime/server/win-x64'):
   files.append((directory+'/GameServer.dll',build))
   if (root/directory/'GameServer.pdb').is_file(): files.append((directory+'/GameServer.pdb',build.with_suffix('.pdb')))
  for rel,src in files:
   target(rel)
   if not src.is_file(): raise FileNotFoundError(src)
  result=dict(preview=not apply,installation=str(root),client_sha256=new_hash,server_sha256=sha(build),progress_tables_verified=len(before),**summary)
  if not apply: return result
  # Require unchanged source files and stopped processes immediately before applying.
  stopped(root)
  with closing(sqlite3.connect(database,timeout=5)) as live:
   if live.execute('pragma wal_checkpoint(TRUNCATE)').fetchone()[0]!=0: raise ValueError('Database busy; close the server')
   if progress(live)!=before: raise ValueError('Progress changed while preparing installation')
  saved=root/'backups'/('tuatha-sovereign-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
  saved.mkdir()
  record=dict(installation=str(root),files=[])
  for index,(rel,src) in enumerate(files):
   path=target(rel);backup=str(index)+'-'+path.name
   shutil.copy2(path,saved/backup)
   record['files'].append(dict(path=rel,backup=backup,original_sha256=sha(path),installed_sha256=sha(src)))
  (saved/'manifest.json').write_text(json.dumps(record,indent=2))
  try:
   for rel,src in files: shutil.copy2(src,target(rel))
   for row in record['files']:
    if sha(target(row['path']))!=row['installed_sha256']: raise ValueError('Installed hash mismatch')
  except BaseException:
   for row in record['files']: shutil.copy2(saved/row['backup'],target(row['path']))
   raise
  return dict(result,backup=str(saved),verified=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('game',type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',type=Path);a=p.parse_args()
 if a.apply and a.rollback: p.error('Choose apply or rollback')
 print(json.dumps(install(a.game,a.apply,a.rollback),indent=2))
