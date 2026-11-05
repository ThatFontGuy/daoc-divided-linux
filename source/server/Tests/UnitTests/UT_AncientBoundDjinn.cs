using System.Runtime.CompilerServices;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_AncientBoundDjinn
    {
        private const int ZoneOffset = 65536;

        private EpicTestServerScope _server;

        private sealed class Djinn : AncientBoundDjinn
        {
            private Djinn() : base(null) { }
            public ushort Model => VisibleModel;
        }

        [SetUp]
        public void SetUp()
        {
            _server = new EpicTestServerScope();
        }

        [TearDown]
        public void TearDown()
        {
            _server.Dispose();
        }

        // No constructor runs, so the djinn has its position but no movement component, and
        // reading X throws. That is a djinn before AddToWorld, as PermanentDjinn's constructor sees it.
        private static Djinn DjinnBeforeAddToWorld(ushort zoneId, int x, int y)
        {
            var region = new Region(new RegionData { Id = 79, Name = "test", Description = "test", Mobs = [] });
            region.Zones.Add(new Zone(region, zoneId, "test", ZoneOffset, ZoneOffset, 65536, 65536, zoneId, false, 0, false, 0, 0, 0, 0, 0));

            var djinn = (Djinn)RuntimeHelpers.GetUninitializedObject(typeof(Djinn));
            djinn.CurrentRegion = region;
            djinn.X = x;
            djinn.Y = y;
            return djinn;
        }

        [TestCase((ushort)81, 0x4ac)]
        [TestCase((ushort)76, 0x4ae)]
        [TestCase((ushort)137, 0x4ad)]
        [TestCase((ushort)73, 0x4aa)]
        public void VisibleModelComesFromTheZoneBeforeTheDjinnIsInTheWorld(ushort zoneId, int model)
        {
            Djinn djinn = DjinnBeforeAddToWorld(zoneId, ZoneOffset + 1000, ZoneOffset + 2000);

            Assert.That(djinn.Model, Is.EqualTo(model));
        }

        [Test]
        public void DjinnOutsideEveryZoneGetsTheDefaultModelInsteadOfAnError()
        {
            Djinn djinn = DjinnBeforeAddToWorld(81, 1000, 2000);

            Assert.That(djinn.Model, Is.EqualTo(0x4aa));
        }
    }
}
