using DOL.Database;
using DOL.GS;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>The follow-up live effects: totem areas, Helping Hand, Track, Champion's Call and totem snares.</summary>
    [TestFixture]
    public class UT_LiveClassEffects
    {
        [Test]
        public void EffectLookupsAreEmptyWithoutAnOwner()
        {
            Assert.That(HelpingHandSpellHandler.HealFor(null), Is.Zero);
            Assert.That(TrackStealthSpellHandler.Bonus(null), Is.Zero);
            Assert.That(MeleeDamageTypeAuraSpellHandler.For(null), Is.Null);
            Assert.That(UninterruptibleAuraSpellHandler.Protects(null), Is.False);
        }

        [Test]
        public void TotemSnaresGrantNoImmunityButOrdinarySnaresDo()
        {
            Spell Of(eSpellType type) => new(new DbSpell { SpellID = 1, Type = type.ToString(), Target = "Enemy", Value = 75, Duration = 3 }, 1);
            Assert.That(EffectHelper.GetImmunityEffectFromSpell(Of(eSpellType.TotemSnare)), Is.EqualTo(eEffect.Unknown));
            Assert.That(EffectHelper.GetImmunityEffectFromSpell(Of(eSpellType.SpeedDecrease)), Is.EqualTo(eEffect.SnareImmunity));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.TotemSnare)), Is.EqualTo(eEffect.MovementSpeedDebuff));
        }

        [Test]
        public void ChantsAndSavageResistsMapToTheirEffects()
        {
            Spell Of(eSpellType type) => new(new DbSpell { SpellID = 1, Type = type.ToString(), Target = "Group", Value = 6, Duration = 6 }, 1);
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.HealthArmorChant)), Is.EqualTo(eEffect.HealthArmorChant));
            Assert.That(HealthArmorChantSpellHandler.Scale(null), Is.EqualTo(1.0));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.SavageMeleeResistanceBuff)), Is.EqualTo(eEffect.SavageBuff));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.AllMeleeResistsBuff)), Is.EqualTo(eEffect.AllMeleeResistsBuff));
        }

        [Test]
        public void SecondGapPassEffectsMapAndAreEmptyWithoutAnOwner()
        {
            Spell Of(eSpellType type) => new(new DbSpell { SpellID = 1, Type = type.ToString(), Target = "Enemy", Value = 50, Duration = 10 }, 1);
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.SpellDamageDebuff)), Is.EqualTo(eEffect.SpellDamageDebuff));
            Assert.That(EffectHelper.GetPropertiesFromEffect(eEffect.SpellDamageDebuff), Is.EqualTo(new[] { eProperty.SpellDamage }));
            Assert.That(EffectHelper.GetPropertiesFromEffect(eEffect.PowerCostDebuff), Is.EqualTo(new[] { eProperty.SpellPowerCost }));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.CrushSlashThrustDebuff)), Is.EqualTo(eEffect.AllMeleeResistsDebuff));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.StealthDetectionAura)), Is.EqualTo(eEffect.StealthDetectionAura));
            Assert.That(PowerCostDebuff.Scale(null), Is.EqualTo(1.0));
            Assert.That(DamageReductionSpellHandler.Percent(null), Is.Zero);
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.StaffSkillBuff)), Is.EqualTo(eEffect.StaffSkillBuff));
            Assert.That(EffectHelper.GetPropertiesFromEffect(eEffect.StaffSkillBuff), Is.EqualTo(new[] { eProperty.Skill_Staff }));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.HealingReceivedBuff)), Is.EqualTo(eEffect.HealingReceivedBuff));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.HealingDoneBuff)), Is.EqualTo(eEffect.HealingDoneBuff));
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.SpellCritAura)), Is.EqualTo(eEffect.SpellCritAura));
            Assert.That(HealingReceivedBuffSpellHandler.Percent(null) + HealingDoneBuffSpellHandler.Percent(null) +
                        SpellCritAuraSpellHandler.Percent(null), Is.Zero);
        }

        [Test]
        public void TotemCentresAreDistinct()
        {
            Assert.That(new[] { TimedPulseAreaSpellHandler.FOLLOW, TimedPulseAreaSpellHandler.TARGET, TimedPulseAreaSpellHandler.FEET,
                                TimedPulseAreaSpellHandler.PHANTOM }, Is.Unique);
        }
    }
}
