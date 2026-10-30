"""Selective Eve of Darkness trainer import; no class unlocks or saved-progress edits."""
from collections import Counter
import hashlib
import json
from pathlib import Path
PACKAGE='OfflineDAoC.ExpansionTrainers.EoD.v1'
TEMPORARY_VALKYRIE='local-valkyrie-test-trainer'
DATA=Path(__file__).with_name('expansion-trainers-eod.json')
EXPECTED_SOURCE_HASH='d82e150eb1cb485d06aff608c4ab14248bdd7a993820197d0c33856935385b06'

def source_rows():
 raw=DATA.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=EXPECTED_SOURCE_HASH:raise ValueError('Trainer source snapshot hash mismatch')
 return json.loads(raw)['trainers']

def apply(db):
 import sqlite3
 db.row_factory=sqlite3.Row
 columns={r['name'] for r in db.execute('pragma table_info(Mob)')}
 equipment={r[0] for r in db.execute('select distinct TemplateID from NPCEquipment')}
 regions={r[0] for r in db.execute('select RegionID from Regions')}
 zones=list(db.execute('select RegionID,OffsetX,OffsetY,Width,Height from Zones'))
 added=[];existing=[];equivalent=[]
 # Validate every dependency and collision before writing any row.
 for original in source_rows():
  row={k:v for k,v in original.items() if k!='SourceMobID'}
  if set(row)-columns:raise ValueError('Incompatible Mob schema')
  if row['EquipmentTemplateID'] and row['EquipmentTemplateID'] not in equipment:raise ValueError('Missing trainer equipment '+row['Name'])
  if row['Region'] not in regions:raise ValueError('Missing trainer region '+str(row['Region']))
  if not any(z['RegionID']==row['Region'] and z['OffsetX']<=row['X']/8192<z['OffsetX']+z['Width'] and z['OffsetY']<=row['Y']/8192<z['OffsetY']+z['Height'] for z in zones):raise ValueError('Trainer is outside known zone bounds: '+row['Name'])
  previous=db.execute('select * from Mob where Mob_ID=?',(row['Mob_ID'],)).fetchone()
  if previous:
   if any(previous[k]!=v for k,v in row.items()):raise ValueError('Trainer identity/content collision: '+row['Name'])
   existing.append(row['Name']);continue
  matches=db.execute('select Name from Mob where lower(Name)=lower(?) and Guild=? and Region=? and Realm=? and ClassType=? and abs(X-?)<=64 and abs(Y-?)<=64 and abs(Z-?)<=64',(row['Name'],row['Guild'],row['Region'],row['Realm'],row['ClassType'],row['X'],row['Y'],row['Z'])).fetchall()
  if matches:equivalent.append(row['Name']);continue
  added.append(row)
 temporary=db.execute('select Name,Guild,ClassType from Mob where Mob_ID=?',(TEMPORARY_VALKYRIE,)).fetchone()
 if temporary and tuple(temporary)!=('Valkyrie Trainer','Valkyrie Trainer','DOL.GS.Trainer.ValkyrieTrainer'):raise ValueError('Temporary Valkyrie identity is unexpectedly occupied')
 for row in added:
  db.execute('insert into Mob ('+','.join('"'+k+'"' for k in row)+') values ('+','.join('?' for _ in row)+')',list(row.values()))
 removed=db.execute('delete from Mob where Mob_ID=?',(TEMPORARY_VALKYRIE,)).rowcount
 return dict(added=len(added),already_installed=len(existing),equivalent_existing=len(equivalent),temporary_valkyrie_removed=removed,
  added_by_class=dict(Counter(r['Guild'] for r in added)),package=PACKAGE)
