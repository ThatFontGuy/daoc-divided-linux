using System.Security.Cryptography;
using System.Text;
using System.Xml.Linq;
using NUnit.Framework;

namespace OfflineDaoc.Launcher.Tests;

public sealed class ModernClientSetupTests
{
    private string root = "";

    [SetUp]
    public void Prepare() => root = Path.Combine(Path.GetTempPath(), "odc-setup-" + Guid.NewGuid().ToString("N"));

    [TearDown]
    public void Clean()
    {
        if (Path.GetFullPath(root).StartsWith(Path.GetFullPath(Path.GetTempPath()), StringComparison.OrdinalIgnoreCase) &&
            Path.GetFileName(root).StartsWith("odc-setup-", StringComparison.Ordinal) && Directory.Exists(root))
            Directory.Delete(root, true);
    }

    private static string Hash(byte[] data) => Convert.ToHexString(SHA256.HashData(data));

    // game.dll: two bytes replaced in place and a section appended; the layout: one line inserted.
    private static readonly byte[] Game = Encoding.ASCII.GetBytes("MZ pristine game bytes 0123456789");
    private static readonly byte[] PatchedGame = Encoding.ASCII.GetBytes("MZ pristine GAME bytes 0123456789+section");
    private static readonly byte[] Layout = Encoding.ASCII.GetBytes("<a/>\r\n<b/>\r\n");
    private static readonly byte[] PatchedLayout = Encoding.ASCII.GetBytes("<a/>\r\n<new/>\r\n<b/>\r\n");

    private static ModernClientSetup.Patch TestPatch() => new(1, "1.130",
    [
        new("game.dll", Hash(Game), Hash(PatchedGame), PatchedGame.Length,
            [new(12, 4, Convert.ToBase64String("GAME"u8.ToArray())), new(Game.Length, 0, Convert.ToBase64String("+section"u8.ToArray()))]),
        new("pregame/character_creation.xml", Hash(Layout), Hash(PatchedLayout), PatchedLayout.Length,
            [new(6, 0, Convert.ToBase64String("<new/>\r\n"u8.ToArray()))])
    ]);

    private string PristineClient()
    {
        string client = Path.Combine(root, "client");
        Directory.CreateDirectory(Path.Combine(client, "pregame"));
        Directory.CreateDirectory(Path.Combine(client, "logs"));
        File.WriteAllBytes(Path.Combine(client, "game.dll"), Game);
        File.WriteAllBytes(Path.Combine(client, "pregame", "character_creation.xml"), Layout);
        File.WriteAllText(Path.Combine(client, "camelot.exe"), "exe");
        File.WriteAllText(Path.Combine(client, "login.dat"), "the player's saved login");
        File.WriteAllText(Path.Combine(client, "logs", "chat.log"), "a log");
        return client;
    }

    [Test]
    public void ApplyRebuildsBothFilesAndRefusesOtherInputs()
    {
        var patch = TestPatch();
        Assert.That(ModernClientSetup.Apply(Game, patch.Files[0]), Is.EqualTo(PatchedGame));
        Assert.That(ModernClientSetup.Apply(Layout, patch.Files[1]), Is.EqualTo(PatchedLayout));
        Assert.Throws<InvalidDataException>(() => ModernClientSetup.Apply("a newer client"u8.ToArray(), patch.Files[0]));
    }

    [Test]
    public void AWholeFileReplacementSwapsTheSplashAndRefusesAnotherOne()
    {
        // pregame/splash.mpk: one edit removes the stock archive and inserts the Divided Realms one.
        byte[] stock = "stock 1.130 splash archive"u8.ToArray(), ours = "divided realms splash"u8.ToArray();
        var splash = new ModernClientSetup.PatchedFile("pregame/splash.mpk", Hash(stock), Hash(ours), ours.Length,
            [new(0, stock.Length, Convert.ToBase64String(ours))]);
        Assert.That(ModernClientSetup.Apply(stock, splash), Is.EqualTo(ours));
        Assert.Throws<InvalidDataException>(() => ModernClientSetup.Apply("a player's own splash"u8.ToArray(), splash));
    }

