using System;
using System.Collections;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.Events;
using DOL.GS;
using DOL.GS.Effects;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests;

/// <summary>Events nothing raised and handlers the ECS rewrite stopped calling. See docs/DEAD-EVENTS.md.</summary>
[TestFixture, NonParallelizable]
public sealed class UT_DeadEventFixes
{
    private const BindingFlags Hidden = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;

    private EpicTestServerScope _server;

    [SetUp]
    public void SetUp() => _server = new EpicTestServerScope();

    [TearDown]
    public void TearDown() => _server.Dispose();

    private sealed class Mob : GameNPC
    {
        public int AttackedByEnemyCalls;
        public override bool IsAlive => true;
        public override string GetName(int article, bool firstLetterUppercase) => "mob";
        public override void OnAttackedByEnemy(AttackData ad) => AttackedByEnemyCalls++;
    }

    private static Mob NewMob()
    {
        var mob = (Mob) RuntimeHelpers.GetUninitializedObject(typeof(Mob));
        mob.ObjectState = GameObject.eObjectState.Active;
        mob.effectListComponent = EffectListComponent.Create(mob);
        typeof(GameLiving).GetField("<TempProperties>k__BackingField", Hidden).SetValue(mob, new PropertyCollection());
        typeof(GameLiving).GetField("<BaseBuffBonusCategory>k__BackingField", Hidden).SetValue(mob, new DOL.GS.PropertyCalc.PropertyIndexer());
        typeof(GameLiving).GetField("<AbilityBonus>k__BackingField", Hidden).SetValue(mob, new DOL.GS.PropertyCalc.PropertyIndexer());
        typeof(GameNPC).GetField("m_brains", Hidden).SetValue(mob, new ArrayList());
        mob.movementComponent = new NpcMovementComponent(mob);
        return mob;
    }

    private static int CountAttackFinished(GameLiving attacker, Action swing)
    {
        int count = 0;
        DOLEventHandler handler = (e, sender, args) => { if (sender == attacker && args is AttackFinishedEventArgs) count++; };
        GameEventMgr.AddHandler(attacker, GameLivingEvent.AttackFinished, handler);

        try
        {
            swing();
            return count;
        }
        finally
        {
            GameEventMgr.RemoveHandler(attacker, GameLivingEvent.AttackFinished, handler);
        }
    }

    [TestCase(eAttackResult.HitUnstyled, 1)]
    [TestCase(eAttackResult.HitStyle, 1)]
    [TestCase(eAttackResult.Missed, 1)]
    [TestCase(eAttackResult.Blocked, 1)]
    [TestCase(eAttackResult.Evaded, 1)]
    [TestCase(eAttackResult.Parried, 1)]
    [TestCase(eAttackResult.Fumbled, 1)]
    [TestCase(eAttackResult.OutOfRange, 0)]
    [TestCase(eAttackResult.TargetNotVisible, 0)]
    [TestCase(eAttackResult.TargetDead, 0)]
    [TestCase(eAttackResult.NotAllowed_ServerRules, 0)]
    [TestCase(eAttackResult.NoValidTarget, 0)]
    public void AttackFinishedIsRaisedOncePerResolvedSwing(eAttackResult result, int expected)
    {
        Mob attacker = NewMob();
        var ad = new AttackData { Attacker = attacker, AttackResult = result };
        Assert.That(CountAttackFinished(attacker, () => WeaponAction.NotifyAttackFinished(attacker, ad)), Is.EqualTo(expected));
    }

    [Test]
    public void TheRealSwingRaisesAttackFinishedAfterTheTargetHasDefended()
    {
        Mob attacker = NewMob();
        Mob target = NewMob();
        int defendedFirst = -1;
        var ad = new AttackData { Attacker = attacker, Target = target, AttackResult = eAttackResult.Missed };
        var action = (WeaponAction) RuntimeHelpers.GetUninitializedObject(typeof(WeaponAction));
        typeof(WeaponAction).GetField("_owner", Hidden).SetValue(action, attacker);
        MethodInfo makeAttack = typeof(WeaponAction).GetMethod("MakeAttack", Hidden, [typeof(AttackData)]);
        DOLEventHandler order = (e, sender, args) => defendedFirst = target.AttackedByEnemyCalls;
        GameEventMgr.AddHandler(attacker, GameLivingEvent.AttackFinished, order);

        try
        {
            Assert.That(CountAttackFinished(attacker, () => makeAttack.Invoke(action, [ad])), Is.EqualTo(1));
            Assert.That(defendedFirst, Is.EqualTo(1));
        }
        finally
        {
            GameEventMgr.RemoveHandler(attacker, GameLivingEvent.AttackFinished, order);
        }
    }

    private sealed class CountingBarrier : BladeBarrierEffect
    {
        public int Stops;

        public void Attach(GameLiving owner)
        {
            m_owner = owner;
            GameEventMgr.AddHandler(owner, GameLivingEvent.AttackFinished, new DOLEventHandler(attackEventHandler));
            GameEventMgr.AddHandler(owner, GameLivingEvent.AttackedByEnemy, new DOLEventHandler(TakeDamage));
        }

        public override void Stop()
        {
            Stops++;
            base.Stop();
        }
    }

