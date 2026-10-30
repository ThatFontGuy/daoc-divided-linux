using System;
using System.Linq;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>Bounded player-test rules. Stock spells and other classes are never modified.</summary>
    public static class ModernWarlock
    {
        public const int FirstSpell = 66000;
        public const int LastSpell = 66399;
        public const string ChamberReuse = "ModernWarlock.ChamberReuse";
        public static bool Owns(int id) => id >= FirstSpell && id <= LastSpell;
        public static bool IsPlayer(GameLiving caster) => caster is GamePlayer { CharacterClass.ID: (int)eCharacterClass.Warlock };
        public static int PrimerMode(Spell spell) => spell.ID is >= 66000 and <= 66005 ? 1 : spell.ID is >= 66010 and <= 66015 ? 2 : 3;
        public static ECSGameSpellEffect Primer(GameLiving caster) => IsPlayer(caster)
            ? caster.effectListComponent.GetSpellEffects(eEffect.WarlockPrimer).FirstOrDefault(x => x.IsActive && !x.IsEnding)
            : null;
        public static bool Secondary(GameLiving caster, Spell spell) => IsPlayer(caster) && Owns(spell.ID) && spell.IsSecondary;
        public static bool IsUninterruptible(GameLiving caster, Spell spell) => Secondary(caster, spell) && Primer(caster) is { } p && PrimerMode(p.SpellHandler.Spell) == 2;
        public static int AdjustDistance(GameLiving caster, Spell spell, int distance) => Secondary(caster, spell) && Primer(caster) is { } p && PrimerMode(p.SpellHandler.Spell) == 1
            ? ScaleDistance(distance, p.SpellHandler.Spell.Value) : distance;
        public static int ScaleDistance(int distance, double percent) => (int)Math.Round(distance * (1 + percent * 0.01));
        public static int AdjustCastTime(GameLiving caster, Spell spell, int time) => Secondary(caster, spell) && Primer(caster) is { } p && PrimerMode(p.SpellHandler.Spell) == 3
            ? ScaleDistance(time, p.SpellHandler.Spell.Value) : time;
        public static double DamageScale(GameLiving caster, Spell spell) => spell.Damage > 0 && IsUninterruptible(caster, spell) ? 1 - Primer(caster).SpellHandler.Spell.Value * 0.01 : 1;
        public static int PercentCost(int baseMana, double percent) => Math.Max(0, (int)(baseMana * Math.Abs(percent) * 0.01));
        public static int? SecondaryCost(GameLiving caster, Spell spell)
        {
            if (!Secondary(caster, spell)) return null;
            var primer = Primer(caster);
            if (primer == null || PrimerMode(primer.SpellHandler.Spell) == 3) return 0;
            var player = (GamePlayer)caster;
            int baseMana = player.CalculateMaxMana(player.Level, player.GetBaseStat(player.CharacterClass.ManaStat));
            return PercentCost(baseMana, primer.SpellHandler.Spell.Power);
        }

        // Tooltip note for secondaries: the client delve has no field for the primer rules, so they are spelled out.
        public const string SecondaryNote = "Secondary spell: needs an active primer stance. Its power cost comes from the primer: " +
            "none with a Powerless primer (Pure, Fluent, Skillful, Artistic or Masterful Cast, which lengthen the cast), " +
            "5% of base power with a Range primer, and the primer's listed percentage with an Uninterruptible primer.";
        public static string DelveNote(Spell spell) => spell != null && Owns(spell.ID) && spell.IsSecondary ? SecondaryNote : null;

        public static int ChainStage(Spell spell) => spell.TryGetParamSingle("WarlockStage", out int stage) is CustomParamsExtensions.RetrievalResult.Success or CustomParamsExtensions.RetrievalResult.SuccessFromConversion ? stage : 0;
        public static bool HasStage(GameLiving target, GameLiving caster, int stage) => target != null && target.effectListComponent.GetSpellEffects(eEffect.DamageOverTime)
            .Any(x => x.IsActive && !x.IsEnding && ReferenceEquals(x.SpellHandler.Caster, caster) && x.SpellHandler.Spell.SpellType == eSpellType.WarlockChainDot && ChainStage(x.SpellHandler.Spell) == stage);
        public static bool ChainReady(int stage, bool dread, bool anguish, bool agony) => stage < 3 || dread && anguish && (stage != 4 || agony);

        // Release is handled before the six-second load is enqueued, so unloading can be instant and mobile.
        public static bool TryRelease(GameLiving caster, Spell spell, SpellLine line)
        {
            if (!IsPlayer(caster) || !Owns(spell.ID) || spell.SpellType != eSpellType.WarlockChamber) return false;
            var ready = caster.effectListComponent.GetSpellEffects(eEffect.WarlockChamber)
                .OfType<WarlockReadyEffect>().FirstOrDefault(x => x.IsActive && !x.IsEnding && x.SpellHandler.Spell.ID == spell.ID);
            if (ready == null) return false;
            var player = (GamePlayer)caster;
            if (!caster.IsAlive || caster.IsCrowdControlled || caster.IsSilenced || caster.IsSitting || caster.castingComponent.IsCasting ||
                GameLoop.GameLoopTime < caster.TempProperties.GetProperty<long>(ChamberReuse))
            {
                player.Out.SendMessage("You cannot release that chamber yet or in your current state.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return true;
            }
            GameLiving target = spell.ID == 66185 ? player.TargetObject as GameLiving : caster;
            if (spell.ID == 66185 && (target == null || !target.IsAlive || !caster.IsWithinRadius(target, 2000) ||
                !player.TargetInView || GameServer.ServerRules.IsAllowedToAttack(caster, target, true)))
            {
                player.Out.SendMessage("Select a living friendly target in sight within 2000 units.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return true;
            }
            switch (spell.ID)
            {
                case 66180:
                    ECSGameEffectFactory.Create(new(caster, 20000, 1, ready.SpellHandler), false, static (in i, hot) => new WarlockChamberBonusEffect(i, hot));
                    break;
                case 66181:
                    var burst = SkillBase.GetSpellByID(66290);
                    if (burst == null) return true;
                    ScriptMgr.CreateSpellHandler(caster, burst, line).StartSpell(caster);
                    break;
                case 66182:
                    caster.ChangeMana(caster, eManaChangeType.Spell, PercentCost(caster.MaxMana, 40));
                    break;
                case 66183:
                    caster.RemoveDisabledSkill(SkillBase.GetAbility(Abilities.Quickcast));
                    break;
                case 66184:
                    ECSGameEffectFactory.Create(new(caster, 20000, 1, ready.SpellHandler), true, static (in i, hot) => new WarlockChamberBonusEffect(i, hot));
                    break;
                case 66185:
                    target.ChangeHealth(caster, eHealthChangeType.Spell, target.MaxHealth / 2);
                    break;
                default: return true;
            }
            ready.End();
            caster.TempProperties.SetProperty(ChamberReuse, GameLoop.GameLoopTime + 10000);
            foreach (var spellLine in player.GetSpellLines())
                foreach (var chamber in SkillBase.GetSpellList(spellLine.KeyName).Where(x => x.SpellType == eSpellType.WarlockChamber))
                    caster.DisableSkill(chamber, 10000);
            player.Out.SendMessage($"You release {spell.Name}.", eChatType.CT_Spell, eChatLoc.CL_SystemWindow);
            return true;
        }
    }

    [SpellHandler(eSpellType.WarlockPrimer)]
    public sealed class WarlockPrimerHandler : SpellHandler
    {
        public WarlockPrimerHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        // Each rank's penalty and secondary cost live in its description.
        public override string ShortDescription => string.IsNullOrEmpty(Spell.Description)
            ? "Toggle a maintained primer stance. Only one may be active. Its modifier and power cost apply to each secondary cast; switching during a cast is forbidden."
            : Spell.Description;
        public override int PowerCost(GameLiving target) => 0;
        public override bool CheckBeginCast(GameLiving target, bool quiet)
        {
            var running = Caster.castingComponent.SpellHandler;
            if (!ModernWarlock.IsPlayer(Caster) || running != null && !ReferenceEquals(running, this)) return false;
            if (!base.CheckBeginCast(target, quiet)) return false;
            var active = ModernWarlock.Primer(Caster);
            if (active?.SpellHandler.Spell.ID == Spell.ID) { active.End(); return false; }
            return true;
        }
        public override void OnDirectEffect(GameLiving target) =>
            ECSGameEffectFactory.Create(new(Caster, 0, 1, this), static (in i) => new WarlockPrimerEffect(i));
    }

    public sealed class WarlockPrimerEffect : ECSGameSpellEffect
    {
        // A spell effect with no duration would expire on the next tick; a primer is held until changed or cancelled.
        public WarlockPrimerEffect(in ECSGameEffectInitParams p) : base(p)
        {
            EffectType = eEffect.WarlockPrimer;
            Duration = 0;
            ExpireTick = long.MaxValue;
        }
        public override bool IsBetterThan(ECSGameEffect effect) => true;
        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    [SpellHandler(eSpellType.WarlockChamber)]
    public sealed class WarlockChamberHandler : SpellHandler
    {
        public WarlockChamberHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => Spell.Description;
        public override int CalculateCastingTime() => 6000;
        public override int PowerCost(GameLiving target) => 0;
        public override bool CheckBeginCast(GameLiving target, bool quiet) => ModernWarlock.IsPlayer(Caster) && !Caster.IsMoving && !Caster.IsStrafing && base.CheckBeginCast(target, quiet);
        public override bool CheckEndCast(GameLiving target) => !Caster.IsMoving && !Caster.IsStrafing && base.CheckEndCast(target);
        public override bool HasConflictingEffectWith(ISpellHandler compare) => Spell.ID == compare.Spell.ID;
        public override void OnDirectEffect(GameLiving target)
        {
            ECSGameEffectFactory.Create(new(Caster, 0, 1, this), static (in i) => new WarlockReadyEffect(i));
            if (Caster is GamePlayer player)
                player.Out.SendMessage($"{Spell.Name} is ready. Use it again to release its fixed effect.", eChatType.CT_Spell, eChatLoc.CL_SystemWindow);
        }
    }

    public sealed class WarlockReadyEffect : ECSGameSpellEffect
    {
        // A loaded chamber stays ready until it is released (or the Warlock logs out).
        public WarlockReadyEffect(in ECSGameEffectInitParams p) : base(p)
        {
            EffectType = eEffect.WarlockChamber;
            Duration = 0;
            ExpireTick = long.MaxValue;
        }
        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    public sealed class WarlockChamberBonusEffect : ECSGameSpellEffect
    {
        private readonly bool _hot;
        public WarlockChamberBonusEffect(in ECSGameEffectInitParams p, bool hot) : base(p)
        {
            _hot = hot;
            EffectType = eEffect.WarlockChamberBonus;
            PulseFreq = hot ? 2000 : 0;
            NextTick = GameLoop.GameLoopTime + 2000;
        }
        public override void OnStartEffect() { if (!_hot) Owner.AbilityBonus[eProperty.CriticalSpellHitChance] += 10; }
        public override void OnStopEffect() { if (!_hot) Owner.AbilityBonus[eProperty.CriticalSpellHitChance] -= 10; }
        public override void OnEffectPulse()
        {
            if (!_hot || !Owner.IsAlive) return;
            var members = Owner.Group?.GetMembersInTheGroup() ?? new System.Collections.Generic.List<GameLiving> { Owner };
            foreach (var member in members)
                if (member.IsAlive && Owner.IsWithinRadius(member, 350))
                    member.ChangeHealth(Owner, eHealthChangeType.Spell, Math.Max(1, member.MaxHealth * 3 / 100));
        }
        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    [SpellHandler(eSpellType.WarlockChainDot)]
    public sealed class WarlockChainDotHandler : DoTSpellHandler
    {
        public WarlockChainDotHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override bool CheckBeginCast(GameLiving target, bool quiet)
        {
            // Player requests commonly omit an explicit target. The base check resolves the
            // selected target (and spell-queue rules) before we inspect chain prerequisites.
            if (!base.CheckBeginCast(target, quiet)) return false;
            target = Target;
            int stage = ModernWarlock.ChainStage(Spell);
            if (!ModernWarlock.ChainReady(stage, ModernWarlock.HasStage(target, Caster, 1), ModernWarlock.HasStage(target, Caster, 2), ModernWarlock.HasStage(target, Caster, 3)))
            {
                if (!quiet) MessageToCaster("The preceding Witchcraft effects must be active from your own spells.", eChatType.CT_System);
                return false;
            }
            return true;
        }
        public override bool CheckEndCast(GameLiving target) => ModernWarlock.ChainReady(ModernWarlock.ChainStage(Spell),
            ModernWarlock.HasStage(target, Caster, 1), ModernWarlock.HasStage(target, Caster, 2), ModernWarlock.HasStage(target, Caster, 3)) && base.CheckEndCast(target);
        protected override int CalculateEffectDuration(GameLiving target) => ModernWarlock.ChainStage(Spell) == 4 ? 10000 : base.CalculateEffectDuration(target);
        public override void CastSubSpells(GameLiving target) { }
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams p) => ECSGameEffectFactory.Create(p, static (in i) => new WarlockChainDotEffect(i));
    }

    public sealed class WarlockChainDotEffect : DamageOverTimeECSGameEffect
    {
        public bool Cured;
        public WarlockChainDotEffect(in ECSGameEffectInitParams p) : base(p) { }
        public override void OnStartEffect()
        {
            base.OnStartEffect();
            int stage = ModernWarlock.ChainStage(SpellHandler.Spell);
            if (stage is 1 or 3 && SpellHandler.Spell.SubSpellID != 0)
            {
                var sub = SkillBase.GetSpellByID(SpellHandler.Spell.SubSpellID);
                if (sub != null) ScriptMgr.CreateSpellHandler(SpellHandler.Caster, sub, SpellHandler.SpellLine).StartSpell(stage == 1 ? SpellHandler.Caster : Owner);
            }
        }
        public override void OnStopEffect()
        {
            base.OnStopEffect();
            if (ModernWarlock.ChainStage(SpellHandler.Spell) != 4 || IsBeingReplaced || !Owner.IsAlive || !SpellHandler.Caster.IsAlive || !(Cured || GameLoop.GameLoopTime >= ExpireTick)) return;
            var burst = SkillBase.GetSpellByID(SpellHandler.Spell.SubSpellID);
            if (burst != null && GameServer.ServerRules.IsAllowedToAttack(SpellHandler.Caster, Owner, true))
                ScriptMgr.CreateSpellHandler(SpellHandler.Caster, burst, SpellHandler.SpellLine).StartSpell(Owner);
        }
    }
}


