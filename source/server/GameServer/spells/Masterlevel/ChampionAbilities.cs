using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Offline Champion Level abilities: one path per realm, CL1-15, trained automatically. Spell IDs are
    /// 63100 + realm * 15 + CL - 1 (Albion, Midgard, Hibernia) and run through the Master Level framework.
    /// Passives are permanent effects holding their bonuses (ability category, so buff caps don't eat
    /// them); the realms share passive strength and differ in their active abilities.
    /// </summary>
    public static class ChampionAbilities
    {
        public const int FirstId = 63100;
        public static readonly eRealm[] Realms = { eRealm.Albion, eRealm.Midgard, eRealm.Hibernia };

        public static int IdFor(eRealm realm, int championLevel) =>
            FirstId + Array.IndexOf(Realms, realm) * 15 + championLevel - 1;

        private static readonly eProperty[] Stats =
        {
            eProperty.Strength, eProperty.Constitution, eProperty.Dexterity, eProperty.Quickness,
            eProperty.Intelligence, eProperty.Piety, eProperty.Empathy, eProperty.Charisma
        };

        private static MLMod Ability(eProperty property, int value) => new(property, MLCategory.Ability, value);

        // Shared passives (CL1, 3, 5, 7, 9, 11, 13).
        private static readonly MLMod[] StatsPassive = Stats.Select(s => Ability(s, 15)).ToArray();
        private static readonly MLMod[] ResistPassive = MLMod.AllResists.Select(r => Ability(r, 5)).ToArray();
        private static readonly MLMod[] RegenPassive =
            { Ability(eProperty.PowerRegenerationAmount, 4), Ability(eProperty.EnduranceRegenerationAmount, 4), Ability(eProperty.HealthRegenerationAmount, 10) };
        private static readonly MLMod[] DamagePassive = { Ability(eProperty.MeleeDamage, 5), Ability(eProperty.SpellDamage, 5) };
        private static readonly MLMod[] CritPassive =
            { Ability(eProperty.CriticalMeleeHitChance, 5), Ability(eProperty.CriticalSpellHitChance, 5), Ability(eProperty.CriticalArcheryHitChance, 5) };
        private static readonly MLMod[] HealthPassive = { Ability(eProperty.Of_Toughness, 10) };
        private static readonly MLMod[] HealingPassive = { Ability(eProperty.HealingEffectiveness, 10) };

        private static readonly eEffect[] CrowdControl =
            { eEffect.Stun, eEffect.Mez, eEffect.Snare, eEffect.MovementSpeedDebuff, eEffect.Confusion, eEffect.Nearsight };
        // Check the live effect instead of duration reduction: style stuns ignore reduction,
        // and even 100% reduction leaves a nonzero control duration.
        public static bool IsControlImmune(GameLiving target, Spell spell) =>
            CrowdControl.Contains(EffectHelper.GetEffectFromSpell(spell)) &&
            target.effectListComponent.GetSpellEffects(eEffect.MasterLevel).Any(effect =>
                !effect.IsEnding && !effect.IsDisabled && effect.ExpireTick > GameLoop.GameLoopTime &&
                effect.SpellHandler is MasterLevelAbilityHandler { Ability.BreaksControl: true });

        private static int Sec(Spell s) => s.Duration / 1000;

        public static IEnumerable<(int Id, MLAbility Ability)> Build()
        {
            foreach (eRealm realm in Realms)
            {
                string path = ChampionRules.PathFor(realm);
                for (int level = 1; level <= 15; level++)
                {
                    MLAbility ability = Make(realm, path, level);
                    if (ability != null)
                        yield return (IdFor(realm, level), ability);
                }
            }
        }

        private static MLAbility Passive(string path, int level, MLMod[] mods, string text) =>
            new() { Path = path, Level = level, Passive = true, Mods = mods, Describe = _ => "Passive: " + text };

        private static MLAbility Make(eRealm realm, string path, int level)
        {
            switch (level)
            {
                case 1: return Passive(path, 1, StatsPassive, "+15 to all stats.");
                case 3: return Passive(path, 3, ResistPassive, "+5% to all resists.");
                case 5: return Passive(path, 5, RegenPassive, "faster health, power and endurance regeneration.");
                case 7: return Passive(path, 7, DamagePassive, "+5% melee and spell damage.");
                case 9: return Passive(path, 9, CritPassive, "+5% melee, spell and archery critical chance.");
                case 11: return Passive(path, 11, HealthPassive, "+10% maximum health.");
                case 13: return Passive(path, 13, HealingPassive, "+10% healing.");
            }
            return realm switch
            {
                eRealm.Albion => Albion(path, level),
                eRealm.Midgard => Midgard(path, level),
                _ => Hibernia(path, level)
            };
        }

        // ---------------- shared building blocks ----------------

        private static void BreakFree(MasterLevelAbilityHandler h)
        {
            int removed = MasterLevelAbilityHandler.Cure(h.Caster, CrowdControl);
            h.Hold(h.Caster);
            h.Animate(h.Caster);
            h.MessageToCasterPublic(removed > 0 ? "You break free!" : "You steel yourself against crowd control.");
        }

        private static void GroupHold(MasterLevelAbilityHandler h)
        {
            var members = h.Group(h.Spell.Radius).ToList();
            foreach (GameLiving member in members)
            {
                h.Hold(member);
                h.Animate(member);
            }
            h.Report(members.Count, "group members");
        }

        private static void Burst(MasterLevelAbilityHandler h, eSpellType control, Action<DbSpell> setup, eDamageType damageType)
        {
            var enemies = h.Enemies(h.Caster, h.Spell.Radius).ToList();
            foreach (GameLiving enemy in enemies)
            {
                if (h.Spell.Damage > 0)
                    h.Damage(enemy, h.Spell.Damage, damageType);
                h.Cast(enemy, 1, control, setup);
            }
            h.Report(enemies.Count, "enemies");
        }

        private static void GroupHeal(MasterLevelAbilityHandler h, Action<GameLiving> extra)
        {
            var members = h.Group(h.Spell.Radius).ToList();
            foreach (GameLiving member in members)
            {
                h.Heal(member, member.MaxHealth * (int)h.Spell.Value / 100);
                extra?.Invoke(member);
            }
            h.Report(members.Count, "group members");
        }

        private static MasterLevelFieldOptions Tempest(string name, ushort effect, eDamageType type) => new()
        {
            Name = name, FollowOwner = true, Hidden = true, Interval = 2000, PulseEffect = effect, SuppressEffect = true,
            OnPulse = (f, enemy) => f.Ability.Damage(enemy, f.Ability.Spell.Damage, type)
        };

        // ---------------- Albion: the Round Table (holy, protection) ----------------
        private static MLAbility Albion(string path, int level) => level switch
        {
            2 => new MLAbility
            {
                Path = path, Level = 2, Positive = true,
                Describe = s => $"Lay on Hands: heal yourself or an ally for {s.Value}% of their health.",
                Run = (h, t) => h.Heal(t, t.MaxHealth * (int)h.Spell.Value / 100)
            },
            4 => new MLAbility
            {
                Path = path, Level = 4,
                Describe = s => $"Smite: {s.Damage} spirit damage to an enemy up to {s.Range} away.",
                Run = (h, t) => h.Damage(t, h.Spell.Damage, eDamageType.Spirit)
            },
            6 => new MLAbility
            {
                Path = path, Level = 6, Positive = true, BreaksControl = true,
                Describe = s => $"Purify: usable while stunned or mesmerized. Breaks crowd control and makes you immune to it for {Sec(s)} s.",
                Run = (h, _) => BreakFree(h)
            },
            8 => new MLAbility
            {
                Path = path, Level = 8, Positive = true,
                Mods = MLMod.Resists(MLCategory.Buff, 10, physical: true).Append(MLMod.Buff(eProperty.ArmorAbsorption, 10)).ToArray(),
                Describe = s => $"Banner of Camelot: your group within {s.Radius} gains 10% absorption and 10% to all resists for {Sec(s) / 60} min.",
                Run = (h, _) => GroupHold(h)
            },
            10 => new MLAbility
            {
                Path = path, Level = 10,
                Describe = s => $"Judgement: stuns every enemy within {s.Radius} for 4 s and deals {s.Damage} spirit damage.",
                Run = (h, _) => Burst(h, eSpellType.Stun, db => { db.Duration = 4; db.ClientEffect = 0; }, eDamageType.Spirit)
            },
            12 => new MLAbility
            {
                Path = path, Level = 12, Positive = true,
                Describe = s => $"Holy Aegis: absorbs all damage you take, up to {s.Value}, for {Sec(s)} s.",
                Run = (h, _) => h.Cast(h.Caster, 1, eSpellType.BothAblativeArmor, db => { db.Target = "Self"; db.Value = h.Spell.Value; db.Damage = 100; db.Duration = Sec(h.Spell); })
            },
            14 => new MLAbility
            {
                Path = path, Level = 14, Positive = true,
                Describe = s => $"Grace of Avalon: heals your group within {s.Radius} for {s.Value}% and cures damage over time, disease, snares and debuffs.",
                Run = (h, _) => GroupHeal(h, member => MasterLevelAbilityHandler.Cure(member, MasterLevelAbilityHandler.Harmful))
            },
            _ => new MLAbility
            {
                Path = path, Level = 15, Positive = true,
                Mods = new[] { MLMod.Buff(eProperty.MeleeDamage, 25), MLMod.Buff(eProperty.SpellDamage, 25) },
                Describe = s => $"Excalibur: strike an enemy for {s.Damage} spirit damage; your group within 1500 deals 25% more damage for {Sec(s)} s.",
                Run = (h, t) =>
                {
                    h.Damage(t, h.Spell.Damage, eDamageType.Spirit);
                    foreach (GameLiving member in h.Group(1500))
                        h.Hold(member);
                }
            }
        };

        // ---------------- Midgard: the Einherjar (frost, fury) ----------------
        private static MLAbility Midgard(string path, int level) => level switch
        {
            2 => new MLAbility
            {
                Path = path, Level = 2, Positive = true,
                Describe = s => $"Valhalla's Call: heal yourself for {s.Value}% of your health and restore 20% endurance.",
                Run = (h, _) =>
                {
                    h.Heal(h.Caster, h.Caster.MaxHealth * (int)h.Spell.Value / 100);
                    MasterLevelAbilityHandler.Restore(h.Caster, h.Caster, 0, 20, h.Spell.Name);
                }
            },
            4 => new MLAbility
            {
                Path = path, Level = 4,
                Describe = s => $"Frostbite Hurl: {s.Damage} cold damage to an enemy up to {s.Range} away, snaring it by 40% for 8 s.",
                Run = (h, t) =>
                {
                    h.Damage(t, h.Spell.Damage, eDamageType.Cold);
                    h.Cast(t, 1, eSpellType.SpeedDecrease, db => { db.Value = 40; db.Duration = 8; db.ClientEffect = 0; });
                }
            },
            6 => new MLAbility
            {
                Path = path, Level = 6, Positive = true, BreaksControl = true,
                Describe = s => $"Berserker's Break: usable while stunned or mesmerized. Breaks crowd control and makes you immune to it for {Sec(s)} s.",
                Run = (h, _) => BreakFree(h)
            },
            8 => new MLAbility
            {
                Path = path, Level = 8, Positive = true,
                Mods = new[] { MLMod.Buff(eProperty.MeleeDamage, 15), MLMod.Buff(eProperty.SpellDamage, 15) },
                Describe = s => $"Warhorn of Heimdall: your group within {s.Radius} deals 15% more melee and spell damage for {Sec(s)} s.",
                Run = (h, _) => GroupHold(h)
            },
            10 => new MLAbility
            {
                Path = path, Level = 10,
                Describe = s => $"Fimbulwinter: freezes every enemy within {s.Radius} in place for 6 s and deals {s.Damage} cold damage.",
                Run = (h, _) => Burst(h, eSpellType.SpeedDecrease, db => { db.Value = 99; db.Duration = 6; db.ClientEffect = 0; }, eDamageType.Cold)
            },
            12 => new MLAbility
            {
                Path = path, Level = 12, Positive = true,
                Describe = s => $"Unyielding: you take half damage from every source for {Sec(s)} s.",
                Run = (h, _) => h.Cast(h.Caster, 1, eSpellType.BothAblativeArmor, db => { db.Target = "Self"; db.Value = h.Spell.Value; db.Damage = 50; db.Duration = Sec(h.Spell); })
            },
            14 => new MLAbility
            {
                Path = path, Level = 14, Positive = true,
                Describe = s => $"Mead Hall: heals your group within {s.Radius} for {s.Value}% and restores 20% power and endurance.",
                Run = (h, _) => GroupHeal(h, member => MasterLevelAbilityHandler.Restore(h.Caster, member, 20, 20, h.Spell.Name))
            },
            _ => new MLAbility
            {
                Path = path, Level = 15,
                Describe = s => $"Ragnarok: for {Sec(s)} s a storm of frost and lightning around you hits every enemy within {s.Radius} for {s.Damage} cold damage every 2 s.",
                Run = (h, _) => h.Field(new Point3D(h.Caster.X, h.Caster.Y, h.Caster.Z), Tempest("Ragnarok", 3528, eDamageType.Cold))
            }
        };

        // ---------------- Hibernia: the Tuatha Dé (nature, glamour) ----------------
        private static MLAbility Hibernia(string path, int level) => level switch
        {
            2 => new MLAbility
            {
                Path = path, Level = 2, Positive = true,
                Describe = s => $"Healing Spring: heal yourself or an ally for {s.Value}%, then 100 more every 3 s for 15 s.",
                Run = (h, t) =>
                {
                    h.Heal(t, t.MaxHealth * (int)h.Spell.Value / 100);
                    h.Cast(t, 1, eSpellType.HealOverTime, db => { db.Target = "Realm"; db.Value = 100; db.Frequency = 30; db.Duration = 15; });
                }
            },
            4 => new MLAbility
            {
                Path = path, Level = 4, Mods = MLMod.Resists(MLCategory.Debuff, 10, physical: true),
                Describe = s => $"Spear of Lugh: {s.Damage} energy damage to an enemy up to {s.Range} away; it loses 10% of all resists for {Sec(s)} s.",
                Run = (h, t) =>
                {
                    h.Damage(t, h.Spell.Damage, eDamageType.Energy);
                    h.Hold(t);
                }
            },
            6 => new MLAbility
            {
                Path = path, Level = 6, Positive = true, BreaksControl = true,
                Describe = s => $"Glamour Shift: usable while stunned or mesmerized. Breaks crowd control, makes you immune to it for {Sec(s)} s and hides you in stealth.",
                Run = (h, _) =>
                {
                    BreakFree(h);
                    if (h.Caster is GamePlayer player && !player.InCombat)
                        player.Stealth(true);
                }
            },
            8 => new MLAbility
            {
                Path = path, Level = 8, Positive = true, Mods = new[] { MLMod.Speed(1.25), MLMod.Buff(eProperty.MissHit, 10) },
                Describe = s => $"Song of the Sidhe: your group within {s.Radius} moves 25% faster, even in combat, and is 10% harder to hit for {Sec(s)} s.",
                Run = (h, _) => GroupHold(h)
            },
            10 => new MLAbility
            {
                Path = path, Level = 10,
                Describe = s => $"Glamour Mist: mesmerizes every enemy within {s.Radius} for 8 s.",
                Run = (h, _) => Burst(h, eSpellType.Mesmerize, db => { db.Duration = 8; db.ClientEffect = 0; }, eDamageType.Spirit)
            },
            12 => new MLAbility
            {
                Path = path, Level = 12, Positive = true, Mods = new[] { MLMod.Buff(eProperty.MissHit, 50) },
                Describe = s => $"Shadowform: attacks are 50% more likely to miss you for {Sec(s)} s.",
                Run = (h, _) => { h.Hold(h.Caster); h.Animate(h.Caster); }
            },
            14 => new MLAbility
            {
                Path = path, Level = 14, Positive = true,
                Describe = s => $"Rebirth Grove: heals your group within {s.Radius} for {s.Value}%, then 150 more every 3 s for 15 s.",
                Run = (h, _) => GroupHeal(h, member =>
                    h.Cast(member, 1, eSpellType.HealOverTime, db => { db.Target = "Realm"; db.Value = 150; db.Frequency = 30; db.Duration = 15; }))
            },
            _ => new MLAbility
            {
                Path = path, Level = 15, Positive = true, Mods = new[] { MLMod.Speed(1.2) },
                Describe = s => $"Wings of the Morrigan: for {Sec(s)} s her crows hit every enemy within {s.Radius} for {s.Damage} spirit damage every 2 s, and your group within 1500 moves 20% faster.",
                Run = (h, _) =>
                {
                    h.Field(new Point3D(h.Caster.X, h.Caster.Y, h.Caster.Z), Tempest("Wings of the Morrigan", 2576, eDamageType.Spirit));
                    foreach (GameLiving member in h.Group(1500))
                        h.Hold(member);
                }
            }
        };
    }
}
