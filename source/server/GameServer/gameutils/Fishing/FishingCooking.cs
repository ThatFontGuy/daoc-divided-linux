using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS.PacketHandler;
using DOL.GS.Spells;

namespace DOL.GS.Fishing
{
    /// <summary>A cooked dish: eating one casts stock 20-minute self regen spells (Potions line).</summary>
    public sealed class FishingDish
    {
        public string TemplateId;
        public string Name;
        public int Model;
        public int PriceCopper;
        public int[] SpellIds;
    }

    /// <summary>
    /// What the catch is good for besides selling: /fish cook at a burning campfire turns raw fish into food, and a
    /// waterlogged chest can be opened for coins and sometimes a random magic item. Food and chests are used from the
    /// backpack through GamePlayer.UseSlot (TryUse). The dish table and the chest rolls are pure and unit tested.
    /// </summary>
    public static class FishingCooking
    {
        public const string ChestTemplateId = "offline_fish_junk_waterlogged_chest";

        /// <summary>Raw fish cooked per /fish cook.</summary>
        public const int FishPerCook = 10;

        private const int CookSeconds = 5;
        private const string CookProperty = "FISHING_COOK";

        // Spells: 92190 "2 Health Regen", 92192 "1 Endo Regen", 92191 "4 Health Regen", 31105 "2 Power Regen",
        // 31134 "8 Health Regen", 31110 "3 Power Regen", 92194 "3 Endo Regen"; all Self, 1200 s, in the Potions line.
        // Models: objects.csv 544 "Small fish", 545 "Large fish".
        public static readonly IReadOnlyList<FishingDish> Dishes = new[]
        {
            new FishingDish { TemplateId = "offline_food_grilled_fish", Name = "Grilled Fish", Model = 544, PriceCopper = 300, SpellIds = new[] { 92190, 92192 } },
            new FishingDish { TemplateId = "offline_food_smoked_fish", Name = "Smoked Fish", Model = 545, PriceCopper = 1200, SpellIds = new[] { 92191, 31105 } },
            new FishingDish { TemplateId = "offline_food_anglers_feast", Name = "Angler's Feast", Model = 545, PriceCopper = 5000, SpellIds = new[] { 31134, 31110, 92194 } },
        };

        public static FishingDish FindDish(string templateId)
        {
            foreach (FishingDish dish in Dishes)
            {
                if (dish.TemplateId == templateId)
                {
                    return dish;
                }
            }

            return null;
        }

        /// <summary>
        /// The dish a raw fish cooks into: a feast from rare species and trophy-size fish, smoked fish from uncommon species
        /// and large fish, grilled fish otherwise. Null for anything that isn't a fish.
        /// </summary>
        public static FishingDish DishFor(string templateId)
        {
            if (!FishingCatalog.TryGetFish(templateId, out eFishingRarity rarity, out int tier))
            {
                return null;
            }

            if (rarity == eFishingRarity.Rare || tier == 3)
            {
                return Dishes[2];
            }

            if (rarity == eFishingRarity.Uncommon || tier == 2)
            {
                return Dishes[1];
            }

            return Dishes[0];
        }

        /// <summary>Coins (copper) in a waterlogged chest for a player of <paramref name="level"/>: level^2 x 20-60.</summary>
        public static long RollChestCoins(int level, Random rng)
        {
            int l = Math.Clamp(level, 1, 50);

            return (long)l * l * rng.Next(20, 61);
        }

        /// <summary>One chest in four also holds a random magic item of about the player's level.</summary>
        public static bool RollChestItem(Random rng)
        {
            return rng.Next(4) == 0;
        }

        public static IReadOnlyList<DbItemTemplate> AllTemplates()
        {
            var templates = new List<DbItemTemplate>();

            foreach (FishingDish dish in Dishes)
            {
                templates.Add(new DbItemTemplate
                {
                    Id_nb = dish.TemplateId,
                    Name = dish.Name,
                    Level = 1,
                    Object_Type = (int)eObjectType.GenericItem,
                    Item_Type = (int)eInventorySlot.FirstBackpack,
                    Model = dish.Model,
                    Weight = 5,
                    Price = dish.PriceCopper,
                    MaxCount = 20,
                    PackSize = 1,
                    IsPickable = true,
                    IsDropable = true,
                    IsTradable = true,
                    PackageID = FishingCatalog.PackageId,
                });
            }

            return templates;
        }

        /// <summary>Called from GamePlayer.UseSlot. True when the item was a fishing item (food, chest or camp kit).</summary>
        public static bool TryUse(GamePlayer player, DbInventoryItem item)
        {
            string id = item?.Id_nb;

            if (FishingCamp.IsCampKit(id))
            {
                FishingCamp.TryDeploy(player, item);

                return true;
            }

            FishingDish dish = FindDish(id);

            if (dish != null)
            {
                Eat(player, item, dish);

                return true;
            }

            if (id == ChestTemplateId)
            {
                OpenChest(player, item);

                return true;
            }

            return false;
        }

