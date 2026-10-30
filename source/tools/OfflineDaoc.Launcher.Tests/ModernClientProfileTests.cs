using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using NUnit.Framework;

namespace OfflineDaoc.Launcher.Tests;

public sealed class ModernClientProfileTests
{
    private string root = "";

    [SetUp]
    public void Prepare() => root = Path.Combine(Path.GetTempPath(), "odc-modern-" + Guid.NewGuid().ToString("N"));

    [TearDown]
    public void Clean()
    {
        if (Path.GetFullPath(root).StartsWith(Path.GetFullPath(Path.GetTempPath()), StringComparison.OrdinalIgnoreCase) &&
            Path.GetFileName(root).StartsWith("odc-modern-", StringComparison.Ordinal) && Directory.Exists(root))
            Directory.Delete(root, true);
    }

    [Test]
    public void MissingProfileKeepsNormalLauncherBehavior() => Assert.That(ModernClientProfile.Load(root), Is.Null);

    [Test]
    public void ValidProfileUsesIsolatedEndpointAndStructuredArguments()
    {
        var profile = WriteProfile();
        var loaded = ModernClientProfile.Load(root)!;
        var info = loaded.CreateStartInfo("test_account", "trailing\\");
        Assert.That(info.ArgumentList.ToArray(), Is.EqualTo(new[] { Path.Combine(root, "game.dll"), "127.0.0.1:10330", "test_account", "trailing\\" }));
        Assert.That(info.UseShellExecute, Is.False);
    }

    [Test]
    public void BundledPathsResolveFromRuntimeRegardlessOfWorkingDirectory()
    {
        var profile = WriteProfile() with { ClientDirectory = ".", ConnectorPath = "connect.exe" };
        File.WriteAllText(Path.Combine(root, "modern-client.json"), JsonSerializer.Serialize(profile));
        var loaded = ModernClientProfile.Load(root)!;
        Assert.That(loaded.ClientDirectory, Is.EqualTo(Path.GetFullPath(root)));
        Assert.That(loaded.CreateStartInfo("test", "password").FileName, Is.EqualTo(Path.Combine(root, "connect.exe")));
    }

    [Test]
    public void RejectsDifferentDatabaseEvenIfItSharesThePrefix()
    {
        WriteProfile();
        WriteConfig(Path.Combine(root, "data", "opendaoc.sqlite3.db-other"));
        Assert.Throws<InvalidDataException>(() => ModernClientProfile.Load(root));
    }

    [Test]
    public void ChangedClientBytesCannotLaunch()
    {
        var profile = WriteProfile();
        File.WriteAllText(Path.Combine(root, "game.dll"), "changed");
        Assert.Throws<InvalidDataException>(() => profile.CreateStartInfo("test", "password"));
    }

    [Test]
    public void PortMustAgreeWithServerConfiguration()
    {
        var profile = WriteProfile() with { Port = 10300 };
        File.WriteAllText(Path.Combine(root, "modern-client.json"), JsonSerializer.Serialize(profile));
        Assert.Throws<InvalidDataException>(() => ModernClientProfile.Load(root));
    }

    [Test]
    public void HostForFriendsServerStillValidatesAndJoinTargetsTheFriend()
    {
        var profile = WriteProfile();
        HostForFriends.Enable(root);
        Assert.That(ModernClientProfile.Load(root), Is.Not.Null);
        var info = profile.CreateStartInfo("guest", "pw", "100.101.102.103");
        Assert.That(info.ArgumentList[1], Is.EqualTo("100.101.102.103:10330"));
    }

    [Test]
    public void ServerOnAnotherAddressIsRejected()
    {
        WriteProfile();
        var config = Path.Combine(root, "server", "config", "serverconfig.xml");
        File.WriteAllText(config, File.ReadAllText(config).Replace("127.0.0.1", "192.168.1.5"));
        Assert.Throws<InvalidDataException>(() => ModernClientProfile.Load(root));
    }

    private ModernClientProfile WriteProfile()
    {
        Directory.CreateDirectory(Path.Combine(root, "server", "config"));
        File.WriteAllText(Path.Combine(root, "game.dll"), "test client bytes");
        File.WriteAllText(Path.Combine(root, "connect.exe"), "test helper bytes");
        WriteConfig(Path.Combine(root, "data", "opendaoc.sqlite3.db"));
        string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
        var profile = new ModernClientProfile
        {
            Port = 10330, ClientDirectory = root, ConnectorPath = Path.Combine(root, "connect.exe"),
            GameSha256 = Hash(Path.Combine(root, "game.dll")), ConnectorSha256 = Hash(Path.Combine(root, "connect.exe"))
        };
        File.WriteAllText(Path.Combine(root, "modern-client.json"), JsonSerializer.Serialize(profile));
        return profile;
    }

    private void WriteConfig(string database) => new XDocument(new XElement("root", new XElement("Server",
        new XElement("IP", "127.0.0.1"), new XElement("Port", "10330"), new XElement("DBType", "SQLITE"),
        new XElement("DBConnectionString", "Data Source=" + database))))
        .Save(Path.Combine(root, "server", "config", "serverconfig.xml"));
}
