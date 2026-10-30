"""Read-only checks of the next ten classes' live spells (round3_lines.py) on a private copy of the modern test world."""
from contextlib import closing
from pathlib import Path
import collections
import sqlite3
import unittest
import round3_lines as r

WORLD = Path(__file__).resolve().parents[2] / 'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'


class Round3LineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORLD.is_file():
            raise unittest.SkipTest('Modern test world is not available')
        cls.db = sqlite3.connect(':memory:'); cls.db.row_factory = sqlite3.Row
        with closing(sqlite3.connect(WORLD.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            src.backup(cls.db)
        with cls.db:
            cls.result = r.apply(cls.db)

    def spell(self, name, line):
        return self.db.execute('select s.*, l.Level as LineLevel from Spell s join LineXSpell l on l.SpellID=s.SpellID where s.Name=? and l.LineName=?',
                               (name, line)).fetchone()

    def by_id(self, spell_id):
        return self.db.execute('select * from Spell where SpellID=?', (spell_id,)).fetchone()

    def test_values(self):
        drain = self.spell('Spirit Drain', 'Spirit Enhancement (Live)')
        self.assertEqual((drain['Type'], drain['Damage'], drain['LifeDrainReturn']), ('PowerDrain', 187.5, 20))
        self.assertEqual(self.spell('Otherworldly Annihilation', 'Spirit Enhancement (Live)')['Value'], 75)
        abolition = self.spell('Soul Abolition', 'Spirit Suppression (Live)')
        self.assertEqual((abolition['Type'], abolition['Target'], abolition['Range'], abolition['Damage']), ('DirectDamage', 'Enemy', 0, 391.8))
        tap = self.spell("Eir's Intervention", 'Pacification Spec')
        self.assertEqual((tap['Type'], tap['Frequency'], self.by_id(int(tap['Value']))['Damage']), ('OffensiveProc', 40, 183.0))
        self.assertEqual(self.spell('Mana Barrier', 'Enchantment Mastery (Live)')['Value'], 1500)
        self.assertEqual(self.spell('Grandmaster Staffman', 'Friar Enhancement Spec')['Type'], 'StaffSkillBuff')

    def test_fourth_pass(self):
        self.assertEqual((self.spell('Greater Earthen Rage', 'Path of Earth (Live)')['Damage']), 10.0)
        tempest = self.spell('Steaming Tempest', 'Liquifaction (Live)')
        self.assertEqual((tempest['Target'], tempest['Radius'], tempest['Damage']), ('Enemy', 300, 391.8))
        self.assertEqual(self.spell('Terrify Minion', 'Pyromancy (Live)')['Duration'], 42)
        self.assertEqual(self.spell('March of Bragi', 'Battlesongs')['Value'], 135)
        frenzy = self.spell("Nature's Frenzy", 'Druid Nature Spec')
        self.assertEqual(self.by_id(frenzy['SubSpellID'])['Type'], 'MeleeDamageBuff')
        self.assertEqual(self.spell('Illusion of Protection', 'Mind Mastery (Live)')['Pulse'], 1)

    def test_live_lines_copy_their_sibling_and_hold_one_spell_per_level(self):
        for key, spec, hint, base in r.LINES:
            sibling = self.db.execute('select * from SpellLine where KeyName=?', (key.replace(' (Live)', ''),)).fetchone()
            if key == 'Warrior Shields (Live)':  # the Warrior had no spell line to copy
                self.assertIsNone(sibling)
                continue
            self.assertEqual((sibling['Spec'], sibling['ClassIDHint'], sibling['IsBaseLine']), (spec, hint, base), key)
        # The client casts only the first spell at a level of a list caster's line, so those keep one per level (the hybrid
        # lines list each spell group).
        for line in {key for key, _, _, _ in r.LINES} | {'Spirit Dimming', 'Illusions', 'Refrigeration', 'Arboreal Mastery', 'Druid Nature Magic',
                                                          'Enchantment'}:
            ours = {x[0] for x in self.db.execute('select l.Level from LineXSpell l join Spell s on s.SpellID=l.SpellID where l.LineName=? and s.PackageID=?',
                                                  (line, r.PACKAGE))}
            levels = collections.Counter(x[0] for x in self.db.execute('select Level from LineXSpell where LineName=?', (line,)))
            self.assertEqual([lv for lv in sorted(ours) if levels[lv] > 1], [], line)

    def test_seventh_pass(self):
        for name, line, cap in [("Hel's Domination", 'Spirit Dimming', 50), ('Phantom Adversary', 'Illusions', 26),
                                ('Engrossing Harmony', 'Instruments', 40)]:
            charm = self.spell(name, line)
            self.assertEqual((charm['Type'], charm['Value'], charm['Damage'], charm['AmnesiaChance'], charm['CastTime']),
                             ('Charm', cap, 100, 0, 4.0), name)
        imbue = self.spell('Imbue Greater Alacrity', 'Friar Enhancement Spec')
        self.assertEqual((imbue['Type'], imbue['Value'], imbue['Concentration'], imbue['EffectGroup'], imbue['LineLevel']),
                         ('CombatSpeedBuff', 20, 19, 100, 46))
        for line in ['Healer Mending Spec', 'Rebirth', 'Regrowth Warden Spec']:
            self.assertEqual(self.spell('Confounding Cast', line)['Type'], 'Confusion')
        stone = self.spell('Enchantment of Stone', 'Enchantment Mastery (Live)')
        self.assertEqual((stone['Type'], stone['DamageType'], self.by_id(stone['SubSpellID'])['Value']), ('MeleeDamageTypeAura', r.MATTER, 300))
        fire = self.spell('Enchantment of Fire', 'Enchantment Mastery (Live)')
        self.assertEqual((fire['DamageType'], self.by_id(fire['SubSpellID'])['Type']), (r.HEAT, 'MeleeDamageBuff'))
        self.assertEqual(self.spell('Enchantment of Zeal', 'Enchantment Mastery (Live)')['Value'], 3)
        for line in ['Infiltrator Stealth', 'Nightshade Stealth', 'Shadowblade Stealth']:
            self.assertEqual(self.spell('Overshadow', line)['Type'], 'AllyStealth')
        for line in ['Valor', 'Battlesongs', 'Instruments']:
            self.assertEqual(self.spell('Siegebreaker', line)['Damage'], 20)
        warp = self.spell('Speedwarp', 'Mind Mastery (Live)')
        self.assertEqual((warp['Type'], warp['Radius'], warp['Duration'], self.by_id(warp['SubSpellID'])['Type']),
                         ('TimedPulseArea', 2000, 300, 'Speedwarp'))
        self.assertEqual(self.spell('Chain Lightning', 'Stormcalling')['Damage'], 396.8)
        self.assertEqual(self.spell('Battle Control', 'Warrior Shields (Live)')['Value'], 5)
        surge = self.spell('Blight Surge', 'Subterranean Spec')
        self.assertEqual(surge['SubSpellID'], 0)  # the pulse child is in LifeDrainReturn, or the cast would hit the Shaman
        blight = self.by_id(surge['LifeDrainReturn'])
        self.assertEqual((blight['Type'], blight['Damage'], self.by_id(blight['SubSpellID'])['Type']), ('DirectDamage', 50, 'Disease'))
        elemental = self.spell('Summon Greater Ice Elemental', 'Refrigeration')
        aged = self.by_id(267)
        self.assertEqual(self.db.execute('select Name from NpcTemplate where TemplateId=?', (elemental['LifeDrainReturn'],)).fetchone()[0],
                         'greater ice elemental')
        self.assertEqual(elemental['Range'], 1875)
        for field in ['Type', 'Target', 'Power', 'CastTime', 'Damage', 'Duration', 'Value', 'ResurrectHealth', 'ResurrectMana']:
            self.assertEqual(elemental[field], aged[field], field)

    def test_pets(self):
        def template(spell):
            return self.db.execute('select * from NpcTemplate where TemplateId=?', (spell['LifeDrainReturn'],)).fetchall()

        # Each pet's template is a copy of its source with the live name.
        for template_id, source, source_name, name in r.PET_TEMPLATES:
            copy = self.db.execute('select * from NpcTemplate where TemplateId=? and Model=(select Model from NpcTemplate where TemplateId=?'
                                   + (' and Name=?)' if source_name else ' limit 1)'),
                                   (template_id, source, source_name) if source_name else (template_id, source)).fetchone()
            self.assertIsNotNone(copy, name)
            self.assertEqual((copy['Name'], copy['PackageID']), (name, r.PACKAGE))
        self.assertEqual(len(template(self.spell('Call Nature Sage', 'Druid Nature Spec'))), 4)  # tree, bear, lynx, wolf

        heavy = self.spell('Heavy Spirit', 'Arboreal Mastery')
        self.assertEqual((heavy['Type'], heavy['LifeDrainReturn'], self.by_id(heavy['SubSpellID'])['Damage'], self.by_id(heavy['SubSpellID'])['Name']),
                         ('Bomber', 730, 133.8, 'Heavy Spirit (Damage)'))
        self.assertEqual(self.by_id(self.spell('Spirit of Guile', 'Creeping Path Spec (Live)')['SubSpellID'])['DamageType'], r.MATTER)
        menace = self.spell("Forest's Menace", 'Creeping Path Spec (Live)')
        spores = self.by_id(menace['SubSpellID'])
        self.assertEqual((template(menace)[0]['Name'], spores['Type'], self.by_id(spores['SubSpellID'])['Type'], self.by_id(spores['SubSpellID'])['Damage']),
                         ("forest's menace", 'Disease', 'DamageOverTime', 15))
        self.assertEqual(self.by_id(self.spell('Grove Druid', 'Creeping Path Spec (Live)')['SubSpellID'])['Value'], 215)
        self.assertEqual(self.by_id(self.spell('Shroom of Life', 'Creeping Path Spec (Live)')['SubSpellID'])['Type'], 'HealOverTime')
        for name, line in [('Guardian of the Forest', 'Arboreal Mastery'), ('Heart of the Grove', 'Creeping Path Spec (Live)'),
                           ('Harbinger of War', 'Verdant Path Spec (Live)')]:
            pet = self.spell(name, line)
            self.assertEqual((pet['Type'], pet['Value'], pet['Damage'], pet['LineLevel']), ('SummonAnimistPet', 50, -100, 40), name)
        warrior = self.spell('Spirit Warrior', 'Summoning (Live)')
        self.assertEqual((warrior['Type'], template(warrior)[0]['Name'], template(warrior)[0]['Abilities']), ('SummonSpiritFighter', 'spirit warrior', 'Intercept|1'))
        gates = self.spell('Gates of Valhalla', 'Spirit Enhancement (Live)')
        einherjar = self.by_id(gates['SubSpellID'])
        self.assertEqual((gates['Type'], gates['Frequency'], einherjar['Type'], template(einherjar)[0]['Name']),
                         ('TimedPulseArea', 120, 'SummonTheurgistPet', 'fallen einherjar'))
        self.assertEqual(self.spell('Summon Grove Guardian', 'Druid Nature Magic')['Value'], 34)
        self.assertEqual(template(self.spell('Underhill Stalker', 'Enchantment'))[0]['Name'], 'underhill stalker')
        # The stock pets live dropped stay (owner's call).
        self.assertIsNotNone(self.spell('Summon Spirit Champion', 'Summoning'))
        self.assertIsNotNone(self.spell('Call Greater Nature Spirit', 'Druid Nature Spec'))

    def test_reapplying_is_stable_and_out_of_the_death_knight_block(self):
        with self.db:
            self.assertEqual(r.apply(self.db), self.result)
        tooltips = [x[0] for x in self.db.execute('select TooltipId from Spell where PackageID=?', (r.PACKAGE,))]
        self.assertFalse(any(r.RESERVED_TOOLTIPS[0] <= t <= r.RESERVED_TOOLTIPS[1] for t in tooltips))
        self.assertTrue(all(t <= 32767 for t in tooltips))


if __name__ == '__main__':
    unittest.main()
