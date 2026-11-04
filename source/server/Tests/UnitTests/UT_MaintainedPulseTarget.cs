using DOL.AI;
using DOL.AI.Brain;
using DOL.Database;
using NUnit.Framework;

namespace DOL.GS.Tests;

/// <summary>
/// Overnight run 2026-11-01: Vampiirs froze "in combat" with nothing near them, because a maintained
/// pulse never ended and each pulse on its far-away target put the caster back in combat.
/// </summary>
[TestFixture]
public sealed class UT_MaintainedPulseTarget
{
    private static Spell Pulse(eSpellType type, string target = "Enemy", int range = 700, int radius = 0, bool focus = false) => new(new DbSpell
    {
        Type = type.ToString(), Target = target, Range = range, Radius = radius, Pulse = 1, Frequency = 50, Duration = 10, IsFocus = focus,
    }, 30);

    [Test]
    public void VampiirSnareAndSensesDebuffAreMaintainedOnOneTarget()
    {
        Assert.That(EffectService.IsMaintainedOnOneTarget(Pulse(eSpellType.VampSpeedDecrease)), Is.True);
        Assert.That(EffectService.IsMaintainedOnOneTarget(Pulse(eSpellType.VampiirEffectivenessDeBuff, range: 500)), Is.True);
    }

    [Test]
    public void OtherPulsesKeepTheirOwnRules()
    {
        Assert.That(EffectService.IsMaintainedOnOneTarget(Pulse(eSpellType.SpeedDecrease, focus: true)), Is.False, "focus spells end through StartSpell");
        Assert.That(EffectService.IsMaintainedOnOneTarget(Pulse(eSpellType.Charm)), Is.False, "a charm song follows its pet");
        Assert.That(EffectService.IsMaintainedOnOneTarget(Pulse(eSpellType.Mesmerize)), Is.False);
        Assert.That(EffectService.IsMaintainedOnOneTarget(Pulse(eSpellType.DirectDamage, range: 0, radius: 350)), Is.False, "a Reaver's aura");
        Assert.That(EffectService.IsMaintainedOnOneTarget(Pulse(eSpellType.SpeedEnhancement, "Group", 0, 2000)), Is.False, "a speed song");

        Spell notPulsing = new(new DbSpell { Type = eSpellType.DirectDamage.ToString(), Target = "Enemy", Range = 1500 }, 30);
        Assert.That(EffectService.IsMaintainedOnOneTarget(notPulsing), Is.False);
    }

    [TestCase(true, true, true, false, TestName = "Live target in range keeps the pulse")]
    [TestCase(false, true, true, true, TestName = "A kill ends the pulse before the monster respawns")]
    [TestCase(true, false, true, true, TestName = "A target taken out of the world ends the pulse")]
    [TestCase(true, true, false, true, TestName = "Leaving range or region ends the pulse")]
    public void MaintainedPulseEndsWithItsTarget(bool alive, bool active, bool inRange, bool gone) =>
        Assert.That(EffectService.MaintainedTargetGone(alive, active, inRange), Is.EqualTo(gone));

    [Test]
    public void BotFsmResumesAfterTheBrainRestarts()
    {
        BotBrain brain = new();

        // What ABrain.Stop does on every MoveTo; the FSM used to be left with no state at all.
        brain.FSM.SetCurrentState(eFSMStateType.WAKING_UP);
        Assert.That(brain.FSM.GetCurrentState()?.StateType, Is.EqualTo(eFSMStateType.WAKING_UP));

        brain.FSM.Think();
        Assert.That(brain.FSM.GetCurrentState()?.StateType, Is.EqualTo(eFSMStateType.IDLE));
    }
}
