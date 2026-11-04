using System.Linq;
using DOL.GS;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl3
    {
        private static readonly string[] Names =
        {
            "Moirai's Destruction", "Kepa's Downfall", "Casta's Annihilation", "Laodamedia's Furious End", "Antioos' Deceptive Death",
            "Glowing Barracuda's Fading", "Shraogh's Fear Removed", "Sting Ray's Power Absorbed", "Sinovia's Power Relinquished", "Conquering Twilight",
        };

        private static readonly TrialScope[] Scopes =
        {
            TrialScope.Group, TrialScope.Raid, TrialScope.Raid, TrialScope.Raid, TrialScope.Group,
            TrialScope.Group, TrialScope.Group, TrialScope.Group, TrialScope.Group, TrialScope.Raid,
        };

        [Test]
        public void EveryStepExistsInOrder()
        {
            Assert.That(Ml3.Trials().Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(Ml3.Trials().Select(trial => trial.Name), Is.EqualTo(Names));
            Assert.That(Ml3.Trials().Select(trial => trial.ML).Distinct(), Is.EqualTo(new[] { 3 }));
        }

        [Test]
        public void ScopesMatchTheWindowAndReports()
        {
            Assert.That(Ml3.Trials().Select(trial => trial.Scope), Is.EqualTo(Scopes));
        }

        [Test]
        public void Finale_NeedsAllNineSteps()
        {
            TrialDefinition finale = Ml3.Trials().Last();
            Assert.That(finale.RequiresSteps, Is.Null);
            Assert.That(TrialManager.Required(finale), Is.EqualTo(Enumerable.Range(1, 9)));
        }

        [Test]
        public void EverythingButShraoghIsInTheTemple()
        {
            foreach (TrialDefinition trial in Ml3.Trials())
            {
                Assert.That(trial.Zone, Is.EqualTo(trial.Step == 7 ? TrialZone.Oceanus : TrialZone.Twilight), trial.Key);
                if (trial.Zone == TrialZone.Twilight)
                {
                    Assert.That(trial.Anchor.X, Is.InRange(8192, 8192 + 65536), trial.Key);
                    Assert.That(trial.Anchor.Y, Is.InRange(8192, 8192 + 65536), trial.Key);
                }
            }
        }

        [Test]
        public void TimeLimitsAreSane()
        {
            Assert.That(Ml3.Trials().Select(trial => trial.TimeLimitSeconds), Is.All.InRange(900, 2400));
        }

        [Test]
        public void Replaces_NeverNamesCommonCreatures()
        {
            string[] common = { "cobra", "lethal cobra", "pregnant cobra", "gorgon guardian", "water crocodile" };
            Assert.That(Ml3.Trials().SelectMany(trial => trial.Replaces).Intersect(common), Is.Empty);
        }

        [Test]
        public void RageMeter_FiresOnAStreakOfOneDamageType()
        {
            RageMeter meter = new(3, 30);
            Assert.That(meter.Hit(eDamageType.Slash), Is.False);
            Assert.That(meter.Hit(eDamageType.Slash), Is.False);
            Assert.That(meter.Hit(eDamageType.Slash), Is.True);
        }

        [Test]
        public void RageMeter_MixedDamageTypesKeepHerCalm()
        {
            RageMeter meter = new(3, 30);
            foreach (eDamageType type in new[] { eDamageType.Slash, eDamageType.Crush, eDamageType.Thrust, eDamageType.Slash, eDamageType.Slash, eDamageType.Crush })
                Assert.That(meter.Hit(type), Is.False);
        }

        [Test]
        public void RageMeter_CalmsBeforeRagingAgain()
        {
            RageMeter meter = new(2, 2);
            meter.Hit(eDamageType.Slash);
            Assert.That(meter.Hit(eDamageType.Slash), Is.True);
            Assert.That(meter.Hit(eDamageType.Slash), Is.False);
            Assert.That(meter.Hit(eDamageType.Slash), Is.False);
            meter.Second();
            meter.Second();
            Assert.That(meter.Hit(eDamageType.Slash), Is.True);
        }

        [Test]
        public void InRing_LeavesTheCentreOfThePlatformSafe()
        {
            Assert.That(Ml34Kit.InRing(100, 250, 1100), Is.False);
            Assert.That(Ml34Kit.InRing(600, 250, 1100), Is.True);
            Assert.That(Ml34Kit.InRing(1500, 250, 1100), Is.False);
        }

        [Test]
        public void Scaled_ShrinksWavesButKeepsAMinimum()
        {
            Assert.That(Ml34Kit.Scaled(12, 1.0), Is.EqualTo(12));
            Assert.That(Ml34Kit.Scaled(12, 0.5), Is.EqualTo(6));
            Assert.That(Ml34Kit.Scaled(12, 0.25), Is.EqualTo(3));
            Assert.That(Ml34Kit.Scaled(3, 0.25), Is.EqualTo(2));
            Assert.That(Ml34Kit.Scaled(1, 0.25), Is.EqualTo(1));
        }

        [Test]
        public void On_PlacesPointsAroundTheCentre()
        {
            TrialPoint center = new(1000, 1000, 50);
            TrialPoint east = Ml34Kit.On(center, 100, 0, 4);
            Assert.That((east.X, east.Y, east.Z), Is.EqualTo((1100, 1000, 50)));
            Assert.That(Ml34Kit.Distance(center, Ml34Kit.On(center, 100, 1, 4)), Is.EqualTo(100).Within(2));
        }
    }
}
