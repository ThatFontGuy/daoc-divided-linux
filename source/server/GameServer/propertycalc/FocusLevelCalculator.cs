using System;

namespace DOL.GS.PropertyCalc
{
    /// <summary>
    /// The Focus Level calculator
    ///
    /// BuffBonusCategory1 is used for buffs, uncapped
    /// BuffBonusCategory2 unused
    /// BuffBonusCategory3 unused
    /// BuffBonusCategory4 unused
    /// BuffBonusMultCategory1 unused
    /// </summary>
    [PropertyCalculator(eProperty.Focus_Darkness, eProperty.Focus_Matter)]
    [PropertyCalculator(eProperty.Focus_Mind, eProperty.Focus_Arboreal)]
    [PropertyCalculator(eProperty.Focus_EtherealShriek, eProperty.Focus_Witchcraft)]
    public class FocusLevelCalculator : PropertyCalculator
    {
        public FocusLevelCalculator() { }

        public override int CalcValue(GameLiving living, eProperty property)
        {
            // Owner 2026-11-01: a bot caster's staff has to count exactly like a player's. This used to answer 0 for
            // anything that was not a GamePlayer, so every GameBot carried a focus value of zero whatever staff it held
            // and BotSpellPower.Cost charged it the focus-free 120% of the base power cost on every cast.
            if (living == null)
                return 0;

            ICharacterClass characterClass = living is GamePlayer player
                ? player.CharacterClass
                : (living as IGamePlayer)?.CharacterClass;
            if (characterClass == null)
                return 0;

            int itemBonus = living.ItemBonus[property];
            int focusLevel = living.BaseBuffBonusCategory[property];

            if (SkillBase.CheckPropertyType(property, ePropertyType.Focus) && characterClass.IsFocusCaster)
            {
                focusLevel += living.BaseBuffBonusCategory[eProperty.AllFocusLevels];
                itemBonus = Math.Max(itemBonus, living.ItemBonus[eProperty.AllFocusLevels]);
            }

            return focusLevel + Math.Min(50, itemBonus);
        }
    }
}
