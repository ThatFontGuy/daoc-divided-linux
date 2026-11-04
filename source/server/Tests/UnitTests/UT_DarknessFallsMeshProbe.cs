using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Numerics;
using System.Reflection;
using System.Text.Json;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>
    /// Tool: every certified Darkness Falls route on a real mesh, leg by leg, with the check the server's mover applies
    /// (issue #3). Read only. Env: OFFLINE_DAOC_NAV_ROOT (folder with navmesh/zone249.nav and lib/Detour.dll),
    /// OFFLINE_DAOC_PROOF_OUT.
    /// </summary>
    [TestFixture, Explicit("Darkness Falls mesh probe tool"), NonParallelizable]
    public class UT_DarknessFallsMeshProbe
    {
        private static AutonomousDarknessFallsNavigation.Certificate LoadCertificate()
        {
            Assembly assembly = typeof(AutonomousDarknessFallsNavigation).Assembly;
            string resource = assembly.GetManifestResourceNames().Single(name => name.EndsWith("darkness_falls_navigation_proofs.json", StringComparison.Ordinal));
            using Stream stream = assembly.GetManifestResourceStream(resource);
            return JsonSerializer.Deserialize<AutonomousDarknessFallsNavigation.Certificate>(stream, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }

        [Test]
        public void ProbeCertifiedRoutes()
        {
            string root = Environment.GetEnvironmentVariable("OFFLINE_DAOC_NAV_ROOT");
            string output = Environment.GetEnvironmentVariable("OFFLINE_DAOC_PROOF_OUT");
            Assume.That(root != null && output != null);
            var certificate = LoadCertificate();

            string previous = Environment.CurrentDirectory;
            Environment.CurrentDirectory = root;
            var nav = PathfindingProvider.LocalPathfindingMgr;
            var zone = new Zone(null, 249, "zone249", 0, 0, 65536 * 8, 65536 * 8, 249, false, 0, false, 0, 0, 0, 0, 0);
            var lines = new List<string>();
            var failed = new Dictionary<(eRealm, string), int>();
            int legs = 0, routes = 0, whole = 0;
            WrappedPathfindingNode[] nodes = new WrappedPathfindingNode[256];
            try
            {
                LocalPathfindingMgr.LoadNavMesh(zone);
                foreach (var proof in certificate.Spawns)
                {
                    foreach (var route in proof.Routes)
                    {
                        routes++;
                        bool ok = true;
                        foreach (float[][] waypoints in new[] { route.InWaypoints, route.OutWaypoints })
                        {
                            for (int i = 1; i < waypoints.Length; i++)
                            {
                                legs++;
                                Vector3 start = new(waypoints[i - 1][0], waypoints[i - 1][1], waypoints[i - 1][2]);
                                Vector3 end = new(waypoints[i][0], waypoints[i][1], waypoints[i][2]);
                                PathfindingResult result = nav.GetPathStraight(zone, start, end, nav.DefaultFilters, nodes);
                                if (AutonomousDarknessFallsNavigation.MayQueuePath(true, AutonomousDarknessFallsPolicy.RegionId, true, result, nodes, start, end, certificate.TraversalLinks))
                                    continue;
                                ok = false;
                                var key = (route.Realm, $"{start.X:0},{start.Y:0},{start.Z:0}>{end.X:0},{end.Y:0},{end.Z:0} {result.Status}");
                                failed[key] = failed.GetValueOrDefault(key) + 1;
                            }
                        }
                        if (ok) whole++;
                    }
                }
            }
            finally
            {
                LocalPathfindingMgr.UnloadNavMesh(zone);
                Environment.CurrentDirectory = previous;
            }
            lines.Add($"routes {routes} complete {whole} legs {legs} failed leg kinds {failed.Count}");
            lines.AddRange(failed.OrderByDescending(pair => pair.Value).Take(30).Select(pair => $"{pair.Key.Item1} {pair.Key.Item2} x{pair.Value}"));
            File.WriteAllLines(output, lines);
        }

        /// <summary>
        /// A bot crossing a drop as an ordinary walk is off the mesh between the lip and the landing. What a re-plan gives from
        /// each point of that walk, to the landing and to the bottom of the realm's drops.
        /// </summary>
        [Test]
        public void ProbeInsideDrops()
        {
            string root = Environment.GetEnvironmentVariable("OFFLINE_DAOC_NAV_ROOT");
            string output = Environment.GetEnvironmentVariable("OFFLINE_DAOC_PROOF_OUT");
            Assume.That(root != null && output != null);
            var certificate = LoadCertificate();

            var falls = certificate.TraversalLinks.Where(link => link.Kind == "Fall").ToArray();
            string previous = Environment.CurrentDirectory;
            Environment.CurrentDirectory = root;
            var nav = PathfindingProvider.LocalPathfindingMgr;
            var zone = new Zone(null, 249, "zone249", 0, 0, 65536 * 8, 65536 * 8, 249, false, 0, false, 0, 0, 0, 0, 0);
            var lines = new List<string>();
            WrappedPathfindingNode[] nodes = new WrappedPathfindingNode[512];
            try
            {
                LocalPathfindingMgr.LoadNavMesh(zone);
                for (int f = 0; f < falls.Length; f++)
                {
                    var link = falls[f];
                    Vector3 lip = new(link.Start[0], link.Start[1], link.Start[2]), landing = new(link.End[0], link.End[1], link.End[2]);
                    var last = falls[f / 3 * 3 + 2];
                    Vector3 bottom = new(last.End[0], last.End[1], last.End[2]);
                    lines.Add($"fall {f} lip {lip} landing {landing}");
                    for (int step = 0; step <= 10; step++)
                    {
                        Vector3 at = Vector3.Lerp(lip, landing, step / 10f);
                        PathfindingResult toLanding = nav.GetPathStraight(zone, at, landing, nav.DefaultFilters, nodes);
                        string first = toLanding.NodeCount > 0 ? $"{nodes[0].Position.X:0},{nodes[0].Position.Y:0},{nodes[0].Position.Z:0}" : "none";
                        int landingNodes = toLanding.NodeCount;
                        PathfindingResult toBottom = nav.GetPathStraight(zone, at, bottom, nav.DefaultFilters, nodes);
                        Vector3? snapped = nav.GetClosestPoint(zone, at, nav.DefaultFilters);
                        lines.Add($"  {step * 10,3}% z={at.Z:0} landing {toLanding.Status} n={landingNodes} first={first} | bottom {toBottom.Status} n={toBottom.NodeCount} | closest {(snapped is { } s ? $"{s.X:0},{s.Y:0},{s.Z:0}" : "none")} | settles {(AutonomousDarknessFallsNavigation.TryFindFloorBelowDrop(nav, zone, at, out Vector3 floor) ? $"{floor.X:0},{floor.Y:0},{floor.Z:0}" : "no")}");
                    }
                }
            }
            finally
            {
                LocalPathfindingMgr.UnloadNavMesh(zone);
                Environment.CurrentDirectory = previous;
            }
            File.WriteAllLines(output, lines);
        }

        /// <summary>
        /// Every floor point around a realm's three entrance drops, not only the certified waypoints: where a companion or a
        /// group follower really stands. Reports what a path to the bottom of the drops gives from each point.
        /// </summary>
        [Test]
        public void ProbeEntranceFloors()
        {
            string root = Environment.GetEnvironmentVariable("OFFLINE_DAOC_NAV_ROOT");
            string output = Environment.GetEnvironmentVariable("OFFLINE_DAOC_PROOF_OUT");
            Assume.That(root != null && output != null);
            var certificate = LoadCertificate();

            var falls = certificate.TraversalLinks.Where(link => link.Kind == "Fall").ToArray();
            string previous = Environment.CurrentDirectory;
            Environment.CurrentDirectory = root;
            var nav = PathfindingProvider.LocalPathfindingMgr;
            var zone = new Zone(null, 249, "zone249", 0, 0, 65536 * 8, 65536 * 8, 249, false, 0, false, 0, 0, 0, 0, 0);
            var lines = new List<string>();
            WrappedPathfindingNode[] nodes = new WrappedPathfindingNode[512];
            try
            {
                LocalPathfindingMgr.LoadNavMesh(zone);
                foreach (var (realm, chain) in new[] { (eRealm.Albion, falls[0..3]), (eRealm.Midgard, falls[3..6]), (eRealm.Hibernia, falls[6..9]) })
                {
                    AutonomousDarknessFallsNavigation.TryFindEntrance(certificate.Spawns, realm, out Vector3 entrance);
                    Vector3 Point(float[] p) => new(p[0], p[1], p[2]);
                    Vector3 bottom = Point(chain[2].End);
                    float[] levels = [Point(chain[0].Start).Z, Point(chain[1].Start).Z, Point(chain[2].Start).Z, bottom.Z];
                    float minX = chain.Min(link => Math.Min(link.Start[0], link.End[0])) - 320, maxX = chain.Max(link => Math.Max(link.Start[0], link.End[0])) + 320;
                    float minY = chain.Min(link => Math.Min(link.Start[1], link.End[1])) - 320, maxY = chain.Max(link => Math.Max(link.Start[1], link.End[1])) + 320;
                    minX = Math.Min(minX, entrance.X); maxX = Math.Max(maxX, entrance.X);
                    minY = Math.Min(minY, entrance.Y); maxY = Math.Max(maxY, entrance.Y);
                    var seen = new HashSet<(int, int, int)>();
                    var counts = new Dictionary<string, int>();
                    var samples = new List<string>();
                    foreach (float level in levels)
                    {
                        for (float x = minX; x <= maxX; x += 24)
                        {
                            for (float y = minY; y <= maxY; y += 24)
                            {
                                Vector3? floor = nav.GetClosestPoint(zone, new(x, y, level), 12, 12, 48, nav.DefaultFilters);
                                if (floor is not { } start || !seen.Add(((int)start.X / 8, (int)start.Y / 8, (int)start.Z / 8)))
                                    continue;
                                int band = Array.FindIndex(levels, z => Math.Abs(z - start.Z) <= 64);
                                PathfindingResult result = nav.GetPathStraight(zone, start, bottom, nav.DefaultFilters, nodes);
                                int count = Math.Min(result.NodeCount, nodes.Length);
                                bool reaches = count > 0 && Vector3.Distance(nodes[count - 1].Position, bottom) <= 64;
                                bool strict = AutonomousDarknessFallsNavigation.MayQueuePath(true, AutonomousDarknessFallsPolicy.RegionId, true, result, nodes, start, bottom, certificate.TraversalLinks);
                                string key = $"level {band} {result.Status} reaches={reaches} strict={strict}";
                                counts[key] = counts.GetValueOrDefault(key) + 1;
                                if ((!reaches || !strict) && samples.Count < 40)
                                {
                                    string last = count > 0 ? $"{nodes[count - 1].Position.X:0},{nodes[count - 1].Position.Y:0},{nodes[count - 1].Position.Z:0}" : "none";
                                    samples.Add($"  {start.X:0},{start.Y:0},{start.Z:0} {result.Status} nodes={count} last={last} strict={strict}");
                                }
                            }
                        }
                    }
                    lines.Add($"{realm} floor points {seen.Count} bottom {bottom}");
                    lines.AddRange(counts.OrderBy(pair => pair.Key).Select(pair => $"  {pair.Key}: {pair.Value}"));
                    lines.AddRange(samples);
                }
            }
            finally
            {
                LocalPathfindingMgr.UnloadNavMesh(zone);
                Environment.CurrentDirectory = previous;
            }
            File.WriteAllLines(output, lines);
        }
    }
}
