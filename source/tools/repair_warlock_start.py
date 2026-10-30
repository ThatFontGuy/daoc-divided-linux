"""Repair zero-region Warlocks in the selected modern test world; preview unless --apply."""
import argparse
from contextlib import closing
import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from warlock_test_data import ensure_start_location
from install_warlock_test import REPO,sha,progress,stopped

POSITION_FIELDS=('Region','Xpos','Ypos','Zpos','Direction','BindRegion','BindXpos','BindYpos','BindZpos','BindHeading')

def repair(db):
    db.row_factory=sqlite3.Row
    before=progress(db)
    characters=[dict(r) for r in db.execute('select * from DOLCharacters order by DOLCharacters_ID')]
    start=ensure_start_location(db)
    values=(start['Region'],start['XPos'],start['YPos'],start['ZPos'],start['Heading'])*2
    # Only the exact corrupt creation state observed in the crash log is eligible.
    result=db.execute('update DOLCharacters set '+','.join(k+'=?' for k in POSITION_FIELDS)+' where Class=59 and Realm=2 and Region=0 and Xpos=0 and Ypos=0 and Zpos=0 and BindRegion=0',values)
    repaired=result.rowcount
    after_characters=[dict(r) for r in db.execute('select * from DOLCharacters order by DOLCharacters_ID')]
    for old,new in zip(characters,after_characters):
        eligible=old['Class']==59 and old['Realm']==2 and old['Region']==old['Xpos']==old['Ypos']==old['Zpos']==old['BindRegion']==0
        expected=dict(old)
        if eligible:expected.update(zip(POSITION_FIELDS,values))
        if new!=expected:raise ValueError('Unexpected character-data change')
    if len(characters)!=len(after_characters):raise ValueError('Character count changed')
    after=progress(db)
    if any(before[t]!=after[t] for t in before if t!='DOLCharacters'):raise ValueError('Other saved progress changed')
    if db.execute('pragma quick_check').fetchone()[0]!='ok':raise ValueError('Database integrity failed')
    return dict(repaired_characters=repaired,start_region=start['Region'],other_progress_tables_verified=len(before)-1)

def install(apply=False):
    root=(REPO/'artifacts/modern-client-test').resolve(strict=True)
    database=root/'runtime/data/opendaoc.sqlite3.db'
    if apply:
        stopped(root)
        with closing(sqlite3.connect(database)) as live:
            if live.execute('pragma wal_checkpoint(TRUNCATE)').fetchone()[0]!=0:raise ValueError('Database busy')
    original=sha(database)
    with tempfile.TemporaryDirectory(prefix='warlock-start-',dir=REPO/'artifacts') as folder:
        candidate=Path(folder)/'world.db'
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(candidate)) as dst:src.backup(dst)
        with closing(sqlite3.connect(candidate)) as db,db:summary=repair(db)
        if not apply:return dict(preview=True,**summary)
        stopped(root)
        if sha(database)!=original:raise ValueError('World changed during preparation')
        saved=root/'backups'/('warlock-start-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));saved.mkdir()
        shutil.copy2(database,saved/'world-before.db')
        record=dict(original_sha256=original,installed_sha256=sha(candidate),**summary)
        (saved/'manifest.json').write_text(json.dumps(record,indent=2))
        try:
            shutil.copy2(candidate,database)
            if sha(database)!=record['installed_sha256']:raise ValueError('Installed hash mismatch')
        except BaseException:
            shutil.copy2(saved/'world-before.db',database)
            raise
        return dict(preview=False,verified=True,backup=str(saved),**summary)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(json.dumps(install(a.apply),indent=2))
