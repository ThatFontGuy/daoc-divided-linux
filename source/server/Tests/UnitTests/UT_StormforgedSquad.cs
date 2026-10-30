using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture, NonParallelizable]
public class UT_StormforgedSquad
{
    private GameServer _previous;
    private PetTestLanguageScope _language;
    private readonly List<GameNPC> _actors = new();
    private Region _region;
    private DOL.GS.PropertyCalc.IPropertyCalculator _healthCalculator;
    private class Server : GameServer
    {
        protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
        protected override GS.ServerRules.IServerRules ServerRulesImpl => new Rules();
    }
    private class Rules : GS.ServerRules.NormalServerRules
    {
        public override bool IsSameRealm(GameLiving a, GameLiving b, bool quiet) => a?.Realm == b?.Realm;
    }
    private class Human : GamePlayer
    {
        private Human() : base(null, null) { }
        public override byte Level => 50;
        public override int MaxHealth => 100;
        public override int Health { get; set; }
        public override bool IsAlive => Health > 0;
        public override int GetModified(eProperty property) => 100;
    }
    private class Root : GameNPC
    {
        public override byte Level { get; set; }
        public override int MaxHealth => 100;
        public override int GetModified(eProperty property) => 100;
    }
    private class TestCommander : StormforgedCommander
    {
        public TestCommander(INpcTemplate template) : base(template) { }
        public override int X => RealX;
        public override int GetModified(eProperty property) => property == eProperty.MaxHealth ? base.GetModified(property) : 100;
    }
    private class TestSupport : StormforgedSupportPet
    {
        public TestSupport(INpcTemplate template) : base(template) { }
        public override int GetModified(eProperty property) => property == eProperty.MaxHealth ? base.GetModified(property) : 100;
    }
    private class SupportBrain : StormforgedSupportBrain
    {
        public int Releases;
        public SupportBrain(GameLiving owner) : base(owner) { }
        public GameLiving Choose(Spell spell) => FindTargetForDefensiveSpell(spell);
        public override void OnRelease() { Releases++; }
    }
    private class Summon : StormforgedPet
    {
        public Summon(GameLiving root, GameSummonedPet pet) : base(root, Spell("StormforgedPet", 62030), Line) { Pet = pet; }
    }
    private static readonly SpellLine Line = new("squad", "squad", "", true);
    private static Spell Spell(string type, int id, double damage = 0, double value = 0) => new(new DbSpell
    {
        SpellID = id, Type = type, Target = type == "Heal" ? "Realm" : "Enemy", Range = 1800,
        Damage = damage, Value = value, CastTime = 2, RecastDelay = 2
    }, 1);
    private static NpcTemplate Template(int id) => new(new DbNpcTemplate
    {
        TemplateId = id, Name = "Storm test", Model = "114", Level = "0", Size = "50",
        TetherRange = 2, Strength = 120, Constitution = 120, Dexterity = 100, Quickness = 100
    });

    [OneTimeSetUp]
    public void Logging() => DOL.Logging.LoggerManager.InitializeWithExplicitLibrary(null, DOL.Logging.LogLibrary.None);

    [SetUp]
    public void Setup()
    {
        _previous = GameServer.Instance;
        GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
        _language = new PetTestLanguageScope();
        var calculators = (DOL.GS.PropertyCalc.IPropertyCalculator[])typeof(GameLiving)
            .GetField("m_propertyCalc", BindingFlags.Static | BindingFlags.NonPublic).GetValue(null);
        _healthCalculator = calculators[(int)eProperty.MaxHealth];
        calculators[(int)eProperty.MaxHealth] = new DOL.GS.PropertyCalc.MaxHealthCalculator();
        _region = new Region(new RegionData { Id = 100, Name = "Storm test", Description = "Storm test", Mobs = [] });
    }
    [TearDown]
    public void Cleanup()
    {
        foreach (var actor in _actors)
        {
            ServiceObjectStore.Remove(actor.castingComponent);
            ServiceObjectStore.Remove(actor.effectListComponent);
            if (actor.Brain != null) ServiceObjectStore.Remove(actor.Brain);
        }
        _actors.Clear();
        ((DOL.GS.PropertyCalc.IPropertyCalculator[])typeof(GameLiving)
            .GetField("m_propertyCalc", BindingFlags.Static | BindingFlags.NonPublic).GetValue(null))[(int)eProperty.MaxHealth] = _healthCalculator;
        _language.Dispose();
        GameServer.LoadTestDouble(_previous);
    }
    private T Track<T>(T npc) where T : GameNPC
    {
        npc.CurrentRegion = _region; npc.Realm = eRealm.Midgard;
        npc.ObjectState = GameObject.eObjectState.Active;
        _actors.Add(npc); return npc;
    }
    private (Root root, StormforgedCommander commander, StormforgedSupportPet support, SupportBrain brain) Graph(byte level)
    {
        var root = Track(new Root { Level = level, Health = 100 });
        var commander = Track(new TestCommander(Template(60171001)));
        commander.SetOwnBrain(new StormforgedCommanderBrain(root));
        commander.SetPetLevel();
        commander.Health = commander.MaxHealth;
        var support = Track(new TestSupport(Template(60171003)));
        var brain = new SupportBrain(commander);
        support.SetOwnBrain(brain);
        support.SetPetLevel(); support.Health = support.MaxHealth;
        commander.AddControlledBrain(brain);
        return (root, commander, support, brain);
    }

