using System;
using System.Linq;
using DOL.AI.Brain;
using DOL.GS;

namespace DOL.GS
{
    public class StormforgedCommander : CommanderPet
    {
        public StormforgedCommander(INpcTemplate template) : base(template)
        {
            InitControlledBrainArray(2);
            Taunting = true;
            DamageFactor = 2.0;
        }
        public override double MaxHealthScalingFactor => 4.0;
        public override double GetArmorAF(eArmorSlot slot) => Math.Max(base.GetArmorAF(slot), Level * 2);
        public override double GetArmorAbsorb(eArmorSlot slot) => Math.Max(base.GetArmorAbsorb(slot), 0.35);
        public override bool SetPetLevel()
        {
            SummonSpellDamage = -100;
            SummonSpellValue = 255;
            return base.SetPetLevel();
        }
    }

    public class StormforgedSupportPet : BdCasterSubPet
    {
        public StormforgedSupportPet(INpcTemplate template) : base(template) { }
        public override double MaxHealthScalingFactor => 2.0;
        public override bool SetPetLevel()
        {
            SummonSpellDamage = -100;
            SummonSpellValue = 255;
            return base.SetPetLevel();
        }
        public override double GetSpellScalingFactor() => Level / 50.0;
        public override void SortSpells()
        {
            base.SortSpells();
            if (HarmfulSpells != null)
                HarmfulSpells = HarmfulSpells.Select(GetScaledSpell).ToList();
            if (InstantHarmfulSpells != null)
                InstantHarmfulSpells = InstantHarmfulSpells.Select(GetScaledSpell).ToList();
            if (HealSpells != null)
                HealSpells = HealSpells.Select(GetScaledSpell).ToList();
        }
    }
}

namespace DOL.AI.Brain
{
    public class StormforgedCommanderBrain : CommanderBrain
    {
        public StormforgedCommanderBrain(GameLiving owner) : base(owner) { }
        public override int ModifyDamageWithTaunt(int damage) => Math.Max(1, damage) * 8;
        public override void Think()
        {
            if (Body is StormforgedCommander commander && commander.SetPetLevel())
                commander.SortSpells();
            base.Think();
        }
    }

    public class StormforgedSupportBrain : BdCasterBrain
    {
        public StormforgedSupportBrain(GameLiving owner) : base(owner) { }
        public override void Think()
        {
            if (Body is StormforgedSupportPet support && support.SetPetLevel())
                support.SortSpells();
            // Heal/buff while following as well as while assisting an attack.
            if (base.CheckSpells(eCheckSpellType.Defensive))
            {
                if (Body.IsMoving) Body.StopMoving();
                return;
            }
            base.Think();
        }
        private GameLiving RootOwner => Owner is GameSummonedPet commander ? commander.Owner : GetLivingOwner();
        private System.Collections.Generic.IEnumerable<GameLiving> SupportTargets(Spell spell)
        {
            // Always include the actual summoner, even when their group roster is
            // temporarily empty or doesn't yet include them after a group change.
            return BonedancerSupportTargets(spell, true).Concat(new[] { RootOwner, Owner })
                .Where(target => target != null && target.IsAlive &&
                    target.ObjectState == GameObject.eObjectState.Active &&
                    target.CurrentRegion == Body.CurrentRegion &&
                    Body.IsWithinRadius(target, spell.CalculateEffectiveRange(Body)) &&
                    GameServer.ServerRules.IsSameRealm(Body, target, true)).Distinct();
        }
        protected override GameLiving FindTargetForDefensiveSpell(Spell spell)
        {
            if (spell.SpellType == eSpellType.Heal)
                return SupportTargets(spell).Where(target => target.HealthPercent < 90)
                    .OrderBy(target => target == RootOwner ? 0 : 1).ThenBy(target => target.HealthPercent).FirstOrDefault();
            if (spell.ID is >= 62220 and <= 62239)
            {
                // Buff the owner and commander first, then the rest of the nearby
                // party/pet roster. The short shaman HoT is only needed when hurt.
                return SupportTargets(spell).Where(target =>
                        (spell.SpellType != eSpellType.HealthRegenBuff || target.HealthPercent < 90) &&
                        !HasEquivalentBuff(target, spell))
                    .OrderBy(target => target == RootOwner ? 0 : target == Owner ? 1 : 2).FirstOrDefault();
            }
            return base.FindTargetForDefensiveSpell(spell);
        }
        private static bool HasEquivalentBuff(GameLiving target, Spell spell)
        {
            eEffect type = EffectHelper.GetEffectFromSpell(spell);
            // A weaker existing buff should be upgraded; an equal/stronger one
            // should not produce an endless "already has that effect" cast loop.
            return target.effectListComponent.GetSpellEffects(type).Any(effect =>
                effect.IsActive && !effect.IsEnding && effect.SpellHandler.Spell.Value >= spell.Value);
        }
        public override bool CheckSpells(eCheckSpellType type)
        {
            if (type == eCheckSpellType.Offensive && base.CheckSpells(eCheckSpellType.Defensive))
                return true;
            return base.CheckSpells(type);
        }
    }
}
