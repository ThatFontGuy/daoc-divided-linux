using System;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS.Trials
{
    /// <summary>Small building blocks shared by the Master Level 7 and 8 trials.</summary>
    public static class Ml7Kit
    {
        public static TrialMobSpec Foe(string name, ushort model, byte level, byte size, int health, double damage, TrialPoint at, string tag = null, eDamageType melee = eDamageType.Crush, bool required = true) => new()
        {
            Name = name,
            Model = model,
            Level = level,
            Size = size,
            Health = health,
            DamageFactor = damage,
            At = at,
            Tag = tag,
            MeleeDamage = melee,
            Required = required,
        };

        /// <summary>A clickable that leaves the world once used, so nothing stands beside the fight it opens.</summary>
        public static TrialMobSpec Clickable(string name, ushort model, byte size, TrialPoint at, string text, string tag = null, Action<TrialRun, TrialMob> then = null) => new()
        {
            Name = name,
            Model = model,
            Size = size,
            Level = 60,
            Health = 100,
            At = at,
            Objective = true,
            ObjectiveText = text,
            Tag = tag,
            OnDeath = (run, mob) =>
            {
                mob.Delete();
                then?.Invoke(run, mob);
            },
        };

        public static IEnumerable<TrialMobSpec> AtEach(IEnumerable<TrialPoint> points, Func<TrialPoint, TrialMobSpec> make) => points.Select(make);

        public static IEnumerable<TrialPoint> Circle(TrialPoint center, int radius, int count)
        {
            for (int i = 0; i < count; i++)
            {
                double angle = 2 * Math.PI * i / count;
                yield return new TrialPoint(center.X + (int)Math.Round(radius * Math.Cos(angle)), center.Y + (int)Math.Round(radius * Math.Sin(angle)), center.Z);
            }
        }

        public static bool Gone(TrialRun run, string tag) => !run.Mobs(tag).Any();

        /// <summary>Counts seconds under a key and returns the new count.</summary>
        public static int Count(TrialRun run, string key)
        {
            int value = run.Get(key, 0) + 1;
            run.Set(key, value);
            return value;
        }

        public static bool Near(GameObject who, TrialPoint point, int radius) =>
            Math.Abs(who.X - point.X) <= radius && Math.Abs(who.Y - point.Y) <= radius;

        public static void Relocate(TrialRun run, TrialMob mob, TrialPoint point) =>
            mob.MoveTo(run.Starter.CurrentRegionID, point.X, point.Y, point.Z, point.Heading);

        /// <summary>Moves the leader, the group and its bots. A dead bot stays where it fell.</summary>
        public static void MoveParty(TrialRun run, TrialPoint point)
        {
            IEnumerable<GameLiving> party = run.Players.Cast<GameLiving>();
            if (run.Leader.Group != null)
                party = party.Concat(run.Leader.Group.GetMembersInTheGroup());

            foreach (GameLiving member in party.Distinct().ToList())
                member.MoveTo(run.Starter.CurrentRegionID, point.X, point.Y, point.Z, point.Heading);
        }

        public static void Resist(TrialMob mob, int amount, params eProperty[] resists)
        {
            foreach (eProperty resist in resists)
                mob.OtherBonus[resist] = amount;
        }

        /// <summary>How many of the falling health marks have been passed at this percent.</summary>
        public static int MarksPassed(int healthPercent, params int[] marks) => marks.Count(mark => healthPercent <= mark);
    }
}