    [Test]
    public void BladeBarrierBreaksOnAMissAndLeavesNoHandlersBehind()
    {
        Mob owner = NewMob();
        typeof(GameLiving).GetField("m_effects", Hidden).SetValue(owner, new GameEffectList(owner));
        var barrier = new CountingBarrier();
        barrier.Attach(owner);
        var ad = new AttackData { Attacker = owner, AttackResult = eAttackResult.Missed };

        WeaponAction.NotifyAttackFinished(owner, ad);
        Assert.That(barrier.Stops, Is.EqualTo(1));

        WeaponAction.NotifyAttackFinished(owner, ad);
        Assert.That(barrier.Stops, Is.EqualTo(1));
    }

    [TestCase(typeof(DisarmSpellHandler))]
    [TestCase(typeof(WaterBreathingSpellHandler))]
    [TestCase(typeof(VampiirStealthDetection))]
    [TestCase(typeof(VampiirMeleeResistance))]
    [TestCase(typeof(VampiirMagicResistance))]
    [TestCase(typeof(CCResistSpellHandler))]
    public void RevivedHandlersCreateTheirOwnEffect(Type handler)
    {
        MethodInfo create = handler.GetMethod(nameof(SpellHandler.CreateECSEffect));
        Assert.That(create.DeclaringType, Is.EqualTo(handler));
    }

    private static LegacySpellECSEffect Bridge(ISpellHandler handler, GameLiving owner) => new(new ECSGameEffectInitParams(owner, 60000, 1, handler));

    private static Spell SpellOf(eSpellType type, double value) =>
        new(new DbSpell { SpellID = 1, Type = type.ToString(), Target = "Self", Value = value, Duration = 60 }, 1);

    private static readonly SpellLine Line = new("test", "test", "test", false);

    [Test]
    public void VampiirMeleeResistanceAppliesOnStartAndClearsOnStop()
    {
        Mob owner = NewMob();
        LegacySpellECSEffect effect = Bridge(new VampiirMeleeResistance(owner, SpellOf(eSpellType.VampiirMeleeResistance, 14), Line), owner);

        effect.OnStartEffect();
        Assert.That(owner.BaseBuffBonusCategory[eProperty.Resist_Slash], Is.EqualTo(14));

        effect.OnStopEffect();
        Assert.That(owner.BaseBuffBonusCategory[eProperty.Resist_Slash], Is.Zero);
    }

    [Test]
    public void VampiirMagicResistanceWorksOnALivingThatIsNotAPlayer()
    {
        Mob owner = NewMob();
        LegacySpellECSEffect effect = Bridge(new VampiirMagicResistance(owner, SpellOf(eSpellType.VampiirMagicResistance, 26), Line), owner);

        effect.OnStartEffect();
        Assert.That(owner.AbilityBonus[eProperty.Resist_Heat], Is.EqualTo(26));

        effect.OnStopEffect();
        Assert.That(owner.AbilityBonus[eProperty.Resist_Heat], Is.Zero);
    }

    [Test]
    public void CCResistStaysBalancedAcrossARefresh()
    {
        Mob owner = NewMob();
        var handler = new CCResistSpellHandler(owner, SpellOf(eSpellType.CCResist, 20), Line);

        // A renewed effect is a new instance that is stopped without ever being started.
        LegacySpellECSEffect first = Bridge(handler, owner);
        LegacySpellECSEffect renewed = Bridge(handler, owner);
        first.OnStartEffect();
        Assert.That(owner.BaseBuffBonusCategory[eProperty.StunDurationReduction], Is.EqualTo(20));

        renewed.OnStopEffect();
        Assert.That(owner.BaseBuffBonusCategory[eProperty.StunDurationReduction], Is.Zero);
    }

    [Test]
    public void SelectingACharacterRaisesCharacterSelected()
    {
        var client = (GameClient) RuntimeHelpers.GetUninitializedObject(typeof(GameClient));
        var character = new DbCoreCharacter();
        typeof(GameClient).GetField("<Account>k__BackingField", Hidden).SetValue(client, new DbAccount { Characters = [character] });
        DbCoreCharacter seen = null;
        DOLEventHandler handler = (e, sender, args) => seen = ((CharacterEventArgs) args).Character;
        GameEventMgr.AddHandler(DatabaseEvent.CharacterSelected, handler);

        try
        {
            // There's no database here, so loading fails. The event comes first, so that it can repair the row before it's read.
            Assert.Catch(() => client.LoadPlayer(0).GetAwaiter().GetResult());
            Assert.That(seen, Is.SameAs(character));
        }
        finally
        {
            GameEventMgr.RemoveHandler(DatabaseEvent.CharacterSelected, handler);
        }
    }

    [Test]
    public void HereticPiercingMagicCountsAsPiercingMagic()
    {
        Mob owner = NewMob();
        ECSGameSpellEffect Effect(eSpellType type) => new(new ECSGameEffectInitParams(owner, 60000, 1, new SpellHandler(owner, SpellOf(type, 5), Line)));

        Assert.That(SpellHandler.IsPiercingMagic(Effect(eSpellType.HereticPiercingMagic)), Is.True);
        Assert.That(SpellHandler.IsPiercingMagic(Effect(eSpellType.PiercingMagic)), Is.True);
        Assert.That(SpellHandler.IsPiercingMagic(Effect(eSpellType.CCResist)), Is.False);
    }
}
