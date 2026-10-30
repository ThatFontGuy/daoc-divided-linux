using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.ServerRules;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Call of a Thousand Storms: eight more attackers before the defense penalties, against monsters of level 50+.</summary>
    [TestFixture, NonParallelizable]
    public class UT_ThousandStorms
    {
        private GameServer _previous;
        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
            protected override IServerRules ServerRulesImpl => new NormalServerRules();
        }
        private sealed class Actor : GameNPC
        {
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int GetModified(eProperty property) => 0;
            public override int MaxHealth => 1000;
        }

        [SetUp]
        public void Setup()
        {
            _previous = GameServer.Instance;
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
        }

        [TearDown]
        public void Cleanup() => GameServer.LoadTestDouble(_previous);

        [Test]
        public void OnlyLevel50MonstersAreAffectedAndOnlyWhileTheCallIsUp()
        {
            var thane = new Actor { Level = 45 };
            var boss = new Actor { Level = 55 };
            var trash = new Actor { Level = 49 };
            Assert.That(ThousandStormsECSGameEffect.IsQualifyingMonster(boss), Is.True);
            Assert.That(ThousandStormsECSGameEffect.IsQualifyingMonster(trash), Is.False);
            Assert.That(ThousandStormsECSGameEffect.EffectiveAttackers(thane, boss, 6), Is.EqualTo(6), "no effect, no change");

            var effect = new ThousandStormsECSGameEffect(new(thane, ThousandStormsECSGameEffect.EXTRA_ATTACKERS * 1000, 1));
            Assert.That(effect.Start(), Is.True);
            thane.effectListComponent.BeginTick();
            try
            {
                Assert.That(ThousandStormsECSGameEffect.ExtraAttackers(thane, boss), Is.EqualTo(8));
                Assert.That(ThousandStormsECSGameEffect.EffectiveAttackers(thane, boss, 6), Is.EqualTo(1), "six attackers count as one");
                Assert.That(ThousandStormsECSGameEffect.EffectiveAttackers(thane, boss, 12), Is.EqualTo(4));
                Assert.That(ThousandStormsECSGameEffect.EffectiveAttackers(thane, trash, 6), Is.EqualTo(6), "below level 50 unchanged");
            }
            finally
            {
                effect.End();
                thane.effectListComponent.BeginTick();
            }
            Assert.That(ThousandStormsECSGameEffect.ExtraAttackers(thane, boss), Is.Zero);
        }
    }
}
