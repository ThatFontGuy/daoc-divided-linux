using System;
using System.Collections.Generic;
using System.Linq;
using DOL.AI.Brain;

namespace DOL.GS.Trials
{
    /// <summary>Hook helpers shared by the Master Level 1 and 2 trials.</summary>
    internal static class Ml12Kit
    {
        /// <summary>A spot on a circle around a point, used to stand several things apart.</summary>
        public static TrialPoint Ring(TrialPoint center, int radius, int index, int count)
        {
            double angle = 2 * Math.PI * index / Math.Max(1, count);
            return new TrialPoint(center.X + (int)Math.Round(radius * Math.Cos(angle)), center.Y + (int)Math.Round(radius * Math.Sin(angle)), center.Z, center.Heading);
        }

        public static IEnumerable<TrialMobSpec> Circle(TrialPoint center, int radius, int count, Func<TrialPoint, TrialMobSpec> make) =>
            Enumerable.Range(0, count).Select(index => make(Ring(center, radius, index, count)));

        public static bool Near(int x, int y, TrialPoint point, int radius)
        {
            long dx = x - point.X;
            long dy = y - point.Y;
            return dx * dx + dy * dy <= (long)radius * radius;
        }

        /// <summary>True on every nth call for this key. Hooks run once a second, so n is seconds.</summary>
        public static bool Every(TrialRun run, string key, int seconds)
        {
            int ticks = run.Get(key, 0) + 1;
            run.Set(key, ticks);
            return ticks % seconds == 0;
        }

        public static int Scaled(TrialRun run, int damage) => (int)(damage * run.DamageScale);

        public static void Strike(TrialRun run, GameLiving source, GameLiving target, int damage, eDamageType type) =>
            target.TakeDamage(source, type, Scaled(run, damage), 0);

        /// <summary>Area damage on demand, for blasts that do not fit a fixed <see cref="TrialPulse"/>.</summary>
        public static void Burst(TrialRun run, GameLiving source, GameObject center, int radius, int damage, eDamageType type, Func<GameLiving, bool> spared = null)
        {
            foreach (GameLiving target in run.Hostiles(center, radius).Where(target => spared == null || !spared(target)))
                Strike(run, source, target, damage, type);
        }

        public static GameLiving RandomHostile(TrialRun run, GameObject center, int radius)
        {
            List<GameLiving> hostiles = run.Hostiles(center, radius).ToList();
            return hostiles.Count == 0 ? null : hostiles[Util.Random(hostiles.Count - 1)];
        }

        /// <summary>Takes a share of a monster's full health, past any immunity. Kills it at zero.</summary>
        public static void Wound(TrialRun run, TrialMob mob, double share)
        {
            int left = mob.Health - (int)(mob.MaxHealth * share);
            if (left > 0)
            {
                mob.Health = left;
                return;
            }
            mob.Health = 0;
            mob.Die(run.Starter);
        }

        public static void Heal(TrialMob mob, double share) =>
            mob.Health = Math.Min(mob.MaxHealth, mob.Health + (int)(mob.MaxHealth * share));

        public static void HealAll(TrialRun run, string tag, double share)
        {
            foreach (TrialMob mob in run.Mobs(tag))
                Heal(mob, share);
        }

        /// <summary>Plants monsters where they stand.</summary>
        public static void Fix(TrialRun run, string tag)
        {
            foreach (TrialMob mob in run.Mobs(tag))
                mob.MaxSpeedBase = 0;
        }

        /// <summary>Makes passive monsters start looking for targets.</summary>
        public static void Wake(TrialRun run, string tag, int range)
        {
            foreach (TrialMob mob in run.Mobs(tag))
            {
                if (mob.Brain is StandardMobBrain brain)
                    brain.AggroRange = range;
            }
        }

        /// <summary>Only for monsters that are not required, or in phases with their own Done: a deleted monster still counts as alive.</summary>
        public static void Clear(TrialRun run, string tag)
        {
            foreach (TrialMob mob in run.Mobs(tag).ToList())
                mob.Delete();
        }

        /// <summary>Moves the party, standing apart. The temple's gates have no door rows, so chambers are entered this way.</summary>
        public static void MoveParty(TrialRun run, TrialPoint to)
        {
            List<GameLiving> party = run.Definition.Scope == TrialScope.Solo || run.Leader.Group == null
                ? new List<GameLiving> { run.Leader }
                : run.Leader.Group.GetMembersInTheGroup();

            for (int i = 0; i < party.Count; i++)
            {
                GameLiving member = party[i];
                if (!member.IsAlive || !member.IsWithinRadius(run.Starter, run.Definition.LeashRange))
                    continue;
                TrialPoint spot = party.Count > 1 ? Ring(to, 120, i, party.Count) : to;
                member.MoveTo(run.Starter.CurrentRegionID, spot.X, spot.Y, spot.Z, spot.Heading);
            }
        }
    }
}
