"""Read-only checks of the live Envenom poisons (envenom_lines.py) on a private copy of the modern test world."""
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest
import envenom_lines as e

WORLD = Path(__file__).resolve().parents[2] / 'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'


class EnvenomLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORLD.is_file():
            raise unittest.SkipTest('Modern test world is not available')
        cls.db = sqlite3.connect(':memory:'); cls.db.row_factory = sqlite3.Row
        with closing(sqlite3.connect(WORLD.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            src.backup(cls.db)
        with cls.db:
            cls.result = e.apply(cls.db)

    def coating(self, name, line='Nightshade Envenom'):
        return self.db.execute('select s.*, l.Level as LineLevel from Spell s join LineXSpell l on l.SpellID=s.SpellID where s.Name=? and l.LineName=?',
                               (name, line)).fetchone()

    def poison(self, coating):
        return self.db.execute('select * from Spell where SpellID=?', (int(coating['Value']),)).fetchone()

    def test_all_three_assassins_get_the_same_32_spells(self):
        self.assertEqual((self.result['envenom_spells'], self.result['envenom_lines']), (32, 3))
        for key, hint in e.LINES:
            line = self.db.execute('select * from SpellLine where KeyName=?', (key,)).fetchone()
            self.assertEqual((line['Spec'], line['ClassIDHint'], line['IsBaseLine']), ('Envenom', hint, 0))
            self.assertEqual(self.db.execute('select count(*) from LineXSpell where LineName=?', (key,)).fetchone()[0], 32)
        spec = self.db.execute("select Implementation from Specialization where KeyName='Envenom'").fetchone()
        self.assertEqual(spec[0], e.HYBRID)

    def test_coatings_fire_their_live_poison(self):
        lifebane = self.coating('Lifebane')
        self.assertEqual((lifebane['Type'], lifebane['Frequency'], lifebane['RecastDelay'], lifebane['SharedTimerGroup'], lifebane['LineLevel']),
                         ('PoisonCoating', 100, 7, e.COATING_TIMER, 50))
        self.assertEqual((self.poison(lifebane)['Type'], self.poison(lifebane)['Damage'], self.poison(lifebane)['Frequency']), ('DamageOverTime', 82, 39))
        self.assertEqual(self.coating('Minor Lethal Poison')['RecastDelay'], 10)
        self.assertEqual(self.poison(self.coating('Swordbreaker'))['Value'], 15)
        touch = self.poison(self.coating('Touch of Death'))
        self.assertEqual((touch['Type'], int(touch['Value'] / 5.4)), ('WeaponSkillDebuff', 21))
        shadowbind = self.poison(self.coating('Shadowbind'))
        self.assertEqual((shadowbind['Type'], shadowbind['Value'], shadowbind['Duration']), ('PoisonSnare', 60, 7))
        self.assertEqual(self.coating('Crippling Toxin')['RecastDelay'], 7)
        miasma = self.coating('Tranquilizing Miasma')
        self.assertEqual((miasma['RecastDelay'], miasma['SharedTimerGroup'], self.poison(miasma)['Radius'], self.poison(miasma)['Duration']),
                         (120, e.MEZ_TIMER, 700, 8))
        self.assertEqual(self.coating('Consume Venom')['Type'], 'ConsumeVenom')

    def test_stealth_line_spells(self):
        self.assertEqual(self.result['stealth_spells'], 22)
        caltrops = self.coating('Caltrops', 'Infiltrator Stealth')
        self.assertEqual((caltrops['Type'], caltrops['LifeDrainReturn'], self.db.execute('select Value from Spell where SpellID=?', (caltrops['SubSpellID'],)).fetchone()[0]), ('TimedPulseArea', 2, 25))
        self.assertEqual(self.coating('Heightened Awareness', 'Hunter Stealth')['LineLevel'], 30)
        reflection = self.coating('Eventide Reflection', 'Nightshade Stealth')
        self.assertEqual((reflection['Type'], reflection['Damage'], reflection['Duration']), ('DamageShield', 5.0, 1200))
        self.assertEqual(self.coating('Clouded Destruction', 'Nightshade Stealth')['Damage'], 22)
        bludgeon = self.coating('Bludgeon', 'Shadowblade Stealth')
        self.assertEqual((bludgeon['Type'], bludgeon['DamageType'], bludgeon['RecastDelay']), ('MeleeDamageTypeAura', 1, 180))
        line = self.db.execute("select * from SpellLine where KeyName='Nightshade Stealth'").fetchone()
        self.assertEqual((line['Spec'], line['ClassIDHint'], line['IsBaseLine']), ('Stealth', 49, 0))

    def test_ranks_share_a_group_so_only_the_best_shows(self):
        groups = {r[0] for r in self.db.execute("select SpellGroup from Spell where PackageID=? and Type='PoisonCoating'", (e.PACKAGE,))}
        self.assertEqual(len(groups), len(e.FAMILIES))

    def test_reapplying_is_stable_and_out_of_the_death_knight_block(self):
        with self.db:
            self.assertEqual(e.apply(self.db), self.result)
        tooltips = [r[0] for r in self.db.execute('select TooltipId from Spell where PackageID=?', (e.PACKAGE,))]
        self.assertFalse(any(e.RESERVED_TOOLTIPS[0] <= t <= e.RESERVED_TOOLTIPS[1] for t in tooltips))
        self.assertTrue(all(t <= 32767 for t in tooltips))


if __name__ == '__main__':
    unittest.main()
