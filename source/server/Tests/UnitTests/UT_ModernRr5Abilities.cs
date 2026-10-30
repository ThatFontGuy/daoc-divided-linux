using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS;
using DOL.GS.RealmAbilities;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernRr5Abilities
    {
        private ModernRaTestScope _scope;
        private int _groupLimit;
        private readonly List<Actor> _actors = new();
        private readonly List<Group> _groups = new();
        private sealed class Actor : GameNPC
        {
            public int Disabled, Healed, Powered, Rested;
            private int _health = 1000;
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override int X { get; set; }
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int MaxHealth => 1000;
            public override int MaxMana => 400;
            public override int MaxEndurance => 100;
            public override int Health { get => _health; set => _health = System.Math.Clamp(value, 0, MaxHealth); }
            public override int ChangeHealth(GameObject source, eHealthChangeType kind, int amount) { Healed += amount; return amount; }
            public override int ChangeMana(GameObject source, eManaChangeType kind, int amount) { Powered += amount; return amount; }
            public override int ChangeEndurance(GameObject source, eEnduranceChangeType kind, int amount) { Rested += amount; return amount; }
            public override void DisableSkill(Skill skill, int duration) { Disabled = duration; }
            public override int GetModified(eProperty property) => property == eProperty.HealingEffectiveness ? 0 : base.GetModified(property);
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
            foreach (var actor in _actors)
            {
                foreach (var effect in actor.effectListComponent.GetEffects()) { effect.End(); ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick(); ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _groups.Clear(); _actors.Clear();
            DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER = _groupLimit;
            _scope.Dispose();
        }
        private Actor New(int x = 0) { var actor = new Actor { X = x }; _actors.Add(actor); return actor; }
        private void Together(params Actor[] actors)
        {
            var group = new Group(actors[0]); _groups.Add(group);
            foreach (var actor in actors) Assert.That(group.AddMember(actor), Is.True);
        }
        private static void Tick(params Actor[] actors) { foreach (var actor in actors) actor.effectListComponent.BeginTick(); }
        private static AttackData Hit(GameLiving target, int damage, AttackData.eAttackType type = AttackData.eAttackType.MeleeOneHand) =>
            new() { Target = target, Damage = damage, AttackType = type, AttackResult = eAttackResult.HitUnstyled };

        [Test]
        public void LiveReuseTimers()
        {
            Assert.That(new ModernDissoluteSwings(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ModernFueledByRage(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ModernFrenzyOfTheUnderhill(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(300));
            Assert.That(new ModernRestorativeMend(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ModernFarSight(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ModernBestialHeart(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ModernNaturesMadness(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ModernVoiceOfSkadi(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(300));
            Assert.That(new ModernMjollnirsProtection(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ModernVoiceOfSkadi(Def("a"), 1).CostForUpgrade(0), Is.Zero, "RR5s are free");
        }

        [Test]
        public void DissoluteSwingsRaisesDamageBothWays()
        {
            var merc = New();
            new ModernDissoluteSwings(Def("ds"), 1).Execute(merc); Tick(merc);
            Assert.That(merc.Disabled, Is.EqualTo(600000));
            Assert.That(ModernRr5.OutgoingFactor(merc), Is.EqualTo(1.25));
            var hit = Hit(merc, 100); ModernRr5.ModifyIncoming(merc, hit);
            Assert.That(hit.Damage, Is.EqualTo(125));
        }

        [Test]
        public void FueledByRageReducesDamageAndHealsHalfOfIt()
        {
            var savage = New();
            new ModernFueledByRage(Def("fr"), 1).Execute(savage); Tick(savage);
            var hit = Hit(savage, 100); ModernRr5.ModifyIncoming(savage, hit);
            Assert.That(hit.Damage, Is.EqualTo(80));
            Assert.That(savage.Healed, Is.EqualTo(10));
        }

        [Test]
        public void MjollnirsProtectionAbsorbsHalfOfSpellDamageUpToItsPool()
        {
            var thane = New(); var ally = New(500); Together(thane, ally);
            new ModernMjollnirsProtection(Def("mp"), 1).Execute(thane); Tick(thane, ally);
            var melee = Hit(ally, 400); ModernRr5.ModifyIncoming(ally, melee);
            Assert.That(melee.Damage, Is.EqualTo(400), "Spell damage only");
            var spell = Hit(ally, 1000, AttackData.eAttackType.Spell); ModernRr5.ModifyIncoming(ally, spell);
            Assert.That(spell.Damage, Is.EqualTo(500));
            var big = Hit(ally, 3000, AttackData.eAttackType.Spell); ModernRr5.ModifyIncoming(ally, big);
            Assert.That(big.Damage, Is.EqualTo(2000), "Only 1000 of the 1500 pool was left");
            Tick(ally);
            Assert.That(ModernRr5.Get(ally, eEffect.ModernMjollnirsProtection), Is.Null, "Ends once drained");
            Assert.That(ModernRr5.Get(thane, eEffect.ModernMjollnirsProtection), Is.Not.Null, "Each member has their own pool");
        }

        [Test]
        public void RestorativeMendTicksFifteenPercentOfEachPool()
        {
            var shaman = New();
            ModernRestorativeMend.Tick(shaman);
            Assert.That(shaman.Healed, Is.EqualTo(150)); Assert.That(shaman.Powered, Is.EqualTo(60)); Assert.That(shaman.Rested, Is.EqualTo(15));
        }

        [Test]
        public void VoiceOfSkadiGrantsControlImmunity()
        {
            var skald = New();
            new ModernVoiceOfSkadi(Def("vs"), 1).Execute(skald); Tick(skald);
            Assert.That(ModernRr5.IsControlImmune(skald), Is.True);
            Assert.That(skald.Disabled, Is.EqualTo(300000));
        }

        [Test]
        public void BestialHeartAppliesItsBonusesAndBlocksTheBowThenRemovesThem()
        {
            var hunter = New();
            new ModernBestialHeart(Def("bh"), 1).Execute(hunter); Tick(hunter);
            Assert.That(hunter.AbilityBonus[eProperty.MeleeDamage], Is.EqualTo(15));
            Assert.That(hunter.BaseBuffBonusCategory[eProperty.MeleeSpeed], Is.EqualTo(40));
            Assert.That(hunter.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(2.15));
            Assert.That(ModernRr5.BlocksBow(hunter), Is.True);
            ModernRr5.Get(hunter, eEffect.ModernBestialHeart).End(); Tick(hunter);
            Assert.That(hunter.AbilityBonus[eProperty.MeleeDamage], Is.Zero);
            Assert.That(hunter.BaseBuffBonusCategory[eProperty.MeleeSpeed], Is.Zero);
            Assert.That(hunter.BuffBonusMultCategory1.Get((int)eProperty.MaxSpeed), Is.EqualTo(1.0));
        }

        [Test]
        public void FarSightExtendsRangeAndGrantsNearsightImmunity()
        {
            var scout = New();
            new ModernFarSight(Def("fs"), 1).Execute(scout); Tick(scout);
            Assert.That(scout.AbilityBonus[eProperty.ArcheryRange], Is.EqualTo(20));
            Assert.That(ModernRr5.SpellRange(scout, 1500), Is.EqualTo(1800));
            Assert.That(ModernRr5.IsNearsightImmune(scout), Is.True);
            Assert.That(ModernFarSight.NearsightSpell.Value, Is.EqualTo(50));
            Assert.That(ModernFarSight.NearsightSpell.Duration, Is.EqualTo(20000));
        }

        [Test]
        public void LegacyRr5sCarryTheLiveValues()
        {
            Assert.That(new FungalUnionAbility(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(300));
            Assert.That(new AllureOfDeathAbility(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new DreamweaverAbility(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new SelectiveBlindnessAbility(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(new ShadowShroudAbility(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600));
            Assert.That(OverwhelmAbility.BONUS, Is.EqualTo(0.10));
            Assert.That(BloodDrinkingAbility.HEALPERCENT, Is.EqualTo(45));
            Assert.That(BloodDrinkingAbility.DURATION, Is.EqualTo(15000));
            Assert.That(new ModernSelflessDevotion(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600), "1.129");
            Assert.That(new ModernWallOfFlame(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600), "1.129");
            Assert.That(new ModernBadgeOfValor(Def("a"), 1).GetReUseDelay(1), Is.EqualTo(600), "1.121");
        }

        [Test]
        public void ValeDefenseAblativesAndFanaticismAbsorption()
        {
            var spell = ModernValeDefense.Ablative(2000);
            Assert.That(spell.Value, Is.EqualTo(2000)); Assert.That(spell.Damage, Is.EqualTo(50)); Assert.That(spell.Duration, Is.EqualTo(600000));
            var heretic = New(); var ally = New(300); Together(heretic, ally);
            new ModernFanaticism(Def("f"), 1).Execute(heretic); Tick(heretic, ally);
            Assert.That(ally.BaseBuffBonusCategory[eProperty.MagicAbsorption], Is.EqualTo(25));
            Assert.That(ModernRr5.Get(ally, eEffect.ModernFanaticism).Duration, Is.EqualTo(15000));
        }

        [Test]
        public void SelflessDevotionScalesWithGroupSize()
        {
            Assert.That(ModernSelflessDevotion.GroupHeal(1), Is.Zero);
            Assert.That(ModernSelflessDevotion.GroupHeal(4), Is.EqualTo(300));
            Assert.That(ModernSelflessDevotion.GroupHeal(8), Is.EqualTo(500));
            var paladin = New(); ModernSelflessDevotion.Pulse(paladin);
            Assert.That(paladin.Healed, Is.GreaterThanOrEqualTo(100), "The Paladin always heals for 100");
        }

        [Test]
        public void SputinsLegacyCheatsDeathThenGrantsImmunity()
        {
            var healer = New(); healer.Health = 100;
            new ModernSputinsLegacy(Def("s"), 1).Execute(healer); Tick(healer);
            var blow = Hit(healer, 500); ModernRr5.ModifyIncoming(healer, blow);
            Assert.That(blow.Damage, Is.EqualTo(99), "The killing blow leaves 1 health");
            Assert.That(healer.Healed, Is.GreaterThanOrEqualTo(300), "Heals at least 30%");
            Tick(healer);
            var next = Hit(healer, 400); ModernRr5.ModifyIncoming(healer, next);
            Assert.That(next.Damage, Is.Zero, "Damage immunity afterwards");
            Assert.That(ModernRr5.IsControlImmune(healer), Is.True);
        }

        [Test]
        public void NaturesWombTurnsDamageIntoHealing()
        {
            var druid = New();
            new ModernNaturesWomb(Def("n"), 1).Execute(druid); Tick(druid);
            var hit = Hit(druid, 300); ModernRr5.ModifyIncoming(druid, hit);
            Assert.That(hit.Damage, Is.Zero); Assert.That(druid.Healed, Is.EqualTo(300));
            Assert.That(druid.SilencedTime, Is.GreaterThan(0));
        }

        [Test]
        public void FuryOfNatureDoublesStylesAndSpreadHealsTheMostInjured()
        {
            var warden = New(); var hurt = New(100); var fine = New(200); Together(warden, hurt, fine);
            hurt.Health = 200; fine.Health = 900;
            new ModernFuryOfNature(Def("f"), 1).Execute(warden); Tick(warden);
            Assert.That(ModernRr5.StyleFactor(warden), Is.EqualTo(2));
            ModernFuryOfNature.SpreadHeal(warden, 300);
            Assert.That(hurt.Healed, Is.EqualTo(300)); Assert.That(fine.Healed, Is.Zero); Assert.That(warden.Healed, Is.Zero);
        }

        [Test]
        public void SmallerRr5Formulas()
        {
            Assert.That(ModernSpiritMartyr.PoolFor(50), Is.EqualTo(1600));
            Assert.That(ModernSpiritMartyr.PoolFor(100), Is.EqualTo(3200));
            var champion = New();
            Assert.That(ModernBadgeOfValor.ArmorFactor(champion, 0.25), Is.EqualTo(1), "Only while active");
            new ModernBadgeOfValor(Def("b"), 1).Execute(champion); Tick(champion);
            Assert.That(ModernBadgeOfValor.ArmorFactor(champion, 0.25), Is.EqualTo(1.25 / 0.75).Within(1e-9));
            var pet = New();
            ECSGameEffectFactory.Create(new(pet, 60000, 1), static (in ECSGameEffectInitParams i) =>
                new ModernRr5Effect(i, eEffect.ModernResoluteMinion, "Resolute Minion", 1));
            Tick(pet);
            Assert.That(ModernRr5.IsControlImmune(pet), Is.True);
        }

        [Test]
        public void FrenzyAndMadnessChangeCastTimes()
        {
            var pet = New(); var enemy = New();
            ECSGameEffectFactory.Create(new(pet, 30000, 1), static (in ECSGameEffectInitParams i) =>
                new ModernRr5Effect(i, eEffect.ModernFrenzyOfTheUnderhill, "Frenzy", 1));
            ECSGameEffectFactory.Create(new(enemy, 3000, 1), static (in ECSGameEffectInitParams i) =>
                new ModernRr5Effect(i, eEffect.ModernNaturesMadnessSlow, "Madness", 1));
            Tick(pet, enemy);
            Assert.That(ModernRr5.CastTime(pet, 3000), Is.EqualTo(1500), "+100% casting speed");
            Assert.That(ModernRr5.CastTime(enemy, 2100), Is.EqualTo(3000), "30% slower casting");
        }
    }
}
