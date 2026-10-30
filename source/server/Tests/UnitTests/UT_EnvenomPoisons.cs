using DOL.Database;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>The live assassin poisons: coatings are offensive procs, poison snares grant no immunity, and the weaponskill debuff.</summary>
    [TestFixture]
    public class UT_EnvenomPoisons
    {
        private static Spell Of(eSpellType type) => new(new DbSpell { SpellID = 1, Type = type.ToString(), Target = "Enemy", Value = 60, Duration = 7 }, 1);

        [Test]
        public void CoatingsRunAsOffensiveProcs()
        {
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.PoisonCoating)), Is.EqualTo(eEffect.OffensiveProc));
        }

        [Test]
        public void PoisonSnaresSnareWithoutImmunity()
        {
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.PoisonSnare)), Is.EqualTo(eEffect.MovementSpeedDebuff));
            Assert.That(EffectHelper.GetImmunityEffectFromSpell(Of(eSpellType.PoisonSnare)), Is.EqualTo(eEffect.Unknown));
        }

        [Test]
        public void TheWeaponskillDebuffTouchesOnlyWeaponskill()
        {
            Assert.That(EffectHelper.GetEffectFromSpell(Of(eSpellType.WeaponSkillDebuff)), Is.EqualTo(eEffect.WeaponSkillDebuff));
            Assert.That(EffectHelper.GetPropertiesFromEffect(eEffect.WeaponSkillDebuff), Is.EqualTo(new[] { eProperty.WeaponSkill }));
        }
    }
}
