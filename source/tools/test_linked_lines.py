"""Read-only checks of the totems and other linked spells (linked_lines.py) on a private copy of the modern test world."""
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest
import linked_lines as k

WORLD = Path(__file__).resolve().parents[2] / 'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'


class LinkedLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORLD.is_file():
            raise unittest.SkipTest('Modern test world is not available')
        cls.db = sqlite3.connect(':memory:'); cls.db.row_factory = sqlite3.Row
        with closing(sqlite3.connect(WORLD.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            src.backup(cls.db)
        with cls.db:
            cls.result = k.apply(cls.db)

    def spell(self, name, line):
        return self.db.execute('select s.*, l.Level as LineLevel from Spell s join LineXSpell l on l.SpellID=s.SpellID where s.Name=? and l.LineName=?',
                               (name, line)).fetchone()

    def by_id(self, spell_id):
        return self.db.execute('select * from Spell where SpellID=?', (spell_id,)).fetchone()

    def test_totems_pulse_their_child_at_the_live_rates(self):
        obsidian = self.spell('Obsidian Totem', 'Bone Mystics (Totems)')
        self.assertEqual((obsidian['Type'], obsidian['Frequency'], obsidian['Duration'], obsidian['Radius'], obsidian['Value'], obsidian['LifeDrainReturn']),
                         ('TimedPulseArea', 30, 30, 300, 16, 1))
        self.assertEqual((self.by_id(obsidian['SubSpellID'])['Type'], self.by_id(obsidian['SubSpellID'])['Damage']), ('DirectDamage', 252.5))
        grasping = self.spell('Grasping Totem', 'Bone Guardians (Totems)')
        self.assertEqual((self.by_id(grasping['SubSpellID'])['Type'], self.by_id(grasping['SubSpellID'])['Value']), ('TotemSnare', 75))
        self.assertEqual(grasping['SharedTimerGroup'], obsidian['SharedTimerGroup'], 'damage and snare totems share a reuse')
        sable = self.spell('Sable Totem', 'Bone Mystics (Totems)')
        self.assertEqual((sable['Frequency'], sable['LifeDrainReturn'], sable['RecastDelay']), (3, 2, 600))
        line = self.db.execute("select * from SpellLine where KeyName='Bone Mystics (Totems)'").fetchone()
        self.assertEqual((line['Spec'], line['ClassIDHint'], line['IsBaseLine']), ('Darkness', 30, 0))

    def test_thunder_champion_and_helping_hand(self):
        thunder = self.spell('Swirling Thunder', 'Stormcalling')
        self.assertEqual((thunder['LifeDrainReturn'], thunder['Frequency'], thunder['Duration'], self.by_id(thunder['SubSpellID'])['Damage']), (0, 25, 15, 26.9))
        call = self.spell('Call of the Champion', 'Valor')
        victorious = self.by_id(int(call['Value']))
        self.assertEqual((call['Type'], call['Frequency'], victorious['Damage'], self.by_id(victorious['SubSpellID'])['Value']), ('OffensiveProc', 100, 20.5, 30))
        self.assertEqual(self.by_id(call['SubSpellID'])['Type'], 'MeleeDamageTypeAura')
        holy = self.spell('Holy Hand', 'Terrible Hammer')
        self.assertEqual((holy['Type'], holy['Value'], holy['Duration'], holy['Power']), ('HelpingHand', 100, 20, 66))

    def test_champion_and_thane_chants(self):
        vitality, stoutness = self.spell('Vitality of Valor', 'Valor'), self.spell('Stoutness of Valor', 'Valor')
        self.assertEqual((vitality['Type'], vitality['Value'], vitality['Pulse'], vitality['Frequency'], vitality['Range'], vitality['Target']),
                         ('HealthArmorChant', 6, 1, 60, 1500, 'Group'))
        self.assertEqual(vitality['SpellGroup'], stoutness['SpellGroup'], 'one chant family')
        bulwark = self.spell('Bulwark of Thor', 'Stormcalling')
        self.assertEqual((bulwark['Value'], bulwark['LineLevel']), (6, 45))
        self.assertNotEqual(bulwark['SpellGroup'], vitality['SpellGroup'])

    def test_bonedancer_commands(self):
        defeat = self.spell('Familiar Defeat', 'Bone Warriors (Commands)')
        self.assertEqual((defeat['Type'], defeat['RecastDelay'], self.by_id(defeat['SubSpellID'])['Damage']), ('CommanderCommand', 15, 85.3))
        self.assertEqual(self.by_id(self.spell('Deathly Wail', 'Bone Warriors (Commands)')['SubSpellID'])['Type'], 'Taunt')
        soldier = self.spell('Punish Soldier', 'Bone Guardians (Commands)')
        self.assertEqual((self.by_id(soldier['SubSpellID'])['Type'], self.by_id(soldier['SubSpellID'])['Duration']), ('Disarm', 15))
        line = self.db.execute("select * from SpellLine where KeyName='Bone Warriors (Commands)'").fetchone()
        self.assertEqual((line['Spec'], line['ClassIDHint'], line['IsBaseLine']), ('Bone Army', 0, 0))

    def test_second_gap_pass(self):
        revenants = self.spell('Bone Revenants', 'Bone Mystics (Totems)')
        self.assertEqual((revenants['LifeDrainReturn'], revenants['Value'], revenants['Frequency'], self.by_id(revenants['SubSpellID'])['Damage']),
                         (3, 3, 50, 300))
        mender = self.spell('Summon Bone Mender', 'Bone Army (Summons)')
        self.assertEqual((mender['Type'], mender['LifeDrainReturn'], mender['DamageType'], mender['Value']), ('SummonMinion', 76, 1, 45))
        self.assertEqual(self.spell('Summon Commander', 'Bone Army (Commanders)')['Type'], 'SummonCommander')
        elder = self.db.execute("select s.Duration, s.RecastDelay, s.Damage, l.Level from Spell s join LineXSpell l on l.SpellID=s.SpellID "
                                "where s.SpellID=3592 and l.LineName='Beastcraft'").fetchone()
        self.assertEqual(tuple(elder), (300, 90, -100, 50))
        frenzy = self.spell('Wolfen Frenzy', 'Beastcraft')
        self.assertEqual((frenzy['Type'], frenzy['Target'], self.by_id(frenzy['SubSpellID'])['Type']), ('CombatSpeedBuff', 'Pet', 'MeleeDamageBuff'))
        self.assertEqual((self.spell('Halt Magic', 'Subterranean Spec')['Type'], self.spell('Bane of Prophecy', 'Subterranean Spec')['Value']),
                         ('SpellDamageDebuff', 999))
        self.assertEqual(self.spell('Caustic Carapace', 'Shaman Augmentation Spec')['LifeDrainReturn'], 1, 'melee only')
        self.assertEqual(self.spell('Song of Sorcerous Reach', 'Instruments')['Type'], 'SpellRangeBuff')
        self.assertEqual(self.spell('Familiar Defeat', 'Bone Warriors (Commands)')['Power'], -20)

    def test_reapplying_is_stable_and_out_of_the_death_knight_block(self):
        with self.db:
            self.assertEqual(k.apply(self.db), self.result)
        tooltips = [r[0] for r in self.db.execute('select TooltipId from Spell where PackageID=?', (k.PACKAGE,))]
        self.assertFalse(any(k.RESERVED_TOOLTIPS[0] <= t <= k.RESERVED_TOOLTIPS[1] for t in tooltips))
        self.assertTrue(all(t <= 32767 for t in tooltips))


if __name__ == '__main__':
    unittest.main()
