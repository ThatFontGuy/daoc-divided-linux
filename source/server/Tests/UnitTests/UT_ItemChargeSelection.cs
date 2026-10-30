using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using DOL.Logging;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture, NonParallelizable]
public class UT_ItemChargeSelection
{
    private const int PrimaryId = 1900000001;
    private const int SecondaryId = 1900000002;
    private sealed class Server : GameServer
    {
        protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
    }
    private GameServer _previousServer;
    [SetUp]
    public void SetUp()
    {
        _previousServer = GameServer.Instance;
        GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
    }
    [TearDown]
    public void TearDown() => GameServer.LoadTestDouble(_previousServer);
    private sealed class Index : SkillBase
    {
        public static Dictionary<int, Spell> Spells => m_spellIndex;
    }
    private sealed class Player : GamePlayer
    {
        private Player() : base(null, null) { }
        public override byte Level { get => 50; set { } }
        public override bool IsOnHorse { get => false; set { } }
        public override GameObject TargetObject { get => null; set { } }
        public override void Stealth(bool enabled) { }
        public void UseCharge(DbInventoryItem item, int type) => UseItemCharge(item, type);
    }
    private sealed class Handler : SpellHandler
    {
        private readonly bool _accepted;
        public Handler(GameLiving caster, Spell spell, SpellLine line, bool accepted) : base(caster, spell, line)
        {
            _accepted = accepted;
            // Keep the test on charge selection; no region timer or server is started.
            m_startReuseTimer = false;
        }
        public override bool CheckBeginCast(GameLiving target) => true;
        public override bool StartSpell(GameLiving target, DbInventoryItem item) => _accepted;
    }

    [TestCase(1, 5, 7, true, 2, 4)]
    [TestCase(2, 5, 7, true, 3, 3)]
    [TestCase(2, 0, 7, true, 3, 3)]
    [TestCase(2, 5, 0, true, 3, 4)]
    [TestCase(1, 0, 7, true, 3, 4)]
    [TestCase(1, 5, 7, false, 3, 4)]
    [TestCase(2, 5, 7, false, 3, 4)]
    public void SuccessfulUseConsumesOnlySelectedFinitePool(int type, int max1, int max2, bool accepted, int expected1, int expected2)
    {
        LoggerManager.InitializeWithExplicitLibrary(null, LogLibrary.None);
        using var language = new PetTestLanguageScope();
        var cache = (ConcurrentDictionary<eSpellType, Func<GameLiving, Spell, SpellLine, ISpellHandler>>)
            typeof(ScriptMgr).GetField("_spellHandlerConstructorCache", BindingFlags.Static | BindingFlags.NonPublic)!.GetValue(null)!;
        cache.TryGetValue(eSpellType.DirectDamage, out var previous);
        Index.Spells.TryGetValue(PrimaryId, out var oldPrimary);
        Index.Spells.TryGetValue(SecondaryId, out var oldSecondary);
        int selected = 0;
        try
        {
            Index.Spells[PrimaryId] = new Spell(new DbSpell { SpellID = PrimaryId, Type = "DirectDamage", Target = "Self" }, 1);
            Index.Spells[SecondaryId] = new Spell(new DbSpell { SpellID = SecondaryId, Type = "DirectDamage", Target = "Self" }, 1);
            cache[eSpellType.DirectDamage] = (caster, spell, line) =>
            {
                selected = spell.ID;
                return new Handler(caster, spell, line, accepted);
            };
            var item = new GameInventoryItem(new DbItemTemplate
            {
                Id_nb = "unit-test-two-charge-pools", Level = 1,
                SpellID = PrimaryId, SpellID1 = SecondaryId, MaxCharges = max1, MaxCharges1 = max2
            }) { Charges = 3, Charges1 = 4 };
            var player = (Player)RuntimeHelpers.GetUninitializedObject(typeof(Player));
            player.UseCharge(item, type);
            Assert.Multiple(() =>
            {
                Assert.That(selected, Is.EqualTo(type == 1 ? PrimaryId : SecondaryId));
                Assert.That(item.Charges, Is.EqualTo(expected1));
                Assert.That(item.Charges1, Is.EqualTo(expected2));
            });
        }
        finally
        {
            if (previous != null) cache[eSpellType.DirectDamage] = previous;
            else cache.TryRemove(eSpellType.DirectDamage, out _);
            if (oldPrimary != null) Index.Spells[PrimaryId] = oldPrimary;
            else Index.Spells.Remove(PrimaryId);
            if (oldSecondary != null) Index.Spells[SecondaryId] = oldSecondary;
            else Index.Spells.Remove(SecondaryId);
        }
    }
}
