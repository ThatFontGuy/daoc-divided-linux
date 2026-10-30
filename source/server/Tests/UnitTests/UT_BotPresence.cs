using System;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests.Gameserver
{
    [TestFixture]
    public class UT_BotPresence
    {
        private static readonly DateTime T0 = new(2026, 1, 1, 12, 0, 0, DateTimeKind.Utc);

        [Test]
        public void NoPlayerSinceStart_MeansNoPlayers()
        {
            Assert.That(BotPresence.ComputeNoPlayers(T0, long.MinValue, false, 120, out long seen), Is.True);
            Assert.That(seen, Is.EqualTo(long.MinValue));
        }

        [Test]
        public void PlayerPresent_ClearsNoPlayers_AndRemembersTheTime()
        {
            Assert.That(BotPresence.ComputeNoPlayers(T0, long.MinValue, true, 120, out long seen), Is.False);
            Assert.That(seen, Is.EqualTo(T0.Ticks));
        }

        [Test]
        public void AfterPlayerLeaves_BotsStayUntilGraceEnds()
        {
            Assert.That(BotPresence.ComputeNoPlayers(T0.AddSeconds(119), T0.Ticks, false, 120, out _), Is.False);
            Assert.That(BotPresence.ComputeNoPlayers(T0.AddSeconds(120), T0.Ticks, false, 120, out _), Is.True);
        }
    }
}
