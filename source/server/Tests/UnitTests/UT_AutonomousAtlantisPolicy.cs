using System.Linq;
using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_AutonomousAtlantisPolicy
    {
        [TestCase(eRealm.Albion, (ushort) 73, true)]
        [TestCase(eRealm.Midgard, (ushort) 30, true)]
        [TestCase(eRealm.Hibernia, (ushort) 130, true)]
        [TestCase(eRealm.Albion, (ushort) 30, false, Description = "Another realm's copy")]
        [TestCase(eRealm.Midgard, (ushort) 130, false)]
        [TestCase(eRealm.Albion, (ushort) 70, false, Description = "The Halls have no usable navmesh")]
        [TestCase(eRealm.Albion, (ushort) 1, false)]
        public void BotsUseOnlyTheirRealmsAtlantis(eRealm realm, ushort region, bool expected)
        {
            Assert.That(AutonomousAtlantisPolicy.IsOpenTo(realm, region), Is.EqualTo(expected));
        }

        [TestCase(44, false)]
        [TestCase(45, true)]
        [TestCase(50, true)]
        public void LowLevelPartiesStayHome(int level, bool expected)
        {
            Assert.That(AutonomousOrdinaryPveRealmPolicy.CanAssignCamp(eRealm.Albion, 73, 82, level), Is.EqualTo(expected));
        }

        [Test]
        public void AnotherRealmsCopyGetsNoCamps()
        {
            Assert.That(AutonomousOrdinaryPveRealmPolicy.CanAssignCamp(eRealm.Midgard, 73, 82, 50), Is.False);
        }

        [Test]
        public void ClassicCampsAreUnchanged()
        {
            Assert.That(AutonomousOrdinaryPveRealmPolicy.CanAssignCamp(eRealm.Albion, 1, 2, 10), Is.True);
        }

        [TestCase((ushort) 74, 3000, false, Description = "The seabed, off the mesh")]
        [TestCase((ushort) 74, 8100, true, Description = "An island")]
        [TestCase((ushort) 82, 7112, true, Description = "Land of Atum lies below sea level")]
        public void CampsStayOnLand(ushort zone, int z, bool expected)
        {
            Assert.That(AutonomousAtlantisPolicy.IsLandSpawn(zone, z), Is.EqualTo(expected));
        }

        [TestCase("Hesperos", true)]
        [TestCase("Delta", true)]
        [TestCase("Green Glades", true)]
        [TestCase("Typhon's Reach", true)]
        [TestCase("Land of Atum", false, Description = "Lands among 101 aggressive monsters")]
        [TestCase("Talos", false, Description = "A boss door")]
        public void BotsOnlyTeleportToRealStones(string destination, bool expected)
        {
            Assert.That(AutonomousAtlantisPolicy.IsStoneDestination(destination), Is.EqualTo(expected));
        }

        [Test]
        public void ProvenCampsCoverEveryRealmsCopy()
        {
            // Stygian Delta is Albion zone 81, Midgard 38, Hibernia 138. The point is the middle of a proven cell.
            const int x = 296136;
            const int y = 400384;
            Assert.That(AutonomousAtlantisPolicy.IsProvenCamp(81, x, y), Is.True);

            Assert.That(AutonomousAtlantisPolicy.IsProvenCamp(38, x, y), Is.True);
            Assert.That(AutonomousAtlantisPolicy.IsProvenCamp(138, x, y), Is.True);
        }

        [Test]
        public void UnprovenGroundIsNeverACamp()
        {
            Assert.That(AutonomousAtlantisPolicy.IsProvenCamp(81, 1, 1), Is.False);
        }

        [Test]
        public void EveryRealmGetsAWayInAndBack()
        {
            DbZonePoint[] edges = AutonomousAtlantisPolicy.GatewayEdges();

            Assert.Multiple(() =>
            {
                Assert.That(edges, Has.Length.EqualTo(6));
                Assert.That(edges.Select(edge => edge.Id).Distinct().Count(), Is.EqualTo(6));
                Assert.That(edges.All(AutonomousWorldBotController.IsAuthoritativeZonePointEdge), Is.True);

                foreach (DbZonePoint edge in edges)
                {
                    Assert.That(edges.Any(back => back.Realm == edge.Realm && back.SourceRegion == edge.TargetRegion &&
                                                  back.TargetRegion == edge.SourceRegion), Is.True);
                }
            });
        }
    }
}
