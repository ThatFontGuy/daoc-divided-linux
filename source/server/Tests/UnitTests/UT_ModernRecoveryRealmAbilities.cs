using System;
using System.Runtime.CompilerServices;
using System.Reflection;
using DOL.Database;
using DOL.GS;
using DOL.GS.RealmAbilities;
using NUnit.Framework;

namespace DOL.UnitTests
{
    internal sealed class ModernRaTestScope : IDisposable
    {
        private readonly GameServer _previous;
        private readonly PetTestLanguageScope _language;
        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
            protected override DOL.GS.ServerRules.IServerRules ServerRulesImpl => new DOL.GS.ServerRules.NormalServerRules();
        }
        public ModernRaTestScope()
        {
            _previous = GameServer.Instance;
            _language = new PetTestLanguageScope();
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
        }
        public void Dispose() { GameServer.LoadTestDouble(_previous); _language.Dispose(); }
    }

    [TestFixture, NonParallelizable]
    public class UT_ModernRecoveryRealmAbilities
    {
        private ModernRaTestScope _scope;
        [SetUp] public void Setup() => _scope = new ModernRaTestScope();
        [TearDown] public void Cleanup() => _scope.Dispose();

        private class Actor : GameNPC
        {
            public bool Combat;
            public bool Full;
            public int Restored, Disabled;
            public string Resource;
            public override bool IsAlive => true;
            public override bool IsSitting { get; set; }
            public override bool InCombat => Combat;
            public override int MaxHealth => 2000;
            public override int MaxMana => 1000;
            public override int MaxEndurance => 100;
            public override int ChangeHealth(GameObject source, eHealthChangeType kind, int amount) => Record("health", amount);
            public override int ChangeMana(GameObject source, eManaChangeType kind, int amount) => Record("power", amount);
            public override int ChangeEndurance(GameObject source, eEnduranceChangeType kind, int amount) => Record("endurance", amount);
            private int Record(string resource, int amount) { Resource = resource; Restored = Full ? 0 : amount; return Restored; }
            public override void DisableSkill(Skill skill, int duration) { Disabled = duration; }
        }
        private static DbAbility Definition => new DbAbility { KeyName = "test", Name = "Test", Description = "Test" };
        private static ModernRecoveryAbility Ability(string kind, int rank) => kind switch
        {
            "IP" => new ModernIgnorePain(Definition, rank), "MCL" => new ModernMCL(Definition, rank),
            "RP" => new ModernRagingPower(Definition, rank), _ => new ModernSecondWind(Definition, rank)
        };

        [TestCase("IP", 1, "health", 400, 900)]
        [TestCase("IP", 5, "health", 1600, 900)]
        [TestCase("MCL", 2, "power", 400, 180)]
        [TestCase("MCL", 5, "power", 1000, 180)]
        [TestCase("RP", 2, "power", 350, 600)]
        [TestCase("RP", 5, "power", 800, 600)]
        [TestCase("SW", 1, "endurance", 100, 900)]
        [TestCase("SW", 5, "endurance", 100, 120)]
        public void RecoveryExecutesRealResourceChangeAndCooldown(string kind, int rank, string resource, int restored, int reuse)
        {
            var actor = (Actor)RuntimeHelpers.GetUninitializedObject(typeof(Actor));
            actor.Combat = kind != "MCL";
            var ability = Ability(kind, rank);
            ability.Execute(actor);
            Assert.That(actor.Resource, Is.EqualTo(resource));
            Assert.That(actor.Restored, Is.EqualTo(restored));
            Assert.That(actor.Disabled, Is.EqualTo(reuse * 1000));
            ability.Activate(actor, false);
            ability.Level = rank == 5 ? 4 : rank + 1;
            Assert.That(actor.Disabled, Is.EqualTo(reuse * 1000), "Training must not reset the active cooldown");
        }
        [TestCase("IP")][TestCase("MCL")][TestCase("RP")][TestCase("SW")]
        public void FullResourceDoesNotConsumeRecovery(string kind)
        {
            var actor = (Actor)RuntimeHelpers.GetUninitializedObject(typeof(Actor)); actor.Full = true;
            Ability(kind, 5).Execute(actor);
            Assert.That(actor.Disabled, Is.Zero);
        }
        [Test]
        public void MclCannotBeUsedInCombatAndRecoveryCannotBeUsedWhileSitting()
        {
            var actor = (Actor)RuntimeHelpers.GetUninitializedObject(typeof(Actor)); actor.Combat = true;
            Ability("MCL", 5).Execute(actor);
            Assert.That(actor.Resource, Is.Null);
            actor.IsSitting = true;
            Ability("IP", 5).Execute(actor);
            Assert.That(actor.Resource, Is.Null);
            Assert.That(actor.Disabled, Is.Zero);
        }
        [TestCase(1, 5, 900)][TestCase(2, 2, 900)][TestCase(3, 0, 900)][TestCase(4, 0, 600)][TestCase(5, 0, 300)]
        public void PurgeRanksHaveSeparateActivationDelaysAndReuse(int rank, int delay, int reuse)
        {
            var purge = new ModernPurge(Definition, rank);
            Assert.That(ModernPurge.DelaySeconds(rank), Is.EqualTo(delay));
            Assert.That(purge.GetReUseDelay(rank), Is.EqualTo(reuse));
            Assert.That(purge.MaxLevel, Is.EqualTo(5));
            Assert.That(purge.CostForUpgrade(rank - 1), Is.EqualTo(ModernRealmRanks.ActiveCost(rank - 1)));
        }
        [Test]
        public void RemainingPassiveAndChargeRanksUseExplicitTables()
        {
            Assert.That(new ModernSerenity(Definition, 5).GetAmountForLevel(5), Is.EqualTo(7));
            Assert.That(new ModernSerenity(Definition, 5).MaxLevel, Is.EqualTo(5));
            Assert.That(new ModernLifter(Definition, 9).GetAmountForLevel(9), Is.EqualTo(90));
            Assert.That(new ModernLongWind(Definition, 5).GetAmountForLevel(5) * 5 / 100, Is.EqualTo(5));
            Assert.That(new ModernMasteryOfFocus(Definition, 9).GetAmountForLevel(9), Is.EqualTo(39));
            Assert.That(new ModernPhysicalDefense(Definition, 9).GetAmountForLevel(9), Is.EqualTo(30));
            Assert.That(new ModernCharge(Definition, 5).GetReUseDelay(5), Is.EqualTo(90));
            Assert.That(new ModernCharge(Definition, 1).MaxLevel, Is.EqualTo(5));
        }
    }
}
