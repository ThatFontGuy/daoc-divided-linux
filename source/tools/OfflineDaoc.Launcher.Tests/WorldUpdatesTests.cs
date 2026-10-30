using System.Data.SQLite;
using System.Security.Cryptography;
using System.Text.Json;
using NUnit.Framework;

namespace OfflineDaoc.Launcher.Tests;

public sealed class WorldUpdatesTests
{
    private string root = "";
    private string Runtime => Path.Combine(root, "runtime");
    private string World => Path.Combine(Runtime, "data", "opendaoc.sqlite3.db");

    [SetUp]
    public void Prepare()
    {
        root = Path.Combine(Path.GetTempPath(), "odc-world-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(Runtime, "data"));
        Directory.CreateDirectory(Path.Combine(Runtime, WorldUpdates.Folder));
    }

    [TearDown]
    public void Clean()
    {
        SQLiteConnection.ClearAllPools();
        if (Path.GetFileName(root).StartsWith("odc-world-", StringComparison.Ordinal) && Directory.Exists(root))
            Directory.Delete(root, true);
    }

    // A world from an older release: two monsters, one the game has since re-rolled, and a player's character.
    private static void OlderWorld(string path)
    {
        using var c = new SQLiteConnection($"Data Source={path};Pooling=False");
        c.Open();
        foreach (string sql in new[]
                 {
                     "CREATE TABLE Mob (Mob_ID TEXT PRIMARY KEY, Name TEXT, Level INTEGER, X INTEGER)",
                     "INSERT INTO Mob VALUES ('guard', 'Guard', 20, 100), ('rat', 'Rat', 2, 500)",
                     "CREATE TABLE DOLCharacters (DOLCharacters_ID TEXT PRIMARY KEY, Name TEXT, Level INTEGER)",
                     "INSERT INTO DOLCharacters VALUES ('c1', 'Tester', 24)",
                 })
            using (var cmd = new SQLiteCommand(sql, c)) cmd.ExecuteNonQuery();
    }

    private static object?[] Row(params object?[] values) => values;

    // Step 1 moves the guard and fixes the rat's level; step 2 adds a battleground keeper.
    private void TwoSteps()
    {
        string[] cols = ["Mob_ID", "Name", "Level", "X"];
        var step1 = new
        {
            Version = "0.38-dev2", IgnoreColumns = Array.Empty<string>(), NewTables = Array.Empty<object>(), NewColumns = Array.Empty<object>(),
            Tables = new object[]
            {
                new
                {
                    Table = "Mob", Columns = cols, Key = new[] { "Mob_ID" }, IgnoreCompare = Array.Empty<string>(), ByKey = true,
                    Insert = Array.Empty<object>(), Delete = Array.Empty<object>(),
                    Update = new object[]
                    {
                        new { Old = Row("guard", "Guard", 20, 100), New = Row("guard", "Guard", 20, 150), Set = new[] { "X" } },
                        new { Old = Row("rat", "Rat", 2, 500), New = Row("rat", "Rat", 3, 500), Set = new[] { "Level" } },
                    }
                }
            }
        };
        var step2 = new
        {
            Version = "0.38-dev3", IgnoreColumns = Array.Empty<string>(), NewColumns = Array.Empty<object>(),
            NewTables = new object[] { new { Table = "BgKeep", Create = "CREATE TABLE BgKeep (Id TEXT PRIMARY KEY, Name TEXT)", Indexes = Array.Empty<string>() } },
            Tables = new object[]
            {
                new
                {
                    Table = "Mob", Columns = cols, Key = new[] { "Mob_ID" }, IgnoreCompare = Array.Empty<string>(), ByKey = true,
                    Insert = new object[] { Row("keeper", "Keep Lord", 24, 900) }, Update = Array.Empty<object>(), Delete = Array.Empty<object>()
                }
            }
        };
        var steps = new List<WorldUpdates.Step>();
        foreach (var (version, step) in new[] { ("0.38-dev2", (object)step1), ("0.38-dev3", step2) })
        {
            string file = $"world-{version}.json";
            string path = Path.Combine(Runtime, WorldUpdates.Folder, file);
            File.WriteAllText(path, JsonSerializer.Serialize(step));
            steps.Add(new(version, file, Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)))));
        }
        File.WriteAllText(Path.Combine(Runtime, WorldUpdates.Folder, WorldUpdates.Index), JsonSerializer.Serialize(new WorldUpdates.Chain(1, steps.ToArray())));
    }

    private static object? Value(string path, string sql)
    {
        using var c = new SQLiteConnection($"Data Source={path};Pooling=False;Read Only=True");
        c.Open();
        using var cmd = new SQLiteCommand(sql, c);
        return cmd.ExecuteScalar();
    }

    [Test]
    public void AnOlderWorldGetsEveryStepAndKeepsItsSaves()
    {
        OlderWorld(World);
        TwoSteps();
        using (var c = new SQLiteConnection($"Data Source={World};Pooling=False"))
        {
            c.Open();
            using var cmd = new SQLiteCommand("UPDATE Mob SET Level = 21 WHERE Mob_ID = 'guard'", c);   // re-rolled by the game: not part of step 1's fix
            cmd.ExecuteNonQuery();
        }

        var log = WorldUpdates.Prepare(Runtime);
        Assert.That(Value(World, "SELECT X FROM Mob WHERE Mob_ID='guard'"), Is.EqualTo(150L));
        Assert.That(Value(World, "SELECT Level FROM Mob WHERE Mob_ID='guard'"), Is.EqualTo(21L), "the game's own value stays");
        Assert.That(Value(World, "SELECT Level FROM Mob WHERE Mob_ID='rat'"), Is.EqualTo(3L));
        Assert.That(Value(World, "SELECT Name FROM Mob WHERE Mob_ID='keeper'"), Is.EqualTo("Keep Lord"));
        Assert.That(Value(World, "SELECT count(*) FROM sqlite_master WHERE name='BgKeep'"), Is.EqualTo(1L));
        Assert.That(Value(World, "SELECT Level FROM DOLCharacters WHERE Name='Tester'"), Is.EqualTo(24L), "the character is kept");
        Assert.That(Value(World, "SELECT group_concat(Version) FROM (SELECT Version FROM offline_patch_log ORDER BY Version)"), Is.EqualTo("0.38-dev2,0.38-dev3"));
        Assert.That(log, Has.Some.StartsWith("Backed up the world"));
        string backup = Directory.GetDirectories(Path.Combine(Runtime, "backups")).Single();
        Assert.That(Value(Path.Combine(backup, "opendaoc.sqlite3.db"), "SELECT X FROM Mob WHERE Mob_ID='guard'"), Is.EqualTo(100L), "the backup is the world before");

        Assert.That(WorldUpdates.Prepare(Runtime), Is.Empty, "each step runs once");
    }

    [Test]
    public void AFreshInstallGetsTheCleanWorldAndRunsNoStep()
    {
        string clean = Path.Combine(Runtime, "data", WorldUpdates.CleanWorld);
        OlderWorld(clean);
        TwoSteps();
        using (var c = new SQLiteConnection($"Data Source={clean};Pooling=False"))
        {
            c.Open();
            // build_modern_test_package.py stamps the release's clean world with every step of its chain
            using var cmd = new SQLiteCommand("CREATE TABLE offline_patch_log (Version TEXT PRIMARY KEY, AppliedUtc TEXT, Notes TEXT); " +
                                              "INSERT INTO offline_patch_log VALUES ('0.38-dev2','',''), ('0.38-dev3','','')", c);
            cmd.ExecuteNonQuery();
        }
        Assert.That(WorldUpdates.Prepare(Runtime), Is.EqualTo(new[] { "Made a new world from this release's clean world." }));
        Assert.That(File.Exists(World), Is.True);
        Assert.That(Value(World, "SELECT X FROM Mob WHERE Mob_ID='guard'"), Is.EqualTo(100L));
        Assert.That(Directory.Exists(Path.Combine(Runtime, "backups")), Is.False);
    }

    [Test]
    public void ADamagedStepChangesNothing()
    {
        OlderWorld(World);
        TwoSteps();
        File.AppendAllText(Path.Combine(Runtime, WorldUpdates.Folder, "world-0.38-dev3.json"), " ");
        Assert.Throws<InvalidDataException>(() => WorldUpdates.Prepare(Runtime));
        Assert.That(Value(World, "SELECT X FROM Mob WHERE Mob_ID='guard'"), Is.EqualTo(100L));
        Assert.That(Value(World, "SELECT count(*) FROM sqlite_master WHERE name='offline_patch_log'"), Is.EqualTo(0L));
    }

    [Test]
    public void AFolderWithoutUpdatesIsLeftAlone()
    {
        OlderWorld(World);
        Assert.That(WorldUpdates.Prepare(Runtime), Is.Empty);
    }
}
