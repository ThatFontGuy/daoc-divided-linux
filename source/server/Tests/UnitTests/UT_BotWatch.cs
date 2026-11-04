using System.IO;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_BotWatch
    {
        [Test]
        public void ThePageIsInsideTheServer()
        {
            using Stream page = typeof(BotWatch).Assembly.GetManifestResourceStream("DOL.GS.BotWatch.html");

            Assert.That(page, Is.Not.Null);
            Assert.That(new StreamReader(page).ReadToEnd(), Does.Contain("/api/region/"));
        }

        [Test]
        public void ItDoesNotShareThePassportDeskPort()
        {
            Assert.That(BotWatch.PORT_OFFSET, Is.Not.EqualTo(DOL.Network.BaseServer.PASSPORT_DESK_PORT_OFFSET));
        }
    }
}
