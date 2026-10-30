using DOL.Database;
using DOL.GS;
using DOL.GS.PacketHandler.Client.v168;
using DOL.GS.PlayerClass;
using DOL.GS.ServerProperties;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture, NonParallelizable]
public sealed class UT_ValkyrieCreation
{
    private bool previous;

    [SetUp]
    public void EnableTest()
    {
        previous = Properties.ENABLE_VALKYRIE_TEST;
        Properties.ENABLE_VALKYRIE_TEST = true;
    }

    [TearDown]
    public void Restore() => Properties.ENABLE_VALKYRIE_TEST = previous;

    [TestCase(eRace.Norseman)]
    [TestCase(eRace.Dwarf)]
    [TestCase(eRace.Frostalf)]
    [TestCase(eRace.Valkyn)]
    public void EligibleRaces(eRace race) => Assert.That(new ClassValkyrie().EligibleRaces.Exists(x => x.ID == race), Is.True);

    [Test]
    public void DisabledByDefaultProfile()
    {
        Properties.ENABLE_VALKYRIE_TEST = false;
        Assert.That(new ClassValkyrie().EligibleRaces, Is.Empty);
    }

    private static DbCoreCharacter Character() => new()
    {
        Name = "Valktest", AccountName = "unit-test", Level = 1,
        Race = (int)eRace.Norseman, Realm = (int)eRealm.Midgard, Class = (int)eCharacterClass.Valkyrie, Gender = 1,
        Strength = 80, Constitution = 80, Dexterity = 60, Quickness = 50,
        Intelligence = 60, Piety = 60, Empathy = 60, Charisma = 60
    };

    [Test]
    public void FemaleNorseCreationIsValid() => Assert.That(CharacterCreateRequestHandler.IsCharacterValid(Character()), Is.True);

    [Test]
    public void MaleCreationRemainsInvalid()
    {
        var c = Character(); c.Gender = 0;
        Assert.That(CharacterCreateRequestHandler.IsCharacterValid(c), Is.False);
    }

    [Test]
    public void TrollRemainsInvalid() => Assert.That(new ClassValkyrie().EligibleRaces.Exists(x => x.ID == eRace.Troll), Is.False);
}
