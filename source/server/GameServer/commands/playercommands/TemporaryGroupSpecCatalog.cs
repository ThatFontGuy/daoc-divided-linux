using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS.Commands
{
    /// <summary>
    /// The builds a /spawn companion can be asked for (owner 2026-10-28: /spawn specs, and /spawn &lt;class&gt; &lt;spec&gt;
    /// for macros). Nothing here changes a build: the options are the class's existing builds, named after the spec line
    /// each one really trains highest (owner: "basing the spec name on what is actually being trained"). A family such as
    /// the Friar's staff builds holds variants that train different lines highest, so options are the distinct lines,
    /// and an option is spawned from one of the existing variants that trains it highest. Melee families are weapon
    /// setups (one-handed and shield, two-handed, dual wield...) and keep that name; their weapon type stays random.
    /// </summary>
    public static class TemporaryGroupSpecCatalog
    {
        public sealed record Option(string Label, eSpecType[] Families, bool WeaponSetup);

        private const int Samples = 200;
        private const int SpawnTries = 400;
        private static readonly ConcurrentDictionary<eCharacterClass, IReadOnlyList<Option>> Cache = new();

        public static bool IsWeaponSetup(eSpecType family) => family is eSpecType.OneHanded or eSpecType.OneHandAndShield or
            eSpecType.OneHandHybrid or eSpecType.TwoHandAndShield or eSpecType.TwoHandHybrid or eSpecType.TwoHanded or
            eSpecType.DualWield or eSpecType.DualWieldAndShield or eSpecType.LeftAxe or eSpecType.Mid or eSpecType.Ranged or
            eSpecType.Instrument;

        public static string SetupLabel(eCharacterClass characterClass, eSpecType family) => family switch
        {
            eSpecType.OneHanded or eSpecType.OneHandAndShield => "One Handed and Shield",
            eSpecType.OneHandHybrid => "One Handed Hybrid",
            // The Armsman has both: its hybrid trains the two-hander first and keeps a shield.
            eSpecType.TwoHandHybrid or eSpecType.TwoHandAndShield when characterClass == eCharacterClass.Armsman => "Two Handed Hybrid",
            eSpecType.TwoHandHybrid or eSpecType.TwoHandAndShield or eSpecType.TwoHanded or eSpecType.Mid => "Two Handed",
            eSpecType.DualWield when characterClass == eCharacterClass.Blademaster => Specs.Celtic_Dual,
            eSpecType.DualWield when characterClass == eCharacterClass.Savage => Specs.HandToHand,
            eSpecType.DualWield => "Dual Wield",
            eSpecType.DualWieldAndShield when characterClass == eCharacterClass.Blademaster => Specs.Celtic_Dual + " and Shield",
            eSpecType.DualWieldAndShield => "Dual Wield and Shield",
            eSpecType.LeftAxe => Specs.Left_Axe,
            _ => family.ToString(),
        };

        /// <summary>The spec line a build trains highest; on a tie, the one the build lists first.</summary>
        public static string TopLine(BotSpec spec)
        {
            string top = null;
            uint cap = 0;
            foreach (BotSpecLine line in spec?.SpecLines ?? [])
            {
                if (top == null || line.SpecCap > cap)
                {
                    top = line.Spec;
                    cap = line.SpecCap;
                }
            }
            return top;
        }

        /// <summary>The class's options, or none when it has a single build.</summary>
        public static IReadOnlyList<Option> For(eCharacterClass characterClass) => Cache.GetOrAdd(characterClass, Build);

        private static IReadOnlyList<Option> Build(eCharacterClass characterClass)
        {
            IReadOnlyList<eSpecType> families = BotSpec.GetSpecializationChoices(characterClass);
            if (families.Count < 2 || families.All(family => family == eSpecType.None))
                return [];

            List<Option> options = new();
            Dictionary<string, List<eSpecType>> byLine = new();
            List<string> order = new();
            foreach (eSpecType family in families)
            {
                if (IsWeaponSetup(family))
                {
                    string label = SetupLabel(characterClass, family);
                    if (!options.Any(option => option.Label == label))
                        options.Add(new(label, [family], true));
                    continue;
                }
                for (int i = 0; i < Samples; i++)
                {
                    string line = TopLine(BotSpec.GetSpec(characterClass, family));
                    if (line == null)
                        continue;
                    if (!byLine.TryGetValue(line, out List<eSpecType> lineFamilies))
                    {
                        byLine[line] = lineFamilies = new();
                        order.Add(line);
                    }
                    if (!lineFamilies.Contains(family))
                        lineFamilies.Add(family);
                }
            }
            options.AddRange(order.Select(line => new Option(line, byLine[line].ToArray(), false)));
            return options;
        }

        public static bool TryResolve(eCharacterClass characterClass, string input, out Option option)
        {
            string wanted = Normalize(input);
            option = For(characterClass).FirstOrDefault(candidate => Normalize(candidate.Label) == wanted);
            return option != null;
        }

        /// <summary>A new build for the option: a weapon setup as asked; otherwise one of the existing variants that trains the line highest.</summary>
        public static BotSpec Create(eCharacterClass characterClass, Option option)
        {
            if (option.WeaponSetup)
                return BotSpec.GetSpec(characterClass, option.Families[0]);
            BotSpec spec = null;
            for (int i = 0; i < SpawnTries; i++)
            {
                spec = BotSpec.GetSpec(characterClass, option.Families[Util.Random(option.Families.Length - 1)]);
                if (TopLine(spec) == option.Label)
                    return spec;
            }
            return spec;
        }

        public static string Describe(eCharacterClass characterClass) =>
            string.Join(", ", For(characterClass).Select(option => option.Label));

        public static string Normalize(string value) =>
            new(value.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());
    }
}
