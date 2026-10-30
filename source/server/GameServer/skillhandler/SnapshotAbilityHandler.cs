using DOL.GS.PacketHandler;
using DOL.Language;

namespace DOL.GS.SkillHandler
{
    /// <summary>
    /// Snapshot (Armsman, level 25, live 1.130a): for 60 seconds, ranged weapons fire while moving without the shot
    /// being interrupted. Live gives no reuse; five minutes here.
    /// </summary>
    [SkillHandler(Abilities.Snapshot)]
    public class SnapshotAbilityHandler : IAbilityActionHandler
    {
        public const int REUSE_TIMER = 300 * 1000;
        public const int DURATION = 60 * 1000;

        public void Execute(Ability ab, GamePlayer player)
        {
            if (player == null)
                return;

            if (!player.IsAlive)
            {
                player.Out.SendMessage(LanguageMgr.GetTranslation(player.Client.Account.Language, "Skill.Ability.CannotUseDead"), eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }

            if (EffectListService.GetAbilityEffectOnTarget(player, eEffect.Snapshot) != null)
            {
                player.Out.SendMessage(LanguageMgr.GetTranslation(player.Client.Account.Language, "Skill.Ability.CannotUseAlreadyActive"), eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }

            player.DisableSkill(ab, REUSE_TIMER);
            ECSGameEffectFactory.Create(new(player, DURATION, 1), static (in i) => new SnapshotECSGameEffect(i));
        }
    }
}

namespace DOL.GS
{
    public class SnapshotECSGameEffect : ECSGameAbilityEffect
    {
        public SnapshotECSGameEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.Snapshot;
        }

        public override ushort Icon => 485;
        public override string Name => "Snapshot";
        public override bool HasPositiveEffect => true;

        public override void OnStartEffect()
        {
            OwnerPlayer?.Out.SendMessage("You steady your aim: you can shoot on the move.", eChatType.CT_Spell, eChatLoc.CL_SystemWindow);
        }

        public override void OnStopEffect()
        {
            OwnerPlayer?.Out.SendMessage("Your snapshot readiness fades.", eChatType.CT_SpellExpires, eChatLoc.CL_SystemWindow);
        }

        /// <summary>Whether moving keeps <paramref name="living"/>'s ranged shot going.</summary>
        public static bool KeepsShotOnMove(GameLiving living) =>
            living != null && EffectListService.GetAbilityEffectOnTarget(living, eEffect.Snapshot) != null;
    }
}
