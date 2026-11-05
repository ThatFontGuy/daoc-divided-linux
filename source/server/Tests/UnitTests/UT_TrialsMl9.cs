using System.Collections.Generic;
using System.Linq;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl9
    {
        private static readonly string[] Names =
        {
            "Wings of Aerus", "Lachlen's Explorers", "Atlantis Warlords", "Kings of Aerus", "Scholars of Aerus",
            "Patrolling the City", "Uncontrolled Host", "Guardians of the Phoenix", "Centaur's Patrol", "Rise of the Phoenix",
        };

        private static List<TrialDefinition> Trials => Ml9.Trials().ToList();

        [Test]
        public void Steps_ExistInOrder()
        {
            Assert.That(Trials.Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(Trials.Select(trial => trial.Name), Is.EqualTo(Names));
            Assert.That(Trials.All(trial => trial.ML == 9 && trial.Zone == TrialZone.Aerus));
        }

        [Test]
        public void OnlyLachlenIsAGroupTrial()
        {
            Assert.That(Trials.Where(trial => trial.Scope == TrialScope.Group).Select(trial => trial.Step), Is.EqualTo(new[] { 2 }));
            Assert.That(Trials.Where(trial => trial.Step != 2).All(trial => trial.Scope == TrialScope.Raid));
        }

        [Test]
        public void Finale_NeedsTheFirstNine()
        {
            Assert.That(TrialManager.Required(Trials[9]), Is.EqualTo(Enumerable.Range(1, 9)));
        }

        [Test]
        public void Anchors_LieInsideTheCityOfAerus()
        {
            foreach (TrialDefinition trial in Trials)
            {
                Assert.That(trial.Anchor.X, Is.InRange(8192, 73728), trial.Key);
                Assert.That(trial.Anchor.Y, Is.InRange(8192, 73728), trial.Key);
            }
        }

        [Test]
        public void Tuning_StaysInsideTheBrief()
        {
            foreach (TrialDefinition trial in Trials)
            {
                Assert.That(trial.TimeLimitSeconds, Is.InRange(900, 2400), trial.Key);
                foreach (TrialMobSpec mob in trial.Phases.SelectMany(phase => phase.Mobs).Where(mob => !mob.Objective))
                    Assert.That((int)mob.Level, Is.InRange(55, 70), mob.Name);
            }
        }

        [Test]
        public void Replaces_NeverTakeACommonCreature()
        {
            string[] common = { "avriel", "iaculus", "enraged iaculus", "elusive jinni", "avriel young" };
            Assert.That(Trials.SelectMany(trial => trial.Replaces).Intersect(common), Is.Empty);
        }

        [Test]
        public void Kyros_CyclesThroughFourForms()
        {
            Assert.That(Ml9.KyrosForm(1), Is.EqualTo(0));
            Assert.That(Ml9.KyrosForm(Ml9.KyrosFormSeconds), Is.EqualTo(1));
            Assert.That(Ml9.KyrosForm(Ml9.KyrosFormSeconds * 3), Is.EqualTo(3));
            Assert.That(Ml9.KyrosForm(Ml9.KyrosFormSeconds * 4), Is.EqualTo(0));
        }

        [Test]
        public void Lachlen_RunsOutOfHeals()
        {
            Assert.That(Ml9.LachlenMayHeal(Ml9.LachlenHeals - 1), Is.True);
            Assert.That(Ml9.LachlenMayHeal(Ml9.LachlenHeals), Is.False);
        }

        [Test]
        public void Terrible_BreedsButStopsAtEight()
        {
            Assert.That(Ml9.TerribleBrood(0), Is.EqualTo(1));
            Assert.That(Ml9.TerribleBrood(3), Is.EqualTo(3));
            Assert.That(Ml9.TerribleBrood(6), Is.EqualTo(2));
            Assert.That(Ml9.TerribleBrood(8), Is.EqualTo(0));
        }

        [Test]
        public void Chan_NoticesOnlyThoseOnHisRoad()
        {
            Assert.That(Ml9.PastChan(Ml9.BypassX + 1, 12049), Is.True);
            Assert.That(Ml9.PastChan(Ml9.BypassX, 12049), Is.False);
            Assert.That(Ml9.PastChan(Ml9.BypassX + 1, 15900), Is.False);
        }

        [TestCase(3, 75)]
        [TestCase(2, 50)]
        [TestCase(1, 25)]
        [TestCase(0, 0)]
        public void Phoenix_LosesAQuarterForEachGenerator(int generators, int floor)
        {
            Assert.That(Ml9.PhoenixFloor(generators), Is.EqualTo(floor));
        }

        [Test]
        public void Phoenix_WeakensAsGeneratorsFall()
        {
            Assert.That(Ml9.PhoenixFireball(3), Is.GreaterThan(Ml9.PhoenixFireball(2)));
            Assert.That(Ml9.PhoenixFireball(3), Is.LessThanOrEqualTo(300));
            Assert.That(Ml9.PhoenixFireball(0), Is.Zero);
            Assert.That(Ml9.PhoenixFlare(0), Is.Zero);
        }

        [Test]
        public void Phoenix_LeashCoversTheGenerators()
        {
            Assert.That(Trials[9].LeashRange, Is.GreaterThan(10500));
            Assert.That(Trials[9].Phases.SelectMany(phase => phase.Mobs).Count(mob => mob.Name == "Phoenix Generator"), Is.EqualTo(3));
        }
    }
}
