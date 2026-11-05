using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_GroupAblativeEffect
    {
        [Test]
        public void BarkLineCountsAsAnAblative()
        {
            Spell bark = new(new DbSpell { SpellID = 1, Type = "GroupAblativeHalfOnCaster", Target = "Group" }, 1);
            Assert.That(EffectHelper.GetEffectFromSpell(bark), Is.EqualTo(eEffect.AblativeArmor));
        }
    }
}
