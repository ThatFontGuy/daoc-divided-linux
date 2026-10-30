using System;
using DOL.GS.Spells;

namespace DOL.GS
{
    public class SavageBuffECSGameEffect : StatBuffECSEffect
    {
        public SavageBuffECSGameEffect(in ECSGameEffectInitParams initParams) : base(initParams) { }

        public override void OnStartEffect()
        {
            ApplyBonuses(false);

            // "You parry with extra skill!"
            // "{0} begins parrying faster!"
            OnEffectStartsMsg(true, false, true);
        }

        public override void OnStopEffect()
        {
            ApplyBonuses(true);
            OnHealthCost();
        }

        // Property2 and Property3 are Undefined (ignored) except for the live all-melee resist buff.
        private void ApplyBonuses(bool isSubtracted)
        {
            AbstractSavageBuff buff = SpellHandler as AbstractSavageBuff;

            foreach (eProperty property in new[] { buff.Property1, buff.Property2, buff.Property3 })
                ApplyBonus(Owner, buff.BonusCategory1, property, SpellHandler.Spell.Value, Effectiveness, isSubtracted);
        }

        private void OnHealthCost()
        {
            if (SpellHandler.Spell.Power == 0)
                return;

            int cost;
            int maxHp = SpellHandler.Caster.MaxHealth;

            if (SpellHandler.Spell.Power < 0)
                cost = (int) (maxHp * Math.Abs(SpellHandler.Spell.Power) * 0.01);
            else
                cost = SpellHandler.Spell.Power;

            // Costs at least 1 HP, leaves at least 1 HP.
            cost = Math.Min(Math.Max(1, cost), Owner.Health - 1);

            // This can be negative if the owner is dead.
            if (cost > 0)
                Owner.ChangeHealth(Owner, eHealthChangeType.Spell, -cost);
        }
    }
}
