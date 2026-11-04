using System;
using System.Numerics;
using NUnit.Framework;

namespace DOL.GS.Tests;

/// <summary>Zone crossings bots could not walk to, from the modern test server's log of 2026-10-30.</summary>
[TestFixture]
public sealed class UT_SeamCrossingQuarantine
{
    private static readonly DateTime Now = new(2026, 10, 30, 12, 0, 0, DateTimeKind.Utc);
    private static readonly Vector3 Crossing = new(385088, 486624, 5547);

    [SetUp]
    public void Reset() => AutonomousSeamCrossingQuarantine.ResetForTests();

    [TearDown]
    public void Clear() => AutonomousSeamCrossingQuarantine.ResetForTests();

    [Test]
    public void ACrossingIsBenchedOnlyAfterThreeDifferentBotsFailIt()
    {
        Assert.That(AutonomousSeamCrossingQuarantine.ReportFailure(200, Crossing, 101, Now), Is.False);
        Assert.That(AutonomousSeamCrossingQuarantine.ReportFailure(200, Crossing, 101, Now.AddMinutes(1)), Is.False,
            "the same bot again does not count twice");
        Assert.That(AutonomousSeamCrossingQuarantine.ReportFailure(200, Crossing, 102, Now.AddMinutes(2)), Is.False);
        Assert.That(AutonomousSeamCrossingQuarantine.IsQuarantined(200, Crossing, Now.AddMinutes(2)), Is.False);
        Assert.That(AutonomousSeamCrossingQuarantine.ReportFailure(200, Crossing, 103, Now.AddMinutes(3)), Is.True);
        Assert.That(AutonomousSeamCrossingQuarantine.IsQuarantined(200, Crossing, Now.AddMinutes(3)), Is.True);
    }

    [Test]
    public void TheBenchCoversNearbyCrossingsOnly()
    {
        AutonomousSeamCrossingQuarantine.Quarantine(200, Crossing, Now);
        Assert.Multiple(() =>
        {
            Assert.That(AutonomousSeamCrossingQuarantine.IsQuarantined(200, new Vector3(385088, 486752, 5493), Now), Is.True,
                "the next listed crossing on the same wall");
            Assert.That(AutonomousSeamCrossingQuarantine.IsQuarantined(200, new Vector3(385088, 491592, 5203), Now), Is.False);
            Assert.That(AutonomousSeamCrossingQuarantine.IsQuarantined(1, Crossing, Now), Is.False, "another region");
        });
    }

    [Test]
    public void TheBenchExpiresAndOldFailuresDoNotAddUp()
    {
        AutonomousSeamCrossingQuarantine.Quarantine(200, Crossing, Now);
        DateTime expired = Now + AutonomousSeamCrossingQuarantine.QuarantineDuration;
        Assert.That(AutonomousSeamCrossingQuarantine.IsQuarantined(200, Crossing, expired), Is.False);

        Vector3 other = new(100000, 100000, 0);
        AutonomousSeamCrossingQuarantine.ReportFailure(200, other, 101, Now);
        AutonomousSeamCrossingQuarantine.ReportFailure(200, other, 102, Now);
        DateTime late = Now + AutonomousSeamCrossingQuarantine.FailureWindow + TimeSpan.FromMinutes(1);
        Assert.That(AutonomousSeamCrossingQuarantine.ReportFailure(200, other, 103, late), Is.False);
    }
}
