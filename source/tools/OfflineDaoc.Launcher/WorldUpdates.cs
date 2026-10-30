using System.Data.SQLite;
using System.Text.Json;
using OfflineDaoc.Patcher;

namespace OfflineDaoc.Launcher;

/// <summary>
/// The modern test packages ship their world as data/world-clean.sqlite3.db, never as the played database: copying a newer
/// release over an older folder then can't overwrite the player's saves. The launcher makes data/opendaoc.sqlite3.db from
/// the clean world when there is none, and brings an existing one up to this release with world-updates/: one update per
/// release since the first (made by build_modern_test_package.py), applied in order by the patcher's own WorldUpdate. Each
/// runs once (offline_patch_log) and only changes world rows that still have their released values, so a world from any
/// earlier release ends up with this release's fixes and the player's saves and game-written rows are left alone.
/// </summary>
public static class WorldUpdates
{
    public const string CleanWorld = "world-clean.sqlite3.db";
    public const string Folder = "world-updates";
    public const string Index = "world-updates.json";

    public sealed record Step(string Version, string File, string Sha256);
    public sealed record Chain(int Format, Step[] Steps);

    public static Chain? Load(string runtime)
    {
        string index = Path.Combine(runtime, Folder, Index);
        if (!File.Exists(index)) return null;
        var chain = JsonSerializer.Deserialize<Chain>(File.ReadAllText(index)) ?? throw new InvalidDataException("The world update list is empty.");
        if (chain.Format != 1)
            throw new InvalidDataException("This launcher doesn't know the world update list's format.");
        return chain;
    }

    /// <summary>The steps this world hasn't had yet, in order.</summary>
    public static Step[] Pending(string database, Chain chain)
    {
        if (!File.Exists(database)) return chain.Steps;
        using var c = new SQLiteConnection($"Data Source={database};Pooling=False;Read Only=True");
        c.Open();
        var done = new HashSet<string>(StringComparer.Ordinal);
        using (var exists = new SQLiteCommand("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='offline_patch_log'", c))
            if (Convert.ToInt64(exists.ExecuteScalar()) > 0)
                using (var read = new SQLiteCommand("SELECT Version FROM offline_patch_log", c))
                using (var r = read.ExecuteReader())
                    while (r.Read()) done.Add(r.GetString(0));
        return chain.Steps.Where(s => !done.Contains(s.Version)).ToArray();
    }

    /// <summary>
    /// Makes the world from the clean one when there is none, then applies the pending updates (after a backup in
    /// backups\world-update-&lt;version&gt;-&lt;time&gt;). Returns what was done, one line each; nothing when the world is current.
    /// The server must not be running. A failed update is rolled back (one transaction) and stops the rest.
    /// </summary>
    public static List<string> Prepare(string runtime)
    {
        var log = new List<string>();
        string data = Path.Combine(runtime, "data"), database = Path.Combine(data, "opendaoc.sqlite3.db"), clean = Path.Combine(data, CleanWorld);
        if (!File.Exists(database) && File.Exists(clean))
        {
            string temporary = database + ".new";
            File.Copy(clean, temporary, true);
            File.Move(temporary, database);
            log.Add("Made a new world from this release's clean world.");
        }
        var chain = Load(runtime);
        if (chain == null || !File.Exists(database)) return log;
        var pending = Pending(database, chain);
        if (pending.Length == 0) return log;

        foreach (var step in pending)
        {
            string file = Path.Combine(runtime, Folder, step.File);
            if (!File.Exists(file) || !Hash(file).Equals(step.Sha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException($"The world update {step.File} is missing or damaged. Extract the whole release again.");
        }
        string backup = Path.Combine(runtime, "backups", $"world-update-{pending[^1].Version}-{DateTime.Now:yyyyMMdd-HHmmss}");
        Directory.CreateDirectory(backup);
        using (var from = new SQLiteConnection($"Data Source={database};Pooling=False"))
        using (var to = new SQLiteConnection($"Data Source={Path.Combine(backup, "opendaoc.sqlite3.db")};Pooling=False"))
        {
            from.Open();
            to.Open();
            from.BackupDatabase(to, "main", "main", -1, null, 0);
        }
        log.Add($"Backed up the world to {backup}.");
        foreach (var step in pending)
            new WorldUpdate(database, Path.Combine(runtime, Folder, step.File), step.Version, log.Add).Apply();
        File.WriteAllLines(Path.Combine(backup, "UPDATE-REPORT.txt"), log);
        return log;
    }

    private static string Hash(string path)
    {
        using var stream = File.OpenRead(path);
        return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream));
    }
}
