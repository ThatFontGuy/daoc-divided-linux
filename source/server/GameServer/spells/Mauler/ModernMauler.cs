using System;
using System.Linq;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    public static class ModernMauler
    {
        public static bool Owns(int id) => id is >= 67000 and <= 67999;
        public static bool IsMauler(int id) => id is >= 60 and <= 62;
        // Mauler players and Mauler bots (the bot companions and gamebots) follow the same rules.
        public static bool IsPlayer(GameLiving living) => living switch
        {
            GamePlayer p => IsMauler(p.CharacterClass.ID),
            IGamePlayer bot => bot.CharacterClass != null && IsMauler(bot.CharacterClass.ID),
            _ => false
        };
        public static int Param(Spell spell, string key)
        {
            spell.TryGetParamSingle(key, out int value);
            return value;
        }
        public static ECSGameSpellEffect Aura(GameLiving living) => living.effectListComponent.GetSpellEffects(eEffect.MaulerStance)
            .FirstOrDefault(x => x.IsActive && !x.IsEnding);
        public static bool Farseer(GameLiving living) => Aura(living)?.SpellHandler.Spell.ID == 67001;
        public static bool HasUtility(GameLiving living, int code) => living.effectListComponent.GetSpellEffects(eEffect.MaulerUtility)
            .Any(x => x.IsActive && !x.IsEnding && (int)x.SpellHandler.Spell.Value == code);
        public static bool FreeCosts(GameLiving living) => IsPlayer(living) && HasUtility(living, 1);
        public static bool PierceBladeturn(GameLiving living) => IsPlayer(living) && HasUtility(living, 2);
        public static bool MeetsStaffRequirement(int required, int trained, bool equipped) => required < 0 || equipped && trained >= required;
        // A gift needs an aura and, for most ranks, a trained and equipped Mauler Staff. Bots check this before choosing
        // it: a fist-wrap Mauler that kept choosing its 1,500-range gift stood out of reach of its target, refused.
        public static bool GiftReady(GameLiving caster, Spell spell) =>
            IsPlayer(caster) && Aura(caster) != null &&
            MeetsStaffRequirement(Param(spell, "MaulerStaffRequired"), caster.GetBaseSpecLevel(Specs.Mauler_Staff),
                caster.ActiveWeapon?.Object_Type == (int)eObjectType.MaulerStaff);
        // Test coefficient: a lost percentage of maximum health supplies the same percentage of maximum power.
        // Only actual hostile health loss qualifies; absorbed damage and self/environmental damage do not.
        public static int PowerFromDamage(int damage, int maxHealth, int maxPower) => maxHealth <= 0 ? 0 :
            (int)Math.Min(maxPower, Math.Max(0L, (long)damage) * maxPower / maxHealth);
        public static void ReceivedDamage(GameLiving victim, GameObject source, int actualLoss)
        {
            if (IsPlayer(victim) && victim.IsAlive && source is GameLiving attacker && attacker != victim &&
                GameServer.ServerRules.IsAllowedToAttack(attacker, victim, true))
            {
                double amount = victim.TempProperties.GetProperty<double>("Mauler.PowerRemainder") +
                    Math.Max(0, actualLoss) * (double)victim.MaxMana / Math.Max(1, victim.MaxHealth);
                victim.ChangeMana(source, eManaChangeType.Spell, (int)amount);
                victim.TempProperties.SetProperty("Mauler.PowerRemainder", amount - Math.Floor(amount));
            }
        }
        // Tooltip text. The client delve shows only a handler's ShortDescription, so every Mauler handler builds one
        // from the spell's own values instead of the placeholder database description.
        public static string For(Spell spell) => spell.Duration > 0 ? $" for {spell.Duration / 1000} seconds" : "";
        public static bool Placeholder(Spell spell) => string.IsNullOrEmpty(spell.Description) || spell.Description == "Modern Mauler test kit.";
        public static string StatText(Spell spell) => ModernMauler.Param(spell, "MaulerStat") switch
        {
            10 => $"Increases your weapon skill by {spell.Value}%{For(spell)}.",
            11 => $"Increases your chance to evade by {spell.Value}%{For(spell)}.",
            12 => $"Increases your chance to parry by {spell.Value}%{For(spell)}.",
            13 => $"Increases your melee damage by {spell.Value}%{For(spell)}.",
            14 => $"The target has a {spell.Value}% chance to fumble melee attacks{For(spell)}.",
            15 => $"Slows the casting speed of enemies within {spell.Radius} by {spell.Value}%{For(spell)}.",
            _ => spell.Description
        };
        public static string UtilityText(Spell spell) => (int)spell.Value switch
        {
            1 => $"Your spells and styles cost no power or endurance{For(spell)}.",
            2 => $"Your attacks pierce bladeturn{For(spell)}.",
            3 => "Strips all ablative shields from the target.",
            4 => $"Absorbs {spell.Damage}% of the damage the target takes from enemies{For(spell)}; the absorbed damage becomes power for you.",
            6 => $"Drains {spell.Damage}% of the target's maximum power and gives it to you.",
            8 => $"Increases your spell damage by {spell.Damage}%{For(spell)}.",
            9 => $"Increases your movement speed by 50%{For(spell)}.",
            _ => spell.Description
        };
        public static string ChildText(GameLiving caster, int id, string aura)
        {
            Spell child = SkillBase.GetSpellByID(id);
            if (child == null) return null;
            string text = ScriptMgr.CreateSpellHandler(caster, child, null)?.ShortDescription;
            return string.IsNullOrEmpty(text) ? null : $"{aura}: {text}";
        }

        public static int BoundedTap(int requested, int available) => Math.Min(Math.Max(0, requested), Math.Max(0, available));
        public static void Protect(GameLiving victim, GameObject source, eDamageType type, ref int damage, ref int critical)
        {
            if (source is not GameLiving attacker || attacker == victim || !GameServer.ServerRules.IsAllowedToAttack(attacker, victim, true)) return;
            var protection = victim.effectListComponent.GetSpellEffects(eEffect.MaulerUtility)
                .Where(x => x.IsActive && !x.IsEnding && x.SpellHandler.Spell.Value is 4 or 7)
                .Where(x => x.SpellHandler.Spell.Value == 4 || type is >= eDamageType.Body and <= eDamageType.Spirit)
                .OrderByDescending(x => x.SpellHandler.Spell.Damage).FirstOrDefault();
            if (protection == null || !protection.SpellHandler.Caster.IsAlive) return;
            int percent = (int)protection.SpellHandler.Spell.Damage;
            int old = Math.Max(0, damage) + Math.Max(0, critical);
            damage = Math.Max(0, damage) * (100 - percent) / 100;
            critical = Math.Max(0, critical) * (100 - percent) / 100;
            if (protection.SpellHandler.Spell.Value == 4 && protection.SpellHandler.Caster is { IsAlive: true } owner)
                owner.ChangeMana(source, eManaChangeType.Spell, PowerFromDamage(old - damage - critical, victim.MaxHealth, owner.MaxMana));
        }
    }

    [SpellHandler(eSpellType.MaulerStance)]
    public sealed class MaulerStanceHandler : SpellHandler
    {
        public MaulerStanceHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => Spell.Description;
        public override int PowerCost(GameLiving target) => 0;
        public override bool CheckBeginCast(GameLiving target, bool quiet) => ModernMauler.IsPlayer(Caster) && base.CheckBeginCast(target, quiet);
        public override void OnDirectEffect(GameLiving target) => ECSGameEffectFactory.Create(new(Caster, 0, 1, this), static (in i) => new MaulerStanceEffect(i));
    }
    public sealed class MaulerStanceEffect : ECSGameSpellEffect
    {
        // The aura is held until another aura replaces it; with no duration it would expire on the next tick.
        public MaulerStanceEffect(in ECSGameEffectInitParams p) : base(p)
        {
            EffectType = eEffect.MaulerStance;
            Duration = 0;
            ExpireTick = long.MaxValue;
        }
        public override bool IsBetterThan(ECSGameEffect other) => true;
        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    [SpellHandler(eSpellType.MaulerGift)]
    public sealed class MaulerGiftHandler : SpellHandler
    {
        private bool _farseer;
        public MaulerGiftHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => string.Join("\n\n", new[]
        {
            Spell.Description,
            ModernMauler.ChildText(Caster, Spell.SubSpellID, "Aura of the Wildbull"),
            ModernMauler.ChildText(Caster, ModernMauler.Param(Spell, "MaulerFarseerSpell"), "Aura of the Farseer")
        }.Where(x => !string.IsNullOrEmpty(x)));
        private bool Requirements() => ModernMauler.GiftReady(Caster, Spell);
        public override bool CheckBeginCast(GameLiving target, bool quiet)
        {
            if (!Requirements())
            {
                if (!quiet) MessageToCaster("Choose a Mauler aura and equip/train the required Mauler Staff for this gift.", eChatType.CT_System);
                return false;
            }
            _farseer = ModernMauler.Farseer(Caster);
            return base.CheckBeginCast(target, quiet);
        }
        public override bool CheckEndCast(GameLiving target) => Requirements() && _farseer == ModernMauler.Farseer(Caster) && base.CheckEndCast(target);
        public override void FinishSpellCast(GameLiving target)
        {
            Caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }
        public override void CastSubSpells(GameLiving target) { }
        public override void OnDirectEffect(GameLiving target)
        {
            int id = _farseer ? ModernMauler.Param(Spell, "MaulerFarseerSpell") : Spell.SubSpellID;
            var child = SkillBase.GetSpellByID(id);
            if (child != null) ScriptMgr.CreateSpellHandler(Caster, child, SpellLine).StartSpell(target);
        }
    }

    [SpellHandler(eSpellType.MaulerControl)]
    public sealed class MaulerControlHandler : SpellHandler
    {
        public MaulerControlHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => Spell.Value == 1
            ? $"Silences the target{ModernMauler.For(Spell)}: it cannot cast spells."
            : $"Disarms the target{ModernMauler.For(Spell)}: it cannot attack.";
        public override void FinishSpellCast(GameLiving target) { Caster.Mana -= PowerCost(target); base.FinishSpellCast(target); }
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams p) => ECSGameEffectFactory.Create(p, static (in i) => new MaulerControlEffect(i));
    }
    public sealed class MaulerControlEffect : ECSGameSpellEffect
    {
        private long _until;
        private bool Silence => SpellHandler.Spell.Value == 1;
        public MaulerControlEffect(in ECSGameEffectInitParams p) : base(p) { EffectType = eEffect.MaulerControl; }
        public override void OnStartEffect()
        {
            _until = Owner.CurrentRegion.Time + Duration;
            if (Silence) { Owner.SilencedTime = Math.Max(Owner.SilencedTime, _until); Owner.StopCurrentSpellcast(); }
            else { Owner.DisarmedTime = Math.Max(Owner.DisarmedTime, _until); Owner.attackComponent.StopAttack(); }
        }
        public override void OnStopEffect()
        {
            if (Silence && Owner.SilencedTime == _until) Owner.SilencedTime = 0;
            if (!Silence && Owner.DisarmedTime == _until) Owner.DisarmedTime = 0;
        }
    }

    [SpellHandler(eSpellType.MaulerUtility)]
    public sealed class MaulerUtilityHandler : SpellHandler
    {
        public MaulerUtilityHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => ModernMauler.Placeholder(Spell) ? ModernMauler.UtilityText(Spell) : Spell.Description;
        public override void FinishSpellCast(GameLiving target) { Caster.Mana -= PowerCost(target); base.FinishSpellCast(target); }
        public override void OnDirectEffect(GameLiving target)
        {
            if (Spell.Value == 3)
                foreach (var effect in target.effectListComponent.GetSpellEffects(eEffect.AblativeArmor).ToArray()) effect.End();
            else if (Spell.Value == 6)
            {
                int amount = ModernMauler.BoundedTap(target.MaxMana * (int)Spell.Damage / 100, target.Mana);
                int removed = -target.ChangeMana(Caster, eManaChangeType.Spell, -amount);
                Caster.ChangeMana(Caster, eManaChangeType.Spell, removed);
            }
            else if (Spell.Value == 7)
            {
                // Convergence uses a self-only parent; apply the protection to nearby group members.
                var members = Caster.Group?.GetMembersInTheGroup() ?? new System.Collections.Generic.List<GameLiving> { Caster };
                foreach (var member in members.Where(x => x.IsAlive && Caster.IsWithinRadius(x, 2000)))
                {
                    int offered = -member.ChangeMana(Caster, eManaChangeType.Spell, -member.Mana / 2);
                    if (member != Caster) Caster.ChangeMana(Caster, eManaChangeType.Spell, offered);
                    ECSGameEffectFactory.Create(new(member, 30000, 1, this), static (in i) => new MaulerUtilityEffect(i, true));
                }
                foreach (var enemy in Caster.GetPlayersInRadius(500).Cast<GameLiving>().Concat(Caster.GetNPCsInRadius(500).Cast<GameLiving>()))
                    if (enemy.IsAlive && GameServer.ServerRules.IsAllowedToAttack(Caster, enemy, true))
                        Caster.ChangeMana(Caster, eManaChangeType.Spell, -enemy.ChangeMana(Caster, eManaChangeType.Spell,
                            -ModernMauler.BoundedTap(Caster.MaxMana - Caster.Mana, enemy.Mana)));
            }
        }
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams p) => ECSGameEffectFactory.Create(p, static (in i) => new MaulerUtilityEffect(i, false));
    }
    public sealed class MaulerUtilityEffect : ECSGameSpellEffect
    {
        public MaulerUtilityEffect(in ECSGameEffectInitParams p, bool convergence) : base(p) { EffectType = eEffect.MaulerUtility; }
        public override void OnStartEffect()
        {
            if (SpellHandler.Spell.Value == 8) Owner.AbilityBonus[eProperty.SpellDamage] += (int)SpellHandler.Spell.Damage;
            if (SpellHandler.Spell.Value == 9)
            {
                Owner.BuffBonusMultCategory1.Set((int)eProperty.MaxSpeed, this, 1.5);
                Owner.OnMaxSpeedChange();
            }
        }
        public override void OnStopEffect()
        {
            if (SpellHandler.Spell.Value == 8) Owner.AbilityBonus[eProperty.SpellDamage] -= (int)SpellHandler.Spell.Damage;
            if (SpellHandler.Spell.Value == 9)
            {
                Owner.BuffBonusMultCategory1.Remove((int)eProperty.MaxSpeed, this);
                Owner.OnMaxSpeedChange();
            }
        }
        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    [SpellHandler(eSpellType.MaulerEnduranceTap)]
    public sealed class MaulerEnduranceTapHandler : SpellHandler
    {
        public MaulerEnduranceTapHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => $"Steals up to {Spell.Damage} endurance from the target.";
        public override void FinishSpellCast(GameLiving target) { Caster.Mana -= PowerCost(target); base.FinishSpellCast(target); }
        public override void OnDirectEffect(GameLiving target)
        {
            int stolen = -target.ChangeEndurance(Caster, eEnduranceChangeType.Spell, -ModernMauler.BoundedTap((int)Spell.Damage, target.Endurance));
            Caster.ChangeEndurance(Caster, eEnduranceChangeType.Spell, stolen);
        }
    }

    [SpellHandler(eSpellType.MaulerStat)]
    public sealed class MaulerStatHandler : SpellHandler
    {
        public MaulerStatHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => ModernMauler.StatText(Spell);
        public override void FinishSpellCast(GameLiving target) { Caster.Mana -= PowerCost(target); base.FinishSpellCast(target); }
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams p) => ECSGameEffectFactory.Create(p, static (in i) => new MaulerStatEffect(i));
    }
    public sealed class MaulerStatEffect : ECSGameSpellEffect
    {
        private int Kind => ModernMauler.Param(SpellHandler.Spell, "MaulerStat");
        public MaulerStatEffect(in ECSGameEffectInitParams p) : base(p) { EffectType = eEffect.MaulerStat; }
        public static eProperty Property(int kind) => kind switch
        {
            10 => eProperty.WeaponSkill, 11 => eProperty.EvadeChance, 12 => eProperty.ParryChance,
            13 => eProperty.MeleeDamage, 14 => eProperty.FumbleChance, 15 => eProperty.CastingSpeed,
            _ => eProperty.Undefined
        };
        private void Apply(int sign)
        {
            eProperty property = Property(Kind);
            if (property == eProperty.Undefined) return;
            int amount = sign * (int)SpellHandler.Spell.Value;
            if (Kind >= 14) Owner.DebuffCategory[property] += amount;
            else Owner.BaseBuffBonusCategory[property] += amount;
        }
        public override void OnStartEffect() => Apply(1);
        public override void OnStopEffect() => Apply(-1);
    }
}
