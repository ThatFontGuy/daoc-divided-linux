using System;
using DOL.AI.Brain;
using DOL.Database;
using DOL.Events;
using DOL.GS.PacketHandler;
using DOL.GS.PlayerClass;
using DOL.GS.RealmAbilities;

namespace DOL.GS.Spells
{
    /// <summary>Rules shared by the artifact abilities that have no class spell to reuse.</summary>
    public static class ArtifactAbilities
    {
        public const int CheatDeathHealPercent = 25;

        /// <summary>A Feedback effect stops one matching crowd control spell, then ends.</summary>
        public static bool BlockedByFeedback(GameLiving target, eSpellType crowdControl)
        {
            if (crowdControl is not eSpellType.Mesmerize and not eSpellType.Stun and not eSpellType.UnresistableStun)
                return false;

            eEffect feedback = crowdControl is eSpellType.Mesmerize ? eEffect.ArtifactMezFeedback : eEffect.ArtifactStunFeedback;

            if (ModernRr5.Get(target, feedback) is not { } effect)
                return false;

            effect.End();
            return true;
        }

        /// <summary>A killing blow leaves the owner alive and heals them once. Returns true when it fired.</summary>
        public static bool CheatDeath(GameLiving target, AttackData ad)
        {
            if (ModernRr5.Get(target, eEffect.ArtifactCheatDeath) is not { } effect || ad.Damage + ad.CriticalDamage < target.Health)
                return false;

            ad.CriticalDamage = 0;
            ad.Damage = System.Math.Max(0, target.Health - 1);
            effect.End();
            target.ChangeHealth(target, eHealthChangeType.Spell, target.MaxHealth * CheatDeathHealPercent / 100);
            return true;
        }

        /// <summary>Shape changes a living for a while and puts its model back afterwards. Only one artifact morph at a time.</summary>
        public static bool Morph(GameLiving target, ushort model, int duration, string name, ushort icon)
        {
            if (target?.effectListComponent == null || ModernRr5.Get(target, eEffect.ArtifactMorph) != null)
                return false;

            ushort original = target.Model;
            ModernRr5Classic.Buff(target, duration, eEffect.ArtifactMorph, name, icon, e => SetModel(e.Owner, model), e => SetModel(e.Owner, original));
            return true;
        }

        private static void SetModel(GameLiving living, ushort model)
        {
            living.Model = model;
            (living as GamePlayer)?.Out.SendUpdatePlayer();
        }

        public static void ApplyTimedEffect(SpellHandler handler, GameLiving target, eEffect type)
        {
            ModernRr5.Get(target, type)?.End();
            ModernRr5Classic.Buff(target, handler.Spell.Duration, type, handler.Spell.Name, (ushort) handler.Spell.Icon);
        }
    }

    /// <summary>Arrogance: raises every stat by Value. Pair it with an absorption sub-spell for the melee protection.</summary>
    [SpellHandler(eSpellType.ArtifactAllStats)]
    public class ArtifactAllStatsBuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatBuff(caster, spell, line)
    {
        public override string ShortDescription => $"Increases {TargetPronoun} stats by {Spell.Value}.";
        public override eProperty Property1 => eProperty.Strength;
        public override eProperty Property2 => eProperty.Constitution;
        public override eProperty Property3 => eProperty.Dexterity;
        public override eProperty Property4 => eProperty.Quickness;
        public override eProperty Property5 => eProperty.Acuity;
    }

    /// <summary>The damage half of Arch Magery.</summary>
    [SpellHandler(eSpellType.ArtifactSpellDamage)]
    public class ArtifactSpellDamageBuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatBuff(caster, spell, line)
    {
        public override string ShortDescription => $"Increases {TargetPronoun} spell damage by {Spell.Value}%.";
        public override eProperty Property1 => eProperty.SpellDamage;
    }

    /// <summary>Ring of Dances: lowers the target's spell damage and five magic resists by Value.</summary>
    [SpellHandler(eSpellType.LoreDebuff)]
    public class ArtifactLoreDebuff(GameLiving caster, Spell spell, SpellLine line) : SingleStatDebuff(caster, spell, line)
    {
        public override string ShortDescription => $"Decreases {TargetPronoun} spell damage and resists by {Spell.Value}%.";
        public override eProperty Property1 => eProperty.SpellDamage;
        public override eProperty Property2 => eProperty.Resist_Heat;
        public override eProperty Property3 => eProperty.Resist_Cold;
        public override eProperty Property4 => eProperty.Resist_Matter;
        public override eProperty Property5 => eProperty.Resist_Spirit;
        public override eProperty Property6 => eProperty.Resist_Energy;
        public override eBuffBonusCategory BonusCategory2 => eBuffBonusCategory.Debuff;
        public override eBuffBonusCategory BonusCategory3 => eBuffBonusCategory.Debuff;
        public override eBuffBonusCategory BonusCategory4 => eBuffBonusCategory.Debuff;
        public override eBuffBonusCategory BonusCategory5 => eBuffBonusCategory.Debuff;
        public override eBuffBonusCategory BonusCategory6 => eBuffBonusCategory.Debuff;
    }

