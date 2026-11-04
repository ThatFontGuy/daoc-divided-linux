using System.Collections.Generic;
using System.Linq;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl10
    {
        private static List<TrialDefinition> Trials => Ml10.Trials().ToList();

        [Test]
        public void Steps_ExistInOrder()
        {
            Assert.That(Trials.Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 5)));
            Assert.That(Trials.Select(trial => trial.Name), Is.EqualTo(new[] { "Sagittarius", "Scorpius", "Centaurus", "Leo", "Draco" }));
            Assert.That(Trials.All(trial => trial.ML == 10 && trial.Scope == TrialScope.Raid));
        }

        [Test]
        public void EachStep_NeedsAllTheEarlierOnes()
        {
            foreach (TrialDefinition trial in Trials)
                Assert.That(TrialManager.Required(trial), Is.EqualTo(Enumerable.Range(1, trial.Step - 1)), trial.Key);
        }

        [Test]
        public void Anchors_AreDistinctAndInsideTheCity()
        {
            Assert.That(Trials.Select(trial => trial.Anchor).Distinct().Count(), Is.EqualTo(5));
            foreach (TrialDefinition trial in Trials)
                Assert.That(trial.Anchor.X, Is.InRange(8192, 73728), trial.Key);
        }

        [Test]
        public void Party_StaysLeashedOnTheIsland()
        {
            foreach (TrialDefinition trial in Trials)
            {
                double dx = trial.Anchor.X - Ml10.Isle.X, dy = trial.Anchor.Y - Ml10.Isle.Y, dz = trial.Anchor.Z - Ml10.Isle.Z;
                Assert.That(System.Math.Sqrt(dx * dx + dy * dy + dz * dz) + 1000, Is.LessThan(trial.LeashRange), trial.Key);
            }
        }

        [Test]
        public void EveryIslandMonster_HasItsOwnPlace()
        {
            foreach (TrialDefinition trial in Trials)
                Assert.That(trial.Phases.SelectMany(phase => phase.Mobs).All(mob => mob.At != null), trial.Key);
        }

        [Test]
        public void Party_GoesHomeBeforeTheClockRunsOut()
        {
            foreach (TrialDefinition trial in Trials)
                Assert.That(trial.TimeLimitSeconds, Is.GreaterThan(Ml10.ReturnAtSeconds), trial.Key);
        }

        [Test]
        public void Sagittarius_WardsSixSecondsInThirty()
        {
            Assert.That(Enumerable.Range(0, 30).Count(Ml10.SagittariusWarded), Is.EqualTo(6));
            Assert.That(Ml10.SagittariusWarded(23), Is.False);
            Assert.That(Ml10.SagittariusWarded(24), Is.True);
        }

        [Test]
        public void Cheiron_IsMortalOnlyBriefly()
        {
            Assert.That(Enumerable.Range(0, Ml10.CheironCycle).Count(Ml10.CheironMortal), Is.EqualTo(Ml10.CheironSeconds));
        }

        [TestCase(100, 0)]
        [TestCase(81, 0)]
        [TestCase(80, 1)]
        [TestCase(41, 2)]
        [TestCase(20, 4)]
        [TestCase(1, 4)]
        public void Leo_SplitsEveryFifthOfHisHealth(int health, int splits)
        {
            Assert.That(Ml10.LeoSplits(health), Is.EqualTo(splits));
        }

        [Test]
        public void Draco_IsTheStrongestOfThem()
        {
            int Boss(int index) => Trials[index].Phases.SelectMany(phase => phase.Mobs).Max(mob => mob.Health);
            Assert.That(Boss(4), Is.EqualTo(Enumerable.Range(0, 5).Max(Boss)));
            Assert.That(Boss(4), Is.LessThanOrEqualTo(150000));
        }
    }
}
