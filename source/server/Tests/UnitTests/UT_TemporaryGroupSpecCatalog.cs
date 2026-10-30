using System.Linq;
using DOL.GS.Commands;
using NUnit.Framework;

namespace DOL.GS.Tests
{
    /// <summary>/spawn specs (owner 2026-10-28): builds named after the spec line each one really trains highest.</summary>
    [TestFixture]
    public sealed class UT_TemporaryGroupSpecCatalog
    {
        private static string[] Labels(eCharacterClass characterClass) =>
            TemporaryGroupSpecCatalog.For(characterClass).Select(option => option.Label).OrderBy(label => label).ToArray();

        [Test]
        public void BuildsAreNamedAfterWhatTheyTrainHighest() => Assert.Multiple(() =>
        {
            // The Friar's "staff" family includes variants that train Enhancement highest, and its "rejuvenation" family
            // one that trains Staff and one Enhancement; the options are the lines really trained.
            Assert.That(Labels(eCharacterClass.Friar), Is.EqualTo(new[] { Specs.Enhancement, Specs.Rejuvenation, Specs.Staff }));
            Assert.That(Labels(eCharacterClass.Healer), Is.EqualTo(new[] { Specs.Augmentation, Specs.Mending, Specs.Pacification }));
            Assert.That(Labels(eCharacterClass.Druid), Is.EqualTo(new[] { Specs.Nature, Specs.Nurture, Specs.Regrowth }));
            Assert.That(Labels(eCharacterClass.Theurgist), Is.EqualTo(new[] { Specs.Cold_Magic, Specs.Earth_Magic, Specs.Wind_Magic }));
        });

        [Test]
        public void AnOptionSpawnsABuildThatTrainsItHighest()
        {
            foreach (eCharacterClass characterClass in new[] { eCharacterClass.Friar, eCharacterClass.Healer, eCharacterClass.Druid })
                foreach (TemporaryGroupSpecCatalog.Option option in TemporaryGroupSpecCatalog.For(characterClass))
                    for (int i = 0; i < 20; i++)
                        Assert.That(TemporaryGroupSpecCatalog.TopLine(TemporaryGroupSpecCatalog.Create(characterClass, option)),
                            Is.EqualTo(option.Label), $"{characterClass} ({option.Label})");
        }

        [Test]
        public void SpecsAreTypedInFull()
        {
            Assert.That(TemporaryGroupSpecCatalog.TryResolve(eCharacterClass.Healer, "augmentation", out var option), Is.True);
            Assert.That(option.Label, Is.EqualTo(Specs.Augmentation));
            Assert.That(TemporaryGroupSpecCatalog.TryResolve(eCharacterClass.Theurgist, "Cold Magic", out _), Is.True);
            Assert.That(TemporaryGroupSpecCatalog.TryResolve(eCharacterClass.Healer, "aug", out _), Is.False);
        }

        [Test]
        public void WeaponSetupsKeepTheirNames() => Assert.Multiple(() =>
        {
            Assert.That(TemporaryGroupSpecCatalog.SetupLabel(eCharacterClass.Warrior, eSpecType.OneHandAndShield), Is.EqualTo("One Handed and Shield"));
            Assert.That(TemporaryGroupSpecCatalog.SetupLabel(eCharacterClass.Armsman, eSpecType.TwoHandHybrid), Is.EqualTo("Two Handed Hybrid"));
            Assert.That(TemporaryGroupSpecCatalog.SetupLabel(eCharacterClass.Paladin, eSpecType.TwoHandHybrid), Is.EqualTo("Two Handed"));
            Assert.That(TemporaryGroupSpecCatalog.SetupLabel(eCharacterClass.Blademaster, eSpecType.DualWield), Is.EqualTo("Celtic Dual"));
            Assert.That(TemporaryGroupSpecCatalog.SetupLabel(eCharacterClass.Savage, eSpecType.DualWield), Is.EqualTo("Hand to Hand"));
        });

        [Test]
        public void ASingleBuildClassHasNoOptions() =>
            Assert.That(TemporaryGroupSpecCatalog.For(eCharacterClass.Berserker), Is.Empty);
    }
}
