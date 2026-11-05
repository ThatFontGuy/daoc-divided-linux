using System.Collections.Generic;
using System.Linq;
using DOL.GS.PacketHandler;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrainerWindowPackets
    {
        private const int Budget = PacketLib1105.TRAINER_NAMES_BYTE_BUDGET;
        private const int MaxPacketSize = 2048;
        private const int PacketOverhead = 8; // 3 of TCP header + count, points, code, 0, start index

        // 141 names of 13 and 14 characters: the same 2,098 bytes of names as the discarded Hunter packet.
        private static List<string> HunterArcheryNames()
        {
            List<string> names = Enumerable.Range(0, 141).Select(i => new string('x', i < 124 ? 14 : 13)).ToList();
            Assert.That(Cost(names, 0, names.Count) + PacketOverhead, Is.EqualTo(2106));
            return names;
        }

        private static int Cost(List<string> names, int start, int count) =>
            names.Skip(start).Take(count).Sum(name => 1 + name.Length);

        private static void AssertContiguous(List<(int Start, int Count)> ranges, int nameCount)
        {
            int next = 0;

            foreach ((int start, int count) in ranges)
            {
                Assert.That(start, Is.EqualTo(next), "a gap or an overlap");
                Assert.That(count, Is.GreaterThan(0));
                next = start + count;
            }

            Assert.That(next, Is.EqualTo(nameCount), "every name is sent");
        }

        [Test]
        public void TheHunterArcheryNamesSplitAndEveryPacketStaysUnderBudget()
        {
            List<string> names = HunterArcheryNames();
            List<(int Start, int Count)> ranges = PacketLib1105.SplitTrainerNames(names, Budget);

            Assert.That(ranges, Has.Count.GreaterThan(1));
            Assert.That(Budget + PacketOverhead, Is.LessThan(MaxPacketSize));

            foreach ((int start, int count) in ranges)
            {
                Assert.That(Cost(names, start, count), Is.LessThanOrEqualTo(Budget));
                Assert.That(Cost(names, start, count) + PacketOverhead, Is.LessThanOrEqualTo(MaxPacketSize));
            }
        }

        [Test]
        public void RangesAreContiguousAndCoverEveryName()
        {
            List<string> names = HunterArcheryNames();

            AssertContiguous(PacketLib1105.SplitTrainerNames(names, Budget), names.Count);
            AssertContiguous(PacketLib1105.SplitTrainerNames(names, 100), names.Count);
        }

        [Test]
        public void ASpecWithNoNamesStillGetsOneEmptyPacket()
        {
            Assert.That(PacketLib1105.SplitTrainerNames(new List<string>(), Budget), Is.EqualTo(new[] { (0, 0) }));
        }

        [Test]
        public void NamesThatFitStayInOnePacket()
        {
            List<string> names = ["Sword", "Slash", "Thrust"];

            Assert.That(PacketLib1105.SplitTrainerNames(names, Budget), Is.EqualTo(new[] { (0, 3) }));
        }

        [Test]
        public void ABudgetFilledExactlyIsNotSplit()
        {
            List<string> names = ["abcd", "efgh"];

            Assert.That(PacketLib1105.SplitTrainerNames(names, 10), Is.EqualTo(new[] { (0, 2) }));
            Assert.That(PacketLib1105.SplitTrainerNames(names, 9), Is.EqualTo(new[] { (0, 1), (1, 1) }));
        }

        [Test]
        public void ANameOverTheBudgetIsSentAlone()
        {
            List<string> names = ["short", new string('x', 300), "short"];

            Assert.That(PacketLib1105.SplitTrainerNames(names, 50), Is.EqualTo(new[] { (0, 1), (1, 1), (2, 1) }));
        }

        [Test]
        public void TheCountNeverOverflowsItsByte()
        {
            List<string> names = Enumerable.Repeat("x", 300).ToList();
            List<(int Start, int Count)> ranges = PacketLib1105.SplitTrainerNames(names, Budget);

            Assert.That(ranges.Max(range => range.Count), Is.LessThanOrEqualTo(255));
            AssertContiguous(ranges, names.Count);
        }

        [Test]
        public void ANullNameCostsOnlyItsLengthByte()
        {
            List<string> names = [null, null];

            Assert.That(PacketLib1105.SplitTrainerNames(names, 2), Is.EqualTo(new[] { (0, 2) }));
        }
    }
}
