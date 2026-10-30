using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>/spawn &lt;class&gt; &lt;spec&gt; picks one of the class's own spec templates.</summary>
    [TestFixture]
    public class UT_BotSpecChoice
    {
        [TestCase(eCharacterClass.Wizard, "fire", eSpecType.FireWiz)]
        [TestCase(eCharacterClass.Wizard, "ICE", eSpecType.IceWiz)]
        [TestCase(eCharacterClass.Enchanter, "mana", eSpecType.ManaEnchanter)]
        [TestCase(eCharacterClass.Warrior, "two", eSpecType.TwoHanded)]
        [TestCase(eCharacterClass.Warrior, "shield", eSpecType.OneHandAndShield)]
        [TestCase(eCharacterClass.TuathaSovereign, "two", eSpecType.TwoHanded)]
        public void SpecWordResolvesToTheClassTemplate(eCharacterClass charClass, string word, eSpecType expected)
        {
            Assert.That(BotSpec.TryResolveSpecialization(charClass, word, out eSpecType spec), Is.True);
            Assert.That(spec, Is.EqualTo(expected));
        }

        [TestCase(eCharacterClass.Wizard, "body")]
        [TestCase(eCharacterClass.Wizard, "")]
        public void UnknownSpecWordIsRejected(eCharacterClass charClass, string word) =>
            Assert.That(BotSpec.TryResolveSpecialization(charClass, word, out _), Is.False);
    }
}
