using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using DOL.Events;

namespace DOL.GS.Trials
{
    /// <summary>One blow against a watched monster, copied off the attack so it can wait for the run's tick.</summary>
    public readonly record struct TrialHit(eDamageType DamageType, AttackData.eAttackType AttackType, int Damage);

    /// <summary>Laodameia's temper: too many blows of one damage type in a row, then a pause before she can rage again.</summary>
    public sealed class RageMeter
    {
        private readonly int _limit;
        private readonly int _calmSeconds;
        private eDamageType _last;
        private int _streak;
        private int _calm;

        public RageMeter(int limit, int calmSeconds)
        {
            _limit = limit;
            _calmSeconds = calmSeconds;
        }

        /// <summary>Counts a blow. True when it sets off a rage.</summary>
        public bool Hit(eDamageType type)
        {
            _streak = type == _last ? _streak + 1 : 1;
            _last = type;
            if (_calm > 0 || _streak < _limit)
                return false;
            _streak = 0;
            _calm = _calmSeconds;
            return true;
        }

        public void Second()
        {
            if (_calm > 0)
                _calm--;
        }
    }

    /// <summary>Oukesson's splitting: every few blows make a clone, but arrows never do.</summary>
    public sealed class SplitMeter
    {
        private readonly int _blows;
        private int _count;

        public SplitMeter(int blows) => _blows = blows;

        /// <summary>Counts a blow. True when it makes a clone.</summary>
        public bool Hit(bool ranged)
        {
            if (ranged)
                return false;
            _count++;
            if (_count < _blows)
                return false;
            _count = 0;
            return true;
        }
    }

