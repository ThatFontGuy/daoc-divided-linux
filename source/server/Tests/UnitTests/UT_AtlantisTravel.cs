using DOL.GS;
using DOL.GS.Movement;
using DOL.GS.PacketHandler.Client.v168;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_AtlantisTravel
    {
        [TestCase((ushort) 73, 1049, true, Description = "Hesperos seabed")]
        [TestCase((ushort) 31, 7000, true, Description = "Midgard's copy of Mesothalassa")]
        [TestCase((ushort) 134, 3299, true, Description = "Hibernia's copy of Anatole")]
        [TestCase((ushort) 70, 3295, true, Description = "Ruins of Atlantis, a sea zone")]
        [TestCase((ushort) 72, 7296, true, Description = "Hibernia's copy of the Ruins")]
        [TestCase((ushort) 73, 8112, false, Description = "An island above the sea")]
        [TestCase((ushort) 82, 7112, false, Description = "Land of Atum lies below sea level but is land")]
        [TestCase((ushort) 81, 6418, false, Description = "Stygian Delta is land")]
        [TestCase((ushort) 1, 1000, false, Description = "Not Atlantis")]
        public void OnlySeaZoneSpawnsBelowTheSurfaceStayOffTheMesh(ushort zone, int z, bool expected)
        {
            Assert.That(Pathfinder.IsBelowAtlantisSea(zone, z), Is.EqualTo(expected));
        }

        [TestCase(444485, 551238, true, Description = "Dockmaster on the pier")]
        [TestCase(448007, 556030, true, Description = "Dockmistress set back from the pier")]
        [TestCase(460000, 551238, false, Description = "Too far away")]
        [TestCase(444485, 570000, false, Description = "Too far away")]
        public void RouteStartsWithinReachOfItsDockmaster(int x, int y, bool expected)
        {
            PathPoint start = new(442288, 552070, 7970, 1000, default);

            Assert.That(GameBoatStableMaster.IsRouteStartInReach(start, x, y), Is.EqualTo(expected));
        }

        [TestCase("skiff", true)]
        [TestCase("skiff3", true, Description = "Realm copies bought before the shipwright fix")]
        [TestCase("Viking_Longship", true)]
        [TestCase("viking_longship", true)]
        [TestCase("Viking_Longship2", true)]
        [TestCase("British_Cog2", true)]
        [TestCase("Elvish_Caravel", true)]
        [TestCase("red_hull_paint", false)]
        [TestCase("bt_notos_hesperos", false)]
        [TestCase(null, false)]
        public void BoatItemsAreRecognised(string itemId, bool expected)
        {
            Assert.That(GameBoat.IsBoatItem(itemId), Is.EqualTo(expected));
        }

        [TestCase(PlayerPositionUpdateHandler.StateFlags.SWIMMING, true)]
        [TestCase(PlayerPositionUpdateHandler.StateFlags.SWIMMING | PlayerPositionUpdateHandler.StateFlags.STRAFING_LEFT, true)]
        [TestCase((PlayerPositionUpdateHandler.StateFlags) 0, false)]
        [TestCase(PlayerPositionUpdateHandler.StateFlags.DEAD, false)]
        [TestCase(PlayerPositionUpdateHandler.StateFlags.FLYING, false)]
        [TestCase(PlayerPositionUpdateHandler.StateFlags.CLIMBING, false)]
        public void OnlyThePlainSwimmingStateCounts(PlayerPositionUpdateHandler.StateFlags flags, bool expected)
        {
            Assert.That(PlayerPositionUpdateHandler.IsSwimmingState(flags), Is.EqualTo(expected));
        }

        [TestCase((ushort) 1615, "Viking_Longship")]
        [TestCase((ushort) 1616, "skiff")]
        [TestCase((ushort) 1657, "Elvish_Caravel")]
        [TestCase((ushort) 2648, "scout_boat")]
        [TestCase((ushort) 1, null)]
        public void PackedBoatsBecomeTheItemTheyCameFrom(ushort model, string itemId)
        {
            Assert.That(GameBoat.ItemIdForModel(model), Is.EqualTo(itemId));
        }

        [Test]
        public void NoRouteIsNeverInReach()
        {
            Assert.That(GameBoatStableMaster.IsRouteStartInReach(null, 0, 0), Is.False);
        }
    }
}
