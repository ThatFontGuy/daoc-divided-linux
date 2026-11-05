using System.Reflection;
using DOL.GS;
using DOL.GS.RealmAbilities;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ArtifactAbilities
    {
        private ModernRaTestScope _scope;
        private Actor _actor;

        private sealed class Actor : GameNPC
        {
            public int Healed;
            private int _health = 1000;
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int Health { get => _health; set => _health = value; }
            public override int MaxHealth => 1000;
            public override int ChangeHealth(GameObject changeSource, eHealthChangeType changeType, int changeAmount) { Healed += changeAmount; return changeAmount; }
        }

        [SetUp]
        public void Setup()
        {
            _scope = new ModernRaTestScope();
            _actor = new Actor();
        }

        [TearDown]
        public void Cleanup()
        {
            foreach (var effect in _actor.effectListComponent.GetEffects())
            {
                effect.End();
                ServiceObjectStore.Remove(effect);
            }

            _actor.effectListComponent.BeginTick();
            ServiceObjectStore.Remove(_actor.effectListComponent);
            _scope.Dispose();
        }

        private void Tick() => _actor.effectListComponent.BeginTick();

        [Test]
        public void FeedbackStopsOneMatchingCrowdControlOnly()
        {
            ModernRr5Classic.Buff(_actor, 60000, eEffect.ArtifactMezFeedback, "Feedback", 1);
            Tick();
            Assert.That(ArtifactAbilities.BlockedByFeedback(_actor, eSpellType.Stun), Is.False, "Mez feedback ignores stuns");
            Assert.That(ArtifactAbilities.BlockedByFeedback(_actor, eSpellType.Mesmerize), Is.True);
            Tick();
            Assert.That(ArtifactAbilities.BlockedByFeedback(_actor, eSpellType.Mesmerize), Is.False, "Only the first one is blocked");
        }

        [Test]
        public void CheatDeathTurnsAKillingBlowIntoAHeal()
        {
            _actor.Health = 100;
            ModernRr5Classic.Buff(_actor, 60000, eEffect.ArtifactCheatDeath, "Cheat Death", 1);
            Tick();
            Assert.That(ArtifactAbilities.CheatDeath(_actor, new AttackData { Target = _actor, Damage = 50 }), Is.False);

            var blow = new AttackData { Target = _actor, Damage = 400, CriticalDamage = 100 };
            Assert.That(ArtifactAbilities.CheatDeath(_actor, blow), Is.True);
            Assert.That(blow.Damage, Is.EqualTo(99));
            Assert.That(blow.CriticalDamage, Is.Zero);
            Assert.That(_actor.Healed, Is.EqualTo(250));
        }

        [Test]
        public void SummonsMatchClassAndRealm()
        {
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.Sun, eCharacterClass.Armsman, eRealm.Albion), Does.Contain("Sun_Polearm"));
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.Sun, eCharacterClass.Valewalker, eRealm.Hibernia), Is.EqualTo(new[] { "Sun_Scythe" }));
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.Sun, eCharacterClass.Wizard, eRealm.Albion), Is.Empty);
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.Moon, eCharacterClass.Healer, eRealm.Midgard), Is.EqualTo(new[] { "Moon_MaceM", "Moon_Staff" }));
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.Trident, eCharacterClass.Hero, eRealm.Hibernia), Is.EqualTo(new[] { "Golden_Trident_of_FlameH" }));
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.Harp, eCharacterClass.Bard, eRealm.Hibernia), Is.EqualTo(new[] { "Phoebus_Summoned_Harp" }));
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.Harp, eCharacterClass.Skald, eRealm.Midgard), Is.Empty);
            Assert.That(ArtifactSummons.ItemsFor(ArtifactSummons.BladeShadow, eCharacterClass.Warrior, eRealm.Midgard), Is.EqualTo(new[] { "Blade_ShadowM" }));
            Assert.That(ArtifactSummons.LostOnDeath("Sun_Crush", night: true), Is.True);
            Assert.That(ArtifactSummons.LostOnDeath("Sun_Crush", night: false), Is.False);
            Assert.That(ArtifactSummons.LostOnDeath("Moon_Staff", night: false), Is.True);
            Assert.That(ArtifactSummons.LostOnDeath("Golden_Trident_of_Flame", night: false), Is.False);
            Assert.That(ArtifactSummons.IsSummoned("Artef_Javelin"), Is.True);
            Assert.That(ArtifactSummons.IsSummoned("Battler_Alb_Crush"), Is.False);
        }

        [Test]
        public void MorphRestoresTheOriginalModelAndAllowsOnlyOne()
        {
            _actor.Model = 100;
            Assert.That(ArtifactAbilities.Morph(_actor, 971, 60000, "Morph", 1), Is.True);
            Tick();
            Assert.That(_actor.Model, Is.EqualTo(971));
            Assert.That(ArtifactAbilities.Morph(_actor, 104, 60000, "Morph", 1), Is.False, "A second morph is refused");
            ModernRr5.Get(_actor, eEffect.ArtifactMorph).End();
            Tick();
            Assert.That(_actor.Model, Is.EqualTo(100));
        }

        [TestCase(eSpellType.ArtifactAllStats)]
        [TestCase(eSpellType.ArtifactSpellDamage)]
        [TestCase(eSpellType.ArtifactFeedback)]
        [TestCase(eSpellType.ArtifactCheatDeath)]
        [TestCase(eSpellType.ArtifactRecovery)]
        [TestCase(eSpellType.ArtifactMorph)]
        [TestCase(eSpellType.ArtifactShatter)]
        [TestCase(eSpellType.ArtifactProcPet)]
        [TestCase(eSpellType.ArtifactSummonItems)]
        public void EveryNewSpellTypeHasAHandler(eSpellType type)
        {
            bool found = false;

            foreach (var handler in typeof(SpellHandler).Assembly.GetTypes())
            {
                foreach (var attribute in handler.GetCustomAttributes<SpellHandlerAttribute>(false))
                    found |= attribute.SpellType == type;
            }

            Assert.That(found, Is.True);
        }
    }
}
