using System.Collections.Generic;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS;
using DOL.GS.RealmAbilities;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernWarlockLive
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
        public void TorrentOnlyHitsRealmTargets()
        {
            var monster = New();
            Assert.That(WarlockTorrentHandler.IsRealmTarget(monster), Is.False, "Ordinary monsters are never hit");
            var pet = New(); pet.SetOwnBrain(new ControlledMobBrain(New()));
            Assert.That(WarlockTorrentHandler.IsRealmTarget(pet), Is.True, "Pets are");
        }

        [Test]
        public void HealingAuraRaisesHealingEffectiveness()
        {
            var spell = new Spell(new DbSpell { Name = "Calming Incantation", Type = eSpellType.WarlockHealingAura.ToString(), Target = "Group", Value = 8 }, 50);
            var handler = new WarlockHealingAuraHandler(New(), spell, new SpellLine("test", "test", "test", true));
            Assert.That(handler.Property1, Is.EqualTo(eProperty.HealingEffectiveness));
        }

        [Test]
        public void PetFearLeavesASixtySecondImmunity()
        {
            var pet = New();
            Assert.That(WarlockPetFearHandler.IsImmune(pet), Is.False);
            var fear = (WarlockPetFearEffect)ECSGameEffectFactory.Create(new(pet, 5000, 1),
                static (in ECSGameEffectInitParams i) => new WarlockPetFearEffect(i, null));
            pet.effectListComponent.BeginTick();
            Assert.That(WarlockPetFearHandler.IsImmune(pet), Is.True, "Cannot be feared again while feared");
            fear.End(); pet.effectListComponent.BeginTick();
            Assert.That(pet.effectListComponent.ContainsEffectForEffectType(eEffect.WarlockPetFearImmunity), Is.True);
            Assert.That(WarlockPetFearHandler.ImmunityMs, Is.EqualTo(60000));
        }

        [Test]
        public void SecondaryTooltipsExplainThePrimerCostAndPrimersShowTheirRank()
        {
            var line = new SpellLine("Cursing Spec", "Cursing Spec", "Cursing Spec", true);
            var burst = new Spell(new DbSpell { SpellID = 66080, Name = "Spellbinder's Blast", Type = "DirectDamage", Target = "Enemy",
                Damage = 325, Radius = 300, IsSecondary = true }, 45);
            string delve = SpellDelve.GetSpellString(new DirectDamageSpellHandler(New(), burst, line));
            Assert.That(delve, Does.Contain("Secondary spell: needs an active primer"));
            Assert.That(delve, Does.Contain("none with a Powerless primer"));
            var normal = new Spell(new DbSpell { SpellID = 66070, Name = "Wrenching Curse", Type = "DirectDamage", Target = "Enemy", Damage = 145 }, 33);
            Assert.That(SpellDelve.GetSpellString(new DirectDamageSpellHandler(New(), normal, line)), Does.Not.Contain("Secondary spell"));
            var primer = new Spell(new DbSpell { SpellID = 66022, Name = "Skillful Cast", Type = "WarlockPrimer", Target = "Self",
                Description = "Toggle maintained primer: 25% cast-time penalty; free secondary. Secondary cost: 0% base power." }, 28);
            Assert.That(new WarlockPrimerHandler(New(), primer, line).ShortDescription, Does.Contain("free secondary"));
        }

        [Test]
        public void BoilingCauldronBedazzlesWithFumbleAndMiscast()
        {
            var target = New();
            Assert.That(ModernBoilingCauldron.IsBedazzled(target), Is.False);
            Assert.That(ModernBoilingCauldron.Miscasts(target), Is.False);
            ModernBoilingCauldron.Bedazzle(target); target.effectListComponent.BeginTick();
            Assert.That(ModernBoilingCauldron.IsBedazzled(target), Is.True);
            Assert.That(target.DebuffCategory[eProperty.FumbleChance], Is.EqualTo(30));
            Assert.That(ModernRr5.Get(target, eEffect.ModernBedazzle).Duration, Is.EqualTo(20000), "1.129b: 20 seconds");
            Assert.That(new ModernBoilingCauldron(new DbAbility { KeyName = "bc", Name = "bc", Description = "bc" }, 1).GetReUseDelay(1), Is.EqualTo(600));
            ModernRr5.Get(target, eEffect.ModernBedazzle).End(); target.effectListComponent.BeginTick();
            Assert.That(target.DebuffCategory[eProperty.FumbleChance], Is.Zero);
        }
    }
}
