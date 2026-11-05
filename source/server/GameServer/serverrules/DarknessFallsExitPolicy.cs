using System.Collections.Generic;
using System.Linq;
using DOL.Database;

namespace DOL.GS.ServerRules;

/// <summary>
/// The eight Darkness Falls exit IDs each have one destination row per realm (zonejump.csv in dat249.mpk:
/// 71 MidBoss and 77 LordExit, by Legion's hall, had no rows until 2026-11-03).
/// Even a GM must use the row for their character's realm; an ID-only lookup
/// otherwise picks whichever realm happens to be first in the database.
/// </summary>
public static class DarknessFallsExitPolicy
{
    public const ushort RegionId = 249;

    public static bool IsExitRequest(ushort currentRegion, ushort zonePointId) =>
        currentRegion == RegionId && zonePointId is >= 70 and <= 77;

    public static ushort HomeRegion(eRealm realm) => realm switch
    {
        eRealm.Albion => 1,
        eRealm.Midgard => 100,
        eRealm.Hibernia => 200,
        _ => 0,
    };

    public static DbZonePoint SelectRealmExit(IEnumerable<DbZonePoint> rows, eRealm realm, ushort zonePointId)
    {
        ushort home = HomeRegion(realm);
        if (home == 0 || rows == null)
            return null;

        return rows.FirstOrDefault(point => point != null && point.Id == zonePointId &&
            IsExitRequest(point.SourceRegion, point.Id) &&
            point.Realm == (ushort)realm && point.TargetRegion == home);
    }
}
