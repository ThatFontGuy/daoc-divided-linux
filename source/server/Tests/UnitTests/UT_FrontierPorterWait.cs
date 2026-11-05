using System.Linq;
using NUnit.Framework;

namespace DOL.GS.Tests;

/// <summary>
/// Overnight run of 2026-10-31: 714 of 1,669 fifteen-minute rescues were bots "Waiting for a frontier teleporter" in
/// capitals, Atlantis and the Shrouded Isles, committed to a siege in a frontier only a porter reaches.
/// </summary>
[TestFixture, NonParallelizable]
public class UT_FrontierPorterWait
{
    [SetUp] public void ResetEvents() => RvrEventTestState.Clear();
    [TearDown] public void ClearEvents() => RvrEventTestState.Clear();

    // The regions the stuck bots stood in, for the sieges they were sent to.
    [TestCase(eRealm.Hibernia, (ushort)201, (ushort)100, TestName = "Hibernian in Tir na Nog to Midgard")]
    [TestCase(eRealm.Hibernia, (ushort)181, (ushort)100, TestName = "Hibernian in Hy Brasil to Midgard")]
    [TestCase(eRealm.Hibernia, (ushort)130, (ushort)100, TestName = "Hibernian in Atlantis to Midgard")]
    [TestCase(eRealm.Albion, (ushort)51, (ushort)100, TestName = "Albion in Avalon to Midgard")]
    [TestCase(eRealm.Albion, (ushort)73, (ushort)100, TestName = "Albion in Atlantis to Midgard")]
    [TestCase(eRealm.Albion, (ushort)10, (ushort)100, TestName = "Albion in Camelot to Midgard")]
    [TestCase(eRealm.Midgard, (ushort)101, (ushort)200, TestName = "Midgard in Jordheim to Hibernia")]
    public void ABotOutsideTheFrontiersGoesToItsOwnFrontierFirst(eRealm realm, ushort current, ushort destination) =>
        Assert.That(AutonomousFrontierTransport.NeedsHomeFrontierFirst(realm, current, destination), Is.True);

    [Test]
    public void TheHomeFrontierLegIsOnlyForAPorterJourneyFromOutsideTheFrontiers()
    {
        foreach (ushort frontier in new ushort[] { 1, 100, 200 })
            Assert.That(AutonomousFrontierTransport.NeedsHomeFrontierFirst(eRealm.Hibernia, frontier, 100), Is.False,
                "a bot in a frontier region boards its porter there");
        Assert.That(AutonomousFrontierTransport.NeedsHomeFrontierFirst(eRealm.Hibernia, 201, 130), Is.False, "not a frontier");
        Assert.That(AutonomousFrontierTransport.NeedsHomeFrontierFirst(eRealm.None, 201, 100), Is.False, "no realm, no porter");
    }

    [Test]
    public void EveryRealmHasABorderKeepInItsOwnFrontierToWalkTo()
    {
        foreach ((eRealm realm, ushort home) in new[] { (eRealm.Albion, (ushort)1), (eRealm.Midgard, (ushort)100), (eRealm.Hibernia, (ushort)200) })
        {
            Assert.That(AutonomousRvrStaging.TryGetBorderKeep(realm, out var keep), Is.True);
            Assert.That(keep.RegionId, Is.EqualTo(home));
            Assert.That(AutonomousFrontierTransport.Destination(realm, home).Medallion, Is.EqualTo("home_necklace"));
        }
    }

    [Test]
    public void TheWaitIsBoundedAndShorterThanTheWatchdog()
    {
        long limit = AutonomousFrontierTransport.PorterWaitMilliseconds;
        Assert.That(AutonomousFrontierTransport.PorterWaitExpired(0, limit * 10), Is.False, "no wait running");
        Assert.That(AutonomousFrontierTransport.PorterWaitExpired(1_000, 1_000 + limit - 1), Is.False);
        Assert.That(AutonomousFrontierTransport.PorterWaitExpired(1_000, 1_000 + limit), Is.True);
        Assert.That(limit, Is.LessThan((long)AutonomousStuckWatchdog.StuckThreshold.TotalMilliseconds));
    }

    [Test]
    public void GivingUpLeavesTheSiegeAndDeliversTheReleaseOnce()
    {
        long now = GameLoop.GameLoopTime + 1;
        const string force = "rvr-porter-test";
        var keep = new AutonomousRvrEventLayer.LiveObjective("rvr-keep-porter", "keep Hlidskialf Faste",
            AutonomousRvrEventLayer.Intent.AssaultKeep, eRealm.Midgard, 100, 0, 0, 0, false, 0, 0, 10, 2);
        AutonomousRvrEventLayer.ChooseOrJoin(new(force, eRealm.Hibernia, 8, 50, 2), [keep], now, 0);
        Assert.That(AutonomousRvrEventLayer.KeepPlan(force, eRealm.Hibernia, now), Is.Not.Null, "committed to the siege");

        AutonomousRvrEventLayer.ReleaseForce(force, "No frontier teleporter");

        Assert.That(AutonomousRvrEventLayer.KeepPlan(force, eRealm.Hibernia, now), Is.Null);
        Assert.That(AutonomousRvrEventLayer.IsEventForce(force, now), Is.False);
        Assert.That(AutonomousRvrEventLayer.TryConsumeRelease(force, now, out string reason), Is.True);
        Assert.That(reason, Is.EqualTo("No frontier teleporter"));
        Assert.That(AutonomousRvrEventLayer.TryConsumeRelease(force, now, out _), Is.False);
    }

    [Test]
    public void ReleasingAForceWithNoEventStillReachesItsOwner()
    {
        AutonomousRvrEventLayer.ReleaseForce("rvr-roamer", "No frontier teleporter");
        Assert.That(AutonomousRvrEventLayer.TryConsumeRelease("rvr-roamer", GameLoop.GameLoopTime + 1, out string reason), Is.True);
        Assert.That(reason, Is.EqualTo("No frontier teleporter"));
    }
}
