using System.Collections.Generic;
using System.Linq;
using DOL.GS;
using DOL.GS.Trials;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_TrialsMl5
    {
        private const int HallsMin = 8192;
        private const int HallsMax = 73728;
        private const int AtumMinX = 229376;
        private const int AtumMaxX = 294912;
        private const int AtumMinY = 393216;
        private const int AtumMaxY = 458752;
        private const int TyphonMinX = 458752;
        private const int AshenMaxX = 589824;
        private const int VolcanusMinY = 524288;
        private const int VolcanusMaxY = 589824;

        private static List<TrialDefinition> Ml5Trials => Ml5.Trials().ToList();
        private static List<TrialDefinition> Ml6Trials => Ml6.Trials().ToList();

        private static IEnumerable<TrialDefinition> Both => Ml5Trials.Concat(Ml6Trials);

        private static IEnumerable<TrialPoint> Points(TrialDefinition trial) =>
            new[] { trial.Anchor }.Concat(trial.Phases.SelectMany(phase => phase.Mobs).Where(mob => mob.At.HasValue).Select(mob => mob.At.Value));

        private static TrialDefinition Step(int ml, int step) => TrialCatalog.Find($"{ml}.{step}");

        [Test]
        public void Ml5_StepsExistInOrder()
        {
            Assert.That(Ml5Trials.Select(trial => trial.Name), Is.EqualTo(new[]
            {
                "Ma'atis' Coil", "Ma'atis' Hunger", "Ma'atis' Breath", "Ma'atis' Blood", "Ma'ati's Reflection",
                "Ma'atis' Preservation", "Ma'atis' Mask", "Ma'atis' Wrap", "Token", "Ammut's Appetite",
            }));
            Assert.That(Ml5Trials.Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(Ml5Trials.All(trial => trial.ML == 5));
        }

        [Test]
        public void Ml6_StepsExistInOrder()
        {
            Assert.That(Ml6Trials.Select(trial => trial.Name), Is.EqualTo(new[]
            {
                "Hunt for the Haje-Uraei", "Sacrifice", "Lateef", "Infestation", "Flames",
                "Siraadi", "Ankhkare", "Efreet", "Fortress", "Chimera's Fortification",
            }));
            Assert.That(Ml6Trials.Select(trial => trial.Step), Is.EqualTo(Enumerable.Range(1, 10)));
            Assert.That(Ml6Trials.All(trial => trial.ML == 6));
        }

        [Test]
        public void Ml5_ScopesFollowTheWindowText()
        {
            Assert.That(Ml5Trials.Take(9).All(trial => trial.Scope == TrialScope.Group));
            Assert.That(Step(5, 10).Scope, Is.EqualTo(TrialScope.Raid));
        }

        [Test]
        public void Ml6_ScopesFollowTheWindowText()
        {
            TrialScope[] expected =
            {
                TrialScope.Group, TrialScope.Raid, TrialScope.Raid, TrialScope.Raid, TrialScope.Solo,
                TrialScope.Raid, TrialScope.Raid, TrialScope.Raid, TrialScope.Raid, TrialScope.Raid,
            };
            Assert.That(Ml6Trials.Select(trial => trial.Scope), Is.EqualTo(expected));
        }

        [Test]
        public void Finales_NeedEveryEarlierStep()
        {
            Assert.That(TrialManager.Required(Step(5, 10)), Is.EqualTo(Enumerable.Range(1, 9)));
            Assert.That(TrialManager.Required(Step(6, 10)), Is.EqualTo(Enumerable.Range(1, 9)));
        }

        [Test]
        public void Tokens_AreStoodForByEarlierSteps()
        {
            Assert.That(Step(5, 9).RequiresSteps, Is.EqualTo(new[] { 6, 7, 8 }));
            Assert.That(Step(6, 7).RequiresSteps, Is.EqualTo(new[] { 4, 5, 6 }));
        }

        [Test]
        public void Places_SitInsideTheirZones()
        {
            foreach (TrialDefinition trial in Ml5Trials.Where(trial => trial.Zone == TrialZone.Maati))
            {
                foreach (TrialPoint point in Points(trial))
                {
                    Assert.That(point.X, Is.InRange(HallsMin, HallsMax), trial.Key);
                    Assert.That(point.Y, Is.InRange(HallsMin, HallsMax), trial.Key);
                }
            }

            foreach (TrialPoint point in Points(Step(5, 5)))
            {
                Assert.That(point.X, Is.InRange(AtumMinX, AtumMaxX));
                Assert.That(point.Y, Is.InRange(AtumMinY, AtumMaxY));
            }

            foreach (TrialDefinition trial in Ml6Trials)
            {
                Assert.That(trial.Zone, Is.EqualTo(TrialZone.Oceanus), trial.Key);
                foreach (TrialPoint point in Points(trial))
                {
                    Assert.That(point.X, Is.InRange(TyphonMinX, AshenMaxX), trial.Key);
                    Assert.That(point.Y, Is.InRange(VolcanusMinY, VolcanusMaxY), trial.Key);
                }
            }
        }

        [Test]
        public void Tuning_StaysInsideTheBrief()
        {
            foreach (TrialDefinition trial in Both)
            {
                Assert.That(trial.TimeLimitSeconds, Is.InRange(900, 2400), trial.Key);
                foreach (TrialPhase phase in trial.Phases)
                {
                    Assert.That(phase.Pulses.All(pulse => pulse.Damage <= 300), trial.Key);
                    foreach (TrialMobSpec mob in phase.Mobs.Where(mob => !mob.Objective))
                        Assert.That(mob.Level, Is.InRange((byte)55, (byte)70), $"{trial.Key} {mob.Name}");
                }
            }
        }

        [Test]
        public void EveryRequiredMonster_CanBeFinished()
        {
            foreach (TrialDefinition trial in Both.Where(trial => trial.Key != "5.7" && trial.Key != "6.5"))
            {
                IEnumerable<TrialMobSpec> mobs = trial.Phases.SelectMany(phase => phase.Mobs);
                Assert.That(mobs.Where(mob => mob.Immune).All(mob => !mob.Required), trial.Key);
            }
        }

        [Test]
        public void Replaces_NameNoCommonCreature()
        {
            string[] common = { "uraeus", "salamander", "efreeti", "siam-he prema", "siam-he chanter", "bound zaubak", "elite taur defender" };
            Assert.That(Both.SelectMany(trial => trial.Replaces).Intersect(common), Is.Empty);
        }

        [Test]
        public void Thresholds_CountHealthMarksPassed()
        {
            Assert.That(Ml5.PassedThresholds(100, Ml5.DuamutefSplits), Is.EqualTo(0));
            Assert.That(Ml5.PassedThresholds(65, Ml5.DuamutefSplits), Is.EqualTo(1));
            Assert.That(Ml5.PassedThresholds(30, Ml5.DuamutefSplits), Is.EqualTo(2));
            Assert.That(Ml5.PassedThresholds(26, Ml5.HapySplits), Is.EqualTo(2));
        }

        [Test]
        public void Heals_GrowWithWhatIsLeftAlive()
        {
            Assert.That(Ml5.ScarabHeal(0, 28000), Is.EqualTo(0));
            Assert.That(Ml5.ScarabHeal(6, 28000), Is.EqualTo(420));
            Assert.That(Ml5.HapyCopyHeal(24000), Is.EqualTo(960));
        }

        [Test]
        public void Ring_SpacesPointsOnTheCircle()
        {
            TrialPoint centre = new(1000, 2000, 300);
            Assert.That(Ml6.Ring(centre, 100, 0, 4), Is.EqualTo(new TrialPoint(1100, 2000, 300)));
            Assert.That(Ml6.Ring(centre, 100, 1, 4), Is.EqualTo(new TrialPoint(1000, 2100, 300)));
            Assert.That(Ml6.Ring(centre, 100, 2, 4), Is.EqualTo(new TrialPoint(900, 2000, 300)));
        }

        [Test]
        public void GateWaves_SpeedUpAsTheGateFails()
        {
            Assert.That(Ml6.GateWaveSeconds(100), Is.EqualTo(Ml6.OpenGateWaveSeconds));
            Assert.That(Ml6.GateWaveSeconds(31), Is.EqualTo(Ml6.OpenGateWaveSeconds));
            Assert.That(Ml6.GateWaveSeconds(30), Is.EqualTo(Ml6.FailingGateWaveSeconds));
        }
    }
}
