using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS;
using DOL.GS.PropertyCalc;
using DOL.GS.RealmAbilities;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernStealthRealmAbilities
    {
        private ModernRaTestScope _scope;
        private readonly List<Actor> _actors = new();
        private sealed class Actor : GameNPC
        {
            public int Disabled;
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int MaxHealth => 1000;
            public override void DisableSkill(Skill skill, int duration) { Disabled = duration; }
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
        public void MasteryOfStealthUsesThePre1121NineRankTables()
        {
            var mos = new ModernMasteryOfStealth(Def("mos"), 1);
            Assert.That(mos.MaxLevel, Is.EqualTo(9));
            Assert.That(Enumerable.Range(1, 9).Select(mos.GetAmountForLevel), Is.EqualTo(new[] { 10, 15, 20, 25, 30, 35, 40, 45, 50 }));
            Assert.That(Enumerable.Range(1, 9).Select(ModernMasteryOfStealth.Detection), Is.EqualTo(new[] { 75, 125, 175, 235, 300, 375, 450, 535, 625 }));
            Assert.That(Enumerable.Range(0, 9).Select(mos.CostForUpgrade), Is.EqualTo(new[] { 1, 1, 2, 3, 3, 5, 5, 7, 7 }));
            Assert.That(mos.CheckRequirement(null), Is.True, "No Augmented Quickness prerequisite on live");
        }

        [Test]
        public void MasteryOfStealthIsVisibleToTheStealthSpeedCalculator()
        {
            var actor = New(); var mos = new ModernMasteryOfStealth(Def("mos"), 9); actor.AddAbility(mos, false);
            Assert.That(actor.GetAbility<AtlasOF_MasteryOfStealth>(), Is.SameAs(mos));
        }

        [Test]
        public void MasteryOfStealthDetectionIsCounteredByCamouflageAndMutualDetectHidden()
        {
            var archer = New(); var enemy = New();
            Assert.That(ModernMasteryOfStealth.DetectionBonus(archer, enemy), Is.Zero, "No ability, no bonus");
            archer.AddAbility(new ModernMasteryOfStealth(Def("mos"), 5), false);
            Assert.That(ModernMasteryOfStealth.DetectionBonus(archer, enemy), Is.EqualTo(300));
            archer.AddAbility(SkillBase.GetAbility(Abilities.DetectHidden) ?? new Ability(new DbAbility { KeyName = Abilities.DetectHidden, Name = "dh", Description = "dh" }, 0), false);
            enemy.AddAbility(SkillBase.GetAbility(Abilities.DetectHidden) ?? new Ability(new DbAbility { KeyName = Abilities.DetectHidden, Name = "dh", Description = "dh" }, 0), false);
            Assert.That(ModernMasteryOfStealth.DetectionBonus(archer, enemy), Is.Zero, "Assassins detecting assassins");
        }

        [Test]
        public void VanishIsTheTrainableFiveRankRealmAbilityAgain()
        {
            var vanish = new ModernVanish(Def("vanish"), 1);
            Assert.That(vanish.MaxLevel, Is.EqualTo(5));
            Assert.That(vanish.GetReUseDelay(5), Is.EqualTo(900));
            Assert.That(Enumerable.Range(1, 5).Select(ModernVanish.Duration), Is.EqualTo(new[] { 3, 3, 4, 5, 6 }));
            Assert.That(ModernVanish.Speed(1), Is.EqualTo(1.0));
            Assert.That(ModernVanish.Speed(2), Is.EqualTo(MaxSpeedCalculator.SPEED1));
            Assert.That(ModernVanish.Speed(3), Is.EqualTo(MaxSpeedCalculator.SPEED3));
            Assert.That(ModernVanish.Speed(5), Is.EqualTo(MaxSpeedCalculator.SPEED5));
            Assert.That(Enumerable.Range(0, 5).Select(vanish.CostForUpgrade), Is.EqualTo(new[] { 5, 5, 5, 7, 8 }));
            Assert.That(ModernVanish.LockoutMs, Is.EqualTo(30000), "1.123: 30 s disarm and silence");
        }

        [Test]
        public void VanishGrantsSpeedAndLocksOutAttacksAndCastingThenRestoresSpeed()
        {
            var actor = New();
            new ModernVanish(Def("vanish"), 5).Execute(actor); actor.effectListComponent.BeginTick();
            Assert.That(actor.Disabled, Is.EqualTo(900000));
            var effect = actor.effectListComponent.GetAbilityEffects(eEffect.Vanish).OfType<ModernVanishEffect>().Single();
            Assert.That(effect.Duration, Is.EqualTo(6000));
            Assert.That(actor.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(MaxSpeedCalculator.SPEED5));
            Assert.That(actor.DisarmedTime - GameLoop.GameLoopTime, Is.EqualTo(ModernVanish.LockoutMs).Within(50));
            Assert.That(actor.SilencedTime - GameLoop.GameLoopTime, Is.EqualTo(ModernVanish.LockoutMs).Within(50));
            effect.End(); actor.effectListComponent.BeginTick();
            Assert.That(actor.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(1.0));
        }

        [Test]
        public void VanishOneKeepsNormalSpeed()
        {
            var actor = New();
            new ModernVanish(Def("vanish"), 1).Execute(actor); actor.effectListComponent.BeginTick();
            Assert.That(actor.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(1.0));
            Assert.That(actor.Disabled, Is.EqualTo(900000));
        }
    }
}