    /// <summary>Shared by the ML3 and ML4 trials: placing waves, area effects a pulse cannot shape, and watching blows.</summary>
    public static class Ml34Kit
    {
        public static TrialMobSpec Mob(string name, ushort model, byte level, byte size, int health, double damage, TrialPoint? at = null,
            string tag = null, bool required = true, bool immune = false, int aggro = 1500, eDamageType melee = eDamageType.Crush)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = model,
                Level = level,
                Size = size,
                Health = health,
                DamageFactor = damage,
                At = at,
                Tag = tag,
                Required = required,
                Immune = immune,
                AggroRange = aggro,
                MeleeDamage = melee,
            };
        }

        public static TrialMobSpec Clickable(string name, ushort model, byte size, TrialPoint at, string text, bool required = true)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = model,
                Size = size,
                Level = 50,
                At = at,
                Objective = true,
                ObjectiveText = text,
                Required = required,
            };
        }

        /// <summary>A point on a circle around a centre.</summary>
        public static TrialPoint On(TrialPoint center, int radius, int index, int count)
        {
            double angle = 2 * Math.PI * index / Math.Max(1, count);
            return new TrialPoint(center.X + (int)(radius * Math.Cos(angle)), center.Y + (int)(radius * Math.Sin(angle)), center.Z, center.Heading);
        }

        /// <summary>A point part way from a to b, pushed sideways by offset.</summary>
        public static TrialPoint Along(TrialPoint a, TrialPoint b, double share, int offset)
        {
            double dx = b.X - a.X, dy = b.Y - a.Y;
            double length = Math.Max(1, Math.Sqrt(dx * dx + dy * dy));
            return new TrialPoint(
                (int)(a.X + dx * share - dy / length * offset),
                (int)(a.Y + dy * share + dx / length * offset),
                (int)(a.Z + (b.Z - a.Z) * share));
        }

        /// <summary>Waves shrink with the party, or a lone player meets a raid's adds at a fraction of their health but all of their number.</summary>
        public static int Scaled(int designCount, double healthScale, int minimum = 2) =>
            Math.Max(Math.Min(minimum, designCount), (int)Math.Round(designCount * healthScale, MidpointRounding.AwayFromZero));

        public static void Wave(TrialRun run, TrialMobSpec spec, int designCount, TrialPoint center, int radius)
        {
            int count = Scaled(designCount, run.HealthScale);
            for (int i = 0; i < count; i++)
                run.Spawn(At(spec, On(center, radius, i, count)));
        }

        public static TrialMobSpec At(TrialMobSpec spec, TrialPoint point)
        {
            return new TrialMobSpec
            {
                Name = spec.Name,
                Model = spec.Model,
                Level = spec.Level,
                Size = spec.Size,
                Health = spec.Health,
                DamageFactor = spec.DamageFactor,
                At = point,
                MeleeDamage = spec.MeleeDamage,
                AggroRange = spec.AggroRange,
                Immune = spec.Immune,
                Reflect = spec.Reflect,
                Required = spec.Required,
                Objective = spec.Objective,
                ObjectiveText = spec.ObjectiveText,
                Tag = spec.Tag,
                OnDeath = spec.OnDeath,
            };
        }

        public static Func<TrialRun, bool> Cleared(params string[] tags) => run => !tags.Any(tag => run.Mobs(tag).Any());

        public static TrialMob First(TrialRun run, string tag) => run.Mobs(tag).FirstOrDefault();

        /// <summary>True once every given number of seconds. Call it from a tick, once for each key.</summary>
        public static bool Every(TrialRun run, string key, int seconds)
        {
            int count = run.Get<int>(key) + 1;
            run.Set(key, count);
            return count % seconds == 0;
        }

        public static int HealthPercent(GameLiving living) => living.MaxHealth <= 0 ? 0 : (int)(living.Health * 100L / living.MaxHealth);

        public static TrialPoint Where(GameObject thing) => new(thing.X, thing.Y, thing.Z, thing.Heading);

        public static double Distance(TrialPoint a, TrialPoint b)
        {
            double dx = a.X - b.X, dy = a.Y - b.Y;
            return Math.Sqrt(dx * dx + dy * dy);
        }

        public static bool InRing(double distance, int inner, int outer) => distance >= inner && distance <= outer;

        /// <summary>Everyone in the leader's party, bots too, wherever they stand.</summary>
        public static List<GameLiving> Party(TrialRun run)
        {
            IEnumerable<GameLiving> group = run.Leader.Group?.GetMembersInTheGroup() ?? Enumerable.Empty<GameLiving>();
            return run.Players.Cast<GameLiving>().Concat(group).Distinct()
                .Where(living => living.IsAlive && living.CurrentRegion == run.Starter.CurrentRegion).ToList();
        }

        public static IEnumerable<GameLiving> Ring(TrialRun run, TrialPoint center, int inner, int outer) =>
            Party(run).Where(living => InRing(Distance(Where(living), center), inner, outer));

        /// <summary>Damage scaled as a pulse would be.</summary>
        public static void Hurt(TrialRun run, GameLiving source, IEnumerable<GameLiving> targets, int damage, eDamageType type)
        {
            int scaled = (int)(damage * run.DamageScale);
            foreach (GameLiving target in targets.ToList())
                target.TakeDamage(source, type, scaled, 0);
        }

        /// <summary>For a starter who turns into the monster: she leaves while the run lasts and comes back with the next.</summary>
        public static void HideStarter(TrialRun run)
        {
            TrialStarter starter = run.Starter;
            ushort model = starter.Model;
            GameNPC.eFlags flags = starter.Flags;
            starter.Model = InvisibleModel;
            starter.Flags = flags | GameNPC.eFlags.CANTTARGET;
            new ECSGameTimer(starter, timer =>
            {
                if (starter.Run != null)
                    return 1000;
                starter.Model = model;
                starter.Flags = flags;
                return 0;
            }, 1000);
        }

        public const ushort InvisibleModel = 666;

        /// <summary>Attacks arrive on other threads, so they queue here until <see cref="TakeHits"/> on the tick.</summary>
        public static void WatchHits(TrialRun run, TrialMob mob, string key)
        {
            ConcurrentQueue<TrialHit> hits = new();
            run.Set(key, hits);
            GameEventMgr.AddHandler(mob, GameLivingEvent.AttackedByEnemy, (e, sender, arguments) =>
            {
                if (arguments is AttackedByEnemyEventArgs { AttackData: { } attack })
                    hits.Enqueue(new TrialHit(attack.DamageType, attack.AttackType, attack.Damage + attack.CriticalDamage));
            });
        }

        public static List<TrialHit> TakeHits(TrialRun run, string key)
        {
            List<TrialHit> taken = new();
            ConcurrentQueue<TrialHit> hits = run.Get<ConcurrentQueue<TrialHit>>(key);
            while (hits != null && hits.TryDequeue(out TrialHit hit))
                taken.Add(hit);
            return taken;
        }

        public static void MoveParty(TrialRun run, TrialPoint point)
        {
            List<GameLiving> party = Party(run);
            for (int i = 0; i < party.Count; i++)
            {
                TrialPoint spot = On(point, 120, i, party.Count);
                party[i].MoveTo(run.Starter.CurrentRegionID, spot.X, spot.Y, spot.Z, spot.Heading);
            }
        }
    }
}
