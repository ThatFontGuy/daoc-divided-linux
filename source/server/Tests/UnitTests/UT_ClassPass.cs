using DOL.GS.PlayerClass;
using DOL.GS.Realm;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_ClassPass
    {
        [Test]
        public void HitPointsMatchLive()
        {
            Assert.That(new ClassMaulerAlb().BaseHP, Is.EqualTo(720));
            Assert.That(new ClassMaulerMid().BaseHP, Is.EqualTo(720));
            Assert.That(new ClassMaulerHib().BaseHP, Is.EqualTo(720));
            Assert.That(new ClassValkyrie().BaseHP, Is.EqualTo(760));
            Assert.That(new ClassVampiir().BaseHP, Is.EqualTo(880));
        }

        [Test]
        public void LiveRaceAndClassPairsCanBeCreated()
        {
            Assert.That(new ClassShadowblade().EligibleRaces, Does.Contain(PlayerRace.Dwarf));
            Assert.That(new ClassRanger().EligibleRaces, Does.Contain(PlayerRace.Sylvan));
            Assert.That(new ClassChampion().EligibleRaces, Does.Contain(PlayerRace.Sylvan));
            Assert.That(new ClassBlademaster().EligibleRaces, Does.Contain(PlayerRace.Lurikeen));
            Assert.That(new ClassNightshade().EligibleRaces, Does.Contain(PlayerRace.Celt));
            Assert.That(new ClassAnimist().EligibleRaces, Does.Contain(PlayerRace.Elf));
            Assert.That(new ClassWizard().EligibleRaces, Does.Contain(PlayerRace.Inconnu));
            Assert.That(new ClassMinstrel().EligibleRaces, Does.Contain(PlayerRace.Inconnu));
            Assert.That(new ClassInfiltrator().EligibleRaces, Does.Contain(PlayerRace.Highlander));
            Assert.That(new ClassFriar().EligibleRaces, Is.EquivalentTo(new[] { PlayerRace.Avalonian, PlayerRace.Briton, PlayerRace.Highlander }));
        }
    }
}
