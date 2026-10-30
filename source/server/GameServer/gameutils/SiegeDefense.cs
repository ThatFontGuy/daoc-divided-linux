using System;

namespace DOL.GS
{
    /// <summary>
    /// Siege damage taken by a living (live 1.130a): Siege Resistance (Armsman, Hero, Warrior) removes 33% (the live
    /// hotfix's figure, down from 50%), and the strongest siege-protection song on it (Champion, Minstrel, Skald;
    /// 10-50%) removes its share of the rest. Boiling oil included.
    /// </summary>
    public static class SiegeDefense
    {
        public const string SIEGE_RESISTANCE = "Siege Resist";
        public const int SIEGE_RESISTANCE_PERCENT = 33;

        public static int Reduce(GameLiving target, int damage)
        {
            if (target == null || damage <= 0)
                return damage;

            return Apply(damage, target.HasAbility(SIEGE_RESISTANCE), SongPercent(target));
        }

        /// <summary>The damage left after Siege Resistance (if any) and a song of <paramref name="songPercent"/>.</summary>
        public static int Apply(int damage, bool siegeResistance, int songPercent)
        {
            double remaining = damage;

            if (siegeResistance)
                remaining *= 1 - SIEGE_RESISTANCE_PERCENT / 100.0;

            if (songPercent > 0)
                remaining *= 1 - Math.Min(100, songPercent) / 100.0;

            return (int) Math.Round(remaining);
        }

        public static int SongPercent(GameLiving target)
        {
            int best = 0;
            foreach (ECSGameSpellEffect effect in target.effectListComponent.GetSpellEffects(eEffect.SiegeProtection))
            {
                if (effect.IsActive)
                    best = Math.Max(best, (int) effect.SpellHandler.Spell.Value);
            }
            return best;
        }
    }
}