    /// <summary>Blocks the next mesmerize (Value 1) or stun (Value 2) cast on the target.</summary>
    [SpellHandler(eSpellType.ArtifactFeedback)]
    public class ArtifactFeedbackSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Blocks the next {(Spell.Value == 1 ? "mesmerize" : "stun")} cast on you.";

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            ArtifactAbilities.ApplyTimedEffect(this, target, Spell.Value == 1 ? eEffect.ArtifactMezFeedback : eEffect.ArtifactStunFeedback);
        }
    }

    /// <summary>The next killing blow is survived instead.</summary>
    [SpellHandler(eSpellType.ArtifactCheatDeath)]
    public class ArtifactCheatDeathSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Survive the next killing blow and heal {ArtifactAbilities.CheatDeathHealPercent}% of your health.";

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            ArtifactAbilities.ApplyTimedEffect(this, target, eEffect.ArtifactCheatDeath);
        }
    }

    /// <summary>
    /// Shape change. LifeDrainReturn is the model, 0 for the wearer's own shade form. Value is an optional spell cast on each morphed
    /// target, for effects that chain further than one sub-spell.
    /// </summary>
    [SpellHandler(eSpellType.ArtifactMorph)]
    public class ArtifactMorphSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "The target is shape changed.";

        public override double CalculateSpellResistChance(GameLiving target)
        {
            return 0;
        }

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            ushort model = (ushort) Spell.LifeDrainReturn;

            if (model == 0 && target is GamePlayer player)
                model = player.CharacterClass is ClassDisciple ? (ushort) 0 : player.ShadeModel;

            if (model != 0 && !ArtifactAbilities.Morph(target, model, Spell.Duration, Spell.Name, (ushort) Spell.Icon))
                MessageToCaster("That target is already shape changed.", eChatType.CT_SpellResisted);

            if (Spell.Value > 0 && SkillBase.GetSpellByID((int) Spell.Value) is { } extra)
                ScriptMgr.CreateSpellHandler(Caster, extra, SpellLine).StartSpell(target);
        }
    }

    /// <summary>Removes an artifact shape change from the target.</summary>
    [SpellHandler(eSpellType.ArtifactShatter)]
    public class ArtifactShatterSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "Removes illusions from the target.";

        public override double CalculateSpellResistChance(GameLiving target)
        {
            return 0;
        }

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            ModernRr5.Get(target, eEffect.ArtifactMorph)?.End();
        }
    }

    /// <summary>
    /// Traitor's Dagger and Zo'arkat pets: a short lived spirit that stays where it appears and attacks only the proc's target.
    /// LifeDrainReturn is the NPC template, ResurrectHealth the drain per hit and AmnesiaChance the percent chance a hit drains.
    /// </summary>
    [SpellHandler(eSpellType.ArtifactProcPet)]
    public class ArtifactProcPetSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SummonSpellHandler(caster, spell, line)
    {
        private GameLiving _victim;
        private ISpellHandler _drain;

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            _victim = target;
            base.ApplyEffectOnTarget(target);

            if (m_pet?.Brain is not ProcPetBrain brain)
                return;

            m_pet.Level = Caster.Level;
            m_pet.MaxSpeedBase = 0;
            brain.AssignTarget(target);
            brain.AddToAggroList(target, 1);
            brain.Think();
        }

        protected override void GetPetLocation(out int x, out int y, out int z, out ushort heading, out Region region)
        {
            base.GetPetLocation(out x, out y, out z, out heading, out region);

            if (_victim == null)
                return;

            x = _victim.X + 24;
            y = _victim.Y + 24;
            z = _victim.Z;
        }

        protected override GameSummonedPet GetGamePet(INpcTemplate template) { return new ArtifactProcPet(template); }
        protected override IControlledBrain GetPetBrain(GameLiving owner) { return new ProcPetBrain(owner); }
        protected override void SetBrainToOwner(IControlledBrain brain) { }
        protected override void AddHandlers() { GameEventMgr.AddHandler(m_pet, GameLivingEvent.AttackFinished, OnPetAttack); }

        private void OnPetAttack(DOLEvent e, object sender, EventArgs arguments)
        {
            if (arguments is not AttackFinishedEventArgs { AttackData: { IsHit: true } attack } || !Util.Chance(Spell.AmnesiaChance))
                return;

            _drain ??= MakeDrain();
            _drain.StartSpell(attack.Target);
        }

        private ISpellHandler MakeDrain()
        {
            DbSpell drain = new()
            {
                Name = Spell.Name,
                Icon = 11020,
                ClientEffect = 11020,
                DamageType = (int) eDamageType.Body,
                Target = eSpellTarget.ENEMY.ToString(),
                Type = eSpellType.PetLifedrain.ToString(),
                Damage = Spell.ResurrectHealth,
                LifeDrainReturn = 100,
                Range = 350
            };
            return ScriptMgr.CreateSpellHandler(m_pet, new Spell(drain, 50), SkillBase.GetSpellLine(GlobalSpellsLines.Reserved_Spells));
        }
    }

    /// <summary>Clears PvE and RvR resurrection illness.</summary>
    [SpellHandler(eSpellType.ArtifactRecovery)]
    public class ArtifactRecoverySpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "Removes resurrection illness.";

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            EffectListService.GetEffectOnTarget(target, eEffect.ResurrectionIllness)?.End();
            EffectListService.GetEffectOnTarget(target, eEffect.RvrResurrectionIllness)?.End();
            MessageToLiving(target, "Your resurrection illness fades.", eChatType.CT_Spell);
        }
    }
}

namespace DOL.GS
{
    public class ArtifactProcPet(INpcTemplate template) : GameSummonedPet(template)
    {
        public override int MaxHealth => Level * 15;
        public override void OnAttackedByEnemy(AttackData ad) { }
    }
}
