using System;
using NUnit.Framework;

namespace DOL.GS.Tests;

/// <summary>Gamebot trips to camp, from the modern test server's log of 2026-10-28.</summary>
[TestFixture]
public sealed class UT_BotTripFixesOct28
{
    private static readonly DateTime Now = new(2026, 10, 28, 12, 0, 0, DateTimeKind.Utc);

    [SetUp]
    public void Reset() => AutonomousZoneSeamBlocks.ResetForTests();

    [Test]
    public void AZoneCrossingIsBlockedOnlyAfterThreeDifferentBotsFailIt()
    {
        // Black Mtns. South (2) to Pennine Mountains (14), Albion region 1.
        Assert.That(AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, 101, Now), Is.False);
        Assert.That(AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, 101, Now.AddMinutes(1)), Is.False,
            "the same bot again does not count twice");
        Assert.That(AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, 102, Now.AddMinutes(2)), Is.False);
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 2, 14, Now.AddMinutes(2)), Is.False);
        Assert.That(AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, 103, Now.AddMinutes(3)), Is.True);
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 2, 14, Now.AddMinutes(3)), Is.True);
        // Another realm, another start zone and the same zone are unaffected.
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Midgard, 1, 2, 14, Now.AddMinutes(3)), Is.False);
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 0, 14, Now.AddMinutes(3)), Is.False);
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 14, 14, Now.AddMinutes(3)), Is.False);
        // The block expires.
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 2, 14,
            Now.AddMinutes(3) + AutonomousZoneSeamBlocks.BlockDuration), Is.False);
    }

    [Test]
    public void FailuresOutsideTheWindowDoNotAddUp()
    {
        AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, 101, Now);
        AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, 102, Now);
        DateTime late = Now + AutonomousZoneSeamBlocks.FailureWindow + TimeSpan.FromMinutes(1);
        Assert.That(AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, 103, late), Is.False);
    }

    [Test]
    public void ADestinationBlockedFromTwoStartZonesIsBlockedFromAnywhere()
    {
        foreach (long bot in new long[] { 1, 2, 3 })
            AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 2, 14, bot, Now);
        Assert.That(AutonomousZoneSeamBlocks.IsDestinationBlocked(eRealm.Albion, 1, 14, Now), Is.False);
        foreach (long bot in new long[] { 4, 5, 6 })
            AutonomousZoneSeamBlocks.ReportFailure(eRealm.Albion, 1, 0, 14, bot, Now);
        Assert.That(AutonomousZoneSeamBlocks.IsDestinationBlocked(eRealm.Albion, 1, 14, Now), Is.True);
        // A bot in Camelot (another region) or Salisbury Plains skips those camps too.
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 0, 14, Now), Is.True);
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 1, 14, Now), Is.True);
        Assert.That(AutonomousZoneSeamBlocks.IsBlocked(eRealm.Albion, 1, 1, 11, Now), Is.False);
    }

    [TestCase("albion-0-23390033-SoloPve", eAutonomousObjectiveKind.SoloPve, false, true)]
    [TestCase("albion-0-23390033-SoloPve", eAutonomousObjectiveKind.GroupPve, false, true)]
    [TestCase("albion-0-1660-GroupPve", eAutonomousObjectiveKind.SoloPve, false, true)]
    [TestCase("albion-0-1660-GroupPve", eAutonomousObjectiveKind.GroupPve, true, false)]
    [TestCase("albion-50-77-RvR", eAutonomousObjectiveKind.SoloPve, false, false)]
    [TestCase("automatic-raid-dragon-12-5", eAutonomousObjectiveKind.SoloPve, false, false)]
    public void APveRenewalKeepsTheCampTheBotIsStillWalkingTo(string previous, eAutonomousObjectiveKind kind,
        bool dungeon, bool keeps)
    {
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment(previous, kind, betweenTasks: false,
            grouped: false, hasCamp: true, campIsDungeon: dungeon, arrivedAtCamp: false), Is.EqualTo(keeps));
    }

    [Test]
    public void APveRenewalStillMovesABotThatIsAtItsCampOrHasNoSavedCamp()
    {
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment("albion-0-4-SoloPve",
            eAutonomousObjectiveKind.SoloPve, false, false, hasCamp: true, campIsDungeon: false, arrivedAtCamp: true), Is.False);
        // Matchmaking timeouts and capital recovery clear the saved camp first.
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment("albion-0-4-GroupPve",
            eAutonomousObjectiveKind.SoloPve, false, false, hasCamp: false, campIsDungeon: false), Is.False);
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment("albion-0-4-SoloPve",
            eAutonomousObjectiveKind.SoloPve, false, grouped: true, hasCamp: true, campIsDungeon: false), Is.False);
    }

    [TestCase(ConColor.PURPLE)]
    [TestCase(ConColor.RED)]
    public void ASoloBotGivesUpTheCampRatherThanWalkIntoAHopelessMonster(ConColor con)
    {
        // Inside the retarget cooldown it used to walk on ("Ignore").
        Assert.That(AutonomousRouteThreatPolicy.Decide(con, grouped: false, packSize: 1, bossLike: false,
            detourAvailable: false, detoursSoFar: 0, mayRetarget: false), Is.EqualTo(RouteThreatAction.Ignore));
        Assert.That(AutonomousRouteThreatPolicy.Decide(con, grouped: false, packSize: 1, bossLike: false,
            detourAvailable: false, detoursSoFar: 0, mayRetarget: false, mayAbandonHopeless: true),
            Is.EqualTo(RouteThreatAction.Retarget));
        // A way around is still taken first.
        Assert.That(AutonomousRouteThreatPolicy.Decide(con, grouped: false, packSize: 1, bossLike: false,
            detourAvailable: true, detoursSoFar: 0, mayRetarget: false, mayAbandonHopeless: true),
            Is.EqualTo(RouteThreatAction.Detour));
    }

    [Test]
    public void OrangesGroupsAndBossesKeepTheirOldRules()
    {
        // A single orange is still fought inside the cooldown.
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.ORANGE, false, 1, false, false, 0, false,
            mayAbandonHopeless: true), Is.EqualTo(RouteThreatAction.Pull));
        // Groups are unchanged.
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.PURPLE, true, 8, false, false, 0, false,
            mayAbandonHopeless: true), Is.EqualTo(RouteThreatAction.Ignore));
        // A solo bot also leaves a boss it cannot pass.
        Assert.That(AutonomousRouteThreatPolicy.Decide(ConColor.YELLOW, false, 1, true, false, 0, false,
            mayAbandonHopeless: true), Is.EqualTo(RouteThreatAction.Retarget));
    }

    [Test]
    public void ABotThatGivesUpBecauseOfAMonsterBacksOutOfItsReach()
    {
        // 2026-10-29: a level-10 Savage gave up its camp 200 units from a red vendo bone-collector (aggro 500),
        // stood still for the replan wait and died 31 seconds later.
        float radius = AutonomousRouteThreatPolicy.RetreatRadius(500, AutonomousRouteThreatPolicy.MeleeMargin);
        Assert.That(radius, Is.EqualTo(830f));
        var threat = new System.Numerics.Vector2(769761, 682262);
        var bot = threat + new System.Numerics.Vector2(-120, 160);
        System.Numerics.Vector2[] points = AutonomousRouteThreatPolicy.RetreatCandidates(bot, threat, radius);
        Assert.That(points, Has.Length.EqualTo(5));
        foreach (var point in points)
        {
            Assert.That(System.Numerics.Vector2.Distance(point, threat), Is.EqualTo(radius).Within(0.5f));
            // Never across the monster: every point is on the bot's side of it.
            Assert.That(System.Numerics.Vector2.Dot(point - threat, bot - threat), Is.GreaterThanOrEqualTo(-1f));
        }
        // A pack is backed away from as a whole: past the far member's aggro, from the pack's centre.
        var (center, packRadius) = AutonomousRouteThreatPolicy.PackRetreat(
        [
            (threat, 500), (threat + new System.Numerics.Vector2(400, 0), 500),
        ], AutonomousRouteThreatPolicy.MeleeMargin);
        Assert.That(center.X, Is.EqualTo(threat.X + 200).Within(0.5f));
        Assert.That(packRadius, Is.EqualTo(200 + 500 + 80 + 250).Within(0.5f));
        Assert.That(AutonomousRouteThreatPolicy.DistanceToSegment(new(0, 0), new(100, 0), new(50, 30)), Is.EqualTo(30f).Within(0.01f));
        Assert.That(AutonomousRouteThreatPolicy.DistanceToSegment(new(0, 0), new(100, 0), new(130, 40)), Is.EqualTo(50f).Within(0.01f));

        // Straight away first.
        Assert.That(System.Numerics.Vector2.Normalize(points[0] - threat).X,
            Is.EqualTo(System.Numerics.Vector2.Normalize(bot - threat).X).Within(0.001f));
    }

    [Test]
    public void TheCotswoldPortalPadFollowsTheInstalledWorldsPlatform()
    {
        // Navmesh floor under the pad: 2816 in the 1.130 world, 2698 in the classic one; the measured pad is 2694.
        var pad = new System.Numerics.Vector3(564976, 509200, 2694);
        var modern = ShroudedIslesPortals.SnapToFloor(pad, 2816);
        Assert.That(modern.Z, Is.EqualTo(2816f));
        Assert.That(ShroudedIslesPortals.IsOnPad(modern, new(565031, 509168, 2816)), Is.True,
            "where the bots stood for fifteen minutes");
        Assert.That(ShroudedIslesPortals.SnapToFloor(pad, 2698).Z, Is.EqualTo(2698f));
        // No floor found, or one far off: the measured pad stays.
        Assert.That(ShroudedIslesPortals.SnapToFloor(pad, null), Is.EqualTo(pad));
        Assert.That(ShroudedIslesPortals.SnapToFloor(pad, 3200).Z, Is.EqualTo(2694f));
    }
}
