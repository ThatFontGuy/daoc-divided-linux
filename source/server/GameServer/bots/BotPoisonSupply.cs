using System;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS
{
    /// <summary>Assassin bots keep their class's live Envenom coating up outside combat; item poisons left the game in 1.121.</summary>
    public static class BotPoisonSupply
    {
        private static readonly Dictionary<eCharacterClass, string> Lines = new()
        {
            [eCharacterClass.Infiltrator] = "Infiltrator Envenom",
            [eCharacterClass.Shadowblade] = "Shadowblade Envenom",
            [eCharacterClass.Nightshade] = "Nightshade Envenom"
        };

        public static bool IsAssassin(eCharacterClass characterClass) => Lines.ContainsKey(characterClass);
        public static int EligibleLevel(int level, int envenom) => Math.Clamp(Math.Min(level, envenom), 0, 50);

        /// <summary>The strongest coating in reach that delivers damage: its child is a damage over time.</summary>
        public static Spell BestCoat(IEnumerable<Spell> line, int level, Func<int, Spell> child) =>
            line.Where(spell => spell.SpellType == eSpellType.PoisonCoating && spell.Level <= level &&
                    child((int)spell.Value)?.SpellType == eSpellType.DamageOverTime)
                .OrderByDescending(spell => spell.Level).FirstOrDefault();

        public static bool Maintain(GameBot bot)
        {
            if (bot?.CharacterClass == null || !Lines.TryGetValue((eCharacterClass)bot.CharacterClass.ID, out string lineName) ||
                !bot.IsAlive || bot.InCombat || bot.IsAttacking || bot.IsCasting || bot.IsCrowdControlled ||
                bot.castingComponent?.HasPendingSkillRequests == true) return false;
            if (bot.effectListComponent.GetSpellEffects().Any(effect => effect.SpellHandler?.Spell?.SpellType == eSpellType.PoisonCoating))
                return false;
            int level = EligibleLevel(bot.Level, bot.GetModifiedSpecLevel(Specs.Envenom));
            Spell coat = BestCoat(SkillBase.GetSpellList(lineName), level, SkillBase.GetSpellByID);
            return coat != null && bot.CastSpell(coat, SkillBase.GetSpellLine(lineName), false);
        }

        public static void Changed(GameBot bot)
        {
            if (!bot.IsAutonomousWorldBot) return;
            bot.MarkAutonomousStateDirty();
            // A coat changes neither equipment suitability nor backpack space;
            // don't invalidate the expensive vendor/upgrade appraisal cache.
            AutonomousBotStatusPersistence.Queue(bot, true);
        }
    }
}
