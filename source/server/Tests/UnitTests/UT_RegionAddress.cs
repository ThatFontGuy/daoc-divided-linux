using System.Net;
using DOL.GS.PacketHandler;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_RegionAddress
    {
        [TestCase("8.8.8.8", true)]
        [TestCase("203.0.114.9", true)]
        [TestCase("127.0.0.1", false)]
        [TestCase("10.0.0.5", false)]
        [TestCase("172.16.0.1", false)]
        [TestCase("172.32.0.1", true)]
        [TestCase("192.168.1.20", false)]
        [TestCase("100.64.0.1", false)] // Tailscale and carrier-grade NAT
        [TestCase("100.127.255.254", false)]
        [TestCase("100.128.0.1", true)]
        [TestCase("169.254.3.4", false)]
        [TestCase("224.0.0.1", false)]
        [TestCase("0.0.0.0", false)]
        public void InternetAddresses(string address, bool internet)
        {
            Assert.That(RegionAddress.IsInternet(IPAddress.Parse(address)), Is.EqualTo(internet));
        }

        [Test]
        public void MappedIPv4IsJudgedAsIPv4()
        {
            Assert.That(RegionAddress.IsInternet(IPAddress.Parse("192.168.1.20").MapToIPv6()), Is.False);
            Assert.That(RegionAddress.IsInternet(IPAddress.Parse("8.8.8.8").MapToIPv6()), Is.True);
        }

        [TestCase("any", true)]
        [TestCase("0.0.0.0", true)]
        [TestCase("127.0.0.1", true)]
        [TestCase("192.168.1.20", true)]
        [TestCase("10.13.0.1", true)]
        [TestCase("8.8.8.8", false)] // a configured public region address is sent as it is
        public void PlaceholderRegionAddresses(string configured, bool placeholder)
        {
            Assert.That(RegionAddress.IsPlaceholder(configured), Is.EqualTo(placeholder));
        }
    }
}
