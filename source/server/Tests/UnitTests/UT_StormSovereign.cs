using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using DOL.GS.ServerRules;
using DOL.GS.RealmAbilities;
using DOL.GS.PropertyCalc;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture,NonParallelizable]
    public class UT_StormSovereign
    {
        private GameServer _previous;
        private PetTestLanguageScope _language;
        private readonly List<GameLiving> _actors=new();
        private static readonly SpellLine Line=new("Stormforged.Sovereign", "Storm Sovereign", "StormforgedCareer", true);
        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl=>DispatchProxy.Create<IObjectDatabase,UT_UnobservedConcentration.EmptyReads>();
            protected override IServerRules ServerRulesImpl=>new NormalServerRules();
        }
        private class Actor : GameNPC
        {
            public bool Hidden;
            public override byte Level { get; set; }=50;
            public override bool IsStealthed=>Hidden;
            public override void Stealth(bool hidden)=>Hidden=hidden;
            public override bool IsAlive=>true;
            public override int GetModified(eProperty p)=>p==eProperty.MaxSpeed?200:0;
            public override int MaxHealth=>1000;
            public override int MaxMana=>500;
            public override int MaxEndurance=>100;
            public override void OnMaxSpeedChange() { }
        }
        private sealed class Wolf : StormWolf
        {
            public Wolf():base(null) { }
            public override bool IsAlive=>true;
            public override int GetModified(eProperty p)=>0;
            public override int MaxHealth=>1000;
        }
        private sealed class Pool : GameNPC
        {
            public override byte Level { get; set; }=50;
            public override int MaxHealth=>1000;
            public override int MaxMana=>1000;
            public override int MaxEndurance=>1000;
            public override int Health { get; set; }=100;
            public override int Mana { get; set; }=100;
            public override int Endurance { get; set; }=100;
            public override ushort Model { get; set; }=153;
            public override bool IsAlive=>Health>0;
            public override int GetModified(eProperty p)=>0;
            public override int CalculateCastingTime(SpellHandler handler)=>handler.Spell.CastTime;
        }
        [SetUp]
        public void Setup()
        {
            _previous=GameServer.Instance;
            _language=new PetTestLanguageScope();
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
        }
        [TearDown]
        public void Cleanup()
        {
            foreach(var actor in _actors)
            {
                foreach(var effect in actor.effectListComponent.GetEffects()) { effect.End();ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick();ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _actors.Clear();GameServer.LoadTestDouble(_previous);_language.Dispose();
        }
        private Actor NewActor() { var actor=new Actor();_actors.Add(actor);return actor; }
        private Pool NewPool() { var pool=new Pool();_actors.Add(pool);return pool; }
        private static AttackData Hit(GameLiving target,int damage,bool melee)=>new() {
            Target=target,Damage=damage,AttackType=melee?AttackData.eAttackType.MeleeOneHand:AttackData.eAttackType.Spell };
        private StormforgedAvatarEffect StartCrown(GameLiving owner,int offset=0)
        {
            var crown=new Spell(new DbSpell { SpellID=SpellFor(20).ID+offset,Type="StormforgedAvatar",Target="Self",Duration=60,Value=918 },50);
            var effect=new StormforgedAvatarEffect(new(owner,60000,1,new StormforgedAvatar(owner,crown,Line)));
            Assert.That(effect.Start(),Is.True);owner.effectListComponent.BeginTick();
            return effect;
        }
        [Test]
        public void EveryHitStealsHealthPowerAndEnduranceWithoutOverkill()
        {
            var owner=NewPool();var enemy=NewPool();
            StormSovereignAbilities.Siphon(owner,Hit(enemy,100,true),1000);
            Assert.That((owner.Health,owner.Mana,owner.Endurance),Is.EqualTo((130,110,110)),"melee 30%/10%");
            StormSovereignAbilities.Siphon(owner,Hit(enemy,100,false),1000);
            Assert.That((owner.Health,owner.Mana,owner.Endurance),Is.EqualTo((180,130,130)),"spell 50%/20%");
            StormSovereignAbilities.Siphon(owner,Hit(enemy,100,false),40);
            Assert.That(owner.Health,Is.EqualTo(200),"only the 40 damage that landed counts");
            StormSovereignAbilities.Siphon(owner,Hit(enemy,0,false),1000);
            Assert.That(owner.Health,Is.EqualTo(200),"resisted hits return nothing");
        }
        [TestCase(0)] [TestCase(1600)]
        public void StormCrownEmpowersSovereignAndRemovesEveryBonus(int offset)
        {
            var owner=NewPool();var enemy=NewPool();
            var effect=StartCrown(owner,offset);
            Assert.That(owner.AbilityBonus[eProperty.ArmorAbsorption],Is.EqualTo(20));
            Assert.That(owner.AbilityBonus[eProperty.MeleeDamage],Is.EqualTo(50));
            Assert.That(owner.AbilityBonus[eProperty.MeleeSpeed],Is.EqualTo(20));
            effect.OnEffectPulse();
            Assert.That((owner.Health,owner.Mana,owner.Endurance),Is.EqualTo((200,200,200)),"10% regeneration per pulse");
            StormSovereignAbilities.Siphon(owner,Hit(enemy,100,true),1000);
            Assert.That((owner.Health,owner.Mana,owner.Endurance),Is.EqualTo((245,215,215)),"1.5x melee steal");
            var royal=new Spell(new DbSpell { SpellID=SpellFor(0).ID+offset,Type="StormSovereignAbility",Target="Enemy",CastTime=2500 },50);
            Assert.That(new SpellHandler(owner,royal,Line).CalculateCastingTime(),Is.EqualTo(250));
            effect.End();owner.effectListComponent.BeginTick();
            Assert.That(owner.AbilityBonus[eProperty.ArmorAbsorption]+owner.AbilityBonus[eProperty.MeleeDamage]+owner.AbilityBonus[eProperty.MeleeSpeed],Is.Zero);
            Assert.That(owner.Model,Is.EqualTo(153));
        }
        [Test]
        public void WolfIsTougherAndHitsHarderDuringStormCrown()
        {
            var owner=NewPool();
            var wolf=new Wolf();_actors.Add(wolf);
            wolf.SetOwnBrain(new StormWolfBrain(owner));
            Assert.That(wolf.MaxHealthScalingFactor,Is.EqualTo(4.0));
            wolf.SyncOwner();
            Assert.That(wolf.DamageFactor,Is.EqualTo(StormWolf.NormalDamage));
            StartCrown(owner);
            wolf.SyncOwner();
            Assert.That(wolf.DamageFactor,Is.EqualTo(StormWolf.CrownDamage));
        }
        private static Spell SpellFor(int key,int level=50,string type="StormSovereignAbility")=>new(new DbSpell {
            SpellID=62400+Array.IndexOf(StormSovereignAbilities.Levels,level)*32+key,Type=type,Target="Self",Duration=30,Value=205,Description="Royal ability" },level);
        [Test]
        public void EveryRoyalAbilityAndStyleProcHasExecutableBehavior()
        {
            foreach(var (id,ability) in StormSovereignAbilities.Build())
            {
                Assert.That(MasterLevelAbilities.For(id),Is.Not.Null);
                Assert.That(ability.Run,Is.Not.Null,id.ToString());
            }
            Assert.That(new DOL.GS.PlayerClass.ClassStormforged().ID,Is.EqualTo((int)eCharacterClass.Stormforged));
        }
        [Test]
        public void SovereignPassivesApplyUpgradeAndRespecWithoutLeakingBonuses()
        {
            var owner=NewActor();
            var db=new DbAbility { KeyName="Sovereign_Test",Name="Royal ability" };
            foreach(var ability in new SovereignPassive[] { new SovereignRoyalFortitude(db,1),new SovereignStormMastery(db,1),new SovereignCrownsResolve(db,1) })
            {
                Assert.That(Enumerable.Range(0,3).Select(ability.CostForUpgrade),Is.EqualTo(new[]{2,4,6}));
                ability.Activate(owner,false);
                ability.Level=3;
                Assert.That(ability.Amount,Is.EqualTo(ability is SovereignRoyalFortitude?9:6));
                ability.Deactivate(owner,false);
            }
            foreach(var property in MLMod.AllResists.Concat(new[]{eProperty.Of_Toughness,eProperty.MeleeDamage,eProperty.SpellDamage}))
                Assert.That(owner.AbilityBonus[property],Is.Zero,property.ToString());
        }
        [Test]
        public void SecondaryWardIsRealMitigationEvenWithNoPrimaryResists()
        {
            var owner=NewActor();
            var calculator=new ResistCalculator();
            owner.AbilityBonus[eProperty.Resist_Cold]=10;
            Assert.That(calculator.CalcValueFromBuffs(owner,eProperty.Resist_Cold),Is.Zero);
            Assert.That(calculator.CalcValue(owner,eProperty.Resist_Cold),Is.EqualTo(10));
            owner.BaseBuffBonusCategory[eProperty.Resist_Cold]=24;
            Assert.That(calculator.CalcValue(owner,eProperty.Resist_Cold),Is.EqualTo(31));
        }
        [Test]
        public void RoyalRR5EmpowermentExpiresAndRestoresBothCombatBonuses()
        {
            var owner=NewActor();
            var wolf=new Wolf();_actors.Add(wolf);
            var spell=new Spell(new DbSpell { SpellID=StormSovereignAbilities.RR5SpellId,Type="StormSovereignAbility",Target="Self",Duration=20 },50);
            var handler=new StormSovereignHandler(owner,spell,Line);
            foreach(var target in new GameLiving[]{owner,wolf})
            {
                handler.Hold(target);target.effectListComponent.BeginTick();
                Assert.That(target.BaseBuffBonusCategory[eProperty.MeleeDamage],Is.EqualTo(20));
                Assert.That(target.BaseBuffBonusCategory[eProperty.SpellDamage],Is.EqualTo(20));
                Assert.That(target.OtherBonus[eProperty.CriticalMeleeHitChance],Is.EqualTo(10));
                Assert.That(target.AbilityBonus[eProperty.CriticalSpellHitChance],Is.EqualTo(10));
                target.effectListComponent.GetSpellEffects(eEffect.MasterLevel).Single().End();target.effectListComponent.BeginTick();
                Assert.That(target.BaseBuffBonusCategory[eProperty.MeleeDamage]+target.AbilityBonus[eProperty.CriticalSpellHitChance],Is.Zero);
            }
            Assert.That(new SovereignWrathOfTheCrown(new DbAbility(),1).GetReUseDelay(1),Is.EqualTo(300));
        }
        [Test]
        public void MaintainedRoyalEffectsCanBeCancelledWithoutLeakingBonuses()
        {
            var owner=NewActor();
            var spell=SpellFor(14);
            var handler=new StormSovereignHandler(owner,spell,Line);
            handler.Hold(owner);
            owner.effectListComponent.BeginTick();
            Assert.That(owner.AbilityBonus[eProperty.Resist_Cold],Is.EqualTo(10));
            Assert.That(owner.effectListComponent.GetSpellEffects(eEffect.MasterLevel).Single().ExpireTick,Is.EqualTo(long.MaxValue));
            Assert.That(handler.CheckBeginCast(owner),Is.False,"recast toggles off instead of adding another copy");
            owner.effectListComponent.BeginTick();
            Assert.That(owner.AbilityBonus[eProperty.Resist_Cold],Is.Zero);
        }
        [Test]
        public void RoyalPresenceAddsAllSupportBonusesAndRemovesThemExactly()
        {
            var owner=NewActor();
            var spell=SpellFor(6,40,"StormforgedChant");
            var effect=new StormforgedChantEffect(new(owner,60000,1,new StormforgedChant(owner,spell,Line)));
            effect.Start();owner.effectListComponent.BeginTick();
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Resist_Heat],Is.EqualTo(24));
            Assert.That(owner.BaseBuffBonusCategory[eProperty.MeleeSpeed],Is.EqualTo(17));
            Assert.That(owner.BaseBuffBonusCategory[eProperty.ArmorFactor],Is.EqualTo(80));
            Assert.That(StormforgedRules.HasStormsong(owner),Is.True);
            effect.End();owner.effectListComponent.BeginTick();
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Resist_Heat]+owner.BaseBuffBonusCategory[eProperty.MeleeSpeed]+owner.BaseBuffBonusCategory[eProperty.ArmorFactor],Is.Zero);
        }
        [Test]
        public void WolfSharesOwnerStealthAndDoesNotAttackWhileHidden()
        {
            var owner=NewActor();
            var wolf=new Wolf();_actors.Add(wolf);
            var brain=new StormWolfBrain(owner);wolf.SetOwnBrain(brain);
            owner.Hidden=true;
            wolf.SyncOwner();
            Assert.That(wolf.IsStealthed,Is.True);
            Assert.That(wolf.Level,Is.EqualTo(owner.Level));
            brain.Think();
            Assert.That(wolf.IsAttacking,Is.False);
            owner.Hidden=false;wolf.SyncOwner();
            Assert.That(wolf.IsStealthed,Is.False);
        }
        [Test]
        public void SecondAndThirdWolfAttachToTheFirstAsSubPetsCappedAtTwo()
        {
            // Drengr's second/third wolf (SummonDrengrWolfCompanion): same commander/sub-pet
            // attachment as Bonedancer's CommanderPet, but every wolf -- not just the first --
            // still resolves the real owner's stealth/speed through RootOwner/GetPlayerOwner(),
            // so all three act like independent pets of the owner rather than a hierarchy.
            var owner=NewActor();
            var wolf1=new Wolf();_actors.Add(wolf1);
            var brain1=new StormWolfBrain(owner);wolf1.SetOwnBrain(brain1);
            wolf1.InitControlledBrainArray(2);

            var wolf2=new Wolf();_actors.Add(wolf2);
            var brain2=new StormWolfBrain(wolf1);wolf2.SetOwnBrain(brain2);
            Assert.That(wolf1.AddControlledBrain(brain2),Is.True,"room for a second wolf");
            Assert.That(wolf1.PetCount,Is.EqualTo(1));
            Assert.That(wolf2.RootOwner,Is.EqualTo(owner),"RootOwner walks past the first wolf to the real owner");

            owner.Hidden=true;
            wolf2.SyncOwner();
            Assert.That(wolf2.IsStealthed,Is.True,"second wolf follows the real owner's stealth, not the first wolf's");
            owner.Hidden=false;wolf2.SyncOwner();

            var wolf3=new Wolf();_actors.Add(wolf3);
            var brain3=new StormWolfBrain(wolf1);wolf3.SetOwnBrain(brain3);
            Assert.That(wolf1.AddControlledBrain(brain3),Is.True,"room for a third wolf");
            Assert.That(wolf1.PetCount,Is.EqualTo(2));

            var wolf4=new Wolf();_actors.Add(wolf4);
            var brain4=new StormWolfBrain(wolf1);wolf4.SetOwnBrain(brain4);
            Assert.That(wolf1.AddControlledBrain(brain4),Is.False,"capped at two sub-pets -- three wolves total");

            Assert.That(wolf1.RemoveControlledBrain(brain2),Is.True);
            Assert.That(wolf1.PetCount,Is.EqualTo(1));
            Assert.That(wolf1.AddControlledBrain(brain4),Is.True,"a freed slot can be reused");
        }
        [Test]
        public void ReleasingTheCommanderAlsoReleasesItsAttachedWolves()
        {
            // SummonStormWolf.OnPetReleased: ending the commander's own Pet effect only despawns
            // itself, so without this override any Drengr second/third wolf companions attached
            // to it would be left behind in the world.
            var owner=NewActor();
            var wolf1=new Wolf();_actors.Add(wolf1);
            var brain1=new StormWolfBrain(owner);wolf1.SetOwnBrain(brain1);
            wolf1.InitControlledBrainArray(2);

            var wolf2=new Wolf();_actors.Add(wolf2);var sub1=new StormWolfBrain(wolf1);wolf2.SetOwnBrain(sub1);
            var wolf3=new Wolf();_actors.Add(wolf3);var sub2=new StormWolfBrain(wolf1);wolf3.SetOwnBrain(sub2);
            wolf1.AddControlledBrain(sub1);wolf1.AddControlledBrain(sub2);
            Assert.That(wolf1.PetCount,Is.EqualTo(2));

            var handler=new SummonStormWolf(owner,SpellFor(5),Line);
            typeof(SummonSpellHandler).GetField("m_pet",BindingFlags.NonPublic|BindingFlags.Instance)!.SetValue(handler,wolf1);
            handler.OnPetReleased();

            Assert.That(wolf1.PetCount,Is.EqualTo(0),"both attached wolves are detached when the commander is released");
            Assert.That(wolf1.ControlledNpcList,Is.All.Null,"their slots are freed, not just forgotten");
        }
        [Test]
        public void RoyalCleanseSupportsTheControlledCastingBypassAndTooltipsArePrivate()
        {
            Assert.That(MasterLevelAbilities.For(SpellFor(12).ID).BreaksControl,Is.True);
            foreach(int id in new[]{62400,62645,62734,62950,62421990})
                Assert.That(DOL.GS.PacketHandler.PacketLib1110.UsesOwnTooltipIdentity(id),Is.True);
            Assert.That(StormSovereignAbilities.IsHammerfall(SpellFor(21).ID),Is.True);
        }
    }
}
