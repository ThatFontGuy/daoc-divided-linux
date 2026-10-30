using System;
using System.Linq;

namespace DOL.GS
{
    /// <summary>Execution of an assigned PvE goal, separate from difficulty planning.</summary>
    public static class AutonomousPveTargetPolicy
    {
        // The caller separately checks life, region, attack legality and route.
        // Any real monster level is allowed, including grey or purple targets
        // and level 0 creatures (blue to a level 1; used by starter camps).
        public static bool IsAssignedTarget(string assignedName, string monsterName, int monsterLevel) =>
            monsterLevel >= 0 && !string.IsNullOrWhiteSpace(assignedName) &&
            string.Equals(assignedName, monsterName, StringComparison.OrdinalIgnoreCase);

        /// <summary>
        /// Camp catalog input without monsters that have no zone. One such monster made the whole catalog
        /// draft throw, so every bot stayed in "Searching for a valid XP camp" (found by MoomoocowPlus's fork,
        /// 2026-10-18; our own logs show zoneless spawns such as ColialtAdds' ancient zombies).
        /// </summary>
        public static T[] WithZone<T>(T[] monsters, Func<T, Zone> zoneOf) where T : class =>
            monsters?.Where(monster => monster != null && zoneOf(monster) != null).ToArray() ?? [];

        /// <summary>Vertical gap beyond which a flying monster cannot be pulled from the bot's floor.</summary>
        public const int UnreachableFlyerHeight = 400;

        // Flying spawns such as the Gripklosa griffon gliders hover thousands of
        // units over the camp floor: melee could never reach them and pulls timed
        // out (1,195 times in one run). Low flyers (lights, elementals) still count.
        // A high flyer that attacks the bot is fought normally by its defense.
        public static bool IsUnreachableFlyer(GameNPC.eFlags flags, int monsterZ, int botZ) =>
            (flags & GameNPC.eFlags.FLYING) != 0 && Math.Abs(monsterZ - botZ) > UnreachableFlyerHeight;

        /// <summary>How long a bot may "fight" a high flyer with no blow landed or taken before letting it go.</summary>
        public const long UnreachableFlyerAggroDropMilliseconds = 30_000;

        // Defense used to fight an aggressive high flyer "normally", but neither side could reach the
        // other: the 2026-10-19 soak had 19 of 47 fifteen-minute rescues standing under Gripklosa griffon
        // gliders ("Fighting griffon glider"). Any landed or received blow, or lost target health, is a
        // real fight and restarts the watch.
        /// <summary>
        /// Something hit the bot, or the target lost health while the bot itself was fighting. Health lost to a pet
        /// alone does not count: in the overnight 2026-10-20 soak all 20 remaining griffon-glider rescues were
        /// Spiritmasters and Hunters out of combat (inCombat=False, aggro=True), their pets nicking a glider the
        /// owner could never reach, which kept resetting the watch.
        /// </summary>
        public static bool FlyerFightContact(long initialAttackedTick, long attackedTick, int initialTargetHealth, int targetHealth,
            bool ownerFighting) =>
            attackedTick > initialAttackedTick || ownerFighting && targetHealth < initialTargetHealth;

        public static bool ShouldDropUnreachableFlyer(bool unreachableFlyer, bool contactSinceWatch,
            long watchedSinceTick, long nowTick) =>
            unreachableFlyer && !contactSinceWatch && nowTick - watchedSinceTick >= UnreachableFlyerAggroDropMilliseconds;

        /// <summary>How long any other PvE monster may be "fought" with no damage either way.</summary>
        public const long StaleFightDropMilliseconds = 60_000;

        // The same soak had 42 rescues "Fighting Lieutenant Meade": a Hall of the Corrupt boss that takes
        // no damage outside his tether, with the bots stood 1,500 units off. No damage either way for a
        // minute is not a fight. RvR targets are never judged by this rule.
        public static bool ShouldDropStaleFight(bool pveTarget, bool unreachableFlyer, bool contactSinceWatch,
            long watchedSinceTick, long nowTick)
        {
            if (!pveTarget || contactSinceWatch) return false;
            long limit = unreachableFlyer ? UnreachableFlyerAggroDropMilliseconds : StaleFightDropMilliseconds;
            return nowTick - watchedSinceTick >= limit;
        }

        // The height gap alone let low-hovering gliders over a cliff edge through:
        // on 2026-10-18 a level 50 Midgard melee group timed out on them 45 times
        // from 2,400-3,500 units away and one member stood still for 15 minutes
        // (group camps never abandon on unreachable pulls). A bot that can't hit
        // from range must prove a ground approach to a flyer before choosing it;
        // casters and archers shoot it as before.
        public static bool MustProveFlyerApproach(GameNPC.eFlags flags, bool canPullFromRange) =>
            (flags & GameNPC.eFlags.FLYING) != 0 && !canPullFromRange;

        /// <summary>How far a caster or archer may be from a flyer it picks: it can't walk up to one in the air.</summary>
        public const int RangedFlyerPullDistance = 1450;

        // Overnight 2026-10-19 the melee timeouts were gone, but casters took over: a level 50 Runemaster picked
        // gliders 2,900-3,100 units away, never moved closer (there is no ground path to a point in the air) and
        // timed out 86 times. A ranged bot now only picks a flyer it can already shoot.
        public static bool FlyerOutOfRangedReach(GameNPC.eFlags flags, bool canPullFromRange, double distance) =>
            (flags & GameNPC.eFlags.FLYING) != 0 && canPullFromRange && distance > RangedFlyerPullDistance;
    }
}
