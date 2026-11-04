using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_FightReports
    {
        // Parties and livings are plain strings here; monsters named "crab" merge into one enemy row.
        private static FightBook Book() => new(who => who is string name && name.StartsWith("crab") ? "crab" : who);

        [Test]
        public void HitsGivenAndTakenAddUpOnBothSides()
        {
            FightBook book = Book();
            book.Hit("party", "you", null, "crab1", 76, 0);
            book.Hit("party", "pet", null, "crab2", 40, 500);
            book.Hit(null, "crab1", "party", "you", 12, 900);

            FightBook.Fight fight = book.Close(20_000, 8000)[0].Fight;

            Assert.That(fight.Allies["you"].Done, Is.EqualTo(76));
            Assert.That(fight.Allies["you"].Taken, Is.EqualTo(12));
            Assert.That(fight.Allies["pet"].Done, Is.EqualTo(40));
            Assert.That(fight.Enemies["crab"].Taken, Is.EqualTo(116));
            Assert.That(fight.Enemies["crab"].Done, Is.EqualTo(12));
            Assert.That(fight.Enemies["crab"].Members, Has.Count.EqualTo(2));
            Assert.That(fight.Seconds, Is.EqualTo(1));
        }

        [Test]
        public void AFightEndsOnlyAfterItHasBeenQuiet()
        {
            FightBook book = Book();
            book.Hit("party", "you", null, "crab1", 10, 0);
            book.Hit("party", "you", null, "crab1", 10, 7000);

            Assert.That(book.Close(10_000, 8000), Is.Empty);
            Assert.That(book.Close(15_000, 8000), Has.Count.EqualTo(1));
            Assert.That(book.OpenFights, Is.Zero);
        }

        [Test]
        public void HealingOutsideAFightStartsNothing()
        {
            FightBook book = Book();
            book.Heal("party", "healer", "party", "you", 300, 0);

            Assert.That(book.OpenFights, Is.Zero);
        }

        [Test]
        public void HealsAndDeathsInsideAFightAreCounted()
        {
            FightBook book = Book();
            book.Hit(null, "crab1", "party", "you", 50, 0);
            book.Heal("party", "healer", "party", "you", 30, 100);
            book.Died(null, "crab1", "party", "you", 200);
            book.Died("party", "you", null, "crab1", 300);

            FightBook.Fight fight = book.Close(10_000, 8000)[0].Fight;

            Assert.That(fight.Allies["healer"].Healed, Is.EqualTo(30));
            Assert.That(fight.Allies["you"].HealedTaken, Is.EqualTo(30));
            Assert.That(fight.Allies["you"].Kills, Is.EqualTo(1));
            Assert.That(fight.Allies["you"].Deaths, Is.EqualTo(1));
            Assert.That(fight.Enemies["crab"].Deaths, Is.EqualTo(1));
            Assert.That(fight.Enemies["crab"].Kills, Is.EqualTo(1));
        }

        [Test]
        public void TwoListeningPartiesFightingEachOtherEachGetTheirOwnFight()
        {
            FightBook book = Book();
            book.Hit("blue", "you", "red", "them", 100, 0);

            var ended = book.Close(10_000, 8000);

            Assert.That(ended, Has.Count.EqualTo(2));
            FightBook.Fight blue = ended.Find(entry => (string)entry.Party == "blue").Fight;
            FightBook.Fight red = ended.Find(entry => (string)entry.Party == "red").Fight;
            Assert.That(blue.Allies["you"].Done, Is.EqualTo(100));
            Assert.That(blue.Enemies["them"].Taken, Is.EqualTo(100));
            Assert.That(red.Allies["them"].Taken, Is.EqualTo(100));
            Assert.That(red.Enemies["you"].Done, Is.EqualTo(100));
        }

        [Test]
        public void HittingYourOwnPartyMakesNoEnemyOfIt()
        {
            FightBook book = Book();
            book.Hit("party", "you", "party", "friend", 5, 0);

            FightBook.Fight fight = book.Close(10_000, 8000)[0].Fight;

            Assert.That(fight.Enemies, Is.Empty);
        }
    }
}
