using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;

namespace DOL.GS
{
    /// <summary>
    /// Drops a random mythirian from the `Mythirians` merchant list. A world only uses it
    /// when it has a LootGenerator row for `DOL.GS.LootGeneratorMythirian`.
    /// Loot owners follow the ROG rules, so players, autonomous bots and account companions roll.
    /// </summary>
    public class LootGeneratorMythirian : LootGeneratorBase
    {
        public const string MerchantListId = "Mythirians";

        private static readonly Lazy<DbItemTemplate[]> _mythirians = new(LoadMythirians);

        public override LootList GenerateLoot(GameNPC mob, GameObject killer)
        {
            LootList loot = base.GenerateLoot(mob, killer);

            try
            {
                GameLiving owner = ROGMobGenerator.ResolveEquipmentLootOwner(killer);

                if (owner == null || mob.Level < ServerProperties.Properties.LOOTGENERATOR_MYTHIRIAN_MIN_LEVEL || owner.GetConLevel(mob) <= -3)
                    return loot;

                DbItemTemplate[] mythirians = _mythirians.Value;

                if (mythirians.Length == 0)
                    return loot;

                if (Util.Chance(DropChance(mob) / 100.0))
                    loot.AddFixed(mythirians[Util.Random(mythirians.Length - 1)], 1);
            }
            catch
            {
                return loot;
            }

            return loot;
        }

        /// <summary>Drop chance in percent. Named mobs (capitalized names) and epic NPCs get the named multiplier.</summary>
        public static double DropChance(GameNPC mob)
        {
            double chance = ServerProperties.Properties.LOOTGENERATOR_MYTHIRIAN_BASE_CHANCE;

            if (mob is GameEpicNPC || !mob.Name.ToLower().Equals(mob.Name))
                chance *= ServerProperties.Properties.LOOTGENERATOR_MYTHIRIAN_NAMED_MULTIPLIER;

            return Math.Min(100, chance);
        }

        private static DbItemTemplate[] LoadMythirians()
        {
            IList<DbMerchantItem> stock = DOLDB<DbMerchantItem>.SelectObjects(DB.Column("ItemListID").IsEqualTo(MerchantListId));
            return stock.Select(item => GameServer.Database.FindObjectByKey<DbItemTemplate>(item.ItemTemplateID))
                .Where(template => template != null)
                .GroupBy(template => template.Id_nb)
                .Select(group => group.First())
                .ToArray();
        }
    }
}
