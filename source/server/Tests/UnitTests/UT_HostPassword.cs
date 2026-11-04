using DOL.GS.PacketHandler.Client.v168;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_HostPassword
    {
        private static readonly string Stored = HostPassword.Hash("swordfish");

        [Test]
        public void NoHostPasswordAllowsAnyNewAccount()
        {
            Assert.That(HostPassword.AllowsNewAccount("", "anything", "203.0.113.25"), Is.True);
            Assert.That(HostPassword.AllowsNewAccount(null, "anything", "203.0.113.25"), Is.True);
        }

        [Test]
        public void AFriendNeedsTheHostPassword()
        {
            Assert.That(HostPassword.AllowsNewAccount(Stored, "swordfish", "203.0.113.25"), Is.True);
            Assert.That(HostPassword.AllowsNewAccount(Stored, "Swordfish", "203.0.113.25"), Is.False);
            Assert.That(HostPassword.AllowsNewAccount(Stored, "", "203.0.113.25"), Is.False);
            Assert.That(HostPassword.AllowsNewAccount(Stored, null, "203.0.113.25"), Is.False);
        }

        [Test]
        public void HomeNetworkFriendsNeedItToo()
        {
            Assert.That(HostPassword.AllowsNewAccount(Stored, "wrong", "192.168.1.20"), Is.False);
        }

        [Test]
        public void ThisPcDoesNotNeedIt()
        {
            Assert.That(HostPassword.AllowsNewAccount(Stored, "my own password", "127.0.0.1"), Is.True);
        }

        // The launcher's HostForFriends.HashHostPassword has this same value in HostForFriendsTests.
        [Test]
        public void HashMatchesTheLauncher()
        {
            Assert.That(Stored, Has.Length.EqualTo(64));
            Assert.That(Stored, Is.EqualTo("4a9e1d7e2bb770e3f89110ee8d09517a3a4dbd6f4165881d3a79c6d3ef9d0273"));
        }
    }
}
