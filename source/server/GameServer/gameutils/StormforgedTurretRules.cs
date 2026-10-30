using DOL.AI.Brain;

namespace DOL.GS
{
    public static class StormforgedTurretRules
    {
        public const int Limit = 16;
        public static bool IsStormOwner(GameLiving owner) => owner switch
        {
            GamePlayer player => player.CharacterClass?.ID == (int)eCharacterClass.Stormforged,
            IGamePlayer bot => bot.CharacterClass?.ID == (int)eCharacterClass.Stormforged,
            _ => false
        };
        public static bool IsStormSummon(GameLiving owner, Spell spell) =>
            IsStormOwner(owner) && spell?.LifeDrainReturn == 60171002;
        public static bool IsStorm(GameNPC npc) => npc is TurretPet { NPCTemplate.TemplateId: 60171002 };
        // Independent per-owner limit: sixteen storms may share one ground target,
        // and another co-op player's storms don't consume this player's allowance.
        public static bool CanSummon(int ownedStorms) => ownedStorms < Limit;
    }
}
