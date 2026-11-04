using System;

namespace DOL.GS
{
    /// <summary>
    /// Owner 2026-11-02: the level a bot's specialization spell line is read at.
    ///
    /// A monster has no specializations, so the engine has always estimated its spell line at three quarters of its
    /// level ("mobs know a middling rank") - 38 for a level 50. Every bot in this world has a real, point-funded build
    /// (BotSpec plus SpendSpecPoints), but it was still read at that estimate, so a level 50 Minstrel with Instruments
    /// 50 knew nothing above rank 38: the best speed song it could sing was Motivational Strains (189%) while the top
    /// one, Motivational Anthem (204%), needs 43. The same ceiling hid the top ranks of every other line - resurrection,
    /// greater heals, mez, the last buffs.
    /// </summary>
    public static class BotSpellLineLevel
    {
        /// <summary>
        /// The real specialization level for a bot that trains its specs, and the three-quarter estimate for anything
        /// that only imitates one. The result never exceeds the bot's own level and is never below one.
        /// </summary>
        public static int For(bool trainsRealSpecs, int specLevel, int botLevel) =>
            trainsRealSpecs
                ? Math.Clamp(specLevel, 1, Math.Max(1, botLevel))
                : Math.Max(1, botLevel - (botLevel >> 2));
    }
}