    [TestCase((byte)5)] [TestCase((byte)25)] [TestCase((byte)50)]
    public void CommanderAndSupportMatchOwnerAndFollowLevelUps(byte level)
    {
        var (root, commander, support, _) = Graph(level);
        Assert.That(commander.Level, Is.EqualTo(level));
        Assert.That(support.Level, Is.EqualTo(level));
        Assert.That(commander.SubPetCapacity, Is.EqualTo(2));
        Assert.That(commander.MaxHealthScalingFactor, Is.EqualTo(4));
        Assert.That(commander.DamageFactor, Is.EqualTo(2));
        Assert.That(commander.GetArmorAbsorb(eArmorSlot.TORSO), Is.GreaterThanOrEqualTo(.35));
        Assert.That(((CommanderBrain)commander.Brain).ModifyDamageWithTaunt(100), Is.EqualTo(800));
        root.Level++;
        commander.SetPetLevel(); support.SetPetLevel();
        Assert.That(commander.Level, Is.EqualTo(root.Level));
        Assert.That(support.Level, Is.EqualTo(root.Level));
    }

    [Test]
    public void SupportKeepsHealingAndOffensiveSpellsWithoutCompoundingScaling()
    {
        var (_, _, support, _) = Graph(25);
        var bolt = Spell("DirectDamage", 62209, damage: 240);
        support.Spells = [bolt, Spell("Heal", 62208, value: 650), Spell("CombatSpeedDebuff", 62217, value: 25)];
        support.SortSpells(); support.SortSpells();
        Assert.That(support.HarmfulSpells.Single(s => s.ID == 62209).Damage, Is.EqualTo(120));
        Assert.That(support.HealSpells.Single().Value, Is.EqualTo(325));
        Assert.That(bolt.Damage, Is.EqualTo(240));
        Assert.That(support.HarmfulSpells.Select(s => s.ID), Does.Contain(62217));
    }

    [Test]
    public void MenderSelectsInjuredCommanderAndRejectsOutOfRangeTargets()
    {
        var (root, commander, support, brain) = Graph(50);
        commander.Health = Math.Max(1, commander.MaxHealth / 4);
        var heal = Spell("Heal", 62208, value: 650);
        Assert.That(brain.Choose(heal), Is.SameAs(commander));
        commander.X = 10000; root.X = 10000;
        Assert.That(brain.Choose(heal), Is.Null);
    }

    [Test]
    public void MenderPrioritizesHumanSummonerAndOffersNativeBuffsToOwnerAndCommander()
    {
        var (_, commander, support, brain) = Graph(50);
        var human = (Human)RuntimeHelpers.GetUninitializedObject(typeof(Human));
        human.CurrentRegion = _region; human.Realm = eRealm.Midgard;
        human.ObjectState = GameObject.eObjectState.Active; human.Health = 70;
        human.effectListComponent = EffectListComponent.Create(human);
        try
        {
            commander.SetOwnBrain(new StormforgedCommanderBrain(human));
            commander.Health = Math.Max(1, commander.MaxHealth / 4);
            Assert.That(brain.Choose(Spell("Heal", 62208, value: 650)), Is.SameAs(human));
            var buff = new Spell(new DbSpell { SpellID = 62220, Type = "StrengthBuff", Target = "Realm", Range = 1800, Value = 44, Duration = 3600 }, 1);
            Assert.That(brain.Choose(buff), Is.SameAs(human));
            human.CurrentRegion = null;
            Assert.That(brain.Choose(buff), Is.SameAs(commander));
        }
        finally { ServiceObjectStore.Remove(human.effectListComponent); }
    }

    [Test]
    public void ReleasingCommanderReleasesBothSupportBrains()
    {
        var (root, commander, support, brain) = Graph(50);
        var second = Track(new TestSupport(Template(60171004)));
        var otherBrain = new SupportBrain(commander);
        second.SetOwnBrain(otherBrain); second.SetPetLevel();
        Assert.That(commander.AddControlledBrain(otherBrain), Is.True);
        new Summon(root, commander).OnPetReleased();
        Assert.That(brain.Releases, Is.EqualTo(1));
        Assert.That(otherBrain.Releases, Is.EqualTo(1));
    }

    [TestCase(0, true)] [TestCase(12, true)] [TestCase(15, true)] [TestCase(16, false)] [TestCase(17, false)]
    public void TurretsAllowSixteenAndRejectSeventeenth(int owned, bool allowed) =>
        Assert.That(StormforgedTurretRules.CanSummon(owned), Is.EqualTo(allowed));
}
