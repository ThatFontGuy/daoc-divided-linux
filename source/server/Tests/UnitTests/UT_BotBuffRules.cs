using System.Collections.Generic;
using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests;

/// <summary>docs/BUFF_RULES.md: who gets which buff, and in what order.</summary>
[TestFixture]
public class UT_BotBuffRules
{
    private static BotBuffNeed Need(eSpellType type, eCharacterClass cls, bool listCaster,
        bool player = false, bool pet = false, int level = 50, int weaponSpec = 0) =>
        BotBuffRules.NeedFor(type, player, pet, cls, listCaster, level, weaponSpec);

    [Test]
    public void AcuityOnlyForListCasters()
    {
        Assert.That(Need(eSpellType.AcuityBuff, eCharacterClass.Wizard, listCaster: true), Is.EqualTo(BotBuffNeed.Required));
        Assert.That(Need(eSpellType.AcuityBuff, eCharacterClass.Cleric, listCaster: false), Is.EqualTo(BotBuffNeed.None));
        Assert.That(Need(eSpellType.AcuityBuff, eCharacterClass.Armsman, listCaster: false), Is.EqualTo(BotBuffNeed.None));
        Assert.That(Need(eSpellType.AcuityBuff, eCharacterClass.Paladin, listCaster: false, player: true), Is.EqualTo(BotBuffNeed.None),
            "a real player only gets buffs that have an effect");
        Assert.That(Need(eSpellType.AcuityBuff, eCharacterClass.Unknown, listCaster: false, pet: true), Is.EqualTo(BotBuffNeed.None),
            "acuity is player-only");
    }

    [Test]
    public void BaseStrengthRequiredForFightersOptionalForCasterBots()
    {
        Assert.That(Need(eSpellType.StrengthBuff, eCharacterClass.Armsman, false), Is.EqualTo(BotBuffNeed.Required));
        Assert.That(Need(eSpellType.StrengthBuff, eCharacterClass.Friar, false), Is.EqualTo(BotBuffNeed.Required));
        Assert.That(Need(eSpellType.StrengthBuff, eCharacterClass.Valewalker, true), Is.EqualTo(BotBuffNeed.Required));
        Assert.That(Need(eSpellType.StrengthBuff, eCharacterClass.Vampiir, true), Is.EqualTo(BotBuffNeed.Required));
        Assert.That(Need(eSpellType.StrengthBuff, eCharacterClass.Wizard, true), Is.EqualTo(BotBuffNeed.Optional));
        Assert.That(Need(eSpellType.StrengthBuff, eCharacterClass.Wizard, true, player: true), Is.EqualTo(BotBuffNeed.Required),
            "real players always get strength");
        Assert.That(Need(eSpellType.StrengthBuff, eCharacterClass.Unknown, false, pet: true), Is.EqualTo(BotBuffNeed.Required));
    }

    [TestCase(24, BotBuffNeed.Optional)]
    [TestCase(25, BotBuffNeed.Required)]
    [TestCase(50, BotBuffNeed.Required)]
    public void HealerStrengthDependsOnWeaponSpec(int weaponSpec, BotBuffNeed expected)
    {
        foreach (eCharacterClass healer in new[] { eCharacterClass.Cleric, eCharacterClass.Healer,
                     eCharacterClass.Druid, eCharacterClass.Shaman, eCharacterClass.Bard })
            Assert.That(Need(eSpellType.StrengthBuff, healer, false, level: 50, weaponSpec: weaponSpec), Is.EqualTo(expected), healer.ToString());
    }

    [Test]
    public void OtherBuffsGoToEveryone()
    {
        foreach (eSpellType type in new[] { eSpellType.ConstitutionBuff, eSpellType.DexterityBuff,
                     eSpellType.StrengthConstitutionBuff, eSpellType.DexterityQuicknessBuff,
                     eSpellType.BaseArmorFactorBuff, eSpellType.SpecArmorFactorBuff, eSpellType.HealthRegenBuff })
        {
            Assert.That(Need(type, eCharacterClass.Wizard, true), Is.EqualTo(BotBuffNeed.Required), type.ToString());
            Assert.That(Need(type, eCharacterClass.Cleric, false), Is.EqualTo(BotBuffNeed.Required), type.ToString());
        }
    }

    [Test]
    public void TargetTiers()
    {
        Assert.That(BotBuffRules.TargetTier(true, false, BotBuffNeed.Required), Is.EqualTo(0));
        Assert.That(BotBuffRules.TargetTier(false, false, BotBuffNeed.Required), Is.EqualTo(1));
        Assert.That(BotBuffRules.TargetTier(false, false, BotBuffNeed.Optional), Is.EqualTo(2));
        Assert.That(BotBuffRules.TargetTier(false, true, BotBuffNeed.Required), Is.EqualTo(3), "pets come after every member");
        Assert.That(BotBuffRules.TargetTier(true, false, BotBuffNeed.None), Is.EqualTo(-1));
        Assert.That(BotBuffRules.IsRequiredTier(0) && BotBuffRules.IsRequiredTier(1), Is.True);
        Assert.That(BotBuffRules.IsRequiredTier(2) || BotBuffRules.IsRequiredTier(3), Is.False);
    }

