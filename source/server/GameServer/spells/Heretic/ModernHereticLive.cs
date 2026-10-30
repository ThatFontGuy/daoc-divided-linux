using System;
using System.Linq;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Live 1.123 Hellflower chant: increases the group's maximum health and armor factor by Value percent.
    /// The armor factor share is taken from the member's worn torso armor, the piece that represents its armor AF.
    /// </summary>
    [SpellHandler(eSpellType.HereticHellflower)]
    public class HereticHellflowerHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Increases the maximum health and armor factor of group members by {Spell.Value}%.";

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams)
        {
            return ECSGameEffectFactory.Create(initParams, static (in i) => new HereticHellflowerEffect(i));
        }

        public static int ArmorBonus(GameLiving living, double percent)
        {
            int armor = (living as GamePlayer)?.Inventory?.GetItem(eInventorySlot.TorsoArmor)?.DPS_AF ?? living.Level * 2;
            return Math.Max(1, (int)(armor * percent / 100));
        }

        public static int HealthBonus(GameLiving living, double percent) => Math.Max(1, (int)(living.MaxHealth * percent / 100));
    }

    /// <summary>
    /// Live 1.125 Cocoon: places an all-damage ablative (100% absorption) on the enemy, with combat effectiveness and
    /// melee swing speed debuffs that ramp every 2 seconds and end with the ablative. Always lands, keeps its full
    /// duration, and cannot be reapplied while a Cocoon is on the target.
    /// </summary>
    [SpellHandler(eSpellType.HereticCocoon)]
    public class HereticCocoonHandler(GameLiving caster, Spell spell, SpellLine line) : BothAblativeArmorSpellHandler(caster, spell, line)
    {
        public const int RampMs = 2000;
        public int Start => Param("CocoonStart");
        public int Step => Param("CocoonStep");
        public int Max => Param("CocoonMax");
        private int Param(string key) { Spell.TryGetParamSingle(key, out int value); return value; }

        public override string ShortDescription => $"Covers the enemy in a {Spell.Value}-point ablative that absorbs all damage, and debuffs its combat effectiveness and melee swing speed by {Start}%, rising {Step}% every 2 seconds to {Max}%. The debuffs end when the ablative breaks. Cannot be reapplied while active.";
        public override double CalculateSpellResistChance(GameLiving target) => 0;
        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;

        public static bool HasCocoon(GameLiving target) => target.effectListComponent.GetSpellEffects(eEffect.AblativeArmor)
            .Any(e => e is HereticCocoonEffect && !e.IsEnding);

        public static int Ramp(int start, int step, int max, int pulses) => Math.Min(max, start + step * pulses);

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            if (HasCocoon(target))
            {
                MessageToCaster($"{target.GetName(0, true)} is already cocooned.", eChatType.CT_SpellResisted);
                return;
            }
            base.ApplyEffectOnTarget(target);
        }

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams)
        {
            return ECSGameEffectFactory.Create(initParams, static (in i) => new HereticCocoonEffect(i));
        }
    }

    public sealed class HereticCocoonEffect : AblativeArmorECSGameEffect
    {
        private int _debuff;
        private double _effectiveness;
        private int _pulses;

        public HereticCocoonEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            PulseFreq = HereticCocoonHandler.RampMs;
            NextTick = GameLoop.GameLoopTime + HereticCocoonHandler.RampMs;
        }

        private HereticCocoonHandler Cocoon => (HereticCocoonHandler)SpellHandler;
        public int Debuff => _debuff;

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            Apply(Cocoon.Start);
        }

        public override void OnEffectPulse()
        {
            _pulses++;
            Apply(HereticCocoonHandler.Ramp(Cocoon.Start, Cocoon.Step, Cocoon.Max, _pulses));
        }

        public override void OnStopEffect()
        {
            Apply(0);
            base.OnStopEffect();
        }

        private void Apply(int percent)
        {
            Owner.DebuffCategory[eProperty.MeleeSpeed] += percent - _debuff;
            _debuff = percent;
            if (Owner is GamePlayer player)
            {
                player.Effectiveness += _effectiveness;
                _effectiveness = Math.Min(player.Effectiveness, percent / 100.0);
                player.Effectiveness -= _effectiveness;
                player.Out.SendUpdateWeaponAndArmorStats();
            }
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    public sealed class HereticHellflowerEffect : ECSGameSpellEffect
    {
        private int _health;
        private int _armor;

        public HereticHellflowerEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.HereticHellflower;
        }

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            double percent = SpellHandler.Spell.Value;
            _health = HereticHellflowerHandler.HealthBonus(Owner, percent);
            _armor = HereticHellflowerHandler.ArmorBonus(Owner, percent);
            Owner.BaseBuffBonusCategory[eProperty.MaxHealth] += _health;
            Owner.OtherBonus[eProperty.ArmorFactor] += _armor;
            (Owner as GamePlayer)?.Out.SendCharStatsUpdate();
        }

        public override void OnStopEffect()
        {
            base.OnStopEffect();
            Owner.BaseBuffBonusCategory[eProperty.MaxHealth] -= _health;
            Owner.OtherBonus[eProperty.ArmorFactor] -= _armor;
            _health = _armor = 0;
            if (Owner.Health > Owner.MaxHealth)
                Owner.Health = Owner.MaxHealth;
            (Owner as GamePlayer)?.Out.SendCharStatsUpdate();
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }
}
