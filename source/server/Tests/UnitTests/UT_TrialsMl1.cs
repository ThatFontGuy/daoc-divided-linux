using System.Linq;
using DOL.GS;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl1
    {
        private static readonly string[] Names =
        {
            "Survivor", "Retrieval", "Greater Good", "Barrier", "Conflict", "Curses", "The Monument", "The Ruby", "The Crown", "Conquering the Sea",
        };

        private static readonly TrialScope[] Scopes =
        {
            TrialScope.Group, TrialScope.Group, TrialScope.Raid, TrialScope.Group, TrialScope.Solo,
            TrialScope.Raid, TrialScope.Raid, TrialScope.Raid, TrialScope.Raid, TrialScope.Raid,
        };

        [Test]
        public void EveryStep_ExistsInOrder()
        {
            var trials = Ml1.Trials().ToList();
            Assert.That(trials.Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(trials.Select(trial => trial.Name), Is.EqualTo(Names));
            Assert.That(trials.All(trial => trial.ML == 1), Is.True);
        }

        [Test]
        public void EveryStep_HasTheWindowScope()
        {
            Assert.That(Ml1.Trials().Select(trial => trial.Scope), Is.EqualTo(Scopes));
        }

        [Test]
        public void EveryStep_StandsInsideItsZone()
        {
            foreach (TrialDefinition trial in Ml1.Trials())
            {
                if (trial.Zone == TrialZone.CetusPit)
                {
                    Assert.That(trial.Anchor.X, Is.InRange(8192, 73728), trial.Key);
                    Assert.That(trial.Anchor.Y, Is.InRange(8192, 73728), trial.Key);
                }
                else
                {
                    Assert.That(trial.Zone, Is.EqualTo(TrialZone.Oceanus), trial.Key);
                    Assert.That(trial.Anchor.X, Is.InRange(262144, 458752), trial.Key);
                    Assert.That(trial.Anchor.Y, Is.InRange(458752, 655360), trial.Key);
                }
            }
        }

        [Test]
        public void Curses_NeedsTheGemAndBeltSteps()
        {
            Assert.That(TrialManager.Required(Ml1.Trials().First(trial => trial.Step == 6)), Is.EqualTo(new[] { 1, 4 }));
        }

        [Test]
        public void Finale_NeedsTheNineTrials()
        {
            TrialDefinition cetus = Ml1.Trials().Last();
            Assert.That(TrialManager.Required(cetus), Is.EqualTo(Enumerable.Range(1, 9)));
            Assert.That(cetus.Zone, Is.EqualTo(TrialZone.CetusPit));
        }

        [Test]
        public void ReplacedNames_AreNotAlsoAnotherTrialsStarter()
        {
            var trials = TrialCatalog.All.Where(trial => trial.Zone == TrialZone.Oceanus).ToList();
            foreach (TrialDefinition trial in trials)
            {
                foreach (string name in trial.Replaces)
                {
                    bool earlierStarter = trials.TakeWhile(other => other != trial).Any(other => other.StarterName == name);
                    Assert.That(earlierStarter, Is.False, $"{trial.Key} would delete the starter named {name}");
                }
            }
        }

        [Test]
        public void Hideouts_AreTwoDifferentRocks()
        {
            for (int roll = -3; roll < 9; roll++)
            {
                (int first, int second) = Ml1.PickHideouts(roll);
                Assert.That(first, Is.Not.EqualTo(second));
                Assert.That(first, Is.InRange(0, Ml1.Hideouts.Length - 1));
                Assert.That(second, Is.InRange(0, Ml1.Hideouts.Length - 1));
            }
        }

        [Test]
        public void Purros_NeverLastLongerThanTheirBreeder()
        {
            Assert.That(Ml1.PurrosShare, Is.GreaterThan(0));
            Assert.That(1 / Ml1.PurrosShare, Is.LessThanOrEqualTo(12));
        }

        [Test]
        public void Cetus_FleesThreeTimesAtMost()
        {
            Assert.That(Ml1.CetusFlees(80, 0), Is.False);
            Assert.That(Ml1.CetusFlees(75, 0), Is.True);
            Assert.That(Ml1.CetusFlees(60, 1), Is.False);
            Assert.That(Ml1.CetusFlees(50, 1), Is.True);
            Assert.That(Ml1.CetusFlees(25, 2), Is.True);
            Assert.That(Ml1.CetusFlees(1, 3), Is.False);
        }
    }
}
