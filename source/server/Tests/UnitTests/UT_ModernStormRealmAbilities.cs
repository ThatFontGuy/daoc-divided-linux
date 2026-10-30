using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS;
using DOL.GS.RealmAbilities;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernStormRealmAbilities
    {
        private ModernRaTestScope _scope;
        private readonly List<Actor> _actors = new();
        private class Actor : GameNPC
        {
            public bool Alive = true, Moving;
            public Actor() { m_ObjectState = eObjectState.Active; Realm = eRealm.Albion; }
            public override byte Level { get; set; } = 50;
            public override int X { get; set; }
            public override bool IsAlive => Alive;
            public override bool IsMoving => Moving;
            public override int MaxHealth => 1000;
            public override int Health { get; set; } = 1000;
            public override int GetModified(eProperty property) => 90;
            public override void StartHealthRegeneration() { }
            public override void StartEnduranceRegeneration() { }
            public override void StartPowerRegeneration() { }
            public override void OnMaxSpeedChange() { }
            public void Leave() => m_ObjectState = eObjectState.Deleted;
        }
        private static DbAbility Definition => new DbAbility { KeyName = "test", Name = "Test", Description = "Test" };
        [SetUp] public void Setup() => _scope = new ModernRaTestScope();
        [TearDown] public void Cleanup()
        {
            foreach (var actor in _actors)
            {
                foreach (var effect in actor.effectListComponent.GetEffects()) { effect.End(); ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick();
                foreach (var effect in actor.effectListComponent.GetEffects()) ServiceObjectStore.Remove(effect);
                ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _actors.Clear(); _scope.Dispose();
        }
        private Actor New(int x = 0) { var actor = new Actor { X = x }; _actors.Add(actor); return actor; }
        private class Root : ModernRealmRoot
        {
            public Root(GameLiving caster, Spell spell) : base(caster, spell) { }
            public int DurationFor(GameLiving target) => CalculateEffectDuration(target);
        }
        private class Storm : ModernRealmStorm
        {
            public readonly List<GameLiving> Hits = new();
            public Storm(GameLiving caster, ModernStormKind kind, int rank) : base(caster, new Point3D(0, 0, 0), kind, rank) { }
            protected override bool Allowed(GameLiving target) => target.Realm == eRealm.Midgard;
            protected override void Hit(GameLiving target, int pulse) => Hits.Add(target);
        }
        [TestCase(1, 5)][TestCase(2, 7)][TestCase(3, 9)][TestCase(4, 12)][TestCase(5, 15)]
        public void IchorUsesFixedRootDurationDespiteAllDurationReductionStats(int rank, int seconds)
        {
            var caster = New(); var target = New();
            var handler = new Root(caster, ModernIchor.RootSpell(rank));
            Assert.That(handler.DurationFor(target), Is.EqualTo(seconds * 1000));
            var effect = handler.CreateECSEffect(new(target, seconds * 1000, 1, handler));
            target.effectListComponent.BeginTick();
            Assert.That(effect.Duration, Is.EqualTo(seconds * 1000));
            Assert.That(effect.PulseFreq, Is.Zero, "Fixed roots must not decay like ordinary snares");
            effect.End(); target.effectListComponent.BeginTick();
            Assert.That(target.effectListComponent.ContainsEffectForEffectType(eEffect.SnareImmunity), Is.True,
                "All root ranks must give NPC-backed actors immunity when removed");
        }
        [Test]
        public void ThornweedSnareHasNoRootImmunityOrStrengthDecay()
        {
            var actor = New(); var spell = new Spell(new DbSpell { Name = "Thornweed", Type = "SpeedDecrease", Target = "Enemy", Value = 50, Duration = 5 }, 50);
            var handler = new Root(actor, spell);
            var effect = handler.CreateECSEffect(new(actor, 5000, 1, handler)); actor.effectListComponent.BeginTick();
            Assert.That(effect.TriggersImmunity, Is.False); Assert.That(effect.PulseFreq, Is.Zero);
            effect.End(); actor.effectListComponent.BeginTick();
            Assert.That(actor.effectListComponent.ContainsEffectForEffectType(eEffect.SnareImmunity), Is.False);
        }
        [Test]
        public void StormPulsesFilterFriendsCasterDeadAndDistantTargets()
        {
            var caster = New(); var enemy = New(100); enemy.Realm = eRealm.Midgard;
            var friend = New(100); var dead = New(); dead.Realm = eRealm.Midgard; dead.Alive = false;
            var far = New(1000); far.Realm = eRealm.Midgard;
            var storm = new Storm(caster, ModernStormKind.Maelstrom, 5);
            storm.PulseTargets(new GameLiving[] { caster, enemy, enemy, friend, dead, far });
            Assert.That(storm.Hits, Is.EqualTo(new[] { enemy }));
        }
        [Test]
        public void StormTimingAndRadiusMatchTheirDistinctRules()
        {
            var caster = New();
            var nm = new Storm(caster, ModernStormKind.Maelstrom, 5);
            var twf = new Storm(caster, ModernStormKind.Thornweed, 1);
            var st = new Storm(caster, ModernStormKind.Tempest, 5);
            Assert.That((nm.Radius, nm.LifetimeSeconds, nm.PulseMilliseconds), Is.EqualTo((350, 30, 5000)));
            Assert.That((twf.Radius, twf.LifetimeSeconds, twf.PulseMilliseconds), Is.EqualTo((500, 10, 3000)));
            Assert.That((st.Radius, st.LifetimeSeconds, st.PulseMilliseconds), Is.EqualTo((360, 35, 5000)));
            Assert.That(nm.ShouldExpire(GameLoop.GameLoopTime), Is.False);
            Assert.That(nm.ShouldExpire(GameLoop.GameLoopTime + 30001), Is.True);
            caster.Leave(); Assert.That(nm.ShouldExpire(GameLoop.GameLoopTime), Is.True);
        }
        [Test]
        public void DamageTablesAndMaelstromRampUseLiveValues()
        {
            Assert.That(ModernNegativeMaelstrom.PulseDamage(5, 1), Is.EqualTo(775.0 / 6));
            Assert.That(ModernNegativeMaelstrom.PulseDamage(5, 6), Is.EqualTo(775));
            Assert.That(ModernNegativeMaelstrom.PulseDamage(5, 8), Is.EqualTo(775));
            Assert.That(new ModernNegativeMaelstrom(Definition, 5).GetReUseDelay(5), Is.EqualTo(450));
            Assert.That(ModernThornweedField.Damage(5), Is.EqualTo(300));
            Assert.That(ModernIchor.Damage(2), Is.EqualTo(343.8));
            Assert.That(new ModernIchor(Definition, 5).MaxLevel, Is.EqualTo(5));
        }
        [Test]
        public void CastContinuationRejectsMovementAndLeaving()
        {
            var caster = New(); var origin = new Point3D(0, 0, 0);
            Assert.That(ModernRealmCast.CanContinue(caster, null, origin), Is.True);
            caster.Moving = true; Assert.That(ModernRealmCast.CanContinue(caster, null, origin), Is.False);
            caster.Moving = false; caster.X = 1; Assert.That(ModernRealmCast.CanContinue(caster, null, origin), Is.False);
            caster.X = 0; caster.Leave(); Assert.That(ModernRealmCast.CanContinue(caster, null, origin), Is.False);
        }
    }
}
