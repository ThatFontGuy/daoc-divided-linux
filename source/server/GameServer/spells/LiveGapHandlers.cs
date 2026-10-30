using System;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>Shaman Weary..Halt Magic (live 1.130a Cave): the target's spell damage is lowered by Value%.</summary>
    [SpellHandler(eSpellType.SpellDamageDebuff)]
    public class SpellDamageDebuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatDebuff(caster, spell, line)
    {
        public override string ShortDescription => $"Decreases {TargetPronoun} spell damage by {Spell.Value}%.";
        public override eProperty Property1 => eProperty.SpellDamage;

        protected override void SendUpdates(GameLiving target) { }
    }

    /// <summary>
    /// Shaman Bane of Magic..Prophecy (live 1.130a Cave): the target's spells cost more power, Value tenths of a percent
    /// (100 = +10%). Read in SpellHandler.PowerCost.
    /// </summary>
    [SpellHandler(eSpellType.PowerCostDebuff)]
    public class PowerCostDebuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatDebuff(caster, spell, line)
    {
        public override string ShortDescription => $"Increases {TargetPronoun} power costs by {Spell.Value / 10:0.#}%.";
        public override eProperty Property1 => eProperty.SpellPowerCost;

        protected override void SendUpdates(GameLiving target) { }

        /// <summary>The multiplier on <paramref name="living"/>'s power costs.</summary>
        public static double Scale(GameLiving living) =>
            living?.DebuffCategory == null ? 1 : 1 + Math.Abs(living.DebuffCategory[eProperty.SpellPowerCost]) * 0.001;
    }

    /// <summary>Minstrel Song of Magic..Sorcerous Reach (live 1.130a): the group's spell range is raised by Value%.</summary>
    [SpellHandler(eSpellType.SpellRangeBuff)]
    public class SpellRangeBuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatBuff(caster, spell, line)
    {
        public override string ShortDescription => $"Increases {TargetPronoun} spell range by {Spell.Value}%.";
        public override eProperty Property1 => eProperty.SpellRange;
        public override eBuffBonusCategory BonusCategory1 => eBuffBonusCategory.BaseBuff;
    }

    /// <summary>
    /// Shaman Spirit Shell (live 1.130a Augmentation): all damage the target takes is lowered by Value% while it lasts
    /// (GameLiving.OnAttackedByEnemy, before ablatives).
    /// </summary>
    [SpellHandler(eSpellType.DamageReduction)]
    public class DamageReductionSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Reduces all damage taken by {Spell.Value}%.";

        public static int Percent(GameLiving living)
        {
            if (living?.effectListComponent == null)
                return 0;

            int best = 0;
            foreach (ECSGameSpellEffect effect in living.effectListComponent.GetSpellEffects(eEffect.DamageReduction))
            {
                if (effect.IsActive)
                    best = Math.Max(best, (int) effect.SpellHandler.Spell.Value);
            }

            return Math.Min(100, best);
        }

        public static void Reduce(GameLiving owner, AttackData ad)
        {
            if (ad == null || !ad.IsHit)
                return;

            int percent = Percent(owner);
            if (percent <= 0)
                return;

            ad.Damage -= ad.Damage * percent / 100;
            ad.CriticalDamage -= ad.CriticalDamage * percent / 100;
        }
    }

    /// <summary>
    /// Heightened Awareness (live 1.130a Stealth): a group pulse raising stealth detection by Value%. Unlike Track, moving
    /// doesn't end it; TrackStealthSpellHandler.Bonus takes the stronger of the two.
    /// </summary>
    [SpellHandler(eSpellType.StealthDetectionAura)]
    public class StealthDetectionAuraSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Increases the group's stealth detection by {Spell.Value}%.";
    }

    /// <summary>Friar Novice..Grandmaster Staffman (live 1.130a Enhancement): +Value to the Staff skill.</summary>
    [SpellHandler(eSpellType.StaffSkillBuff)]
    public class StaffSkillBuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatBuff(caster, spell, line)
    {
        public override string ShortDescription => $"Increases {TargetPronoun} Staff skill by {Spell.Value}.";
        public override eProperty Property1 => eProperty.Skill_Staff;
    }

    /// <summary>Shaman Escape Hold (live 1.130a Cave): frees another realm member from roots and snares.</summary>
    [SpellHandler(eSpellType.CureRoot)]
    public class CureRootSpellHandler : RemoveSpellEffectHandler
    {
        public override string ShortDescription => "Removes roots and snares from the target. Cannot be cast on yourself.";

        public CureRootSpellHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line)
        {
            m_spellTypesToRemove = [nameof(eEffect.MovementSpeedDebuff)];
        }

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if (selectedTarget == Caster || selectedTarget == null)
            {
                MessageToCaster("You cannot use this on yourself.", eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }
    }
}
