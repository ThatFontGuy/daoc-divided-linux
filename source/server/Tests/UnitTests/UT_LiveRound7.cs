using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>The seventh live pass: grapples, Overshadow, Chain Lightning, Speedwarp, the enchantments and Blight Surge.</summary>
    [TestFixture]
    public class UT_LiveRound7
    {
        private static Spell Of(eSpellType type, string target = "Self") =>
            new(new DbSpell { SpellID = 1, Type = type.ToString(), Target = target, Value = 3, Duration = 10 }, 1);

        [Test]
        public void EverySpellTypeMapsToItsOwnEffect()
        {
            foreach (eSpellType type in new[] { eSpellType.IceGrip, eSpellType.FlameCocoon, eSpellType.BattleControl, eSpellType.AllyStealth,
                                                eSpellType.Speedwarp, eSpellType.StyleZeal, eSpellType.MeleeTruth, eSpellType.Siegebreaker,
                                                eSpellType.BlightSurge })
                Assert.That(EffectHelper.GetEffectFromSpell(Of(type)).ToString(), Is.EqualTo(type.ToString()), type.ToString());
        }

        [Test]
        public void LookupsAreEmptyWithoutAnOwner()
        {
            Assert.That(LiveRound7.Has(null, eEffect.IceGrip), Is.False);
            Assert.That(LiveRound7.BlocksMelee(null, null), Is.False);
            Assert.That(SpeedwarpSpellHandler.IsWarped(null), Is.False);
            Assert.That(StyleZealSpellHandler.StyleFactor(null), Is.EqualTo(1.0));
            Assert.That(MeleeTruthSpellHandler.Strikes(null), Is.False);
            Assert.That(SiegebreakerSpellHandler.IsSiegeObject(null), Is.False);
            Assert.DoesNotThrow(() => LiveRound7.OnAttacked(null, null));
            Assert.DoesNotThrow(() => StyleZealSpellHandler.OnAttacked(null, null));
        }

        [Test]
        public void ChainLightningLosesATenthAJump()
        {
            Assert.That(ChainDirectDamageSpellHandler.Factor(0), Is.EqualTo(1.0));
            Assert.That(ChainDirectDamageSpellHandler.Factor(4), Is.EqualTo(0.6).Within(1e-9));
            Assert.That(ChainDirectDamageSpellHandler.Factor(20), Is.Zero);
        }

        [Test]
        public void ZealSharesTheStyledHitBetweenTheOtherMembers()
        {
            Assert.That(StyleZealSpellHandler.Share(300, 3), Is.EqualTo(100));
            Assert.That(StyleZealSpellHandler.Share(300, 0), Is.Zero);
        }
    }
}
