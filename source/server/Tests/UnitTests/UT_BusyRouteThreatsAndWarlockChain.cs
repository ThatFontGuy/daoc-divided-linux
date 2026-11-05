using System.Collections.Generic;
using System.Numerics;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>
    /// Overnight run 2026-11-02: bots walked past hard monsters busy killing other bots, and Warlock bots tried the last
    /// step of their Witchcraft chain without the first two.
    /// </summary>
    [TestFixture]
    public class UT_BusyRouteThreatsAndWarlockChain
    {
        [Test]
        public void OnlyHardBusyMonstersAreWatched()
        {
            Assert.Multiple(() =>
            {
                Assert.That(AutonomousRouteThreatPolicy.WatchesBusyMonster(ConColor.ORANGE), Is.True);
                Assert.That(AutonomousRouteThreatPolicy.WatchesBusyMonster(ConColor.RED), Is.True);
                Assert.That(AutonomousRouteThreatPolicy.WatchesBusyMonster(ConColor.PURPLE), Is.True);
                Assert.That(AutonomousRouteThreatPolicy.WatchesBusyMonster(ConColor.YELLOW), Is.False);
                Assert.That(AutonomousRouteThreatPolicy.WatchesBusyMonster(ConColor.GREEN), Is.False);
            });
        }

        [Test]
        public void ABusyMonsterIsNeverPulled()
        {
            Assert.Multiple(() =>
            {
                Assert.That(AutonomousRouteThreatPolicy.ForBusyMonster(RouteThreatAction.Pull, canDetour: true, hasCamp: true),
                    Is.EqualTo(RouteThreatAction.Detour));
                Assert.That(AutonomousRouteThreatPolicy.ForBusyMonster(RouteThreatAction.Pull, canDetour: false, hasCamp: true),
                    Is.EqualTo(RouteThreatAction.Retarget));
                Assert.That(AutonomousRouteThreatPolicy.ForBusyMonster(RouteThreatAction.Pull, canDetour: false, hasCamp: false),
                    Is.EqualTo(RouteThreatAction.Ignore), "no camp to give up: walk on as before");
                Assert.That(AutonomousRouteThreatPolicy.ForBusyMonster(RouteThreatAction.Retarget, canDetour: true, hasCamp: true),
                    Is.EqualTo(RouteThreatAction.Retarget));
                Assert.That(AutonomousRouteThreatPolicy.ForBusyMonster(RouteThreatAction.Detour, canDetour: true, hasCamp: true),
                    Is.EqualTo(RouteThreatAction.Detour));
            });
        }

        private static Spell Chain(int id, int level, int stage, double cast) =>
            new(new DbSpell { SpellID = id, Name = "chain", Type = "WarlockChainDot", Target = "Enemy",
                CastTime = cast, Damage = 40, Duration = 25, Range = 1500 }, level)
            { CustomParamsDictionary = new Dictionary<string, object> { ["WarlockStage"] = stage } };

        [Test]
        public void ChainStepsOnlyGiveWayToAHigherSpellOfTheSameStep()
        {
            Spell weakDread = Chain(66200, 8, 1, 0);
            Spell lesserDread = Chain(66202, 32, 1, 0);
            Spell minorAnguish = Chain(66211, 24, 2, 3);
            Spell lesserAnguish = Chain(66212, 34, 2, 3);
            Spell lesserAgony = Chain(66221, 37, 3, 2.5);
            Spell[] known = { weakDread, lesserDread, minorAnguish, lesserAnguish, lesserAgony };
            Assert.Multiple(() =>
            {
                Assert.That(BotBrain.IsOutclassedDamageSpell(lesserAnguish, known, 37), Is.False, "Agony needs it, so Agony never replaces it");
                Assert.That(BotBrain.IsOutclassedDamageSpell(lesserDread, known, 37), Is.False);
                Assert.That(BotBrain.IsOutclassedDamageSpell(lesserAgony, known, 37), Is.False);
                Assert.That(BotBrain.IsOutclassedDamageSpell(minorAnguish, known, 37), Is.True, "a higher Anguish replaces it");
                Assert.That(BotBrain.IsOutclassedDamageSpell(weakDread, known, 37), Is.True, "a higher Dread replaces it");
                Assert.That(BotBrain.IsOutclassedDamageSpell(weakDread, new[] { weakDread, lesserAgony }, 37), Is.False,
                    "the only Dread stays, however low");
            });
        }

        [Test]
        public void ACampBeyondAGivenUpPackIsSkipped()
        {
            AutonomousRouteBlockMemory.Clear();
            const long owner = 4242;
            AutonomousRouteBlockMemory.Note(owner, 1, new Vector2(504_000, 455_000), 500, now: 0);
            Vector2 party = new(504_000, 458_000);
            Assert.Multiple(() =>
            {
                Assert.That(AutonomousRouteBlockMemory.Crosses(owner, 1, party, new(504_600, 444_200), 60_000), Is.True,
                    "the next spawn of the same camp, past the goblins");
                Assert.That(AutonomousRouteBlockMemory.Crosses(owner, 1, party, new(512_000, 470_000), 60_000), Is.False,
                    "a camp the other way");
                Assert.That(AutonomousRouteBlockMemory.Crosses(owner, 2, party, new(504_600, 444_200), 60_000), Is.False,
                    "another region");
                Assert.That(AutonomousRouteBlockMemory.Crosses(owner + 1, 1, party, new(504_600, 444_200), 60_000), Is.False,
                    "another bot or party");
                Assert.That(AutonomousRouteBlockMemory.Crosses(owner, 1, party, new(504_600, 444_200),
                    AutonomousRouteBlockMemory.CooldownMilliseconds + 1), Is.False, "forgotten after the cooldown");
                Assert.That(AutonomousRouteBlockMemory.Crosses(owner, 1, party, new(504_600, 455_400), 60_000), Is.True,
                    "the small radius is raised to the minimum reach");
            });
            AutonomousRouteBlockMemory.Clear();
        }

        [Test]
        public void DreadIsAnInstantAttack() =>
            Assert.That(BotBrain.IsInstantAttackType(eSpellType.WarlockChainDot), Is.True);
    }
}
