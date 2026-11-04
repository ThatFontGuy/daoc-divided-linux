using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading.Channels;
using DOL.GS;
using NUnit.Framework;
using static DOL.GS.CombatNumbers;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_CombatNumbers
    {
        private EpicTestServerScope _server;

        [SetUp] public void Setup() => _server = new EpicTestServerScope();
        [TearDown] public void Cleanup() => _server.Dispose();

        private sealed class TestPlayer : GamePlayer
        {
            private TestPlayer() : base(null, null) { }
        }

        private static GamePlayer Player() => (GamePlayer)RuntimeHelpers.GetUninitializedObject(typeof(TestPlayer));
        private static GameNPC Npc() => (GameNPC)RuntimeHelpers.GetUninitializedObject(typeof(GameNPC));

        [Test]
        public void YourHitsShowAsYoursAndTheTargetPlayerSeesThemAsTaken()
        {
            GamePlayer you = Player();
            GamePlayer enemy = Player();

            var viewers = Viewers(you, false, null, enemy);

            Assert.That(viewers, Is.EqualTo(new[] { (you, true, Who.Self), (enemy, false, Who.Self) }));
        }

        [Test]
        public void YourPetsHitsShowAsYourPets()
        {
            GamePlayer you = Player();

            Assert.That(Viewers(you, true, null, Npc()), Is.EqualTo(new[] { (you, true, Who.Pet) }));
        }

        [Test]
        public void GroupMatesHitsShowAsGroupForEveryPlayerInTheGroup()
        {
            GamePlayer you = Player();
            GamePlayer friend = Player();
            GameNPC companion = Npc();

            var viewers = Viewers(companion, false, new GameLiving[] { you, companion, friend }, Npc());

            Assert.That(viewers, Is.EqualTo(new[] { (you, true, Who.Group), (friend, true, Who.Group) }));
        }

        [Test]
        public void AGroupMatesHealOnYouShowsAsAHealYouReceived()
        {
            GamePlayer you = Player();
            GameNPC healer = Npc();

            var viewers = Viewers(healer, false, new GameLiving[] { you, healer }, you);

            Assert.That(viewers, Is.EqualTo(new[] { (you, false, Who.Self) }));
        }

        [Test]
        public void ASelfHealShowsOnce()
        {
            GamePlayer you = Player();

            Assert.That(Viewers(you, false, new GameLiving[] { you }, you), Is.EqualTo(new[] { (you, true, Who.Self) }));
        }

        [Test]
        public void BystandersSeeNothing()
        {
            Assert.That(Viewers(Npc(), false, null, Npc()), Is.Empty);
        }

        [Test]
        public void ALeftStreamStopsCounting()
        {
            Channel<string> channel = Subscribe("someone");
            Unsubscribe("someone", channel);
            Unsubscribe("someone", channel);

            // With no one listening, a hit is dropped before any lookup.
            Assert.DoesNotThrow(() => Damage(Npc(), Npc(), eDamageType.Slash, 10, 0));
        }

        [Test]
        public void ItDoesNotShareAPortWithTheOtherLocalPages()
        {
            int[] offsets = { PORT_OFFSET, BotWatch.PORT_OFFSET, DOL.Network.BaseServer.PASSPORT_DESK_PORT_OFFSET };

            Assert.That(offsets.Distinct().Count(), Is.EqualTo(offsets.Length));
        }
    }
}
