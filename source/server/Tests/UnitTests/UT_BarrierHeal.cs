using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Live barrier heals: the heal, then a 10 s barrier absorbing all damage up to the heal's Damage.</summary>
    [TestFixture]
    public class UT_BarrierHeal
    {
        [Test]
        public void BarrierAbsorbsAllDamageUpToTheHealsDamageForTenSeconds()
        {
            var heal = new Spell(new DbSpell { SpellID = 75123, Name = "Barrier Refocillation", Type = eSpellType.BarrierHeal.ToString(),
                Target = "Realm", Value = 302, Damage = 100, Icon = 1, ClientEffect = 2 }, 46);
            Spell barrier = BarrierHealSpellHandler.Barrier(heal);
            Assert.That(barrier.SpellType, Is.EqualTo(eSpellType.BothAblativeArmor));
            Assert.That((barrier.Value, barrier.Damage), Is.EqualTo((100.0, 100.0)), "absorbs 100% up to the heal's 100");
            Assert.That(barrier.Duration, Is.EqualTo(BarrierHealSpellHandler.BARRIER_SECONDS * 1000));
            Assert.That(barrier.ID, Is.EqualTo(75123001));
            Assert.That(heal.IsBuff, Is.False, "the heal itself has no duration, so bots treat it as a heal");
            Assert.That(BarrierHealSpellHandler.Barrier(heal), Is.SameAs(barrier));
        }
    }
}
