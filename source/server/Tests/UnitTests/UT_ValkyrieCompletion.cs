using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using DOL.GS.spells;
using DOL.GS.ServerRules;
using DOL.GS.RealmAbilities;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ValkyrieCompletion
    {
        private GameServer _previous;
        private int _groupLimit;
        private PetTestLanguageScope _language;
        private readonly List<GameLiving> _actors = new();
        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase,UT_UnobservedConcentration.EmptyReads>();
            protected override IServerRules ServerRulesImpl => new NormalServerRules();
        }
        private sealed class Actor : GameNPC
        {
            public Actor() { m_ObjectState=eObjectState.Active; }
            public override byte Level { get; set; } = 50;
            public override int MaxHealth => 1000;
            public override int MaxMana => 1000;
            public override bool IsAlive => true;
            public override int GetModified(eProperty property) => 0;
        }
        [SetUp]
        public void Setup()
        {
            _previous=GameServer.Instance;
            _language=new PetTestLanguageScope();
            _groupLimit=DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER;
            DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER=8;
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
        }
        [TearDown]
        public void Cleanup()
        {
            foreach (var actor in _actors)
            {
                foreach (var effect in actor.effectListComponent.GetEffects()) { effect.End();ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick();ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _actors.Clear();DOL.GS.ServerProperties.Properties.GROUP_MAX_MEMBER=_groupLimit;GameServer.LoadTestDouble(_previous);_language.Dispose();
        }
        private Actor NewActor() { var actor=new Actor();_actors.Add(actor);return actor; }
        private static Spell MakeSpell(string type,int id,int capacity=120) => new(new DbSpell {
            SpellID=id,Name=type,Type=type,Target="Self",Duration=6,Value=capacity,Damage=30,ClientEffect=0 },50);
        private static SpellLine Line => new("test-valk","test-valk","Odin's Will",false);
        private static AttackData Hit(GameLiving owner,GameLiving attacker,bool magic,int damage=100,int critical=0) => new() {
            Attacker=attacker,Target=owner,AttackResult=eAttackResult.HitUnstyled,Damage=damage,CriticalDamage=critical,
            AttackType=magic?AttackData.eAttackType.Spell:AttackData.eAttackType.MeleeOneHand,DamageType=eDamageType.Spirit };
        private static AblativeArmorECSGameEffect AddBuffer(GameLiving owner,string type,int id,int capacity=120)
        {
            var spell=MakeSpell(type,id,capacity);
            AblativeArmorSpellHandler handler=type switch {
                "MagicAblativeArmor"=>new MagicAblativeArmorSpellHandler(owner,spell,Line),
                "BothAblativeArmor"=>new BothAblativeArmorSpellHandler(owner,spell,Line),
                _=>new AblativeArmorSpellHandler(owner,spell,Line) };
            var effect=(AblativeArmorECSGameEffect)handler.CreateECSEffect(new(owner,6000,1,handler));
            owner.effectListComponent.BeginTick();
            return effect;
        }
        [TestCase("MagicAblativeArmor",true,70)]
        [TestCase("MagicAblativeArmor",false,100)]
        [TestCase("AblativeArmor",true,100)]
        [TestCase("AblativeArmor",false,70)]
        [TestCase("BothAblativeArmor",true,70)]
        [TestCase("BothAblativeArmor",false,70)]
        public void DamagePipelineUsesCorrectAbsorptionFamily(string type,bool magic,int expected)
        {
            var owner=NewActor();var attacker=NewActor();
            AddBuffer(owner,type,65200);
            var attack=Hit(owner,attacker,magic);
            owner.OnAttackedByEnemy(attack);
            Assert.That(attack.Damage,Is.EqualTo(expected));
        }
        [Test]
        public void MagicBufferDepletesThenAllowsRemainingDamage()
        {
            var owner=NewActor();var attacker=NewActor();
            var effect=AddBuffer(owner,"MagicAblativeArmor",65200,40);
            var first=Hit(owner,attacker,true);owner.OnAttackedByEnemy(first);
            Assert.That(first.Damage,Is.EqualTo(70));Assert.That(effect.RemainingValue,Is.EqualTo(10));
            var second=Hit(owner,attacker,true);owner.OnAttackedByEnemy(second);
            Assert.That(second.Damage,Is.EqualTo(90));Assert.That(effect.RemainingValue,Is.Zero);
            var third=Hit(owner,attacker,true);owner.OnAttackedByEnemy(third);
            Assert.That(third.Damage,Is.EqualTo(100));
        }
        [Test]
        public void MagicDamageWithoutCombatFlagStillConsumesBuffer()
        {
            var owner=NewActor();var attacker=NewActor();
            AddBuffer(owner,"MagicAblativeArmor",65200);
            var attack=Hit(owner,attacker,true);attack.CausesCombat=false;
            owner.OnAttackedByEnemy(attack);
            Assert.That(attack.Damage,Is.EqualTo(70));
        }
        [Test]
        public void CriticalAbsorptionNeverMakesBaseDamageNegative()
        {
            var attack=new AttackData {Damage=5,CriticalDamage=95};
            Assert.That(AblativeArmorSpellHandler.AbsorbDamage(attack,100,100),Is.EqualTo(100));
            Assert.That(attack.Damage,Is.Zero);Assert.That(attack.CriticalDamage,Is.Zero);
        }
        [Test]
        public void PhysicalAndMagicBuffersCoexist()
        {
            var owner=NewActor();var attacker=NewActor();
            AddBuffer(owner,"AblativeArmor",65200);AddBuffer(owner,"MagicAblativeArmor",65201);
            var physical=Hit(owner,attacker,false);owner.OnAttackedByEnemy(physical);
            var magic=Hit(owner,attacker,true);owner.OnAttackedByEnemy(magic);
            Assert.That(physical.Damage,Is.EqualTo(70));Assert.That(magic.Damage,Is.EqualTo(70));
        }
        [TestCase(1000,1000,.03,30)]
        [TestCase(1000,10,.06,10)]
        [TestCase(0,0,.06,0)]
        public void PowerRendIsBoundedByActualPower(int maximum,int current,double fraction,int expected) =>
            Assert.That(PowerRendSpellHandler.DrainAmount(maximum,current,fraction),Is.EqualTo(expected));
        [TestCase(65055,0,1.0)]
        [TestCase(65061,175,0.5)]
        [TestCase(65061,350,0.25)]
        [TestCase(3001,175,1.0)]
        public void OnlyValkyrieAreaHealsUseDistanceFalloff(int id,int distance,double expected) =>
            Assert.That(HealSpellHandler.ValkyrieAreaHealFactor(id,distance,350),Is.EqualTo(expected));
        [Test]
        public void RR5IncludesNonPlayerLivingGroupMembers()
        {
            var owner=NewActor();var ally=NewActor();var group=new Group(owner);
            Assert.That(group.AddMember(owner),Is.True);Assert.That(group.AddMember(ally),Is.True);
            var rr5=new ValhallasBlessingAbility(new DbAbility {KeyName="Valhalla's Blessing",Name="Valhalla's Blessing"},1);
            rr5.Execute(owner);
            Assert.That(owner.EffectList.GetOfType<DOL.GS.Effects.ValhallasBlessingEffect>(),Is.Not.Null);
            Assert.That(ally.EffectList.GetOfType<DOL.GS.Effects.ValhallasBlessingEffect>(),Is.Not.Null);
            owner.EffectList.GetOfType<DOL.GS.Effects.ValhallasBlessingEffect>()?.Cancel(false);
            ally.EffectList.GetOfType<DOL.GS.Effects.ValhallasBlessingEffect>()?.Cancel(false);
            group.RemoveMember(ally);group.RemoveMember(owner);
        }
        [Test]
        public void ChargeHasTrainableRanksAndRR5HasCorrectDurationAndCooldown()
        {
            var charge=new ValkyrieChargeAbility(new DbAbility {KeyName="Valkyrie_Charge",Name="Charge"},1);
            Assert.That(charge.MaxLevel,Is.GreaterThanOrEqualTo(3));
            Assert.That(charge.CostForUpgrade(0),Is.EqualTo(5));
            Assert.That(charge.GetReUseDelay(1),Is.EqualTo(900));
            Assert.That(charge.GetReUseDelay(charge.MaxLevel),Is.EqualTo(90));
            var rr5=new ValhallasBlessingAbility(new DbAbility {KeyName="Valhalla's Blessing",Name="Valhalla's Blessing"},1);
            Assert.That(ValhallasBlessingAbility.DURATION,Is.EqualTo(30000));Assert.That(rr5.GetReUseDelay(1),Is.EqualTo(600));
        }
    }
}
