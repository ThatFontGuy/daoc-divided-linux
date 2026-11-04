using System.Linq;
using DOL.GS;
using NUnit.Framework;
using static DOL.GS.EffectWindows;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_EffectWindows
    {
        [Test]
        public void HarmfulComeFirstThenYoursThenTheSoonestToEnd()
        {
            Effect[] effects =
            {
                new("Endless aura", 1, 0, 0, true, false),
                new("Long buff", 2, 600, 1200, true, false),
                new("Your short buff", 3, 30, 60, true, true),
                new("Snare", 4, 12, 20, false, false),
                new("Your DoT", 5, 18, 24, false, true),
            };

            string[] order = Order(effects).Select(effect => effect.Name).ToArray();

            Assert.That(order, Is.EqualTo(new[] { "Your DoT", "Snare", "Your short buff", "Long buff", "Endless aura" }));
        }

        [Test]
        public void TheSnapshotSendsAsANamedEventTheLauncherReads()
        {
            var snapshot = new Snapshot(new[] { new Effect("Strength", 1, 5, 10, true, true) }, new Unit[0],
                new Unit("crab", 12, 40, new Effect[0]));

            string frame = CombatNumbers.Frame("effects", snapshot);

            Assert.That(frame, Does.StartWith("event: effects\ndata: {\"self\":[{\"name\":\"Strength\",\"icon\":1,\"seconds\":5,\"total\":10,\"good\":true,\"mine\":true}]"));
            Assert.That(frame, Does.Contain("\"target\":{\"name\":\"crab\",\"level\":12,\"health\":40,\"effects\":[]}"));
            Assert.That(frame, Does.EndWith("\n\n"));
        }
    }
}
