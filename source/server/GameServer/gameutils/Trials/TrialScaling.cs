using System;

namespace DOL.GS.Trials
{
    /// <summary>
    /// Sizes a run to the party that starts it: trials were built for raids, and here one player and some
    /// companions must be able to finish them. Fixed at the start, so dismissing bots mid-fight changes nothing.
    /// </summary>
    public static class TrialScaling
    {
        public const double MinimumScale = 0.25;
        public const double MaximumScale = 2.0;
        public const int GroupSize = 8;
        public const int RaidSize = 16;

        public static int DesignSize(TrialScope scope) => scope switch
        {
            TrialScope.Solo => 1,
            TrialScope.Group => GroupSize,
            _ => RaidSize,
        };

        public static double HealthScale(TrialScope scope, int partySize) =>
            scope == TrialScope.Solo ? 1.0 : Math.Clamp((double)Math.Max(1, partySize) / DesignSize(scope), MinimumScale, MaximumScale);

        /// <summary>Damage falls slower than health: a small party still has to respect a boss.</summary>
        public static double DamageScale(TrialScope scope, int partySize) => Math.Sqrt(HealthScale(scope, partySize));

        public static int Health(int baseHealth, double scale) => Math.Max(1, (int)Math.Round(baseHealth * scale));
    }
}
