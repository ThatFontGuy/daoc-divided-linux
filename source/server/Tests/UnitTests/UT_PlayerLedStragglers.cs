using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Events;
using DOL.GS;
using DOL.GS.ServerProperties;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_PlayerLedStragglers
    {
        private static PlayerLedStragglers.Separation Fresh() => new();

        [Test]
        public void ABotBesideItsLeaderIsNeverStranded()
        {
            var separation = Fresh();
            Assert.That(separation.Observe(true, 200, 0), Is.False);
            Assert.That(separation.Observe(true, PlayerLedStragglers.FollowRadius, 600_000), Is.False);
        }

        [Test]
        public void AWalkThatKeepsGettingCloserIsLeftAlone()
        {
            var separation = Fresh();
            for (long now = 0; now <= 300_000; now += 10_000)
                Assert.That(separation.Observe(true, 7_500 - now / 50f, now), Is.False, $"at {now} ms");
        }

        [Test]
        public void AWalkTooLongToBeFollowingIsStrandedEvenWhileItGetsCloser()
        {
            var separation = Fresh();
            Assert.That(separation.Observe(true, 130_000, 0), Is.False);
            Assert.That(separation.Observe(true, 124_000, PlayerLedStragglers.NoProgressMilliseconds), Is.True);
        }

        [Test]
        public void AWalkThatStopsGettingCloserIsStrandedAfterTheWait()
        {
            var separation = Fresh();
            Assert.That(separation.Observe(true, 5_000, 0), Is.False);
            Assert.That(separation.Observe(true, 5_000, PlayerLedStragglers.NoProgressMilliseconds - 1), Is.False);
            Assert.That(separation.Observe(true, 5_000, PlayerLedStragglers.NoProgressMilliseconds), Is.True);
        }

        [Test]
        public void ALeaderInAnotherRegionStrandsTheBotQuickly()
        {
            var separation = Fresh();
            Assert.That(separation.Observe(false, float.MaxValue, 0), Is.False);
            Assert.That(separation.Observe(false, float.MaxValue, PlayerLedStragglers.OtherRegionMilliseconds), Is.True);
        }

        [Test]
        public void ReachingTheLeaderStartsTheCountAgain()
        {
            var separation = Fresh();
            separation.Observe(true, 5_000, 0);
            separation.Observe(true, 300, 20_000);
            Assert.That(separation.Observe(true, 5_000, 25_000), Is.False);
            Assert.That(separation.Observe(true, 5_000, 25_000 + PlayerLedStragglers.NoProgressMilliseconds), Is.True);
        }

        [Test]
        public void RemovingAHandlerThatWasNeverAddedDoesNothing()
        {
            // Playtest 2026-10-31: StormSovereignEffect stops only subscribed to one of two events and threw, skipping its cleanup.
            int calls = 0;
            DOLEventHandler added = (_, _, _) => calls++;
            DOLEventHandler other = (_, _, _) => { };
            var handlers = new DOLEventHandlerCollection();

            handlers.AddHandler(GameLivingEvent.AttackFinished, added);
            Assert.DoesNotThrow(() => handlers.RemoveHandler(GameLivingEvent.AttackFinished, other));
            Assert.DoesNotThrow(() => handlers.RemoveHandler(GameLivingEvent.AttackedByEnemy, other));

            handlers.Notify(GameLivingEvent.AttackFinished, null, null);
            Assert.That(calls, Is.EqualTo(1), "the handler that was added stays");

            handlers.RemoveHandler(GameLivingEvent.AttackFinished, added);
            handlers.Notify(GameLivingEvent.AttackFinished, null, null);
            Assert.That(calls, Is.EqualTo(1));
        }

        [Test]
        public void ABotAlreadyInYourGroupDoesNotAskForAnInvite()
        {
            DOL.Logging.LoggerManager.InitializeWithExplicitLibrary(null, DOL.Logging.LogLibrary.None);
            using var server = new EpicTestServerScope();
            var group = (Group)RuntimeHelpers.GetUninitializedObject(typeof(Group));
            var bot = (GameBot)RuntimeHelpers.GetUninitializedObject(typeof(GameBot));
            var player = (GamePlayer)RuntimeHelpers.GetUninitializedObject(typeof(GamePlayer));
            typeof(GameLiving).GetProperty(nameof(GameLiving.Group))!.SetValue(bot, group);
            typeof(GameLiving).GetProperty(nameof(GameLiving.Group))!.SetValue(player, group);

            for (int seed = 0; seed < 20; seed++)
            {
                string reply = AutonomousBotChatCoordinator.JoinReply(bot, player, new System.Random(seed));
                Assert.That(reply, Does.Not.Contain("inv").And.Not.Contain("invite"), reply);
            }
        }
    }
}
