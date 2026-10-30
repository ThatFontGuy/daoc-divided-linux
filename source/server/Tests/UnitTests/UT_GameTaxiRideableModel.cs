using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_GameTaxiRideableModel
    {
        [TestCase((ushort)449, (ushort)2173)]
        [TestCase((ushort)450, (ushort)2172)]
        [TestCase((ushort)448, (ushort)2174)]
        [TestCase((ushort)413, (ushort)2173)]
        [TestCase((ushort)2127, (ushort)2172)]
        public void OldAndUnsaddledHorsesRideTheSaddledMountRig(ushort model, ushort saddled)
        {
            Assert.That(GameTaxi.RideableModel(model), Is.EqualTo(saddled));
        }

        [TestCase((ushort)2172)]
        [TestCase((ushort)2174)]
        [TestCase((ushort)1207)]   // dragonfly
        [TestCase((ushort)1236)]   // gryphon
        public void SaddledHorsesAndFlyingTaxisKeepTheirModel(ushort model)
        {
            Assert.That(GameTaxi.RideableModel(model), Is.EqualTo(model));
        }
    }
}
