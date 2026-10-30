using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>1.130a: realm ranks through RR15L0, RR15 titles and the 2,000,000,000 realm point cap.</summary>
    [TestFixture]
    public class UT_RealmRank15
    {
        [Test]
        public void RealmPointTableReachesRR15WithThe1130aThresholds()
        {
            long[] table = GamePlayer.REALMPOINTS_FOR_LEVEL;
            Assert.That(table.Length - 1, Is.EqualTo(140), "RR15L0 is realm level 140");
            Assert.That(table[130], Is.EqualTo(187917143), "RR14L0 unchanged");
            long[] live = { 223084000, 278317600, 355644640, 445902496, 555928241, 680853214, 820594584, 990514251, 1230285525, 1650444126 };
            for (int i = 0; i < live.Length; i++)
                Assert.That(table[131 + i], Is.EqualTo(live[i]), $"level {131 + i}");
            for (int level = 1; level < table.Length; level++)
                Assert.That(table[level], Is.GreaterThanOrEqualTo(table[level - 1]), $"level {level} ascends");
            Assert.That(table[^1], Is.LessThan(GamePlayer.MAX_REALM_POINTS));
            Assert.That(GamePlayer.MAX_REALM_POINTS, Is.EqualTo(2000000000));
        }

        [Test]
        public void RealmLevelForPointsStopsAtRR15L0()
        {
            Assert.That(AutonomousBotRealmPointRewards.RealmLevelFor(1650444126), Is.EqualTo(140));
            Assert.That(AutonomousBotRealmPointRewards.RealmLevelFor(1650444125), Is.EqualTo(139));
            Assert.That(AutonomousBotRealmPointRewards.RealmLevelFor(GamePlayer.MAX_REALM_POINTS), Is.EqualTo(140));
            Assert.That(AutonomousBotRealmPointRewards.RealmLevelFor(223084000), Is.EqualTo(131));
        }

        [Test]
        public void EveryRealmAndGenderHasAnRR15Title()
        {
            string[,] expected = { { "Prince", "Princess" }, { "Konungsson", "Konungsdottir" }, { "Prionsa", "Banphrionsa" } };
            for (int realm = 0; realm < 3; realm++)
                for (int gender = 0; gender < 2; gender++)
                    Assert.That(GlobalConstants.REALM_RANK_NAMES[realm, gender, 140 / 10], Is.EqualTo(expected[realm, gender]));
            Assert.That(GlobalConstants.REALM_RANK_NAMES[0, 0, 13], Is.EqualTo("Arch Duke"), "RR14 unchanged");
        }
    }
}
