using System;
using DOL.Database;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Live 1.123 Vampiir Flight spells: a self speed buff that can be cast and kept while in combat.
    /// Snares, roots, mesmerize and stun still apply normally.
    /// </summary>
    [SpellHandler(eSpellType.VampiirFlight)]
    public class VampiirFlightHandler(GameLiving caster, Spell spell, SpellLine line) : SpeedEnhancementSpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Your speed is increased to {Spell.Value}% of normal. This effect is not broken by combat.";
        protected override bool BlockedInCombat => false;
    }

    /// <summary>
    /// Live 1.128 Vampiir self Determination: reduces the duration of mesmerize, stun and snare/root effects.
    /// </summary>
    [SpellHandler(eSpellType.VampiirDetermination)]
    public class VampiirDeterminationHandler(GameLiving caster, Spell spell, SpellLine line) : SingleStatBuff(caster, spell, line)
    {
        public override string ShortDescription => $"Reduces the duration of crowd control effects on you by {Spell.Value}%.";
        public override eProperty Property1 => eProperty.MesmerizeDurationReduction;
        public override eProperty Property2 => eProperty.StunDurationReduction;
        public override eProperty Property3 => eProperty.SpeedDecreaseDurationReduction;

        protected override void SendUpdates(GameLiving target) { }
    }

    /// <summary>
    /// Live 1.123 Vampiiric Feint style proc: raises the Vampiir's spell critical hit chance to Value% for the duration.
    /// </summary>
    [SpellHandler(eSpellType.VampiirFeint)]
    public class VampiirFeintHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Raises your spell critical hit chance to {Spell.Value}% for {Spell.Duration / 1000} seconds.";

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams)
        {
            return ECSGameEffectFactory.Create(initParams, static (in i) => new VampiirFeintEffect(i));
        }
    }

    public sealed class VampiirFeintEffect : ECSGameSpellEffect
    {
        private int _bonus;

        public VampiirFeintEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.VampiirFeint;
        }

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            _bonus = Math.Max(0, (int)SpellHandler.Spell.Value - Owner.GetModified(eProperty.CriticalSpellHitChance));
            Owner.AbilityBonus[eProperty.CriticalSpellHitChance] += _bonus;
        }

        public override void OnStopEffect()
        {
            base.OnStopEffect();
            Owner.AbilityBonus[eProperty.CriticalSpellHitChance] -= _bonus;
            _bonus = 0;
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }
}
