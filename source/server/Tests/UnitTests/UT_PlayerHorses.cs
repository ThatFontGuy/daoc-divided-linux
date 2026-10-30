using DOL.GS;
using DOL.GS.ServerProperties;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_PlayerHorses
    {
        [TestCase(79, eHorseSaddleBag.None)]
        [TestCase(80, eHorseSaddleBag.LeftFront)]
        [TestCase(83, eHorseSaddleBag.LeftFront)]
        [TestCase(84, eHorseSaddleBag.RightFront)]
        [TestCase(88, eHorseSaddleBag.LeftRear)]
        [TestCase(92, eHorseSaddleBag.RightRear)]
        [TestCase(95, eHorseSaddleBag.RightRear)]
        [TestCase(96, eHorseSaddleBag.None)]
        public void EachSaddlebagOpensItsOwnFourSlots(int slot, eHorseSaddleBag bag)
        {
            Assert.That(GamePlayer.SaddleBagForHorseSlot(slot), Is.EqualTo((byte)bag));
        }

        [TestCase("62;63;84", 63, true)]
        [TestCase("62, 63 ,84", 84, true)]
        [TestCase("62;63;84", 1, false)]
        [TestCase("62;63;84", 0, false)]
        [TestCase("", 62, false)]
        [TestCase("abc;;62", 62, true)]
        public void FlyingMountsComeFromTheServerSetting(string setting, int mount, bool flies)
        {
            string previous = Properties.FLYING_MOUNT_IDS;
            try
            {
                Properties.FLYING_MOUNT_IDS = setting;
                Assert.That(GamePlayer.ControlledHorse.IsFlyingMountId((byte)mount), Is.EqualTo(flies));
            }
            finally
            {
                Properties.FLYING_MOUNT_IDS = previous;
            }
        }

        [TestCase(eRealm.Albion, 0)]
        [TestCase(eRealm.Hibernia, 17)]
        [TestCase(eRealm.Midgard, 34)]
        public void UnsaddledHorseShowsItsRealmsBasicSaddle(eRealm realm, int theme)
        {
            Assert.That(GamePlayer.ControlledHorse.RealmBasicSaddle(realm), Is.EqualTo((byte)theme));
        }
    }
}