        private static void Eat(GamePlayer player, DbInventoryItem item, FishingDish dish)
        {
            if (!player.IsAlive)
            {
                return;
            }

            SpellLine line = SkillBase.GetSpellLine(GlobalSpellsLines.Potions_Effects);
            var handlers = new List<ISpellHandler>();

            foreach (int spellId in dish.SpellIds)
            {
                Spell spell = SkillBase.GetSpellByID(spellId);
                ISpellHandler handler = spell == null ? null : ScriptMgr.CreateSpellHandler(player, spell, line);

                if (handler != null)
                {
                    handlers.Add(handler);
                }
            }

            if (handlers.Count == 0 || !player.Inventory.RemoveCountFromStack(item, 1))
            {
                return;
            }

            player.Out.SendMessage($"You eat the {dish.Name.ToLowerInvariant()}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

            foreach (ISpellHandler handler in handlers)
            {
                handler.StartSpell(player);
            }
        }

        private static void OpenChest(GamePlayer player, DbInventoryItem item)
        {
            if (!player.IsAlive || player.InCombat)
            {
                player.Out.SendMessage("You can't open that right now.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            if (!player.Inventory.RemoveCountFromStack(item, 1))
            {
                return;
            }

            long coins = RollChestCoins(player.Level, Random.Shared);
            player.AddMoney(coins, "You pry open the waterlogged chest and find {0}!");
            InventoryLogging.LogInventoryAction("(fishing chest)", player, eInventoryActionType.Loot, coins);

            if (RollChestItem(Random.Shared))
            {
                player.Out.SendMessage("Something else glints at the bottom of the chest.", eChatType.CT_Important, eChatLoc.CL_SystemWindow);
                AtlasROGManager.GenerateROG(player, (byte)Math.Clamp((int)player.Level, 1, 51));
            }
        }

        /// <summary>/fish cook: cooks up to FishPerCook raw fish into food beside a burning campfire.</summary>
        public static void TryCook(GamePlayer player)
        {
            if (!FishingCamp.IsNearCampfire(player))
            {
                player.Out.SendMessage("You need a burning campfire to cook. Make camp with a camp kit, then try again.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            if (!player.IsAlive || player.InCombat || player.IsMoving)
            {
                player.Out.SendMessage("You can't cook right now.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            if (player.IsCrafting || (player.CraftTimer != null && player.CraftTimer.IsAlive))
            {
                player.Out.SendMessage("You must finish what you are working on first.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            if (CountRawFish(player) == 0)
            {
                player.Out.SendMessage("You have no raw fish to cook.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            var timer = new ECSGameTimer(player)
            {
                Callback = new ECSGameTimer.ECSTimerCallback(OnCooked)
            };
            timer.Properties.SetProperty(CookProperty, true);
            player.CraftTimer = timer;
            player.Out.SendTimerWindow("Cooking...", CookSeconds);
            player.Out.SendMessage("You set some fish over the fire.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            timer.Start(CookSeconds * 1000);
        }

        private static int CountRawFish(GamePlayer player)
        {
            int count = 0;

            foreach (DbInventoryItem item in player.Inventory.GetItemRange(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack))
            {
                if (DishFor(item?.Id_nb) != null)
                {
                    count += item.Count;
                }
            }

            return count;
        }

        private static int OnCooked(ECSGameTimer timer)
        {
            if (timer.Owner is not GamePlayer player || player.CraftTimer != timer)
            {
                return 0;
            }

            player.CraftTimer = null;
            player.Out.SendCloseTimerWindow();

            if (!player.IsAlive || !FishingCamp.IsNearCampfire(player))
            {
                player.Out.SendMessage("You need to stay by the fire to cook.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return 0;
            }

            var cooked = new Dictionary<FishingDish, int>();
            int left = FishPerCook;

            // A copy: removing a whole stack changes the inventory being walked.
            foreach (DbInventoryItem item in player.Inventory.GetItemRange(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack).ToList())
            {
                FishingDish dish = DishFor(item?.Id_nb);

                if (dish == null || left == 0)
                {
                    continue;
                }

                int take = Math.Min(left, item.Count);

                if (!player.Inventory.RemoveCountFromStack(item, take))
                {
                    continue;
                }

                cooked[dish] = cooked.GetValueOrDefault(dish) + take;
                left -= take;
            }

            foreach ((FishingDish dish, int count) in cooked)
            {
                DbItemTemplate template = GameServer.Database.FindObjectByKey<DbItemTemplate>(dish.TemplateId);

                if (template == null)
                {
                    continue;
                }

                if (!player.Inventory.AddTemplate(GameInventoryItem.Create(template), count, eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack))
                {
                    // Only a nearly full bag of part stacks gets here; the food goes on the ground rather than vanishing.
                    DbInventoryItem food = GameInventoryItem.Create(template);
                    food.Count = count;
                    player.CreateItemOnTheGround(food);
                    player.Out.SendMessage($"Your backpack is full, so you set the {dish.Name.ToLowerInvariant()} on the ground.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                }

                player.Out.SendMessage($"You cook {count} {dish.Name.ToLowerInvariant()}.", eChatType.CT_Important, eChatLoc.CL_SystemWindow);
            }

            return 0;
        }
    }
}
