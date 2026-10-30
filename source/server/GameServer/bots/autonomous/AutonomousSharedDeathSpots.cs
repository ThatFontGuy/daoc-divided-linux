using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS;

/// <summary>
/// The realm's word of mouth about deadly roads: where monsters killed <see cref="SpotDeaths"/> or more gamebots,
/// at least <see cref="DistinctBots"/> different ones, within <see cref="ClusterRadius"/> in the last
/// <see cref="Lifetime"/>. A bot bends its open-world routes around the spots where bots of its level or lower died,
/// as players warn each other about a pack on the road. <see cref="AutonomousRepeatDeathSpots"/> is each bot's own
/// memory; this one is shared, so the next bot does not have to die there three times first.
///
/// 2026-10-27 run: 69% of 7,810 gamebot deaths came on the way to a camp, the top killers being ordinary level 6-10
/// roadside monsters near the starting towns (pixie scout, small hill cat, hill cat, bandit, roaming dirge), which
/// neither the far-above bypass nor the per-bot memory reached in time. Routes only: camps keep their own bench.
/// In memory only: a restart forgets.
/// </summary>
public static class AutonomousSharedDeathSpots
{
    public const int SpotDeaths = 5;
    public const int DistinctBots = 3;
    public const float ClusterRadius = 1_200;
    /// <summary>A death counts for bots up to this many levels above the one that died.</summary>
    public const int LevelsAboveVictim = 3;
    public static readonly TimeSpan Lifetime = TimeSpan.FromHours(2);
    private const int MaximumDeaths = 6_000;
    private static readonly TimeSpan CacheLifetime = TimeSpan.FromSeconds(60);

    public readonly record struct Death(long BotId, int Level, ushort RegionId, int X, int Y, DateTime Utc);

    private static readonly ConcurrentQueue<Death> Deaths = new();
    private static readonly ConcurrentDictionary<(ushort Region, int Level), (DateTime At, List<(int X, int Y)> Spots)> Cache = new();

    public static void Record(long botId, int level, ushort regionId, int x, int y, DateTime utc)
    {
        Deaths.Enqueue(new Death(botId, level, regionId, x, y, utc));
        while (Deaths.Count > MaximumDeaths && Deaths.TryDequeue(out _)) { }
    }

    /// <summary>
    /// Pure rule: the spots (latest death of each cluster) in a region that a bot of this level should avoid: enough
    /// recent deaths of enough different bots at or below <paramref name="level"/> + <see cref="LevelsAboveVictim"/>.
    /// </summary>
    public static List<(int X, int Y)> Spots(IEnumerable<Death> deaths, ushort regionId, int level, DateTime utc)
    {
        Death[] recent = (deaths ?? []).Where(death => death.RegionId == regionId && utc - death.Utc <= Lifetime &&
                                                        level <= death.Level + LevelsAboveVictim)
            .OrderByDescending(death => death.Utc).ToArray();
        var spots = new List<(int X, int Y)>();
        foreach (Death death in recent)
        {
            if (spots.Any(spot => Distance(spot.X, spot.Y, death.X, death.Y) <= ClusterRadius)) continue;
            Death[] cluster = recent.Where(other => Distance(other.X, other.Y, death.X, death.Y) <= ClusterRadius).ToArray();
            if (cluster.Length >= SpotDeaths && cluster.Select(other => other.BotId).Distinct().Count() >= DistinctBots)
                spots.Add((death.X, death.Y));
        }
        return spots;
    }

    /// <summary>The spots within <paramref name="radius"/> of a point for a bot of this level, for route bends.</summary>
    public static List<(int X, int Y)> SpotsNear(ushort regionId, int level, int x, int y, DateTime utc, float radius)
    {
        var key = (regionId, level);
        if (!Cache.TryGetValue(key, out var cached) || utc - cached.At > CacheLifetime)
        {
            cached = (utc, Spots(Deaths.ToArray(), regionId, level, utc));
            Cache[key] = cached;
        }
        return cached.Spots.Where(spot => Distance(spot.X, spot.Y, x, y) <= radius).ToList();
    }

    private static double Distance(int ax, int ay, int bx, int by)
    {
        double dx = (double)ax - bx, dy = (double)ay - by;
        return Math.Sqrt(dx * dx + dy * dy);
    }

    /// <summary>Tests only.</summary>
    public static void Clear()
    {
        Deaths.Clear();
        Cache.Clear();
    }
}
