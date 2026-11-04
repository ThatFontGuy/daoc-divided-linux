using System.Collections.Generic;
using System.Linq;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl7
    {
        private static readonly string[] Names =
        {
            "The Lava Bridge", "Know your Opponents", "Apophian's Challenge", "Volurgon's Challenge", "Shaitan's Challenge",
            "Hephaestian's Challenge", "Crossing the Chamber", "Pillars", "Facing Typhon", "Typhon's Rage",
        };

        private static List<TrialDefinition> Steps() => Ml7.Trials().ToList();

        [Test]
        public void Steps_AreAllThereInOrder()
        {
            Assert.That(Steps().Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(Steps().Select(trial => trial.Name), Is.EqualTo(Names));
            Assert.That(Steps().All(trial => trial.ML == 7 && trial.Zone == TrialZone.Volcanus));
        }

        [Test]
        public void Scopes_MatchTheWindowText()
        {
            Assert.That(Steps().Take(6).All(trial => trial.Scope == TrialScope.Group));
            Assert.That(Steps().Skip(6).All(trial => trial.Scope == TrialScope.Raid));
        }

        [Test]
        public void Requirements_FollowTheRoadThroughTheDungeon()
        {
            List<TrialDefinition> steps = Steps();
            Assert.That(TrialManager.Required(steps[9]), Is.EqualTo(Enumerable.Range(1, 9)));
            Assert.That(TrialManager.Required(steps[1]), Is.EqualTo(new[] { 1 }));
            foreach (TrialDefinition challenge in steps.Skip(2).Take(4))
                Assert.That(TrialManager.Required(challenge), Is.EqualTo(new[] { 2 }));
            Assert.That(TrialManager.Required(steps[8]), Is.EqualTo(new[] { 8 }));
        }

        [Test]
        public void Anchors_LieInsideDeepVolcanus()
        {
            foreach (TrialDefinition trial in Steps())
            {
                Assert.That(trial.Anchor.X, Is.InRange(8192, 73728), trial.Key);
                Assert.That(trial.Anchor.Y, Is.InRange(8192, 73728), trial.Key);
            }
        }

        [Test]
        public void Tuning_StaysInsideTheBrief()
        {
            foreach (TrialDefinition trial in Steps())
            {
                Assert.That(trial.TimeLimitSeconds, Is.InRange(900, 2400), trial.Key);
                foreach (TrialMobSpec mob in trial.Phases.SelectMany(phase => phase.Mobs).Where(mob => !mob.Objective))
                {
                    Assert.That(mob.Level, Is.InRange(55, 70), mob.Name);
                    Assert.That(mob.Health, Is.AtMost(150000), mob.Name);
                }
            }
        }

        [Test]
        public void Challenges_EndBeforeTheyRunOutOfTime()
        {
            foreach (TrialDefinition challenge in Steps().Skip(2).Take(4))
                Assert.That(challenge.Phases.Sum(phase => phase.SurviveSeconds), Is.LessThan(challenge.TimeLimitSeconds), challenge.Key);
        }

        [Test]
        public void Apophian_GrowsUpToTheCap()
        {
            Assert.That(Ml7.ApophianLevel(0), Is.EqualTo(60));
            Assert.That(Ml7.ApophianLevel(90), Is.EqualTo(63));
            Assert.That(Ml7.ApophianLevel(9000), Is.EqualTo(70));
        }

        [TestCase(100, 0)]
        [TestCase(76, 0)]
        [TestCase(75, 1)]
        [TestCase(50, 2)]
        [TestCase(25, 3)]
        [TestCase(1, 3)]
        public void Typhon_MovesPoolsAsHeWeakens(int health, int spot)
        {
            Assert.That(Ml7.TyphonSpot(health), Is.EqualTo(spot));
        }

        [Test]
        public void Bridge_CoversTheCrossingOnly()
        {
            Assert.That(Ml7.OnBridge(32000, 27000), Is.True);
            Assert.That(Ml7.OnBridge(32000, 28800), Is.False);
            Assert.That(Ml7.OnBridge(29000, 27000), Is.False);
        }

        [Test]
        public void Ml8_Replaces_NoNameFromThisLevel()
        {
            IEnumerable<string> ml8 = Ml8.Trials().SelectMany(trial => trial.Replaces);
            Assert.That(Steps().SelectMany(trial => trial.Replaces).Intersect(ml8), Is.Empty);
        }

        [Test]
        public void Circle_KeepsItsHeightAndRadius()
        {
            List<TrialPoint> points = Ml7Kit.Circle(new TrialPoint(1000, 1000, 50), 100, 4).ToList();
            Assert.That(points, Has.Count.EqualTo(4));
            Assert.That(points[0], Is.EqualTo(new TrialPoint(1100, 1000, 50)));
            Assert.That(points.All(point => point.Z == 50));
        }

        [Test]
        public void Marks_CountDownward()
        {
            Assert.That(Ml7Kit.MarksPassed(60, 75, 50, 25), Is.EqualTo(1));
            Assert.That(Ml7Kit.MarksPassed(100, 75), Is.EqualTo(0));
        }
    }
}
