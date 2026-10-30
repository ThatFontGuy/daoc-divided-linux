using System;
using System.Collections.Generic;
using System.Linq;
using DOL.AI.Brain;
using DOL.Database;
using DOL.Events;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    public enum DeathKnightForm { None = 0, Decrepit = 1, Chthonic = 2, Spirit = 3, Darkness = 4 }

    /// <summary>
    /// Shared rules for the Death Knight (class 66), the live 1.122B+ Necromancer. Values follow the 1.122B redesign
    /// with the 1.122C-1.129B tuning; see docs/DEATH-KNIGHT-MODERN-TEST.md.
    /// </summary>
    public static class DeathKnight
    {
        public const string WeaponPrefix = "deathknight_";
        public const string Nethersbane = "deathknight_nethersbane";

        public static bool Is(GameLiving living) => living switch
        {
            GamePlayer player => player.CharacterClass?.ID == (int)eCharacterClass.DeathKnight,
            IGamePlayer bot => bot.CharacterClass?.ID == (int)eCharacterClass.DeathKnight,
            _ => false
        };

        public static DeathKnightFormEffect FormEffect(GameLiving living) => living?.effectListComponent
            .GetSpellEffects(eEffect.DeathKnightForm).OfType<DeathKnightFormEffect>().FirstOrDefault(e => !e.IsEnding);

        public static DeathKnightForm Form(GameLiving living) => FormEffect(living)?.Form ?? DeathKnightForm.None;

        /// <summary>Darkness (the RR5 Call of Darkness, "Demon Lord") counts as Chthonic and Decrepit Form (live delve).</summary>
        public static bool InForm(GameLiving living, DeathKnightForm form)
        {
            DeathKnightForm current = Form(living);
            return current == form || current == DeathKnightForm.Darkness && form is DeathKnightForm.Decrepit or DeathKnightForm.Chthonic;
        }

        /// <summary>Painworking melee: weaponskill and damage come from Intelligence and the Painworking spec.</summary>
        public static int WeaponStat(GameLiving living) => living.GetModified(eProperty.Intelligence);
        public static int PainworkingSpec(GameLiving living) => living.GetModifiedSpecLevel(Specs.Painworking);
        public static bool IsConjured(DbInventoryItem item) => item?.Id_nb?.StartsWith(WeaponPrefix, StringComparison.Ordinal) == true;

        /// <summary>Chthonic bonuses scale with Painworking: half strength untrained, full strength at Painworking = level.</summary>
        public static double PainworkingScale(GameLiving living) =>
            0.5 + 0.5 * Math.Clamp(PainworkingSpec(living) / (double)Math.Max(1, (int)living.Level), 0, 1);

        /// <summary>
        /// Form appearance: the models of live's shapechange spells (Decrepit 6272, Chthonic 5683, Spirit 6441 and Demon
        /// 6573 in the live spell data). With the newer models the client draws the Flesh Wight as the DR greater
        /// necroservant, the demon knight as the DR abomination and the Ash Demon as the DR demon.
        /// </summary>
        public static ushort FormModel(GameLiving living, DeathKnightForm form) => form switch
        {
            DeathKnightForm.Decrepit => 23,
            DeathKnightForm.Chthonic => 653,
            DeathKnightForm.Spirit => 1670,
            DeathKnightForm.Darkness => 635,
            _ => living.Model
        };

        /// <summary>
        /// Servants change appearance, name and abilities while their master is in Spirit Form (live). Each servant's
        /// spirit look is a second NPC template at this offset: its model and name replace the servant's, and its spells
        /// are added to the servant's own (the spirit aegis proc, Rabid Sickness, the phantom's plague, the AoE mez).
        /// </summary>
        public const int SpiritTemplateOffset = 10;

        public static INpcTemplate SpiritTemplate(GameNPC servant) =>
            servant?.NPCTemplate == null ? null : NpcTemplateMgr.GetTemplate(servant.NPCTemplate.TemplateId + SpiritTemplateOffset);

        public static bool IsPowerLocked(GameLiving living) =>
            living?.effectListComponent.GetSpellEffects(eEffect.DeathKnightPowerLock).Any(e => !e.IsEnding) == true;

        /// <summary>1.123B Chthonic armor: 125 AF at 50, 75 at 45-49, 50 at 35-44, 25 at 20-34.</summary>
        public static int ChthonicArmor(int level) => level >= 50 ? 125 : level >= 45 ? 75 : level >= 35 ? 50 : level >= 20 ? 25 : 0;

        /// <summary>Spells tagged DkNoChthonic (pets, PBAoE, bolts) cannot be cast in Chthonic Form (1.122B/1.123).</summary>
        public static bool BlockedByForm(GameLiving caster, Spell spell)
        {
            if (!Is(caster) || Form(caster) != DeathKnightForm.Chthonic)
                return false;
            spell.TryGetParamSingle("DkNoChthonic", out int blocked);
            return blocked > 0;
        }

        /// <summary>Ignore line: chance for an ally to shrug off a debuff.</summary>
        public static int IgnoreChance(GameLiving target) => target?.effectListComponent.GetSpellEffects(eEffect.DeathKnightIgnore)
            .Where(e => !e.IsEnding).Select(e => (int)e.SpellHandler.Spell.Value).DefaultIfEmpty(0).Max() ?? 0;

        public static bool IsDebuff(ISpellHandler handler) => handler is PropertyChangingSpell && !handler.HasPositiveEffect;

        public static void EndForms(GameLiving living)
        {
            foreach (ECSGameSpellEffect effect in living.effectListComponent.GetSpellEffects(eEffect.DeathKnightForm).ToList())
                effect.End();
        }

        public static void ReleasePet(GameLiving living)
        {
            if (living is GamePlayer player && player.ControlledBrain != null)
                player.CommandNpcRelease();
        }
    }

    /// <summary>Decrepit, Chthonic and Spirit Form (Value 1-3) and the RR5 Darkness (4). Maintained until changed.</summary>
    [SpellHandler(eSpellType.DeathKnightForm)]
    public class DeathKnightFormHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public DeathKnightForm Form => (DeathKnightForm)(int)Spell.Value;

        public override string ShortDescription => Form switch
        {
            DeathKnightForm.Decrepit => "Become a Decrepit Magus: 10% more magic damage, health regeneration even in combat, and melee attackers have a 50% chance to be diseased.",
            DeathKnightForm.Chthonic => "Become a Chthonic Knight: up to 30% more health, 20 absorption, the ability to parry (+30%), +20 Painworking, spec armor by level and 10% secondary magic resistance. Your servant is dismissed and none can be summoned.",
            DeathKnightForm.Spirit => "Become a Ghostly Spirit: 10% of damage taken becomes power, greatly increased power regeneration, you see hidden enemies more easily, and your servant gains 55% resistances and its spirit abilities.",
            _ => $"Become a Demon Lord: the benefits of Chthonic and Decrepit Form, increased by 10%, for {Spell.Duration / 1000} seconds."
        };

        public override bool CheckBeginCast(GameLiving selectedTarget, bool quiet)
        {
            // 1.124B: no switching out of Darkness except Revert Form, cancelling it, or waiting.
            if (DeathKnight.Form(Caster) == DeathKnightForm.Darkness && Form != DeathKnightForm.Darkness)
            {
                if (!quiet) MessageToCaster("You must revert from Darkness before taking another form.", eChatType.CT_System);
                return false;
            }
            return base.CheckBeginCast(selectedTarget, quiet);
        }

        public override void FinishSpellCast(GameLiving target)
        {
            Caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            DeathKnight.EndForms(Caster);
            if (Form == DeathKnightForm.Chthonic)
                DeathKnight.ReleasePet(Caster);
            ECSGameEffectFactory.Create(new(Caster, Spell.Duration, 1, this), static (in ECSGameEffectInitParams i) => new DeathKnightFormEffect(i));
        }

        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }

    public class DeathKnightFormEffect : ECSGameSpellEffect
    {
        public const int PulseMs = 3000;
        private readonly List<MLMod> _mods = new();
        private int _healthBonus;
        private GameNPC _spiritPet;

        public DeathKnightFormEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.DeathKnightForm;
            if (Duration <= 0)
            {
                Duration = 0;
                ExpireTick = long.MaxValue;
            }
            PulseFreq = PulseMs;
            NextTick = GameLoop.GameLoopTime + PulseMs;
        }

        public DeathKnightForm Form => (DeathKnightForm)(int)SpellHandler.Spell.Value;
        private bool Has(DeathKnightForm form) => Form == form || Form == DeathKnightForm.Darkness && form is DeathKnightForm.Decrepit or DeathKnightForm.Chthonic;
        private double Boost => Form == DeathKnightForm.Darkness ? 1.1 : 1.0;
        public override DbPlayerXEffect GetSavedEffect() => null;

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            // Live sub-spells: Decrepit Power +10% magic damage (Decrepit Armor's 5 ABS was removed in 1.125 and is
            // not on live's delve); the Demon Lord's own Demon Power (20%), Demon Skill (+40 Painworking) and Demon
            // Deflection (25% parry), with Chthonic's absorption +10%.
            bool demon = Form == DeathKnightForm.Darkness;
            if (Has(DeathKnightForm.Decrepit))
                _mods.Add(new MLMod(eProperty.SpellDamage, MLCategory.Ability, demon ? 20 : 10));
            if (Has(DeathKnightForm.Spirit))
            {
                // Live Spirit Form delve: +40 resistance to Body, Spirit and Energy damage.
                foreach (eProperty resist in new[] { eProperty.Resist_Body, eProperty.Resist_Spirit, eProperty.Resist_Energy })
                    _mods.Add(new MLMod(resist, MLCategory.Buff, (int)(40 * Boost)));
            }
            if (Has(DeathKnightForm.Chthonic))
            {
                double scale = DeathKnight.PainworkingScale(Owner) * Boost;
                _mods.Add(new MLMod(eProperty.ParryChance, MLCategory.Ability, demon ? 25 : 30));
                // Chthonic Skill: +20 Painworking, which raises the Painworking weaponskill and melee damage.
                _mods.Add(new MLMod(eProperty.Skill_Pain_working, MLCategory.Ability, demon ? 40 : 20));
                foreach (eProperty resist in MLMod.MagicResists)
                    _mods.Add(new MLMod(resist, MLCategory.Ability, (int)(10 * Boost)));
                _healthBonus = (int)(Owner.MaxHealth * 0.30 * scale);
                _mods.Add(new MLMod(eProperty.MaxHealth, MLCategory.Buff, _healthBonus));
                // Spec AF that overwrites other spec AF buffs (1.125): only the amount above existing spec AF is added.
                int armor = (int)(DeathKnight.ChthonicArmor(Owner.Level) * Boost) - Owner.SpecBuffBonusCategory[eProperty.ArmorFactor];
                if (armor > 0)
                    _mods.Add(new MLMod(eProperty.ArmorFactor, MLCategory.Other, armor));
            }
            if (Has(DeathKnightForm.Chthonic))
                _mods.Add(new MLMod(eProperty.ArmorAbsorption, MLCategory.Buff, demon ? 22 : 20));
            if (Has(DeathKnightForm.Spirit))
                _mods.Add(new MLMod(eProperty.Skill_Stealth, MLCategory.Buff, 20)); // Spirit Sense: see hidden enemies more easily
            foreach (MLMod mod in _mods)
                mod.Apply(Owner, this, true);
            if (_healthBonus > 0)
                Owner.Health = Math.Min(Owner.MaxHealth, Owner.Health + _healthBonus);
            if (Has(DeathKnightForm.Decrepit) || Has(DeathKnightForm.Spirit))
                GameEventMgr.AddHandler(Owner, GameLivingEvent.AttackedByEnemy, OnAttacked);
            if (Owner is GamePlayer shifted)
                shifted.Model = DeathKnight.FormModel(shifted, Form);
            MLMod.Refresh(Owner);
            (Owner as GamePlayer)?.Out.SendCharStatsUpdate();
            OnEffectStartsMsg(true, true, true);
        }

        public override void OnStopEffect()
        {
            GameEventMgr.RemoveHandler(Owner, GameLivingEvent.AttackedByEnemy, OnAttacked);
            foreach (MLMod mod in _mods)
                mod.Apply(Owner, this, false);
            _mods.Clear();
            SetSpiritPet(null);
            if (Owner is GamePlayer shifted)
            {
                // When switching forms the new form may already be active: keep its appearance.
                DeathKnightFormEffect next = shifted.effectListComponent.GetSpellEffects(eEffect.DeathKnightForm)
                    .OfType<DeathKnightFormEffect>().FirstOrDefault(e => e != this && !e.IsEnding);
                shifted.Model = next != null ? DeathKnight.FormModel(shifted, next.Form) : shifted.CreationModel;
            }
            MLMod.Refresh(Owner);
            if (Owner.Health > Owner.MaxHealth)
                Owner.Health = Owner.MaxHealth;
            (Owner as GamePlayer)?.Out.SendCharStatsUpdate();
            OnEffectExpiresMsg(true, false, true);
            base.OnStopEffect();
        }

        public override void OnEffectPulse()
        {
            if (!Owner.IsAlive)
                return;
            if (Has(DeathKnightForm.Decrepit))
            {
                // Health regeneration that works in combat (1.123 reduced it at 35-45; 1.122C reduced it at 50).
                double percent = Owner.Level >= 50 ? 0.012 : Owner.Level >= 35 ? 0.011 : 0.015;
                Owner.ChangeHealth(Owner, eHealthChangeType.Regenerate, Math.Max(1, (int)(Owner.MaxHealth * percent * Boost)));
            }
            if (Has(DeathKnightForm.Spirit))
            {
                Owner.ChangeMana(Owner, eManaChangeType.Regenerate, Math.Max(1, (int)(Owner.MaxMana * 0.03 * Boost)));
                GameNPC pet = Owner.ControlledBrain?.Body;
                // Like a chant, the pet's spirit form drops when the master is controlled or the pet is out of range.
                bool active = pet != null && pet.IsAlive && !Owner.IsCrowdControlled && Owner.IsWithinRadius(pet, 2000);
                SetSpiritPet(active ? pet : null);
            }
        }

        private void SetSpiritPet(GameNPC pet)
        {
            if (_spiritPet == pet)
                return;
            int resist = (int)(55 * Boost);
            if (_spiritPet != null)
            {
                foreach (eProperty p in MLMod.MagicResists.Concat(new[] { eProperty.Resist_Crush, eProperty.Resist_Slash, eProperty.Resist_Thrust }))
                    _spiritPet.AbilityBonus[p] -= resist;
                if (_normalLook is { } normal)
                {
                    _spiritPet.Model = normal.Model;
                    _spiritPet.Name = normal.Name;
                    _spiritPet.Spells = normal.Spells;
                }
                _normalLook = null;
            }
            _spiritPet = pet;
            if (_spiritPet != null)
            {
                foreach (eProperty p in MLMod.MagicResists.Concat(new[] { eProperty.Resist_Crush, eProperty.Resist_Slash, eProperty.Resist_Thrust }))
                    _spiritPet.AbilityBonus[p] += resist;
                if (DeathKnight.SpiritTemplate(_spiritPet) is { } look)
                {
                    List<Spell> normalSpells = _spiritPet.Spells.ToList();
                    _normalLook = (_spiritPet.Model, _spiritPet.Name, normalSpells);
                    if (ushort.TryParse(look.Model?.Split(';')[0], out ushort model) && model > 0)
                        _spiritPet.Model = model;
                    _spiritPet.Name = look.Name;
                    _spiritPet.Spells = normalSpells.Concat(look.Spells ?? Enumerable.Empty<Spell>()).ToList();
                }
            }
        }

        private (ushort Model, string Name, List<Spell> Spells)? _normalLook;

        private void OnAttacked(DOLEvent e, object sender, EventArgs args)
        {
            if (args is not AttackedByEnemyEventArgs attacked || attacked.AttackData == null)
                return;
            AttackData ad = attacked.AttackData;
            if (Has(DeathKnightForm.Spirit) && ad.Damage + ad.CriticalDamage > 0)
                Owner.ChangeMana(Owner, eManaChangeType.Spell, Math.Max(1, (int)((ad.Damage + ad.CriticalDamage) * 0.10 * Boost)));
            // 1.127: the Decrepit disease proc fires on 50% of melee hits.
            if (Has(DeathKnightForm.Decrepit) && ad.IsMeleeAttack && ad.Attacker is GameLiving attacker && attacker.IsAlive && Util.Chance(50))
            {
                SpellHandler.Spell.TryGetParamSingle("DkDisease", out int diseaseId);
                Spell disease = SkillBase.GetSpellByID(diseaseId);
                if (disease != null)
                    ScriptMgr.CreateSpellHandler(Owner, disease, SpellHandler.SpellLine)?.StartSpell(attacker);
            }
        }
    }

    /// <summary>Revert Form: back to normal form (shares the 2-second form reuse).</summary>
    [SpellHandler(eSpellType.DeathKnightRevert)]
    public class DeathKnightRevertHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "Return to your normal form.";
        public override bool CheckBeginCast(GameLiving selectedTarget, bool quiet)
        {
            if (DeathKnight.Form(Caster) == DeathKnightForm.None)
            {
                if (!quiet) MessageToCaster("You are not in a form.", eChatType.CT_System);
                return false;
            }
            return base.CheckBeginCast(selectedTarget, quiet);
        }
        public override void ApplyEffectOnTarget(GameLiving target) => DeathKnight.EndForms(Caster);
        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }

    /// <summary>
    /// Ground spells: placed at the ground target; only one per caster is active (a new one replaces it) and the class
    /// shares one reuse timer (SharedTimerGroup). GroundKind 1 applies the sub-spell to enemies (disease), 2 deals the
    /// spell's damage to up to 16 enemies, 3 restores Value power to allies. Duration is not extended by items.
    /// </summary>
    [SpellHandler(eSpellType.DeathKnightGround)]
    public class DeathKnightGroundHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public int Kind { get { Spell.TryGetParamSingle("GroundKind", out int kind); return kind; } }
        public int PulseMs { get { Spell.TryGetParamSingle("GroundPulse", out int pulse); return pulse > 0 ? pulse : 3000; } }
        public int MaxTargets { get { Spell.TryGetParamSingle("GroundTargets", out int targets); return targets > 0 ? targets : 16; } }

        public override string ShortDescription => Kind switch
        {
            1 => $"Ground area ({Spell.Radius} radius, {Spell.Duration / 1000} s): inflicts a wasting disease on up to {MaxTargets} enemies inside each tick.",
            2 => $"Ground area ({Spell.Radius} radius, {Spell.Duration / 1000} s): {Spell.Damage} damage every {PulseMs / 1000.0:0.#} seconds to up to {MaxTargets} enemies inside.",
            _ => $"Ground area ({Spell.Radius} radius, {Spell.Duration / 1000} s): allies inside regain {Spell.Value} power every {PulseMs / 1000.0:0.#} seconds, even in combat."
        } + " Only one of your ground spells can be active.";

        public override bool CheckBeginCast(GameLiving selectedTarget, bool quiet)
        {
            if (!Caster.GroundTarget.IsValid || !Caster.GroundTargetInView || !Caster.IsWithinRadius(Caster.GroundTarget, Spell.Range))
            {
                if (!quiet) MessageToCaster("You need a ground target within range.", eChatType.CT_SpellResisted);
                return false;
            }
            return base.CheckBeginCast(selectedTarget, quiet);
        }

        public override void FinishSpellCast(GameLiving target)
        {
            Caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }

        public override bool StartSpell(GameLiving target)
        {
            DeathKnightGround.Remove(Caster);
            new DeathKnightGround(Caster, this, new Point3D(Caster.GroundTarget.X, Caster.GroundTarget.Y, Caster.GroundTarget.Z)).AddToWorld();
            return true;
        }
    }

    public class DeathKnightGround : GameStaticItem
    {
        private static readonly Dictionary<GameLiving, DeathKnightGround> _active = new();
        private static readonly object _lock = new();
        private readonly GameLiving _caster;
        private readonly DeathKnightGroundHandler _handler;
        private readonly long _ends;
        private ECSGameTimer _pulse;

        public DeathKnightGround(GameLiving caster, DeathKnightGroundHandler handler, Point3D point)
        {
            _caster = caster;
            _handler = handler;
            Name = handler.Spell.Name;
            Model = (ushort)(handler.Kind == 3 ? 2654 : handler.Kind == 2 ? 2653 : 3738);
            X = point.X; Y = point.Y; Z = point.Z;
            CurrentRegionID = caster.CurrentRegionID;
            Realm = caster.Realm;
            Level = caster.Level;
            _ends = GameLoop.GameLoopTime + handler.Spell.Duration;
        }

        public static DeathKnightGround Active(GameLiving caster)
        {
            lock (_lock)
                return _active.TryGetValue(caster, out DeathKnightGround ground) ? ground : null;
        }

        public static void Remove(GameLiving caster) => Active(caster)?.RemoveFromWorld();

        public override bool AddToWorld()
        {
            if (!base.AddToWorld())
                return false;
            lock (_lock)
                _active[_caster] = this;
            _pulse = new ECSGameTimer(this, OnPulse, 1);
            return true;
        }

        public override bool RemoveFromWorld()
        {
            _pulse?.Stop();
            lock (_lock)
                if (_active.TryGetValue(_caster, out DeathKnightGround ground) && ground == this)
                    _active.Remove(_caster);
            return base.RemoveFromWorld();
        }

        private int OnPulse(ECSGameTimer timer)
        {
            if (GameLoop.GameLoopTime >= _ends || _caster.ObjectState != eObjectState.Active || _caster.CurrentRegion != CurrentRegion)
            {
                RemoveFromWorld();
                return 0;
            }
            int radius = _handler.Spell.Radius;
            IEnumerable<GameLiving> inside = GetPlayersInRadius((ushort)radius).Cast<GameLiving>().Concat(GetNPCsInRadius((ushort)radius))
                .Where(t => t != null && t.IsAlive && t.ObjectState == eObjectState.Active && t is not GameStorm);
            if (_handler.Kind == 3)
            {
                foreach (GameLiving ally in inside.Where(t => t.Realm == _caster.Realm && !GameServer.ServerRules.IsAllowedToAttack(_caster, t, true)))
                    ally.ChangeMana(_caster, eManaChangeType.Spell, (int)_handler.Spell.Value);
            }
            else
            {
                List<GameLiving> enemies = inside.Where(t => t != _caster && GameServer.ServerRules.IsAllowedToAttack(_caster, t, true)).ToList();
                enemies = enemies.OrderBy(t => GetDistanceTo(t)).Take(_handler.MaxTargets).ToList();
                Spell effect = SkillBase.GetSpellByID(_handler.Spell.SubSpellID);
                if (effect != null)
                    foreach (GameLiving enemy in enemies)
                        ScriptMgr.CreateSpellHandler(_caster, effect, _handler.SpellLine)?.StartSpell(enemy);
            }
            return (int)Math.Min(_handler.PulseMs, Math.Max(1, _ends - GameLoop.GameLoopTime));
        }
    }

    /// <summary>
    /// Magic conversion (Soul of Magic ... Way of Magic): the next magical attack is absorbed (Damage %) and part of it
    /// heals you (WardHeal %). Self only since 1.129B; it renews every Frequency while maintained.
    /// </summary>
    [SpellHandler(eSpellType.DeathKnightMagicWard)]
    public class DeathKnightMagicWardHandler(GameLiving caster, Spell spell, SpellLine line) : MagicAblativeArmorSpellHandler(caster, spell, line)
    {
        public int HealPercent { get { Spell.TryGetParamSingle("WardHeal", out int heal); return heal; } }
        public override string ShortDescription => $"The next magical attack against you is {Spell.Damage}% absorbed and {HealPercent}% of its damage heals you instead.";

        public override void OnDamageAbsorbed(AttackData ad, int damageAmount)
        {
            int total = damageAmount + Math.Max(0, ad.Damage) + Math.Max(0, ad.CriticalDamage);
            int heal = total * HealPercent / 100;
            if (heal > 0)
                ad.Target.ChangeHealth(ad.Target, eHealthChangeType.Spell, heal);
            // One attack per renewal: consume the remaining buffer.
            foreach (ECSGameSpellEffect effect in ad.Target.effectListComponent.GetSpellEffects(eEffect.AblativeArmor))
                if (effect.SpellHandler == this && effect is AblativeArmorECSGameEffect ablative)
                    ablative.RemainingValue = 0;
        }
    }

    /// <summary>Ignore line: the ally has Value% chance to resist debuff spells (1.129B: 20 s, 180 s reuse).</summary>
    [SpellHandler(eSpellType.DeathKnightIgnore)]
    public class DeathKnightIgnoreHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"The target has a {Spell.Value}% chance to resist debuff spells for {Spell.Duration / 1000} seconds.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new DeathKnightSimpleEffect(i, eEffect.DeathKnightIgnore));
        public override void FinishSpellCast(GameLiving target)
        {
            Caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }
    }

    public class DeathKnightSimpleEffect : ECSGameSpellEffect
    {
        public DeathKnightSimpleEffect(in ECSGameEffectInitParams initParams, eEffect type) : base(initParams) { EffectType = type; }
        public override void OnStartEffect() { base.OnStartEffect(); OnEffectStartsMsg(true, true, true); }
        public override void OnStopEffect() { OnEffectExpiresMsg(true, false, true); base.OnStopEffect(); }
        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>Power Shield (Death Servant 35): while below 50% health, power is funneled into health.</summary>
    [SpellHandler(eSpellType.DeathKnightPowerShield)]
    public class DeathKnightPowerShieldHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "While your health is below 50%, your power is converted into health until you are back above 50%.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new DeathKnightPowerShieldEffect(i));
        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }

    public class DeathKnightPowerShieldEffect : ECSGameSpellEffect
    {
        public DeathKnightPowerShieldEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.DeathKnightPowerShield;
            Duration = 0;
            ExpireTick = long.MaxValue;
            PulseFreq = 1000;
            NextTick = GameLoop.GameLoopTime + 1000;
        }

        public static int Transfer(int health, int maxHealth, int mana)
        {
            int missing = maxHealth / 2 - health;
            return missing <= 0 ? 0 : Math.Min(missing, mana);
        }

        public override void OnEffectPulse()
        {
            int amount = Transfer(Owner.Health, Owner.MaxHealth, Owner.Mana);
            if (amount <= 0 || !Owner.IsAlive)
                return;
            Owner.Mana -= amount;
            Owner.ChangeHealth(Owner, eHealthChangeType.Spell, amount);
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>Empowerment aura: group members gain Value% critical chance with all magic while the chant pulses.</summary>
    [SpellHandler(eSpellType.DeathKnightEmpowerment)]
    public class DeathKnightEmpowermentHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Increases the group's critical hit chance with all magic by {Spell.Value}%.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new DeathKnightEmpowermentEffect(i));
    }

    public class DeathKnightEmpowermentEffect : ECSGameSpellEffect
    {
        private int _bonus;
        public DeathKnightEmpowermentEffect(in ECSGameEffectInitParams initParams) : base(initParams) { EffectType = eEffect.DeathKnightEmpowerment; }
        public override void OnStartEffect()
        {
            base.OnStartEffect();
            _bonus = (int)SpellHandler.Spell.Value;
            Owner.AbilityBonus[eProperty.CriticalSpellHitChance] += _bonus;
        }
        public override void OnStopEffect()
        {
            Owner.AbilityBonus[eProperty.CriticalSpellHitChance] -= _bonus;
            _bonus = 0;
            base.OnStopEffect();
        }
        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>Regenerate Flesh line: heals the caster and its servant over time.</summary>
    [SpellHandler(eSpellType.DeathKnightRegenerate)]
    public class DeathKnightRegenerateHandler(GameLiving caster, Spell spell, SpellLine line) : HoTSpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"You and your servant regenerate {Spell.Value} health every {Spell.Frequency / 1000.0:0.#} seconds.";
        public override List<GameLiving> SelectTargets(GameObject castTarget)
        {
            var targets = new List<GameLiving> { Caster };
            if (Caster.ControlledBrain?.Body is GameNPC pet && pet.IsAlive && Caster.IsWithinRadius(pet, Spell.Range))
                targets.Add(pet);
            return targets;
        }
    }

    /// <summary>Snares that ignore and do not grant immunity (the Exhaustion and Ice lines, Freezing Howl, Nethersbane).</summary>
    [SpellHandler(eSpellType.DeathKnightSnare)]
    public class DeathKnightSnareHandler(GameLiving caster, Spell spell, SpellLine line) : SpeedDecreaseSpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Slows the target by {Spell.Value}% for {Spell.Duration / 1000} seconds. Stacks with other snares, ignores immunity and grants none.";

        // Live delves: these snares land on targets that already have root or snare immunity.
        protected override bool RespectsSnareImmunity => false;
        public bool IgnoresSnareImmunity => !RespectsSnareImmunity;
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams)
        {
            ECSGameSpellEffect effect = ECSGameEffectFactory.Create(initParams, static (in i) => new DeathKnightSnareEffect(i));
            effect.TriggersImmunity = false;
            return effect;
        }
    }

    public class DeathKnightSnareEffect : StatDebuffECSEffect
    {
        public DeathKnightSnareEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            PulseFreq = 0;
            NextTick = 0;
        }
        public override void TryApplyImmunity() { }
    }

    /// <summary>Conjure Icebrand / Nethersbane: summons the Painworking weapon for the caster's level.</summary>
    [SpellHandler(eSpellType.DeathKnightConjure)]
    public class DeathKnightConjureHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public bool IsNethersbane => Spell.Value >= 50;
        public static string IcebrandFor(int level) => $"{DeathKnight.WeaponPrefix}icebrand_{Math.Clamp(level / 5 * 5, 0, 50)}";
        public string TemplateId => IsNethersbane ? DeathKnight.Nethersbane : IcebrandFor(Caster.Level);

        public override string ShortDescription => IsNethersbane
            ? "Summons Nethersbane, Arawn's evil blade. Cold damage. It is removed when you log out."
            : "Summons a Chthonic Blade (Icebrand) of your level. Cold damage.";

        public override void FinishSpellCast(GameLiving target)
        {
            Caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            if (Caster is not GamePlayer player)
                return;
            DbItemTemplate template = GameServer.Database.FindObjectByKey<DbItemTemplate>(TemplateId);
            if (template == null)
            {
                MessageToCaster("That weapon is not installed in this world.", eChatType.CT_System);
                return;
            }
            // Replace older conjured blades of the same kind.
            foreach (DbInventoryItem old in player.Inventory.AllItems.Where(i => DeathKnight.IsConjured(i) && (i.Id_nb == DeathKnight.Nethersbane) == IsNethersbane).ToList())
                player.Inventory.RemoveItem(old);
            DbInventoryItem item = GameInventoryItem.Create(template);
            if (!player.Inventory.AddItem(eInventorySlot.FirstEmptyBackpack, item))
            {
                MessageToCaster("You have no room for the weapon.", eChatType.CT_System);
                return;
            }
            InventoryLogging.LogInventoryAction(Caster, player, eInventoryActionType.Other, template, 1);
            MessageToCaster($"{template.Name} appears in your pack.", eChatType.CT_Spell);
        }

        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }

    /// <summary>Death servants (Aegis, Soultorn, Fiend, Priest, Succubus): level with the caster; not in Chthonic Form.</summary>
    [SpellHandler(eSpellType.DeathKnightServant)]
    public class DeathKnightServantHandler(GameLiving caster, Spell spell, SpellLine line) : SummonSpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Summons a death servant of your level. Not usable in Chthonic Form.";

        public override bool CheckBeginCast(GameLiving selectedTarget, bool quiet)
        {
            if (DeathKnight.Form(Caster) == DeathKnightForm.Chthonic)
            {
                if (!quiet) MessageToCaster("You cannot summon a servant in Chthonic Form.", eChatType.CT_SpellResisted);
                return false;
            }
            if (Caster.ControlledBrain != null)
            {
                if (!quiet) MessageToCaster("You already have a servant.", eChatType.CT_SpellResisted);
                return false;
            }
            return base.CheckBeginCast(selectedTarget, quiet);
        }
    }

    /// <summary>
    /// Power Lock (Death Servant 45): locks the Death Knight and its target in place for the duration; the target is
    /// stunned (the sub-spell, 1.125D), loses Value% of its maximum power every second to the Death Knight (1.124D), and
    /// neither can be damaged by melee attacks.
    /// </summary>
    [SpellHandler(eSpellType.DeathKnightPowerLock)]
    public class DeathKnightPowerLockHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"Locks you and your target in place, siphoning {Spell.Value}% of its power every second for {Spell.Duration / 1000} seconds. While locked, neither of you can be damaged by melee attacks.";

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new DeathKnightPowerLockEffect(i));

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            base.ApplyEffectOnTarget(target);
            // The Death Knight is held too, for the same time.
            ECSGameEffectFactory.Create(new(Caster, Spell.Duration, 1, this), static (in ECSGameEffectInitParams i) => new DeathKnightPowerLockEffect(i));
        }

        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;
        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }

    public class DeathKnightPowerLockEffect : ECSGameSpellEffect
    {
        private readonly MLMod _hold = MLMod.Speed(0);

        public DeathKnightPowerLockEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.DeathKnightPowerLock;
            PulseFreq = 1000;
            NextTick = GameLoop.GameLoopTime + 1000;
        }

        private bool IsVictim => Owner != SpellHandler.Caster;

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            _hold.Apply(Owner, this, true);
            MLMod.Refresh(Owner);
            Owner.attackComponent.StopAttack();
            (Owner as GamePlayer)?.Out.SendUpdateMaxSpeed();
            OnEffectStartsMsg(true, true, true);
        }

        public override void OnStopEffect()
        {
            _hold.Apply(Owner, this, false);
            MLMod.Refresh(Owner);
            (Owner as GamePlayer)?.Out.SendUpdateMaxSpeed();
            OnEffectExpiresMsg(true, false, true);
            base.OnStopEffect();
        }

        public override void OnEffectPulse()
        {
            GameLiving caster = SpellHandler.Caster;
            if (!IsVictim || !Owner.IsAlive || caster == null || !caster.IsAlive)
                return;
            int drain = Math.Min(Owner.Mana, Owner.MaxMana * (int)SpellHandler.Spell.Value / 100);
            if (drain <= 0)
                return;
            Owner.ChangeMana(caster, eManaChangeType.Spell, -drain);
            caster.ChangeMana(caster, eManaChangeType.Spell, drain);
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>
    /// Arawn's Legion (Death Servant 50): Arawn's army rises beside up to 8 enemies within the radius (1.124D) and each
    /// legionnaire attacks its own enemy until the duration ends. LifeDrainReturn is the legion NPC template and
    /// Damage/Value set its level, as for any summon.
    /// </summary>
    [SpellHandler(eSpellType.DeathKnightLegion)]
    public class DeathKnightLegionHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public const int MaxTargets = 8;

        public override string ShortDescription =>
            $"Arawn's legion attacks up to {MaxTargets} enemies within {Spell.Radius} units for {Spell.Duration / 1000} seconds.";

        public override bool CheckBeginCast(GameLiving selectedTarget, bool quiet)
        {
            if (DeathKnight.Form(Caster) == DeathKnightForm.Chthonic)
            {
                if (!quiet) MessageToCaster("You cannot call the legion in Chthonic Form.", eChatType.CT_SpellResisted);
                return false;
            }
            return base.CheckBeginCast(selectedTarget, quiet);
        }

        public override void FinishSpellCast(GameLiving target)
        {
            Caster.Mana -= PowerCost(target);
            base.FinishSpellCast(target);
        }

        public override bool StartSpell(GameLiving target)
        {
            List<GameLiving> enemies = Caster.GetPlayersInRadius((ushort)Spell.Radius).Cast<GameLiving>()
                .Concat(Caster.GetNPCsInRadius((ushort)Spell.Radius))
                .Where(t => t != null && t.IsAlive && t.ObjectState == GameObject.eObjectState.Active && GameServer.ServerRules.IsAllowedToAttack(Caster, t, true))
                .OrderBy(t => Caster.GetDistanceTo(t)).Take(MaxTargets).ToList();
            if (enemies.Count == 0)
            {
                MessageToCaster("There are no enemies for the legion to attack.", eChatType.CT_SpellResisted);
                return false;
            }
            foreach (GameLiving enemy in enemies)
                new DeathKnightLegionnaireHandler(Caster, Spell, SpellLine).ApplyEffectOnTarget(enemy);
            return true;
        }
    }

    /// <summary>One legionnaire: a temporary pet, like a Theurgist's, that attacks its enemy and vanishes at the end.</summary>
    public class DeathKnightLegionnaireHandler(GameLiving caster, Spell spell, SpellLine line) : SummonTheurgistPet(caster, spell, line)
    {
        private GameLiving _enemy;

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            _enemy = target;
            base.ApplyEffectOnTarget(target);
        }

        protected override void GetPetLocation(out int x, out int y, out int z, out ushort heading, out Region region)
        {
            base.GetPetLocation(out x, out y, out z, out heading, out region);
            if (_enemy != null && _enemy.CurrentRegion == region)
            {
                // Rise beside the enemy rather than beside the Death Knight.
                x = _enemy.X + Util.Random(-60, 60);
                y = _enemy.Y + Util.Random(-60, 60);
                z = _enemy.Z;
            }
        }
    }

    /// <summary>Vanquisher's proc: dissipates every ablative barrier on the target (live Ablative Remover).</summary>
    [SpellHandler(eSpellType.DeathKnightAblativeStrip)]
    public class DeathKnightAblativeStripHandler : RemoveSpellEffectHandler
    {
        public override string ShortDescription => "Dissipates all ablative barriers from the target.";

        public DeathKnightAblativeStripHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line)
        {
            m_spellTypesToRemove = ["AblativeArmor", "MagicAblativeArmor", "BothAblativeArmor"];
        }
    }
}
