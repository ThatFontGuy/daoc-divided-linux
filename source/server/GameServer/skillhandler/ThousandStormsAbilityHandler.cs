using DOL.GS.PacketHandler;
using DOL.Language;

namespace DOL.GS.SkillHandler
{
    /// <summary>
    /// Call of a Thousand Storms (Thane and Valkyrie, level 40, live 1.130a): for two minutes, eight more attackers can be
    /// faced at once before the multiple-attacker penalties apply, against monsters of level 50 and up. Three-minute reuse.
    /// </summary>
    [SkillHandler(Abilities.CallOfAThousandStorms)]
    public class ThousandStormsAbilityHandler : IAbilityActionHandler
    {
        public const int REUSE_TIMER = 180 * 1000;
        public const int DURATION = 120 * 1000;

        public void Execute(Ability ab, GamePlayer player)
        {
            if (player == null)
                return;

            if (!player.IsAlive)
            {
                player.Out.SendMessage(LanguageMgr.GetTranslation(player.Client.Account.Language, "Skill.Ability.CannotUseDead"), eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }

            if (EffectListService.GetAbilityEffectOnTarget(player, eEffect.ThousandStorms) != null)
            {
                player.Out.SendMessage(LanguageMgr.GetTranslation(player.Client.Account.Language, "Skill.Ability.CannotUseAlreadyActive"), eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }

            player.DisableSkill(ab, REUSE_TIMER);
            ECSGameEffectFactory.Create(new(player, DURATION, 1), static (in i) => new ThousandStormsECSGameEffect(i));
        }
    }
}

namespace DOL.GS
{
    public class ThousandStormsECSGameEffect : ECSGameAbilityEffect
    {
        /// <summary>How many more attackers the owner can face at once.</summary>
        public const int EXTRA_ATTACKERS = 8;
        /// <summary>Only monsters of this level and up are affected.</summary>
        public const int MIN_MONSTER_LEVEL = 50;

        public ThousandStormsECSGameEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.ThousandStorms;
        }

        public override ushort Icon => 3066;
        public override string Name => "Call of a Thousand Storms";
        public override bool HasPositiveEffect => true;

        public override void OnStartEffect()
        {
            OwnerPlayer?.Out.SendMessage("The storm answers your call: many more foes can face you before your defenses falter.", eChatType.CT_Spell, eChatLoc.CL_SystemWindow);
        }

        public override void OnStopEffect()
        {
            OwnerPlayer?.Out.SendMessage("The call of a thousand storms fades.", eChatType.CT_SpellExpires, eChatLoc.CL_SystemWindow);
        }

        /// <summary>The extra attackers <paramref name="defender"/> can face against this attacker: 8 against monsters of level 50+, else 0.</summary>
        public static int ExtraAttackers(GameLiving defender, GameLiving attacker)
        {
            if (defender == null || !IsQualifyingMonster(attacker))
                return 0;
            return EffectListService.GetAbilityEffectOnTarget(defender, eEffect.ThousandStorms) != null ? EXTRA_ATTACKERS : 0;
        }

        /// <summary>A hostile monster of level 50 or higher: not a player, a player-like bot or a controlled pet.</summary>
        public static bool IsQualifyingMonster(GameLiving attacker) =>
            attacker is GameNPC npc && npc is not IGamePlayer && npc.Brain is not AI.Brain.IControlledBrain && npc.Level >= MIN_MONSTER_LEVEL;

        /// <summary>The attacker count the defense penalties use: the real count less the extra attackers, never below one.</summary>
        public static int EffectiveAttackers(GameLiving defender, GameLiving attacker, int attackers) =>
            attackers <= 1 ? attackers : System.Math.Max(1, attackers - ExtraAttackers(defender, attacker));
    }
}
