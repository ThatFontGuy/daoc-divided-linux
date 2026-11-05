using DOL.AI.Brain;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Owner 2026-10-30: pets, and monsters in a battleground, lose a target that goes into stealth.</summary>
    [TestFixture]
    public class UT_PetLosesStealthedTarget
    {
        //                 pet    bg     seesStealth playerLike stealthed  expected
        [TestCase(true,  false, false, true,  true,  true)]    // a pet outside a battleground
        [TestCase(false, true,  false, true,  true,  true)]    // a monster in a battleground
        [TestCase(true,  true,  false, true,  true,  true)]
        [TestCase(false, false, false, true,  true,  false)]   // an ordinary monster in the world is unchanged
        [TestCase(true,  true,  true,  true,  true,  false)]   // a keep stealther sees through it
        [TestCase(true,  true,  false, true,  false, false)]   // not stealthed: keeps the target
        [TestCase(true,  true,  false, false, true,  false)]   // a stealthed monster is not a player or bot
        public void LosesOnlyAStealthedPlayerOrBotInTheListedPlaces(bool pet, bool battleground, bool sees, bool playerLike, bool stealthed, bool expected) =>
            Assert.That(StandardMobBrain.LosesStealthedTarget(pet, battleground, sees, playerLike, stealthed), Is.EqualTo(expected));
    }
}