    [Test]
    public void QueueJumpers()
    {
        Assert.That(BotBuffRules.SpellRank(eSpellType.EnduranceRegenBuff, eCharacterClass.Shaman, true, false, false), Is.EqualTo(0));
        Assert.That(BotBuffRules.SpellRank(eSpellType.EnduranceRegenBuff, eCharacterClass.Shaman, false, false, false), Is.EqualTo(4),
            "only a grouped Shaman");
        Assert.That(BotBuffRules.SpellRank(eSpellType.EnduranceRegenBuff, eCharacterClass.Cleric, true, false, false), Is.EqualTo(4));
        Assert.That(BotBuffRules.SpellRank(eSpellType.SpeedEnhancement, eCharacterClass.Bard, true, true, false), Is.EqualTo(1));
        Assert.That(BotBuffRules.SpellRank(eSpellType.DexterityBuff, eCharacterClass.Cleric, true, false, true), Is.EqualTo(2));
        Assert.That(BotBuffRules.SpellRank(eSpellType.DexterityQuicknessBuff, eCharacterClass.Cleric, true, false, true), Is.EqualTo(3));
        Assert.That(BotBuffRules.SpellRank(eSpellType.DexterityBuff, eCharacterClass.Cleric, true, false, false), Is.EqualTo(4),
            "dex on someone else is an ordinary buff");
    }

    [Test]
    public void OrderPutsPlayersThenRequiredThenOptionalThenPetsThenSpecThenStrength()
    {
        var list = new List<BotBuffRules.Candidate>
        {
            new(4, 3, 0, 50, 50, 1),   // pet
            new(4, 2, 0, 50, 50, 2),   // optional bot
            new(4, 1, 1, 90, 50, 3),   // required bot, base buff, stronger
            new(4, 1, 0, 40, 40, 4),   // required bot, spec buff
            new(4, 0, 1, 10, 10, 5),   // real player, weak base buff
            new(2, 1, 1, 10, 10, 6),   // own dexterity
            new(4, 1, 0, 40, 45, 7),   // required bot, spec buff, higher rank
        };
        list.Sort(BotBuffRules.Order);
        Assert.That(list.ConvertAll(c => c.SpellId), Is.EqualTo(new List<int> { 6, 5, 7, 4, 3, 2, 1 }));
    }

    [Test]
    public void SpecBeforeBase()
    {
        Assert.That(BotBuffRules.SpecRank(eSpellType.StrengthConstitutionBuff), Is.EqualTo(0));
        Assert.That(BotBuffRules.SpecRank(eSpellType.DexterityQuicknessBuff), Is.EqualTo(0));
        Assert.That(BotBuffRules.SpecRank(eSpellType.SpecArmorFactorBuff), Is.EqualTo(0));
        Assert.That(BotBuffRules.SpecRank(eSpellType.StrengthBuff), Is.EqualTo(1));
        Assert.That(BotBuffRules.SpecRank(eSpellType.BaseArmorFactorBuff), Is.EqualTo(1));
    }

    [Test]
    public void OnlyLongBuffsAreKeptUpOutOfCombat()
    {
        Assert.That(BotBuffRules.IsMaintainedOutOfCombat(eSpellType.StrengthBuff, false, false, 20 * 60_000), Is.True);
        Assert.That(BotBuffRules.IsMaintainedOutOfCombat(eSpellType.StrengthBuff, false, false, 300_000), Is.True);
        Assert.That(BotBuffRules.IsMaintainedOutOfCombat(eSpellType.StrengthBuff, true, false, 0), Is.True, "concentration");
        Assert.That(BotBuffRules.IsMaintainedOutOfCombat(eSpellType.Buff, false, true, 6_000), Is.True, "songs and chants");
        Assert.That(BotBuffRules.IsMaintainedOutOfCombat(eSpellType.CelerityBuff, false, false, 60_000), Is.False);
        Assert.That(BotBuffRules.IsMaintainedOutOfCombat(eSpellType.DamageAdd, false, false, 299_999), Is.False);
        Assert.That(BotBuffRules.IsMaintainedOutOfCombat(eSpellType.SpeedEnhancement, false, false, 60_000), Is.True,
            "travel speed (its own rule decides when)");
    }

    [Test]
    public void LongTimedBuffsRefreshInTheLastMinute()
    {
        Assert.That(BotBuffRules.NeedsRefresh(false, false, 20 * 60_000, 59_999), Is.True);
        Assert.That(BotBuffRules.NeedsRefresh(false, false, 20 * 60_000, 60_000), Is.False);
        Assert.That(BotBuffRules.NeedsRefresh(false, false, 20 * 60_000, 0), Is.False, "already gone: the missing-buff check covers it");
        Assert.That(BotBuffRules.NeedsRefresh(true, false, 20 * 60_000, 1_000), Is.False, "concentration never expires");
        Assert.That(BotBuffRules.NeedsRefresh(false, true, 20 * 60_000, 1_000), Is.False);
        Assert.That(BotBuffRules.NeedsRefresh(false, false, 120_000, 1_000), Is.False, "short buffs are not refreshed");
    }
}
