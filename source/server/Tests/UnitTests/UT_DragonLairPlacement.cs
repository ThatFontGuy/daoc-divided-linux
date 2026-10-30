using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_DragonLairPlacement
    {
        [TestCase(eRealm.Albion, 390)]
        [TestCase(eRealm.Midgard, 3014)]
        [TestCase(eRealm.Hibernia, 2964)]
        public void GroundHomeIsReachableByNormalStationaryMelee(eRealm realm, int ground)
        {
            var home = DragonLairPlacement.Home(realm);
            Assert.That(new Point3D(home.X + 80, home.Y, ground).IsWithinRadius(home, 128), Is.True);
            Assert.That(new Point3D(home.X + 900, home.Y, ground).IsWithinRadius(home, 800), Is.False);
            home.Z += 3000;
            Assert.That(DragonLairPlacement.Home(realm).Z, Is.LessThan(home.Z));
            Assert.That(DragonLairPlacement.GroundFlags(GameNPC.eFlags.FLYING | GameNPC.eFlags.PEACE), Is.EqualTo(GameNPC.eFlags.PEACE));
        }

        [Test]
        public void SavedRowOnTheLairSetsTheHeightForThisWorld()
        {
            try
            {
                // The retail 1.130 mound stands 164 units below the classic one.
                Assert.That(DragonLairPlacement.Adopt(eRealm.Albion, 391326, 755351, 227), Is.True);
                var home = DragonLairPlacement.Home(eRealm.Albion);
                Assert.That((home.X, home.Y, home.Z), Is.EqualTo((391326, 755351, 227)));
                // A row away from the lair (a flight point, a moved row) never moves the home.
                Assert.That(DragonLairPlacement.Adopt(eRealm.Albion, 385865, 756961, 3504), Is.False);
                Assert.That(DragonLairPlacement.Adopt(eRealm.Albion, 391326, 755351, 3504), Is.False);
                Assert.That(DragonLairPlacement.Home(eRealm.Albion).Z, Is.EqualTo(227));
                Assert.That(DragonLairPlacement.Home(eRealm.Midgard).Z, Is.EqualTo(3014));
            }
            finally
            {
                DragonLairPlacement.Forget(eRealm.Albion);
            }
            Assert.That(DragonLairPlacement.Home(eRealm.Albion).Z, Is.EqualTo(391));
        }

        [Test]
        public void LivingDamageSourcesIncludeNpcBasedCompanionsAndPets()
        {
            Assert.That(DragonLairPlacement.CanReceiveDamageType(typeof(GamePlayer)), Is.True);
            Assert.That(DragonLairPlacement.CanReceiveDamageType(typeof(GameBot)), Is.True);
            Assert.That(DragonLairPlacement.CanReceiveDamageType(typeof(GameSummonedPet)), Is.True);
            Assert.That(DragonLairPlacement.CanReceiveDamageType(typeof(GameNPC)), Is.True);
            Assert.That(DragonLairPlacement.CanReceiveDamageType(typeof(GameObject)), Is.False);
        }
    }
}
