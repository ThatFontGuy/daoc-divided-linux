using DOL.GS.Spells;

namespace DOL.GS
{
    /// <summary>
    /// Mauler bots fight as melee classes that cast between swings. The whole Magnetism and Power Strikes kit used to
    /// enter that rotation: in the 2026-11-01 overnight run 82% of their last actions before a death were casts, against
    /// 40-64% for Thanes, Champions and Reavers, only 39% of those casts did damage, and they died at 94% power.
    /// These spells cost a swing and do nothing for the fight, so the bot swings instead.
    /// </summary>
    public static class MaulerBotCombatPolicy
    {
        /// <summary>Endurance is only worth stealing when styles are about to run out of it.</summary>
        public const int TapBelowEndurancePercent = 30;

        /// <summary>The bot's own casting range rules still apply; this only says whether the spell is worth a swing.</summary>
        public static bool AllowsCast(Spell spell, bool inMeleeReach, int endurancePercent)
        {
            // Unceasing Burden channels until the next spell is ready and the bot neither moves nor swings meanwhile: 243
            // of 284 Mauler 15-minute stuck recoveries in that run were level 50 bots in a cast, with no attack running.
            // A Wildbull Perizor gift roots the monster the bot is about to hit.
            if (spell.IsFocus || ModernMauler.IsPerizorGift(spell))
                return false;
            // A snare or root on a monster already in reach stops nothing, and the next hit breaks a root.
            if (spell.SpellType == eSpellType.SpeedDecrease)
                return !inMeleeReach;
            if (spell.SpellType == eSpellType.MaulerEnduranceTap)
                return endurancePercent < TapBelowEndurancePercent;
            return true;
        }
    }
}
