using System;
using System.Linq;
using DOL.Database;

namespace DOL.GS
{
    /// <summary>
    /// Drops Atlantean Glass from mobs in Atlantis. A world only uses it when it has a LootGenerator
    /// row for `DOL.GS.LootGeneratorAtlanteanGlass`. The regions are a server property, so a new
    /// Atlantis region does not need a build.
    /// </summary>
    public class LootGeneratorAtlanteanGlass : LootGeneratorBase
    {
        public const string GlassItemId = "atlanteanglass";
        public const int NamedCount = 5;

        private static readonly Lazy<DbItemTemplate> _glass = new(() => GameServer.Database.FindObjectByKey<DbItemTemplate>(GlassItemId));
        private static string _regionText;
        private static ushort[] _regions = [];

        public override LootList GenerateLoot(GameNPC mob, GameObject killer)
        {
            LootList loot = base.GenerateLoot(mob, killer);

            try
            {
                GameLiving owner = ROGMobGenerator.ResolveEquipmentLootOwner(killer);

                if (owner == null || _glass.Value == null || !InAtlantis(mob.CurrentRegionID) || mob.Level < ServerProperties.Properties.ARTIFACT_GLASS_MIN_LEVEL || owner.GetConLevel(mob) <= -3)
                    return loot;

                if (Util.Chance(DropChance(mob) / 100.0))
                    loot.AddFixed(_glass.Value, IsNamed(mob) ? NamedCount : 1);
            }
            catch
            {
                return loot;
            }

            return loot;
        }

        private static bool InAtlantis(ushort region)
        {
            string text = ServerProperties.Properties.ARTIFACT_GLASS_REGIONS;

            if (text != _regionText)
            {
                _regions = text.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                    .Select(value => ushort.TryParse(value, out ushort id) ? id : (ushort) 0)
                    .Where(id => id != 0)
                    .ToArray();
                _regionText = text;
            }

            return _regions.Contains(region);
        }

        private static bool IsNamed(GameNPC mob)
        {
            return mob is GameEpicNPC || !mob.Name.ToLower().Equals(mob.Name);
        }

        /// <summary>Drop chance in percent.</summary>
        public static double DropChance(GameNPC mob)
        {
            return IsNamed(mob) ? 100 : ServerProperties.Properties.LOOTGENERATOR_ATLANTEANGLASS_BASE_CHANCE;
        }
    }
}
