using System.Collections.Generic;
using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture, NonParallelizable]
    public class UT_ModernMaulerTooltips
    {
        private ModernRaTestScope _scope;
        private readonly SpellLine _line = new("Magnetism", "Magnetism", "Magnetism", true);
        [SetUp] public void Setup() => _scope = new ModernRaTestScope();
        [TearDown] public void Cleanup() => _scope.Dispose();

        private static Spell Make(string type, double value = 0, double damage = 0, int duration = 0, int radius = 0, int stat = 0)
        {
            var db = new DbSpell { SpellID = 67130, Name = "test", Type = type, Target = "Enemy", Value = value, Damage = damage,
                Duration = duration, Radius = radius, Description = "Modern Mauler test kit." };
            if (stat > 0) db.CustomValues = new[] { new DbSpellXCustomValues { KeyName = "MaulerStat", Value = stat.ToString() } };
            return new Spell(db, 50);
        }

        [Test]
        public void StatSpellsDescribeTheirEffect()
        {
            Assert.That(ModernMauler.StatText(Make("MaulerStat", 20, duration: 60, stat: 10)), Is.EqualTo("Increases your weapon skill by 20% for 60 seconds."));
            Assert.That(ModernMauler.StatText(Make("MaulerStat", 40, duration: 60, stat: 12)), Does.Contain("parry by 40%"));
            Assert.That(ModernMauler.StatText(Make("MaulerStat", 30, duration: 30, stat: 14)), Does.Contain("30% chance to fumble"));
            Assert.That(ModernMauler.StatText(Make("MaulerStat", 15, duration: 8, radius: 250, stat: 15)), Does.Contain("within 250 by 15%"));
        }

        [Test]
        public void ControlAndUtilityTooltipsReplaceThePlaceholder()
        {
            Assert.That(new MaulerControlHandler(null, Make("MaulerControl", 1, duration: 6), _line).ShortDescription, Does.StartWith("Silences the target for 6 seconds"));
            Assert.That(new MaulerControlHandler(null, Make("MaulerControl", 2, duration: 4), _line).ShortDescription, Does.StartWith("Disarms the target for 4 seconds"));
            string protect = new MaulerUtilityHandler(null, Make("MaulerUtility", 4, 25, 30), _line).ShortDescription;
            Assert.That(protect, Does.Contain("Absorbs 25%")); Assert.That(protect, Does.Not.Contain("test kit"));
            Assert.That(ModernMauler.UtilityText(Make("MaulerUtility", 6, 30)), Does.Contain("30% of the target's maximum power"));
        }

        [Test]
        public void ConvergenceKeepsItsWrittenDescription()
        {
            var spell = new Spell(new DbSpell { SpellID = 67350, Name = "Aura Convergence", Type = "MaulerUtility", Target = "Self", Value = 7, Damage = 33,
                Description = "Sacrifices half nearby group members current power." }, 50);
            Assert.That(new MaulerUtilityHandler(null, spell, _line).ShortDescription, Does.StartWith("Sacrifices half"));
        }
    }
}
