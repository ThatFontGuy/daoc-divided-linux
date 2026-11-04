using System;

namespace DOL.GS;

/// <summary>
/// How far past the everyday cons a bot reaches when it picks a camp. Owner 2026-11-01: only greys are ignored; green, blue
/// and yellow are fair game; orange, red and purple are tried sometimes, going by how those fights have gone. A lone bot
/// draws its everyday camps up to yellow and now and then adds harder ones, by what the realm's bots have learned about
/// that monster (<see cref="AutonomousMobLessons"/>). A party keeps its +3 and up camps on most picks, and otherwise takes
/// a yellow or blue one, as it always does after a wipe.
/// </summary>
public static class AutonomousCampConStretch
{
    /// <summary>Below this a bot has the gear and hit points for nothing above yellow, where orange is one level away.</summary>
    public const int MinimumSoloLevel = 5;

    public const int SoloOrangePercent = 20;
    public const int SoloRedPercent = 6;
    public const int SoloPurplePercent = 2;

    /// <summary>The share of a party's camp picks that are an easy night.</summary>
    public const int EasyGroupPercent = 30;

    private const int AnyLowerLevel = -50;

    /// <summary>The percent of camp picks that may include a monster felt at this con.</summary>
    public static int SoloChancePercent(ConColor felt) => felt switch
    {
        <= ConColor.YELLOW => 100,
        ConColor.ORANGE => SoloOrangePercent,
        ConColor.RED => SoloRedPercent,
        _ => SoloPurplePercent,
    };

    /// <summary>Pure. <paramref name="roll"/> is 0-99, one roll per camp pick, so a pick that reaches red also reaches orange.</summary>
    public static bool SoloMayTry(ConColor felt, bool provenDeadly, int botLevel, int roll) =>
        !provenDeadly && botLevel >= MinimumSoloLevel && roll < SoloChancePercent(felt);

    public static bool SoloMayTry(ConColor con, string monster, int botLevel, int roll) =>
        botLevel >= MinimumSoloLevel && SoloMayTry(AutonomousMobLessons.Felt(con, monster, false),
            AutonomousMobLessons.IsDeadly(monster, false), botLevel, roll);

    /// <summary>
    /// The levels above the party's average a party may camp at this pick. Pure. <paramref name="roll"/> is 0-99.
    /// After a wipe the rolled top, already lowered by the wipes, is kept and everything below it opens up.
    /// </summary>
    public static (int Low, int High) GroupBand(int rolledBonus, int wipePenalty, int averageLevel, int roll)
    {
        if (wipePenalty > 0)
            return (AnyLowerLevel, Math.Max(0, rolledBonus));
        if (roll >= EasyGroupPercent)
            return (3, Math.Clamp(rolledBonus, 3, 10));
        // Half of the easy picks reach for blue, once there are levels enough for one three below the party.
        return (AnyLowerLevel, roll % 2 == 0 || averageLevel < 10 ? 0 : -3);
    }
}
