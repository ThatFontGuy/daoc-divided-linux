using System;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace DOL.GS
{
    /// <summary>Additional player race choices observed in the bundled 1.130 client.
    /// This does not change bot generation, disabled classes or classic class lists.</summary>
    public static class ModernRaceCreationRules
    {
        private sealed record Registration(int Realm, int Class, int[] Races);
        private static readonly Registration[] Registrations = Load();

        private static Registration[] Load()
        {
            using Stream stream = typeof(ModernRaceCreationRules).Assembly.GetManifestResourceStream("DOL.GS.ModernRaceRegistrations.json")
                ?? throw new InvalidOperationException("Modern race registrations are missing.");
            return JsonSerializer.Deserialize<Registration[]>(stream)
                ?? throw new InvalidDataException("Modern race registrations are empty.");
        }

        public static bool IsAdditionalRaceAllowed(int career, int race, int realm, bool enabled)
            => enabled && race is >= 16 and <= 21 &&
                Registrations.Any(entry => entry.Realm == realm && entry.Class == career && entry.Races.Contains(race));
    }
}
