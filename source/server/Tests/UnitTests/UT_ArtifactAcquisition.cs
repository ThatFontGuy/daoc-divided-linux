using System.Linq;
using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_ArtifactAcquisition
    {
        private static ArtifactItem Item(int level)
        {
            DbItemTemplate template = new()
            {
                Id_nb = "test_artifact",
                Name = "Test",
                Bonus1Type = 1,
                Bonus1 = 50,
                Bonus2Type = 2,
                Bonus2 = -10,
                ProcSpellID = 100,
                SpellID = 200,
                SpellID1 = 300,
                DPS_AF = 165
            };

            return new ArtifactItem(template) { Experience = ArtifactLevels.XpForLevel(level) };
        }

        [Test]
        public void Levels_FollowTheXpTable()
        {
            Assert.That(ArtifactLevels.LevelFor(0), Is.EqualTo(0));
            Assert.That(ArtifactLevels.LevelFor(ArtifactLevels.XpForLevel(1) - 1), Is.EqualTo(0));
            Assert.That(ArtifactLevels.LevelFor(ArtifactLevels.XpForLevel(1)), Is.EqualTo(1));
            Assert.That(ArtifactLevels.LevelFor(ArtifactLevels.XpForLevel(7)), Is.EqualTo(7));
            Assert.That(ArtifactLevels.LevelFor(ArtifactLevels.MaxXp * 2), Is.EqualTo(ArtifactLevels.MaxLevel));
        }

        [Test]
        public void TenLevels_AreAbout1900EvenKills()
        {
            Assert.That(ArtifactLevels.MaxXp / ArtifactLevels.XpPerKill, Is.EqualTo(1900));
        }

        [Test]
        public void Bonuses_StartAt40PercentAndReachFullValue()
        {
            Assert.That(Item(0).Bonus1, Is.EqualTo(20));
            Assert.That(Item(5).Bonus1, Is.EqualTo(35));
            Assert.That(Item(10).Bonus1, Is.EqualTo(50));
        }

        [Test]
        public void NegativeBonuses_ScaleTheSameWay()
        {
            Assert.That(Item(0).Bonus2, Is.EqualTo(-4));
            Assert.That(Item(10).Bonus2, Is.EqualTo(-10));
        }

        [Test]
        public void ArmorAndWeaponValues_DoNotDependOnLevel()
        {
            Assert.That(Item(0).DPS_AF, Is.EqualTo(165));
        }

        [Test]
        public void Abilities_OpenAtFiveAndTen_ProcFirst()
        {
            ArtifactItem low = Item(4);
            Assert.That(low.ProcSpellID, Is.Zero);
            Assert.That(low.SpellID, Is.Zero);

            ArtifactItem mid = Item(5);
            Assert.That(mid.ProcSpellID, Is.EqualTo(100));
            Assert.That(mid.SpellID, Is.Zero);
            Assert.That(mid.SpellID1, Is.Zero);

            ArtifactItem top = Item(10);
            Assert.That(top.SpellID, Is.EqualTo(200));
            Assert.That(top.SpellID1, Is.EqualTo(300));
        }

        [Test]
        public void SetExperience_ClampsToTheTable()
        {
            ArtifactItem item = Item(0);
            item.SetExperience(null, ArtifactLevels.MaxXp + 500);
            Assert.That(item.Experience, Is.EqualTo(ArtifactLevels.MaxXp));

            item.SetExperience(null, -5);
            Assert.That(item.Experience, Is.Zero);
        }

        [Test]
        public void Encounters_AllLoadAndHaveARewardPath()
        {
            Assert.That(ArtifactEncounters.All, Has.Length.EqualTo(62));
            Assert.That(ArtifactEncounters.Find("1056")?.Name, Is.EqualTo("Traitor's Dagger"));

            foreach (ArtifactEncounterDef encounter in ArtifactEncounters.All)
            {
                Assert.That(encounter.HealthFactor, Is.GreaterThan(0), encounter.Name);

                foreach (ArtifactStageDef stage in encounter.Stages)
                    Assert.That(stage.Spawns.All(spawn => spawn.Model > 0 && spawn.Level > 0 && spawn.Count > 0), encounter.Name);
            }
        }

        [Test]
        public void CreditNames_LoseTheirSuffix()
        {
            Assert.That(ArtifactCatalog.CreditName("Bruiser Credit"), Is.EqualTo("Bruiser"));
            Assert.That(ArtifactCatalog.CreditName("Bruiser"), Is.EqualTo("Bruiser"));
        }
    }
}
