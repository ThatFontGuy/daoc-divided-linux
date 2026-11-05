using System;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS;

/// <summary>
/// Ordinary XP camps belong to the realm whose frontier contains them. The
/// frontier itself remains traversable for RvR, defence and realm events;
/// those activities must not use this PvE-only assignment gate.
/// </summary>
public static class AutonomousOrdinaryPveRealmPolicy
{
    public static bool CanAssignCamp(eRealm botRealm, ushort regionId, ushort zoneId)
    {
        eRealm frontierOwner = (regionId, zoneId) switch
        {
            (1, 11 or 12 or 14 or 15) => eRealm.Albion,
            (100, 111 or 112 or 113 or 115) => eRealm.Midgard,
            (200, 210 or 211 or 212 or 214) => eRealm.Hibernia,
            _ => eRealm.None
        };

        // Other regions, including the shared Darkness Falls region, continue
        // through the existing realm, dungeon and navmesh access policies.
        return frontierOwner == eRealm.None || frontierOwner == botRealm;
    }

    /// <summary>The Shrouded Isles regions (Albion, Midgard, Hibernia).</summary>
    public static bool IsShroudedIsles(ushort regionId) => regionId is 51 or 151 or 181;

    /// <summary>
    /// The lowest level (the bot's, or its party's average) that takes XP camps in the Shrouded Isles.
    /// 2026-10-19: level-1 Midgard parties were sent to level 5-11 camps in Aegir's Landing; scimitar cats
    /// (levels 18-21) that roam there killed level-1 bots 201 times in three hours, mostly on the walk from
    /// the Aegirhamn bind to the party's meetup. Below this level a bot takes only a camp on the home shore
    /// (<see cref="IsNewbieShoreCamp"/>), and otherwise levels in its realm's classic zones.
    /// </summary>
    public const int ShroudedIslesMinimumLevel = 10;

    /// <summary>How far from a Shrouded Isles town or its portal arrival a home shore camp may lie.</summary>
    public const int NewbieShoreRadius = 18_000;

    /// <summary>How far an aggressive level 10+ monster must stay from the walk to a home shore camp.</summary>
    public const int NewbieShoreWalkClearance = 3_000;

    /// <summary>How far any aggressive monster must stay from a home shore camp.</summary>
    public const int NewbieShoreCampClearance = 1_500;

    // The town each realm's new characters start in, then the arrival of the portal from the classic zones.
    private static (int X, int Y)[] ShoreStarts(ushort regionId) => regionId switch
    {
        51 => [(535083, 549087), (525818, 542658)],
        151 => [(289036, 355681), (294206, 355969)],
        181 => [(425066, 445632), (423803, 439910)],
        _ => []
    };

    /// <summary>
    /// A Shrouded Isles camp a new bot can use: every spawn under level 10, near town, no aggressive monster at the camp,
    /// and no aggressive level 10+ monster beside the straight walk from town. Owner 2026-11-01: these shores hold real
    /// newbie camps; a database count that day found 23 in Midgard, 40 in Albion and 57 in Hibernia.
    /// </summary>
    public static bool IsNewbieShoreCamp(ushort regionId, int x, int y, IReadOnlyCollection<int> levels,
        IEnumerable<(int X, int Y, int Level)> aggressive)
    {
        if (levels.Count == 0 || levels.Max() >= ShroudedIslesMinimumLevel)
            return false;
        (int X, int Y)[] starts = ShoreStarts(regionId);
        if (starts.Length == 0)
            return false;
        (int X, int Y) start = starts.MinBy(point => Distance(point.X, point.Y, x, y));
        if (Distance(start.X, start.Y, x, y) > NewbieShoreRadius)
            return false;
        foreach ((int X, int Y, int Level) spawn in aggressive)
        {
            if (Distance(spawn.X, spawn.Y, x, y) < NewbieShoreCampClearance)
                return false;
            if (spawn.Level >= ShroudedIslesMinimumLevel &&
                DistanceToWalk(spawn.X, spawn.Y, start.X, start.Y, x, y) < NewbieShoreWalkClearance)
                return false;
        }
        return true;
    }

    private static double Distance(double ax, double ay, double bx, double by) =>
        Math.Sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by));

    private static double DistanceToWalk(int px, int py, int ax, int ay, int bx, int by)
    {
        double dx = bx - ax, dy = by - ay, length = dx * dx + dy * dy;
        double along = length == 0 ? 0 : Math.Clamp(((px - ax) * dx + (py - ay) * dy) / length, 0, 1);
        return Distance(px, py, ax + along * dx, ay + along * dy);
    }

    public static bool CanAssignCamp(eRealm botRealm, ushort regionId, ushort zoneId, int planningLevel, bool newbieShore = false) =>
        (!AutonomousAtlantisPolicy.IsAtlantisRegion(regionId) ||
         AutonomousAtlantisPolicy.CanHuntHere(botRealm, regionId, planningLevel)) &&
        CanAssignCamp(botRealm, regionId, zoneId) &&
        (planningLevel >= ShroudedIslesMinimumLevel || newbieShore || !IsShroudedIsles(regionId));
}
