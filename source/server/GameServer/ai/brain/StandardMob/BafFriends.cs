using System;
using DOL.GS;
using DOL.GS.ServerProperties;

namespace DOL.AI.Brain
{
    /// <summary>
    /// Who comes when a monster brings a friend (owner 2026-10-28). OpenDAoC counts only monsters of the same or an
    /// allied faction, so a monster with no faction never brought anyone: two thirds of the aggressive monsters in the
    /// database have none (Midgard's frore liches, windswept wraiths and chillsome wights among them). A monster with no
    /// faction now brings others of its own kind, as monsters did on live (wraiths bring wraiths): faction-less monsters
    /// of the same name. Monsters with a faction keep the faction rule.
    /// </summary>
    public static class BafFriends
    {
        [ServerProperty("pve", "baf_same_name_without_faction",
            "Does a monster with no faction bring others of its own kind (faction-less monsters with the same name) when it brings a friend? Monsters with a faction always use their faction.", true)]
        public static bool SameNameWithoutFaction = true;

        /// <summary>Pure rule: the faction when the pulled monster has one, otherwise the same name among faction-less monsters.</summary>
        public static bool IsFriend(bool pulledHasFaction, bool factionFriends, bool otherHasFaction, bool sameName, bool sameNameFallback) =>
            pulledHasFaction ? factionFriends : sameNameFallback && !otherHasFaction && sameName;

        public static bool CanBringFriends(GameNPC pulled) => pulled.Faction != null || SameNameWithoutFaction;

        public static bool IsFriend(GameNPC pulled, GameNPC other) =>
            other != null && pulled != null && other is not GameBot &&
            IsFriend(pulled.Faction != null, pulled.Faction != null && other.IsFriend(pulled), other.Faction != null,
                string.Equals(pulled.Name, other.Name, StringComparison.OrdinalIgnoreCase), SameNameWithoutFaction);
    }
}
