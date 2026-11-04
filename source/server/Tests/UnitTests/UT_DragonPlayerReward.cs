using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_DragonPlayerReward
    {
        private sealed class RaidPlayer : GamePlayer
        {
            private RaidPlayer() : base(null, null) { }
            public override eRealm Realm { get; set; }
            public eObjectState State;
            public override eObjectState ObjectState { get => State; set => State = value; }
        }

        private static RaidPlayer Player(eRealm realm, GameObject.eObjectState state = GameObject.eObjectState.Active)
        {
            RaidPlayer player = (RaidPlayer)RuntimeHelpers.GetUninitializedObject(typeof(RaidPlayer));
            player.Realm = realm;
            player.State = state;
            return player;
        }

        private static DbItemTemplate Item(string name) => new() { Id_nb = name, Name = name };

        [Test]
        public void FightersAndTheDragonsRealmNearbyAreOwedAnItem()
        {
            RaidPlayer fighter = Player(eRealm.Midgard);
            RaidPlayer bystander = Player(eRealm.Albion);
            RaidPlayer enemyBystander = Player(eRealm.Hibernia);

            List<GamePlayer> owed = DragonPlayerReward.Recipients(eRealm.Albion, [fighter], [bystander, enemyBystander, fighter], []);

            Assert.That(owed, Is.EquivalentTo(new GamePlayer[] { fighter, bystander }));
        }

        [Test]
        public void APlayerTheSharePaidIsNotPaidTwice()
        {
            RaidPlayer paid = Player(eRealm.Albion);
            RaidPlayer unpaid = Player(eRealm.Albion);

            List<GamePlayer> owed = DragonPlayerReward.Recipients(eRealm.Albion, [paid, unpaid], [], [paid]);

            Assert.That(owed, Is.EqualTo(new GamePlayer[] { unpaid }));
        }

        [Test]
        public void APlayerWhoLeftTheWorldIsSkipped()
        {
            RaidPlayer gone = Player(eRealm.Albion, GameObject.eObjectState.Deleted);

            Assert.That(DragonPlayerReward.Recipients(eRealm.Albion, [gone], [], []), Is.Empty);
        }

        [Test]
        public void PickFollowsDropChanceAndSkipsWhatThePlayerCannotUse()
        {
            DbItemTemplate common = Item("common"), rare = Item("rare"), enemyOnly = Item("enemy"), never = Item("never");
            var table = new List<(DbItemTemplate, int)> { (common, 90), (rare, 10), (enemyOnly, 100), (never, 0), (null, 50) };
            Random random = new(1);

            var picks = Enumerable.Range(0, 2000).Select(_ => DragonPlayerReward.Pick(table, i => i != enemyOnly, random)).ToList();

            Assert.That(picks, Has.None.Null);
            Assert.That(picks, Has.None.EqualTo(enemyOnly));
            Assert.That(picks, Has.None.EqualTo(never));
            Assert.That(picks.Count(p => p == rare), Is.InRange(100, 300));
        }

        [Test]
        public void PickGivesNothingFromAnEmptyOrUnusableTable()
        {
            Assert.That(DragonPlayerReward.Pick([], _ => true, new Random(1)), Is.Null);
            Assert.That(DragonPlayerReward.Pick([(Item("x"), 20)], _ => false, new Random(1)), Is.Null);
        }
    }
}
