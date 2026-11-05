using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using DOL.Database;

namespace DOL.GS;

/// <summary>
/// Gamebots in Atlantis. Each realm has its own copy of the world (Albion 73, Midgard 30, Hibernia 130), and bots
/// use only theirs. Players reach it through the capital teleporter and a Hall of Atlantis, but the Halls have no
/// usable navmesh and a persistent bot pauses on a zone without one. So the capital teleporter and the Hesperos
/// portal join directly here, as the zone point edges every bot route already follows.
/// Sea monsters stay out of camps: bots walk the mesh, which is a sheet on the surface.
/// </summary>
public static class AutonomousAtlantisPolicy
{
    /// <summary>
    /// Most land spawns are level 45 and up. Below this a party would cross the world to monsters it can't fight.
    /// </summary>
    public const int MinimumLevel = 45;
    public const int CampMinimumMembers = 3;
    private const ushort FirstGatewayId = 60_000;

    private readonly record struct Gateway(eRealm Realm, ushort Capital, int CapitalX, int CapitalY, int CapitalZ,
        ushort Atlantis, int PortalX, int PortalY, int PortalZ);

    // The capital spots are the realm's teleporter; the portal spots are the Hesperos exits to the Halls.
    private static readonly Gateway[] Gateways =
    [
        new(eRealm.Albion, 10, 36039, 30870, 8001, 73, 274228, 534289, 8637),
        new(eRealm.Midgard, 101, 31600, 35735, 8002, 30, 274179, 534341, 8646),
        new(eRealm.Hibernia, 201, 33418, 31180, 7999, 130, 274176, 534359, 8637),
    ];

    private const int ArrivalX = 274175;
    private const int ArrivalY = 534600;
    private const int ArrivalZ = 8727;

    // Djinn stones stand at these four havens. The other Djinn rows are boss doors and camps: the Land of Atum one
    // lands among 101 aggressive monsters, and a level 50 bot arriving there died to as many as 68 attackers.
    private static readonly string[] StoneDestinations = ["Hesperos", "Delta", "Green Glades", "Typhon's Reach"];

    private const int ProvenCellSize = 2048;
    private const string ProvenCampResource = "atlantis_camp_cells.json";
    private static readonly Lazy<HashSet<(ushort Zone, int X, int Y)>> ProvenCamps = new(LoadProvenCamps, true);

    public static bool IsStoneDestination(string teleportId) => StoneDestinations.Contains(teleportId);

    /// <summary>
    /// Half the bots take a boat when one serves the trip, because a stone is instant and would otherwise always win.
    /// </summary>
    public static bool PrefersBoats(long botId) => botId % 2 == 0;

    /// <summary>
    /// A cell a bot can really walk to from a haven, proven against the installed meshes by camp_reachability.py.
    /// Islands are cut off from the sea on the mesh, so most land spawns have no route at all.
    /// </summary>
    public static bool IsProvenCamp(ushort zone, int x, int y) =>
        ProvenCamps.Value.Contains((AlbionZone(zone), x / ProvenCellSize, y / ProvenCellSize));

    // Midgard's and Hibernia's copies share Albion's coordinates and meshes.
    private static ushort AlbionZone(ushort zone) => zone switch
    {
        < 50 => (ushort) (zone + 43),
        >= 130 => (ushort) (zone - 57),
        _ => zone
    };

    private static HashSet<(ushort, int, int)> LoadProvenCamps()
    {
        Assembly assembly = typeof(AutonomousAtlantisPolicy).Assembly;
        string resource = assembly.GetManifestResourceNames().First(name => name.EndsWith(ProvenCampResource, StringComparison.OrdinalIgnoreCase));
        using Stream stream = assembly.GetManifestResourceStream(resource);
        int[][] cells = JsonSerializer.Deserialize<int[][]>(stream);
        return cells.Select(cell => ((ushort) cell[0], cell[1], cell[2])).ToHashSet();
    }

    public static bool IsAtlantisRegion(ushort region) => region is 30 or 73 or 130;

    public static bool IsOpenTo(eRealm realm, ushort region) => Gateways.Any(gate => gate.Realm == realm && gate.Atlantis == region);

    public static bool CanHuntHere(eRealm realm, ushort region, int planningLevel) =>
        IsOpenTo(realm, region) && planningLevel >= MinimumLevel;

    public static bool IsLandSpawn(ushort zone, int z) => !Pathfinder.IsBelowAtlantisSea(zone, z);

    public static DbZonePoint[] GatewayEdges()
    {
        var edges = new DbZonePoint[Gateways.Length * 2];
        for (int i = 0; i < Gateways.Length; i++)
        {
            Gateway gate = Gateways[i];
            edges[i * 2] = new DbZonePoint
            {
                Id = (ushort) (FirstGatewayId + i * 2), Realm = (ushort) gate.Realm,
                SourceRegion = gate.Capital, SourceX = gate.CapitalX, SourceY = gate.CapitalY, SourceZ = gate.CapitalZ,
                TargetRegion = gate.Atlantis, TargetX = ArrivalX, TargetY = ArrivalY, TargetZ = ArrivalZ
            };
            edges[i * 2 + 1] = new DbZonePoint
            {
                Id = (ushort) (FirstGatewayId + i * 2 + 1), Realm = (ushort) gate.Realm,
                SourceRegion = gate.Atlantis, SourceX = gate.PortalX, SourceY = gate.PortalY, SourceZ = gate.PortalZ,
                TargetRegion = gate.Capital, TargetX = gate.CapitalX, TargetY = gate.CapitalY, TargetZ = gate.CapitalZ
            };
        }

        return edges;
    }
}
