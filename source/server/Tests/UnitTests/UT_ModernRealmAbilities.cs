using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.PropertyCalc;
using DOL.GS.RealmAbilities;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernRealmAbilities
    {
        private ModernRaTestScope _scope;
        [SetUp] public void Setup() => _scope = new ModernRaTestScope();
        [TearDown] public void Cleanup() => _scope.Dispose();

        private static DbAbility Definition => new DbAbility { KeyName = "test", Name = "Test", Description = "Test" };

        [Test]
        public void LivePassivesExposeAllNineRanksWithoutGlobalScalingFlags()
        {
            var strength = new ModernAugStr(Definition, 1);
            var crit = new ModernMasteryOfPain(Definition, 1);
            Assert.That(strength.MaxLevel, Is.EqualTo(9));
            Assert.That(strength.GetAmountForLevel(9), Is.EqualTo(48));
            Assert.That(crit.GetAmountForLevel(9), Is.EqualTo(39));
            Assert.That(strength.CheckRequirement(null), Is.True);
            int total = 0;
            for (int i = 0; i < 9; i++)
                total += strength.CostForUpgrade(i);
            Assert.That(total, Is.EqualTo(34));
            Assert.That(strength.CostForUpgrade(9), Is.EqualTo(1000));
        }

        [Test]
        public void DeterminationUsesModernDurationsAndSeparateLightTankCosts()
        {
            var normal = new ModernDetermination(Definition, 9);
            var light = new ModernLightTankDetermination(Definition, 9);
            Assert.That(normal.GetAmountForLevel(9), Is.EqualTo(55));
            Assert.That(light.GetAmountForLevel(9), Is.EqualTo(55));
            int total = 0;
            for (int i = 0; i < 9; i++)
                total += light.CostForUpgrade(i);
            Assert.That(total, Is.EqualTo(25));
            Assert.That(light.CostForUpgrade(3), Is.EqualTo(2));
            Assert.That(normal.CostForUpgrade(3), Is.EqualTo(3));
        }

        [TestCase(1, 500, 600)]
        [TestCase(2, 600, 450)]
        [TestCase(3, 700, 300)]
        [TestCase(4, 850, 240)]
        [TestCase(5, 1000, 180)]
        public void FirstAidUsesFinalLiveHealAndReuse(int rank, int heal, int reuse)
        {
            var ability = new ModernFirstAid(Definition, rank);
            Assert.That(ability.MaxLevel, Is.EqualTo(5));
            Assert.That(ModernFirstAid.HealAmount(2000, rank), Is.EqualTo(heal));
            Assert.That(ability.GetReUseDelay(rank), Is.EqualTo(reuse));
            Assert.That(ability.CostForUpgrade(rank - 1), Is.EqualTo(new[] { 5, 5, 5, 7, 8 }[rank - 1]));
        }

        [Test]
        public void PowerAndHealthAreFlatBonusesRatherThanLegacyPercentages()
        {
            Assert.That(new ModernToughness(Definition, 9).GetAmountForLevel(9), Is.EqualTo(400));
            Assert.That(new ModernEtherealBond(Definition, 9).GetAmountForLevel(9), Is.EqualTo(200));
            Assert.That(new ModernDeterminationHybrid(Definition, 9).MaxLevel, Is.EqualTo(9));
        }

        [Test]
        public void FlatBonusesActivateAndRespecWithoutLeavingLegacyPercentageBonuses()
        {
            var actor = (GameNPC)RuntimeHelpers.GetUninitializedObject(typeof(GameNPC));
            typeof(GameLiving).GetField("<AbilityBonus>k__BackingField", BindingFlags.Instance | BindingFlags.NonPublic)
                .SetValue(actor, new PropertyIndexer());
            var health = new ModernToughness(Definition, 9);
            var power = new ModernEtherealBond(Definition, 9);
            health.Activate(actor, false);
            power.Activate(actor, false);
            Assert.That(actor.AbilityBonus[eProperty.MaxHealth], Is.EqualTo(400));
            Assert.That(actor.AbilityBonus[eProperty.MaxMana], Is.EqualTo(200));
            Assert.That(actor.AbilityBonus[eProperty.Of_Toughness], Is.Zero);
            Assert.That(actor.AbilityBonus[eProperty.PowerPool], Is.Zero);
            health.Deactivate(actor, false);
            power.Deactivate(actor, false);
            Assert.That(actor.AbilityBonus[eProperty.MaxHealth], Is.Zero);
            Assert.That(actor.AbilityBonus[eProperty.MaxMana], Is.Zero);
        }

        [Test]
        public void BotPlannerCanBuyModernPassivesWithoutOldStatPrerequisites()
        {
            const string key = "AtlasOF_MasteryOfPain";
            var available = new Dictionary<string, int> { [key] = 9 };
            var legacy = AutonomousBotRealmAbilities.Plan(available, AutonomousBotRealmAbilities.Archetype.Melee, 2, 1,
                (_, rank) => ModernRealmRanks.PassiveCost(rank));
            var modern = AutonomousBotRealmAbilities.Plan(available, AutonomousBotRealmAbilities.Archetype.Melee, 2, 1,
                (_, rank) => ModernRealmRanks.PassiveCost(rank), new HashSet<string> { key });
            Assert.That(legacy, Is.Empty);
            Assert.That(modern[key], Is.EqualTo(1));
        }
    }
}
