using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.ServerProperties;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_SpellCastPushback
    {
        private bool _enabled;
        private int _hit, _cap;
        private long _time;
        private GameLiving _caster;
        private GameServer _previous;
        private PetTestLanguageScope _language;
        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
            protected override DOL.GS.ServerRules.IServerRules ServerRulesImpl => new DOL.GS.ServerRules.NormalServerRules();
        }

        private sealed class Cast : SpellHandler
        {
            public bool Finished;
            public Cast(GameLiving caster, Spell spell) : base(caster, spell, new SpellLine("pushback", "pushback", "", true)) { }
            public override void FinishSpellCast(GameLiving target) { Finished = true; }
        }

        [SetUp]
        public void Setup()
        {
            _previous = GameServer.Instance;
            _language = new PetTestLanguageScope();
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
            _enabled = Properties.SPELL_DAMAGE_PUSHBACK;
            _hit = Properties.SPELL_DAMAGE_PUSHBACK_PER_HIT;
            _cap = Properties.SPELL_DAMAGE_PUSHBACK_CAP;
            _time = GameLoop.GameLoopTime;
            Properties.SPELL_DAMAGE_PUSHBACK = true;
            Properties.SPELL_DAMAGE_PUSHBACK_PER_HIT = 500;
            Properties.SPELL_DAMAGE_PUSHBACK_CAP = 1000;
            Now(10000);
        }

        [TearDown]
        public void Cleanup()
        {
            if (_caster?.effectListComponent != null) ServiceObjectStore.Remove(_caster.effectListComponent);
            Properties.SPELL_DAMAGE_PUSHBACK = _enabled;
            Properties.SPELL_DAMAGE_PUSHBACK_PER_HIT = _hit;
            Properties.SPELL_DAMAGE_PUSHBACK_CAP = _cap;
            Now(_time);
            GameServer.LoadTestDouble(_previous);
            _language.Dispose();
        }

        private static void Now(long tick) => typeof(GameLoop).GetProperty(nameof(GameLoop.GameLoopTime)).SetValue(null, tick);
        private Cast Begin(Type type = null, bool uninterruptible = false, int castTime = 3)
        {
            _caster = (GameLiving)RuntimeHelpers.GetUninitializedObject(type ?? typeof(GameBot));
            _caster.effectListComponent = EffectListComponent.Create(_caster);
            _caster.castingComponent = CastingComponent.Create(_caster);
            var cast = new Cast(_caster, new Spell(new DbSpell { SpellID = 900001, Type = "DirectDamage", Target = "Enemy", CastTime = castTime, Uninterruptible = uninterruptible }, 1));
            typeof(SpellHandler).GetProperty(nameof(SpellHandler.CastState)).SetValue(cast, eCastState.Casting);
            typeof(SpellHandler).GetField("_castStartTick", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(cast, 10000L);
            typeof(CastingComponent).GetProperty(nameof(CastingComponent.SpellHandler)).SetValue(_caster.castingComponent, cast);
            cast.SendCastAnimation(30);
            return cast;
        }

        [TestCase(typeof(GamePlayer))]
        [TestCase(typeof(GameBot))]
        public void DamageDelaysAnActiveCastAndDoesNotCreateLockout(Type type)
        {
            Cast cast = Begin(type);
            Now(11000);
            _caster.StartDamageInterruptTimer(3000, new AttackData { Attacker = (GameNPC)RuntimeHelpers.GetUninitializedObject(typeof(GameNPC)), Damage = 10, AttackResult = eAttackResult.HitUnstyled });
            Assert.That(cast.DamagePushbackApplied, Is.EqualTo(500));
            Assert.That(cast.IsCastEndingSoon(0), Is.False);
            Assert.That(_caster.IsBeingInterruptedByOther, Is.False);
            Assert.That(_caster.IsBeingInterrupted, Is.False, "BotBrain's ordinary casting/healing gates must stay open");
            Now(13000);
            Assert.That(cast.IsCastEndingSoon(0), Is.False);
            Now(13500);
            Assert.That(cast.IsCastEndingSoon(0), Is.True);
        }

        [Test]
        public void ManyHitsAreCappedAndNextCastHasAFreshBudget()
        {
            Cast cast = Begin();
            for (int i = 0; i < 20; i++) cast.ApplyDamagePushback();
            Assert.That(cast.DamagePushbackApplied, Is.EqualTo(1000));
            Now(14000);
            Assert.That(cast.IsCastEndingSoon(0), Is.True);
            Assert.That(new Cast(_caster, cast.Spell).DamagePushbackApplied, Is.Zero);
        }

        [Test]
        public void ZeroDamageAndSelfDamageDoNotPushBack()
        {
            Cast cast = Begin();
            _caster.StartDamageInterruptTimer(3000, new AttackData { Attacker = (GameNPC)RuntimeHelpers.GetUninitializedObject(typeof(GameNPC)), Damage = 0 });
            _caster.StartDamageInterruptTimer(3000, new AttackData { Attacker = _caster, Damage = 10 });
            _caster.StartDamageInterruptTimer(3000, new AttackData { Attacker = (GameNPC)RuntimeHelpers.GetUninitializedObject(typeof(GameNPC)), Damage = 10, AttackResult = eAttackResult.Missed });
            Assert.That(cast.DamagePushbackApplied, Is.Zero);
        }

        [Test]
        public void UninterruptibleAndInstantSpellsAreProtected()
        {
            Cast cast = Begin(uninterruptible: true);
            cast.ApplyDamagePushback();
            Assert.That(cast.DamagePushbackApplied, Is.Zero);
            cast = new Cast(_caster, new Spell(new DbSpell { Type = "DirectDamage", Target = "Enemy", CastTime = 0 }, 1));
            typeof(SpellHandler).GetProperty(nameof(SpellHandler.CastState)).SetValue(cast, eCastState.Casting);
            cast.ApplyDamagePushback();
            Assert.That(cast.DamagePushbackApplied, Is.Zero);
        }

        [Test]
        public void MonstersAndDisabledSettingKeepLegacyPolicy()
        {
            Assert.That(SpellCastPushback.AppliesTo((GameNPC)RuntimeHelpers.GetUninitializedObject(typeof(GameNPC))), Is.False);
            Begin();
            Properties.SPELL_DAMAGE_PUSHBACK = false;
            Assert.That(SpellCastPushback.AppliesTo(_caster), Is.False);
        }

        [Test]
        public void RecentDamageDoesNotForceGamebotToCancelItsCastAndMelee()
        {
            Begin();
            Assert.That(SpellCastPushback.RequiresMeleeFallback(_caster, false, true), Is.False);
            Assert.That(SpellCastPushback.RequiresMeleeFallback(_caster, true, true), Is.True,
                "An explicit interrupt still permits the old fallback");
            Properties.SPELL_DAMAGE_PUSHBACK = false;
            Assert.That(SpellCastPushback.RequiresMeleeFallback(_caster, false, true), Is.True);
        }

        [Test]
        public void SimultaneousHitsCannotExceedBudget()
        {
            Cast cast = Begin();
            System.Threading.Tasks.Parallel.For(0, 100, _ => cast.ApplyDamagePushback());
            Assert.That(cast.DamagePushbackApplied, Is.EqualTo(1000));
            Now(14000);
            Assert.That(cast.IsCastEndingSoon(0), Is.True);
        }

        [Test]
        public void QuickcastIsNotDelayed()
        {
            Cast cast = Begin(typeof(GamePlayer));
            typeof(SpellHandler).GetField("_quickcast", BindingFlags.Instance | BindingFlags.NonPublic)
                .SetValue(cast, RuntimeHelpers.GetUninitializedObject(typeof(QuickCastECSGameEffect)));
            cast.ApplyDamagePushback();
            Assert.That(cast.DamagePushbackApplied, Is.Zero);
        }

        [Test]
        public void CompletedCastsAndFocusChannelsCannotBeExtended()
        {
            Cast cast = Begin();
            Now(13000);
            cast.ApplyDamagePushback();
            Assert.That(cast.DamagePushbackApplied, Is.Zero);
            Now(11000);
            typeof(SpellHandler).GetProperty(nameof(SpellHandler.CastState)).SetValue(cast, eCastState.Focusing);
            cast.ApplyDamagePushback();
            Assert.That(cast.DamagePushbackApplied, Is.Zero);
        }

        [Test]
        public void CustomCapAllowsPartialFinalPushAndClampsNegativeSettings()
        {
            Cast cast = Begin();
            Properties.SPELL_DAMAGE_PUSHBACK_CAP = 750;
            cast.ApplyDamagePushback(); cast.ApplyDamagePushback();
            Assert.That(cast.DamagePushbackApplied, Is.EqualTo(750));
            Properties.SPELL_DAMAGE_PUSHBACK_PER_HIT = -1;
            Assert.That(SpellCastPushback.DelayForHit(0), Is.Zero);
            Properties.SPELL_DAMAGE_PUSHBACK_CAP = -1;
            Assert.That(SpellCastPushback.DelayForHit(0), Is.Zero);
        }

        [Test]
        public void DamageBeforeTheNextCastDoesNotCloseBotCastingAndHealingGates()
        {
            Begin();
            typeof(CastingComponent).GetProperty(nameof(CastingComponent.SpellHandler)).SetValue(_caster.castingComponent, null);
            _caster.StartDamageInterruptTimer(3000, new AttackData { Attacker = (GameNPC)RuntimeHelpers.GetUninitializedObject(typeof(GameNPC)), Damage = 10, AttackResult = eAttackResult.HitStyle });
            Assert.That(_caster.IsBeingInterrupted, Is.False);
            Assert.That(_caster.IsBeingInterruptedByOther, Is.False);
            _caster.StartInterruptTimer(3000, AttackData.eAttackType.MeleeOneHand, _caster);
            Assert.That(_caster.IsBeingSelfInterrupted, Is.True, "The existing own-swing lockout remains separate");
        }
    }
}
