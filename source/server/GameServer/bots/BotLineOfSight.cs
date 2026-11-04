using System.Runtime.CompilerServices;

namespace DOL.GS
{
    /// <summary>
    /// Owner 2026-10-31: the bots (companions and gamebots alike) shot spells through the walls of the keeps. A cast at a player is
    /// checked by that player's client (NpcCastingComponent.GetLosChecker); a cast at anything else, a bot, a guard, a monster, went
    /// ahead with no check at all. A harmful cast at a target that is not a player now needs a clear navmesh line to it, and a bot
    /// that is in range but has no line goes on approaching (BotBrain.ApproachForOffensiveSpell). The answer is kept for a moment per
    /// caster and target so that the ray is not cast on every decision.
    /// </summary>
    public static class BotLineOfSight
    {
        /// <summary>Closer than this the target counts as in view whatever the ray says (a ray may graze the mesh edge).</summary>
        public const int AlwaysInViewDistance = 150;
        public const long CacheMilliseconds = 750;
        private const int EyeHeight = 48;

        private sealed class Entry { public int TargetId; public long Tick; public bool Blocked; }
        private static readonly ConditionalWeakTable<GameLiving, Entry> Cache = new();

        /// <summary>
        /// Whether a line of sight is worth checking: a target that is not a player (a player's own client answers), not too close,
        /// in the caster's zone.
        /// </summary>
        public static bool ShouldCheck(bool targetIsPlayer, int distance, bool sameZone) =>
            !targetIsPlayer && sameZone && distance > AlwaysInViewDistance;

        /// <summary>True when a harmful cast from <paramref name="caster"/> at <paramref name="target"/> must not go ahead for want of a line of sight.</summary>
        public static bool Blocks(GameLiving caster, GameObject target)
        {
            if (caster == null || target is not GameLiving living || living == caster)
                return false;
            if (!ShouldCheck(target is GamePlayer, caster.GetDistanceTo(living), caster.CurrentZone != null && caster.CurrentZone == living.CurrentZone))
                return false;

            long now = GameLoop.GameLoopTime;
            Entry entry = Cache.GetOrCreateValue(caster);
            if (entry.TargetId == living.ObjectID && now - entry.Tick < CacheMilliseconds)
                return entry.Blocked;

            bool blocked = false;
            var nav = PathfindingProvider.Instance;
            if (nav.IsAvailable && nav.HasNavmesh(caster.CurrentZone))
                blocked = !nav.HasLineOfSight(caster.CurrentZone, new(caster.X, caster.Y, caster.Z + EyeHeight),
                    new(living.X, living.Y, living.Z + EyeHeight), nav.DefaultFilters);
            entry.TargetId = living.ObjectID;
            entry.Tick = now;
            entry.Blocked = blocked;
            return blocked;
        }
    }
}
