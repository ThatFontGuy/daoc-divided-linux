using System;
using System.Collections.Concurrent;
using System.Collections.Generic;

namespace DOL.GS
{
    /// <summary>
    /// Zone crossings a realm's bots could not plan, shared by the whole realm so the camp planner
    /// stops choosing camps behind them. In the modern world Albion's four old frontier zones
    /// (Pennine Mountains, Forest Sauvage, Snowdonia, Hadrian's Wall) are walled off from the
    /// homeland, but the camp catalog still lists their camps: on 2026-10-28, 2,623 Albion goals
    /// ended "No safe connected zone seam" and not one Albion goal in those zones was productive.
    /// Each bot only remembered the one camp for 30 minutes, so the same bots failed about 25 times.
    /// A crossing is blocked once several different bots fail it; a destination zone is blocked from
    /// anywhere in the region once it has failed from several different start zones. Nothing in the
    /// world changes, and every block expires, so a world that is fixed is used again.
    /// </summary>
    public static class AutonomousZoneSeamBlocks
    {
        public const int DistinctBotsToBlock = 3;
        public const int DistinctStartZonesToBlockDestination = 2;
        public static readonly TimeSpan FailureWindow = TimeSpan.FromMinutes(60);
        public static readonly TimeSpan BlockDuration = TimeSpan.FromHours(3);

        private sealed class Record
        {
            public readonly Dictionary<long, DateTime> FailedBots = new();
            public DateTime BlockedUntilUtc;
        }

        private readonly record struct PairKey(eRealm Realm, ushort Region, ushort From, ushort To);
        private readonly record struct DestinationKey(eRealm Realm, ushort Region, ushort To);

        private static readonly object Gate = new();
        private static readonly Dictionary<PairKey, Record> Pairs = new();
        private static readonly ConcurrentDictionary<DestinationKey, DateTime> Destinations = new();
        private static int _blocks;

        /// <summary>Returns true when this report blocked the crossing.</summary>
        public static bool ReportFailure(eRealm realm, ushort regionId, ushort fromZone, ushort toZone, long botId,
            DateTime? nowUtc = null)
        {
            if (regionId == 0 || fromZone == toZone || botId <= 0)
                return false;
            DateTime now = nowUtc ?? DateTime.UtcNow;
            PairKey key = new(realm, regionId, fromZone, toZone);
            lock (Gate)
            {
                if (!Pairs.TryGetValue(key, out Record record))
                    Pairs[key] = record = new Record();
                if (record.BlockedUntilUtc > now)
                    return false;
                record.FailedBots[botId] = now;
                List<long> stale = null;
                foreach (KeyValuePair<long, DateTime> pair in record.FailedBots)
                    if (now - pair.Value > FailureWindow)
                        (stale ??= new()).Add(pair.Key);
                if (stale != null)
                    foreach (long id in stale)
                        record.FailedBots.Remove(id);
                if (record.FailedBots.Count < DistinctBotsToBlock)
                    return false;
                record.FailedBots.Clear();
                record.BlockedUntilUtc = now + BlockDuration;
                System.Threading.Interlocked.Increment(ref _blocks);

                int startZones = 0;
                foreach (KeyValuePair<PairKey, Record> pair in Pairs)
                    if (pair.Key.Realm == realm && pair.Key.Region == regionId && pair.Key.To == toZone &&
                        pair.Value.BlockedUntilUtc > now)
                        startZones++;
                if (startZones >= DistinctStartZonesToBlockDestination)
                    Destinations[new(realm, regionId, toZone)] = now + BlockDuration;
                return true;
            }
        }

        /// <summary>
        /// For the camp planner: true when a camp in <paramref name="toZone"/> should not be chosen by a bot of
        /// this realm standing in <paramref name="fromZone"/> (0 when the bot is in another region). Free until
        /// any crossing has ever been blocked.
        /// </summary>
        public static bool IsBlocked(eRealm realm, ushort regionId, ushort fromZone, ushort toZone, DateTime? nowUtc = null)
        {
            if (System.Threading.Volatile.Read(ref _blocks) == 0 || fromZone == toZone && fromZone != 0)
                return false;
            DateTime now = nowUtc ?? DateTime.UtcNow;
            if (Destinations.TryGetValue(new(realm, regionId, toZone), out DateTime until) && until > now)
                return true;
            if (fromZone == 0)
                return false;
            lock (Gate)
                return Pairs.TryGetValue(new(realm, regionId, fromZone, toZone), out Record record) &&
                    record.BlockedUntilUtc > now;
        }

        public static bool IsDestinationBlocked(eRealm realm, ushort regionId, ushort toZone, DateTime? nowUtc = null) =>
            Destinations.TryGetValue(new(realm, regionId, toZone), out DateTime until) && until > (nowUtc ?? DateTime.UtcNow);

        public static void ResetForTests()
        {
            lock (Gate)
                Pairs.Clear();
            Destinations.Clear();
            _blocks = 0;
        }
    }
}
