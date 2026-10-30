using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_SpellLineMerge
    {
        private static Spell Rank(int id, int level) => new(new DbSpell { SpellID = id, Type = "DirectDamage", Target = "Enemy" }, level);

        private readonly SpellLine _cursing = new("Cursing", "Cursing", "Cursing", true);
        private readonly SpellLine _cursingLive = new("Cursing (Live)", "Cursing (Live)", "Cursing", true);
        private readonly SpellLine _hexing = new("Hexing", "Hexing", "Hexing", false);
        private readonly SpellLine _hexing130 = new("Hexing (1.130)", "Hexing (1.130)", "Hexing", false);
        private readonly SpellLine _hexingLive = new("Hexing (Live)", "Hexing (Live)", "Hexing", false);
        private readonly SpellLine _shieldsLive = new("Warrior Shields (Live)", "Warrior Shields (Live)", "Shields", false);
        private readonly SpellLine _mending = new("Mending", "Mending", "Mending", true);

        private List<Spell> _curses, _cursesLive, _hexes, _hexes130, _hexesLive, _shields;

        [SetUp]
        public void SetUp()
        {
            _curses = new() { Rank(1, 1), Rank(2, 10), Rank(3, 20) };
            _cursesLive = new() { Rank(11, 10), Rank(12, 20), Rank(13, 25) };
            _hexes = new() { Rank(21, 5), Rank(22, 6), Rank(23, 7) };
            _hexes130 = new() { Rank(31, 7), Rank(32, 8) };
            _hexesLive = new() { Rank(41, 7) };
            _shields = new() { Rank(51, 30) };
            SpellLineMerge.Reset(new[]
            {
                ("Cursing", (IEnumerable<Spell>)_curses), ("Cursing (Live)", _cursesLive),
                ("Hexing", _hexes), ("Hexing (1.130)", _hexes130), ("Hexing (Live)", _hexesLive),
                ("Warrior Shields (Live)", _shields), ("Mending", new[] { Rank(61, 1) }),
            });
        }

        [TearDown]
        public void TearDown() => SpellLineMerge.Reset();

        [Test]
        public void BaseKeyStripsOnlyMigrationSuffixes()
        {
            Assert.That(SpellLineMerge.BaseKey("Valewalker Arb Path Spec (1.130)"), Is.EqualTo("Valewalker Arb Path Spec"));
            Assert.That(SpellLineMerge.BaseKey("Cursing (Live)"), Is.EqualTo("Cursing"));
            Assert.That(SpellLineMerge.BaseKey("Spirit Enhancement (1.130 II)"), Is.EqualTo("Spirit Enhancement"));
            Assert.That(SpellLineMerge.BaseKey("Bone Army (Commanders)"), Is.EqualTo("Bone Army (Commanders)"));
            Assert.That(SpellLineMerge.IsExtraLine("Mending"), Is.False);
        }

        [Test]
        public void StockSpellsKeepTheirLevelAndExtrasTakeFreeSlotsNotAboveTheirOwn()
        {
            var slots = SpellLineMerge.AssignClientSlots("Hexing", new[]
            {
                ("Hexing (Live)", (IEnumerable<Spell>)_hexesLive), ("Hexing", _hexes), ("Hexing (1.130)", _hexes130),
            });
            // Stock 5, 6, 7 stay; the extras at 7 fall back to 4 and 3; the extra at 8 keeps 8.
            Assert.That(slots[21], Is.EqualTo(5));
            Assert.That(slots[22], Is.EqualTo(6));
            Assert.That(slots[23], Is.EqualTo(7));
            Assert.That(slots[31], Is.EqualTo(4));
            Assert.That(slots[41], Is.EqualTo(3));
            Assert.That(slots[32], Is.EqualTo(8));
            Assert.That(slots.Values.Distinct().Count(), Is.EqualTo(slots.Count));
        }

        [Test]
        public void ExtrasGoAboveWhenNoLowerSlotIsFree()
        {
            var slots = SpellLineMerge.AssignClientSlots("A", new[]
            {
                ("A", (IEnumerable<Spell>)new[] { Rank(1, 1), Rank(2, 2) }), ("A (Live)", new[] { Rank(3, 2) }),
            });
            Assert.That(slots[3], Is.EqualTo(3));
        }

        [Test]
        public void ClientSeesOneLinePerSpecializationAndEachSpellResolvesToItsRealLine()
        {
            var lines = new List<(SpellLine, List<Skill>)>
            {
                (_cursing, _curses.Cast<Skill>().ToList()), (_cursingLive, _cursesLive.Cast<Skill>().ToList()),
                (_mending, new List<Skill>()),
                (_hexing, _hexes.Cast<Skill>().ToList()), (_hexing130, _hexes130.Cast<Skill>().ToList()), (_hexingLive, _hexesLive.Cast<Skill>().ToList()),
            };

            var view = StormforgedRules.ClientSpellLines(lines);
            Assert.That(view.Select(line => line.Item1), Is.EqualTo(new[] { _cursing, _mending, _hexing }));
            Assert.That(view[0].Item2, Is.EquivalentTo(_curses.Concat(_cursesLive)));
            Assert.That(view[2].Item2, Has.Count.EqualTo(6));

            // What UseSpellHandler / DetailDisplayHandler do: find the spell by client level, then its real line.
            foreach (var (clientLine, skills) in view)
            {
                var levels = skills.OfType<Spell>().Select(spell => StormforgedRules.ClientLevel(clientLine, spell)).ToList();
                Assert.That(levels, Is.Unique, clientLine.Name);
                Assert.That(levels, Is.Ordered, clientLine.Name);
                foreach (Spell spell in skills.OfType<Spell>())
                {
                    int level = StormforgedRules.ClientLevel(clientLine, spell);
                    Spell found = skills.OfType<Spell>().First(skill => StormforgedRules.ClientLevel(clientLine, skill) == level);
                    Assert.That(found, Is.SameAs(spell));
                    SpellLine real = lines.First(line => line.Item2.Contains(spell)).Item1;
                    Assert.That(StormforgedRules.ServerLine(lines, clientLine, spell), Is.SameAs(real));
                }
            }
        }

        [Test]
        public void ExtraLineWithoutStockLineDropsItsSuffixForTheClient()
        {
            var lines = new List<(SpellLine, List<Skill>)> { (_shieldsLive, _shields.Cast<Skill>().ToList()) };
            var view = StormforgedRules.ClientSpellLines(lines);
            Assert.That(view[0].Item1.Name, Is.EqualTo("Warrior Shields"));
            Assert.That(view[0].Item1.InternalID, Is.EqualTo(_shieldsLive.InternalID));
            Assert.That(StormforgedRules.ServerLine(lines, view[0].Item1, _shields[0]), Is.SameAs(_shieldsLive));
            Assert.That(_shieldsLive.Name, Is.EqualTo("Warrior Shields (Live)"));
        }

        [Test]
        public void ListsWithoutExtraLinesAreUnchanged()
        {
            var lines = new List<(SpellLine, List<Skill>)> { (_mending, new List<Skill>()), (_hexing, _hexes.Cast<Skill>().ToList()) };
            Assert.That(StormforgedRules.ClientSpellLines(lines), Is.SameAs(lines));
            Assert.That(StormforgedRules.ClientLevel(_mending, _hexes[0]), Is.EqualTo(_hexes[0].Level));
            Assert.That(StormforgedRules.ServerLine(lines, _mending, _hexes[0]), Is.SameAs(_mending));
        }
    }
}
