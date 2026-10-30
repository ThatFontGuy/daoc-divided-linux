using System.Collections.Generic;

namespace DOL.GS
{
    /// <summary>
    /// Item class restrictions. The Death Knight shares every Necromancer item, so an item listing the Necromancer
    /// is usable by both.
    /// </summary>
    public static class ClassItemRules
    {
        public static int ItemClass(int classId) => classId == (int)eCharacterClass.DeathKnight ? (int)eCharacterClass.Necromancer : classId;

        public static eCharacterClass ItemClass(eCharacterClass characterClass) => (eCharacterClass)ItemClass((int)characterClass);

        public static bool Allows(string allowedClasses, int classId)
        {
            if (string.IsNullOrWhiteSpace(allowedClasses))
                return true;

            List<string> allowed = Util.SplitCSV(allowedClasses, true);
            return allowed.Contains(classId.ToString()) || allowed.Contains(ItemClass(classId).ToString());
        }
    }
}
