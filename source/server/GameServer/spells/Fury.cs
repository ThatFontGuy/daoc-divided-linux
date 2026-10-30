namespace DOL.GS.Spells
{
    /// <summary>Fury (tank shout): all magic resists for the caster, and a chance to shrug off crowd control (Value% each).</summary>
    [SpellHandler(eSpellType.Fury)]
    public class FuryHandler(GameLiving caster, Spell spell, SpellLine line) : AllMagicResistsAbilityBuff(caster, spell, line)
    {
        public override string ShortDescription => $"You gain a {Spell.Value}% bonus to all magic resistances and a {Spell.Value}% chance to shrug off crowd control spells.";

        /// <summary>The chance for the target to shrug off this spell: Rampage against debuffs, Fury against crowd control.</summary>
        public static int ShrugChance(ISpellHandler handler, GameLiving target)
        {
            if (target == null || handler.HasPositiveEffect)
                return 0;

            int chance = 0;

            if (handler is PropertyChangingSpell && handler.Spell.IsDebuff && EffectListService.GetEffectOnTarget(target, eEffect.TankRampage) is ECSGameSpellEffect rampage)
                chance = (int) rampage.SpellHandler.Spell.Value;

            if (IsCrowdControl(handler) && EffectListService.GetEffectOnTarget(target, eEffect.TankFury) is ECSGameSpellEffect fury)
                chance = System.Math.Max(chance, (int) fury.SpellHandler.Spell.Value);

            return chance;
        }

        private static bool IsCrowdControl(ISpellHandler handler)
        {
            return handler is AbstractCCSpellHandler || handler.Spell.SpellType is eSpellType.SpeedDecrease or eSpellType.UnbreakableSpeedDecrease or eSpellType.DamageSpeedDecrease;
        }
    }
}
