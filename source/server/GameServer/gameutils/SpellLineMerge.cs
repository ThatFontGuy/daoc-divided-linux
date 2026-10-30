using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace DOL.GS
{
    /// <summary>
    /// The 1.130 class migrations put spells whose level clashed with a stock spell into extra lines
    /// "&lt;line&gt; (Live)" / "&lt;line&gt; (1.130)" beside the stock line. The client sees each such group as one
    /// spellbook line, as on live: the extras merge into the stock line, and every spell gets a client
    /// level of its own, because the client addresses a list spell by line index + level.
    /// The server lines (bots, casting, delves) stay as they are.
    /// </summary>
    public static class SpellLineMerge
    {
        private static readonly Regex Suffix = new(@" \((Live|1\.130)( II| III)?\)$", RegexOptions.Compiled);
        private static Dictionary<string, Dictionary<int, int>> _slots;

        /// <summary>The stock line name a line belongs to: "Cursing (Live)" -> "Cursing".</summary>
        public static string BaseKey(string lineKey) => Suffix.Replace(lineKey, string.Empty);

        public static bool IsExtraLine(string lineKey) => Suffix.IsMatch(lineKey);

        /// <summary>
        /// Client levels for one group. Stock spells keep their own level so existing hotbar buttons
        /// stay valid; extra-line spells take their level when free, else the nearest free level below
        /// it (never above what the player has trained), else the nearest above. Slots never move
        /// while leveling, because they are computed from every spell in the group.
        /// </summary>
        public static Dictionary<int, int> AssignClientSlots(string baseKey, IEnumerable<(string LineKey, IEnumerable<Spell> Spells)> lines)
        {
            var slots = new Dictionary<int, int>();
            var taken = new HashSet<int>();
            var spells = lines.SelectMany(line => line.Spells.Select(spell => (line.LineKey, Spell: spell)))
                .OrderBy(entry => entry.LineKey == baseKey ? 0 : 1)
                .ThenBy(entry => entry.Spell.Level).ThenBy(entry => entry.LineKey, StringComparer.Ordinal).ThenBy(entry => entry.Spell.ID);
            foreach (var (_, spell) in spells)
            {
                if (slots.ContainsKey(spell.ID))
                    continue;
                int slot = spell.Level;
                while (slot > 1 && taken.Contains(slot))
                    slot--;
                if (taken.Contains(slot))
                    for (slot = spell.Level + 1; taken.Contains(slot); slot++) { }
                taken.Add(slot);
                slots[spell.ID] = slot;
            }
            return slots;
        }

        /// <summary>Slot tables for every group that has an extra line, keyed by the stock line name.</summary>
        public static Dictionary<string, Dictionary<int, int>> BuildSlots(IEnumerable<(string LineKey, IEnumerable<Spell> Spells)> lines)
        {
            var all = lines.ToList();
            return all.Where(line => IsExtraLine(line.LineKey)).Select(line => BaseKey(line.LineKey)).Distinct()
                .ToDictionary(baseKey => baseKey, baseKey => AssignClientSlots(baseKey, all.Where(line => BaseKey(line.LineKey) == baseKey)));
        }

        /// <summary>Replaces the slot tables (tests); null rebuilds them from SkillBase on next use.</summary>
        public static void Reset(IEnumerable<(string LineKey, IEnumerable<Spell> Spells)> lines = null) =>
            _slots = lines == null ? null : BuildSlots(lines);

        private static Dictionary<string, Dictionary<int, int>> Slots => _slots ??= BuildSlots(
            SkillBase.GetSpellLineKeys().Select(key => (key, (IEnumerable<Spell>)SkillBase.GetSpellList(key))));

        /// <summary>True for a client-view line that stands for a merged group.</summary>
        public static bool IsMerged(SpellLine line) => line != null && Slots.ContainsKey(BaseKey(line.KeyName));

        public static bool TryClientLevel(SpellLine line, Spell spell, out int level)
        {
            level = 0;
            return line != null && Slots.TryGetValue(BaseKey(line.KeyName), out var slots) && slots.TryGetValue(spell.ID, out level);
        }

        /// <summary>
        /// Each group of lines with one stock name becomes one line at the position of its first
        /// member, shown as the stock line. Lists without extra lines come back unchanged.
        /// </summary>
        public static IList<(SpellLine, List<Skill>)> ClientSpellLines(IList<(SpellLine, List<Skill>)> lines)
        {
            if (!lines.Any(line => IsExtraLine(line.Item1.KeyName)))
                return lines;

            var result = new List<(SpellLine, List<Skill>)>();
            foreach (var group in lines.GroupBy(line => BaseKey(line.Item1.KeyName)))
            {
                var members = group.ToList();
                if (members.Count == 1 && !IsExtraLine(members[0].Item1.KeyName))
                {
                    result.Add(members[0]);
                    continue;
                }
                SpellLine head = members.FirstOrDefault(line => line.Item1.KeyName == group.Key).Item1;
                if (head == null)
                {
                    head = (SpellLine)members[0].Item1.Clone();
                    head.Name = BaseKey(head.Name);
                }
                var skills = members.SelectMany(line => line.Item2)
                    .OrderBy(skill => skill is Spell spell && TryClientLevel(head, spell, out int slot) ? slot : skill.Level).ToList();
                result.Add((head, skills));
            }
            return result;
        }
    }
}
