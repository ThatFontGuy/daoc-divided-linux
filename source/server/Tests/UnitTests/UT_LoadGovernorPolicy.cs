using System;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests.Gameserver
{
    [TestFixture]
    public class UT_LoadGovernorPolicy
    {
        private static readonly DateTime T0 = new(2026, 1, 1, 12, 0, 0, DateTimeKind.Utc);

        private static LoadGovernorPolicy.Decision Step(LoadGovernorPolicy policy, int seconds, double tps, long freeMb = 8000) =>
            policy.Update(T0.AddSeconds(seconds), tps, freeMb, minTpsPercent: 90, resumeTpsPercent: 95, minFreeMb: 1500, shedAfterSeconds: 120);

        [Test]
        public void Healthy_NeverHolds()
        {
            var policy = new LoadGovernorPolicy();
            for (int s = 0; s < 600; s += 10)
                Assert.That(Step(policy, s, 99.5).HoldLogins, Is.False);
        }

        [Test]
        public void SlowTicks_HoldLogins_ButDoNotShedAtOnce()
        {
            var policy = new LoadGovernorPolicy();
            var first = Step(policy, 0, 80);
            Assert.That(first.HoldLogins, Is.True);
            Assert.That(first.Changed, Is.True);
            Assert.That(first.Shed, Is.EqualTo(0));
            Assert.That(Step(policy, 60, 80).Shed, Is.EqualTo(0));
        }

        [Test]
        public void StaysSlow_ShedsAfterGraceThenEveryThirtySeconds()
        {
            var policy = new LoadGovernorPolicy();
            Step(policy, 0, 80);
            Assert.That(Step(policy, 120, 80).Shed, Is.EqualTo(LoadGovernorPolicy.ShedBatch));
            Assert.That(Step(policy, 130, 80).Shed, Is.EqualTo(0));
            Assert.That(Step(policy, 150, 80).Shed, Is.EqualTo(LoadGovernorPolicy.ShedBatch));
        }

        [Test]
        public void Recovery_NeedsAFullMinuteAtResumeLevel()
        {
            var policy = new LoadGovernorPolicy();
            Step(policy, 0, 80);
            Assert.That(Step(policy, 10, 96).HoldLogins, Is.True);
            Assert.That(Step(policy, 40, 92).HoldLogins, Is.True);   // between the limits: unchanged, timer restarts
            Assert.That(Step(policy, 50, 96).HoldLogins, Is.True);
            Assert.That(Step(policy, 109, 96).HoldLogins, Is.True);
            var resumed = Step(policy, 110, 96);
            Assert.That(resumed.HoldLogins, Is.False);
            Assert.That(resumed.Changed, Is.True);
        }

        [Test]
        public void LowMemory_Holds_AndNeedsHeadroomToResume()
        {
            var policy = new LoadGovernorPolicy();
            Assert.That(Step(policy, 0, 99, freeMb: 1000).HoldLogins, Is.True);
            Assert.That(Step(policy, 10, 99, freeMb: 1600).HoldLogins, Is.True);
            Assert.That(Step(policy, 20, 99, freeMb: 2000).HoldLogins, Is.True);
            Assert.That(Step(policy, 80, 99, freeMb: 2000).HoldLogins, Is.False);
        }

        [Test]
        public void ResumeLevelBelowHoldLevel_DoesNotFlipFlop()
        {
            var policy = new LoadGovernorPolicy();
            for (int s = 0; s < 300; s += 10)
            {
                var decision = policy.Update(T0.AddSeconds(s), 99.8, 8000, minTpsPercent: 101, resumeTpsPercent: 95, minFreeMb: 1500, shedAfterSeconds: 120);
                Assert.That(decision.HoldLogins, Is.True);
            }
        }

        [Test]
        public void UnknownMemory_IsIgnored()
        {
            var policy = new LoadGovernorPolicy();
            Assert.That(Step(policy, 0, 99, freeMb: -1).HoldLogins, Is.False);
        }
    }
}
