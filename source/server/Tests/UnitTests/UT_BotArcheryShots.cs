using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture]
public class UT_BotArcheryShots
{
    private static int _nextId;

    private static Spell Shot(string name, int level, double castSeconds, double damage, int power, int range = 2100,
        int shotType = 0, int radius = 0, string target = "Enemy") =>
        new(new DbSpell
        {
            SpellID = ++_nextId, Name = name, Type = eSpellType.Archery.ToString(), Target = target, CastTime = castSeconds,
            Damage = damage, Power = power, Range = range, Radius = radius, LifeDrainReturn = shotType,
        }, level);

    private static readonly Spell Standard = Shot("Standard Shot 9", 49, 4.2, 283.7, 0);
    private static readonly Spell Solo = Shot("Standard Solo Shot", 49, 4.2, 340, 0);
    private static readonly Spell Elemental = Shot("Lithic Shot 9", 49, 5, 378.2, 7);
    private static readonly Spell Long = Shot("Long Shot 8", 44, 5, 170.2, 8, range: 2500);
    private static readonly Spell Power = Shot("Power Shot 8", 45, 3.5, 487.7, 8, shotType: 2);
    private static readonly Spell PointBlank = Shot("Point Blank Shot 3", 40, 2, 347.1, 8, range: 500, shotType: 3);
    private static readonly List<Spell> Kit = new() { Standard, Solo, Elemental, Long, Power, PointBlank };

    private static Spell Choose(int distance = 1500, bool grouped = true, int endurance = 100, params Spell[] cooling) =>
        BotArcheryShots.Choose(Kit, distance, grouped, endurance, shot => shot.Range, shot => !cooling.Contains(shot));

    [Test]
    public void LeavesOutShotsABotCannotUseWell()
    {
        Assert.That(BotArcheryShots.IsBotShot(Standard), Is.True);
        Assert.That(BotArcheryShots.IsBotShot(Shot("Critical Shot 9", 50, 5, 521.5, 15, shotType: 1)), Is.False);
        Assert.That(BotArcheryShots.IsBotShot(Shot("Volley 8", 47, 7, 356, 10, radius: 350, target: "Area")), Is.False);
        Assert.That(BotArcheryShots.IsBotShot(Shot("Rapid Fire 8", 48, 3, 85.1, 4, radius: 350, shotType: 4)), Is.False);
        Assert.That(BotArcheryShots.IsBotShot(Shot("Acid Shot 8", 46, 5, 170.2, 10, range: 1500, radius: 300)), Is.False);
    }

    [Test]
    public void OpensWithPowerShotThenTheBestRepeatableShot()
    {
        Assert.That(Choose(), Is.SameAs(Power));
        Assert.That(Choose(cooling: Power), Is.SameAs(Elemental));
    }

    [Test]
    public void PointBlankOnlyInsideItsRange()
    {
        Assert.That(Choose(distance: 400), Is.SameAs(PointBlank));
        Assert.That(Choose(distance: 501), Is.SameAs(Power));
    }

    [Test]
    public void SoloShotOnlyOutOfAGroup()
    {
        Assert.That(Choose(grouped: false, cooling: Power), Is.SameAs(Solo));
        Assert.That(Choose(grouped: true, cooling: Power), Is.Not.SameAs(Solo));
    }

    [Test]
    public void LowEnduranceFallsBackToFreeShots()
    {
        Assert.That(Choose(grouped: true, endurance: 24), Is.SameAs(Standard));
    }

    [Test]
    public void OnlyLongShotReachesPastBowRange()
    {
        Assert.That(Choose(distance: 2300), Is.SameAs(Long));
        Assert.That(Choose(distance: 2501), Is.Null);
    }

    [Test]
    public void NoShotsLeavesTheClassicBow()
    {
        Assert.That(BotArcheryShots.Choose(new List<Spell>(), 1000, false, 100, shot => shot.Range, shot => true), Is.Null);
    }
}
