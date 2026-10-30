using System;

namespace DOL.GS.PropertyCalc
{
    /// <summary>
    /// Item bonus caps shared by the property calculators and the /bonuses display.
    /// With `modern_item_bonuses` off every value matches the classic ToA rules.
    /// Modern values are the 1.126+ live caps at level 50, scaled by level the same way the classic ones are.
    /// </summary>
    public static class ModernItemBonusRules
    {
        public const int MythicalRegenCap = 50;
        public const int MythicalCrowdControlCap = 25;
        public const int ItemDpsCap = 10;
        public const int ConversionItemCap = 10;

        public static bool Enabled => ServerProperties.Properties.MODERN_ITEM_BONUSES;

        public static bool IsPlayerLike(GameLiving living)
        {
            return living is GamePlayer or IGamePlayer;
        }

        /// <summary>Hits cap increase: 200 classic, 400 modern at level 50.</summary>
        public static int MaxHealthCapIncreaseCap(GameLiving living)
        {
            if (living == null)
                return 0;

            return living.Level * (Enabled ? 8 : 4);
        }

        /// <summary>Resist cap increase per damage type: 5 classic, 15 modern.</summary>
        public static int ResistCapIncreaseCap => Enabled ? 15 : 5;

        /// <summary>Flat power bonus: 26 classic, 25 modern at level 50.</summary>
        public static int FlatPowerCap(GameLiving living)
        {
            return Enabled ? living.Level / 2 : living.Level / 2 + 1;
        }

        /// <summary>Power pool cap increase: up to the level classic (75% pool), 25 modern (50% pool) at level 50.</summary>
        public static int PowerPoolCapIncreaseCap(GameLiving living)
        {
            return Enabled ? living.Level / 2 : living.Level;
        }

        /// <summary>Mythical regen added to every regen tick. Retail never published its formula; this server adds it flat per tick.</summary>
        public static int MythicalRegen(GameLiving living, eProperty regenProperty)
        {
            if (!Enabled || !IsPlayerLike(living))
                return 0;

            eProperty mythical = regenProperty switch
            {
                eProperty.HealthRegenerationAmount => eProperty.MythicalHealthRegen,
                eProperty.PowerRegenerationAmount => eProperty.MythicalPowerRegen,
                eProperty.EnduranceRegenerationAmount => eProperty.MythicalEnduranceRegen,
                _ => eProperty.Undefined
            };

            if (mythical is eProperty.Undefined)
                return 0;

            // Vampiirs and Maulers build power in combat; item regen must not fill it.
            if (mythical is eProperty.MythicalPowerRegen && UsesCombatPower(living))
                return 0;

            return Math.Clamp(living.ItemBonus[mythical], 0, MythicalRegenCap);
        }

        /// <summary>
        /// Applies the mythical crowd control layer to an already reduced duration percent.
        /// It is multiplicative and comes after Determination, Stoicism and dampen.
        /// </summary>
        public static int ApplyMythicalCrowdControl(GameLiving living, int durationPercent)
        {
            if (!Enabled || !IsPlayerLike(living))
                return durationPercent;

            int reduction = Math.Clamp(living.ItemBonus[eProperty.MythicalCrowdControlReduction], 0, MythicalCrowdControlCap);
            return Math.Max(1, (int) (durationPercent * (100 - reduction) * 0.01));
        }

        /// <summary>Mythical physical defense adds to crush, slash and thrust resists and their caps.</summary>
        public static int MythicalPhysicalDefense(GameLiving living, eProperty resist)
        {
            if (!Enabled || resist is not (eProperty.Resist_Crush or eProperty.Resist_Slash or eProperty.Resist_Thrust))
                return 0;

            return Math.Max(0, living.ItemBonus[eProperty.MythicalPhysicalDefense]);
        }

        /// <summary>
        /// Cap for the 10% item bonuses (melee/spell/style/ranged damage, melee/casting speed, ranges).
        /// Modern rules scale it with level like the live game (level / 5, so 7% at 39); classic keeps a flat 10.
        /// </summary>
        public static int PercentCap10(GameLiving living)
        {
            return Enabled ? Math.Clamp(living.Level / 5, 1, 10) : 10;
        }

        /// <summary>Cap for the 25% item bonuses (buff, debuff, healing, duration, Arcane Syphon): level / 2 with the modern rules.</summary>
        public static int PercentCap25(GameLiving living)
        {
            return Enabled ? Math.Clamp(living.Level / 2, 1, 25) : 25;
        }

        /// <summary>
        /// Modern archery: a bow also uses the item casting speed, sharing one item cap with archery speed.
        /// Returns what archery speed adds on top of the casting speed already in GetModified(CastingSpeed).
        /// </summary>
        public static int BowSpeedAlias(GameLiving living)
        {
            return SharedCapExtra(living, eProperty.CastingSpeed, eProperty.ArcherySpeed);
        }

        /// <summary>Modern archery: bow damage also uses the item spell damage, sharing one item cap with archery damage.</summary>
        public static int BowDamageAlias(GameLiving living)
        {
            return SharedCapExtra(living, eProperty.RangedDamage, eProperty.SpellDamage);
        }

        private static int SharedCapExtra(GameLiving living, eProperty counted, eProperty alias)
        {
            if (!Enabled || !IsPlayerLike(living))
                return 0;

            int cap = PercentCap10(living);
            int countedBonus = Math.Clamp(living.ItemBonus[counted], 0, cap);
            int sharedBonus = Math.Clamp(living.ItemBonus[counted] + living.ItemBonus[alias], 0, cap);
            return sharedBonus - countedBonus;
        }

        public static int ItemDps(GameLiving living)
        {
            if (!Enabled || !IsPlayerLike(living))
                return 0;

            return Math.Clamp(living.ItemBonus[eProperty.DPS], 0, ItemDpsCap);
        }

        public static int ConversionItemBonus(GameLiving living)
        {
            int itemBonus = living.ItemBonus[eProperty.Conversion];
            return Enabled ? Math.Min(itemBonus, ConversionItemCap) : itemBonus;
        }

        private static bool UsesCombatPower(GameLiving living)
        {
            ICharacterClass characterClass = living switch
            {
                GamePlayer player => player.CharacterClass,
                IGamePlayer bot => bot.CharacterClass,
                _ => null
            };

            return characterClass?.ID is (int) eCharacterClass.Vampiir or (int) eCharacterClass.MaulerAlb or (int) eCharacterClass.MaulerMid or (int) eCharacterClass.MaulerHib;
        }
    }
}
