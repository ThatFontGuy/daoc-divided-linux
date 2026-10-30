using NUnit.Framework;

namespace DOL.GS.Tests;

[TestFixture]
public sealed class UT_RouteThreatGroupLimit
{
    [Test]
    public void APartyDoesNotPullARedPackFarAboveItsAverage()
    {
        // Group 004 of 2026-10-29: a red giant cicada, a pack of two, 12 levels above the party's average.
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.RED, grouped: true, packSize: 2, bossLike: false, detourAvailable: false,
            detoursSoFar: 0, mayRetarget: false, levelsAboveReference: 12, mayForceRetarget: false), Is.Not.EqualTo(RouteThreatAction.Pull));
    }

    [Test]
    public void APartyStillPullsARedPackCloseToItsAverage()
    {
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.RED, grouped: true, packSize: 2, bossLike: false, detourAvailable: false,
            detoursSoFar: 0, mayRetarget: false, levelsAboveReference: 5), Is.EqualTo(RouteThreatAction.Pull));
    }

    [Test]
    public void TheLimitIsEightLevels()
    {
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.RED, true, 1, false, false, 0, false, levelsAboveReference: 7),
            Is.EqualTo(RouteThreatAction.Pull));
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.RED, true, 1, false, false, 0, false, levelsAboveReference: 8),
            Is.Not.EqualTo(RouteThreatAction.Pull));
    }

    [Test]
    public void AHopelessMonsterMakesAPartyGiveUpTheCampInsideTheCooldown()
    {
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.PURPLE, true, 2, false, false, 0, mayRetarget: false,
            levelsAboveReference: 18, mayForceRetarget: true), Is.EqualTo(RouteThreatAction.Retarget));
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.RED, true, 1, false, false, 0, mayRetarget: false,
            levelsAboveReference: 10, mayForceRetarget: true), Is.EqualTo(RouteThreatAction.Retarget));
    }

    [Test]
    public void TheForcedGiveUpWaitsForItsOwnCooldownAndNeedsAHopelessMonster()
    {
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.PURPLE, true, 2, false, false, 0, mayRetarget: false,
            levelsAboveReference: 18, mayForceRetarget: false), Is.EqualTo(RouteThreatAction.Ignore));
        // Orange monsters in a big pack: not hopeless, the party carries on.
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.ORANGE, true, 9, false, false, 0, mayRetarget: false,
            levelsAboveReference: 4, mayForceRetarget: true), Is.EqualTo(RouteThreatAction.Ignore));
    }

    [Test]
    public void ADetourIsStillPreferredToGivingUp()
    {
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.PURPLE, true, 2, false, detourAvailable: true, 0, mayRetarget: false,
            levelsAboveReference: 18, mayForceRetarget: true), Is.EqualTo(RouteThreatAction.Detour));
    }

    [Test]
    public void ALoneBotIsNotAffected()
    {
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.PURPLE, grouped: false, 1, false, false, 0, mayRetarget: false,
            levelsAboveReference: 18, mayForceRetarget: true), Is.EqualTo(RouteThreatAction.Ignore));
    }
}
