using NUnit.Framework;

namespace DOL.GS.Tests
{
    [TestFixture]
    public sealed class UT_AutonomousTrainingOnArrival
    {
        [TestCase("", "", 50, true)]
        [TestCase("", "", 2, true)]
        [TestCase("", "", 1, false)]
        [TestCase("trained-level|1|realm-points|0", "Rejuvenation|1;Enhancement|1;Smite|1", 50, true)]
        [TestCase("trained-level|1|realm-points|0", "Rejuvenation|1;Enhancement|1;Smite|1", 6, true)]
        [TestCase("trained-level|1|realm-points|0", "Rejuvenation|1;Enhancement|1;Smite|1", 5, false)]
        [TestCase("trained-level|1|realm-points|0", "Rejuvenation|1;Enhancement|4;Smite|1", 50, false)]
        [TestCase("trained-level|30|realm-points|0", "Rejuvenation|1;Enhancement|1;Smite|1", 50, false)]
        [TestCase("", "Rejuvenation|20;Enhancement|30;Smite|1", 50, false)]
        public void TrainsOnlyBotsThatNeverTrained(string abilities, string specs, int level, bool expected)
        {
            Assert.That(GameBot.NeedsTrainingOnArrival(abilities, specs, (byte)level), Is.EqualTo(expected));
        }

        [Test]
        public void OverdueTrainingIsNotLeftToTheTaskBreakRoll()
        {
            Assert.That(AutonomousObjectiveAssignments.RollBetweenTaskPlan(true, false, .95, 1, trainingOverdue: true).Train, Is.True);
            Assert.That(AutonomousObjectiveAssignments.RollBetweenTaskPlan(true, false, .95, 1).Train, Is.False);
            Assert.That(AutonomousObjectiveAssignments.RollBetweenTaskPlan(false, false, 0, 1, trainingOverdue: true).Train, Is.False);
        }
    }
}
