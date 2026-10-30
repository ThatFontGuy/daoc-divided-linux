using System.Collections.Generic;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using DOL.GS.PlayerClass;
using DOL.GS.Realm;
using DOL.GS.ServerProperties;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_DeathKnight
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
        public void ChthonicArmorFollowsTheLevelBands()
        {
            Assert.That(DeathKnight.ChthonicArmor(50), Is.EqualTo(125), "1.123B");
            Assert.That(DeathKnight.ChthonicArmor(47), Is.EqualTo(75));
            Assert.That(DeathKnight.ChthonicArmor(40), Is.EqualTo(50));
            Assert.That(DeathKnight.ChthonicArmor(25), Is.EqualTo(25));
            Assert.That(DeathKnight.ChthonicArmor(10), Is.Zero);
        }

        [Test]
        public void DecrepitFormAddsMagicDamageUntilItEnds()
        {
            var dk = New();
            var handler = new DeathKnightFormHandler(dk, Make(eSpellType.DeathKnightForm, 1), _line);
            var effect = ECSGameEffectFactory.Create(new(dk, 0, 1, handler), static (in ECSGameEffectInitParams i) => new DeathKnightFormEffect(i));
            dk.effectListComponent.BeginTick();
            Assert.That(dk.AbilityBonus[eProperty.SpellDamage], Is.EqualTo(10));
            Assert.That(dk.BaseBuffBonusCategory[eProperty.ArmorAbsorption], Is.Zero, "live delve: no absorption (removed in 1.125)");
            Assert.That(effect.ExpireTick, Is.EqualTo(long.MaxValue), "maintained until changed");
            Assert.That(DeathKnight.Form(dk), Is.EqualTo(DeathKnightForm.Decrepit));
            effect.End(); dk.effectListComponent.BeginTick();
            Assert.That(dk.AbilityBonus[eProperty.SpellDamage], Is.Zero);
        }

        [Test]
        public void DarknessCountsAsChthonicAndDecrepitAndBoostsThem()
        {
            var dk = New();
            var handler = new DeathKnightFormHandler(dk, Make(eSpellType.DeathKnightForm, 4, 30), _line);
            ECSGameEffectFactory.Create(new(dk, 30000, 1, handler), static (in ECSGameEffectInitParams i) => new DeathKnightFormEffect(i));
            dk.effectListComponent.BeginTick();
            Assert.That(DeathKnight.InForm(dk, DeathKnightForm.Chthonic) && DeathKnight.InForm(dk, DeathKnightForm.Decrepit), Is.True);
            Assert.That(DeathKnight.InForm(dk, DeathKnightForm.Spirit), Is.False, "live: Demon Lord has Chthonic and Decrepit benefits only");
            Assert.That(dk.AbilityBonus[eProperty.SpellDamage], Is.EqualTo(20), "live Demon Power");
            Assert.That(dk.AbilityBonus[eProperty.ParryChance], Is.EqualTo(25), "live Demon Deflection");
            Assert.That(dk.AbilityBonus[eProperty.Skill_Pain_working], Is.EqualTo(40), "live Demon Skill");
            Assert.That(dk.BaseBuffBonusCategory[eProperty.ArmorAbsorption], Is.EqualTo(22), "Chthonic's 20 absorption +10%");
        }

        [Test]
        public void FormsChangeTheModel()
        {
            var npc = New();
            // The models of live's shapechange spells.
            Assert.That(DeathKnight.FormModel(npc, DeathKnightForm.Decrepit), Is.EqualTo(23), "Decrepit Shapechange");
            Assert.That(DeathKnight.FormModel(npc, DeathKnightForm.Chthonic), Is.EqualTo(653), "Chthonic Shapechange");
            Assert.That(DeathKnight.FormModel(npc, DeathKnightForm.Darkness), Is.EqualTo(635), "Demon Shapechange");
            Assert.That(DeathKnight.FormModel(npc, DeathKnightForm.Spirit), Is.EqualTo(1670), "Spirit Shapechange");
            Assert.That(DeathKnight.SpiritTemplateOffset, Is.EqualTo(10), "servant 66001 has its spirit look in template 66011");
        }

        [Test]
        public void PowerShieldOnlyFillsHealthBackToHalf()
        {
            Assert.That(DeathKnightPowerShieldEffect.Transfer(300, 1000, 1000), Is.EqualTo(200));
            Assert.That(DeathKnightPowerShieldEffect.Transfer(300, 1000, 50), Is.EqualTo(50));
            Assert.That(DeathKnightPowerShieldEffect.Transfer(600, 1000, 1000), Is.Zero);
        }

        [Test]
        public void IcebrandMatchesTheCasterLevelBand()
        {
            Assert.That(DeathKnightConjureHandler.IcebrandFor(1), Is.EqualTo("deathknight_icebrand_0"));
            Assert.That(DeathKnightConjureHandler.IcebrandFor(37), Is.EqualTo("deathknight_icebrand_35"));
            Assert.That(DeathKnightConjureHandler.IcebrandFor(50), Is.EqualTo("deathknight_icebrand_50"));
            Assert.That(DeathKnight.IsConjured(new DbInventoryItem { Id_nb = "deathknight_nethersbane" }), Is.True);
            Assert.That(DeathKnight.IsConjured(new DbInventoryItem { Id_nb = "necromancer_item" }), Is.False);
        }

        [Test]
        public void IgnoreGivesAChanceToResistDebuffs()
        {
            var ally = New();
            var handler = new DeathKnightIgnoreHandler(New(), Make(eSpellType.DeathKnightIgnore, 70, 20, "Realm"), _line);
            Assert.That(DeathKnight.IgnoreChance(ally), Is.Zero);
            ECSGameEffectFactory.Create(new(ally, 20000, 1, handler), static (in ECSGameEffectInitParams i) => new DeathKnightSimpleEffect(i, eEffect.DeathKnightIgnore));
            ally.effectListComponent.BeginTick();
            Assert.That(DeathKnight.IgnoreChance(ally), Is.EqualTo(70));
        }

        [Test]
        public void SnaresIgnoreAndGrantNoImmunity()
        {
            var target = New();
            var snare = new DeathKnightSnareHandler(New(), Make(eSpellType.DeathKnightSnare, 70, 6, "Enemy"), _line);
            var effect = snare.CreateECSEffect(new(target, 6000, 1, snare));
            Assert.That(effect.TriggersImmunity, Is.False);
            Assert.That(snare.IgnoresSnareImmunity, Is.True, "lands on targets with snare immunity");
            Assert.That(snare.ShortDescription, Does.Contain("70%"));
        }
        [Test]
        public void SharesNecromancerItemsButNotTheReverse()
        {
            int dk = (int)eCharacterClass.DeathKnight, necro = (int)eCharacterClass.Necromancer;
            Assert.That(ClassItemRules.Allows("12", dk), Is.True, "Necromancer items");
            Assert.That(ClassItemRules.Allows("6;12", dk), Is.True);
            Assert.That(ClassItemRules.Allows("66", dk), Is.True);
            Assert.That(ClassItemRules.Allows("", dk), Is.True);
            Assert.That(ClassItemRules.Allows("6", dk), Is.False);
            Assert.That(ClassItemRules.Allows("66", necro), Is.False, "the classic Necromancer gains nothing");
            Assert.That(ClassItemRules.ItemClass(eCharacterClass.DeathKnight), Is.EqualTo(eCharacterClass.Necromancer));
            Assert.That(ClassItemRules.ItemClass(eCharacterClass.Cleric), Is.EqualTo(eCharacterClass.Cleric));
        }

        [Test]
        public void IsANewAlbionClassThatKeepsTheClassicNecromancer()
        {
            Assert.That((int)eCharacterClass.DeathKnight, Is.EqualTo(66));
            Assert.That(GlobalConstants.STARTING_CLASSES_DICT[eRealm.Albion], Does.Contain(eCharacterClass.DeathKnight));
            Assert.That(GlobalConstants.STARTING_CLASSES_DICT[eRealm.Albion], Does.Contain(eCharacterClass.Necromancer));
            var dk = new ClassDeathKnight();
            Assert.That(dk, Is.Not.InstanceOf<ClassDisciple>(), "no classic shade behavior");
            Assert.That(dk.HasAdvancedFromBaseClass(), Is.True);
            Assert.That(dk.ClassType, Is.EqualTo(eClassType.ListCaster));
        }

        [Test]
        public void RacesFollowTheTestSwitch()
        {
            bool previous = Properties.ENABLE_DEATH_KNIGHT_TEST;
            try
            {
                Properties.ENABLE_DEATH_KNIGHT_TEST = false;
                Assert.That(new ClassDeathKnight().EligibleRaces, Is.Empty);
                Properties.ENABLE_DEATH_KNIGHT_TEST = true;
                Assert.That(new ClassDeathKnight().EligibleRaces, Is.EquivalentTo(new[] { PlayerRace.Briton, PlayerRace.Inconnu, PlayerRace.Saracen }));
            }
            finally { Properties.ENABLE_DEATH_KNIGHT_TEST = previous; }
        }
    }
}
