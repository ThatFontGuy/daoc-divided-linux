using System;
using System.Collections.Generic;
using System.Reflection;
using System.Linq;
using DOL.AI.Brain;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.PlayerClass;
using DOL.GS.Realm;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_Stormforged
    {
        private GameServer _previous;
        private PetTestLanguageScope _language;
        private sealed class Actor : GameNPC
        {
            public override byte Level { get; set; }
            public override int MaxHealth => 100;
            public override bool IsAlive => Health > 0;
            public override int GetModified(eProperty property) => 100;
        }
        private sealed class PulseActor : GameNPC
        {
            public override int MaxHealth => 100;
            public override int GetModified(eProperty property) => 100;
            public Spell Requested;
            public int Requests, Cooldown;
            public override bool IsAlive => true;
            public override int GetSkillDisabledDuration(Skill skill) => Cooldown;
            public override bool CastSpell(Spell spell, SpellLine line, ISpellCastingAbilityHandler ability = null, bool checkLos = true)
            {
                Requested = spell;
                Requests++;
                return true;
            }
        }
        private sealed class PulseBrain : StormforgedBombBrain
        {
            public Spell Payload;
            public PulseBrain(GameLiving owner) : base(owner) { }
            protected override Spell StormPulse => Payload;
        }

        private sealed class EmptyServer : GameServer
        {
            protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
        }

        [SetUp]
        public void SetUp()
        {
            _previous = GameServer.Instance;
            GameServer.LoadTestDouble((EmptyServer)RuntimeHelpers.GetUninitializedObject(typeof(EmptyServer)));
            _language = new PetTestLanguageScope();
        }

        [TearDown]
        public void TearDown()
        {
            _language.Dispose();
            GameServer.LoadTestDouble(_previous);
        }

        [TestCase(61, 2, true, 64)]
        [TestCase(61, 2, false, 61)]
        [TestCase(21, 2, true, 21)]
        [TestCase(61, 1, true, 61)]
        [TestCase(62, 3, true, 62)]
        public void CreationMapsOnlyEnabledMidgardMauler(int selected, int realm, bool enabled, int expected)
        {
            Assert.That(StormforgedRules.CreationClass(selected, realm, enabled), Is.EqualTo(expected));
        }

        [TestCase(64, 2, 61)]
        [TestCase(21, 2, 21)]
        [TestCase(63, 3, 63)]
        [TestCase(64, 1, 64)]
        public void OverviewKeepsServerIdentitySeparate(int server, int realm, int client)
        {
            Assert.That(StormforgedRules.OverviewClass(server, realm), Is.EqualTo(client));
        }

        [Test]
        public void EveryMidgardRaceIsEligible()
        {
            var midgard = PlayerRace.AllRaces.Where(race => race.Realm == eRealm.Midgard).Select(race => race.ID);
            Assert.That(new ClassStormforged().EligibleRaces.Select(race => race.ID), Is.EquivalentTo(midgard));
        }

        [Test]
        public void PerTargetReturnsAddWithoutRequiringEnemyMana()
        {
            Assert.That(StormforgedRules.RestorePerHit(100, 75) + StormforgedRules.RestorePerHit(200, 75), Is.EqualTo(225));
            Assert.That(StormforgedRules.RestorePerHit(0, 75), Is.Zero);
            Assert.That(StormforgedRules.RestorePerHit(-100, 75), Is.Zero);
            Assert.That(StormforgedRules.RestorePerHit(int.MaxValue, 1000), Is.EqualTo(int.MaxValue));
        }

        [Test]
        public void SpellDelvesDescribeInstantAreaAndActualWardBonuses()
        {
            var owner = new Actor { Level = 40 };
            var line = new SpellLine("test", "test", "test", true);
            var instant = new Spell(new DbSpell { SpellID = 62002, TooltipId = 20602, Name = "Chain Lightning", Type = "StormforgedStrike", Target = "Enemy", Range = 0, Radius = 350, CastTime = 0 }, 1);
            Assert.That(instant.IsInstantCast, Is.True);
            Assert.That(instant.IsPBAoE, Is.True);
            Assert.That(SpellDelve.GetSpellString(new StormforgedStrike(owner, instant, line)), Does.Contain("instant"));
            var ward = new Spell(new DbSpell { SpellID = 62007, Type = "StormforgedWard", Target = "Self" }, 1);
            string text = new StormforgedWard(owner, ward, line).ShortDescription;
            Assert.That(text, Does.Contain("+50 base and +75"));
            Assert.That(text, Does.Contain("+80"));
            Assert.That(text, Does.Contain("+26%"));
        }

        private sealed class CancelLookup : PlayerEffectListComponent
        {
            public CancelLookup() : base(null) { }
            public void AddForTest(ECSGameEffect effect) => SetEffectIdToEffect(effect);
            public void RemoveForTest(ECSGameEffect effect) => RemoveEffectIdToEffect(effect);
        }

        [Test]
        public void CustomBuffCancellationUsesPrivateIdentityEvenWhenIconsAreShared()
        {
            var owner = new Actor { Level = 40 };
            var line = new SpellLine("test", "test", "test", true);
            var wardSpell = new Spell(new DbSpell { SpellID = 62007, TooltipId = 20607, Icon = 3531, Type = "StormforgedWard", Target = "Self", Duration = 3600 }, 1);
            var chantSpell = new Spell(new DbSpell { SpellID = 62005, TooltipId = 20605, Icon = 3531, Type = "StormforgedChant", Target = "Self", Duration = 3600 }, 1);
            var ward = new StormforgedWardEffect(new(owner, 3600000, 1, new StormforgedWard(owner, wardSpell, line)));
            var chant = new StormforgedChantEffect(new(owner, 3600000, 1, new StormforgedChant(owner, chantSpell, line)));
            var lookup = new CancelLookup();
            lookup.AddForTest(ward);
            lookup.AddForTest(chant);
            Assert.That(ward.HasPositiveEffect, Is.True);
            Assert.That(chant.HasPositiveEffect, Is.True);
            Assert.That(lookup.TryGetEffectFromEffectId(20607), Is.SameAs(ward));
            Assert.That(lookup.TryGetEffectFromEffectId(20605), Is.SameAs(chant));
            lookup.RemoveForTest(ward);
            Assert.That(lookup.TryGetEffectFromEffectId(20607), Is.Null);
            Assert.That(lookup.TryGetEffectFromEffectId(20605), Is.SameAs(chant));
            Assert.That(lookup.TryGetEffectFromEffectId(3531), Is.SameAs(chant));
            lookup.RemoveForTest(chant);
            Assert.That(lookup.TryGetEffectFromEffectId(20605), Is.Null);
        }

        [Test]
        public void StormsongDefersToStrongerWardDamageAddUntilItEnds()
        {
            var owner = new Actor { Level = 40, Health = 100 };
            var line = new SpellLine("test", "test", "test", true);
            var wardSpell = new Spell(new DbSpell { SpellID = 62135, Type = "DamageAdd", Target = "Realm", Duration = 3600, Damage = 17 }, 40);
            var songSpell = new Spell(new DbSpell { SpellID = 62126, Type = "DamageAdd", Target = "Realm", Duration = 9, Damage = 13 }, 40);
            var strongerSong = new Spell(new DbSpell { Type = "DamageAdd", Target = "Realm", Damage = 20 }, 50);
            var ward = new DamageAddECSEffect(new(owner, 3600000, 1, new DamageAddSpellHandler(owner, wardSpell, line)));
            var support = typeof(StormforgedChantEffect).Assembly.GetType("DOL.GS.StormforgedEffectSupport");
            var covers = support.GetMethod("CoversDamageAdd", BindingFlags.NonPublic | BindingFlags.Static);
            try
            {
                ward.Start();
                owner.effectListComponent.BeginTick();
                Assert.That(ward.IsActive, Is.True);
                Assert.That(covers.Invoke(null, new object[] { ward, songSpell }), Is.True);
                Assert.That(covers.Invoke(null, new object[] { ward, wardSpell }), Is.True);
                Assert.That(covers.Invoke(null, new object[] { ward, strongerSong }), Is.False);
                ward.End();
                Assert.That(covers.Invoke(null, new object[] { ward, songSpell }), Is.False);
                owner.effectListComponent.BeginTick();
                Assert.That(covers.Invoke(null, new object[] { ward, songSpell }), Is.False);
            }
            finally { ServiceObjectStore.Remove<ECSGameEffect>(ward); }
        }

        [TestCase(62000, "StormforgedStrike")]
        [TestCase(62001, "StormforgedStrike")]
        [TestCase(62002, "StormforgedStrike")]
        [TestCase(62003, "StormforgedAura")]
        [TestCase(62005, "StormforgedChant")]
        [TestCase(62006, "DamageAdd")]
        [TestCase(62007, "StormforgedWard")]
        [TestCase(62008, "DamageShield")]
        [TestCase(62009, "StormforgedRest")]
        [TestCase(62030, "StormforgedPet")]
        [TestCase(62052, "SummonAnimistFnF")]
        [TestCase(62156, "StormforgedStrike")]
        [TestCase(62220, "StrengthBuff")] [TestCase(62236, "MatterResistBuff")] [TestCase(62239, "Heal")]
        public void StormforgedSpellsAndInternalChildrenNeverChargeEndurance(int id, string type)
        {
            var spell = new Spell(new DbSpell { SpellID = id, Type = type, Target = "Self", Power = 5 }, 1);
            var handler = new SpellHandler(new Actor(), spell, new SpellLine("test", "test", "test", true));
            Assert.That(handler.CalculateEnduranceCost(), Is.Zero);
            Assert.That(handler.CostType, Is.EqualTo(SpellCostType.Power));
            Assert.That(spell.Power, Is.EqualTo(5));
        }

        [TestCase("StrengthBuff")] [TestCase("ConstitutionBuff")] [TestCase("DexterityBuff")]
        [TestCase("BaseArmorFactorBuff")] [TestCase("StrengthConstitutionBuff")] [TestCase("DexterityQuicknessBuff")]
        [TestCase("AcuityBuff")] [TestCase("CombatSpeedBuff")] [TestCase("PowerRegenBuff")]
        [TestCase("EnduranceRegenBuff")] [TestCase("HealthRegenBuff")] [TestCase("BodyResistBuff")]
        [TestCase("SpiritResistBuff")] [TestCase("EnergyResistBuff")] [TestCase("HeatResistBuff")]
        [TestCase("ColdResistBuff")] [TestCase("MatterResistBuff")]
        public void MenderBuffsHaveRealEffectCategories(string type)
        {
            var spell = new Spell(new DbSpell { SpellID = 62220, Type = type, Target = "Realm", Value = 24 }, 1);
            Assert.That(EffectHelper.GetEffectFromSpell(spell), Is.Not.EqualTo(eEffect.Unknown));
        }

        [TestCase(3508)] [TestCase(61999)] [TestCase(62240)]
        public void StockSpellsKeepTheirOriginalEnduranceCost(int id)
        {
            var spell = new Spell(new DbSpell { SpellID = id, Type = "DirectDamage", Target = "Enemy" }, 1);
            Assert.That(new SpellHandler(new Actor(), spell, null).CalculateEnduranceCost(), Is.EqualTo(5));
        }

        [TestCase(1, new[] { 1 })]
        [TestCase(5, new[] { 5 })]
        [TestCase(10, new[] { 10 })]
        [TestCase(50, new[] { 50 })]
        public void SpellListKeepsNewestLearnedRankWithoutChangingStockLines(int level, int[] expected)
        {
            var learned = new[] { 1, 5, 10, 15, 20, 30, 40, 50 }.Where(rank => rank <= level)
                .Select(rank => new Spell(new DbSpell { SpellID = 62000 + rank, Type = "StormforgedStrike", Target = "Enemy" }, rank)).Reverse().ToList();
            Assert.That(StormforgedRules.VisibleSpellRanks("Stormforged.Stormbolt", learned).Select(spell => spell.Level), Is.EqualTo(expected));
            Assert.That(StormforgedRules.VisibleSpellRanks("Stormcalling", learned).Count(), Is.EqualTo(learned.Count));
        }

        [Test]
        public void ClientSlotsAreUniqueAndFollowUnlockLevel()
        {
            Spell Rank(int id, int level) => new Spell(new DbSpell { SpellID = id, Type = "StormforgedStrike", Target = "Enemy" }, level);
            var slots = StormforgedRules.AssignClientSlots(new[]
            {
                ("Stormforged.B", (IEnumerable<Spell>)new[] { Rank(1, 1), Rank(2, 50) }),
                ("Stormforged.A", new[] { Rank(3, 1) }),
                ("Stormforged.Pet", new[] { Rank(4, 5) }),
                ("Stormforged.Late", new[] { Rank(5, 2) }),
            });
            // A and B both unlock at 1; Late (2) is pushed to 3. Every rank of a type shares its slot.
            Assert.That(slots[3], Is.EqualTo(1));
            Assert.That(slots[1], Is.EqualTo(2));
            Assert.That(slots[2], Is.EqualTo(2));
            Assert.That(slots[5], Is.EqualTo(3));
            Assert.That(slots[4], Is.EqualTo(5));
        }

        [Test]
        public void ClientViewMergesStormforgedLinesAndLeavesOtherLinesAlone()
        {
            var bolt = new Spell(new DbSpell { SpellID = 62001, Type = "StormforgedStrike", Target = "Enemy" }, 1);
            var clap = new Spell(new DbSpell { SpellID = 62002, Type = "StormforgedStrike", Target = "Enemy" }, 1);
            var boltLine = new SpellLine("Stormforged.Stormbolt", "Stormbolt", "StormforgedCareer", true);
            var clapLine = new SpellLine("Stormforged.Thunderclap", "Thunderclap", "StormforgedCareer", true);
            var other = new SpellLine("Mending", "Mending", "Mending", true);
            var lines = new List<(SpellLine, List<Skill>)> { (other, new List<Skill>()), (boltLine, new List<Skill> { bolt }), (clapLine, new List<Skill> { clap }) };

            var view = StormforgedRules.ClientSpellLines(lines);
            Assert.That(view.Select(line => line.Item1), Is.EqualTo(new[] { other, StormforgedRules.ClientLine }));
            Assert.That(view[1].Item2, Is.EquivalentTo(new Skill[] { bolt, clap }));
            Assert.That(StormforgedRules.ServerLine(lines, view[1].Item1, clap), Is.SameAs(clapLine));
            Assert.That(StormforgedRules.ServerLine(lines, other, bolt), Is.SameAs(other));

            var stock = new List<(SpellLine, List<Skill>)> { (other, new List<Skill>()) };
            Assert.That(StormforgedRules.ClientSpellLines(stock), Is.SameAs(stock));
        }

        [Test]
        public void StormBombPulseCastsIndependentlyAndHonorsItsOwnCooldownAndPassiveMode()
        {
            var owner = new Actor();
            var body = new PulseActor();
            var pulse = new Spell(new DbSpell { SpellID = 62157, Type = "DirectDamage", Target = "Enemy", Range = 0, Radius = 350, CastTime = 0, RecastDelay = 4 }, 50);
            var brain = new PulseBrain(owner) { Body = body, Payload = pulse };
            Assert.That(brain.TryCastStormPulse(), Is.True);
            Assert.That(body.Requested, Is.SameAs(pulse));
            body.Cooldown = 4000;
            Assert.That(brain.TryCastStormPulse(), Is.False);
            Assert.That(body.Requests, Is.EqualTo(1));
            body.Cooldown = 0;
            brain.AggressionState = eAggressionState.Passive;
            Assert.That(brain.TryCastStormPulse(), Is.False);
            Assert.That(body.Requests, Is.EqualTo(1));
        }

        [Test]
        public void OriginalThaneRemainsIndependent()
        {
            var thane = new ClassThane();
            var storm = new ClassStormforged();
            Assert.That(thane.ID, Is.EqualTo(21));
            Assert.That(storm.ID, Is.EqualTo(64));
            Assert.That(thane.SpecPointsMultiplier, Is.EqualTo(20));
            Assert.That(storm.ManaStat, Is.EqualTo(eStat.PIE));
        }

        [Test]
        public void WardAtFortyCapsAllEightStatBuffsAndReversesOnlyItsOwnBonuses()
        {
            var owner = new Actor { Level = 40 };
            owner.BaseBuffBonusCategory[eProperty.Strength] = 7;
            var spell = new Spell(new DbSpell { SpellID = 62007, Name = "Test ward", Type = "StormforgedWard", Target = "Self", Duration = 600, Value = 100 }, 40);
            var handler = new StormforgedWard(owner, spell, new SpellLine("test", "test", "test", true));
            var effect = new StormforgedWardEffect(new(owner, 600000, 1, handler));
            effect.OnStartEffect();
            foreach (eProperty property in new[] { eProperty.Strength, eProperty.Dexterity, eProperty.Constitution, eProperty.Quickness,
                eProperty.Intelligence, eProperty.Piety, eProperty.Empathy, eProperty.Charisma })
            {
                Assert.That(owner.BaseBuffBonusCategory[property], Is.EqualTo(property == eProperty.Strength ? 57 : 50));
                Assert.That(owner.SpecBuffBonusCategory[property], Is.EqualTo(75));
            }
            Assert.That(owner.SpecBuffBonusCategory[eProperty.ArmorFactor], Is.EqualTo(80));
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Resist_Energy], Is.EqualTo(26));
            effect.OnStopEffect();
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Strength], Is.EqualTo(7));
            Assert.That(owner.SpecBuffBonusCategory[eProperty.ArmorFactor], Is.Zero);
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Resist_Energy], Is.Zero);
        }

        [TestCase(1, 1, 1, 1)]
        [TestCase(5, 6, 9, 4)]
        [TestCase(20, 25, 37, 13)]
        [TestCase(40, 50, 75, 26)]
        public void EvenFirstWardRankScalesWithCharacterLevel(int level, int baseStats, int specStats, int resistance)
        {
            var owner = new Actor { Level = (byte)level };
            var spell = new Spell(new DbSpell { SpellID = 62007, Type = "StormforgedWard", Target = "Self", Duration = 3600, Value = 2.5 }, 1);
            var handler = new StormforgedWard(owner, spell, new SpellLine("test", "test", "test", true));
            var effect = new StormforgedWardEffect(new(owner, 3600000, 1, handler));
            effect.OnStartEffect();
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Strength], Is.EqualTo(baseStats));
            Assert.That(owner.SpecBuffBonusCategory[eProperty.Piety], Is.EqualTo(specStats));
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Resist_Energy], Is.EqualTo(resistance));
            effect.OnStopEffect();
            Assert.That(owner.BaseBuffBonusCategory[eProperty.Strength], Is.Zero);
        }

        [Test]
        public void SingerChantLastsUntilCanceledButGroupEffectsKeepTheirRangeTimeout()
        {
            var singer = new Actor();
            var member = new Actor();
            var spell = new Spell(new DbSpell { Type = "StormforgedChant", Target = "Self", Duration = 3600, Frequency = 40 }, 1);
            var handler = new StormforgedChant(singer, spell, new SpellLine("test", "test", "test", true));
            var root = new StormforgedChantEffect(new(singer, 3600000, 1, handler));
            var child = new StormforgedChantEffect(new(member, 8000, 1, handler));
            Assert.That(root.Duration, Is.Zero);
            Assert.That(root.ExpireTick, Is.EqualTo(long.MaxValue));
            Assert.That(child.Duration, Is.EqualTo(8000));
            Assert.That(child.ExpireTick, Is.LessThan(long.MaxValue));
        }

        [Test]
        public void MaintainedEffectsKeepStealthAndHaveIndependentEffectSlots()
        {
            var owner = new Actor();
            var line = new SpellLine("test", "test", "test", true);
            var effects = new System.Collections.Generic.HashSet<eEffect>();
            foreach (eSpellType type in new[] { eSpellType.StormforgedAura, eSpellType.StormforgedChant, eSpellType.StormforgedWard })
            {
                var spell = new Spell(new DbSpell { Type = type.ToString(), Target = "Self", Duration = 600 }, 1);
                effects.Add(EffectHelper.GetEffectFromSpell(spell));
                var handler = type switch
                {
                    eSpellType.StormforgedAura => (StormforgedMaintainedSpell)new StormforgedAura(owner, spell, line),
                    eSpellType.StormforgedChant => new StormforgedChant(owner, spell, line),
                    _ => new StormforgedWard(owner, spell, line)
                };
                Assert.That(handler.UnstealthCasterOnStart, Is.False);
                Assert.That(handler.UnstealthCasterOnFinish, Is.False);
            }
            Assert.That(effects, Has.Count.EqualTo(3));
            Assert.That(effects, Does.Not.Contain(eEffect.Unknown));
            Assert.That(effects, Does.Not.Contain(eEffect.MovementSpeedBuff));
        }
    }
}
