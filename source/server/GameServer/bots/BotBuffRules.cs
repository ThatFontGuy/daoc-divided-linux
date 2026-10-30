using System;
using System.Collections.Generic;
using DOL.AI.Brain;
using DOL.Database;

namespace DOL.GS;

/// <summary>How much a group member needs a particular buff (docs/BUFF_RULES.md).</summary>
public enum BotBuffNeed
{
    /// <summary>The buff does nothing for this target; never cast it on them.</summary>
    None = 0,
    /// <summary>Given while concentration lasts and taken back first.</summary>
    Optional = 1,
    Required = 2,
}

/// <summary>
/// Who gets which buff, and in what order (docs/BUFF_RULES.md). Pure rules that read only class
/// data, so they are the same for all three realms and for companions and autonomous gamebots.
/// </summary>
public static class BotBuffRules
{
    /// <summary>A long buff is refreshed once less than this is left on it.</summary>
    public const long RefreshWindowMs = 60_000;

    /// <summary>A timed buff this long or longer counts as a long buff.</summary>
    public const long LongBuffMinDurationMs = 300_000;

    // ---- Which buffs are kept up out of combat, and refreshed ----

    /// <summary>
    /// Long buffs (5 min or more, concentration, songs/chants, or untimed) are kept up out of combat;
    /// short timed buffs are not. Speed is kept up while travelling.
    /// </summary>
    public static bool IsMaintainedOutOfCombat(eSpellType spellType, bool isConcentration, bool isPulsing, long durationMs) =>
        spellType == eSpellType.SpeedEnhancement || isConcentration || isPulsing ||
        durationMs <= 0 || durationMs >= LongBuffMinDurationMs;

    /// <summary>A timed long buff with less than a minute left is recast before it runs out.</summary>
    public static bool NeedsRefresh(bool isConcentration, bool isPulsing, long durationMs, long remainingMs) =>
        !isConcentration && !isPulsing && durationMs >= LongBuffMinDurationMs &&
        remainingMs > 0 && remainingMs < RefreshWindowMs;

    // ---- Which member gets which single-target buff ----

    private static bool IsHealerType(eCharacterClass cls) => cls is
        eCharacterClass.Cleric or eCharacterClass.Healer or eCharacterClass.Druid or
        eCharacterClass.Shaman or eCharacterClass.Bard;

    /// <summary>
    /// Base strength: required for players, melee classes, hybrids, Valewalker, Vampiir, Friar, and a
    /// Cleric/Healer/Druid/Shaman/Bard whose highest weapon spec is at least half its level; optional
    /// for caster bots and healing-spec healer bots.
    /// </summary>
    public static BotBuffNeed StrengthNeed(eCharacterClass cls, bool isListCaster, int level, int highestWeaponSpec)
    {
        if (cls is eCharacterClass.Friar or eCharacterClass.Valewalker or eCharacterClass.Vampiir)
            return BotBuffNeed.Required;
        if (IsHealerType(cls))
            return highestWeaponSpec * 2 >= level ? BotBuffNeed.Required : BotBuffNeed.Optional;
        return isListCaster ? BotBuffNeed.Optional : BotBuffNeed.Required;
    }

    /// <summary>
    /// How much a target needs a buff of this type. Acuity counts only for list casters (the server's
    /// StatCalculator adds acuity to a list caster's casting stat only), so nobody else gets it, real
    /// players included. Pets get everything except acuity.
    /// </summary>
    public static BotBuffNeed NeedFor(eSpellType spellType, bool isRealPlayer, bool isPet,
        eCharacterClass cls, bool isListCaster, int level, int highestWeaponSpec)
    {
        if (spellType == eSpellType.AcuityBuff)
            return !isPet && isListCaster ? BotBuffNeed.Required : BotBuffNeed.None;
        if (isPet || isRealPlayer)
            return BotBuffNeed.Required;
        if (spellType == eSpellType.StrengthBuff)
            return StrengthNeed(cls, isListCaster, level, highestWeaponSpec);
        return BotBuffNeed.Required;
    }

    /// <summary>
    /// Target order for one buff: real players, then bots that need it, then bots for whom it is
    /// optional, then pets (pets only once every member in range has it). -1 = never.
    /// </summary>
    public static int TargetTier(bool isRealPlayer, bool isPet, BotBuffNeed need) =>
        need == BotBuffNeed.None ? -1 : isPet ? 3 : isRealPlayer ? 0 : need == BotBuffNeed.Required ? 1 : 2;

    public static bool IsRequiredTier(int tier) => tier is 0 or 1;

    // ---- The order a buffer works through ----

