using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.Events;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_StormforgedHeroics
    {
        private GameServer _previous;
        private PetTestLanguageScope _language;
        private long _time;
        private readonly List<ECSGameEffect> _effects = new();
        private readonly List<Actor> _actors = new();
        private static readonly SpellLine Line = new("heroic test", "heroic test", "", true);

        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
        }

        private sealed class Actor : GameNPC
        {
            public int Deaths;
            public override int MaxHealth => 100;
            public override int MaxMana => 100;
            public override int MaxEndurance => 100;
            public override int Health { get; set; } = 100;
            public override int Mana { get; set; } = 10;
            public override int Endurance { get; set; } = 10;
            public override ushort Model { get; set; } = 153;
            public override bool IsAlive => Health > 0;
            public override int GetModified(eProperty property) => 100;
            public override int CalculateCastingTime(SpellHandler handler) => handler.Spell.CastTime;
            public override void Die(GameObject killer) { Deaths++; }
        }

        private sealed class Rebirth : StormforgedSecondThunderEffect
        {
            public int Bursts;
            public Rebirth(in ECSGameEffectInitParams init) : base(init) { }
            protected override void CastRebirthBurst() { Bursts++; }
        }

        private sealed class Guard : StormforgedStormguardEffect
        {
            public int Counters;
            public Guard(in ECSGameEffectInitParams init) : base(init) { }
            protected override void CastRetaliation(GameLiving attacker) { Counters++; }
        }

        [SetUp]
        public void Setup()
        {
            _previous = GameServer.Instance;
            _language = new PetTestLanguageScope();
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
            _time = GameLoop.GameLoopTime;
            typeof(GameLoop).GetProperty(nameof(GameLoop.GameLoopTime)).SetValue(null, 120000L);
        }

        [TearDown]
        public void Cleanup()
        {
            foreach (var effect in _effects)
            {
                effect.End();
                effect.Owner.effectListComponent.BeginTick();
                ServiceObjectStore.Remove(effect);
            }
            foreach (var actor in _actors)
                ServiceObjectStore.Remove(actor.effectListComponent);
            _effects.Clear();
            _actors.Clear();
            typeof(GameLoop).GetProperty(nameof(GameLoop.GameLoopTime)).SetValue(null, _time);
            GameServer.LoadTestDouble(_previous);
            _language.Dispose();
        }

        private Actor NewActor()
        {
            var actor = new Actor { ObjectState = GameObject.eObjectState.Active };
            _actors.Add(actor);
            return actor;
        }

        private T Start<T>(T effect) where T : ECSGameEffect
        {
            _effects.Add(effect);
            Assert.That(effect.Start(), Is.True);
            effect.Owner.effectListComponent.BeginTick();
            Assert.That(effect.IsActive, Is.True);
            return effect;
        }

        private static Spell MakeSpell(int id, string type, double value = 0) => new(new DbSpell
        {
            SpellID = id, TooltipId = (ushort)(20800 + id - 62200), Name = type,
            Type = type, Target = "Self", Duration = 60, Value = value
        }, 40);

        [Test]
        public void AvatarTransformsRegeneratesAcceleratesOnlyPrivateSpellsAndRestoresAppearance()
        {
            var owner = NewActor();
            owner.Health = owner.Mana = owner.Endurance = 50;
            var avatar = MakeSpell(62200, "StormforgedAvatar", 918);
            var effect = Start(new StormforgedAvatarEffect(new(owner, 60000, 1, new StormforgedAvatar(owner, avatar, Line))));
            Assert.That(owner.Model, Is.EqualTo(918));
            Assert.That(StormforgedHeroicRules.HasAvatar(owner), Is.True);
            effect.OnEffectPulse();
            Assert.That(owner.Health, Is.EqualTo(65));
            Assert.That(owner.Mana, Is.EqualTo(65));
            Assert.That(owner.Endurance, Is.EqualTo(65));
            var custom = new Spell(new DbSpell { SpellID = 62000, Type = "StormforgedStrike", Target = "Enemy", CastTime = 2 }, 40);
            var stock = new Spell(new DbSpell { SpellID = 3508, Type = "DirectDamage", Target = "Enemy", CastTime = 2 }, 40);
            Assert.That(new SpellHandler(owner, custom, Line).CalculateCastingTime(), Is.EqualTo(250));
            Assert.That(new SpellHandler(owner, stock, Line).CalculateCastingTime(), Is.EqualTo(2000));
            effect.End(); owner.effectListComponent.BeginTick();
            Assert.That(owner.Model, Is.EqualTo(153));
            Assert.That(StormforgedHeroicRules.HasAvatar(owner), Is.False);
        }

        [Test]
        public void SecondThunderInterceptsActualFatalDamageAndCannotBeResetByRecasting()
        {
            var owner = NewActor(); owner.Health = 30;
            var spell = MakeSpell(62202, "StormforgedSecondThunder");
            var effect = Start(new Rebirth(new(owner, 3600000, 1, new StormforgedSecondThunder(owner, spell, Line))));
            owner.TakeDamage(null, eDamageType.Energy, 20, 20);
            Assert.That(owner.Health, Is.EqualTo(100));
            Assert.That(owner.Mana, Is.EqualTo(100));
            Assert.That(owner.Endurance, Is.EqualTo(100));
            Assert.That(owner.Deaths, Is.Zero);
            Assert.That(effect.Bursts, Is.EqualTo(1));
            effect.End(); owner.effectListComponent.BeginTick();
            var recast = Start(new Rebirth(new(owner, 3600000, 1, new StormforgedSecondThunder(owner, spell, Line))));
            owner.Health = 30;
            Assert.That(recast.TrySave(30), Is.False, "Rearming the buff must preserve the trigger cooldown");
            typeof(GameLoop).GetProperty(nameof(GameLoop.GameLoopTime)).SetValue(null, 240001L);
            Assert.That(recast.TrySave(30), Is.True);
            Assert.That(recast.Bursts, Is.EqualTo(1));
        }

        [Test]
        public void SecondThunderIgnoresNonfatalDamageAndUnprotectedActorsStillDie()
        {
            var owner = NewActor();
            var spell = MakeSpell(62202, "StormforgedSecondThunder");
            var effect = Start(new Rebirth(new(owner, 3600000, 1, new StormforgedSecondThunder(owner, spell, Line))));
            owner.TakeDamage(null, eDamageType.Energy, 20, 0);
            Assert.That(owner.Health, Is.EqualTo(80));
            Assert.That(effect.Bursts, Is.Zero);
            var unprotected = NewActor();
            unprotected.TakeDamage(null, eDamageType.Energy, 100, 0);
            Assert.That(unprotected.Deaths, Is.EqualTo(1));
        }

        [Test]
        public void StormguardRespondsOnlyToBlockedMeleeAndUnsubscribesWhenCancelled()
        {
            var owner = NewActor(); var attacker = NewActor();
            var spell = MakeSpell(62201, "StormforgedStormguard");
            var effect = Start(new Guard(new(owner, 3600000, 1, new StormforgedStormguard(owner, spell, Line))));
            var attack = new AttackData { Attacker = attacker, Target = owner, AttackType = AttackData.eAttackType.MeleeOneHand, AttackResult = eAttackResult.Blocked };
            GameEventMgr.Notify(GameLivingEvent.AttackedByEnemy, owner, new AttackedByEnemyEventArgs(attack));
            Assert.That(effect.Counters, Is.EqualTo(1));
            attack.AttackResult = eAttackResult.Parried;
            GameEventMgr.Notify(GameLivingEvent.AttackedByEnemy, owner, new AttackedByEnemyEventArgs(attack));
            attack.AttackResult = eAttackResult.Blocked; attack.AttackType = AttackData.eAttackType.Spell;
            GameEventMgr.Notify(GameLivingEvent.AttackedByEnemy, owner, new AttackedByEnemyEventArgs(attack));
            Assert.That(effect.Counters, Is.EqualTo(1));
            effect.End(); owner.effectListComponent.BeginTick();
            attack.AttackType = AttackData.eAttackType.MeleeOneHand;
            GameEventMgr.Notify(GameLivingEvent.AttackedByEnemy, owner, new AttackedByEnemyEventArgs(attack));
            Assert.That(effect.Counters, Is.EqualTo(1));
        }
    }
}
