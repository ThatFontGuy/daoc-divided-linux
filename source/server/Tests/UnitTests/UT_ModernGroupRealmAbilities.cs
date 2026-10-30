using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS;
using DOL.GS.PropertyCalc;
using DOL.GS.RealmAbilities;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernGroupRealmAbilities
    {
        private ModernRaTestScope _scope;
        private int _groupLimit;
        private readonly List<Actor> _actors = new();
        private readonly List<Group> _groups = new();
        private sealed class Actor : GameNPC
        {
            public bool Alive = true;
            public int Healed, Disabled;
            public int HeatResist;
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override byte Level { get; set; } = 50;
            public override int X { get; set; }
            public override bool IsAlive => Alive;
            public override int MaxHealth => 2000;
            public override int GetModified(eProperty property) => property == eProperty.Resist_Heat ? HeatResist : 0;
            public override int ChangeHealth(GameObject source, eHealthChangeType kind, int amount) { Healed += amount; return amount; }
            public override void DisableSkill(Skill skill, int duration) { Disabled = duration; }
        }
        private static DbAbility Definition => new DbAbility { KeyName = "test", Name = "Test", Description = "Test" };
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
            foreach (Actor actor in _actors)
            {
                foreach (var effect in actor.effectListComponent.GetEffects()) { effect.End(); ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick(); ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _groups.Clear(); _actors.Clear();
            DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER = _groupLimit;
            _scope.Dispose();
        }
        private Actor New(int x = 0)
        {
            var actor = new Actor { X = x }; _actors.Add(actor); return actor;
        }
        private void Together(params Actor[] actors)
        {
            var group = new Group(actors[0]); _groups.Add(group);
            foreach (var actor in actors) Assert.That(group.AddMember(actor), Is.True);
        }
        private static void Tick(params Actor[] actors) { foreach (var actor in actors) actor.effectListComponent.BeginTick(); }

        [Test]
        public void GroupHealIncludesNpcGroupMembersAndSkipsCasterDeadAndOutOfRange()
        {
            var caster = New(); var ally = New(100); var dead = New(200); var far = New(3000); dead.Alive = false;
            Together(caster, ally, dead, far);
            new ModernVehementRenewal(Definition, 5).Execute(caster);
            Assert.That(ally.Healed, Is.EqualTo(1500));
            Assert.That(caster.Healed, Is.Zero); Assert.That(dead.Healed, Is.Zero); Assert.That(far.Healed, Is.Zero);
            Assert.That(caster.Disabled, Is.EqualTo(600000));
        }
        [Test]
        public void MelodiesHasTenThreeSecondPulsesAndNeverHealsTheCaster()
        {
            var caster = New(); var ally = New(100); Together(caster, ally);
            new ModernAmelioratingMelodies(Definition, 5).Execute(caster); Tick(caster);
            var effect = caster.effectListComponent.GetEffects(eEffect.ModernRealmMelodies).OfType<ModernRealmMelodiesEffect>().Single();
            Assert.That(effect.PulseFreq, Is.EqualTo(3000));
            for (int tick = 0; tick < 20; tick++) effect.OnEffectPulse();
            Assert.That(ally.Healed, Is.EqualTo(4000)); Assert.That(caster.Healed, Is.Zero);
            Assert.That(caster.Disabled, Is.EqualTo(900000));
        }
        [Test]
        public void BarriersAreMutuallyExclusiveAndRemoveTheirExactBonuses()
        {
            var caster = New();
            new ModernBunkerOfFaith(Definition, 5).Execute(caster); Tick(caster);
            Assert.That(caster.AbilityBonus[eProperty.PhysicalAbsorption], Is.EqualTo(40));
            caster.Disabled = 0;
            new ModernBrilliantAura(Definition, 5).Execute(caster); Tick(caster);
            new ModernSoldiersBarricade(Definition, 5).Execute(caster); Tick(caster);
            Assert.That(caster.OtherBonus[eProperty.Resist_Heat], Is.Zero);
            Assert.That(caster.Disabled, Is.Zero, "Blocked barriers must not consume a reuse timer");
            caster.effectListComponent.GetEffects(eEffect.ModernRealmBarrier).Single().End(); Tick(caster);
            Assert.That(caster.AbilityBonus[eProperty.PhysicalAbsorption], Is.Zero);
            Assert.That(caster.TempProperties.GetProperty<bool>(ModernRealmBuffEffect.BarrierLock), Is.False);
            new ModernSoldiersBarricade(Definition, 5).Execute(caster); Tick(caster);
            Assert.That(caster.OtherBonus[eProperty.Resist_Heat], Is.EqualTo(30));
            Assert.That(caster.OtherBonus[eProperty.Resist_Slash], Is.EqualTo(30));
            Assert.That(caster.OtherBonus[eProperty.ArmorFactor], Is.Zero);
        }
        [Test]
        public void EmptyMindLastsFortyFiveSecondsAndDoesNotModifyCrowdControlResists()
        {
            var caster = New(); var ally = New(100); Together(caster, ally);
            new ModernEmptyMind(Definition, 5).Execute(caster); Tick(caster, ally);
            Assert.That(caster.OtherBonus[eProperty.Resist_Heat], Is.EqualTo(30));
            Assert.That(caster.AbilityBonus[eProperty.Resist_Heat], Is.Zero);
            Assert.That(ally.OtherBonus[eProperty.Resist_Heat], Is.Zero);
            Assert.That(caster.effectListComponent.GetEffects(eEffect.ModernRealmMind).Single().Duration, Is.EqualTo(45000));
        }
        [Test]
        public void BarrierFiltersOutDistantAndDeadGroupMembers()
        {
            var caster = New(); var ally = New(100); var far = New(3000); var dead = New(); dead.Alive = false;
            Together(caster, ally, far, dead);
            new ModernBrilliantAura(Definition, 3).Execute(caster); Tick(caster, ally, far, dead);
            Assert.That(ally.OtherBonus[eProperty.Resist_Cold], Is.EqualTo(20));
            Assert.That(caster.OtherBonus[eProperty.Resist_Cold], Is.EqualTo(20));
            Assert.That(far.OtherBonus[eProperty.Resist_Cold], Is.Zero); Assert.That(dead.OtherBonus[eProperty.Resist_Cold], Is.Zero);
        }
        [Test]
        public void DamageRanksUseLiveValuesAndCooldowns()
        {
            Assert.That(ModernAngerOfTheGods.Damage(2), Is.EqualTo(22.5));
            Assert.That(ModernAngerDamageAdd.SwingDamage(45, 4000), Is.EqualTo(180));
            Assert.That(new ModernAngerOfTheGods(Definition, 5).GetReUseDelay(5), Is.EqualTo(300));
            Assert.That(ModernWrathOfTheChampion.Damage(2), Is.EqualTo(522.5));
            Assert.That(new ModernWrathOfTheChampion(Definition, 5).BuildSpell(5).Radius, Is.EqualTo(150));
            Assert.That(ModernVolcanicPillar.Damage(5), Is.EqualTo(1500));
            Assert.That(new ModernVolcanicPillar(Definition, 5).GetReUseDelay(5), Is.EqualTo(450));
        }
        private class Damage : ModernRealmDamage
        {
            public Damage(GameLiving caster, Spell spell) : base(caster, spell) { }
            public override double CalculateToHitChance(GameLiving target) => 100;
        }
        [Test]
        public void DamagePipelineHonorsResistsInsteadOfRawTakeDamage()
        {
            var caster = New(); var target = New(100); target.HeatResist = 50;
            var spell = new ModernVolcanicPillar(Definition, 5).BuildSpell(5);
            var handler = new Damage(caster, spell);
            var hit = handler.CalculateDamageToTarget(target);
            Assert.That(hit.Damage, Is.EqualTo(750)); Assert.That(hit.CriticalDamage, Is.Zero);
        }
    }
}
