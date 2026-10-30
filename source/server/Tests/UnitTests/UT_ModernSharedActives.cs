using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS;
using DOL.GS.RealmAbilities;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernSharedActives
    {
        private ModernRaTestScope _scope;
        private readonly List<Actor> _actors = new();
        private readonly List<Group> _groups = new();
        private int _groupLimit;
        private sealed class Actor : GameNPC
        {
            public int Disabled;
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override int X { get; set; }
            private int _health = 1000;
            public override int Health { get => _health; set => _health = System.Math.Clamp(value, 0, MaxHealth); }
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int MaxHealth => 1000;
            public override void DisableSkill(Skill skill, int duration) { Disabled = duration; }
        }
        private static DbAbility Def(string key) => new DbAbility { KeyName = key, Name = key, Description = key };
        [SetUp] public void Setup()
        {
            _scope = new ModernRaTestScope();
            _groupLimit = DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER;
            DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER = 8;
        }
        [TearDown] public void Cleanup()
        {
            foreach (Group group in _groups)
                foreach (GameLiving member in group.GetMembersInTheGroup().ToArray()) group.RemoveMember(member);
            _groups.Clear();
            DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER = _groupLimit;
            foreach (var actor in _actors)
            {
                foreach (var effect in actor.effectListComponent.GetEffects()) { effect.End(); ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick(); ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _actors.Clear(); _scope.Dispose();
        }
        private Actor New(int x = 0) { var actor = new Actor { X = x }; _actors.Add(actor); return actor; }
        private void Together(params Actor[] actors)
        {
            var group = new Group(actors[0]); _groups.Add(group);
            foreach (var actor in actors) Assert.That(group.AddMember(actor), Is.True);
        }

        [Test]
        public void SharedActivesUseTheLiveRankTables()
        {
            Assert.That(Enumerable.Range(1, 5).Select(ModernSpeedOfSound.Duration), Is.EqualTo(new[] { 10, 20, 30, 45, 60 }));
            Assert.That(Enumerable.Range(1, 5).Select(ModernPerfectRecovery.Restore), Is.EqualTo(new[] { 10, 25, 50, 75, 100 }));
            Assert.That(Enumerable.Range(1, 5).Select(ModernDecimationTrap.Damage), Is.EqualTo(new[] { 300, 450, 600, 750, 900 }));
            var rush = new ModernAdrenalineRush(Def("ar"), 1);
            Assert.That(Enumerable.Range(1, 5).Select(rush.GetReUseDelay), Is.EqualTo(new[] { 1200, 900, 600, 450, 300 }));
            Assert.That(new ModernSpeedOfSound(Def("sos"), 1).GetReUseDelay(5), Is.EqualTo(600));
            Assert.That(new ModernPerfectRecovery(Def("pr"), 1).GetReUseDelay(5), Is.EqualTo(300));
            Assert.That(new ModernDecimationTrap(Def("dt"), 1).GetReUseDelay(5), Is.EqualTo(900));
            foreach (var ability in new TimedRealmAbility[] { rush, new ModernSpeedOfSound(Def("s"), 1), new ModernPerfectRecovery(Def("p"), 1), new ModernDecimationTrap(Def("d"), 1) })
            {
                Assert.That(ability.MaxLevel, Is.EqualTo(5));
                Assert.That(Enumerable.Range(0, 5).Select(ability.CostForUpgrade), Is.EqualTo(new[] { 5, 5, 5, 7, 8 }));
            }
        }

        [Test]
        public void PerfectRecoveryBuildsARealmLineResurrectionPerRank()
        {
            var ability = new ModernPerfectRecovery(Def("pr"), 2);
            var spell = ability.BuildSpell(2, 50);
            Assert.That(spell.SpellType, Is.EqualTo(eSpellType.Resurrect));
            Assert.That(spell.ResurrectHealth, Is.EqualTo(25)); Assert.That(spell.ResurrectMana, Is.EqualTo(25));
            Assert.That(spell.RecastDelay, Is.EqualTo(300000));
            Assert.That(((ISpellCastingAbilityHandler)ability).SpellLine.KeyName, Is.EqualTo(GlobalSpellsLines.Realm_Spells), "No rez sickness");
            Assert.That(((ISpellCastingAbilityHandler)ability).Ability, Is.SameAs(ability));
            Assert.That(ability, Is.InstanceOf<AtlasOF_PerfectRecovery>(), "The decline path re-enables the ability through this type");
        }

        [Test]
        public void SpeedOfSoundGivesCompanionsSpeedAndControlImmunityThenBreaksOnAttack()
        {
            var bot = New();
            new ModernSpeedOfSound(Def("sos"), 3).Execute(bot); bot.effectListComponent.BeginTick();
            Assert.That(bot.Disabled, Is.EqualTo(600000));
            var effect = bot.effectListComponent.GetAbilityEffects(eEffect.SpeedOfSound).OfType<ModernSpeedOfSoundEffect>().Single();
            Assert.That(effect.Duration, Is.EqualTo(30000));
            Assert.That(bot.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(DOL.GS.PropertyCalc.MaxSpeedCalculator.SPEED4));
            Assert.That(ModernRealmControl.IsMovingTooFast(bot), Is.True);
            ModernSpeedOfSoundEffect.BreakOnAction(bot); bot.effectListComponent.BeginTick();
            Assert.That(bot.effectListComponent.ContainsEffectForEffectType(eEffect.SpeedOfSound), Is.False);
            Assert.That(bot.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(1.0));
            Assert.That(ModernRealmControl.IsMovingTooFast(bot), Is.False);
        }

        [Test]
        public void SpeedOfSoundOnlyBreaksOnDeliberateHarmfulSpells()
        {
            static Spell Make(string type, string target) => new(new DbSpell { Name = "x", Type = type, Target = target }, 50);
            var cast = new SpellLine("spec", "spec", "spec", true);
            Assert.That(ModernSpeedOfSoundEffect.BreaksOn(Make("DirectDamage", "Enemy"), cast), Is.True);
            Assert.That(ModernSpeedOfSoundEffect.BreaksOn(Make("Heal", "Group"), cast), Is.False);
            Assert.That(ModernSpeedOfSoundEffect.BreaksOn(Make("DirectDamage", "Enemy"), new SpellLine(GlobalSpellsLines.Item_Effects, "i", "i", true)), Is.False,
                "Weapon and reactive procs are not an action by the owner");
        }

        [Test]
        public void ChargeNowMovesFasterAndBlocksControl()
        {
            var actor = New();
            new ModernCharge(Def("charge"), 5).Execute(actor); actor.effectListComponent.BeginTick();
            Assert.That(actor.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(DOL.GS.PropertyCalc.MaxSpeedCalculator.SPEED3));
            Assert.That(ModernRealmControl.IsMovingTooFast(actor), Is.True);
            actor.effectListComponent.GetEffects(eEffect.Charge).Single().End(); actor.effectListComponent.BeginTick();
            Assert.That(actor.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(1.0));
        }

        [Test]
        public void AdrenalineRushDoublesBaseDamageOnlyWhileActive()
        {
            var actor = New();
            Assert.That(ModernAdrenalineRush.DamageFactor(actor), Is.EqualTo(1));
            new ModernAdrenalineRush(Def("ar"), 4).Execute(actor); actor.effectListComponent.BeginTick();
            Assert.That(actor.Disabled, Is.EqualTo(450000));
            Assert.That(ModernAdrenalineRush.DamageFactor(actor), Is.EqualTo(2));
            actor.effectListComponent.GetEffects(eEffect.ModernAdrenalineRush).Single().End(); actor.effectListComponent.BeginTick();
            Assert.That(ModernAdrenalineRush.DamageFactor(actor), Is.EqualTo(1));
        }

        [Test]
        public void DecimationTrapSpellMatchesTheRank()
        {
            var spell = new ModernDecimationTrap(Def("dt"), 1).BuildSpell(4);
            Assert.That(spell.Damage, Is.EqualTo(750)); Assert.That(spell.Radius, Is.EqualTo(350));
            Assert.That(spell.DamageType, Is.EqualTo(eDamageType.Energy));
            Assert.That(ModernDecimationTrap.Lifetime, Is.EqualTo(600000));
        }

        [Test]
        public void DashingDefenseCoversGroupmatesInRangeButNotTheTank()
        {
            var tank = New(); var ally = New(500); var far = New(1500); Together(tank, ally, far);
            new ModernDashingDefense(Def("dd"), 4).Execute(tank);
            tank.effectListComponent.BeginTick(); ally.effectListComponent.BeginTick(); far.effectListComponent.BeginTick();
            Assert.That(tank.Disabled, Is.EqualTo(600000));
            var effect = ally.effectListComponent.GetAbilityEffects(eEffect.ModernDashingDefense).OfType<ModernDashingDefenseEffect>().Single();
            Assert.That(effect.Source, Is.SameAs(tank)); Assert.That(effect.Duration, Is.EqualTo(45000));
            Assert.That(tank.effectListComponent.ContainsEffectForEffectType(eEffect.ModernDashingDefense), Is.False);
            Assert.That(far.effectListComponent.ContainsEffectForEffectType(eEffect.ModernDashingDefense), Is.False);
            Assert.That(ModernDashingDefense.CanDefend(tank, ally), Is.True);
            Assert.That(ModernDashingDefense.CanDefend(tank, far), Is.False, "Out of the 1000 radius");
            Assert.That(ModernDashingDefense.CanDefend(tank, tank), Is.False);
            var spell = new AttackData { Attacker = far, Target = ally, AttackType = AttackData.eAttackType.Spell };
            Assert.That(ModernDashingDefense.TryDefend(spell, false, out _), Is.False, "Spells cannot be blocked or parried for you");
            Assert.That(Enumerable.Range(1, 5).Select(ModernDashingDefense.Duration), Is.EqualTo(new[] { 10, 20, 30, 45, 60 }));
        }

        [Test]
        public void DashingDefenseAloneDoesNotSpendTheCooldown()
        {
            var tank = New();
            new ModernDashingDefense(Def("dd"), 5).Execute(tank);
            Assert.That(tank.Disabled, Is.Zero);
        }

        [Test]
        public void DivineInterventionSharesOnePoolAndEndsWhenDrained()
        {
            var healer = New(); var a = New(100); var b = New(200); Together(healer, a, b);
            new ModernDivineIntervention(Def("di"), 1).Execute(healer);
            foreach (var actor in new[] { healer, a, b }) actor.effectListComponent.BeginTick();
            Assert.That(healer.effectListComponent.ContainsEffectForEffectType(eEffect.ModernDivineIntervention), Is.False, "Never the user");
            Assert.That(healer.Disabled, Is.EqualTo(600000));
            a.Health = 400;
            Assert.That(ModernDivineIntervention.Absorb(a, 700), Is.EqualTo(600), "Capped by missing health");
            Assert.That(a.Health, Is.EqualTo(1000));
            b.Health = 100;
            Assert.That(ModernDivineIntervention.Absorb(b, 900), Is.EqualTo(400), "Capped by what is left of the shared 1000 pool");
            a.effectListComponent.BeginTick(); b.effectListComponent.BeginTick();
            Assert.That(a.effectListComponent.ContainsEffectForEffectType(eEffect.ModernDivineIntervention), Is.False);
            Assert.That(b.effectListComponent.ContainsEffectForEffectType(eEffect.ModernDivineIntervention), Is.False);
            Assert.That(Enumerable.Range(1, 5).Select(ModernDivineIntervention.Pool), Is.EqualTo(new[] { 1000, 1500, 2000, 2500, 3000 }));
        }
    }
}
