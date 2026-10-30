using System;
using System.Collections.Generic;
using System.Linq;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS.Keeps;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    // Live (1.130a) class spells that needed a new mechanic (round3_lines.py, seventh pass). The grapples, Blight
    // Surge and the enchantments are read by GameLiving.OnAttackedByEnemy, AttackComponent and MaxSpeedCalculator.

    /// <summary>Shared checks for the effects below.</summary>
    public static class LiveRound7
    {
        public static bool Has(GameLiving living, eEffect type) =>
            living?.effectListComponent != null && living.effectListComponent.GetSpellEffects(type).Any(e => e.IsActive && !e.IsEnding);

        public static ECSGameSpellEffect Best(GameLiving living, eEffect type) =>
            living?.effectListComponent?.GetSpellEffects(type).Where(e => e.IsActive && !e.IsEnding)
                .OrderByDescending(e => e.SpellHandler.Spell.Value).FirstOrDefault();

        /// <summary>Melee can't land on (or be swung by) a grappled living (AttackComponent.CalculateEnemyAttackResult).</summary>
        public static bool BlocksMelee(GameLiving target, GameLiving attacker) =>
            Has(target, eEffect.IceGrip) || Has(target, eEffect.FlameCocoon) || Has(target, eEffect.BattleControl) ||
            Has(attacker, eEffect.BattleControl);

        /// <summary>
        /// Called for every attack before ablatives: Ice Grip and Blight Surge take no damage at all, and Siegebreaker
        /// adds its damage to melee hits on keep doors, keep walls and siege weapons.
        /// </summary>
        public static void OnAttacked(GameLiving victim, AttackData ad)
        {
            if (ad == null || !ad.IsHit)
                return;

            if (Has(victim, eEffect.IceGrip) || Has(victim, eEffect.BlightSurge))
            {
                ad.Damage = 0;
                ad.CriticalDamage = 0;
                return;
            }

            if (ad.IsMeleeAttack && SiegebreakerSpellHandler.IsSiegeObject(victim) && Best(ad.Attacker as GameLiving, eEffect.Siegebreaker) is { } siege)
                ad.Damage += (int) siege.SpellHandler.Spell.Damage;
        }

        /// <summary>The living's spot as a point, for the radius searches.</summary>
        public static IEnumerable<GameLiving> EnemiesNear(GameLiving caster, GameObject centre, ushort radius)
        {
            foreach (GamePlayer player in centre.GetPlayersInRadius(radius))
                if (player.IsAlive && GameServer.ServerRules.IsAllowedToAttack(caster, player, true))
                    yield return player;
            foreach (GameNPC npc in centre.GetNPCsInRadius(radius))
                if (npc.IsAlive && GameServer.ServerRules.IsAllowedToAttack(caster, npc, true))
                    yield return npc;
        }
    }

    /// <summary>An effect that holds its owner in place for its duration (the grapples, Heart of Nature's root).</summary>
    public class LiveHoldEffect : ECSGameSpellEffect
    {
        private readonly MLMod _hold = MLMod.Speed(0);

        public LiveHoldEffect(in ECSGameEffectInitParams initParams, eEffect type) : base(initParams)
        {
            EffectType = type;
        }

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            _hold.Apply(Owner, this, true);
            OnEffectStartsMsg(true, true, true);
        }

        public override void OnStopEffect()
        {
            _hold.Apply(Owner, this, false);
            OnEffectExpiresMsg(true, false, true);
            base.OnStopEffect();
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>
    /// Wizard Ice Grip (Cold 44, live 1.121): the target is held in place and can't be damaged at all for the
    /// duration, but it can still swing at whoever is in reach.
    /// </summary>
    [SpellHandler(eSpellType.IceGrip)]
    public class IceGripSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"Grapples the target in place for {Spell.Duration / 1000} seconds. The target can't be damaged, but may still use melee attacks.";

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new LiveHoldEffect(i, eEffect.IceGrip));

        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;
    }

    /// <summary>
    /// Wizard Flame Cocoon (Fire 45, live 1.121): the Wizard is held in place, silenced and protected from melee, and
    /// heals Value every Frequency ms. Cancelling the cocoon ends the hold and the protection; the silence lasts its
    /// full duration.
    /// </summary>
    [SpellHandler(eSpellType.FlameCocoon)]
    public class FlameCocoonSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"Grapples yourself for {Spell.Duration / 1000} seconds: melee attacks can't hurt you and you restore {Spell.Value} health every " +
            $"{Spell.Frequency / 1000.0:0.#} seconds, but you can't move or cast. You may cancel the cocoon; the silence lasts its full duration.";

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new FlameCocoonEffect(i));

        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            target.SilencedTime = target.CurrentRegion.Time + Spell.Duration;
            target.StopCurrentSpellcast();
            base.ApplyEffectOnTarget(target);
        }
    }

    public class FlameCocoonEffect : LiveHoldEffect
    {
        public FlameCocoonEffect(in ECSGameEffectInitParams initParams) : base(initParams, eEffect.FlameCocoon)
        {
            PulseFreq = Math.Max(500, SpellHandler.Spell.Frequency);
            NextTick = GameLoop.GameLoopTime + PulseFreq;
        }

        public override void OnEffectPulse()
        {
            if (Owner.IsAlive)
                Owner.ChangeHealth(SpellHandler.Caster, eHealthChangeType.Spell, (int) SpellHandler.Spell.Value);
        }
    }

    /// <summary>
    /// Warrior Battle Control (Shield 50, live 1.121): the Warrior and up to Value-1 group members (pets too) within the
    /// radius are grappled: they can't move, melee or be hit by melee, but can still cast and receive spells. It ignores
    /// grapple immunities.
    /// </summary>
    [SpellHandler(eSpellType.BattleControl)]
    public class BattleControlSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"Grapples you and up to {(int) Spell.Value - 1} group members (pets included) within {Spell.Radius} units for {Spell.Duration / 1000} " +
            "seconds: they can't move, melee or be struck by melee, but may cast and receive spells.";

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new LiveHoldEffect(i, eEffect.BattleControl));

        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;
        public override double CalculateSpellResistChance(GameLiving target) => 0;

        public override List<GameLiving> SelectTargets(GameObject castTarget)
        {
            List<GameLiving> members = [Caster];
            IEnumerable<GameLiving> group = Caster.Group?.GetMembersInTheGroup() ?? Enumerable.Empty<GameLiving>();
            foreach (GameLiving member in group.Prepend(Caster).Distinct())
            {
                if (member != Caster && member.IsAlive && Caster.IsWithinRadius(member, Spell.Radius))
                    members.Add(member);
                if (member.ControlledBrain?.Body is GameNPC pet && pet.IsAlive && Caster.IsWithinRadius(pet, Spell.Radius))
                    members.Add(pet);
            }

            int cap = Spell.Value > 0 ? (int) Spell.Value : members.Count;
            return members.Distinct().OrderBy(m => m == Caster ? 0 : Caster.GetDistanceTo(m)).Take(cap).ToList();
        }

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            target.attackComponent.StopAttack();
            base.ApplyEffectOnTarget(target);
        }
    }

    /// <summary>
    /// Assassin Overshadow (Stealth 39, live 1.121/1.125): an ally (not yourself, a stealther or a Minstrel) is hidden
    /// for the duration; it may move, and any combat action reveals it.
    /// </summary>
    [SpellHandler(eSpellType.AllyStealth)]
    public class AllyStealthSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"Stealths the targeted ally for {Spell.Duration / 1000} seconds. Can't be used on yourself, on a Minstrel or on a class with the Stealth skill.";

        public override bool UnstealthCasterOnStart => false;
        public override bool UnstealthCasterOnFinish => false;

        public static bool CanHide(GameLiving caster, GameLiving target) =>
            target is GamePlayer player && player != caster && player.IsAlive && !player.HasSpecialization(Specs.Stealth) &&
            player.CharacterClass.ID != (int) eCharacterClass.Minstrel;

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if (!CanHide(Caster, selectedTarget))
            {
                MessageToCaster("You can't hide that target.", eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new AllyStealthEffect(i));

        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;
    }

    public class AllyStealthEffect : ECSGameSpellEffect
    {
        public AllyStealthEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.AllyStealth;
        }

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            Owner.Stealth(true);
        }

        public override void OnStopEffect()
        {
            if (Owner.IsStealthed)
                Owner.Stealth(false);
            base.OnStopEffect();
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>
    /// Thane Chain Lightning (Stormcalling 49, live 1.125): direct damage to the target, then up to MaxJumps other
    /// random enemies near it, each jump doing JumpLoss less (the server's chain bolt rule; live gives no figure).
    /// </summary>
    [SpellHandler(eSpellType.ChainDirectDamage)]
    public class ChainDirectDamageSpellHandler(GameLiving caster, Spell spell, SpellLine line) : DirectDamageSpellHandler(caster, spell, line)
    {
        public const int MaxJumps = 4;
        public const ushort JumpRadius = 500;
        public const double JumpLoss = 0.1;

        public override string ShortDescription =>
            $"Inflicts {Spell.Damage} {Spell.DamageTypeToString()} damage to the target, then jumps to up to {MaxJumps} other random enemies " +
            "near it, doing less damage with each jump.";

        public static double Factor(int jump) => Math.Max(0, 1 - JumpLoss * jump);

        protected override void DealDamage(GameLiving target)
        {
            Strike(target, 1);
            List<GameLiving> others = LiveRound7.EnemiesNear(Caster, target, JumpRadius).Where(l => l != target).ToList();
            for (int jump = 1; jump <= MaxJumps && others.Count > 0; jump++)
            {
                GameLiving next = others[Util.Random(others.Count - 1)];
                others.Remove(next);
                Strike(next, Factor(jump));
            }
        }

        private void Strike(GameLiving target, double factor)
        {
            if (!target.IsAlive || target.ObjectState is not GameObject.eObjectState.Active)
                return;

            AttackData ad = CalculateDamageToTarget(target);
            ad.Damage = (int) (ad.Damage * factor);
            ad.CriticalDamage = (int) (ad.CriticalDamage * factor);
            SendDamageMessages(ad);
            DamageTarget(ad, true);
            target.StartDamageInterruptTimer(target.SpellInterruptDuration, ad);
        }
    }

    /// <summary>
    /// Mentalist Speedwarp's pulse (Mentalism 49): enemies in the ward lose every speed boost while it lasts
    /// (MaxSpeedCalculator caps their speed at normal run speed; snares still apply).
    /// </summary>
    [SpellHandler(eSpellType.Speedwarp)]
    public class SpeedwarpSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "Negates the target's speed boosts.";

        public static bool IsWarped(GameLiving living) => LiveRound7.Has(living, eEffect.Speedwarp);

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new SpeedwarpEffect(i));

        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;
        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }

    public class SpeedwarpEffect : ECSGameSpellEffect
    {
        public SpeedwarpEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.Speedwarp;
        }

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            Owner.OnMaxSpeedChange();
        }

        public override void OnStopEffect()
        {
            base.OnStopEffect();
            Owner.OnMaxSpeedChange();
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>
    /// Druid Heart of Nature (Nature 50, live 1.123): frees the group from roots and snares, then roots up to RootsPerAlly
    /// enemies within the radius of each ally for the duration. The root ignores immunities and damage doesn't break it.
    /// </summary>
    [SpellHandler(eSpellType.HeartOfNature)]
    public class HeartOfNatureSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public const int RootsPerAlly = 2;

        public override string ShortDescription =>
            $"Removes all root and snare effects from your group and roots up to {RootsPerAlly} enemies within {Spell.Radius} units of each ally " +
            $"for {Spell.Duration / 1000} seconds. This root ignores immunities and does not break on damage.";

        public override bool HasPositiveEffect => true;

        public override List<GameLiving> SelectTargets(GameObject castTarget)
        {
            List<GameLiving> members = (Caster.Group?.GetMembersInTheGroup() ?? [Caster]).Where(m => m.IsAlive &&
                (m == Caster || Caster.IsWithinRadius(m, Spell.Range))).ToList();
            if (!members.Contains(Caster))
                members.Add(Caster);
            return members;
        }

        public override void ApplyEffectOnTarget(GameLiving ally)
        {
            foreach (ECSGameSpellEffect snare in ally.effectListComponent.GetSpellEffects(eEffect.MovementSpeedDebuff).ToList())
                snare.End();

            int rooted = 0;
            foreach (GameLiving enemy in LiveRound7.EnemiesNear(Caster, ally, (ushort) Spell.Radius))
            {
                if (rooted >= RootsPerAlly)
                    break;
                if (LiveRound7.Has(enemy, eEffect.NatureRoot))
                    continue;
                ECSGameEffectFactory.Create(new(enemy, Spell.Duration, 1, this), static (in ECSGameEffectInitParams i) => new LiveHoldEffect(i, eEffect.NatureRoot));
                rooted++;
            }
        }
    }

    /// <summary>
    /// Enchanter Enchantment of Zeal (Enchantments 50, live 1.122B): the group's melee style damage bonus is multiplied
    /// by Value, and the damage of each styled hit heals the attacker's other group members, shared between them.
    /// </summary>
    [SpellHandler(eSpellType.StyleZeal)]
    public class StyleZealSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public const ushort HealRange = 2000;

        public override string ShortDescription =>
            $"Multiplies the damage bonus of melee combat styles by {Spell.Value} for all allies, and the damage they do with styles heals the group.";

        public static double StyleFactor(GameLiving attacker) => LiveRound7.Best(attacker, eEffect.StyleZeal) is { } zeal ? zeal.SpellHandler.Spell.Value : 1;

        /// <summary>The healed share each other group member in range gets from a styled hit of <paramref name="damage"/>.</summary>
        public static int Share(int damage, int members) => members <= 0 ? 0 : damage / members;

        public static void OnAttacked(GameLiving victim, AttackData ad)
        {
            if (ad == null || !ad.IsHit || ad.Style == null || ad.Attacker is not GameLiving attacker || !LiveRound7.Has(attacker, eEffect.StyleZeal))
                return;

            List<GameLiving> others = attacker.Group?.GetMembersInTheGroup().Where(m => m != attacker && m.IsAlive && attacker.IsWithinRadius(m, HealRange)).ToList();
            int share = Share(ad.Damage + ad.CriticalDamage, others?.Count ?? 0);
            if (share <= 0)
                return;
            foreach (GameLiving member in others)
                member.ChangeHealth(attacker, eHealthChangeType.Spell, share);
        }
    }

    /// <summary>
    /// Enchanter Enchantment of Truth (Enchantments 46, live 1.122B): the group's melee attacks can't miss and pierce
    /// bladeturn magic. Stacks with the other enchantments.
    /// </summary>
    [SpellHandler(eSpellType.MeleeTruth)]
    public class MeleeTruthSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "All allies' melee attacks strike with 100% accuracy and pierce bladeturn magic.";

        public static bool Strikes(AttackData ad) => ad != null && ad.IsMeleeAttack && LiveRound7.Has(ad.Attacker as GameLiving, eEffect.MeleeTruth);
    }

    /// <summary>
    /// Champion, Skald and Minstrel Siegebreaker (level 40, live 1.122B): the group's melee hits on keep doors, keep
    /// walls and siege weapons do Damage more. (The bonus live gives controlled siege weapons has no figure; not built.)
    /// </summary>
    [SpellHandler(eSpellType.Siegebreaker)]
    public class SiegebreakerSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"The group's melee swings do {Spell.Damage} additional damage to siege objects.";

        public static bool IsSiegeObject(GameObject target) => target is GameKeepComponent or GameKeepDoor or GameSiegeWeapon;
    }

    /// <summary>
    /// Shaman Blight Surge (Cave 50, live 1.123/1.126): for the duration the Shaman takes no damage and heals Value% of
    /// its maximum health every Frequency ms; each pulse, enemies within the radius take the LifeDrainReturn spell (Matter
    /// damage and a disease) and lose Damage endurance.
    /// </summary>
    [SpellHandler(eSpellType.BlightSurge)]
    public class BlightSurgeSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"Wrap yourself in blight for {Spell.Duration / 1000} seconds, immune to all damage and regenerating {Spell.Value}% of your health " +
            $"every {Spell.Frequency / 1000.0:0.#} seconds. Enemies within {Spell.Radius} units are diseased, lose {Spell.Damage} endurance and take matter damage.";

        public override bool HasPositiveEffect => true;

        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new BlightSurgeEffect(i));

        protected override int CalculateEffectDuration(GameLiving target) => Spell.Duration;
        public override double CalculateSpellResistChance(GameLiving target) => 0;
    }

    public class BlightSurgeEffect : ECSGameSpellEffect
    {
        public BlightSurgeEffect(in ECSGameEffectInitParams initParams) : base(initParams)
        {
            EffectType = eEffect.BlightSurge;
            PulseFreq = Math.Max(500, SpellHandler.Spell.Frequency);
            NextTick = GameLoop.GameLoopTime + PulseFreq;
        }

        public override void OnEffectPulse()
        {
            Spell spell = SpellHandler.Spell;
            if (!Owner.IsAlive)
                return;

            Owner.ChangeHealth(Owner, eHealthChangeType.Spell, (int) (Owner.MaxHealth * spell.Value / 100));
            Spell child = SkillBase.GetSpellByID(spell.LifeDrainReturn); // not SubSpellID: the cast would put it on the Shaman
            foreach (GameLiving enemy in LiveRound7.EnemiesNear(Owner, Owner, (ushort) spell.Radius).ToList())
            {
                enemy.ChangeEndurance(Owner, eEnduranceChangeType.Spell, -(int) spell.Damage);
                if (child != null)
                    ScriptMgr.CreateSpellHandler(Owner, child, SpellHandler.SpellLine)?.StartSpell(enemy);
            }
        }

        public override DbPlayerXEffect GetSavedEffect() => null;
    }

    /// <summary>
    /// Reaver Malefic Horror (Soulrending 39, live 1.121): enemy pets and monsters within the radius flee for the
    /// duration. Pets respect the pet-fear immunity without gaining it (as the Bainshee's Ethereal Shriek).
    /// </summary>
    [SpellHandler(eSpellType.MaleficHorror)]
    public class MaleficHorrorSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Causes enemy pets and monsters within {Spell.Radius} units to flee in terror for {Spell.Duration / 1000} seconds.";

        public static bool Scares(GameLiving caster, GameLiving target) => target is GameNPC npc && npc.IsAlive && npc is not GameKeepGuard &&
            (npc.Brain is not IControlledBrain || WarlockPetFearHandler.IsEnemyPet(caster, npc)) && !WarlockPetFearHandler.IsImmune(npc);

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            if (!Scares(Caster, target))
                return;
            GameLiving caster = Caster;
            ECSGameEffectFactory.Create(new(target, Spell.Duration, 1), (in ECSGameEffectInitParams i) => new WarlockPetFearEffect(i, caster, false));
        }
    }
}
