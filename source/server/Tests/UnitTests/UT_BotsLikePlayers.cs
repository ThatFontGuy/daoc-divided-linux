using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.Commands;
using DOL.GS.PacketHandler.Client.v168;
using DOL.GS.ServerProperties;
using DOL.GS.ServerRules;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Owner 2026-10-30: bots shown as players, bots that invite the player, and /bots hunt.</summary>
    [TestFixture, NonParallelizable]
    public class UT_BotsLikePlayers
    {
        private static readonly IObjectDatabase EmptyDatabase = DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
        private bool _showAsPlayers;
        private GameServer _previousServer;

        private sealed class TestServer : GameServer
        {
            protected override IServerRules ServerRulesImpl => new NormalServerRules();
            protected override IObjectDatabase DataBaseImpl => EmptyDatabase;
        }

        private sealed class WorldBot : GameBot
        {
            private WorldBot() : base((OfflineWorldBotRecord)null) { }
            public override eObjectState ObjectState { get => eObjectState.Active; set { } }
            public override ushort CurrentRegionID { get => 7; set { } }
        }

        private static WorldBot NewBot() => (WorldBot)RuntimeHelpers.GetUninitializedObject(typeof(WorldBot));

        private static GameClient NewClient(GameClient.eClientVersion version)
        {
            var client = (GameClient)RuntimeHelpers.GetUninitializedObject(typeof(BotDummyClient));
            client.Version = version;
            return client;
        }

        [SetUp]
        public void SetUp()
        {
            _previousServer = GameServer.Instance;
            GameServer.LoadTestDouble((TestServer)RuntimeHelpers.GetUninitializedObject(typeof(TestServer)));
            _showAsPlayers = Properties.BOT_SHOW_AS_PLAYERS;
            Properties.BOT_SHOW_AS_PLAYERS = true;
        }

        [TearDown]
        public void TearDown()
        {
            Properties.BOT_SHOW_AS_PLAYERS = _showAsPlayers;
            GameServer.LoadTestDouble(_previousServer);
        }

        [Test]
        public void DeathPacket_TakesABotAsWellAsAPlayer()
        {
            var parameter = typeof(DOL.GS.PacketHandler.IPacketLib).GetMethod(nameof(DOL.GS.PacketHandler.IPacketLib.SendPlayerDied)).GetParameters()[0];
            Assert.That(parameter.ParameterType, Is.EqualTo(typeof(GameLiving)));
            Assert.That(typeof(GameBot).GetMethod("ShowDeadToViewers", BindingFlags.Instance | BindingFlags.NonPublic), Is.Not.Null);
        }

        // gamedata.mpk monsters.csv: the rows exist under these ids in the 1.127 and 1.130 tables alike.
        [Test]
        public void FrenzyModels_AreTheOnesBothClientTablesShare()
        {
            Assert.That(BerserkECSGameEffect.VendoModel, Is.EqualTo(582));
            Assert.That(BerserkECSGameEffect.DwarfVendoModel, Is.EqualTo(2032));
            Assert.That(StagECSGameEffect.StagModel, Is.EqualTo(583));
            Assert.That(StagECSGameEffect.LurikeenStagModel, Is.EqualTo(859));
        }

        [TestCase("lfg 30 cleric", true)]
        [TestCase("LFG", true)]
        [TestCase("looking for a group", true)]
        [TestCase("anyone? looking for group near mularn", true)]
        [TestCase("lf group", true)]
        [TestCase("not lfg just chatting", false)]
        [TestCase("3 hours lfg and nothing", false)]
        [TestCase("lfm vendo need healer", false)]
        [TestCase("looking for a merchant", false)]
        [TestCase("", false)]
        public void SaysLookingForGroup_ReadsTheLine(string line, bool expected) =>
            Assert.That(AutonomousLivingServer.SaysLookingForGroup(line), Is.EqualTo(expected));

        [Test]
        public void BotInvite_OnlyAPlayerOfAboutItsLevel()
        {
            Assert.That(AutonomousLivingServer.FitsBotInvite(20, 25, AutonomousLivingServer.LfgInviteLevelGap), Is.True);
            Assert.That(AutonomousLivingServer.FitsBotInvite(20, 26, AutonomousLivingServer.LfgInviteLevelGap), Is.False);
            Assert.That(AutonomousLivingServer.FitsBotInvite(30, 26, AutonomousLivingServer.CampInviteLevelGap), Is.True);
            Assert.That(AutonomousLivingServer.FitsBotInvite(31, 26, AutonomousLivingServer.CampInviteLevelGap), Is.False);
        }

        [Test]
        public void SharedCamp_NeedsTimeThereAndFightingOnBothSides()
        {
            int settled = 0;
            settled = AutonomousLivingServer.NextSettledCount(settled, true, 100);
            Assert.That(AutonomousLivingServer.SharesCamp(settled, true, true), Is.False, "one scan is passing through");
            settled = AutonomousLivingServer.NextSettledCount(settled, true, 100);
            Assert.That(AutonomousLivingServer.SharesCamp(settled, true, true), Is.True);
            Assert.That(AutonomousLivingServer.SharesCamp(settled, false, true), Is.False, "the player isn't fighting");
            Assert.That(AutonomousLivingServer.SharesCamp(settled, true, false), Is.False, "the bot isn't fighting");
            Assert.That(AutonomousLivingServer.NextSettledCount(settled, true, 5_000), Is.Zero, "moved on");
            Assert.That(AutonomousLivingServer.NextSettledCount(settled, false, 0), Is.Zero, "another region");
        }

        [Test]
        public void HuntTargets_SkipGreyAndStopAtWhatThePartyCanTake()
        {
            Assert.That(PlayerBotHunt.IsHuntTarget(-3, 3), Is.False, "grey");
            Assert.That(PlayerBotHunt.IsHuntTarget(-2, 1), Is.True);
            Assert.That(PlayerBotHunt.IsHuntTarget(0, 1), Is.True);
            Assert.That(PlayerBotHunt.IsHuntTarget(2, 2), Is.False, "red is too much for two");
            Assert.That(PlayerBotHunt.IsHuntTarget(1, 3), Is.True);
            Assert.That(PlayerBotHunt.IsHuntTarget(3, 8), Is.False, "purple");
        }

        [Test]
        public void NextPull_WaitsForHealthPowerAndTheDead()
        {
            Assert.That(PlayerBotHunt.ReadyForPull(true, 70, 100, 30, false), Is.True);
            Assert.That(PlayerBotHunt.ReadyForPull(true, 69, 100, 30, false), Is.False);
            Assert.That(PlayerBotHunt.ReadyForPull(true, 100, 100, 29, false), Is.False, "the healer is out of power");
            Assert.That(PlayerBotHunt.ReadyForPull(true, 100, 0, 0, false), Is.True, "no power to wait for");
            Assert.That(PlayerBotHunt.ReadyForPull(true, 100, 100, 0, true), Is.True, "a song class never refills");
            Assert.That(PlayerBotHunt.ReadyForPull(false, 100, 100, 100, false), Is.False);
        }

        [Test]
        public void Presentation_OnlyForTheModernClient()
        {
            WorldBot bot = NewBot();
            try
            {
                Assert.That(BotPlayerPresentation.TryGetSession(NewClient(GameClient.eClientVersion.Version1127), bot, out _), Is.False,
                    "the new client announces 1.127 and reads no other player's position");
                Assert.That(BotPlayerPresentation.TryGetSession(NewClient(GameClient.eClientVersion.Version1130), bot, out ushort session), Is.True);
                Assert.That(session, Is.InRange(BotPlayerPresentation.FirstSession, BotPlayerPresentation.LastSession));
                Properties.BOT_SHOW_AS_PLAYERS = false;
                Assert.That(BotPlayerPresentation.TryGetSession(NewClient(GameClient.eClientVersion.Version1130), bot, out _), Is.False);
            }
            finally
            {
                BotPlayerPresentation.Release(bot);
            }
        }

        [Test]
        public void Sessions_AreUniqueInARegionAndComeBack()
        {
            GameClient client = NewClient(GameClient.eClientVersion.Version1130);
            WorldBot first = NewBot(), second = NewBot();
            try
            {
                BotPlayerPresentation.TryGetSession(client, first, out ushort firstSession);
                BotPlayerPresentation.TryGetSession(client, second, out ushort secondSession);
                BotPlayerPresentation.TryGetSession(client, first, out ushort again);
                Assert.That(secondSession, Is.Not.EqualTo(firstSession));
                Assert.That(again, Is.EqualTo(firstSession), "a bot keeps its id");
                Assert.That(BotPlayerPresentation.FindBySession(7, firstSession), Is.SameAs(first));
                Assert.That(BotPlayerPresentation.FindBySession(8, firstSession), Is.Null, "another region");
                Assert.That(BotPlayerPresentation.FindBySession(7, 1), Is.Null, "a real client's id");

                BotPlayerPresentation.Release(first);
                Assert.That(BotPlayerPresentation.FindBySession(7, firstSession), Is.Null);
            }
            finally
            {
                BotPlayerPresentation.Release(first);
                BotPlayerPresentation.Release(second);
            }
        }

        [Test]
        public void Sessions_RunOutToTheNpcPackets()
        {
            GameClient client = NewClient(GameClient.eClientVersion.Version1130);
            WorldBot[] bots = Enumerable.Range(0, BotPlayerPresentation.LastSession - BotPlayerPresentation.FirstSession + 1).Select(_ => NewBot()).ToArray();
            WorldBot extra = NewBot();
            try
            {
                Assert.That(bots.All(bot => BotPlayerPresentation.TryGetSession(client, bot, out _)), Is.True);
                Assert.That(BotPlayerPresentation.TryGetSession(client, extra, out _), Is.False);
            }
            finally
            {
                foreach (WorldBot bot in bots)
                    BotPlayerPresentation.Release(bot);
            }
        }

        [Test]
        public void UpdateInterval_KeepsAStandingBotFromGoingQuiet()
        {
            Assert.That(BotPlayerPresentation.UpdateInterval(true, false), Is.EqualTo(BotPlayerPresentation.MovingUpdateInterval));
            Assert.That(BotPlayerPresentation.UpdateInterval(false, true), Is.EqualTo(BotPlayerPresentation.MovingUpdateInterval), "the stop goes out quickly");
            Assert.That(BotPlayerPresentation.UpdateInterval(false, false), Is.EqualTo(BotPlayerPresentation.StandingUpdateInterval));
            Assert.That(BotPlayerPresentation.StandingUpdateInterval, Is.LessThan(Properties.WORLD_NPC_UPDATE_INTERVAL == 0 ? 5000 : (int)Properties.WORLD_NPC_UPDATE_INTERVAL));
        }

        [Test]
        public void BuffRecastGuard_TripsOnTheThirdCastAndEnds()
        {
            var guard = new BotBuffRecastGuard();
            Assert.That(guard.Record(5, 0, 1_000), Is.False);
            Assert.That(guard.Record(5, 0, 5_000), Is.False);
            Assert.That(guard.Blocks(5, 0, 5_000), Is.False);
            Assert.That(guard.Record(5, 0, 9_000), Is.True);
            Assert.That(guard.Blocks(5, 0, 10_000), Is.True);
            Assert.That(guard.Blocks(6, 0, 10_000), Is.False, "another spell goes on");
            Assert.That(guard.Blocks(5, 0, 9_000 + BotBuffRecastGuard.BlockMs), Is.False, "it tries again later");
        }

        [Test]
        public void BuffRecastGuard_LeavesNormalBuffingAlone()
        {
            var guard = new BotBuffRecastGuard();
            for (int target = 1; target <= 8; target++)
                Assert.That(guard.Record(5, target, target * 3_000), Is.False, "one buff, eight people");
            Assert.That(guard.Record(7, 1, 0), Is.False);
            Assert.That(guard.Record(7, 1, 70_000), Is.False, "a slow refresh");
            Assert.That(guard.Record(7, 1, 140_000), Is.False);
            Assert.That(guard.Record(7, 1, 210_000), Is.False);
        }

        [Test]
        public void BuffRecastGuard_OnlyPlainBuffs()
        {
            Assert.That(BotBuffRecastGuard.Applies(true, false, false, false), Is.True);
            Assert.That(BotBuffRecastGuard.Applies(false, false, false, false), Is.False);
            Assert.That(BotBuffRecastGuard.Applies(true, true, false, false), Is.False, "harmful");
            Assert.That(BotBuffRecastGuard.Applies(true, false, true, false), Is.False, "a heal");
            Assert.That(BotBuffRecastGuard.Applies(true, false, false, true), Is.False, "a pulse");
        }

        [Test]
        public void StateFlags_DeadComesFirst()
        {
            Assert.That(BotPlayerPresentation.StateFlags(false, false, false, false), Is.Zero);
            Assert.That(BotPlayerPresentation.StateFlags(true, true, true, true), Is.EqualTo((byte)PlayerPositionUpdateHandler.StateFlags.DEAD));
            Assert.That(BotPlayerPresentation.StateFlags(false, true, false, false), Is.EqualTo((byte)PlayerPositionUpdateHandler.StateFlags.RIDING));
            Assert.That(BotPlayerPresentation.StateFlags(false, false, false, true), Is.EqualTo((byte)PlayerPositionUpdateHandler.StateFlags.SWIMMING));
        }

        [Test]
        public void Face_IsTheSameEveryTimeAndStaysInRange()
        {
            Assert.That(BotPlayerPresentation.Face("Aldric"), Is.EqualTo(BotPlayerPresentation.Face("Aldric")));
            Assert.That(BotPlayerPresentation.Face(null), Has.Length.EqualTo(7));
            string[] names = ["Aldric", "Aineella", "Bryn", "Cuan", "Dagny", "Eirik", "Fionn", "Gwen"];
            Assert.That(names.Select(name => string.Join(",", BotPlayerPresentation.Face(name))).Distinct().Count(), Is.GreaterThan(1));
            foreach (byte[] face in names.Select(BotPlayerPresentation.Face))
            {
                Assert.That(face[3], Is.LessThan(4));
                Assert.That(face[4], Is.LessThan(4));
                Assert.That(face[5] & 0x0F, Is.Zero);
                Assert.That(face[6] & 0x0F, Is.Zero);
            }
        }
    }
}
