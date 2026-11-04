using System.Linq;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl2
    {
        private static readonly string[] Names =
        {
            "Death from Shadow", "Stalking Terror", "Triton Hoards", "Rrionne's Reflection", "Chath's Test of Strategy",
            "Kanahkt Test of Tactics", "Pick Your Poison", "Stand Fast", "Battle Masters", "Immortal Imposter",
        };

        private static TrialDefinition Step(int step) => Ml2.Trials().First(trial => trial.Step == step);

        [Test]
        public void EveryStep_ExistsInOrder()
        {
            var trials = Ml2.Trials().ToList();
            Assert.That(trials.Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(trials.Select(trial => trial.Name), Is.EqualTo(Names));
            Assert.That(trials.All(trial => trial.ML == 2), Is.True);
        }

        [Test]
        public void EveryStep_HasItsScope()
        {
            Assert.That(Step(5).Scope, Is.EqualTo(TrialScope.Group));
            Assert.That(Ml2.Trials().Where(trial => trial.Step is not (5 or 8)).All(trial => trial.Scope == TrialScope.Raid), Is.True);
        }

        [Test]
        public void StandFast_IsSoloAsReportedNotGroupAsTheWindowSays()
        {
            Assert.That(Step(8).Scope, Is.EqualTo(TrialScope.Solo));
        }

        [Test]
        public void EveryStep_StandsInsideItsZone()
        {
            foreach (TrialDefinition trial in Ml2.Trials())
            {
                if (trial.Step == 10)
                {
                    Assert.That(trial.Zone, Is.EqualTo(TrialZone.Oceanus));
                    Assert.That(trial.Anchor.X, Is.InRange(327680, 393216));
                    Assert.That(trial.Anchor.Y, Is.InRange(458752, 524288));
                }
                else
                {
                    Assert.That(trial.Zone, Is.EqualTo(TrialZone.Sobekite), trial.Key);
                    Assert.That(trial.Anchor.X, Is.InRange(8192, 73728), trial.Key);
                    Assert.That(trial.Anchor.Y, Is.InRange(8192, 73728), trial.Key);
                }
            }
        }

        [Test]
        public void KeyedTrials_NeedTheStepThatGivesTheKey()
        {
            Assert.That(TrialManager.Required(Step(5)), Is.EqualTo(new[] { 4 }));
            Assert.That(TrialManager.Required(Step(6)), Is.EqualTo(new[] { 3 }));
            Assert.That(TrialManager.Required(Step(7)), Is.EqualTo(new[] { 3 }));
            Assert.That(TrialManager.Required(Step(9)), Is.EqualTo(new[] { 3 }));
        }

        [Test]
        public void Finale_NeedsTheNineTrials()
        {
            Assert.That(TrialManager.Required(Step(10)), Is.EqualTo(Enumerable.Range(1, 9)));
        }

        [Test]
        public void Bait_SpringsOnSittingOrAfterTheWait()
        {
            Assert.That(Ml2.BaitSprung(2, 30), Is.False);
            Assert.That(Ml2.BaitSprung(3, 30), Is.True);
            Assert.That(Ml2.BaitSprung(0, 90), Is.True);
        }

        [Test]
        public void Reaver_VanishesTwice()
        {
            Assert.That(Ml2.ReaverVanishes(70, 0), Is.False);
            Assert.That(Ml2.ReaverVanishes(66, 0), Is.True);
            Assert.That(Ml2.ReaverVanishes(50, 1), Is.False);
            Assert.That(Ml2.ReaverVanishes(30, 1), Is.True);
            Assert.That(Ml2.ReaverVanishes(5, 2), Is.False);
        }

        [Test]
        public void Board_TakesTheQueenFirstAndTheKingLast()
        {
            Assert.That(Ml2.NextPiece(Ml2.ChessOrder.Reverse()), Is.EqualTo("Chaths's Queen"));
            Assert.That(Ml2.NextPiece(new[] { "Chaths's King", "Chaths's Pawn" }), Is.EqualTo("Chaths's Pawn"));
            Assert.That(Ml2.NextPiece(new[] { "Chaths's King" }), Is.EqualTo("Chaths's King"));
            Assert.That(Ml2.NextPiece(new string[0]), Is.Null);
        }

        [Test]
        public void Eidolons_GrowUpToALimit()
        {
            Assert.That(Ml2.EidolonDamage(1), Is.GreaterThan(Ml2.EidolonDamage(0)));
            Assert.That(Ml2.EidolonDamage(50), Is.LessThanOrEqualTo(300));
        }

        [Test]
        public void Spikes_FallOnTheFourth()
        {
            Assert.That(Ml2.SpikesFall(3), Is.False);
            Assert.That(Ml2.SpikesFall(4), Is.True);
        }

        [Test]
        public void Poisons_OfferAllThreeTests()
        {
            Assert.That(Ml2.Poisons, Is.EqualTo(new[] { "Fear", "Terror", "Horror" }));
        }
    }
}
