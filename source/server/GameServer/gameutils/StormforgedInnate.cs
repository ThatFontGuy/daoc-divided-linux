using System;

namespace DOL.GS
{
    /// <summary>Intrinsic class bonuses, separate from item/buff caps and saved base stats.</summary>
    public static class StormforgedInnate
    {
        public static int Bonus(GameLiving living, eProperty property)
        {
            int? classId = living switch
            {
                GamePlayer player => player.CharacterClass?.ID,
                IGamePlayer bot => bot.CharacterClass?.ID,
                _ => null
            };
            if (!classId.HasValue || !PendragonRules.IsSovereign(classId.Value))
                return 0;
            int level = Math.Clamp((int)living.Level, 1, 50);
            if (property >= eProperty.Stat_First && property <= eProperty.Stat_Last)
                return level * 23 / 10;
            return property switch
            {
                eProperty.MaxHealth => level * 23 / 2,
                eProperty.MaxMana => level * 23 / 10,
                _ => 0
            };
        }
    }
}
