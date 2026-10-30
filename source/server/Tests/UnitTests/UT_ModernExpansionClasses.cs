using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using DOL.Database;
using DOL.GS;
using DOL.GS.PacketHandler.Client.v168;
using DOL.GS.PlayerClass;
using DOL.GS.PropertyCalc;
using DOL.GS.Realm;
using DOL.GS.RealmAbilities;
using DOL.GS.ServerProperties;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernExpansionClasses
    {
        private ModernRaTestScope _scope;
        private readonly List<GameNPC> _actors = new();
        private readonly SpellLine _line = new("test", "test", "test", true);
        private sealed class Actor : GameNPC
        {
            public Actor() { m_ObjectState = eObjectState.Active; }
            public override byte Level { get; set; } = 50;
            public override bool IsAlive => true;
            public override int MaxHealth => 1000;
        }
        private sealed class FlightProbe(GameLiving caster, Spell spell, SpellLine line) : VampiirFlightHandler(caster, spell, line)
        {
            public bool Blocked => BlockedInCombat;
        }
        [SetUp] public void Setup() => _scope = new ModernRaTestScope();
        [TearDown] public void Cleanup()
        {
            foreach (var actor in _actors)
            {
                foreach (var effect in actor.effectListComponent.GetEffects()) { effect.End(); ServiceObjectStore.Remove(effect); }
                actor.effectListComponent.BeginTick(); ServiceObjectStore.Remove(actor.effectListComponent);
            }
            _actors.Clear(); _scope.Dispose();
        }
        private Actor New() { var actor = new Actor(); _actors.Add(actor); return actor; }
        private static Spell Make(eSpellType type, double value, int duration = 0, string target = "Self") =>
            new(new DbSpell { Name = type.ToString(), Type = type.ToString(), Target = target, Value = value, Duration = duration }, 50);

        [Test]
        public void FlightSpellsWorkInCombat()
        {
            var flight = new FlightProbe(New(), Make(eSpellType.VampiirFlight, 176, 45), _line);
            Assert.That(flight.Blocked, Is.False, "1.123: Flight can be cast and kept in combat");
            Assert.That(EffectHelper.GetEffectFromSpell(flight.Spell), Is.EqualTo(eEffect.MovementSpeedBuff));
        }

        [Test]
        public void DeterminationReducesEveryCrowdControlDuration()
        {
            var handler = new VampiirDeterminationHandler(New(), Make(eSpellType.VampiirDetermination, 46, 180), _line);
            Assert.That(new[] { handler.Property1, handler.Property2, handler.Property3 }, Is.EqualTo(new[]
                { eProperty.MesmerizeDurationReduction, eProperty.StunDurationReduction, eProperty.SpeedDecreaseDurationReduction }));
            Assert.That(handler.ShortDescription, Does.Contain("46%"));
        }

        [Test]
        public void VampiricFeintRaisesSpellCritToItsValue()
        {
            var calculators = (IPropertyCalculator[])typeof(GameLiving).GetField("m_propertyCalc", BindingFlags.Static | BindingFlags.NonPublic).GetValue(null);
            var previous = calculators[(int)eProperty.CriticalSpellHitChance];
            calculators[(int)eProperty.CriticalSpellHitChance] = new CriticalSpellHitChanceCalculator();
            try
            {
                var vampiir = New();
                var handler = new VampiirFeintHandler(vampiir, Make(eSpellType.VampiirFeint, 25, 10), _line);
                var effect = ECSGameEffectFactory.Create(new(vampiir, 10000, 1, handler), static (in ECSGameEffectInitParams i) => new VampiirFeintEffect(i));
                vampiir.effectListComponent.BeginTick();
                Assert.That(vampiir.AbilityBonus[eProperty.CriticalSpellHitChance], Is.EqualTo(25), "An NPC has no base spell crit");
                effect.End(); vampiir.effectListComponent.BeginTick();
                Assert.That(vampiir.AbilityBonus[eProperty.CriticalSpellHitChance], Is.Zero);
            }
            finally { calculators[(int)eProperty.CriticalSpellHitChance] = previous; }
        }

        [Test]
        public void HellflowerRaisesHealthAndArmorByPercent()
        {
            var member = New();
            Assert.That(HereticHellflowerHandler.HealthBonus(member, 10), Is.EqualTo(100));
            Assert.That(HereticHellflowerHandler.ArmorBonus(member, 50), Is.EqualTo(member.Level), "No armor: level x 2 as the base");
            Assert.That(HereticHellflowerHandler.HealthBonus(member, 1), Is.EqualTo(10));
        }

        [Test]
        public void EthereaShriekScaresPetsWithoutGrantingImmunity()
        {
            var pet = New();
            var fear = ECSGameEffectFactory.Create(new(pet, 5000, 1),
                static (in ECSGameEffectInitParams i) => new WarlockPetFearEffect(i, null, grantsImmunity: false));
            pet.effectListComponent.BeginTick();
            fear.End(); pet.effectListComponent.BeginTick();
            Assert.That(pet.effectListComponent.ContainsEffectForEffectType(eEffect.WarlockPetFearImmunity), Is.False);
            Assert.That(typeof(BainsheeRealmPulseHandler).IsSubclassOf(typeof(BainsheePulseDmgSpellHandler)), Is.True);
        }

        [Test]
        public void ExpansionRacesFollowTheirTestSwitches()
        {
            bool vampiir = Properties.ENABLE_VAMPIIR_TEST, heretic = Properties.ENABLE_HERETIC_TEST, bainshee = Properties.ENABLE_BAINSHEE_TEST;
            try
            {
                Properties.ENABLE_VAMPIIR_TEST = Properties.ENABLE_HERETIC_TEST = Properties.ENABLE_BAINSHEE_TEST = false;
                Assert.That(new ClassVampiir().EligibleRaces, Is.Empty);
                Assert.That(new ClassHeretic().EligibleRaces, Is.Empty);
                Assert.That(new ClassBainshee().EligibleRaces, Is.Empty);
                Properties.ENABLE_VAMPIIR_TEST = Properties.ENABLE_HERETIC_TEST = Properties.ENABLE_BAINSHEE_TEST = true;
                Assert.That(new ClassVampiir().EligibleRaces, Is.EquivalentTo(new[] { PlayerRace.Celt, PlayerRace.Lurikeen, PlayerRace.Shar }));
                Assert.That(new ClassHeretic().EligibleRaces.Contains(PlayerRace.Saracen), Is.True, "1.125 added Saracen Heretics");
                Assert.That(new ClassBainshee().EligibleRaces.Count, Is.EqualTo(3));
            }
            finally
            {
                Properties.ENABLE_VAMPIIR_TEST = vampiir; Properties.ENABLE_HERETIC_TEST = heretic; Properties.ENABLE_BAINSHEE_TEST = bainshee;
            }
        }
        [Test]
        public void CocoonRampsItsDebuffsAndDropsThemWithTheAblative()
        {
            Assert.That(Enumerable.Range(0, 8).Select(i => HereticCocoonHandler.Ramp(25, 5, 50, i)), Is.EqualTo(new[] { 25, 30, 35, 40, 45, 50, 50, 50 }));
            var target = New();
            var db = new DbSpell { Name = "Destructive Cocoon", Type = eSpellType.HereticCocoon.ToString(), Target = "Enemy", Value = 200, Damage = 100, Duration = 60,
                CustomValues = new[] { new DbSpellXCustomValues { KeyName = "CocoonStart", Value = "25" }, new DbSpellXCustomValues { KeyName = "CocoonStep", Value = "5" },
                    new DbSpellXCustomValues { KeyName = "CocoonMax", Value = "50" } } };
            var handler = new HereticCocoonHandler(New(), new Spell(db, 49), _line);
            Assert.That(handler.CalculateSpellResistChance(target), Is.Zero, "Always lands");
            Assert.That(handler.ShortDescription, Does.Contain("200-point ablative"));
            var effect = (HereticCocoonEffect)ECSGameEffectFactory.Create(new(target, 60000, 1, handler), static (in ECSGameEffectInitParams i) => new HereticCocoonEffect(i));
            target.effectListComponent.BeginTick();
            Assert.That(target.DebuffCategory[eProperty.MeleeSpeed], Is.EqualTo(25));
            Assert.That(effect.RemainingValue, Is.EqualTo(200));
            Assert.That(HereticCocoonHandler.HasCocoon(target), Is.True, "Cannot be reapplied while active");
            effect.OnEffectPulse();
            Assert.That(target.DebuffCategory[eProperty.MeleeSpeed], Is.EqualTo(30));
            effect.End(); target.effectListComponent.BeginTick();
            Assert.That(target.DebuffCategory[eProperty.MeleeSpeed], Is.Zero);
        }

        [Test]
        public void ChargeUsesTheReducedLiveCosts()
        {
            var charge = new ModernCharge(new DbAbility { KeyName = "Charge", Name = "Charge", Description = "Charge" }, 0);
            Assert.That(Enumerable.Range(0, 5).Select(charge.CostForUpgrade), Is.EqualTo(new[] { 3, 3, 3, 5, 6 }), "1.128c");
        }

        [Test]
        public void VampiirBoltDescribesItsDrain()
        {
            var bolt = new VampiirBoltSpellHandler(New(), new Spell(new DbSpell { Name = "Devouring Bolt", Type = "VampiirBolt", Target = "Enemy",
                Value = 50, Range = 1875, RecastDelay = 45 }, 50), _line);
            Assert.That(bolt.ShortDescription, Does.Contain("20% of a player's maximum power").And.Contain("reuse 45 seconds").And.Contain("Usable in combat"));
        }

        [TestCase(eCharacterClass.Bainshee, eRealm.Hibernia, 1)]
        [TestCase(eCharacterClass.Vampiir, eRealm.Hibernia, 0)]
        [TestCase(eCharacterClass.Heretic, eRealm.Albion, 0)]
        public void EveryEligibleRacePassesCreationOnlyWhileEnabled(eCharacterClass career, eRealm realm, int gender)
        {
            bool vampiir = Properties.ENABLE_VAMPIIR_TEST, heretic = Properties.ENABLE_HERETIC_TEST, bainshee = Properties.ENABLE_BAINSHEE_TEST;
            try
            {
                Properties.ENABLE_VAMPIIR_TEST = Properties.ENABLE_HERETIC_TEST = Properties.ENABLE_BAINSHEE_TEST = true;
                var races = ScriptMgr.FindCharacterClass((int)career).EligibleRaces;
                Assert.That(races, Is.Not.Empty);
                foreach (var race in races)
                    Assert.That(CharacterCreateRequestHandler.IsCharacterValid(Character((int)race.ID, realm, career, gender)), Is.True, race.ID.ToString());
                Properties.ENABLE_VAMPIIR_TEST = Properties.ENABLE_HERETIC_TEST = Properties.ENABLE_BAINSHEE_TEST = false;
                Assert.That(CharacterCreateRequestHandler.IsCharacterValid(Character((int)races[0].ID, realm, career, gender)), Is.False);
            }
            finally
            {
                Properties.ENABLE_VAMPIIR_TEST = vampiir; Properties.ENABLE_HERETIC_TEST = heretic; Properties.ENABLE_BAINSHEE_TEST = bainshee;
            }
        }

        private static DbCoreCharacter Character(int race, eRealm realm, eCharacterClass career, int gender)
        {
            var stats = GlobalConstants.STARTING_STATS_DICT[(eRace)race];
            return new DbCoreCharacter
            {
                Name = "Expansiontest", AccountName = "unit-test", Level = 1, Race = race, Realm = (int)realm, Class = (int)career, Gender = gender,
                Strength = stats[eStat.STR] + 10, Constitution = stats[eStat.CON] + 10, Dexterity = stats[eStat.DEX] + 10,
                Quickness = stats[eStat.QUI], Intelligence = stats[eStat.INT], Piety = stats[eStat.PIE],
                Empathy = stats[eStat.EMP], Charisma = stats[eStat.CHR]
            };
        }
    }
}