    /// <summary>Spec-line buffs (and acuity) before base-line ones.</summary>
    public static int SpecRank(eSpellType spellType) => spellType switch
    {
        eSpellType.SpecArmorFactorBuff or eSpellType.StrengthConstitutionBuff or
        eSpellType.DexterityQuicknessBuff or eSpellType.AcuityBuff => 0,
        _ => 1,
    };

    /// <summary>
    /// The buffs that jump the queue: a grouped Shaman's endurance regen, speed while travelling,
    /// then the buffer's own dexterity and dexterity/quickness (dexterity shortens every cast).
    /// </summary>
    public static int SpellRank(eSpellType spellType, eCharacterClass casterClass, bool grouped,
        bool traveling, bool targetIsSelf)
    {
        if (spellType == eSpellType.EnduranceRegenBuff && grouped && casterClass == eCharacterClass.Shaman)
            return 0;
        if (spellType == eSpellType.SpeedEnhancement && traveling)
            return 1;
        if (targetIsSelf && spellType == eSpellType.DexterityBuff)
            return 2;
        if (targetIsSelf && spellType == eSpellType.DexterityQuicknessBuff)
            return 3;
        return 4;
    }

    /// <summary>One castable buff and the target it would go to.</summary>
    public readonly record struct Candidate(int SpellRank, int Tier, int SpecRank, double Value, int Level, int SpellId);

    /// <summary>Queue jumpers, then target tier, then spec before base, then stronger, then higher rank.</summary>
    public static readonly IComparer<Candidate> Order = Comparer<Candidate>.Create((a, b) =>
    {
        int c = a.SpellRank.CompareTo(b.SpellRank);
        if (c != 0) return c;
        c = a.Tier.CompareTo(b.Tier);
        if (c != 0) return c;
        c = a.SpecRank.CompareTo(b.SpecRank);
        if (c != 0) return c;
        c = b.Value.CompareTo(a.Value);
        if (c != 0) return c;
        c = b.Level.CompareTo(a.Level);
        return c != 0 ? c : a.SpellId.CompareTo(b.SpellId);
    });

    // ---- Reading the live objects ----

    /// <summary>A real (human) player, as opposed to a companion bot, gamebot or pet.</summary>
    public static bool IsRealPlayer(GameLiving living) => living is GamePlayer;

    /// <summary>A pet or other controlled NPC that is not itself a bot.</summary>
    public static bool IsPet(GameLiving living) =>
        living is GameNPC npc && npc is not GameBot && npc.Brain is IControlledBrain;

    /// <summary>Highest weapon spec a bot has in the weapons it carries.</summary>
    public static int HighestWeaponSpec(GameLiving living)
    {
        if (living is not GameBot bot || bot.Inventory == null)
            return 0;
        int best = 0;
        foreach (eInventorySlot slot in WeaponSlots)
        {
            DbInventoryItem item = bot.Inventory.GetItem(slot);
            if (item != null)
                best = Math.Max(best, bot.WeaponSpecLevel(item));
        }
        return best;
    }

    private static readonly eInventorySlot[] WeaponSlots =
    [
        eInventorySlot.RightHandWeapon, eInventorySlot.LeftHandWeapon,
        eInventorySlot.TwoHandWeapon, eInventorySlot.DistanceWeapon,
    ];

    public static BotBuffNeed NeedFor(Spell spell, GameLiving target)
    {
        if (spell == null || target == null)
            return BotBuffNeed.None;
        bool pet = IsPet(target);
        bool player = IsRealPlayer(target);
        // Only acuity (everyone) and base strength (bots) depend on the class; skip the lookup otherwise.
        bool classMatters = spell.SpellType == eSpellType.AcuityBuff ||
                            spell.SpellType == eSpellType.StrengthBuff && !player && !pet;
        if (pet || !classMatters)
            return NeedFor(spell.SpellType, player, pet, eCharacterClass.Unknown, false, target.Level, 0);
        ICharacterClass characterClass = target switch
        {
            GamePlayer gamePlayer => gamePlayer.CharacterClass,
            GameBot gameBot => gameBot.CharacterClass,
            _ => null,
        };
        if (characterClass == null)
            return spell.SpellType == eSpellType.AcuityBuff ? BotBuffNeed.None : BotBuffNeed.Required;
        eCharacterClass cls = (eCharacterClass)characterClass.ID;
        bool isListCaster = characterClass.ClassType == eClassType.ListCaster;
        // Weapon spec only matters for a healer bot's strength.
        int weaponSpec = spell.SpellType == eSpellType.StrengthBuff && IsHealerType(cls) ? HighestWeaponSpec(target) : 0;
        return NeedFor(spell.SpellType, player, pet, cls, isListCaster, target.Level, weaponSpec);
    }

    public static int TargetTier(Spell spell, GameLiving target) =>
        TargetTier(IsRealPlayer(target), IsPet(target), NeedFor(spell, target));
}
