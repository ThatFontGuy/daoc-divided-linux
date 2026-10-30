using System.Data.SQLite;
using System.Reflection;
using NUnit.Framework;

namespace OfflineDaoc.Launcher.Tests;

/// <summary>
/// Since 0.33 "Claude Takeover": every install makes its own local account, and the
/// retired Sluaghbinder (class 63) is never rolled.
/// </summary>
public sealed class ClaudeTakeoverEditionTests
{
    private static readonly Assembly Launcher = Assembly.Load("OfflineDAoC");
    private static readonly BindingFlags HiddenStatic = BindingFlags.Static | BindingFlags.NonPublic;

    [Test]
    public void EachInstallCreatesItsOwnAccountOnceAndNeverReplacesIt()
    {
        string folder = Path.Combine(Path.GetTempPath(), "odc-account-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        try
        {
            var first = PortableCredentials.ReadOrCreate(folder);
            var second = PortableCredentials.ReadOrCreate(folder);
            Assert.That(first, Is.EqualTo(second), "an existing account.txt is reused, never regenerated");
            Assert.That(first.Account, Is.EqualTo("offline"));
            Assert.That(first.Password, Has.Length.EqualTo(20), "the legacy login packet allows 20 characters");

            string other = Path.Combine(folder, "other");
            Directory.CreateDirectory(other);
            Assert.That(PortableCredentials.ReadOrCreate(other).Password, Is.Not.EqualTo(first.Password),
                "a second install gets its own password");
        }
        finally { Directory.Delete(folder, true); }
    }

    [Test]
    public void RetiredSluaghbinderIsNeverRolled()
    {
        var reserved = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        MethodInfo generate = Launcher.GetType("OfflineDaoc.Launcher.BotCharacterGenerator")!
            .GetMethod("Generate", BindingFlags.Static | BindingFlags.Public, [typeof(int), typeof(ISet<string>), typeof(ISet<string>)])!;
        int Roll()
        {
            object identity = generate.Invoke(null, [3, reserved, null])!;
            return (int)identity.GetType().GetProperty("ClassId")!.GetValue(identity)!;
        }
        var rolled = Enumerable.Range(0, 1500).Select(_ => Roll()).ToList();
        Assert.That(rolled, Does.Not.Contain(63));
    }

    [Test]
    public void NewerClassesAreRolledOnlyWhileTheirSwitchIsOn()
    {
        MethodInfo generate = Launcher.GetType("OfflineDaoc.Launcher.BotCharacterGenerator")!
            .GetMethod("Generate", BindingFlags.Static | BindingFlags.Public, [typeof(int), typeof(ISet<string>), typeof(ISet<string>)])!;
        List<int> Rolls(int realm, ISet<string>? switches)
        {
            var reserved = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            return Enumerable.Range(0, 1000).Select(_ =>
            {
                object identity = generate.Invoke(null, [realm, reserved, switches])!;
                return (int)identity.GetType().GetProperty("ClassId")!.GetValue(identity)!;
            }).ToList();
        }
        var mauler = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "enable_mauler_test" };
        Assert.Multiple(() =>
        {
            Assert.That(Rolls(2, null), Has.None.GreaterThan(32).And.None.EqualTo(34));
            Assert.That(Rolls(2, new HashSet<string>()), Has.None.GreaterThan(32));
            List<int> midgard = Rolls(2, mauler);
            Assert.That(midgard, Does.Contain(61));
            Assert.That(midgard, Has.None.EqualTo(34).And.None.EqualTo(59).And.None.EqualTo(64));
            Assert.That(Rolls(3, new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "enable_tuatha" }), Does.Contain(67));
        });
    }

    [TestCase(true, "VERSION 0.37b")]
    [TestCase(false, "VERSION 0.37")]
    public void VersionLabelNamesTheInstalledEdition(bool customClass, string expected)
    {
        MethodInfo label = Launcher.GetType("OfflineDaoc.Launcher.MainForm")!.GetMethod("VersionLabel", HiddenStatic)!;
        Assert.That(label.Invoke(null, [customClass]), Is.EqualTo(expected));
    }

    [TestCase(null, true)]
    [TestCase("True", true)]
    [TestCase("true", true)]
    [TestCase("False", false)]
    [TestCase(" false ", false)]
    public void LauncherReadsTheServerEditionSwitch(string? value, bool expected)
    {
        using var connection = new SQLiteConnection("Data Source=:memory:;Version=3;");
        connection.Open();
        using (var setup = connection.CreateCommand())
        {
            setup.CommandText = "CREATE TABLE ServerProperty (Category TEXT, `Key` TEXT, Value TEXT)";
            setup.ExecuteNonQuery();
            if (value != null)
            {
                setup.CommandText = "INSERT INTO ServerProperty VALUES ('classes','enable_sluaghbinder',@value)";
                setup.Parameters.AddWithValue("@value", value);
                setup.ExecuteNonQuery();
            }
        }
        using var transaction = connection.BeginTransaction();
        MethodInfo read = Launcher.GetType("OfflineDaoc.Launcher.MainForm")!.GetMethod("SluaghbinderEnabled", HiddenStatic)!;
        Assert.That(read.Invoke(null, [connection, transaction]), Is.EqualTo(expected));
    }
}
