using System;
using DOL.GS.PacketHandler;
using DOL.GS.Spells;

namespace DOL.GS.spells
{
    [SpellHandler(eSpellType.PowerRend)]
    public class PowerRendSpellHandler : SpellHandler
    {
        public PowerRendSpellHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => $"Removes {Spell.Value * 100:0}% of each enemy's maximum power.";
        public static int DrainAmount(int maximum, int current, double fraction) =>
            Math.Min(Math.Max(0,current), (int)(Math.Max(0,maximum) * Math.Clamp(fraction,0,1)));
        public override void OnDirectEffect(GameLiving target)
        {
            if (target == null || !target.IsAlive || target.ObjectState != GameObject.eObjectState.Active)
                return;
            GameLiving pool = target is NecromancerPet pet ? pet.Owner : target;
            if (pool == null) return;
            int drained = DrainAmount(pool.MaxMana, pool.Mana, Spell.Value);
            pool.Mana -= drained;
            SendEffectAnimation(target,Spell.ClientEffect,0,false,1);
            MessageToCaster($"You rend {drained} power from {target.Name}.",eChatType.CT_Spell);
            pool.MessageToSelf($"You lose {drained} power.",eChatType.CT_Spell);
            target.StartInterruptTimer(target.SpellInterruptDuration,AttackData.eAttackType.Spell,Caster);
        }
        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }
}
