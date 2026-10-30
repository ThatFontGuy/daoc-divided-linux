using System;
using DOL.GS.ServerProperties;

namespace DOL.GS
{
    /// <summary>Damage delays player and gamebot spells; explicit interrupts retain their normal path.</summary>
    public static class SpellCastPushback
    {
        public static bool AppliesTo(GameLiving caster) =>
            Properties.SPELL_DAMAGE_PUSHBACK && caster is GamePlayer or GameBot;

        public static int DelayForHit(int alreadyApplied) =>
            Math.Min(Math.Max(0, Properties.SPELL_DAMAGE_PUSHBACK_PER_HIT),
                Math.Max(0, Properties.SPELL_DAMAGE_PUSHBACK_CAP - alreadyApplied));

        public static bool RequiresMeleeFallback(GameLiving caster, bool interrupted, bool recentlyHit) =>
            interrupted || !AppliesTo(caster) && recentlyHit;
    }
}
