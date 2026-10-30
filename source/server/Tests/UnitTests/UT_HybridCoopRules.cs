using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS;
using DOL.GS.Keeps;
using DOL.GS.ServerRules;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture, NonParallelizable]
public class UT_HybridCoopRules
{
    private GameServer _previous;
    private bool _enabled;
    private int _claimLimit;
    private readonly List<GameNPC> _pets = new();
    private class Server : GameServer
    {
        public static Rules Active;
        protected override IServerRules ServerRulesImpl => Active;
        public override GameServerConfiguration Configuration => new() { ServerType = EGameServerType.GST_Normal };
        protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
    }
    private class Human : GamePlayer
    {
        private Human() : base(null, null) { }
        public int Position;
        public override int X => Position;
        public override int Y => 100;
        public override bool IsAlive => true;
    }
    private class Pet : GameNPC
    {
        public int Position;
        public override int X => Position;
        public override int Y => 100;
        public override bool IsAlive => true;
        public override int MaxHealth => 100;
        public override int GetModified(eProperty property) => 100;
    }
    private class Rules : HybridCoopRules
    {
        public bool GeneralAllowed = true;
        public readonly HashSet<GameLiving> Protected = new();
        protected override bool GeneralAttack(GameLiving a, GameLiving b, bool quiet) => GeneralAllowed;
        protected override bool ProtectedArea(GameLiving living) => Protected.Contains(living);
    }
    private class TestKeep : GameKeep
    {
        public bool Portal;
        public int Resets, Claims;
        public eRealm CapturedRealm;
        public override bool IsPortalKeep => Portal;
        public override void Reset(eRealm realm) { Resets++; CapturedRealm=realm; Guild=null; }
        public override void Claim(GamePlayer player) { Claims++; Guild=player.Guild; }
    }
    [OneTimeSetUp]
    public void Logging() => DOL.Logging.LoggerManager.InitializeWithExplicitLibrary(null, DOL.Logging.LogLibrary.None);
    [SetUp]
    public void Setup()
    {
        _previous = GameServer.Instance;
        _enabled = GS.ServerProperties.Properties.HYBRID_COOP_PVP;
        _claimLimit = GS.ServerProperties.Properties.GUILDS_CLAIM_LIMIT;
        GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
    }
    [TearDown]
    public void Cleanup()
    {
        foreach (var pet in _pets)
        {
            ServiceObjectStore.Remove(pet.effectListComponent);
            ServiceObjectStore.Remove(pet.castingComponent);
            if (pet.Brain != null) ServiceObjectStore.Remove(pet.Brain);
        }
        _pets.Clear();
        GS.ServerProperties.Properties.HYBRID_COOP_PVP = _enabled;
        GS.ServerProperties.Properties.GUILDS_CLAIM_LIMIT = _claimLimit;
        GameServer.LoadTestDouble(_previous);
    }
    private static Region Region(ushort id)
    {
        var region = (Region)RuntimeHelpers.GetUninitializedObject(typeof(Region));
        typeof(Region).GetField("m_regionData", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(region, new RegionData { Id = id });
        var zones = new List<Zone>();
        typeof(Region).GetField("m_zones", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(region, zones);
        zones.Add(new Zone(region, 0, "Home", 0, 0, 10000, 10000, 0, false, 0, false, 0, 0, 0, 0, 0));
        zones.Add(new Zone(region, 11, "Frontier", 10000, 0, 10000, 10000, 0, false, 0, false, 0, 0, 0, 0, 0));
        return region;
    }
    private static Human Player(Region region, eRealm realm, int position = 11000)
    {
        var player = (Human)RuntimeHelpers.GetUninitializedObject(typeof(Human));
        player.CurrentRegion = region; player.Realm = realm; player.Position = position;
        typeof(GameLiving).GetField("<TempProperties>k__BackingField", BindingFlags.NonPublic | BindingFlags.Instance)
            .SetValue(player, new PropertyCollection());
        return player;
    }
    private static Guild Guild(string id) => new(new DbGuild { GuildID = id, GuildName = id, BonusStartTime = DateTime.MinValue });
    private static void Join(Human player, Guild guild) => typeof(GamePlayer)
        .GetField("m_guild", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(player, guild);
    private Pet Summon(GameLiving owner, int x = 11000)
    {
        var pet = new Pet { Position = x, CurrentRegion = owner.CurrentRegion, Realm = owner.Realm };
        pet.SetOwnBrain(new ControlledMobBrain(owner)); _pets.Add(pet); return pet;
    }

    [TestCase(1,0,false)] [TestCase(1,11,true)] [TestCase(1,12,true)] [TestCase(1,14,true)] [TestCase(1,15,true)]
    [TestCase(100,100,false)] [TestCase(100,111,true)] [TestCase(100,112,true)] [TestCase(100,113,true)] [TestCase(100,115,true)]
    [TestCase(200,200,false)] [TestCase(200,210,true)] [TestCase(200,211,true)] [TestCase(200,212,true)] [TestCase(200,214,true)]
    [TestCase(249,249,true)] [TestCase(250,250,true)] [TestCase(251,251,true)] [TestCase(252,252,true)] [TestCase(253,253,true)]
    [TestCase(163,171,true)] [TestCase(165,165,true)] [TestCase(238,238,true)]
    [TestCase(101,101,false)] [TestCase(2,11,false)] [TestCase(151,151,false)]
    public void WarBoundariesKeepHomeLandsCitiesHousingAndSIProtected(int region, int zone, bool war) =>
        Assert.That(HybridCoopRules.IsWarLocation((ushort)region, (ushort)zone), Is.EqualTo(war));

    [Test]
    public void DifferentRealmsCooperateAtHomeAndFightRealmAgainstRealmInFrontier()
    {
        var region = Region(1); var a = Player(region, eRealm.Albion,100); var b = Player(region, eRealm.Midgard,200);
        var rules = new Rules();
        Assert.That(rules.IsAllowedToAttack(a,b,true), Is.False);
        Assert.That(rules.IsSameRealm(a,b,true), Is.True);
        Assert.That(rules.GetLivingRealm(a,b), Is.EqualTo((byte)eRealm.Albion), "Shown as a friend at home.");
        a.Position = b.Position = 11000;
        Assert.That(rules.IsAllowedToAttack(a,b,true), Is.True);
        Assert.That(rules.IsSameRealm(a,b,true), Is.False);
        Assert.That(rules.GetLivingRealm(a,b), Is.EqualTo((byte)eRealm.Midgard), "Shown as the enemy realm it is.");
        Assert.That(HybridCoopRules.RewardEnemies(a,b), Is.True);
        b.Realm = a.Realm;
        Assert.That(rules.IsAllowedToAttack(a,b,true), Is.False, "Same realm is friendly in the frontier, as normal.");
        Assert.That(rules.IsSameRealm(a,b,true), Is.True);
        Assert.That(HybridCoopRules.RewardEnemies(a,b), Is.False);
    }
    [Test]
    public void GroupsStayOneTeamButGuildsDoNotOverrideRealms()
    {
        var region = Region(249); var a = Player(region,eRealm.Albion); var b = Player(region,eRealm.Midgard);
        var rules = new Rules();
        Assert.That(rules.IsAllowedToAttack(a,b,true), Is.True);
        var guild = Guild("one"); Join(a,guild); Join(b,guild);
        Assert.That(rules.IsAllowedToAttack(a,b,true), Is.True, "A mixed-realm guild still fights by realm in DF.");
        a.Group = b.Group = new Group(a);
        Assert.That(rules.IsAllowedToAttack(a,b,true), Is.False);
        Assert.That(rules.IsSameRealm(a,b,true), Is.True);
        Assert.That(HybridCoopRules.RewardEnemies(a,b), Is.False);
    }
    [Test]
    public void RealmsGroupAcrossOnlyOutsideTheWarAreas()
    {
        var region = Region(1); var a = Player(region,eRealm.Albion,100); var b = Player(region,eRealm.Midgard,200);
        var rules = new Rules();
        Assert.That(rules.IsAllowedToGroup(a,b,true), Is.True);
        GS.ServerProperties.Properties.HYBRID_COOP_PVP=false;
        Assert.That(HybridCoopRules.CanGroup(a,b), Is.False, "Bots keep their realm unless co-op is on.");
        GS.ServerProperties.Properties.HYBRID_COOP_PVP=true;
        Assert.That(HybridCoopRules.CanGroup(a,b), Is.True);
        b.Position = 11000;
        Assert.That(rules.IsAllowedToGroup(a,b,true), Is.False);
        Assert.That(HybridCoopRules.CanGroup(a,b), Is.False);
        b.Realm = a.Realm;
        Assert.That(rules.IsAllowedToGroup(a,b,true), Is.True);
        Assert.That(HybridCoopRules.CanGroup(a,b), Is.True);
    }
    [Test]
    public void PetTreeAndAreaAttacksRespectOwnerTeamsAndBothSidesOfSafeBoundary()
    {
        var region = Region(1); var a = Player(region,eRealm.Albion); var b = Player(region,eRealm.Midgard);
        var commander = Summon(a); var support = Summon(commander); var bomb = Summon(a);
        var rules = new Rules();
        Assert.That(HybridCoopRules.Controller(support), Is.SameAs(a));
        Assert.That(rules.IsAllowedToAttack(support,b,true), Is.True);
        Assert.That(rules.IsAllowedToAttack(bomb,b,true), Is.True);
        Assert.That(rules.IsAllowedToAttack(support,a,true), Is.False);
        a.Position=100;
        Assert.That(rules.IsAllowedToAttack(support,b,true), Is.False);
        Assert.That(rules.IsSameRealm(a,b,true), Is.False, "Can't heal an opposing team from the safe side.");
        a.Position=11000; bomb.Position=100;
        Assert.That(rules.IsAllowedToAttack(bomb,b,true), Is.False);
        bomb.Position=11000; rules.Protected.Add(b);
        Assert.That(rules.IsAllowedToAttack(bomb,b,true), Is.False);
        rules.Protected.Clear(); rules.GeneralAllowed=false;
        Assert.That(rules.IsAllowedToAttack(bomb,b,true), Is.False, "Core immunity/GM/peace checks still gate attacks.");
    }
    [Test]
    public void KeepsBelongToRealmsAndProtectGroupGuests()
    {
        var region=Region(249); var owner=Player(region,eRealm.Albion); var guest=Player(region,eRealm.Midgard);
        var keep=new TestKeep { DBKeep=new DbKeep { Region=249, Realm=(byte)eRealm.Albion }, CurrentRegion=region };
        Assert.That(HybridCoopRules.KeepEnemy(keep,owner), Is.False);
        Assert.That(HybridCoopRules.KeepEnemy(keep,guest), Is.True);
        Assert.That(HybridCoopRules.KeepEnemy(keep,Summon(guest)), Is.True, "A pet answers for its owner.");
        owner.Group=guest.Group=new Group(owner);
        typeof(Group).GetField("_groupMembers",BindingFlags.NonPublic|BindingFlags.Instance).SetValue(owner.Group,new List<GameLiving>{owner,guest});
        Assert.That(HybridCoopRules.KeepEnemy(keep,guest), Is.False);
        Assert.That(HybridCoopRules.KeepEnemy(keep,guest,false), Is.True);
        keep.Portal=true;
        Assert.That(HybridCoopRules.KeepEnemy(keep,guest,false), Is.False);
    }
    [Test]
    public void CaptureByOwnedPetAssignsGuildAndPortalKeepsCannotBeCaptured()
    {
        var region=Region(249); var owner=Player(region,eRealm.Midgard);
        var guild=Guild("winner"); Join(owner,guild);
        var keep=new TestKeep { DBKeep=new DbKeep { Region=249 }, CurrentRegion=region };
        GS.ServerProperties.Properties.GUILDS_CLAIM_LIMIT=1;
        HybridCoopRules.CaptureKeep(keep,Summon(owner));
        Assert.That(keep.Resets,Is.EqualTo(1));
        Assert.That(keep.CapturedRealm,Is.EqualTo(eRealm.Midgard));
        Assert.That(keep.Guild,Is.SameAs(guild));
        Assert.That(keep.Claims,Is.EqualTo(1));
        keep.Portal=true;
        HybridCoopRules.CaptureKeep(keep,owner);
        Assert.That(keep.Resets,Is.EqualTo(1));
        keep.Portal=false; GS.ServerProperties.Properties.GUILDS_CLAIM_LIMIT=0;
        HybridCoopRules.CaptureKeep(keep,owner);
        Assert.That(keep.Guild,Is.Null);
        Assert.That(keep.Claims,Is.EqualTo(1),"Existing claim limit is respected.");
    }

    [Test]
    public void LateSpellDamageAndHealingRecheckSafeBoundaryAndGuildAlignment()
    {
        var region=Region(1); var a=Player(region,eRealm.Albion); var b=Player(region,eRealm.Midgard);
        var rules=new Rules(); Server.Active=rules;
        GS.ServerProperties.Properties.HYBRID_COOP_PVP=true;
        var spell=new Spell(new DbSpell { SpellID=62200, Type="DirectDamage", Target="Enemy" },1);
        var handler=new GS.Spells.SpellHandler(a,spell,null);
        var attack=new AttackData { Attacker=a, Target=b, Damage=100, CriticalDamage=25 };
        b.Position=100;
        handler.DamageTarget(attack,false);
        Assert.That(attack.Damage,Is.Zero);
        Assert.That(attack.CriticalDamage,Is.Zero);
        a.ObjectState=b.ObjectState=GameObject.eObjectState.Active;
        Assert.That(new GS.Spells.HealSpellHandler(a,spell,null).HealTarget(b,100,true),Is.False);
    }

    [Test]
    public void FactoryOptInAndDFGateDoNotRequireChangingTheGlobalServerType()
    {
        GS.ServerProperties.Properties.HYBRID_COOP_PVP=true;
        Assert.That(ScriptMgr.CreateServerRules(EGameServerType.GST_Normal), Is.TypeOf<HybridCoopRules>());
        Assert.That(DFEnterJumpPoint.CanRealmEnter(eRealm.Albion), Is.True);
        Assert.That(new Rules().IsAllowedToJoinGuild(null,null), Is.True);
        Assert.That(new Rules().IsAllowedToGroup(null,null,true), Is.True);
        GS.ServerProperties.Properties.HYBRID_COOP_PVP=false;
        Assert.That(ScriptMgr.CreateServerRules(EGameServerType.GST_Normal), Is.TypeOf<NormalServerRules>());
    }
}
