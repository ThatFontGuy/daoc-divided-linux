using System.Collections.Generic;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Arawn's Singe and the other Heretic ramping focus spells (RampingDamageFocus).</summary>
    [TestFixture, NonParallelizable]
    public class UT_HereticRampingFocus
    {
        private ModernRaTestScope _scope;
        private readonly List<GameNPC> _actors = new();
        private sealed class Actor : GameNPC
        {
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int MaxHealth => 1000;
        }
        private sealed class Probe(GameLiving caster, Spell spell, SpellLine line) : RampingDamageFocus(caster, spell, line)
        {
            public readonly List<GameLiving> Damaged = new();
            protected override void DealDamage(GameLiving target) => Damaged.Add(target);
        }
        [SetUp] public void Setup() { _scope = new ModernRaTestScope(); GameLiving.LoadCalculators(); }
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

        private static Spell Singe() => new(new DbSpell { SpellID = 70000, Name = "Arawn's Singe", Type = "RampingDamageFocus", Target = "Enemy",
            Range = 1650, Duration = 16, Frequency = 15, Pulse = 1, Damage = 5, DamageType = 13, Power = 1, LifeDrainReturn = 50,
            AmnesiaChance = 150, PulsePower = 1 }, 1);

        [Test]
        public void EveryLandedPulseDealsDamage()
        {
            // ECS pulses land through StartSpell -> ApplyEffectOnTarget. The ramping damage used to live only in the
            // legacy OnSpellPulse, so each pulse rolled a resist and applied a blank effect: one hit per cast, no ramp.
            Actor caster = New(), target = New();
            var probe = new Probe(caster, Singe(), new SpellLine("test", "test", "test", true));
            probe.ApplyEffectOnTarget(target);
            probe.ApplyEffectOnTarget(target);
            target.effectListComponent.BeginTick();
            Assert.That(probe.Damaged, Is.EqualTo(new[] { target, target }));
            Assert.That(target.effectListComponent.GetEffects(), Is.Empty, "no blank duration effect on the target");
        }

        [Test]
        public void ResistIsTheNormalSpellChance()
        {
            Actor caster = New(), target = New();
            Assert.That(new RampingDamageFocus(caster, Singe(), new SpellLine("test", "test", "test", true)).CalculateSpellResistChance(target),
                Is.EqualTo(12.5), "level-matched resist, like any spell");
        }
    }
}
