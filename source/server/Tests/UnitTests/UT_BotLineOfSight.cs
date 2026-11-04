using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Owner 2026-10-31: the bots no longer cast through the keep walls at targets that are not players.</summary>
    [TestFixture]
    public class UT_BotLineOfSight
    {
        [TestCase(false, 1000, true, true)]     // a bot or a monster far enough, same zone: check the line
        [TestCase(true, 1000, true, false)]     // a player: the player's client answers
        [TestCase(false, 149, true, false)]     // touching: always in view
        [TestCase(false, 150, true, false)]
        [TestCase(false, 151, true, true)]
        [TestCase(false, 1000, false, false)]   // another zone: no check
        public void OnlyAFarTargetThatIsNotAPlayerIsChecked(bool targetIsPlayer, int distance, bool sameZone, bool expected) =>
            Assert.That(BotLineOfSight.ShouldCheck(targetIsPlayer, distance, sameZone), Is.EqualTo(expected));

        [Test]
        public void NothingIsBlockedWithoutACasterOrATarget()
        {
            Assert.That(BotLineOfSight.Blocks(null, null), Is.False);
        }
    }
}
