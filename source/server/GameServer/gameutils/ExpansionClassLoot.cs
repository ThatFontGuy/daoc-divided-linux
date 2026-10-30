using System.Collections.Generic;

namespace DOL.GS
{
    /// <summary>
    /// Random-object-generator (ROG) rules for the expansion classes the generator's own switches predate.
    /// Weapons, armor, shields and skills follow each class's trained lines and granted abilities, so dropped
    /// loot is usable. Stat weighting borrows an existing class with the same stat profile.
    /// </summary>
    public static class ExpansionClassLoot
    {
        private sealed record Rules(eObjectType Armor, eObjectType[] Weapons, int Shield, eCharacterClass StatTemplate, HashSet<eProperty> Skills);

        private static HashSet<eProperty> Skills(params eProperty[] lines) =>
            new(lines) { eProperty.AllSkills };

        private static readonly Rules Mauler = new(eObjectType.Leather, [eObjectType.FistWraps, eObjectType.MaulerStaff], 0, eCharacterClass.Champion,
            Skills(eProperty.Skill_FistWraps, eProperty.Skill_MaulerStaff, eProperty.Skill_Aura_Manipulation, eProperty.Skill_Magnetism,
                eProperty.Skill_Power_Strikes, eProperty.AllMeleeWeaponSkills, eProperty.AllMagicSkills));

        private static readonly Dictionary<eCharacterClass, Rules> ByClass = new()
        {
            [eCharacterClass.Heretic] = new(eObjectType.Cloth, [eObjectType.CrushingWeapon, eObjectType.Flexible, eObjectType.Staff, eObjectType.Shield], 1,
                eCharacterClass.Friar, Skills(eProperty.Skill_Crushing, eProperty.Skill_Flexible_Weapon, eProperty.Skill_Enhancement,
                    eProperty.Skill_Rejuvenation, eProperty.Skill_Shields, eProperty.AllMeleeWeaponSkills, eProperty.AllMagicSkills)),
            [eCharacterClass.Valkyrie] = new(eObjectType.Chain, [eObjectType.Sword, eObjectType.Spear, eObjectType.Staff, eObjectType.Shield], 3,
                eCharacterClass.Thane, Skills(eProperty.Skill_Sword, eProperty.Skill_Spear, eProperty.Skill_Shields, eProperty.Skill_Parry,
                    eProperty.Skill_Mending, eProperty.Skill_OdinsWill, eProperty.AllMeleeWeaponSkills, eProperty.AllMagicSkills)),
            [eCharacterClass.Bainshee] = new(eObjectType.Cloth, [eObjectType.Staff], 0, eCharacterClass.Eldritch,
                Skills(eProperty.Skill_EtherealShriek, eProperty.Skill_PhantasmalWail, eProperty.Skill_SpectralGuard, eProperty.AllMagicSkills)),
            [eCharacterClass.Warlock] = new(eObjectType.Cloth, [eObjectType.Staff], 0, eCharacterClass.Runemaster,
                Skills(eProperty.Skill_Cursing, eProperty.Skill_Hexing, eProperty.Skill_Witchcraft, eProperty.AllMagicSkills)),
            [eCharacterClass.Vampiir] = new(eObjectType.Leather, [eObjectType.Piercing], 0, eCharacterClass.Champion,
                Skills(eProperty.Skill_Piercing, eProperty.Skill_Dementia, eProperty.Skill_ShadowMastery, eProperty.Skill_VampiiricEmbrace,
                    eProperty.AllMeleeWeaponSkills, eProperty.AllMagicSkills)),
            [eCharacterClass.MaulerAlb] = Mauler,
            [eCharacterClass.MaulerMid] = Mauler,
            [eCharacterClass.MaulerHib] = Mauler,
        };

        public static bool Covers(eCharacterClass characterClass) => ByClass.ContainsKey(characterClass);

        public static bool SkillValid(eCharacterClass characterClass, eProperty property) =>
            ByClass.TryGetValue(characterClass, out Rules rules) && rules.Skills.Contains(property);

        public static bool TryWeapon(eCharacterClass characterClass, out eObjectType weapon)
        {
            weapon = eObjectType.GenericItem;
            if (!ByClass.TryGetValue(characterClass, out Rules rules)) return false;
            weapon = rules.Weapons[Util.Random(rules.Weapons.Length - 1)];
            return true;
        }

        public static bool TryArmor(eCharacterClass characterClass, out eObjectType armor)
        {
            armor = ByClass.TryGetValue(characterClass, out Rules rules) ? rules.Armor : eObjectType.GenericItem;
            return rules != null;
        }

        public static bool TryShieldSize(eCharacterClass characterClass, out int size)
        {
            size = ByClass.TryGetValue(characterClass, out Rules rules) ? rules.Shield : 0;
            return rules != null;
        }

        /// <summary>The existing class whose stat weighting and power/acuity rules this class shares.</summary>
        public static eCharacterClass StatTemplate(eCharacterClass characterClass) =>
            ByClass.TryGetValue(characterClass, out Rules rules) ? rules.StatTemplate : characterClass;
    }
}
