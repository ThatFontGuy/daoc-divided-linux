using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Small fixes from the overnight play test of 2026-10-31.</summary>
    [TestFixture]
    public class UT_OvernightSmallFixes
    {
        [TestCase("Atlantean Glass", "Atlantean Glass")]
        [TestCase("Dragon Scales", "Dragon Scales")]
        [TestCase("aurulite", "aurulite")]
        [TestCase("Daemon Diamond Seal", "Daemon Diamond Seals")]
        [TestCase("Blood Seal", "Blood Seals")]
        [TestCase("", "")]
        public void CurrencyNameReadsRightInTheMerchantLine(string name, string expected)
        {
            Assert.That(GameMerchant.CurrencyPlural(name), Is.EqualTo(expected));
        }

        [TestCase(AutonomousObjectiveAssignments.NoCampGoal)]
        [TestCase("Grind great lynx in Jamtland Mountains")]
        public void FrontierBotsReportTheirFrontierGoalNotACampGoal(string staleGoal)
        {
            Assert.Multiple(() =>
            {
                Assert.That(AutonomousObjectiveAssignments.GoalFor(eAutonomousObjectiveKind.RvR, staleGoal),
                    Is.EqualTo(AutonomousObjectiveAssignments.RvrGoal));
                Assert.That(AutonomousObjectiveAssignments.GoalFor(eAutonomousObjectiveKind.Battleground, staleGoal),
                    Is.EqualTo(AutonomousObjectiveAssignments.BattlegroundGoal));
            });
        }

        [TestCase(eAutonomousObjectiveKind.SoloPve)]
        [TestCase(eAutonomousObjectiveKind.GroupPve)]
        public void PveBotsKeepTheirCampGoals(eAutonomousObjectiveKind kind)
        {
            Assert.Multiple(() =>
            {
                Assert.That(AutonomousObjectiveAssignments.GoalFor(kind, AutonomousObjectiveAssignments.NoCampGoal),
                    Is.EqualTo(AutonomousObjectiveAssignments.NoCampGoal));
                Assert.That(AutonomousObjectiveAssignments.GoalFor(kind, "Grind orc beachcomber in Aldland"),
                    Is.EqualTo("Grind orc beachcomber in Aldland"));
            });
        }

        [TestCase("Assemble, then roam frontier keeps, relic routes, and enemy realm forces")]
        [TestCase("Battleground: Thidranki (levels 20-24)")]
        [TestCase(null)]
        public void OtherGoalTextIsLeftAlone(string goal)
        {
            Assert.That(AutonomousObjectiveAssignments.GoalFor(eAutonomousObjectiveKind.RvR, goal), Is.EqualTo(goal));
        }

        [Test]
        public void AnUnknownRaceWarnsOnce()
        {
            // Races no other test uses, so the once-only list starts without them.
            Assert.Multiple(() =>
            {
                Assert.That(UnknownRaceWarnings.First(987654), Is.True);
                Assert.That(UnknownRaceWarnings.First(987654), Is.False);
                Assert.That(UnknownRaceWarnings.First(987655), Is.True);
            });
        }
    }
}
