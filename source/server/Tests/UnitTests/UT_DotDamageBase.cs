using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_DotDamageBase
    {
        private static Spell Dot(string type, double damage) =>
            new(new DbSpell { SpellID = 1, Type = type, Target = "Enemy", Damage = damage }, 1);

        private static SpellLine Line(string keyName) => new(keyName, keyName, keyName, true);

        [TestCase(121)]
        [TestCase(0)]
        public void SpellLineDotTicksForItsRow(double damage)
        {
            DoTSpellHandler handler = new(null, Dot("DamageOverTime", damage), Line("Telekinesis"));
            Assert.That(handler.CalculateDamageBase(null), Is.EqualTo(damage));
        }

        [Test]
        public void WarlockChainDotTicksForItsRow()
        {
            WarlockChainDotHandler handler = new(null, Dot("WarlockChainDot", 215), Line("Witchcraft"));
            Assert.That(handler.CalculateDamageBase(null), Is.EqualTo(215));
        }

        [Test]
        public void StyleEffectDotStillGoesThroughWeaponSkillScaling()
        {
            // The base method reads the caster's weapon skill, which a null caster cannot give.
            DoTSpellHandler handler = new(null, Dot("ArcheryDoT", 64), Line(GlobalSpellsLines.Combat_Styles_Effect));
            Assert.Throws<System.NullReferenceException>(() => handler.CalculateDamageBase(null));
        }
    }
}
