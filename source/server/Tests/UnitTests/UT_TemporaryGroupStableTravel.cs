using System.Reflection;
using System.Runtime.CompilerServices;
using NUnit.Framework;

namespace DOL.GS.Tests;

[TestFixture]
public sealed class UT_TemporaryGroupStableTravel
{
    [Test]
    public void GamebotsFollowingAPlayersGroupComeThroughTransfers()
    {
        var player = (GamePlayer)RuntimeHelpers.GetUninitializedObject(typeof(GamePlayer));
        var other = (GamePlayer)RuntimeHelpers.GetUninitializedObject(typeof(GamePlayer));
        var gamebot = (GameBot)RuntimeHelpers.GetUninitializedObject(typeof(GameBot));
        PropertyInfo leader = typeof(GameBot).GetProperty(nameof(GameBot.PlayerGroupLeader))!;

        Assert.That(TemporaryGroupStableTravel.FollowsThroughTransfers(gamebot, player), Is.False, "an independent gamebot travels on its own");
        leader.SetValue(gamebot, player);
        Assert.Multiple(() =>
        {
            Assert.That(TemporaryGroupStableTravel.FollowsThroughTransfers(gamebot, player), Is.True, "it follows the player it grouped with");
            Assert.That(TemporaryGroupStableTravel.FollowsThroughTransfers(gamebot, other), Is.False, "but not another player");
            Assert.That(TemporaryGroupStableTravel.FollowsThroughTransfers(null, player), Is.False);
        });
    }

    [Test]
    public void OnlyInRangeTemporaryGroupedFollowersMirrorAPlayersRide()
    {
        Assert.Multiple(() =>
        {
            Assert.That(TemporaryGroupStableTravel.IsEligibleForMirroredRide(true, true, true, true, true, 650), Is.True);
            Assert.That(TemporaryGroupStableTravel.IsEligibleForMirroredRide(false, true, true, true, true, 10), Is.False);
            Assert.That(TemporaryGroupStableTravel.IsEligibleForMirroredRide(true, true, true, false, true, 10), Is.False);
            Assert.That(TemporaryGroupStableTravel.IsEligibleForMirroredRide(true, true, true, true, false, 10), Is.False);
            Assert.That(TemporaryGroupStableTravel.IsEligibleForMirroredRide(true, true, true, true, true, 651), Is.False);
        });
    }

    [Test]
    public void ConfirmedSameZoneMoveToRelocatesAndPreservesEligibleGroupHelpers()
    {
        Assert.Multiple(() =>
        {
            Assert.That(TemporaryGroupStableTravel.ShouldRelocateForOwnerTransfer(true, true, true, true, 1, 1, 10, 10), Is.True);
            Assert.That(TemporaryGroupStableTravel.ShouldRelocateForOwnerTransfer(true, true, false, true, 1, 1, 10, 10), Is.False,
                "the helper must still belong to the player's existing group");
        });
    }

    [Test]
    public void ConfirmedCrossZoneAndCrossRegionTransferRelocateOnlyTemporaryGroupedFollowers()
    {
        Assert.Multiple(() =>
        {
            Assert.That(TemporaryGroupStableTravel.ShouldRelocateForOwnerTransfer(true, true, true, true, 1, 2, 10, 10), Is.True);
            Assert.That(TemporaryGroupStableTravel.ShouldRelocateForOwnerTransfer(true, true, true, true, 1, 1, 10, 11), Is.True);
            Assert.That(TemporaryGroupStableTravel.ShouldRelocateForOwnerTransfer(true, false, true, true, 1, 2, 10, 11), Is.False,
                "bots that do not follow the player (independent gamebots) travel on their own");
        });
    }

    [Test]
    public void OrdinaryWalkingAcrossBoundaryDoesNotTriggerTeleportCohesion()
    {
        Assert.That(TemporaryGroupStableTravel.ShouldRelocateForOwnerTransfer(false, true, true, true, 1, 1, 10, 11), Is.False);
        Assert.That(TemporaryGroupStableTravel.ShouldRelocateForOwnerTransfer(false, true, true, true, 1, 2, 10, 10), Is.False);
    }
}
