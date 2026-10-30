using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.AI.Brain;
using DOL.Database;
using DOL.Events;
using DOL.GS;
using DOL.GS.ServerRules;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_StormforgedNetwork
    {
        private GameServer _previous;
        private PetTestLanguageScope _language;
        private long _time;
        private Region _region;
        private readonly List<GameLiving> _actors = new();
        private readonly List<ECSGameEffect> _effects = new();
        private static readonly SpellLine Line = new("network test", "network test", "", true);

        private sealed class Rules : NormalServerRules
        {
            public override bool IsAllowedToAttack(GameLiving attacker, GameLiving defender, bool quiet) =>
                defender != null && defender.IsAlive && defender.Realm != attacker.Realm;
        }
        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
            protected override IServerRules ServerRulesImpl => new Rules();
        }
        private class Actor : GameNPC
        {
            public override bool GroundTargetInView { get; set; }
            public int Moves, Casts;
            public bool Immune, Revealed;
            public Spell LastSpell;
            public override int X => RealX;
            public override int Y => RealY;
            public override int Z => RealZ;
            public override int MaxHealth => 100;
            public override int GetModified(eProperty property) => 100;
            public override bool IsAlive => true;
            public override bool HasAbility(string key) => Immune && (key == DOL.GS.Abilities.CCImmunity || key == DOL.GS.Abilities.RootImmunity);
            public override void Stealth(bool stealth) { Revealed = !stealth; }
            public override bool MoveTo(ushort region, int x, int y, int z, ushort heading)
            {
                Moves++; X = x; Y = y; Z = z; return true;
            }
            public override bool MoveInRegion(ushort region, int x, int y, int z, ushort heading, bool forceMove) => MoveTo(region, x, y, z, heading);
            public override bool CastSpell(Spell spell, SpellLine line, ISpellCastingAbilityHandler ability = null, bool checkLos = true)
            {
                Casts++; LastSpell = spell; return true;
            }
        }
        private sealed class Storm : TurretFnfPet
        {
            public int Moves, Casts;
            public Spell LastSpell;
            public Storm() : base(null) { }
            public override int X => RealX;
            public override int Y => RealY;
            public override int Z => RealZ;
            public override int MaxHealth => 100;
            public override int GetModified(eProperty property) => 100;
            public override bool IsAlive => true;
            public override bool MoveInRegion(ushort region, int x, int y, int z, ushort heading, bool forceMove)
            {
                Moves++; X = x; Y = y; Z = z; return true;
            }
            public override bool CastSpell(Spell spell, SpellLine line, ISpellCastingAbilityHandler ability = null, bool checkLos = true)
            {
                Casts++; LastSpell = spell; return true;
            }
        }
        private sealed class Step : StormforgedStep
        {
            public Step(GameLiving owner, Spell spell) : base(owner, spell, Line) { }
        }

        [SetUp]
        public void Setup()
        {
            _previous = GameServer.Instance;
            _language = new PetTestLanguageScope();
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
            _time = GameLoop.GameLoopTime;
            typeof(GameLoop).GetProperty(nameof(GameLoop.GameLoopTime)).SetValue(null, 120000L);
            _region = (Region)RuntimeHelpers.GetUninitializedObject(typeof(Region));
            typeof(Region).GetField("m_regionData", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(_region, new RegionData { Id = 100 });
            var zones = new List<Zone>();
            typeof(Region).GetField("m_zones", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(_region, zones);
            zones.Add(new Zone(_region, 100, "Test terrain", 0, 0, 10000, 10000, 100, false, 0, false, 0, 0, 0, 0, 0));
        }

        [TearDown]
        public void Cleanup()
        {
            foreach (var effect in _effects)
            {
                effect.End(); effect.Owner.effectListComponent.BeginTick(); ServiceObjectStore.Remove(effect);
            }
            foreach (var actor in _actors)
            {
                foreach (var entry in AutonomousPetSupport.OwnedFieldTurrets(actor).ToArray())
                    AutonomousPetSupport.UnregisterFieldTurret(actor, entry.Turret);
                ServiceObjectStore.Remove(actor.effectListComponent);
                if (actor is GameNPC npc && npc.Brain != null) ServiceObjectStore.Remove(npc.Brain);
            }
            _actors.Clear(); _effects.Clear();
            typeof(GameLoop).GetProperty(nameof(GameLoop.GameLoopTime)).SetValue(null, _time);
            GameServer.LoadTestDouble(_previous);
            _language.Dispose();
        }

        private Actor NewActor(int x = 1000)
        {
            var actor = new Actor { ObjectState = GameObject.eObjectState.Active, CurrentRegion = _region, X = x, Y = 1000, Z = 100, Realm = eRealm.Midgard };
            _actors.Add(actor); return actor;
        }

        private Storm NewStorm(GameLiving owner)
        {
            var storm = new Storm { ObjectState = GameObject.eObjectState.Active, CurrentRegion = _region, X = 1200, Y = 1000, Z = 100,
                NPCTemplate = new NpcTemplate(new DbNpcTemplate { TemplateId = 60171002, Name = "Lightning Bomb" }) };
            storm.SetOwnBrain(new ControlledMobBrain(owner) { Body = storm });
            AutonomousPetSupport.RegisterFieldTurret(owner, storm);
            _actors.Add(storm); return storm;
        }

        private T Start<T>(T effect) where T : ECSGameEffect
        {
            _effects.Add(effect); Assert.That(effect.Start(), Is.True);
            effect.Owner.effectListComponent.BeginTick(); Assert.That(effect.IsActive, Is.True); return effect;
        }

        private static Spell Spell(int id, string type, int range = 0, int radius = 0) => new(new DbSpell
        {
            SpellID = id, Name = type, Type = type, Target = type == "StormforgedStrike" ? "Enemy" : "Self",
            Range = range, Radius = radius, Damage = 200, DamageType = 12, Duration = 3600
        }, 30);

        [Test]
        public void StormstepLandsInFrontOfItsTargetAndStillValidatesGround()
        {
            var owner = NewActor(); var enemy = NewActor(2800); enemy.Realm = eRealm.None; enemy.Health = 100;
            var step = new Step(owner, Spell(62210, "StormforgedStep", 2000));
            step.ApplyEffectOnTarget(enemy);
            Assert.That(owner.X, Is.EqualTo(2710));
            Assert.That(owner.Y, Is.EqualTo(1000));
            // Already beside the target: stay put rather than stacking onto it.
            owner.X = 2750;
            Assert.That(StormforgedTravel.ResolveBeside(owner, enemy).X, Is.EqualTo(2750));
            // No target, no travel.
            owner.X = 1000;
            step.ApplyEffectOnTarget(null);
            Assert.That(owner.X, Is.EqualTo(1000));
            Assert.That(StormforgedTravel.TryResolvePoint(owner, new Point3D(-1, 1000, 100), 2000, out _), Is.False);
            Assert.That(StormforgedTravel.TryResolvePoint(owner, new Point3D(1200, 1000, 900), 2000, out _), Is.False);
        }

        [Test]
        public void RideTheStormEchoesOwnedSourcesAndNeverRecursesOrCopiesOtherCasters()
        {
            var owner = NewActor(); var enemy = NewActor(1500); enemy.Realm = eRealm.None;
            var other = NewActor();
            var storm = NewStorm(owner); var otherStorm = NewStorm(other);
            var main = NewActor(1100);
            main.NPCTemplate = new NpcTemplate(new DbNpcTemplate { TemplateId = 60171001, Name = "Stormbound Elemental" });
            var brain = new ControlledMobBrain(owner) { Body = main }; main.SetOwnBrain(brain);
            owner.InitControlledBrainArray(1); owner.ControlledNpcList[0] = brain;
            var effect = Start(new StormforgedRideEffect(new(owner, 3600000, 1, new StormforgedRide(owner, Spell(62211, "StormforgedRide"), Line))));
            var hammer = Spell(62016, "StormforgedStrike", 1500, 350);
            var cast = new StormforgedStrike(owner, hammer, Line);
            GameEventMgr.Notify(GameLivingEvent.CastFinished, owner, new CastingEventArgs(cast, enemy));
            Assert.That(main.Casts, Is.EqualTo(1)); Assert.That(storm.Casts, Is.EqualTo(1)); Assert.That(otherStorm.Casts, Is.Zero);
            Assert.That(storm.LastSpell.Radius, Is.EqualTo(350));
            Assert.That(storm.LastSpell.IsInstantCast, Is.True); Assert.That(storm.LastSpell.Power, Is.Zero);
            Assert.That(effect.TryEcho(new DirectDamageSpellHandler(owner, storm.LastSpell, Line), enemy), Is.Zero);
            Assert.That(effect.TryEcho(new StormforgedStrike(other, hammer, Line), enemy), Is.Zero);
            Assert.That(StormforgedRideEffect.IsEchoable(Spell(62004, "StormforgedStrike")), Is.False);
            effect.End(); owner.effectListComponent.BeginTick();
            GameEventMgr.Notify(GameLivingEvent.CastFinished, owner, new CastingEventArgs(cast, enemy));
            Assert.That(storm.Casts, Is.EqualTo(1));
        }

        [Test]
        public void ThunderRecallMovesOnlyOwnedStormsAndRefreshesTheirRealSummonEffect()
        {
            var owner = NewActor(); var other = NewActor(); var storm = NewStorm(owner);
            var summon = Spell(62152, "SummonAnimistFnF");
            var effect = Start(new ECSGameSpellEffect(new(storm, 1000, 1, new SpellHandler(owner, summon, Line))));
            Assert.That(StormforgedTravel.MoveStorm(other, storm, new Point3D(2000, 1000, 100)), Is.False);
            Assert.That(StormforgedTravel.MoveStorm(owner, storm, new Point3D(2000, 1000, 100)), Is.True);
            Assert.That(storm.X, Is.EqualTo(2000)); Assert.That(storm.Moves, Is.EqualTo(1));
            Assert.That(effect.Duration, Is.EqualTo(120000));
            Assert.That(effect.ExpireTick, Is.EqualTo(GameLoop.GameLoopTime + 120000));
            Assert.That(AutonomousPetSupport.OwnedFieldTurrets(owner).Single().ExpiresAt, Is.EqualTo(effect.ExpireTick));
            Assert.That(StormforgedTravel.IsOwnedStorm(owner, NewActor()), Is.False);
        }

        [Test]
        public void EyePullsHostileMobsButLeavesFriendliesAndImmuneMobsAlone()
        {
            var owner = NewActor(); var enemy = NewActor(1500); enemy.Realm = eRealm.None;
            var friendly = NewActor(1500); var immune = NewActor(1500); immune.Realm = eRealm.None; immune.Immune = true;
            Assert.That(StormforgedTravel.Pull(owner, enemy), Is.True);
            Assert.That(enemy.X, Is.EqualTo(1090)); Assert.That(owner.Revealed, Is.True);
            Assert.That(StormforgedTravel.Pull(owner, friendly), Is.False);
            Assert.That(StormforgedTravel.Pull(owner, immune), Is.False);
            Assert.That(friendly.Moves, Is.Zero); Assert.That(immune.Moves, Is.Zero);
            Assert.That(StormforgedTravel.Pull(owner, enemy), Is.False, "Already gathered mobs stay put");
        }
    }
}
