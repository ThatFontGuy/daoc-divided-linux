using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Numerics;

namespace DOL.GS
{
    /// <summary>
    /// A zone crossing that several different bots walked to and could not reach is skipped by the zone planner for a
    /// while. The corridor check can prove a crossing from far off while the bot's own walk ends on the wrong side of
    /// a thin wall: Valley of Bri Leith's crossings into Lough Derg at 385088,486624 lie 70 units past a wall from the
    /// strip the walk arrives on (the two sides join 85,000 units away), and Hibernian bots gave up there 408 times on
    /// 2026-10-30. Nothing in the world changes; the crossing is planned again once the bench expires.
    /// </summary>
    public static class AutonomousSeamCrossingQuarantine
    {
        public const int DistinctBotsToQuarantine = 3;
        public const int Cell = 512;
        public static readonly TimeSpan FailureWindow = TimeSpan.FromMinutes(30);
        public static readonly TimeSpan QuarantineDuration = TimeSpan.FromHours(2);

        private sealed class Record
        {
            public readonly object Gate = new();
            public readonly Dictionary<long, DateTime> FailedBots = new();
            public DateTime QuarantinedUntilUtc;
        }

        private static readonly ConcurrentDictionary<(ushort Region, int X, int Y), Record> Records = new();
        private static int _quarantines;

        private static (ushort, int, int) Key(ushort region, Vector3 inside) =>
            (region, (int)MathF.Floor(inside.X / Cell), (int)MathF.Floor(inside.Y / Cell));

        /// <summary>Returns true when this report benched the crossing.</summary>
        public static bool ReportFailure(ushort region, Vector3 inside, long botId, DateTime? nowUtc = null)
        {
            if (botId <= 0)
                return false;
            DateTime now = nowUtc ?? DateTime.UtcNow;
            Record record = Records.GetOrAdd(Key(region, inside), _ => new Record());
            lock (record.Gate)
            {
                if (record.QuarantinedUntilUtc > now)
                    return false;
                record.FailedBots[botId] = now;
                List<long> stale = null;
                foreach (KeyValuePair<long, DateTime> pair in record.FailedBots)
                    if (now - pair.Value > FailureWindow)
                        (stale ??= new()).Add(pair.Key);
                if (stale != null)
                    foreach (long id in stale)
                        record.FailedBots.Remove(id);
                if (record.FailedBots.Count < DistinctBotsToQuarantine)
                    return false;
                record.FailedBots.Clear();
                record.QuarantinedUntilUtc = now + QuarantineDuration;
                System.Threading.Interlocked.Increment(ref _quarantines);
                return true;
            }
        }

        /// <summary>Planner check; free until any crossing has ever been benched.</summary>
        public static bool IsQuarantined(ushort region, Vector3 inside, DateTime? nowUtc = null) =>
            System.Threading.Volatile.Read(ref _quarantines) > 0 && Records.TryGetValue(Key(region, inside), out Record record) &&
            record.QuarantinedUntilUtc > (nowUtc ?? DateTime.UtcNow);

        /// <summary>Tools and tests: bench a crossing at once.</summary>
        public static void Quarantine(ushort region, Vector3 inside, DateTime? nowUtc = null)
        {
            Records.GetOrAdd(Key(region, inside), _ => new Record()).QuarantinedUntilUtc = (nowUtc ?? DateTime.UtcNow) + QuarantineDuration;
            System.Threading.Interlocked.Increment(ref _quarantines);
        }

        public static void ResetForTests()
        {
            Records.Clear();
            _quarantines = 0;
        }
    }
}
