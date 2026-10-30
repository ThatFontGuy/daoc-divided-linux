using System.Collections.Generic;
using DOL.Database;
using DOL.GS;
using DOL.GS.Effects;
using DOL.GS.RealmAbilities;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_LiveRr5Abilities
    {
        private ModernRaTestScope _scope;
        private readonly List<Actor> _actors = new();
        private sealed class Actor : GameNPC
        {
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int MaxHealth => 1000;
        }
        private static DbAbility Def(string key) => new DbAbility { KeyName = key, Name = key, Description = key };
        [SetUp] public void Setup() => _scope = new ModernRaTestScope();
        [TearDown] public void Cleanup()
        {
            foreach (var actor in _actors)
            {
                foreach (var effect in actor.effectListComponent.GetEffects()) { effect.End(); ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick(); ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _actors.Clear(); _scope.Dispose();
        }
        private Actor New() { var actor = new Actor(); _actors.Add(actor); return actor; }

        [Test]
        public void SelfBuffRr5sUseTheLiveReuseTimers()
        {
            Assert.That(new FerociousWillAbility(Def("fw"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new BladeBarrierAbility(Def("bb"), 1).GetReUseDelay(1), Is.EqualTo(300));
            Assert.That(new RuneOfUtterAgilityAbility(Def("rua"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new CombatAwarenessAbility(Def("ca"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new SoldiersCitadelAbility(Def("sc"), 1).GetReUseDelay(1), Is.EqualTo(600), "Live 1.129: 10 minutes");
            Assert.That(new TestudoAbility(Def("t"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ShieldOfImmunityAbility(Def("soi"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ArmsLengthAbility(Def("al"), 1).GetReUseDelay(1), Is.EqualTo(600));
        }

        [Test]
        public void FerociousWillAddsAbsorptionAndThe1108ResistsThenRemovesThem()
        {
            var actor = New(); var effect = new FerociousWillEffect();
            effect.Start(actor);
            Assert.That(actor.BaseBuffBonusCategory[eProperty.PhysicalAbsorption], Is.EqualTo(25));
            Assert.That(actor.OtherBonus[eProperty.Resist_Heat], Is.EqualTo(FerociousWillEffect.RESIST_BONUS));
            Assert.That(actor.OtherBonus[eProperty.Resist_Slash], Is.EqualTo(FerociousWillEffect.RESIST_BONUS));
            effect.Stop();
            Assert.That(actor.BaseBuffBonusCategory[eProperty.PhysicalAbsorption], Is.Zero);
            Assert.That(actor.OtherBonus[eProperty.Resist_Heat], Is.Zero);
            Assert.That(FerociousWillEffect.CC_SHRUG, Is.EqualTo(25));
        }

        [Test]
        public void AllureOfDeathResistsNearsightAtTheLive75Percent()
        {
            Assert.That(AllureofDeathEffect.ccchance, Is.EqualTo(75));
            Assert.That(AllureofDeathEffect.nschance, Is.EqualTo(75));
        }

        [Test]
        public void TestudoSlowsTheWarrior() => Assert.That(TestudoEffect.SPEED_FACTOR, Is.EqualTo(0.5));
    }
}
