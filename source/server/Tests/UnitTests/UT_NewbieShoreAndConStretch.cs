using System.Collections.Generic;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_NewbieShoreAndConStretch
    {
        private const ushort Aegir = 151;
        private const int TownX = 289036, TownY = 355681;
        private static readonly (int X, int Y, int Level)[] NoAggressors = [];

        [Test]
        public void ACampBesideAegirhamnIsOnTheHomeShore() =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.IsNewbieShoreCamp(Aegir, TownX - 8_000, TownY, [1, 2, 3], NoAggressors), Is.True);

        [Test]
        public void ACampTooFarFromTownIsNot() =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.IsNewbieShoreCamp(Aegir, TownX - 19_000, TownY, [1], NoAggressors), Is.False);

        [Test]
        public void ACampWithALevel10SpawnIsNot() =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.IsNewbieShoreCamp(Aegir, TownX - 8_000, TownY, [8, 10], NoAggressors), Is.False);

        [Test]
        public void AnAggressiveMonsterOnTheWalkClosesTheCamp() =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.IsNewbieShoreCamp(Aegir, TownX - 8_000, TownY, [1],
                [(TownX - 4_000, TownY + 1_000, 14)]), Is.False);

        [Test]
        public void ALowAggressiveMonsterBesideTheWalkDoesNot() =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.IsNewbieShoreCamp(Aegir, TownX - 8_000, TownY, [1],
                [(TownX - 4_000, TownY + 1_000, 7)]), Is.True);

        [Test]
        public void AnyAggressiveMonsterAtTheCampClosesIt() =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.IsNewbieShoreCamp(Aegir, TownX - 8_000, TownY, [1],
                [(TownX - 8_500, TownY, 7)]), Is.False);

        [Test]
        public void OnlyTheThreeShroudedIslesHaveAHomeShore() =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.IsNewbieShoreCamp(100, TownX, TownY, [1], NoAggressors), Is.False);

        [TestCase((ushort)151, 5, true, true)]
        [TestCase((ushort)151, 5, false, false)]
        [TestCase((ushort)151, 10, false, true)]
        [TestCase((ushort)100, 5, false, true)]
        public void ANewBotTakesOnlyAHomeShoreCampInTheShroudedIsles(ushort region, int level, bool shore, bool allowed) =>
            Assert.That(AutonomousOrdinaryPveRealmPolicy.CanAssignCamp(eRealm.Midgard, region, 0, level, shore), Is.EqualTo(allowed));

        [TestCase(ConColor.ORANGE, 19, true)]
        [TestCase(ConColor.ORANGE, 20, false)]
        [TestCase(ConColor.RED, 5, true)]
        [TestCase(ConColor.RED, 6, false)]
        [TestCase(ConColor.PURPLE, 1, true)]
        [TestCase(ConColor.PURPLE, 2, false)]
        public void HarderConsAreRarer(ConColor felt, int roll, bool allowed) =>
            Assert.That(AutonomousCampConStretch.SoloMayTry(felt, false, 20, roll), Is.EqualTo(allowed));

        [Test]
        public void AnOrangeBotsKeepBeatingFeelsYellowAndIsAlwaysFair() =>
            Assert.That(AutonomousCampConStretch.SoloMayTry(
                AutonomousMobLessons.Felt(ConColor.ORANGE, 20, 0, false), false, 20, 99), Is.True);

        [Test]
        public void AMonsterThatKeepsKillingBotsIsNeverTried() =>
            Assert.That(AutonomousCampConStretch.SoloMayTry(ConColor.ORANGE, true, 20, 0), Is.False);

        [Test]
        public void AVeryNewBotStaysAtYellowOrEasier() =>
            Assert.That(AutonomousCampConStretch.SoloMayTry(ConColor.ORANGE, false, 4, 0), Is.False);

        [Test]
        public void MostPartyPicksKeepThePlusThreeBand() =>
            Assert.That(AutonomousCampConStretch.GroupBand(8, 0, 30, 30), Is.EqualTo((3, 8)));

        [Test]
        public void SomePartyPicksAreYellowOrBlue()
        {
            Assert.That(AutonomousCampConStretch.GroupBand(8, 0, 30, 0).High, Is.EqualTo(0));
            Assert.That(AutonomousCampConStretch.GroupBand(8, 0, 30, 1).High, Is.EqualTo(-3));
            Assert.That(AutonomousCampConStretch.GroupBand(8, 0, 5, 1).High, Is.EqualTo(0));
        }

        [Test]
        public void APartyThatWipedOpensEverythingBelowItsLoweredTop()
        {
            Assert.That(AutonomousCampConStretch.GroupBand(2, 2, 30, 99).High, Is.EqualTo(2));
            Assert.That(AutonomousCampConStretch.GroupBand(-1, 5, 30, 99).High, Is.EqualTo(0));
        }

        [Test]
        public void TheBandPicksItsHighestLevel() =>
            Assert.That(AutonomousGroupTargetPolicy.SelectBandLevel(new List<int> { 25, 28, 30, 33 }, -20, 30), Is.EqualTo(30));
    }
}
