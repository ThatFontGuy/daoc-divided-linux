using System.Linq;
using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture]
public sealed class UT_MultipleChants
{
    private static Spell Pulse(int id, string type, int level = 10, int effectGroup = 0, bool focus = false) =>
        new(new DbSpell { SpellID = id, Type = type, Target = "Group", Pulse = 1, Frequency = 60, EffectGroup = effectGroup, IsFocus = focus }, level);

    [Test]
    public void DifferentChantsRunTogether()
    {
        // Paladin endurance chant and damage-add chant; Skald speed song and resist chant.
        Assert.That(EffectListComponent.PulsesConflict(Pulse(1, "EnduranceRegenBuff"), Pulse(2, "DamageAdd"), true), Is.False);
        Assert.That(EffectListComponent.PulsesConflict(Pulse(3, "SpeedEnhancement"), Pulse(4, "BodyResistBuff"), true), Is.False);
    }

    [Test]
    public void SameTypeChantReplacesTheRunningOne() =>
        Assert.That(EffectListComponent.PulsesConflict(Pulse(1, "CombatHeal", 20), Pulse(2, "CombatHeal", 10), true), Is.True);

    [Test]
    public void SharedEffectGroupReplacesTheRunningOne() =>
        Assert.That(EffectListComponent.PulsesConflict(Pulse(1, "BodyResistBuff", effectGroup: 50), Pulse(2, "SpiritResistBuff", effectGroup: 50), true), Is.True);

    [Test]
    public void DifferentEffectGroupsRunTogether() =>
        Assert.That(EffectListComponent.PulsesConflict(Pulse(1, "BodyResistBuff", effectGroup: 50), Pulse(2, "HeatResistBuff", effectGroup: 51), true), Is.False);

    [Test]
    public void OnlyOneFocusSpellRuns()
    {
        Assert.That(EffectListComponent.PulsesConflict(Pulse(1, "FocusShell", focus: true), Pulse(2, "DamageShield", focus: true), true), Is.True);
        Assert.That(EffectListComponent.PulsesConflict(Pulse(3, "DamageAdd"), Pulse(4, "FocusShell", focus: true), true), Is.False);
    }

    [Test]
    public void ClassicRulesKeepOnePulse() =>
        Assert.That(EffectListComponent.PulsesConflict(Pulse(1, "EnduranceRegenBuff"), Pulse(2, "DamageAdd"), false), Is.True);

    [Test]
    public void CapAllowsEightPulsesForMostClassesAndTwelveForSkalds()
    {
        Assert.That(EffectListComponent.MaxPulses((int)eCharacterClass.Paladin), Is.EqualTo(8));
        Assert.That(EffectListComponent.MaxPulses((int)eCharacterClass.Bard), Is.EqualTo(8));
        Assert.That(EffectListComponent.MaxPulses((int)eCharacterClass.Skald), Is.EqualTo(12));
    }

    private static Spell[] Running(int count) =>
        Enumerable.Range(0, count).Select(i => Pulse(100 + i, "DamageAdd", effectGroup: 500 + i)).ToArray();

    [Test]
    public void CapBlocksANewChantOnlyWhenFull()
    {
        Spell incoming = Pulse(1, "SpeedEnhancement");
        Assert.That(EffectListComponent.CanStartPulse(incoming, Running(7), 8), Is.True);
        Assert.That(EffectListComponent.CanStartPulse(incoming, Running(8), 8), Is.False);
        Assert.That(EffectListComponent.CanStartPulse(incoming, Running(8), 12), Is.True);
    }

    [Test]
    public void ReplacingAChantOrRunningFocusSpellsDoNotCountAgainstTheCap()
    {
        Spell[] full = Running(7).Append(Pulse(9, "SpeedEnhancement", 5)).ToArray();
        Assert.That(EffectListComponent.CanStartPulse(Pulse(10, "SpeedEnhancement", 20), full, 8), Is.True, "replaces the running speed song");
        Spell[] withFocus = Running(7).Append(Pulse(11, "FocusShell", focus: true)).ToArray();
        Assert.That(EffectListComponent.CanStartPulse(Pulse(12, "Bladeturn"), withFocus, 8), Is.True);
    }

    [Test]
    public void BotsSkipAChantAlreadyRunningAtThatRankOrHigher()
    {
        Assert.That(BotSongTwistPolicy.KeepsRunning(Pulse(1, "DamageAdd", 20), Pulse(1, "DamageAdd", 20)), Is.True);
        Assert.That(BotSongTwistPolicy.KeepsRunning(Pulse(2, "DamageAdd", 30), Pulse(1, "DamageAdd", 20)), Is.True);
        Assert.That(BotSongTwistPolicy.KeepsRunning(Pulse(1, "DamageAdd", 20), Pulse(2, "DamageAdd", 30)), Is.False);
        Assert.That(BotSongTwistPolicy.KeepsRunning(Pulse(1, "DamageAdd", 20), Pulse(3, "CombatHeal", 20)), Is.False);
    }
}
