using System;
using System.Linq;
using NUnit.Framework;

namespace DOL.GS.Tests
{
    [TestFixture]
    public sealed class UT_AutonomousSharedDeathSpots
    {
        private static readonly DateTime Now = new(2026, 10, 28, 12, 0, 0, DateTimeKind.Utc);

        private static AutonomousSharedDeathSpots.Death At(long bot, int level, int x, double minutesAgo = 5) =>
            new(bot, level, 1, x, 1000, Now.AddMinutes(-minutesAgo));

        [Test]
        public void FiveDeathsOfThreeBotsMakeASpot()
        {
            var deaths = new[] { At(1, 8, 0), At(2, 8, 100), At(3, 8, 200), At(1, 8, 300), At(2, 8, 400) };
            Assert.That(AutonomousSharedDeathSpots.Spots(deaths, 1, 8, Now), Has.Count.EqualTo(1));
        }

        [Test]
        public void OneUnluckyBotIsNotWordOfMouth()
        {
            var deaths = Enumerable.Range(0, 8).Select(i => At(1, 8, i * 50)).Append(At(2, 8, 0)).ToArray();
            Assert.That(AutonomousSharedDeathSpots.Spots(deaths, 1, 8, Now), Is.Empty);
        }

        [Test]
        public void OnlyBotsNearTheVictimsLevelAvoidIt()
        {
            var deaths = new[] { At(1, 8, 0), At(2, 8, 100), At(3, 8, 200), At(4, 8, 300), At(5, 8, 400) };
            Assert.That(AutonomousSharedDeathSpots.Spots(deaths, 1, 11, Now), Has.Count.EqualTo(1));
            Assert.That(AutonomousSharedDeathSpots.Spots(deaths, 1, 12, Now), Is.Empty);
            Assert.That(AutonomousSharedDeathSpots.Spots(deaths, 1, 3, Now), Has.Count.EqualTo(1));
        }

        [Test]
        public void OldDeathsAndOtherRegionsAreForgotten()
        {
            var old = new[] { At(1, 8, 0, 130), At(2, 8, 100, 130), At(3, 8, 200, 130), At(4, 8, 300, 130), At(5, 8, 400, 130) };
            Assert.That(AutonomousSharedDeathSpots.Spots(old, 1, 8, Now), Is.Empty);
            var fresh = new[] { At(1, 8, 0), At(2, 8, 100), At(3, 8, 200), At(4, 8, 300), At(5, 8, 400) };
            Assert.That(AutonomousSharedDeathSpots.Spots(fresh, 2, 8, Now), Is.Empty);
        }

        [Test]
        public void SpreadOutDeathsAreNotOneSpot()
        {
            var deaths = Enumerable.Range(0, 6).Select(i => At(i, 8, i * 2_000)).ToArray();
            Assert.That(AutonomousSharedDeathSpots.Spots(deaths, 1, 8, Now), Is.Empty);
        }

        [TestCase(true, false, ConColor.GREEN, 70)]
        [TestCase(true, false, ConColor.YELLOW, 150)]
        [TestCase(false, true, ConColor.GREEN, 130)]
        [TestCase(false, true, ConColor.YELLOW, 60)]
        [TestCase(false, true, ConColor.BLUE, 100)]
        [TestCase(false, false, ConColor.YELLOW, 100)]
        public void CampConTasteByRole(bool caster, bool melee, ConColor con, int expected)
        {
            Assert.That(AutonomousBotDecisionEngine.RoleConWeightPercent(caster, melee, con), Is.EqualTo(expected));
        }
    }
}
