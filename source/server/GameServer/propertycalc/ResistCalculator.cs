using System;

namespace DOL.GS.PropertyCalc
{
    [PropertyCalculator(eProperty.Resist_Natural)]
    [PropertyCalculator(eProperty.Resist_First, eProperty.Resist_Last)]
    public class ResistCalculator : PropertyCalculator
    {
        public ResistCalculator() { }

        public override int CalcValue(GameLiving living, eProperty property)
        {
            return CalcValueInternal(living, property, false);
        }

        public override int CalcValueBase(GameLiving living, eProperty property)
        {
            return CalcValueInternal(living, property, true);
        }

        private int CalcValueInternal(GameLiving living, eProperty property, bool forCrowdControlDuration)
        {
            // Necromancer pets receive resistances from Avoidance of Magic and other active RAs.
            GameLiving livingToCheck;

            if (living is NecromancerPet necroPet && necroPet.Owner is GamePlayer or IGamePlayer)
                livingToCheck = necroPet.Owner;
            else
                livingToCheck = living;

            int itemBonus = CalcValueFromItems(living, property);
            int abilityBonus = livingToCheck.AbilityBonus[property]; // Applied as secondary resists.

            // Ability bonuses are taken into account for crowd control duration unless they're put in `OtherBonus`.
            if (!forCrowdControlDuration)
                abilityBonus += livingToCheck.OtherBonus[property];

            int racialBonus = SkillBase.GetRaceResist(living.Race, (eResist) property);
            int buffBonus = CalcValueFromBuffs(living, property);

            int result = itemBonus + buffBonus; // Primary resists.
            result += (int) ((1 - result * 0.01) * abilityBonus); // Secondary resists.

            // Treat NPC resists from constitution buffs as another layer of resists for now.
            if (living is GameNPC)
            {
                double resistanceFromConstitution = StatCalculator.CalculateBuffContributionToAbsorbOrResist(living, eProperty.Constitution) / 8 * 100;
                result += (int) ((1 - result * 0.01) * resistanceFromConstitution);
            }

            // http://www.postcount.net/forum/showthread.php?192979-Primary-Secondary-and-Tertiary-resist-graphs-plus-racial-resist-oddities
            result += racialBonus;
            return Math.Min(result, HardCap);
        }

        /// <summary>
        /// Calculate modified resists from buffs and debuffs.
        /// </summary>
        public override int CalcValueFromBuffs(GameLiving living, eProperty property)
        {
            GameLiving livingToCheck;

            if (living is NecromancerPet necroPet && necroPet.Owner is GamePlayer or IGamePlayer)
                livingToCheck = necroPet.Owner;
            else
                livingToCheck = living;

            int buff = living.BaseBuffBonusCategory[property] + living.SpecBuffBonusCategory[property];
            // A bot-owned servant has the same cap as a player-owned servant.
            // Do not change ordinary NPC or other bot-class calculations here.
            bool playerOwnedServant = living is NecromancerPet { Owner: GamePlayer or IGamePlayer };
            buff = livingToCheck is GameNPC && !playerOwnedServant ? buff : Math.Min(buff, BuffBonusCap);
            int debuff = Math.Abs(living.DebuffCategory[property]) + Math.Abs(living.SpecDebuffCategory[property]);
            buff -= debuff;

            if (buff < 0 && living is GamePlayer)
                buff /= 2;

            return buff;
        }

        /// <summary>
        /// Calculate modified resists from items only.
        /// </summary>
        public override int CalcValueFromItems(GameLiving living, eProperty property)
        {
            // Necromancer pets receive resistances from their owner's items.
            GameLiving livingToCheck;

            if (living is NecromancerPet necroPet && necroPet.Owner is GamePlayer or IGamePlayer)
                livingToCheck = necroPet.Owner;
            else
                livingToCheck = living;

            // NPC-backed bots wear real gear and get its resists, like players.
            if (livingToCheck is GameNPC && livingToCheck is not IGamePlayer && living is not NecromancerPet { Owner: GamePlayer or IGamePlayer })
                return 0;

            int itemBonus = livingToCheck.ItemBonus[property] + ModernItemBonusRules.MythicalPhysicalDefense(livingToCheck, property);

            // Item bonus cap and cap increase from Mythirians.
            int itemBonusCap = livingToCheck.Level / 2 + 1;
            int itemBonusCapIncrease = GetItemBonusCapIncrease(livingToCheck, property);

            return Math.Min(itemBonus, itemBonusCap + itemBonusCapIncrease);
        }

        /// <summary>
        /// Returns the resist cap increase for the given living and the given
        /// resist type: 5% with the classic rules, 15% with the modern ones.
        /// </summary>
        public static int GetItemBonusCapIncrease(GameLiving living, eProperty property)
        {
            if (living == null)
                return 0;

            int capIncrease = living.ItemBonus[eProperty.ResCapBonus_First - eProperty.Resist_First + property];
            capIncrease += ModernItemBonusRules.MythicalPhysicalDefense(living, property);
            return Math.Min(capIncrease, ModernItemBonusRules.ResistCapIncreaseCap);
        }

        /// <summary>
        /// Cap for player cast resist buffs.
        /// </summary>
        public static int BuffBonusCap => 24;

        /// <summary>
        /// Hard cap for resists.
        /// </summary>
        public static int HardCap => 70;
    }
}
