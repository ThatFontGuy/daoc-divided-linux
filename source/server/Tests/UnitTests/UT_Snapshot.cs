using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.ServerRules;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Snapshot (Armsman): ranged shots carry on while moving, only while the effect is up.</summary>
    [TestFixture, NonParallelizable]
    public class UT_Snapshot
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
        public void ShotsCarryOnWhileMovingOnlyDuringSnapshot()
        {
            var armsman = new Actor();
            Assert.That(SnapshotECSGameEffect.KeepsShotOnMove(armsman), Is.False);
            var effect = new SnapshotECSGameEffect(new(armsman, DOL.GS.SkillHandler.SnapshotAbilityHandler.DURATION, 1));
            Assert.That(effect.Start(), Is.True);
            armsman.effectListComponent.BeginTick();
            try
            {
                Assert.That(SnapshotECSGameEffect.KeepsShotOnMove(armsman), Is.True);
            }
            finally
            {
                effect.End();
                armsman.effectListComponent.BeginTick();
            }
            Assert.That(SnapshotECSGameEffect.KeepsShotOnMove(armsman), Is.False);
        }
    }
}
