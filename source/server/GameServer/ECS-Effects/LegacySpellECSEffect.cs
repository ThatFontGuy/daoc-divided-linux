using DOL.GS.Effects;

namespace DOL.GS
{
    // For handlers whose work sits in `OnEffectStart` and `OnEffectExpires`. Only `GameSpellEffect` calls those, and a normal
    // cast creates an ECS effect instead, so without this the target gets an icon and nothing else.
    // Handlers must not rely on `FindEffectOnTarget`, since `GameSpellEffect.Cancel` can't reach this effect.
    public class LegacySpellECSEffect : ECSGameSpellEffect
    {
        public LegacySpellECSEffect(in ECSGameEffectInitParams initParams) : base(initParams) { }

        public override void OnStartEffect()
        {
            SpellHandler.OnEffectStart(new OwnedSpellEffect(this));
        }

        public override void OnStopEffect()
        {
            SpellHandler.OnEffectExpires(new OwnedSpellEffect(this), IsBeingReplaced);
        }

        // Never started or added to an effect list. It only tells the handler who the effect is on.
        private sealed class OwnedSpellEffect : GameSpellEffect
        {
            public OwnedSpellEffect(ECSGameSpellEffect effect) : base(effect.SpellHandler, (int) effect.Duration, 0, effect.Effectiveness)
            {
                Owner = effect.Owner;
            }
        }
    }
}
