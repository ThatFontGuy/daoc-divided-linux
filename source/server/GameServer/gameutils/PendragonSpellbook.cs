using System;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS
{
    /// <summary>One merged client spellbook line for a realm's royal spell lines (Pendragon.*, Tuatha.*).</summary>
    public sealed class RoyalSpellbook
    {
        private readonly string _prefix;
        public SpellLine ClientLine { get; }
        private Dictionary<int,int> _slots;
        public RoyalSpellbook(string prefix, string name, string career)
        {
            _prefix = prefix + ".";
            ClientLine = new(prefix, name, career, true);
        }
        public bool OwnsLine(string key) => key.StartsWith(_prefix, StringComparison.Ordinal);
        private Dictionary<int,int> Slots => _slots ??= StormforgedRules.AssignClientSlots(
            SkillBase.GetSpellLineKeys().Where(OwnsLine)
                .Select(key => (key,(IEnumerable<Spell>)SkillBase.GetSpellList(key))));
        public int ClientLevel(Spell spell) => Slots.TryGetValue(spell.ID,out int slot) ? slot : spell.Level;
        public IList<(SpellLine,List<Skill>)> ClientSpellLines(IList<(SpellLine,List<Skill>)> lines)
        {
            int first = -1;
            for(int index=0;index<lines.Count;index++)
                if(OwnsLine(lines[index].Item1.KeyName)) { first=index;break; }
            if(first<0) return lines;
            var merged=lines.Where(line=>OwnsLine(line.Item1.KeyName))
                .SelectMany(line=>line.Item2).OrderBy(skill=>skill is Spell spell?ClientLevel(spell):skill.Level).ToList();
            var result=lines.Where(line=>!OwnsLine(line.Item1.KeyName)).ToList();
            result.Insert(first,(ClientLine,merged));
            return result;
        }
    }

    public static class PendragonSpellbook
    {
        public static readonly RoyalSpellbook Albion = new("Pendragon", "Pendragon Sovereign", "PendragonCareer");
        public static readonly RoyalSpellbook Hibernia = new("Tuatha", "Tuatha Sovereign", "TuathaCareer");
        public static readonly RoyalSpellbook[] All = { Albion, Hibernia };
        public static SpellLine ClientLine => Albion.ClientLine;
        public static int ClientLevel(Spell spell) => Albion.ClientLevel(spell);
        public static RoyalSpellbook For(SpellLine clientLine) => All.FirstOrDefault(book => ReferenceEquals(book.ClientLine, clientLine));
        public static bool OwnsLine(string key) => All.Any(book => book.OwnsLine(key));
        public static IList<(SpellLine,List<Skill>)> ClientSpellLines(IList<(SpellLine,List<Skill>)> lines)
        {
            foreach (var book in All)
                lines = book.ClientSpellLines(lines);
            return lines;
        }
    }
}
