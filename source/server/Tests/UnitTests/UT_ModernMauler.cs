using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.PlayerClass;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public sealed class UT_ModernMauler
    {
        private GameServer _previous;
        private sealed class Server : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
        }
        private sealed class Actor : GameNPC
        {
            public override int MaxHealth => 1000;
            public override int MaxMana => 1000;
            public override int GetModified(eProperty property) => 0;
        }
        [SetUp]
        public void Setup()
        {
            _previous = GameServer.Instance;
            GameServer.LoadTestDouble((Server)RuntimeHelpers.GetUninitializedObject(typeof(Server)));
        }
        [TearDown]
        public void Cleanup() => GameServer.LoadTestDouble(_previous);

        [TestCase(59, false)] [TestCase(60, true)] [TestCase(61, true)] [TestCase(62, true)] [TestCase(63, false)] [TestCase(64, false)] [TestCase(65, false)]
        public void NativeClassesDoNotOverlapCustomClasses(int id, bool expected) => Assert.That(ModernMauler.IsMauler(id), Is.EqualTo(expected));

        [TestCase(35, 35, true, true)] [TestCase(35, 34, true, false)] [TestCase(35, 50, false, false)]
        [TestCase(0, 0, true, true)] [TestCase(0, 0, false, false)] [TestCase(-1, 0, false, true)]
        public void GiftsRequireTrainedStaffAndEquippedWeaponExceptExplicitExemptions(int required, int trained, bool equipped, bool expected) =>
            Assert.That(ModernMauler.MeetsStaffRequirement(required, trained, equipped), Is.EqualTo(expected));

        // Bots choose a gift only when it can be cast: a fist-wrap Mauler chose its 1,500-range gift on every think, was
        // refused, and stood out of reach of its target (2026-10-28 run: 535,000 refusals, 7,400 pull timeouts).
        [Test]
        public void OnlyAMaulerCanBeReadyForAGift()
        {
            var gift = new Spell(new DbSpell { SpellID = 67410, Type = "MaulerGift", Target = "Enemy", Range = 1500 }, 5);
            Assert.That(ModernMauler.GiftReady(new Actor(), gift), Is.False);
        }

        private static Tuple<SpellLine, int> Line(string key, int classHint) => new(new SpellLine(key, key, "Aura Manipulation", false), classHint);

        // 2026-11-01 overnight run: none of the 164 Mauler bots knew an aura, so their gifts were skipped 6 million times,
        // and they also lacked Strength of the Forge and every Discipline of Laresh rank above 12%.
        [TestCase(60, "Mauler Albion Gifts")] [TestCase(61, "Mauler Midgard Gifts")] [TestCase(62, "Mauler Hibernia Gifts")]
        public void RealmGiftLinesAreAddedToAuraManipulation(int classId, string gifts)
        {
            var lines = new[] { Line("Aura Manipulation", 0), Line("Mauler Albion Gifts", 60), Line("Mauler Midgard Gifts", 61), Line("Mauler Hibernia Gifts", 62) };
            Assert.That(Specialization.SpecLinesForClass(lines, classId).Select(line => line.Item1.KeyName), Is.EqualTo(new[] { "Aura Manipulation", gifts }));
        }

        [Test]
        public void OtherClassLinesStillReplaceTheNeutralLine()
        {
            var lines = new[] { Line("Mundane Poisons", 0), Line("Infiltrator Envenom", 9), Line("Shadowblade Envenom", 23) };
            Assert.That(Specialization.SpecLinesForClass(lines, 9).Select(line => line.Item1.KeyName), Is.EqualTo(new[] { "Infiltrator Envenom" }));
            Assert.That(Specialization.SpecLinesForClass(lines, 1).Select(line => line.Item1.KeyName), Is.EqualTo(new[] { "Mundane Poisons" }));
        }

        private static Spell Kit(string type, int timerGroup = 0, double value = 0, bool focus = false) =>
            new(new DbSpell { SpellID = 67900, Type = type, Target = "Enemy", Value = value, SharedTimerGroup = timerGroup, IsFocus = focus }, 50);

        // 39% of Mauler bot casts did damage in the overnight run. Taps and snares cost swings and did nothing for the fight.
        [TestCase("SpeedDecrease", true, 100, false)] [TestCase("SpeedDecrease", false, 100, true)]
        [TestCase("MaulerEnduranceTap", true, 100, false)] [TestCase("MaulerEnduranceTap", true, 29, true)] [TestCase("MaulerEnduranceTap", true, 30, false)]
        [TestCase("DirectDamage", true, 100, true)] [TestCase("PowerDrain", true, 100, true)] [TestCase("CombatSpeedDebuff", true, 100, true)]
        public void BotsSwingInsteadOfCastingWhatDoesNotHelp(string type, bool inReach, int endurance, bool expected) =>
            Assert.That(MaulerBotCombatPolicy.AllowsCast(Kit(type), inReach, endurance), Is.EqualTo(expected));

        [TestCase(false)] [TestCase(true)]
        public void BotsNeverHoldAFocusSnareOrRootWithPerizor(bool inReach)
        {
            Assert.That(MaulerBotCombatPolicy.AllowsCast(Kit("SpeedDecrease", focus: true), inReach, 100), Is.False);
            Assert.That(MaulerBotCombatPolicy.AllowsCast(Kit("MaulerGift", 67320), inReach, 100), Is.False);
            Assert.That(MaulerBotCombatPolicy.AllowsCast(Kit("MaulerGift", 0), inReach, 100), Is.True, "realm gift");
        }

        [Test]
        public void TheNethuniGiftIsABotCombatHealAndOtherGiftsAreNot()
        {
            Assert.That(BotClassKitPolicy.Handles(Kit("MaulerGift", 67300)), Is.True);
            Assert.That(BotClassKitPolicy.IsCombatSupport(Kit("MaulerGift", 67300)), Is.True);
            foreach (int family in new[] { 0, 67310, 67320, 67330 })
            {
                Assert.That(BotClassKitPolicy.Handles(Kit("MaulerGift", family)), Is.False);
                Assert.That(BotClassKitPolicy.IsCombatSupport(Kit("MaulerGift", family)), Is.False);
            }
        }

        [TestCase(150, 40, 40)] [TestCase(50, 100, 50)] [TestCase(50, 0, 0)] [TestCase(-1, 100, 0)]
        public void TapsCannotCreatePowerOrEnduranceBeyondTargetsResources(int requested, int available, int expected) => Assert.That(ModernMauler.BoundedTap(requested, available), Is.EqualTo(expected));

        [TestCase(100, 1000, 200, 20)] [TestCase(0, 1000, 200, 0)] [TestCase(-1, 1000, 200, 0)]
        [TestCase(100000, 1000, 200, 200)] [TestCase(100, 0, 200, 0)]
        public void IncomingDamagePowerIsBoundedAndUsesHealthFraction(int damage, int hp, int power, int expected) =>
            Assert.That(ModernMauler.PowerFromDamage(damage, hp, power), Is.EqualTo(expected));

        [Test]
        public void AllThreeCreationGatesAndModernSpecMultiplierAgree()
        {
            bool old = DOL.GS.ServerProperties.Properties.ENABLE_MAULER_TEST;
            try
            {
                var careers = new CharacterClassBase[] { new ClassMaulerAlb(), new ClassMaulerMid(), new ClassMaulerHib() };
                foreach (var career in careers)
                {
                    DOL.GS.ServerProperties.Properties.ENABLE_MAULER_TEST = false;
                    Assert.That(career.EligibleRaces, Is.Empty);
                    DOL.GS.ServerProperties.Properties.ENABLE_MAULER_TEST = true;
                    Assert.That(career.EligibleRaces.Count, Is.GreaterThanOrEqualTo(3));
                    Assert.That(career.CanUseLefthandedWeapon, Is.True);
                    Assert.That(career.SpecPointsMultiplier, Is.EqualTo(18));
                }
            }
            finally { DOL.GS.ServerProperties.Properties.ENABLE_MAULER_TEST = old; }
        }

        [TestCase(10, eProperty.WeaponSkill)] [TestCase(11, eProperty.EvadeChance)] [TestCase(12, eProperty.ParryChance)]
        [TestCase(13, eProperty.MeleeDamage)] [TestCase(14, eProperty.FumbleChance)] [TestCase(15, eProperty.CastingSpeed)]
        public void EachBuffAndDebuffAppliesAndRemovesItsOwnProperty(int kind, eProperty property)
        {
            var owner = new Actor();
            var spell = new Spell(new DbSpell { SpellID = 67500, Type = "MaulerStat", Target = kind >= 14 ? "Enemy" : "Self", Value = 20 }, 50);
            spell.CustomParamsDictionary["MaulerStat"] = kind;
            var handler = new MaulerStatHandler(owner, spell, new SpellLine("mauler-test", "mauler-test", "Aura Manipulation", false));
            var effect = new MaulerStatEffect(new(owner, 30000, 1, handler));
            effect.OnStartEffect();
            Assert.That(kind >= 14 ? owner.DebuffCategory[property] : owner.BaseBuffBonusCategory[property], Is.EqualTo(20));
            // Evasion and weaponskill are separate properties even when both aura gifts coexist.
            if (kind == 10) Assert.That(owner.BaseBuffBonusCategory[eProperty.EvadeChance], Is.Zero);
            if (kind == 11) Assert.That(owner.BaseBuffBonusCategory[eProperty.WeaponSkill], Is.Zero);
            effect.OnStopEffect();
            Assert.That(kind >= 14 ? owner.DebuffCategory[property] : owner.BaseBuffBonusCategory[property], Is.Zero);
        }
    }
}
