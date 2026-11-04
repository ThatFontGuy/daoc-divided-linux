using System.Collections.Generic;
using System.Linq;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl8
    {
        private static readonly string[] Names =
        {
            "Agne's Crystal", "Agne's Shield", "Agne's Sword", "Centaur's Hunt", "Treasure of the Cyclops",
            "Agne's Will", "Agne's Might", "Gorgon's Secret", "Agne's Spare Arm", "Agne's Great Might",
        };

        private static List<TrialDefinition> Steps() => Ml8.Trials().ToList();

        [Test]
        public void Steps_AreAllThereInOrder()
        {
            Assert.That(Steps().Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(Steps().Select(trial => trial.Name), Is.EqualTo(Names));
            Assert.That(Steps().All(trial => trial.ML == 8 && trial.Zone == TrialZone.Oceanus));
        }

        [Test]
        public void Scopes_MatchTheWindowText()
        {
            int[] groups = { 4, 5, 7, 9 };
            foreach (TrialDefinition trial in Steps())
                Assert.That(trial.Scope, Is.EqualTo(groups.Contains(trial.Step) ? TrialScope.Group : TrialScope.Raid), trial.Key);
        }

        [Test]
        public void Finale_NeedsEveryPieceOfAgne()
        {
            Assert.That(TrialManager.Required(Steps()[9]), Is.EqualTo(Enumerable.Range(1, 9)));
            Assert.That(Steps().Take(9).SelectMany(TrialManager.Required), Is.Empty);
        }

        [Test]
        public void Anchors_LieInGreenGladesOrArborGlen()
        {
            foreach (TrialDefinition trial in Steps())
            {
                Assert.That(trial.Anchor.X, Is.InRange(44 * 8192, 60 * 8192), trial.Key);
                Assert.That(trial.Anchor.Y, Is.InRange(80 * 8192, 88 * 8192), trial.Key);
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
        public void Replaces_NeverTakesACommonCreature()
        {
            string[] common = { "cobra guardian", "self-maintaining statue", "centaur guard" };
            Assert.That(Steps().SelectMany(trial => trial.Replaces).Intersect(common), Is.Empty);
        }

        [Test]
        public void Replaces_NoNameTwice()
        {
            List<string> names = Steps().SelectMany(trial => trial.Replaces).ToList();
            Assert.That(names, Is.Unique);
        }

        [TestCase(100, 0)]
        [TestCase(75, 1)]
        [TestCase(40, 2)]
        [TestCase(10, 3)]
        public void Ibn_StormsAtEachMark(int health, int storms)
        {
            Assert.That(Ml8.IbnStorms(health), Is.EqualTo(storms));
        }

        [TestCase(100, 0)]
        [TestCase(66, 1)]
        [TestCase(20, 2)]
        public void Dawar_FleesAtEachMark(int health, int flights)
        {
            Assert.That(Ml8.DawarFlights(health), Is.EqualTo(flights));
        }

        [Test]
        public void Torso_AlwaysTurnsUp()
        {
            Assert.That(Ml8.TorsoFound(1, 0.9), Is.False);
            Assert.That(Ml8.TorsoFound(1, 0.1), Is.True);
            Assert.That(Ml8.TorsoFound(12, 0.99), Is.True);
        }

        [Test]
        public void Talos_CallsForHealingOnce()
        {
            Assert.That(Ml8.TalosCallsForHealing(26, false), Is.False);
            Assert.That(Ml8.TalosCallsForHealing(25, false), Is.True);
            Assert.That(Ml8.TalosCallsForHealing(10, true), Is.False);
        }
    }
}
