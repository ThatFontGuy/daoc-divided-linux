using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture]
public sealed class UT_ValkyrieOdinsWill
{
    private static Spell Buff(int value, int concentration = 1, bool shearable = false) =>
        new(new DbSpell { Type = "DexterityQuicknessBuff", Target = "Realm", Value = value, Concentration = concentration, Duration = 0 }, 1)
        { IsShearable = shearable };

    [TestCase(0, 0)]
    [TestCase(5, 5)]
    [TestCase(-9, 90)]
    [TestCase(-10, 100)]
    public void PulseCostUsesFlatOrPercentOfMaxPower(int pulsePower, int expected) =>
        Assert.That(BotSpellPower.PulseCost(1000, pulsePower), Is.EqualTo(expected));

    [TestCase(64990, true)]
    [TestCase(65135, true)]
    [TestCase(65151, false)]
    [TestCase(65152, false)]
    public void ValkyrieSpellsUseTheirOwnTooltips(int spellId, bool expected) =>
        Assert.That(DOL.GS.PacketHandler.PacketLib1110.UsesOwnTooltipIdentity(spellId), Is.EqualTo(expected));

    [Test]
    public void PercentPulseCostRoundsUp() => Assert.That(BotSpellPower.PulseCost(101, -9), Is.EqualTo(10));

    [Test]
    public void ShearRemovesConcentrationBuffWithinCap()
    {
        Assert.That(ValkyrieConeShear.CanShear(Buff(75), false, 75), Is.True);
        Assert.That(ValkyrieConeShear.CanShear(Buff(76), false, 75), Is.False);
    }

    [Test]
    public void UncappedShearRemovesAnyValue() => Assert.That(ValkyrieConeShear.CanShear(Buff(500), false, 0), Is.True);

    [Test]
    public void ShearIgnoresNonConcentrationBuffs() => Assert.That(ValkyrieConeShear.CanShear(Buff(10, concentration: 0), false, 0), Is.False);

    [Test]
    public void SelfCastBuffNeedsShearableFlag()
    {
        Assert.That(ValkyrieConeShear.CanShear(Buff(10), true, 0), Is.False);
        Assert.That(ValkyrieConeShear.CanShear(Buff(10, shearable: true), true, 0), Is.True);
    }
}
