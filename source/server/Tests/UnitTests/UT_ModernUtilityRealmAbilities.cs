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
    public class UT_ModernUtilityRealmAbilities
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
            public override int GetModified(eProperty property) => 0;
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
        public void SpecializedRaHandlersRemainVisibleToLegacyConsumers()
        {
            var actor = New();
            var wind = new ModernLongWind(Def("wind"), 5); var lifter = new ModernLifter(Def("lifter"), 9);
            var minion = new ModernWildMinion(Def("minion"), 9);
            actor.AddAbility(wind, false); actor.AddAbility(lifter, false); actor.AddAbility(minion, false);
            Assert.That(actor.GetAbility<AtlasOF_LongWindAbility>(), Is.SameAs(wind));
            Assert.That(actor.GetAbility<AtlasOF_LifterAbility>(), Is.SameAs(lifter));
            Assert.That(actor.GetAbility<AtlasOF_WildMinionAbility>(), Is.SameAs(minion));
            var exact = new AtlasOF_LongWindAbility(Def("legacy-wind"), 1); actor.AddAbility(exact, false);
            Assert.That(actor.GetAbility<AtlasOF_LongWindAbility>(), Is.SameAs(exact), "Keep existing exact-type preference");
        }
        [Test]
        public void DualThreatAddsMeleeAndSpellCritWithoutAddingHealCrit()
        {
            var actor = New(); var ability = new ModernDualThreat(Def("dual"), 5);
            ability.Activate(actor, false);
            Assert.That(actor.AbilityBonus[eProperty.CriticalMeleeHitChance], Is.EqualTo(20));
            Assert.That(actor.AbilityBonus[eProperty.CriticalSpellHitChance], Is.EqualTo(20));
            Assert.That(actor.AbilityBonus[eProperty.CriticalHealHitChance], Is.Zero);
            ability.Deactivate(actor, false); Assert.That(actor.AbilityBonus[eProperty.CriticalMeleeHitChance], Is.Zero);
        }
        [Test]
        public void ViperIsAPersistentPoisonOnlyBonus()
        {
            var actor = New(); var ability = new ModernViper(Def("viper"), 4); actor.AddAbility(ability, false);
            Assert.That(ability.MaxLevel, Is.EqualTo(5)); Assert.That(ability, Is.Not.InstanceOf<TimedRealmAbility>());
            Assert.That(ModernViper.PoisonMultiplier(actor, true), Is.EqualTo(1.75));
            Assert.That(ModernViper.PoisonMultiplier(actor, false), Is.EqualTo(1));
        }
        [Test]
        public void ReflexOnlyCountersDamagingMeleeHits()
        {
            var hit = new AttackData { AttackType = AttackData.eAttackType.MeleeOneHand, AttackResult = eAttackResult.HitUnstyled, Damage = 10 };
            Assert.That(ModernReflexAttack.Eligible(hit), Is.True);
            hit.AttackResult = eAttackResult.Missed; Assert.That(ModernReflexAttack.Eligible(hit), Is.False);
            hit.AttackResult = eAttackResult.HitUnstyled; hit.AttackType = AttackData.eAttackType.Spell;
            Assert.That(ModernReflexAttack.Eligible(hit), Is.False);
            Assert.That(new ModernReflexAttack(Def("reflex"), 5).GetAmountForLevel(5), Is.EqualTo(50));
        }
        [TestCase(45, 1, 55)][TestCase(60, 5, 70)][TestCase(75, 5, 75)]
        public void JuggernautRestoresExactLevelAndSizeAfterItsCap(int level, int rank, int boosted)
        {
            var pet = New(); pet.Level = (byte)level; pet.Size = 250;
            var effect = ECSGameEffectFactory.Create(new(pet, 60000, ModernJuggernaut.Amount(rank)), static (in i) => new ModernJuggernautEffect(i));
            pet.effectListComponent.BeginTick();
            Assert.That(pet.Level, Is.EqualTo(boosted)); Assert.That(pet.Size, Is.EqualTo(255));
            effect.End(); pet.effectListComponent.BeginTick();
            Assert.That(pet.Level, Is.EqualTo(level)); Assert.That(pet.Size, Is.EqualTo(250));
        }
        [Test]
        public void StrikePredictionProvidesAMinimumInsteadOfStackingEvade()
        {
            var actor = New(); new ModernStrikePrediction(Def("strike"), 5).Execute(actor); actor.effectListComponent.BeginTick();
            Assert.That(ModernStrikePrediction.MinimumChance(actor, 0), Is.EqualTo(200));
            Assert.That(ModernStrikePrediction.MinimumChance(actor, 100), Is.EqualTo(200));
            Assert.That(ModernStrikePrediction.MinimumChance(actor, 300), Is.EqualTo(300));
            Assert.That(actor.AbilityBonus[eProperty.EvadeChance], Is.Zero);
        }
        private sealed class Probe : SpellHandler
        {
            public Probe(GameLiving owner, string type) : base(owner, new Spell(new DbSpell { Name = "probe", Type = type,
                Target = "Enemy", Value = 99, Damage = 100, Duration = 20 }, 50), new SpellLine("test", "test", "test", true)) { }
            public override List<GameLiving> SelectTargets(GameObject target) => new();
            public double DamageFactor => CalculateDamageEffectiveness();
            public double BuffFactor => CalculateBuffDebuffEffectiveness();
            public int DurationFor(GameLiving target) => CalculateEffectDuration(target);
        }
        [Test]
        public void MocScalesDamageAndControlDurationAndSnapshotsTheCast()
        {
            var actor = New(); new ModernMasteryOfConcentration(Def("moc"), 1).Execute(actor); actor.effectListComponent.BeginTick();
            Assert.That(ModernMasteryOfConcentration.Factor(actor), Is.EqualTo(0.25));
            Assert.That(ModernMasteryOfConcentration.SpellFactor(actor, new SpellLine(GlobalSpellsLines.Item_Effects, "items", "items", true)), Is.EqualTo(1));
            var damage = new Probe(actor, "DirectDamage"); damage.StartSpell(actor);
            var root = new Probe(actor, "SpeedDecrease"); root.StartSpell(actor);
            Assert.That(damage.DamageFactor, Is.EqualTo(0.25));
            Assert.That(root.BuffFactor, Is.EqualTo(1), "Root strength must not turn into a weak snare");
            Assert.That(root.DurationFor(actor), Is.EqualTo(5000));
            actor.effectListComponent.GetEffects(eEffect.MasteryOfConcentration).Single().End(); actor.effectListComponent.BeginTick();
            Assert.That(ModernMasteryOfConcentration.Factor(actor), Is.EqualTo(1));
            Assert.That(damage.DamageFactor, Is.EqualTo(0.25), "A cast made under MoC must not gain full strength when it expires");
            Assert.That(actor.Disabled, Is.EqualTo(600000));
        }
    }
}
