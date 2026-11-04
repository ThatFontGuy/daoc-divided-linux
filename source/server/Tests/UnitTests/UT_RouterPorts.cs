using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using DOL.Network;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_RouterPorts
    {
        private static readonly (int, ProtocolType)[] Ports = [(10430, ProtocolType.Udp), (10330, ProtocolType.Tcp), (10340, ProtocolType.Tcp)];

        [Test]
        public void ARefusedPortDoesNotCostTheOthers()
        {
            // An ASUS router, 2026-11-01: error 718 for the two ports it had rules for, while the Desk's port stayed closed.
            List<int> refused = [];
            var opened = BaseServer.ForwardEach(Ports, (port, _) =>
            {
                if (port != 10340)
                    throw new WebException("(500) Internal Server Error.");
            }, (port, _, _) => refused.Add(port));

            Assert.That(opened.Select(p => p.Port), Is.EqualTo(new[] { 10340 }));
            Assert.That(refused, Is.EqualTo(new[] { 10430, 10330 }));
        }

        [Test]
        public void OnlyTheOpenedPortsAreListedForRemoval()
        {
            Assert.That(BaseServer.ForwardEach(Ports, (_, _) => { }, (_, _, _) => Assert.Fail()), Has.Count.EqualTo(3));
        }
    }
}
