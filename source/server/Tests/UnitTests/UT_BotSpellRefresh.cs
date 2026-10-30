using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.GS;
using DOL.GS.PlayerClass;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Bots must pick up the spells a level-up or a trainer visit unlocks (the usable-skill lists are cached).</summary>
    [TestFixture]
    public class UT_BotSpellRefresh
    {
        private sealed class RefreshBot : GameBot
        {
            private RefreshBot() : base((OfflineWorldBotRecord)null) { }
            public ICharacterClass Class;
            public readonly List<string> Calls = new();
            public override ICharacterClass CharacterClass => Class;
            public override List<Tuple<Skill, Skill>> GetAllUsableSkills(bool update = false)
            {
                Calls.Add($"skills:{update}");
                return new();
            }
            public override List<Tuple<SpellLine, List<Skill>>> GetAllUsableListSpells(bool update = false)
            {
                Calls.Add($"list:{update}");
                return new();
            }
        }

        [TestCase(typeof(ClassWizard))]
        [TestCase(typeof(ClassArmsman))]
        public void SetBotSpellsRebuildsTheCachedSkillLists(Type characterClass)
        {
            var bot = (RefreshBot)RuntimeHelpers.GetUninitializedObject(typeof(RefreshBot));
            typeof(RefreshBot).GetField(nameof(RefreshBot.Calls)).SetValue(bot, new List<string>());
            bot.Class = (ICharacterClass)Activator.CreateInstance(characterClass);
            typeof(GameBot).GetMethod("SetBotSpells", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(bot, null);
            // The rebuild comes before any cached read.
            Assert.That(bot.Calls.GetRange(0, 2), Is.EqualTo(new[] { "skills:True", "list:True" }));
        }
    }
}
