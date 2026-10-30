"""Read-only checks of the live hybrid-line spells on a private copy of the modern test world."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3
import unittest
import hybrid_lines as h

REPO = Path(__file__).resolve().parents[2]
WORLD = REPO / 'artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db'
SPELL_TYPES = REPO / 'source/server/GameServer/Enums/eSpellType.cs'


class HybridLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORLD.is_file():
            raise unittest.SkipTest('Modern test world is not available')
        cls.db = sqlite3.connect(':memory:'); cls.db.row_factory = sqlite3.Row
        with closing(sqlite3.connect(WORLD.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            src.backup(cls.db)
        cls.before = cls.db.execute("select count(*) from LineXSpell l join Spell s on s.SpellID=l.SpellID where l.LineName='Stormcalling' "
                                    "and coalesce(s.PackageID,'')<>?", (h.PACKAGE,)).fetchone()[0]
        with cls.db:
            cls.result = h.apply(cls.db)

    def rows(self):
        return list(self.db.execute('select s.*, l.LineName, l.Level as LineLevel from Spell s join LineXSpell l on l.SpellID=s.SpellID '
                                    'where s.PackageID=?', (h.PACKAGE,)))

    def test_reapplying_is_stable_and_adds_only_new_ranks(self):
        with self.db:
            self.assertEqual(h.apply(self.db), self.result)
        after = self.db.execute("select count(*) from LineXSpell where LineName='Stormcalling'").fetchone()[0]
        self.assertEqual(after, self.before + 18)
        self.assertEqual(len(self.rows()), len(h.definitions()))

    def test_ids_tooltips_and_art_are_valid(self):
        types = set(re.findall(r'^\s*(\w+),', SPELL_TYPES.read_text(), re.M))
        for row in self.rows():
            self.assertTrue(h.FIRST <= row['SpellID'] <= h.LAST)
            self.assertLessEqual(row['TooltipId'], 32767, 'client reads tooltip IDs as signed 16-bit')
            self.assertIn(row['Type'], types, row['Name'])
            self.assertTrue(self.db.execute('select 1 from Spell where SpellID=? and PackageID<>?', (row['ClientEffect'], h.PACKAGE)).fetchone(),
                            f"{row['Name']} borrows art from an existing spell")
        self.assertFalse(self.db.execute('select 1 from Spell where TooltipId between ? and ? and PackageID<>?',
                                         (h.TOOLTIP_BASE, h.TOOLTIP_BASE + h.LAST - h.FIRST, h.PACKAGE)).fetchone())

    def test_live_values_for_each_family(self):
        by_name = {r['Name']: r for r in self.rows()}
        self.assertEqual((by_name['Banish Energy']['LineLevel'], by_name['Banish Energy']['Value'], by_name['Banish Energy']['Radius']), (43, 30, 400))
        self.assertEqual((by_name['Ultimate Bewildering']['Value'], by_name['Ultimate Bewildering']['RecastDelay'], by_name['Ultimate Bewildering']['CastTime']), (69, 20, 0))
        chant = by_name["Thor's Tenacity"]
        self.assertEqual((chant['Target'], chant['Pulse'], chant['Frequency'], chant['Duration'], chant['Value']), ('Group', 1, 50, 6, 25))
        self.assertEqual((by_name["Mjollnir's Sagacity"]['LineLevel'], by_name["Mjollnir's Sagacity"]['Value']), (50, 10))


    def test_thousand_storms_reaches_thane_and_valkyrie_at_40(self):
        grants = sorted(tuple(r) for r in self.db.execute("select Spec,SpecLevel,AbilityLevel from SpecXAbility where AbilityKey='Call of a thousand storms'"))
        self.assertEqual(grants, [('ThaneCareer', 40, 1), ('ValkyrieCareer', 40, 1)])
        row = self.db.execute("select IconID,InternalID from Ability where KeyName='Call of a thousand storms'").fetchone()
        self.assertEqual((row['IconID'], row['InternalID']), (3066, 3150))


    def test_batch_families_renames_and_abilities(self):
        by_name = {r['Name']: r for r in self.rows()}
        self.assertEqual({r['LineName'] for r in self.rows()}, {'Stormcalling', 'Battlesongs', 'Valor', 'Soulrending', 'Instruments', 'Chants'})
        circle = by_name['Circle of Despair']
        self.assertEqual((circle['Type'], circle['Range'], circle['Radius'], circle['Damage']), ('DirectDamage', 0, 750, 25.0), 'PBAoE')
        self.assertEqual((by_name['Soul Drain']['Damage'], by_name['Soul Drain']['LifeDrainReturn']), (109.0, 60))
        self.assertEqual(by_name['Reincarnate']['ResurrectHealth'], 25)
        # Each new family has a group of its own, so the hybrid list never merges it with an older local family.
        groups = {}
        for r in self.rows():
            if r['SpellGroup']:
                groups.setdefault(r['SpellGroup'], set()).add(r['Type'])
        self.assertTrue(all(len(types) == 1 for types in groups.values()))
        self.assertFalse(self.db.execute('select 1 from Spell where SpellGroup in (%s) and PackageID<>?' % ','.join('?' * len(groups)),
                                         (*groups, h.PACKAGE)).fetchone())
        for line, old, new, _ in h.RENAMES:
            names = {r[0] for r in self.db.execute('select s.Name from LineXSpell l join Spell s on s.SpellID=l.SpellID where l.LineName=?', (line,))}
            self.assertIn(new, names); self.assertNotIn(old, names)
        reaver = {r[0]: r[1] for r in self.db.execute("select AbilityKey,SpecLevel from SpecXAbility where Spec='ReaverCareer' and AbilityKey in ('Intercept','Stoicism')")}
        self.assertEqual(reaver, {'Intercept': 25, 'Stoicism': 35})
        self.assertGreater(self.db.execute("select count(*) from SpecXAbility where AbilityKey='Intercept' and Spec<>'ReaverCareer'").fetchone()[0], 5,
                           "other classes keep Intercept")


    def test_class_abilities_reach_live_levels_without_touching_other_classes(self):
        def grants(key, spec, cls=0):
            return sorted((r[0], r[1]) for r in self.db.execute('select SpecLevel,AbilityLevel from SpecXAbility where AbilityKey=? and Spec=? and ClassId=?',
                                                                (key, spec, cls)))
        for career in h.TANKS:
            self.assertEqual(grants('Fury', career), [(50, 0)])
            self.assertEqual(grants('Memories of War', career)[-1], (50, 10))
        self.assertEqual(grants('Safe Fall', 'Stealth', 9), [(10, 1), (20, 2), (30, 3), (38, 4), (48, 5)])
        self.assertEqual(grants('Safe Fall', 'Stealth', 25), [(10, 1)])
        self.assertEqual(grants('Safe Fall', 'Stealth', 4), [(10, 1), (20, 2), (30, 3), (40, 4), (50, 5)], 'the Minstrel keeps its ranks')
        self.assertEqual(grants('Guard', 'WardenCareer'), [(15, 3)])
        self.assertEqual(grants('Intercept', 'MaulerCareer'), [(12, 0)])
        shouts = {r['SpellID']: r for r in self.db.execute('select * from Spell where PackageID=?', (h.ABILITY_PACKAGE,))}
        self.assertEqual(set(shouts), {14373, 14374, 14375, 14376, 14377})
        self.assertEqual((shouts[14374]['Value'], shouts[14373]['Value'], shouts[14375]['Value']), (45, 100, 3))
        self.assertTrue(all(r['TooltipId'] <= 32767 for r in shouts.values()))


if __name__ == '__main__':
    unittest.main()
