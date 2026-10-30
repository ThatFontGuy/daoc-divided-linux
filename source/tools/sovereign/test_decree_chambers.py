from contextlib import closing
import sqlite3
import unittest
from seed_decree_chambers import seed
from install_sovereign import progress
from test_pendragon import WORLD

class ChamberMigrationTests(unittest.TestCase):
 def test_both_realms_gain_preparations_without_changing_combat_or_progress(self):
  with closing(sqlite3.connect(WORLD.resolve().as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(':memory:')) as db:
   src.backup(db);db.row_factory=sqlite3.Row
   before=progress(db)
   combat=[tuple(r) for r in db.execute('select SpellID,Damage,Power,Range,Radius,Duration,CastTime,RecastDelay from Spell where SpellID between 62400 and 62655 or SpellID between 64000 and 64255 order by SpellID')]
   with db: result=seed(db)
   self.assertEqual(result['preparation_spells'],0)
   self.assertFalse(db.execute("select 1 from SpellLine where KeyName like 'CrownPreparations.%'").fetchone())
   self.assertFalse(db.execute('select 1 from Spell where SpellID between 62970 and 62972 or SpellID between 64570 and 64572').fetchone())
   self.assertEqual(progress(db),before)
   self.assertEqual([tuple(r) for r in db.execute('select SpellID,Damage,Power,Range,Radius,Duration,CastTime,RecastDelay from Spell where SpellID between 62400 and 62655 or SpellID between 64000 and 64255 order by SpellID')],combat)
   with db:self.assertEqual(seed(db),result)
   self.assertEqual(progress(db),before)
