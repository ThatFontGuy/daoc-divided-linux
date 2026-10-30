using System;
using System.Collections.Generic;
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
