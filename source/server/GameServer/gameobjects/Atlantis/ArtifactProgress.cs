using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.Database.Attributes;

namespace DOL.GS
{
    /// <summary>What one character has earned toward one artifact.</summary>
    [DataTable(TableName = "offline_artifact_progress")]
    public sealed class OfflineArtifactProgress : DataObject
    {
        [DataElement(AllowDbNull = false, Index = true, Varchar = 100)] public string CharacterID { get; set; } = string.Empty;
        [DataElement(AllowDbNull = false, Varchar = 32)] public string ArtifactID { get; set; } = string.Empty;

        /// <summary>Finished the encounter, so the scholar hands over a level 10 artifact.</summary>
        [DataElement(AllowDbNull = false)] public bool EncounterDone { get; set; }

        /// <summary>Has been given this artifact at least once, so a lost one can be replaced.</summary>
        [DataElement(AllowDbNull = false)] public bool Claimed { get; set; }

        /// <summary>Experience at the last level reached, used when a lost artifact is replaced.</summary>
        [DataElement(AllowDbNull = false)] public long Experience { get; set; }
    }

    /// <summary>Per-character artifact records, read once and kept with the player.</summary>
    public static class ArtifactProgress
    {
        private const string CacheKey = "ArtifactProgress";

        public static Dictionary<string, OfflineArtifactProgress> For(GamePlayer player)
        {
            Dictionary<string, OfflineArtifactProgress> rows = player.TempProperties.GetProperty<Dictionary<string, OfflineArtifactProgress>>(CacheKey);

            if (rows != null)
                return rows;

            rows = DOLDB<OfflineArtifactProgress>.SelectObjects(DB.Column("CharacterID").IsEqualTo(player.InternalID))
                .GroupBy(row => row.ArtifactID)
                .ToDictionary(group => group.Key, group => group.First());
            player.TempProperties.SetProperty(CacheKey, rows);
            return rows;
        }

        public static OfflineArtifactProgress Get(GamePlayer player, string artifactId)
        {
            return For(player).GetValueOrDefault(artifactId);
        }

        public static void Update(GamePlayer player, string artifactId, Action<OfflineArtifactProgress> change)
        {
            Dictionary<string, OfflineArtifactProgress> rows = For(player);

            if (rows.TryGetValue(artifactId, out OfflineArtifactProgress row))
            {
                change(row);
                row.Dirty = true;
                GameServer.Database.SaveObject(row);
                return;
            }

            row = new OfflineArtifactProgress { CharacterID = player.InternalID, ArtifactID = artifactId };
            change(row);
            GameServer.Database.AddObject(row);
            rows[artifactId] = row;
        }

        public static void RememberLevel(GamePlayer player, ArtifactItem item)
        {
            string artifactId = ArtifactCatalog.ArtifactOf(item.Id_nb);

            if (artifactId != null)
                Update(player, artifactId, row => row.Experience = Math.Max(row.Experience, item.Experience));
        }
    }

    /// <summary>The Artifact, ArtifactXItem and credit rows, indexed once.</summary>
    public static class ArtifactCatalog
    {
        public const string CreditPackagePrefix = "artifact:";

        private sealed class Tables
        {
            public readonly Dictionary<string, List<DbItemTemplate>> Versions = new();
            public readonly Dictionary<string, string> ArtifactByItem = new(StringComparer.OrdinalIgnoreCase);
            public readonly Dictionary<string, DbItemTemplate> CreditByArtifact = new();
            public readonly Dictionary<string, string> ArtifactByCredit = new(StringComparer.OrdinalIgnoreCase);
            public readonly Dictionary<string, string> Names = new();
        }

        private static readonly Lazy<Tables> _tables = new(Load);

        private static Tables Load()
        {
            Tables tables = new();

            foreach (DbArtifactXItem row in GameServer.Database.SelectAllObjects<DbArtifactXItem>())
            {
                DbItemTemplate template = GameServer.Database.FindObjectByKey<DbItemTemplate>(row.ItemID);

                if (template == null)
                    continue;

                if (!tables.Versions.TryGetValue(row.ArtifactID, out List<DbItemTemplate> versions))
                    tables.Versions[row.ArtifactID] = versions = [];

                versions.Add(template);
                tables.ArtifactByItem[template.Id_nb] = row.ArtifactID;
            }

            foreach (DbItemTemplate credit in DOLDB<DbItemTemplate>.SelectObjects(DB.Column("PackageID").IsLike(CreditPackagePrefix + "%")))
            {
                string artifactId = credit.PackageID[CreditPackagePrefix.Length..];
                tables.CreditByArtifact[artifactId] = credit;
                tables.ArtifactByCredit[credit.Id_nb] = artifactId;
            }

            foreach ((string artifactId, List<DbItemTemplate> versions) in tables.Versions)
            {
                tables.Names[artifactId] = ArtifactEncounters.Find(artifactId)?.Name
                    ?? (tables.CreditByArtifact.TryGetValue(artifactId, out DbItemTemplate credit) ? CreditName(credit.Name) : versions[0].Name);
            }

            return tables;
        }

        public static string CreditName(string name)
        {
            return name.EndsWith(" Credit", StringComparison.OrdinalIgnoreCase) ? name[..^7] : name;
        }

        public static IEnumerable<string> ArtifactIds => _tables.Value.Versions.Keys;

        public static string ArtifactOf(string itemId)
        {
            return itemId != null && _tables.Value.ArtifactByItem.TryGetValue(itemId, out string artifactId) ? artifactId : null;
        }

        public static string ArtifactOfCredit(string itemId)
        {
            return itemId != null && _tables.Value.ArtifactByCredit.TryGetValue(itemId, out string artifactId) ? artifactId : null;
        }

        public static string NameOf(string artifactId)
        {
            return _tables.Value.Names.GetValueOrDefault(artifactId, artifactId);
        }

        public static string FindByName(string name)
        {
            return _tables.Value.Names.FirstOrDefault(pair => pair.Value.Equals(name, StringComparison.OrdinalIgnoreCase)).Key;
        }

        public static bool CanUse(GamePlayer player, DbItemTemplate template)
        {
            if (template.Realm != 0 && template.Realm != (int) player.Realm)
                return false;

            return string.IsNullOrEmpty(template.AllowedClasses)
                || template.AllowedClasses.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).Contains(player.CharacterClass.ID.ToString());
        }

        public static List<DbItemTemplate> VersionsFor(GamePlayer player, string artifactId)
        {
            return _tables.Value.Versions.TryGetValue(artifactId, out List<DbItemTemplate> versions)
                ? versions.Where(template => CanUse(player, template)).ToList()
                : [];
        }
    }
}
