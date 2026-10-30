using DOL.GS;
using DOL.GS.SkillHandler;
using DOL.Database;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Siege Resistance (33%), the siege-protection songs (10-50%) and Memories of War (10% at 50).</summary>
    [TestFixture]
    public class UT_SiegeDefense
    {
        [Test]
        public void ResistanceAndSongsCutSiegeDamage()
        {
            Assert.That(SiegeDefense.Apply(1000, false, 0), Is.EqualTo(1000));
            Assert.That(SiegeDefense.Apply(1000, true, 0), Is.EqualTo(670), "33% Siege Resistance leaves 670 of 1,000");
            Assert.That(SiegeDefense.Apply(1000, false, 50), Is.EqualTo(500), "the top song removes half");
            Assert.That(SiegeDefense.Apply(1000, true, 50), Is.EqualTo(335), "both apply in turn");
            Assert.That(SiegeDefense.Apply(1000, false, 150), Is.Zero);
        }

        [Test]
        public void MemoriesOfWarReachesTenPercentAtFifty()
        {
            var memories = new MemoriesOfWar(new DbAbility { KeyName = Abilities.MemoriesOfWar, Name = "Memories of War" }, 10);
            Assert.That(memories.GetAmountForLevel(1), Is.EqualTo(1));
            Assert.That(memories.GetAmountForLevel(10), Is.EqualTo(10));
            Assert.That(memories.GetAmountForLevel(12), Is.EqualTo(10));
        }
    }
}
