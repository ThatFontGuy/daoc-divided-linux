using System;
using System.Linq;
using System.Text;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS.Fishing
{
    /// <summary>
    /// /fish craft: lists the FishingCraft recipes and makes one. It works like salvaging: the work runs on
    /// player.CraftTimer behind a progress bar, so moving, fighting or casting stops it, and the materials are only
    /// taken when it finishes. No crafting station is needed, so poles and camp kits can be made in the field.
    /// </summary>
    public static class FishingWorkbench
    {
        private const string RecipeProperty = "FISHING_RECIPE";
        private const eInventorySlot FirstBag = eInventorySlot.FirstBackpack;
        private const eInventorySlot LastBag = eInventorySlot.LastBackpack;

        public static void ShowRecipes(GamePlayer player)
        {
            int skill = FishingProgressStore.PeekSkill(player);
            player.Out.SendMessage($"Fishing skill: {skill} / {FishingCraft.MaxSkill}. Type /fish craft <number> to make one:", eChatType.CT_System, eChatLoc.CL_SystemWindow);

            for (int i = 0; i < FishingCraft.Recipes.Count; i++)
            {
                FishingRecipe recipe = FishingCraft.Recipes[i];
                string state = skill < recipe.RequiredSkill ? $"needs skill {recipe.RequiredSkill}" : skill >= recipe.RequiredSkill + FishingCraft.RecipeGreyMargin ? "grey" : "teaches skill";
                player.Out.SendMessage($"{i + 1}. {recipe.Name} ({state}): {DescribeMaterials(player, recipe)}", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            }

            player.Out.SendMessage("Materials are sold by crafting merchants in every realm.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        public static void TryCraft(GamePlayer player, string number)
        {
            if (!int.TryParse(number, out int index) || index < 1 || index > FishingCraft.Recipes.Count)
            {
                ShowRecipes(player);

                return;
            }

            FishingRecipe recipe = FishingCraft.Recipes[index - 1];

            if (!player.IsAlive || player.InCombat)
            {
                player.Out.SendMessage("You can't do that right now.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            if (player.IsCrafting || (player.CraftTimer != null && player.CraftTimer.IsAlive))
            {
                player.Out.SendMessage("You must finish what you are working on first.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            if (player.IsMoving)
            {
                player.Out.SendMessage("You must stand still to do that.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            if (!CanMake(player, recipe))
            {
                return;
            }

            int seconds = Math.Max(1, (int)Math.Round(recipe.CraftSeconds / Math.Max(0.1, player.CraftingSpeed)));
            var timer = new ECSGameTimer(player)
            {
                Callback = new ECSGameTimer.ECSTimerCallback(OnFinished)
            };
            timer.Properties.SetProperty(RecipeProperty, recipe);
            player.CraftTimer = timer;
            player.Out.SendTimerWindow($"Making {recipe.Name}", seconds);
            player.Out.SendMessage($"You begin work on a {recipe.Name}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            timer.Start(seconds * 1000);
        }

        private static int OnFinished(ECSGameTimer timer)
        {
            GamePlayer player = timer.Owner as GamePlayer;
            FishingRecipe recipe = timer.Properties.GetProperty<FishingRecipe>(RecipeProperty);

            if (player == null || recipe == null || player.CraftTimer != timer)
            {
                return 0;
            }

            player.CraftTimer = null;
            player.Out.SendCloseTimerWindow();

            if (!player.IsAlive || !CanMake(player, recipe))
            {
                return 0;
            }

            DbItemTemplate template = GameServer.Database.FindObjectByKey<DbItemTemplate>(recipe.ResultTemplateId);

            if (template == null)
            {
                player.Out.SendMessage($"The {recipe.Name} can't be made right now.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return 0;
            }

            foreach (FishingMaterial material in recipe.Materials)
            {
                if (!TakeMaterial(player, material))
                {
                    player.Out.SendMessage($"You are missing {material.Name}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                    return 0;
                }
            }

            DbInventoryItem item = GameInventoryItem.Create(template);
            item.IsCrafted = true;
            item.Creator = player.Name;

            if (!player.Inventory.AddItem(eInventorySlot.FirstEmptyBackpack, item))
            {
                // The materials were made into the item already; it goes on the ground rather than vanishing.
                player.CreateItemOnTheGround(item);
                player.Out.SendMessage($"Your backpack is full, so you set the {recipe.Name} on the ground.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            }
            else
            {
                InventoryLogging.LogInventoryAction("(fishing craft)", player, eInventoryActionType.Craft, item.Template, item.Count);
            }

            player.Out.SendMessage($"You successfully make a {recipe.Name}!", eChatType.CT_Important, eChatLoc.CL_SystemWindow);

            FishingProgress progress = FishingProgressStore.Load(player);
            FishingSkill.Gain(player, progress, FishingCraft.RollCraftGain(progress.Skill, recipe, Random.Shared));

            return 0;
        }

        private static bool CanMake(GamePlayer player, FishingRecipe recipe)
        {
            int skill = FishingProgressStore.PeekSkill(player);

            if (skill < recipe.RequiredSkill)
            {
                player.Out.SendMessage($"You need {recipe.RequiredSkill} fishing skill to make a {recipe.Name}. You have {skill}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return false;
            }

            foreach (FishingMaterial material in recipe.Materials)
            {
                int have = CountMaterial(player, material);

                if (have < material.Count)
                {
                    player.Out.SendMessage($"You need {material.Count} {material.Name} for a {recipe.Name} (you have {have}).", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                    return false;
                }
            }

            return true;
        }

        // The stock world has several templates per material, all with the same name: one per merchant list
        // (cured_leather_squares, cured_leather_square3...) plus the leather/cloth/wood conversion results. Any of them
        // counts, matched by name (FishingMaterial.Name is the stock name).
        private static bool IsMaterial(DbInventoryItem item, FishingMaterial material)
        {
            return item != null && string.Equals(item.Name, material.Name, StringComparison.OrdinalIgnoreCase);
        }

        private static int CountMaterial(GamePlayer player, FishingMaterial material)
        {
            return player.Inventory.GetItemRange(FirstBag, LastBag).Where(item => IsMaterial(item, material)).Sum(item => item.Count);
        }

        // Caller has checked CountMaterial. Takes from as many stacks as it needs.
        private static bool TakeMaterial(GamePlayer player, FishingMaterial material)
        {
            int left = material.Count;

            foreach (DbInventoryItem item in player.Inventory.GetItemRange(FirstBag, LastBag).Where(item => IsMaterial(item, material)).ToList())
            {
                int take = Math.Min(left, item.Count);

                if (player.Inventory.RemoveCountFromStack(item, take))
                {
                    left -= take;
                }

                if (left == 0)
                {
                    return true;
                }
            }

            return false;
        }

        private static string DescribeMaterials(GamePlayer player, FishingRecipe recipe)
        {
            var text = new StringBuilder();

            foreach (FishingMaterial material in recipe.Materials)
            {
                if (text.Length > 0)
                {
                    text.Append(", ");
                }

                int have = CountMaterial(player, material);
                text.Append($"{material.Count} {material.Name} ({have})");
            }

            return text.ToString();
        }
    }
}
