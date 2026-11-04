using DOL.GS.Commands;
using DOL.GS.PacketHandler;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_EodClientFindings
    {
        [TestCase("&appeal", "stuck")]
        [TestCase("&appeal", "Stuck", "here")]
        public void StuckAppealNeedsNoLongText(params string[] args)
        {
            Assert.That(AppealCommandHandler.HasEnoughDetail(args), Is.True);
        }

        [Test]
        public void OtherAppealsStillNeedDetail()
        {
            Assert.That(AppealCommandHandler.HasEnoughDetail(["&appeal", "harassment", "help"]), Is.False);
            Assert.That(AppealCommandHandler.HasEnoughDetail(["&appeal", "harassment", "a", "b", "c"]), Is.True);
        }

        [TestCase(0x1D, true)]
        [TestCase(0x42, true)]
        [TestCase(0x43, true)]
        [TestCase(0xAC, true)]
        [TestCase(0xB8, true)]
        [TestCase(0x41, false)]
        [TestCase(0x98, false)]
        public void WorldNoticesAreNotReportedAsUnhandled(int code, bool known)
        {
            Assert.That(PacketProcessor.IsKnownUnhandledClientPacket(code), Is.EqualTo(known));
        }
    }
}
