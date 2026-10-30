using System;
using System.Collections.Generic;
using DOL.GS.Effects;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    [SpellHandler(eSpellType.StormforgedStrike)]
    public class StormforgedStrike : DirectDamageSpellHandler
    {
        public StormforgedStrike(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }

        public override string ShortDescription => $"Lightning damage: {Spell.Damage}. Each damaging hit restores {Spell.LifeDrainReturn}% as health and {Spell.Value}% as power and endurance.";

        protected override void DealDamage(GameLiving target)
        {
            if (target == null || !target.IsAlive || target.ObjectState != GameObject.eObjectState.Active)
                return;

            Caster.Stealth(false);
            AttackData attack = CalculateDamageToTarget(target);
            if (StormforgedHeroicRules.HasAvatar(Caster))
            {
                attack.Damage *= 2;
                attack.CriticalDamage *= 2;
            }
            int healthBefore = target.Health;
            SendDamageMessages(attack);
            DamageTarget(attack, true);
            // Never restore on a resist, immunity, absorbed hit or overkill damage.
            int dealt = Math.Min(healthBefore, Math.Max(0, attack.Damage + attack.CriticalDamage));
            if (dealt > 0 && Caster.IsAlive)
            {
                Caster.ChangeHealth(Caster, eHealthChangeType.Spell, StormforgedRules.RestorePerHit(dealt, Spell.LifeDrainReturn));
                Caster.ChangeMana(Caster, eManaChangeType.Spell, StormforgedRules.RestorePerHit(dealt, (int)Spell.Value));
                Caster.ChangeEndurance(Caster, eEnduranceChangeType.Spell, StormforgedRules.RestorePerHit(dealt, (int)Spell.Value));
            }

            target.StartDamageInterruptTimer(target.SpellInterruptDuration, attack);
        }
    }

    /// <summary>Timed maintained effects deliberately do not use the stock song pulse slot.</summary>
    public abstract class StormforgedMaintainedSpell : SpellHandler
    {
        protected StormforgedMaintainedSpell(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override bool UnstealthCasterOnStart => false;
        public override bool UnstealthCasterOnFinish => false;
        public override void CastSubSpells(GameLiving target) { }

        // A self spell with a radius (the chant's 1,500, the Avatar's 350) went through the stock PBAE branch, which puts the
        // effect on every non-hostile player and NPC in range: town NPCs, guards and strangers' bots got the chant's speed,
        // resists and damage add, or the Avatar form. The effects fan out on their own (the chant to its group and their pets).
        public override List<GameLiving> SelectTargets(GameObject castTarget)
        {
            if (Spell.Target is not eSpellTarget.SELF)
                return base.SelectTargets(castTarget);
            List<GameLiving> list = GameLoop.GetListForTick<GameLiving>();
            list.Add(Caster);
            return list;
        }

        public override void FinishSpellCast(GameLiving target)
        {
            Caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }
    }

    [SpellHandler(eSpellType.StormforgedAura)]
    public class StormforgedAura : StormforgedMaintainedSpell
    {
        public StormforgedAura(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => "Maintained lightning storm. Each enemy damaged restores health, power and endurance separately. Cancel the buff icon to stop it.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new StormforgedAuraEffect(i));
    }

    [SpellHandler(eSpellType.StormforgedChant)]
    public class StormforgedChant : StormforgedMaintainedSpell
    {
        public StormforgedChant(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => $"Until cancelled: restores {Spell.Damage} health, power and endurance every {Spell.Frequency / 1000.0:0.#} seconds to your group within {Spell.Radius} units. Movement speed: {Spell.Value}% of normal, including combat and stealth. Weapon damage add: {SkillBase.GetSpellByID(Spell.SubSpellID)?.Damage ?? 0:0.#}. Roots and mezzes still apply.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new StormforgedChantEffect(i));
    }

    [SpellHandler(eSpellType.StormforgedWard)]
    public class StormforgedWard : StormforgedMaintainedSpell
    {
        public StormforgedWard(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => StormSovereignAbilities.Owns(Spell.ID)
            ? "Full base and specialization buffs to all eight stats, scaling with character level. Innate vitality and normal equipment bonuses stack separately."
            : $"All eight stats (STR, CON, DEX, QUI, INT, PIE, EMP, CHA): +{Math.Max(1, (int)(Caster.Level * 1.25))} base and +{Math.Max(1, (int)(Caster.Level * 1.875))} specialization bonus each. " +
            $"Armor factor: +{Math.Max(1, Caster.Level * 2)}. All nine resists: +{Math.Max(1, (int)Math.Ceiling(26 * Math.Min(40, (int)Caster.Level) / 40.0))}%. " +
            $"Weapon damage add: {SkillBase.GetSpellByID(Spell.ID + 8)?.Damage ?? 0:0.#}. Reactive damage shield: {SkillBase.GetSpellByID(Spell.SubSpellID)?.Damage ?? 0:0.#}. Bonuses scale with your level; normal stat caps apply.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new StormforgedWardEffect(i));
    }

    [SpellHandler(eSpellType.StormforgedRest)]
    public class StormforgedRest : HealSpellHandler
    {
        public StormforgedRest(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override bool CheckBeginCast(GameLiving target) => CanRecover(target) && base.CheckBeginCast(target);
        public override bool CheckEndCast(GameLiving target) => CanRecover(target) && base.CheckEndCast(target);
        public override bool StartSpell(GameLiving target) => CanRecover(target) && base.StartSpell(target);

        private bool CanRecover(GameLiving target)
        {
            if (!Caster.InCombat && target?.InCombat != true)
                return true;
            MessageToCaster("Stormrest requires both you and your target to be out of combat.", eChatType.CT_SpellResisted);
            return false;
        }
    }

    [SpellHandler(eSpellType.StormforgedPet)]
    public class StormforgedPet : SummonSpiritFighter
    {
        public StormforgedPet(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override bool IsSummoningSpell => true;
        public override string ShortDescription => "Summons a tank commander and two support spirits at your level. The mender heals, casts lightning and slows attacks; the caster casts lightning and weakens energy resistance. All share pet controls.";
        protected override DOL.AI.Brain.IControlledBrain GetPetBrain(GameLiving owner) => new DOL.AI.Brain.StormforgedCommanderBrain(owner);
        protected override GameSummonedPet GetGamePet(INpcTemplate template) => new StormforgedCommander(template);

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            base.ApplyEffectOnTarget(target);
            if (Pet == null || Pet.ObjectState != GameObject.eObjectState.Active) return;
            Pet.Spells = new System.Collections.Generic.List<Spell>
            {
                SkillBase.GetSpellByID(Spell.ID + 1), SkillBase.GetSpellByID(Spell.ID + 4), SkillBase.GetSpellByID(62219)
            }.FindAll(spell => spell != null);
            foreach (int id in new[] { 62206, 62207 })
                if (SkillBase.GetSpellByID(id) is Spell summon)
                    new StormforgedSupportSummon(Caster, summon, SpellLine).ApplyEffectOnTarget(target);
        }

        public override void OnPetReleased()
        {
            if (Pet?.ControlledNpcList != null)
                foreach (var brain in (DOL.AI.Brain.IControlledBrain[])Pet.ControlledNpcList.Clone())
                    (brain as DOL.AI.Brain.ControlledMobBrain)?.OnRelease();
            base.OnPetReleased();
        }
    }

    // Automatic support summons deliberately bypass the stock Bonedancer 75-level pool.
    // The owner is still the player for spell effects; the commander owns their brains.
    public class StormforgedSupportSummon : SummonSpellHandler
    {
        public StormforgedSupportSummon(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { m_isSilent = true; }
        protected override DOL.AI.Brain.IControlledBrain GetPetBrain(GameLiving owner) => new DOL.AI.Brain.StormforgedSupportBrain(owner.ControlledBrain.Body);
        protected override GameSummonedPet GetGamePet(INpcTemplate template) => new StormforgedSupportPet(template);
        protected override void SetBrainToOwner(DOL.AI.Brain.IControlledBrain brain) => Caster.ControlledBrain.Body.AddControlledBrain(brain);
        public override void OnPetReleased()
        {
            if (Pet?.Owner is CommanderPet commander && Pet.Brain is DOL.AI.Brain.IControlledBrain brain)
                commander.RemoveControlledBrain(brain);
        }
    }
}
