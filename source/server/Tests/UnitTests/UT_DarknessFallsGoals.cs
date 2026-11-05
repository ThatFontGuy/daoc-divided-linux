using DOL.GS;
using NUnit.Framework;

namespace DOL.Tests.Unit.Gameserver;

[TestFixture]
public class UT_DarknessFallsGoals
{
    [TestCase(19, 0)]
    [TestCase(19, 20)]
    public void NoGoalBelowLevelTwenty(int level, int roll) =>
        Assert.That(AutonomousDarknessFallsPolicy.RollGoal(level, 0, roll), Is.EqualTo(eDarknessFallsGoal.None));

    [Test]
    public void NoGoalOnceTheDungeonIsFull() =>
        Assert.That(AutonomousDarknessFallsPolicy.RollGoal(50, AutonomousDarknessFallsPolicy.GoalPopulationLimit, 0),
            Is.EqualTo(eDarknessFallsGoal.None));

    [TestCase(20, 0, eDarknessFallsGoal.Pve)]
    [TestCase(44, 14, eDarknessFallsGoal.Pve)]
    [TestCase(44, 15, eDarknessFallsGoal.None)]
    [TestCase(45, 14, eDarknessFallsGoal.Pve)]
    [TestCase(45, 15, eDarknessFallsGoal.Pvp)]
    [TestCase(50, 29, eDarknessFallsGoal.Pvp)]
    [TestCase(50, 30, eDarknessFallsGoal.None)]
    public void GoalByLevelAndRoll(int level, int roll, eDarknessFallsGoal expected) =>
        Assert.That(AutonomousDarknessFallsPolicy.RollGoal(level, 0, roll), Is.EqualTo(expected));

    [Test]
    public void GapIsSecondClosestEntranceMinusClosest()
    {
        Assert.That(AutonomousDarknessFallsPolicy.EntranceGap(9_000, 2_000, 4_000), Is.EqualTo(2_000));
        Assert.That(AutonomousDarknessFallsPolicy.EntranceGap(2_000, 2_000, 40_000), Is.EqualTo(0));
    }

    [Test]
    public void MeetingRoomNeedsTwoRealmsClose()
    {
        Assert.That(AutonomousDarknessFallsPolicy.IsMeetingRoom(20_000, 27_500, 50_000), Is.True);
        Assert.That(AutonomousDarknessFallsPolicy.IsMeetingRoom(20_000, 27_501, 50_000), Is.False);
        Assert.That(AutonomousDarknessFallsPolicy.IsMeetingRoom(20_000, 21_000, float.PositiveInfinity), Is.False);
    }
}
