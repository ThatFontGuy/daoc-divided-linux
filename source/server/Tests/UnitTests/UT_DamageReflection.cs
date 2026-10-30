using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Cleric reflection and the Skald wards: the parts that need no world.</summary>
    [TestFixture]
    public class UT_DamageReflection
    {
        private static Spell Of(eSpellType type) => new(new DbSpell { SpellID = 1, Type = type.ToString(), Target = "Enemy" }, 1);

        [Test]
        public void NothingIsReflectedWithoutAHitOrAnOwner()
        {
            Assert.That(DamageReflectionSpellHandler.Reflected(null, 100), Is.Zero);
        }

        [Test]
        public void WardsStopOnlyMesmerizeAndMagicalStun()
        {
            Assert.That(CrowdControlGuardSpellHandler.WardKind(Of(eSpellType.Mesmerize)), Is.EqualTo(CrowdControlGuardSpellHandler.MEZ));
            Assert.That(CrowdControlGuardSpellHandler.WardKind(Of(eSpellType.Stun)), Is.EqualTo(CrowdControlGuardSpellHandler.STUN));
            Assert.That(CrowdControlGuardSpellHandler.WardKind(Of(eSpellType.StyleStun)), Is.Zero, "style stuns are not warded");
            Assert.That(CrowdControlGuardSpellHandler.WardKind(Of(eSpellType.SpeedDecrease)), Is.Zero);
            Assert.That(CrowdControlGuardSpellHandler.Blocks(Of(eSpellType.Mesmerize), null), Is.False);
        }
    }
}
