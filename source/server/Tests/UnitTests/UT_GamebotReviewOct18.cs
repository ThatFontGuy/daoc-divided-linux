using System.Linq;
using NUnit.Framework;

namespace DOL.GS.Tests;

/// <summary>Autonomous gamebot review, 2026-10-18.</summary>
[TestFixture]
public sealed class UT_GamebotReviewOct18
{
    [Test]
    public void BattlegroundKeepDefendersHoldingTheirPostAreNotMovementStalls()
    {
        eAutonomousProgressKind hold = AutonomousStuckWatchdog.DefensivePostProgress(eAutonomousObjectiveKind.Battleground);
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(hold), Is.True);
        // Holding a post is not an outcome: a forty-five-minute quiet hold is still recovered.
        Assert.That(AutonomousStuckWatchdog.CountsAsGoalProgress(hold), Is.False);
    }

    [TestCase(eAutonomousObjectiveKind.RvR)]
    [TestCase(eAutonomousObjectiveKind.SoloPve)]
    [TestCase(eAutonomousObjectiveKind.GroupPve)]
    public void OtherDefendersKeepTheirExistingWatchdogRules(eAutonomousObjectiveKind kind)
    {
        eAutonomousProgressKind hold = AutonomousStuckWatchdog.DefensivePostProgress(kind);
        Assert.That(hold, Is.EqualTo(eAutonomousProgressKind.Objective));
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(hold), Is.False);
    }

    [Test]
    public void MovementClockKindsAreUnchanged()
    {
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(eAutonomousProgressKind.Movement), Is.True);
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(eAutonomousProgressKind.StableTravel), Is.True);
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(eAutonomousProgressKind.Recovery), Is.True);
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(eAutonomousProgressKind.SiegeParticipation), Is.True);
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(eAutonomousProgressKind.Combat), Is.False);
        Assert.That(AutonomousStuckWatchdog.RefreshesMovementClock(eAutonomousProgressKind.Objective), Is.False);
    }

    [Test]
    public void MedallionMerchantWaitsOnlyWhileASaleMadeRoom()
    {
        Assert.That(AutonomousFrontierTransport.KeepWaitingForMedallionRoom(backpackFull: true, soldTrash: true), Is.True);
        // Nothing sellable: fall through to the walking itinerary instead of holding until the watchdog.
        Assert.That(AutonomousFrontierTransport.KeepWaitingForMedallionRoom(backpackFull: true, soldTrash: false), Is.False);
        Assert.That(AutonomousFrontierTransport.KeepWaitingForMedallionRoom(backpackFull: false, soldTrash: false), Is.False);
    }

    [TestCase(eAutonomousObjectiveKind.SoloPve, false, true)]
    [TestCase(eAutonomousObjectiveKind.GroupPve, false, true)]
    [TestCase(eAutonomousObjectiveKind.GroupPve, true, false)]
    [TestCase(eAutonomousObjectiveKind.SoloPve, true, true)]
    [TestCase(eAutonomousObjectiveKind.RvR, false, false)]
    [TestCase(eAutonomousObjectiveKind.Battleground, false, false)]
    public void FirstPveAssignmentKeepsTheCampTheBotIsAlreadyWalkingTo(eAutonomousObjectiveKind kind, bool dungeon, bool keeps)
    {
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment(string.Empty, kind,
            betweenTasks: false, grouped: false, hasCamp: true, campIsDungeon: dungeon), Is.EqualTo(keeps));
    }

    [Test]
    public void AnUnreachableFlyerIsLetGoAfterThirtySecondsWithoutContact()
    {
        const long start = 1_000_000;
        long limit = AutonomousPveTargetPolicy.UnreachableFlyerAggroDropMilliseconds;
        Assert.That(AutonomousPveTargetPolicy.ShouldDropUnreachableFlyer(true, false, start, start + limit - 1), Is.False);
        Assert.That(AutonomousPveTargetPolicy.ShouldDropUnreachableFlyer(true, false, start, start + limit), Is.True);
        // A landed or received blow is a real fight; a reachable target is never dropped.
        Assert.That(AutonomousPveTargetPolicy.ShouldDropUnreachableFlyer(true, true, start, start + 10 * limit), Is.False);
        Assert.That(AutonomousPveTargetPolicy.ShouldDropUnreachableFlyer(false, false, start, start + 10 * limit), Is.False);
    }

    [Test]
    public void OnlyRealDamageCountsAsContactWithAFlyer()
    {
        // A bow draw or a pet's swing stamps LastAttackTick without reaching anything; it is not an input.
        Assert.That(AutonomousPveTargetPolicy.FlyerFightContact(100, 100, 5000, 5000, true), Is.False);
        Assert.That(AutonomousPveTargetPolicy.FlyerFightContact(100, 101, 5000, 5000, false), Is.True, "being hit always counts");
        Assert.That(AutonomousPveTargetPolicy.FlyerFightContact(100, 100, 5000, 4999, true), Is.True);
        // A pet nicking a glider while its Spiritmaster or Hunter stands out of combat is no fight of the bot's.
        Assert.That(AutonomousPveTargetPolicy.FlyerFightContact(100, 100, 5000, 4999, false), Is.False);
    }

    [Test]
    public void AFightWithNoDamageEitherWayIsDroppedAfterAMinute()
    {
        const long start = 1_000_000;
        long minute = AutonomousPveTargetPolicy.StaleFightDropMilliseconds;
        long flyer = AutonomousPveTargetPolicy.UnreachableFlyerAggroDropMilliseconds;
        Assert.That(AutonomousPveTargetPolicy.ShouldDropStaleFight(true, false, false, start, start + minute - 1), Is.False);
        Assert.That(AutonomousPveTargetPolicy.ShouldDropStaleFight(true, false, false, start, start + minute), Is.True);
        Assert.That(AutonomousPveTargetPolicy.ShouldDropStaleFight(true, true, false, start, start + flyer), Is.True);
        // Damage either way, or an RvR target, is never judged stale.
        Assert.That(AutonomousPveTargetPolicy.ShouldDropStaleFight(true, false, true, start, start + 10 * minute), Is.False);
        Assert.That(AutonomousPveTargetPolicy.ShouldDropStaleFight(false, false, false, start, start + 10 * minute), Is.False);
    }

    [Test]
    public void GriffonGlidersHoveringOverTheCampFloorAreUnreachable()
    {
        // Gripklosa: a glider at Z 7482 over a Hunter rescued at Z 6677.
        Assert.That(AutonomousPveTargetPolicy.IsUnreachableFlyer(GameNPC.eFlags.FLYING, 7482, 6677), Is.True);
        Assert.That(AutonomousPveTargetPolicy.IsUnreachableFlyer(GameNPC.eFlags.FLYING, 6900, 6677), Is.False);
        Assert.That(AutonomousPveTargetPolicy.IsUnreachableFlyer(0, 7482, 6677), Is.False);
    }

    [Test]
    public void RealReassignmentsStillDropTheRoute()
    {
        // A renewal reaching a bot already at its camp is a real reassignment (2026-10-28: still walking keeps it).
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment("albion-0-4-SoloPve",
            eAutonomousObjectiveKind.SoloPve, false, false, true, false, arrivedAtCamp: true), Is.False);
        // Between-task services, party members and bots with no live camp replan as before.
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment(string.Empty,
            eAutonomousObjectiveKind.SoloPve, betweenTasks: true, grouped: false, hasCamp: true, campIsDungeon: false), Is.False);
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment(string.Empty,
            eAutonomousObjectiveKind.SoloPve, betweenTasks: false, grouped: true, hasCamp: true, campIsDungeon: false), Is.False);
        Assert.That(AutonomousObjectiveAssignments.KeepsCampOnFirstAssignment(null,
            eAutonomousObjectiveKind.SoloPve, betweenTasks: false, grouped: false, hasCamp: false, campIsDungeon: false), Is.False);
    }

    [Test]
    public void ADeadBotsCorpseStaysWhereItDied()
    {
        // Ported from chris4aker's Social Expansion fork: the corpse used to be sent to its spawn point.
        Assert.That(DOL.AI.ABrain.ShouldReturnToSpawnOnStop(isBot: true, botIntentionalWorldMove: false, alive: false,
            nearSpawn: false, active: false), Is.False);
        // Everything else keeps the old rule: an inactive monster away from its spawn goes home.
        Assert.That(DOL.AI.ABrain.ShouldReturnToSpawnOnStop(false, false, false, false, false), Is.True);
        Assert.That(DOL.AI.ABrain.ShouldReturnToSpawnOnStop(true, false, true, false, false), Is.True);
        Assert.That(DOL.AI.ABrain.ShouldReturnToSpawnOnStop(true, true, true, false, false), Is.False);
        Assert.That(DOL.AI.ABrain.ShouldReturnToSpawnOnStop(false, false, true, true, false), Is.False);
        Assert.That(DOL.AI.ABrain.ShouldReturnToSpawnOnStop(false, false, true, false, true), Is.False);
    }

    [Test]
    public void TheCampCatalogSkipsMonstersWithNoZone()
    {
        // Ported from MoomoocowPlus's fork: one zoneless monster used to throw the whole catalog draft.
        var zone = (Zone)System.Runtime.CompilerServices.RuntimeHelpers.GetUninitializedObject(typeof(Zone));
        var monsters = new[] { new Spawn("zombie", null), new Spawn("wolf", zone), null };
        var kept = AutonomousPveTargetPolicy.WithZone(monsters, monster => monster.Zone);
        Assert.That(kept.Select(monster => monster.Name), Is.EqualTo(new[] { "wolf" }));
        Assert.That(AutonomousPveTargetPolicy.WithZone<string>(null, _ => zone), Is.Empty);
    }


    [Test]
    public void SoloWatchdogRescuesCountAgainstTheirCamp()
    {
        Assert.That(AutonomousStuckWatchdog.ReportsCampOnRescue("AUTONOMOUS_STUCK_15M_RECOVERY", false, "camp-a"), Is.True);
        Assert.That(AutonomousStuckWatchdog.ReportsCampOnRescue("AUTONOMOUS_GOAL_STALL_45M_RECOVERY", false, "camp-a"), Is.True);
        // A frozen party, a position repair or a bot with no camp is no evidence against a camp.
        Assert.That(AutonomousStuckWatchdog.ReportsCampOnRescue("AUTONOMOUS_STUCK_15M_RECOVERY", true, "camp-a"), Is.False);
        Assert.That(AutonomousStuckWatchdog.ReportsCampOnRescue("AUTONOMOUS_POSITION_RECOVERY", false, "camp-a"), Is.False);
        Assert.That(AutonomousStuckWatchdog.ReportsCampOnRescue("AUTONOMOUS_GOAL_STALL_45M_RECOVERY", false, ""), Is.False);
    }

    [Test]
    public void ThreeSoloRescuesOnOneCampBenchIt()
    {
        // The Sheeroe Hills "pale horse" camp: three different bots stalled there within eleven minutes.
        AutonomousCampRouteQuarantine.ResetForTests();
        var start = new System.DateTime(2026, 10, 19, 13, 27, 0, System.DateTimeKind.Utc);
        const string camp = "capnbry-source-empty:216:200:256:434:pale horse:50";
        try
        {
            Assert.That(AutonomousCampRouteQuarantine.ReportFailure(camp, 101, start), Is.False);
            Assert.That(AutonomousCampRouteQuarantine.ReportFailure(camp, 102, start.AddMinutes(9)), Is.False);
            Assert.That(AutonomousCampRouteQuarantine.ReportFailure(camp, 103, start.AddMinutes(11)), Is.True);
            Assert.That(AutonomousCampRouteQuarantine.IsQuarantined(camp, start.AddMinutes(12)), Is.True);
        }
        finally { AutonomousCampRouteQuarantine.ResetForTests(); }
    }

    [Test]
    public void ACloseServiceNotReachedInThreeMinutesIsGivenUp()
    {
        const long start = 1_000_000;
        long limit = AutonomousServiceReachability.NearbyApproachLimitMilliseconds;
        // Wilered under Grimspound's Kel: 2,400 units away for twelve minutes.
        Assert.That(AutonomousServiceReachability.NearbyApproachTimedOut(true, 2_400, start, start + limit - 1), Is.False);
        Assert.That(AutonomousServiceReachability.NearbyApproachTimedOut(true, 2_400, start, start + limit), Is.True);
        // A far or cross-zone service keeps the existing rules; no clock means no timeout.
        Assert.That(AutonomousServiceReachability.NearbyApproachTimedOut(true, 9_000, start, start + 10 * limit), Is.False);
        Assert.That(AutonomousServiceReachability.NearbyApproachTimedOut(false, 2_400, start, start + 10 * limit), Is.False);
        Assert.That(AutonomousServiceReachability.NearbyApproachTimedOut(true, 2_400, 0, start + 10 * limit), Is.False);
    }

    [Test]
    public void ATownCircleContainsABotAboveItsCentreOnlyWhenMeasuredFlat()
    {
        // Caer Witrin's circle (radius 1,000, centre Z 2448) and a bot rescued on its town break there.
        var caerWitrin = new Area.Circle("Caer Witrin", 437031, 650943, 2448, 1000);
        Assert.That(caerWitrin.IsContaining(436628, 651118, 3390, true), Is.False, "the old 3D test");
        Assert.That(caerWitrin.IsContaining(436628, 651118, 3390, false), Is.True, "the flat test the break uses");
    }

    [Test]
    public void AFrozenTravellingPartyEndsAfterFiveMinutes()
    {
        var five = AutonomousStuckWatchdog.PartyTravelStallThreshold;
        var justUnder = five - System.TimeSpan.FromSeconds(1);
        Assert.That(AutonomousStuckWatchdog.IsPartyTravelStall(true, "Traveling in group formation", five, false), Is.True);
        Assert.That(AutonomousStuckWatchdog.IsPartyTravelStall(true, "Traveling to svartalf watcher", five, false), Is.True);
        Assert.That(AutonomousStuckWatchdog.IsPartyTravelStall(true, "Traveling in group formation", justUnder, false), Is.False);
        // Fighting, casting, resting or riding is not a stall, and neither is any other hold or a solo bot.
        Assert.That(AutonomousStuckWatchdog.IsPartyTravelStall(true, "Traveling in group formation", five, true), Is.False);
        Assert.That(AutonomousStuckWatchdog.IsPartyTravelStall(true, "Waiting for group members", five, false), Is.False);
        Assert.That(AutonomousStuckWatchdog.IsPartyTravelStall(false, "Traveling to svartalf watcher", five, false), Is.False);
        Assert.That(AutonomousStuckWatchdog.IsPartyTravelStall(true, null, five, false), Is.False);
    }

    [Test]
    public void APartyBelowPullReadinessRestsEvenWithoutAFight()
    {
        // The frozen parties: a member below 90/80/80 with no fight near the leader got neither a rest nor a pull.
        Assert.That(AutonomousBotGroupCoordinator.StartsBetweenPullRecovery(false, true, false), Is.True);
        // The old cases stay as they were.
        Assert.That(AutonomousBotGroupCoordinator.StartsBetweenPullRecovery(true, true, true), Is.True);
        Assert.That(AutonomousBotGroupCoordinator.StartsBetweenPullRecovery(false, true, true), Is.False);
        // Before the task starts (meeting up), or outside group PvE, nothing new is started.
        Assert.That(AutonomousBotGroupCoordinator.StartsBetweenPullRecovery(false, false, false), Is.False);
    }

    [Test]
    public void RescuesOnDifferentSpotsOfOneCampBenchTheWholeFamily()
    {
        // Pale horse in Sheeroe Hills: three solo bots stalled on three different spots within 17 minutes.
        AutonomousCampRouteQuarantine.ResetForTests();
        var start = new System.DateTime(2026, 10, 19, 23, 41, 0, System.DateTimeKind.Utc);
        string family = AutonomousCampRouteQuarantine.FamilyKey(200, "Pale Horse ");
        try
        {
            Assert.That(family, Is.EqualTo("family:200:pale horse"));
            Assert.That(AutonomousCampRouteQuarantine.FamilyKey(200, ""), Is.Empty);
            Assert.That(AutonomousCampRouteQuarantine.IsFamilyQuarantined(200, "pale horse", start), Is.False);
            AutonomousCampRouteQuarantine.ReportFailure(family, 1, start);
            AutonomousCampRouteQuarantine.ReportFailure(family, 2, start.AddMinutes(17));
            Assert.That(AutonomousCampRouteQuarantine.ReportFailure(family, 3, start.AddMinutes(17)), Is.True);
            Assert.That(AutonomousCampRouteQuarantine.IsFamilyQuarantined(200, "pale horse", start.AddMinutes(18)), Is.True);
            // Another region's pale horses are not benched.
            Assert.That(AutonomousCampRouteQuarantine.IsFamilyQuarantined(100, "pale horse", start.AddMinutes(18)), Is.False);
        }
        finally { AutonomousCampRouteQuarantine.ResetForTests(); }
    }

    [Test]
    public void AHealerLetsTheSameSpellFinishInsteadOfRestartingIt()
    {
        // From stefanrows/OfflineDAoC: a cure mezz on a still-mezzed mate was stopped and restarted every turn.
        Assert.That(DOL.AI.Brain.BotBrain.IsAlreadyCastingSpell(true, 4321, 4321, Target, Target), Is.True);
        Assert.That(DOL.AI.Brain.BotBrain.IsAlreadyCastingSpell(true, 1234, 4321, Target, Target), Is.False, "a different spell may replace it");
        Assert.That(DOL.AI.Brain.BotBrain.IsAlreadyCastingSpell(false, 4321, 4321, Target, Target), Is.False);
        Assert.That(DOL.AI.Brain.BotBrain.IsAlreadyCastingSpell(true, null, 4321, Target, Target), Is.False);
        Assert.That(DOL.AI.Brain.BotBrain.IsAlreadyCastingSpell(true, 4321, 4321, Target, new object()), Is.False, "the same spell for another target may replace it");
    }
    private static readonly object Target = new();
    private sealed record Spawn(string Name, Zone Zone);
}
