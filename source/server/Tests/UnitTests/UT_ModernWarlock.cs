using DOL.Database;
using DOL.GS;
using DOL.GS.PlayerClass;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture, NonParallelizable]
public sealed class UT_ModernWarlock
{
    private static Spell S(int id, string type = "DirectDamage") => new(new DbSpell { SpellID = id, Type = type, Target = "Self" }, 1);

    [TestCase(65999, false)]
    [TestCase(66000, true)]
    [TestCase(66399, true)]
    [TestCase(66400, false)]
    public void OnlyReservedSpellsUseWarlockRules(int id, bool expected) => Assert.That(ModernWarlock.Owns(id), Is.EqualTo(expected));

    [TestCase(1500, 20, 1800)]
    [TestCase(300, 20, 360)]
    [TestCase(2500, 5, 2625)]
    public void PercentageModifiersUseBaseDistanceOrDexAdjustedCastTime(int value, double percent, int expected) =>
        Assert.That(ModernWarlock.ScaleDistance(value, percent), Is.EqualTo(expected));

    [TestCase(500, 5, 25)]
    [TestCase(500, 40, 200)]
    [TestCase(500, 0, 0)]
    public void SecondaryCostUsesBasePower(int mana, double percent, int expected) => Assert.That(ModernWarlock.PercentCost(mana, percent), Is.EqualTo(expected));

    [TestCase(3, true, true, false, true)]
    [TestCase(3, true, false, false, false)]
    [TestCase(4, true, true, false, false)]
    [TestCase(4, true, true, true, true)]
    public void ChainRequiresPrecedingStages(int stage, bool dread, bool anguish, bool agony, bool expected) =>
        Assert.That(ModernWarlock.ChainReady(stage, dread, anguish, agony), Is.EqualTo(expected));

    [Test]
    public void FeatureGateControlsCreationAndChambersKeepSixSecondLoad()
    {
        bool old = DOL.GS.ServerProperties.Properties.ENABLE_WARLOCK_TEST;
        try
        {
            var career = new ClassWarlock();
            DOL.GS.ServerProperties.Properties.ENABLE_WARLOCK_TEST = false;
            Assert.That(career.EligibleRaces, Is.Empty);
            DOL.GS.ServerProperties.Properties.ENABLE_WARLOCK_TEST = true;
            Assert.That(career.EligibleRaces, Has.Count.EqualTo(4));
            Assert.That(career.CanChangeCastingSpeed(null, S(66180, "WarlockChamber")), Is.False);
            Assert.That(career.CanChangeCastingSpeed(null, S(66075)), Is.True);
        }
        finally { DOL.GS.ServerProperties.Properties.ENABLE_WARLOCK_TEST = old; }
    }

    [Test]
    public void ClientUsesIndependentTooltips() => Assert.That(DOL.GS.PacketHandler.PacketLib1110.UsesOwnTooltipIdentity(66075), Is.True);

    [Test]
    public void AnyPrimerCanReplaceAnyOtherPrimer()
    {
        var line = new SpellLine("test", "test", "Cursing", false);
        var highPenalty = new WarlockPrimerEffect(new(null, 0, 1, new WarlockPrimerHandler(null, S(66010, "WarlockPrimer"), line)));
        var lowPenalty = new WarlockPrimerEffect(new(null, 0, 1, new WarlockPrimerHandler(null, S(66015, "WarlockPrimer"), line)));
        Assert.That(lowPenalty.IsBetterThan(highPenalty), Is.True);
        Assert.That(highPenalty.Duration, Is.Zero);
    }

    [Test]
    public void PrimersLoadedChambersAndMaulerAurasAreHeldUntilCancelled()
    {
        // October 25 tester report: primers switched off at once and chambers never stayed loaded. A spell
        // effect with no duration expires on the next tick unless its expiry is pushed out.
        var line = new SpellLine("test", "test", "Cursing", false);
        var primer = new WarlockPrimerEffect(new(null, 0, 1, new WarlockPrimerHandler(null, S(66010, "WarlockPrimer"), line)));
        var chamber = new WarlockReadyEffect(new(null, 0, 1, new WarlockChamberHandler(null, S(66180, "WarlockChamber"), line)));
        var aura = new MaulerStanceEffect(new(null, 0, 1, new MaulerStanceHandler(null, S(67000, "MaulerStance"), line)));
        Assert.Multiple(() =>
        {
            Assert.That(primer.ExpireTick, Is.EqualTo(long.MaxValue));
            Assert.That(chamber.ExpireTick, Is.EqualTo(long.MaxValue));
            Assert.That(aura.ExpireTick, Is.EqualTo(long.MaxValue));
        });
    }
}
