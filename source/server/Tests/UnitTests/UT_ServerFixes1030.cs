using System.Runtime.CompilerServices;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Owner 2026-10-30: bots buying item-currency gear for coin.</summary>
    [TestFixture]
    public class UT_ServerFixes1030
    {
        [Test]
        public void BotsOnlyBuyUpgradesFromCoinMerchants() => Assert.Multiple(() =>
        {
            Assert.That(AutonomousBotEconomy.SellsForCoin(Make<GameMerchant>()), Is.True);
            Assert.That(AutonomousBotEconomy.SellsForCoin(Make<GameDiamondSealsMerchant>()), Is.False);
            Assert.That(AutonomousBotEconomy.SellsForCoin(Make<GameSapphireSealsMerchant>()), Is.False);
            Assert.That(AutonomousBotEconomy.SellsForCoin(Make<GameEmeraldSealsMerchant>()), Is.False);
            Assert.That(AutonomousBotEconomy.SellsForCoin(Make<GameBountyMerchant>()), Is.False);
            Assert.That(AutonomousBotEconomy.SellsForCoin(null), Is.False);
        });

        [Test]
        public void SealGearIsOnlyForTheMerchantsOwnRealmAndNeedsABot() => Assert.Multiple(() =>
        {
            Assert.That(GameDarknessFallsSealsMerchant.CanTrade(eRealm.Albion, eRealm.Albion), Is.True);
            Assert.That(GameDarknessFallsSealsMerchant.CanTrade(eRealm.Albion, eRealm.Midgard), Is.False);
            Assert.That(AutonomousBotEconomy.HasSealPurchase(null), Is.False);
            Assert.That(AutonomousBotEconomy.SealCount(null, "DiamondSeal"), Is.Zero);
            Assert.That(AutonomousBotEconomy.FindSealPurchase(null, Make<GameDiamondSealsMerchant>()), Is.Null);
            // Appended last, so the numbers of the existing service kinds are unchanged.
            Assert.That((int)eWorldServiceKind.SealMerchant, Is.EqualTo((int)eWorldServiceKind.CraftStation + 1));
        });

        // The disabled class and race lists hold ranges ("58-62", "16-21") that character creation never expanded.
        [Test]
        public void DisabledClassAndRaceRangesAreExpanded() => Assert.Multiple(() =>
        {
            var classes = Util.SplitCSV("33;34;39;58-62", true);
            Assert.That(classes, Does.Contain("60").And.Contain("58").And.Contain("62").And.Contain("33"));
            Assert.That(classes, Does.Not.Contain("20"), "Necromancer (Disciple) stays creatable");
            Assert.That(Util.SplitCSV("16-21", true), Is.EquivalentTo(new[] { "16", "17", "18", "19", "20", "21" }));
        });

        private static T Make<T>() where T : class => (T)RuntimeHelpers.GetUninitializedObject(typeof(T));
    }
}
