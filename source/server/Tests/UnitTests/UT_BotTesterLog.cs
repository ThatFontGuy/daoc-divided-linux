using System.IO;
using System.Linq;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture, NonParallelizable]
public sealed class UT_BotTesterLog
{
    private static BotTesterLog.SkillStats Skill(string kind = "spell", double listedDamage = 0) => new()
    {
        Kind = kind, ClassId = 21, Id = 1000, Name = "Test Skill", Type = "DirectDamage", Level = 10,
        Harmful = true, ListedDamage = listedDamage
    };

    private static BotTesterLog.Finding[] Findings(BotTesterLog.SkillStats skill) =>
        BotTesterLog.FindingsFor([skill], _ => "Thane").ToArray();

    [Test]
    public void AlwaysRefusedSpellIsHighWithTheGameMessage()
    {
        var skill = Skill();
        skill.Refused = 6;
        skill.Reason("You must wait 5 seconds to cast again.");
        BotTesterLog.Finding finding = Findings(skill).Single();
        Assert.That(finding.Severity, Is.EqualTo("high"));
        Assert.That(finding.Problem, Does.Contain("always refused"));
        Assert.That(finding.Detail, Does.Contain("You must wait"));
    }

    [Test]
    public void DamageSpellThatNeverDealsDamageIsFlagged()
    {
        var skill = Skill(listedDamage: 40);
        skill.Casts = 8;
        skill.Hits = 8;
        Assert.That(Findings(skill).Select(f => f.Problem), Has.Some.Contains("0 damage"));
    }

    [Test]
    public void HealthyDamageSpellHasNoFindings()
    {
        var skill = Skill(listedDamage: 40);
        skill.Casts = 30;
        skill.Hits = 30;
        skill.Damage = 3000;
        skill.Refused = 2;
        skill.KnownBy.TryAdd("bot", 0);
        Assert.That(Findings(skill), Is.Empty);
    }

    [Test]
    public void StyleWhoseRequirementsAlwaysFailIsFlagged()
    {
        var style = Skill("style");
        style.Failed = 12;
        style.Reason("needs Back position");
        Assert.That(Findings(style).Single().Problem, Does.Contain("style never executed"));
    }

    [Test]
    public void KnownButNeverTriedIsInfo()
    {
        var skill = Skill();
        skill.KnownBy.TryAdd("bot-a", 0);
        skill.KnownBy.TryAdd("bot-b", 0);
        BotTesterLog.Finding finding = Findings(skill).Single();
        Assert.That(finding.Severity, Is.EqualTo("info"));
        Assert.That(finding.Problem, Does.Contain("known by 2"));
        Assert.That(finding.Detail, Does.Contain("never considered"), "no skip recorded means the AI never looked at it");
    }

    [Test]
    public void NeverTriedSpellShowsWhyTheAiSkippedIt()
    {
        var skill = Skill();
        skill.KnownBy.TryAdd("bot-a", 0);
        skill.Skip("instant: spell type not used by the bot attack AI");
        skill.Skip("instant: spell type not used by the bot attack AI");
        skill.Skip("instant: on cooldown");
        BotTesterLog.Finding finding = Findings(skill).Single();
        Assert.That(finding.Detail, Does.StartWith("skipped: instant: spell type not used by the bot attack AI x2"));
    }

    [Test]
    public void MostlyResistedSpellIsMedium()
    {
        var skill = Skill();
        skill.Casts = 20;
        skill.Negated = 19;
        Assert.That(Findings(skill).Single(f => f.Problem.Contains("resisted")).Severity, Is.EqualTo("medium"));
    }

    [Test]
    public void PulsingDamageSpellResistedOnEveryPulseIsHigh()
    {
        // Arawn's Singe in the first soak: 98 casts, 348 resisted pulses, no hits.
        var skill = Skill(listedDamage: 20);
        skill.Casts = 98;
        skill.Negated = 348;
        BotTesterLog.Finding finding = Findings(skill).Single(f => f.Problem.Contains("resisted"));
        Assert.That(finding.Severity, Is.EqualTo("high"));
        Assert.That(finding.Problem, Does.Contain("348 of 348"));
    }

    [Test]
    public void CrowdControlThatLandsIsNotReportedAsAlwaysResisted()
    {
        // Wasting Disease, pet stuns and disarms never deal damage: before landings were counted,
        // the 12.5% of procs that were resisted were the only thing recorded, so they looked 100% resisted.
        var skill = Skill();
        skill.Type = "Disease";
        skill.Negated = 312;
        skill.Landed = 2200;
        Assert.That(Findings(skill).Where(f => f.Problem.Contains("resisted")), Is.Empty);
        skill.Landed = 0;
        Assert.That(Findings(skill).Single(f => f.Problem.Contains("resisted")).Problem, Does.Contain("312 of 312 attempts to land (0 landed"));
    }

    [Test]
    public void HooksIgnoreNonBotsAndNulls()
    {
        Assert.That(BotTesterLog.Resolve(null, out bool pet), Is.Null);
        Assert.That(pet, Is.False);
        Assert.DoesNotThrow(() =>
        {
            BotTesterLog.SpellMessage(null, null, "message");
            BotTesterLog.CastRefused(null);
            BotTesterLog.StyleExecuted(null, null, false, 0);
            BotTesterLog.ServiceException("Test", null, new System.Exception("x"));
            BotTesterLog.Died(null, null);
        });
    }

    [Test]
    public void ReportFilesAreWritten()
    {
        BotTesterLog.Reset();
        BotTesterLog.WriteReport();
        Assert.That(File.Exists(Path.Combine(BotTesterLog.Folder, "REPORT.txt")), Is.True);
        Assert.That(File.ReadAllText(Path.Combine(BotTesterLog.Folder, "summary-latest.json")), Does.Contain("\"findings\""));
    }
}