    [Test]
    public void InstallCopiesAndPatchesWithoutTouchingTheSource()
    {
        string client = PristineClient(), destination = Path.Combine(root, "game", "client-modern", "app");
        ModernClientSetup.Install(client, destination, TestPatch(), null, CancellationToken.None);
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "game.dll")), Is.EqualTo(PatchedGame));
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "pregame", "character_creation.xml")), Is.EqualTo(PatchedLayout));
        Assert.That(File.Exists(Path.Combine(destination, "camelot.exe")), Is.True);
        Assert.That(File.Exists(Path.Combine(destination, "login.dat")), Is.False, "the player's login stays out");
        Assert.That(Directory.Exists(Path.Combine(destination, "logs")), Is.False);
        Assert.That(File.ReadAllBytes(Path.Combine(client, "game.dll")), Is.EqualTo(Game), "the player's own client is unchanged");
        Assert.That(File.Exists(Path.Combine(destination, ModernClientSetup.IncompleteMarker)), Is.False);
    }

    [Test]
    public void AnInterruptedSetupCountsAsNotSetUpAndIsRedone()
    {
        string client = PristineClient(), destination = Path.Combine(root, "game", "client-modern", "app");
        Directory.CreateDirectory(destination);
        File.WriteAllText(Path.Combine(destination, "game.dll"), "half copied");
        File.WriteAllText(Path.Combine(destination, ModernClientSetup.IncompleteMarker), "");
        var profile = new ModernClientProfile { ClientDirectory = destination };
        Assert.That(ModernClientSetup.IsSetUp(profile), Is.False);
        ModernClientSetup.Install(client, destination, TestPatch(), null, CancellationToken.None);
        Assert.That(ModernClientSetup.IsSetUp(profile), Is.True);
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "game.dll")), Is.EqualTo(PatchedGame));
    }

    // A later release: game.dll gets one more edit than TestPatch's, and pregame/splash.mpk is patched for the first time.
    private static readonly byte[] Splash = "stock 1.130 splash archive"u8.ToArray();
    private static readonly byte[] PatchedSplash = "divided realms splash"u8.ToArray();
    private static readonly byte[] NewerGame = Encoding.ASCII.GetBytes("MZ pristine GAME BYTES 0123456789+section");

    private static ModernClientSetup.Patch NewerPatch() => new(1, "1.130",
    [
        new("game.dll", Hash(Game), Hash(NewerGame), NewerGame.Length,
            [new(12, 10, Convert.ToBase64String("GAME BYTES"u8.ToArray())), new(Game.Length, 0, Convert.ToBase64String("+section"u8.ToArray()))]),
        TestPatch().Files[1],
        new("pregame/splash.mpk", Hash(Splash), Hash(PatchedSplash), PatchedSplash.Length, [new(0, Splash.Length, Convert.ToBase64String(PatchedSplash))])
    ]);

    private (string Client, string Destination) OlderReleaseCopy()
    {
        string client = PristineClient(), destination = Path.Combine(root, "game", "client-modern", "app");
        File.WriteAllBytes(Path.Combine(client, "pregame", "splash.mpk"), Splash);
        ModernClientSetup.Install(client, destination, TestPatch(), null, CancellationToken.None);
        return (client, destination);
    }

    [Test]
    public void SetupRemembersThePlayersClientFolder()
    {
        var (client, destination) = OlderReleaseCopy();
        Assert.That(ModernClientSetup.RememberedSource(destination), Is.EqualTo(Path.GetFullPath(client)));
        Assert.That(ModernClientSetup.Stale(destination, TestPatch()), Is.Empty, "a fresh setup matches its own release");
    }

    [Test]
    public void ANewerReleasePatchesTheOlderCopyAgainFromTheRememberedClient()
    {
        var (client, destination) = OlderReleaseCopy();
        var patch = NewerPatch();
        Assert.That(ModernClientSetup.Stale(destination, patch).Select(f => f.Path), Is.EqualTo(new[] { "game.dll", "pregame/splash.mpk" }));
        Assert.That(ModernClientSetup.NeedSource(destination, patch).Select(f => f.Path), Is.EqualTo(new[] { "game.dll" }),
            "the copy's splash is still the stock one, but its game.dll holds the older patch");

        ModernClientSetup.Update(destination, patch, ModernClientSetup.RememberedSource(destination));
        Assert.That(ModernClientSetup.Stale(destination, patch), Is.Empty);
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "game.dll")), Is.EqualTo(NewerGame));
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "pregame", "splash.mpk")), Is.EqualTo(PatchedSplash));
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "game.dll.bak")), Is.EqualTo(PatchedGame), "the replaced file is kept");
        Assert.That(File.ReadAllBytes(Path.Combine(client, "game.dll")), Is.EqualTo(Game), "the player's own client is unchanged");
    }

    [Test]
    public void FilesStillPristineInTheCopyArePatchedWithoutTheClientFolder()
    {
        var (_, destination) = OlderReleaseCopy();
        var patch = new ModernClientSetup.Patch(1, "1.130", [TestPatch().Files[0], TestPatch().Files[1], NewerPatch().Files[2]]);
        Assert.That(ModernClientSetup.NeedSource(destination, patch), Is.Empty);
        ModernClientSetup.Update(destination, patch, null);
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "pregame", "splash.mpk")), Is.EqualTo(PatchedSplash));
    }

    [Test]
    public void AnUpdateWithoutAPristineClientChangesNothing()
    {
        var (client, destination) = OlderReleaseCopy();
        Assert.Throws<InvalidDataException>(() => ModernClientSetup.Update(destination, NewerPatch(), null));
        File.WriteAllText(Path.Combine(client, "game.dll"), "a newer client");
        Assert.Throws<InvalidDataException>(() => ModernClientSetup.Update(destination, NewerPatch(), client));
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "game.dll")), Is.EqualTo(PatchedGame));
        Assert.That(File.ReadAllBytes(Path.Combine(destination, "pregame", "splash.mpk")), Is.EqualTo(Splash),
            "the splash, which could have been patched, waits until every file can be");
    }

    [Test]
    public void AWrongClientIsRefusedBeforeAnythingIsCopied()
    {
        string client = PristineClient(), destination = Path.Combine(root, "game", "app");
        File.WriteAllText(Path.Combine(client, "game.dll"), "a newer client");
        Assert.That(ModernClientSetup.CheckSource(client, TestPatch()), Does.Contain("isn't the 1.130 build"));
        Assert.Throws<InvalidDataException>(() => ModernClientSetup.Install(client, destination, TestPatch(), null, CancellationToken.None));
        Assert.That(Directory.Exists(destination), Is.False);
    }

    [Test]
    public void TheDestinationMayNotBeInsideTheSource()
    {
        string client = PristineClient();
        Assert.Throws<IOException>(() => ModernClientSetup.Install(client, Path.Combine(client, "copy"), TestPatch(), null, CancellationToken.None));
    }

    [Test]
    public void APackageRelativeDatabasePathValidates()
    {
        string runtime = Path.Combine(root, "runtime");
        Directory.CreateDirectory(Path.Combine(runtime, "server", "config"));
        new XDocument(new XElement("root", new XElement("Server", new XElement("IP", "127.0.0.1"), new XElement("Port", "10330"),
                new XElement("DBType", "SQLITE"), new XElement("DBConnectionString", "Data Source=../data/opendaoc.sqlite3.db;Version=3"))))
            .Save(Path.Combine(runtime, "server", "config", "serverconfig.xml"));
        Assert.DoesNotThrow(() => new ModernClientProfile { Port = 10330 }.ValidateServer(runtime));
    }
}
