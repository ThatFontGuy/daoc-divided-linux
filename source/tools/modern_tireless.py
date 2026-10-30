"""Free native Tireless from level one for all classes. No saved-character edits."""
import sqlite3

def apply(db):
 db.row_factory=sqlite3.Row
 ability=db.execute("select Implementation from Ability where KeyName='Tireless'").fetchone()
 if ability is None or ability[0] not in (None,''):raise ValueError('Unexpected native Tireless implementation; review first')
 rows=db.execute("select * from SpecXAbility where Spec='CharacterCareer' and AbilityKey='Tireless'").fetchall()
 if len(rows)!=1:raise ValueError('Expected exactly one universal Tireless career definition')
 row=rows[0]
 if row['ClassId'] not in (99,0):raise ValueError('Unexpected Tireless career scope')
 if not db.execute("select 1 from ClassXSpecialization where ClassID=0 and SpecKeyName='CharacterCareer'").fetchone():raise ValueError('Missing universal character career')
 db.execute("update SpecXAbility set SpecLevel=1,AbilityLevel=1,ClassId=0 where Spec='CharacterCareer' and AbilityKey='Tireless'")
 db.execute("update Ability set Description='Automatically grants one endurance regeneration per tick from level 1. Does not stack with stronger endurance regeneration.' where KeyName='Tireless'")
 removed=db.execute("delete from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_Tireless'").rowcount
 return dict(tireless_level=1,tireless_rank=1,class_scope='all classes, including base and custom classes',paid_tireless_bindings_removed=removed,existing_purchases_preserved=True)
