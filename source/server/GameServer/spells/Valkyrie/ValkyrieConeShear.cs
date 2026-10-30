using System.Collections.Generic;
using System.Linq;
using DOL.AI.Brain;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    [SpellHandler(eSpellType.ValkyrieDexQuiShearCone)]
    public class ValkyrieDexQuiShearCone : ValkyrieConeShear
    {
        public ValkyrieDexQuiShearCone(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }

        protected override eEffect ShearedEffect => eEffect.DexQuickBuff;
        protected override string ShearedName => "Dex/Qui";
    }

    [SpellHandler(eSpellType.ValkyrieAcuityShearCone)]
    public class ValkyrieAcuityShearCone : ValkyrieConeShear
    {
        public ValkyrieAcuityShearCone(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }

        protected override eEffect ShearedEffect => eEffect.AcuityBuff;
        protected override string ShearedName => "Acuity";
    }

    /// <summary>
    /// Frontal cone (Target Cone, Range = length, Radius = arc) dealing Spirit damage to enemy players,
    /// bots and controlled pets only, then removing one concentration buff of one kind from each.
    /// Spell.Value is the strongest buff value it can remove; 0 removes any value.
    /// The stock AbstractBuffShear searches the legacy EffectList, which ECS buffs never enter.
    /// </summary>
    public abstract class ValkyrieConeShear : DirectDamageSpellHandler
    {
        protected ValkyrieConeShear(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }

        protected abstract eEffect ShearedEffect { get; }
        protected abstract string ShearedName { get; }

        public override string ShortDescription =>
            $"Inflicts {Spell.Damage} {Spell.DamageTypeToString()} damage on enemy players and pets in front of you and removes one concentration {ShearedName} buff" +
            (Spell.Value > 0 ? $" of up to {Spell.Value}." : ".");

        public static bool IsPlayerOrPet(GameLiving living) =>
            living is GamePlayer or GameBot || (living is GameNPC npc && npc.Brain is IControlledBrain);

        public static bool CanShear(Spell buff, bool castOnSelf, double maxValue) =>
            buff.IsConcentration && (!castOnSelf || buff.IsShearable) && (maxValue <= 0 || buff.Value <= maxValue);

        public override List<GameLiving> SelectTargets(GameObject castTarget)
        {
            List<GameLiving> targets = base.SelectTargets(castTarget);
            targets.RemoveAll(target => !IsPlayerOrPet(target));
            return targets;
        }

        protected override void DealDamage(GameLiving target)
        {
            base.DealDamage(target);

            if (target.IsAlive && target.ObjectState is GameObject.eObjectState.Active)
                Shear(target);
        }

        private void Shear(GameLiving target)
        {
            ECSGameSpellEffect buff = target.effectListComponent.GetSpellEffects(ShearedEffect)
                .Where(effect => CanShear(effect.SpellHandler.Spell, effect.SpellHandler.Caster == target, Spell.Value))
                .OrderByDescending(effect => effect.SpellHandler.Spell.Value)
                .FirstOrDefault();

            if (buff == null)
                return;

            buff.End();
            MessageToCaster("Your spell rips away some of your target's enhancing magic.", eChatType.CT_Spell);
            MessageToLiving(target, "Some of your enhancing magic has been ripped away by a spell!", eChatType.CT_Spell);
        }
    }
}
