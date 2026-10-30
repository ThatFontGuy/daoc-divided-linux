"""Retire the chamber experiment; future reseeds retain instant decrees."""
import sqlite3

def seed(db,classes=(64,65)):
 db.row_factory=sqlite3.Row
 for cls in classes:
  offset={65:1600,67:10600}.get(cls,0)
  package={65:'OfflineDAoC.Pendragon.v1',67:'OfflineDAoC.Tuatha.v1'}.get(cls,'OfflineDAoC.Stormforged.v1')
  line='CrownPreparations.'+{65:'Albion',67:'Hibernia'}.get(cls,'Midgard')
  for slot in range(3):
   id=62970+offset+slot
   row=db.execute('select PackageID from Spell where SpellID=?',(id,)).fetchone()
   if row and row[0]!=package: raise ValueError('Preparation identity belongs to another package')
   db.execute('delete from LineXSpell where SpellID=?',(id,))
   db.execute('delete from Spell where SpellID=? and PackageID=?',(id,package))
  db.execute('delete from LineXSpell where LineName=?',(line,))
  db.execute('delete from SpellLine where KeyName=? and ClassIDHint=?',(line,cls))
  db.execute("update Spell set Description=replace(Description,' Requires a prepared decree chamber.','') where PackageID=? and Description like '%Requires a prepared decree chamber.%'",(package,))
 return dict(instant_decree_classes=list(classes),preparation_spells=0,player_tables_changed=False)
