using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS
{
    /// <summary>
    /// Every real player in a dragon raid leaves with at least one item from the dragon's own loot table (owner
    /// 2026-11-02: a tester's raid gave them nothing). A player the expedition's share already gave an item gets
    /// nothing more; everyone else gets one roll, straight to the bag, dead or alive. A full bag puts it at their feet.
    /// </summary>
    public static class DragonPlayerReward
    {
        private static readonly Logging.Logger Log = Logging.LoggerManager.Create(typeof(DragonPlayerReward));

        public static void Grant(GameNPC dragon, IEnumerable<GamePlayer> contributors, IEnumerable<GamePlayer> alreadyPaid)
        {
            eRealm realm = DragonLairPlacement.DragonRealm(dragon);
            if (realm == eRealm.None)
                return;

            List<(DbItemTemplate Item, int Chance)> table = LootGeneratorTemplate.MobTable(dragon.Name)
                .Select(t => (GameServer.Database.FindObjectByKey<DbItemTemplate>(t.ItemTemplateID), t.Chance))
                .ToList();

            foreach (GamePlayer player in Recipients(realm, contributors,
                         dragon.GetPlayersInRadius(WorldMgr.VISIBILITY_DISTANCE), alreadyPaid))
            {
                DbItemTemplate template = Pick(table, item => LootGeneratorBase.CanReceiveRealmDrop(player, item), Random.Shared);
                if (template == null)
                {
                    if (Log.IsWarnEnabled)
                        Log.Warn($"DRAGON_PLAYER_LOOT_NONE dragon=\"{dragon.Name}\" player=\"{player.Name}\" table={table.Count}");
                    continue;
                }
                Give(dragon, player, template);
            }
        }

        /// <summary>
        /// The players owed a dragon item: whoever fought it (pets and spawned helpers count as their owner), and
        /// every player of the dragon's realm standing by it, less those the expedition's share already paid.
        /// Dead players stay in; only players no longer in the world are left out.
        /// </summary>
        public static List<GamePlayer> Recipients(eRealm dragonRealm, IEnumerable<GamePlayer> contributors,
            IEnumerable<GamePlayer> nearby, IEnumerable<GamePlayer> alreadyPaid)
        {
            HashSet<GamePlayer> paid = alreadyPaid?.ToHashSet() ?? [];
            return (contributors ?? [])
                .Concat((nearby ?? []).Where(p => p != null && p.Realm == dragonRealm))
                .Where(p => p != null && p.ObjectState == GameObject.eObjectState.Active && !paid.Contains(p))
                .Distinct()
                .ToList();
        }

        /// <summary>One item from the table, weighted by each entry's drop chance; null when none suits the player.</summary>
        public static DbItemTemplate Pick(IReadOnlyList<(DbItemTemplate Item, int Chance)> table,
            Func<DbItemTemplate, bool> canUse, Random random)
        {
            var usable = table.Where(e => e.Item != null && e.Chance > 0 && !GameMoney.IsItemMoney(e.Item.Name) && canUse(e.Item))
                .ToList();
            int roll = random.Next(Math.Max(1, usable.Sum(e => e.Chance)));
            foreach (var entry in usable)
            {
                if (roll < entry.Chance)
                    return entry.Item;
                roll -= entry.Chance;
            }
            return null;
        }

        private static void Give(GameNPC dragon, GamePlayer player, DbItemTemplate template)
        {
            GameInventoryItem item = GameInventoryItem.Create(template);
            item.IsCrafted = false;
            item.Creator = dragon.Name;
            if (item.PackSize > 1 && item.MaxCount >= item.PackSize)
                item.Count = item.PackSize;

            bool inBag = player.ReceiveItem(dragon, item);
            if (!inBag)
            {
                player.CreateItemOnTheGround(item);
                player.Out.SendMessage($"Your backpack is full: {item.GetName(0, false)} from {dragon.Name} lies at your feet.",
                    eChatType.CT_Important, eChatLoc.CL_SystemWindow);
            }
            if (Log.IsInfoEnabled)
                Log.Info($"DRAGON_PLAYER_LOOT dragon=\"{dragon.Name}\" player=\"{player.Name}\" item=\"{item.Name}\" " +
                         $"alive={player.IsAlive} bag={inBag} region={player.CurrentRegionID}");
        }
    }
}
