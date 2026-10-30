using System;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Live (1.121+) assassin poisons: an instant self buff that fires its poison (Value = the child SpellID) on melee
    /// hits (Frequency = the chance in percent, 100 for every live poison). Landing a poison leaves the buff active
    /// (official 1.121 notes); one poison buff is active at a time (they share an effect group).
    /// </summary>
    [SpellHandler(eSpellType.PoisonCoating)]
    public class PoisonCoatingSpellHandler(GameLiving caster, Spell spell, SpellLine line) : OffensiveProcSpellHandler(caster, spell, line)
    {
        public override string ShortDescription
        {
            get
            {
                ISpellHandler poison = ScriptMgr.CreateSpellHandler(m_caster, SkillBase.GetSpellByID((int) Spell.Value), null);
                return "Coats your weapons. Your melee hits deliver the poison:\n\n" +
                    (poison != null ? poison.ShortDescription : $"Spell with ID {Spell.Value} not found.");
            }
        }

        public override void SendSpellMessages()
        {
            MessageToCaster($"You coat your weapons with {Spell.Name}.", eChatType.CT_Spell);
        }
    }

    /// <summary>A poison snare (Crippling Toxin, Snaring Toxin, Shadowbind): it lasts through damage, ignores snare immunity and grants none.</summary>
    [SpellHandler(eSpellType.PoisonSnare)]
    public class PoisonSnareSpellHandler(GameLiving caster, Spell spell, SpellLine line) : UnbreakableSpeedDecreaseSpellHandler(caster, spell, line)
    {
        protected override bool RespectsSnareImmunity => false;
    }

    /// <summary>
    /// A weaponskill-only debuff (the Weakening Poison line). WeaponSkillPercentCalculator divides debuffs by 5.4
    /// (it was written for the old weaponskill/Con poisons), so Value is the percent times 5.4.
    /// </summary>
    [SpellHandler(eSpellType.WeaponSkillDebuff)]
    public class WeaponSkillDebuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatDebuff(caster, spell, line)
    {
        public override string ShortDescription => $"Decreases {TargetPronoun} weaponskill by {(int) (Math.Abs(Spell.Value) / 5.4)}%.";
        public override eProperty Property1 => eProperty.WeaponSkill;

        protected override void SendUpdates(GameLiving target) { }
    }

    /// <summary>Consume Venom (Envenom 50): removes the caster's own damage-over-time effects; grants no immunity.</summary>
    [SpellHandler(eSpellType.ConsumeVenom)]
    public class ConsumeVenomSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "Removes all damage-over-time effects from you.";

        public override bool StartSpell(GameLiving target)
        {
            int removed = 0;

            foreach (ECSGameSpellEffect effect in Caster.effectListComponent.GetSpellEffects(eEffect.DamageOverTime))
            {
                if (effect.End())
                    removed++;
            }

            MessageToCaster(removed > 0 ? "You consume the venom in your veins." : "You have no damage-over-time effects to consume.", eChatType.CT_Spell);
            return true;
        }

        public override void FinishSpellCast(GameLiving target)
        {
            m_caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }
    }
}
