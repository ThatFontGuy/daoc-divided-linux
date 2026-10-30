using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>
    /// 2026-10-27 overnight run, 3,000 bots: the effect service grew to 30 million effects and each tick spent 326 ms in it.
    /// Sovereign chants reached every friendly NPC in range, two Sovereigns swapped their chant on each member every pulse,
    /// and effects ended before their start callback ran were put back in the service for good.
    /// </summary>
    [TestFixture, NonParallelizable]
    public class UT_ChantScopeAndEffectLeak
    {
        private GameServer _previous;

        private sealed class EmptyServer : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
        }

        private sealed class Actor : GameNPC
        {
            public override int MaxHealth => 100;
            public override bool IsAlive => true;
            public override int GetModified(eProperty property) => 100;
        }

        [SetUp]
        public void SetUp()
        {
            _previous = GameServer.Instance;
            GameServer.LoadTestDouble((EmptyServer)RuntimeHelpers.GetUninitializedObject(typeof(EmptyServer)));
        }

        [TearDown]
        public void TearDown() => GameServer.LoadTestDouble(_previous);

        [TestCase("StormforgedChant", 1500)]
        [TestCase("StormforgedAvatar", 350)]
        public void SelfSpellsWithARadiusOnlyTargetTheCaster(string type, int radius)
        {
            var caster = new Actor();
            var spell = new Spell(new DbSpell { Type = type, Target = "Self", Radius = radius, Duration = 600, Frequency = 40 }, 1);
            var line = new SpellLine("test", "test", "test", true);
            SpellHandler handler = type == "StormforgedChant" ? new StormforgedChant(caster, spell, line) : new StormforgedAvatar(caster, spell, line);

            Assert.That(handler.SelectTargets(caster), Is.EqualTo(new GameLiving[] { caster }));
        }

        [Test]
        public void ASingerKeepsTheirOwnSong() =>
            Assert.That(StormforgedChantEffect.YieldsTo(otherIsOwnSong: true, otherDamage: 11, ourDamage: 50), Is.True);

        [Test]
        public void AnEqualChantAlreadyHeldIsLeftAlone() =>
            Assert.That(StormforgedChantEffect.YieldsTo(otherIsOwnSong: false, otherDamage: 50, ourDamage: 50), Is.True);

        [Test]
        public void AStrictlyStrongerChantStillTakesOver() =>
            Assert.That(StormforgedChantEffect.YieldsTo(otherIsOwnSong: false, otherDamage: 40, ourDamage: 50), Is.False);

        [Test]
        public void EndedEffectsLeaveTheServiceUnlessRestarting()
        {
            Assert.That(EffectService.IsStaleEndedEffect(ended: true, starting: false, enabling: false), Is.True);
            Assert.That(EffectService.IsStaleEndedEffect(ended: true, starting: true, enabling: false), Is.False);
            Assert.That(EffectService.IsStaleEndedEffect(ended: true, starting: false, enabling: true), Is.False);
            Assert.That(EffectService.IsStaleEndedEffect(ended: false, starting: false, enabling: false), Is.False);
        }
    }
}
