using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>
    /// Owner 2026-11-02: a companion or an autonomous bot trains real specializations, so its spell lines are read at
    /// that level; a monster keeps the three-quarter estimate. The ceiling used to be 38 at level 50, which dropped
    /// every rank above it - the Minstrel's 204% speed song needs Instruments 43.
    /// </summary>
    [TestFixture]
    public class UT_BotSpellLineLevel
    {
        [Test]
        public void ABotWithATrainedSpecReadsTheWholeLine()
        {
            Assert.That(BotSpellLineLevel.For(true, 50, 50), Is.EqualTo(50));
            Assert.That(BotSpellLineLevel.For(true, 43, 50), Is.EqualTo(43));
        }

        [Test]
        public void AMonsterKeepsTheThreeQuarterEstimate()
        {
            Assert.That(BotSpellLineLevel.For(false, 50, 50), Is.EqualTo(38));
            Assert.That(BotSpellLineLevel.For(false, 50, 40), Is.EqualTo(30));
        }

        [Test]
        public void TheLineNeverExceedsTheBotsOwnLevelAndNeverFallsBelowOne()
        {
            Assert.That(BotSpellLineLevel.For(true, 60, 44), Is.EqualTo(44));
            Assert.That(BotSpellLineLevel.For(true, 0, 50), Is.EqualTo(1));
            Assert.That(BotSpellLineLevel.For(true, -5, 50), Is.EqualTo(1));
            Assert.That(BotSpellLineLevel.For(false, 0, 1), Is.EqualTo(1));
        }
    }
}
