using DOL.GS.PacketHandler;

namespace DOL.GS.Fishing
{
    /// <summary>
    /// "Camp Rest" on the buff bar while a player is beside a burning campfire (FishingCamp). It only shows the icon; the
    /// camp itself does the restoring. An ability effect, so no spell animation plays. It ends itself once the player
    /// is away from every burning fire.
    /// </summary>
    public class CampRestECSGameEffect : ECSGameAbilityEffect
    {
        // spells.csv 8075 "Elixir of Mending": the health regeneration potion icon.
        private const ushort RestIcon = 8075;

        public CampRestECSGameEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.CampRest;
            PulseFreq = 1000;
            NextTick = GameLoop.GameLoopTime;
        }

        public override ushort Icon => RestIcon;
        public override string Name => "Camp Rest";
        public override bool HasPositiveEffect => true;

        public override long GetRemainingTimeForClient()
        {
            return 0;
        }

        public override void OnStartEffect()
        {
            OwnerPlayer?.Out.SendMessage("You rest by the campfire.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        public override void OnStopEffect()
        {
            OwnerPlayer?.Out.SendMessage("You leave the warmth of the campfire.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        public override void OnEffectPulse()
        {
            if (!Owner.IsAlive || !FishingCamp.IsNearCampfire(Owner))
            {
                End();
            }
        }
    }
}
