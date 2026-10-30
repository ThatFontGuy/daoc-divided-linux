using System.Net;
using NUnit.Framework;

namespace OfflineDaoc.Launcher.Tests;

public sealed class JoinFriendTests
{
    private string _directory = string.Empty;
    private string ProfilePath => Path.Combine(_directory, "join-friend.json");

    [SetUp]
    public void SetUp() => _directory = Path.Combine(Path.GetTempPath(), "odc-join-" + Guid.NewGuid().ToString("N"));

    [TearDown]
    public void TearDown()
    {
        if (Directory.Exists(_directory))
            Directory.Delete(_directory, true);
    }

    [Test]
    public void RememberedPasswordRoundTripsWithoutPlaintextOnDisk()
    {
        JoinFriendProfile.Save(ProfilePath, "100.120.169.75", "Aaron", "S3cret!pw", rememberPassword: true);

        JoinFriendProfile loaded = JoinFriendProfile.Load(ProfilePath);
        Assert.That(loaded.HostAddress, Is.EqualTo("100.120.169.75"));
        Assert.That(loaded.GuestAccount, Is.EqualTo("Aaron"));
        Assert.That(loaded.Password, Is.EqualTo("S3cret!pw"));
        Assert.That(File.ReadAllText(ProfilePath), Does.Not.Contain("S3cret!pw"));
    }

    [Test]
    public void DetailsAreKeptButPasswordIsForgottenWhenNotRemembered()
    {
        JoinFriendProfile.Save(ProfilePath, "100.120.169.75", "Aaron", "S3cret!pw", rememberPassword: true);
        JoinFriendProfile.Save(ProfilePath, "100.120.169.75", "Aaron", "S3cret!pw", rememberPassword: false);

        JoinFriendProfile loaded = JoinFriendProfile.Load(ProfilePath);
        Assert.That(loaded.GuestAccount, Is.EqualTo("Aaron"));
        Assert.That(loaded.Password, Is.Empty);
        Assert.That(loaded.RememberPassword, Is.False);
    }

    [Test]
    public void MissingOrDamagedProfileLoadsEmpty()
    {
        Assert.That(JoinFriendProfile.Load(ProfilePath).HostAddress, Is.Empty);

        Directory.CreateDirectory(_directory);
        File.WriteAllText(ProfilePath, "{ not json");
        Assert.That(JoinFriendProfile.Load(ProfilePath).GuestAccount, Is.Empty);

        // stefanrows' profile files also carry HostAccount; it is ignored.
        File.WriteAllText(ProfilePath, "{\"HostAddress\":\"100.64.0.1\",\"HostAccount\":\"offline\",\"ProtectedPassword\":\"not-base64!\"}");
        JoinFriendProfile loaded = JoinFriendProfile.Load(ProfilePath);
        Assert.That(loaded.HostAddress, Is.EqualTo("100.64.0.1"));
        Assert.That(loaded.Password, Is.Empty);
    }

    [TestCase("100.64.0.1", true)]
    [TestCase("100.127.255.254", true)]
    [TestCase("192.168.1.20", true)]
    [TestCase("10.0.0.7", true)]
    [TestCase("172.20.1.1", true)]
    [TestCase("100.63.0.1", true)]
    [TestCase("203.0.113.25", true)] // internet mode
    [TestCase("169.254.1.1", false)]
    [TestCase("224.0.0.1", false)]
    [TestCase("0.1.2.3", false)]
    [TestCase("127.0.0.1", false)]
    [TestCase("100.64.1", false)]
    [TestCase(" 100.64.0.1 ", true)]
    [TestCase("friend.example.com", false)]
    public void HostAddressIsAnyHostButThisPc(string text, bool accepted)
    {
        Assert.That(JoinFriend.TryParseHost(text, out _, out string error), Is.EqualTo(accepted));
        Assert.That(error, accepted ? Is.Empty : Is.Not.Empty);
    }

    [TestCase("Aaron", true)]
    [TestCase("guest2", true)]
    [TestCase("", false)]
    [TestCase("has space", false)]
    [TestCase("abcdefghijklmnopqrstu", false)]
    public void AccountNamesFollowTheLegacyClient(string account, bool valid) =>
        Assert.That(JoinFriend.IsValidAccount(account), Is.EqualTo(valid));

    [TestCase("pw", true)]
    [TestCase("", false)]
    [TestCase("tab\tchar", false)]
    [TestCase("ünicode", false)]
    public void PasswordsFollowTheLegacyClient(string password, bool valid) =>
        Assert.That(JoinFriend.IsValidPassword(password), Is.EqualTo(valid));

    [Test]
    public void OriginalClientConnectsToTheHostOnTheClassicPort()
    {
        string runtime = Path.Combine(_directory, "runtime");
        string app = Path.Combine(runtime, "client-opendaoc", "app");
        Directory.CreateDirectory(app);
        File.WriteAllText(Path.Combine(app, "game.dll"), "x");
        File.WriteAllText(Path.Combine(app, "connect.exe"), "x");

        JoinClient client = JoinClient.For(runtime, modern: null);
        Assert.That(client.IsInstalled, Is.True);
        Assert.That(client.LoginPort, Is.EqualTo(10300));
        var info = client.CreateStartInfo(IPAddress.Parse("100.70.1.2"), "Aaron", "pw");
        Assert.That(info.FileName, Is.EqualTo(Path.Combine(app, "connect.exe")));
        Assert.That(info.ArgumentList.ToArray(), Is.EqualTo(new[] { "game.dll", "100.70.1.2", "Aaron", "pw" }));
        Assert.That(info.UseShellExecute, Is.False);
    }
}
