using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using DOL.Database;
using DOL.GS.ServerProperties;
using DOL.Logging;

namespace DOL.GS;

/// <summary>
/// Gamebots craft for real. A bot joins an order at its realm's craft master, buys the recipe's materials from a merchant
/// with its own coin, works at a real forge or lathe, gains skill by the same tables a player does and ends up with real
/// items, which it wears when they are upgrades and otherwise posts on the Realm Exchange at its next stop there. Skill
/// lives in <see cref="OfflineWorldBotRecord.SerializedCraftingSkills"/> ("skill|value;skill|value", the primary craft
/// first, the format of DbAccountXCrafting). The trip is the executor of <see cref="eAutonomousActivity.Craft"/>;
/// the world controller owns the walking (AutonomousWorldBotController.Crafting.cs).
/// </summary>
public static class AutonomousBotCrafting
{
    private static readonly Logger Log = LoggerManager.Create(typeof(AutonomousBotCrafting));

    [ServerProperty("autonomous", "bot_crafting", "Gamebots train a craft, buy materials, work at real stations and sell what they make.", true)]
    public static bool Enabled = true;

    /// <summary>Chance, at a task break, that a bot with no craft goes to join an order.</summary>
    public const double TrainChance = 0.10;
    /// <summary>Chance, at a task break, that a crafter goes shopping for a session.</summary>
    public const double SessionChance = 0.15;
    public const int MinimumBotLevel = 5;
    /// <summary>Items made on one trip; a session is an errand between tasks, not a career.</summary>
    public const int CraftsPerSession = 6;
    /// <summary>A session spends at most this share of the bot's coin.</summary>
    public const double ShareOfCoin = 0.25;
    public const int SubSkillCap = AbstractCraftingSkill.subSkillCap;

    /// <summary>The crafts a bot can follow; alchemy and spellcraft need tinctures and gem work no bot uses yet.</summary>
    public static readonly eCraftingSkill[] Professions =
    [
        eCraftingSkill.WeaponCrafting, eCraftingSkill.ArmorCrafting, eCraftingSkill.Tailoring, eCraftingSkill.Fletching,
    ];

    public sealed record Choice(Recipe Recipe, int Skill, int Make, int Gain);

    /// <summary>What one trip makes. <paramref name="OrderId"/> is set when the piece was commissioned by another bot
    /// (<see cref="AutonomousBotCraftOrders"/>).</summary>
    public sealed record Session(Recipe Recipe, eCraftingSkill Skill, int Copies, string OrderId = null);

    public sealed record Purchase(DbItemTemplate Material, int Packs, long Copper);

    private sealed class Catalog
    {
        public Dictionary<eCraftingSkill, List<Recipe>> Recipes = new();
        public HashSet<string> Materials = new(StringComparer.OrdinalIgnoreCase);
        public Dictionary<eCraftingSkill, HashSet<string>> MaterialsBySkill = new();
        public Dictionary<string, List<GameMerchant>> Sellers = new(StringComparer.OrdinalIgnoreCase);
        public List<CraftNPC> Masters = new();
        public List<GameStaticItem> Forges = new();
        public List<GameStaticItem> Lathes = new();
        public bool AllOnSaleForTests;
    }

    private static volatile Catalog _catalog;
    private static int _loading;
    /// <summary>The between-task assignment whose craft trip is over, per bot.</summary>
    private static readonly ConcurrentDictionary<long, string> FinishedTrips = new();

    #region Skills

    /// <summary>Reads the skills in saved order; the first is the primary craft.</summary>
    public static List<KeyValuePair<eCraftingSkill, int>> ParseSkills(string saved)
    {
        var skills = new List<KeyValuePair<eCraftingSkill, int>>();
        foreach (string entry in (saved ?? string.Empty).Split(';', StringSplitOptions.RemoveEmptyEntries))
        {
            string[] parts = entry.Split('|');
            if (parts.Length == 2 && int.TryParse(parts[0], out int id) && int.TryParse(parts[1], out int value) &&
                Enum.IsDefined(typeof(eCraftingSkill), id) && id != 0 && skills.All(pair => pair.Key != (eCraftingSkill)id))
                skills.Add(new((eCraftingSkill)id, value));
        }
        return skills;
    }

    public static string SerializeSkills(IEnumerable<KeyValuePair<eCraftingSkill, int>> skills) =>
        string.Join(";", skills.Select(pair => $"{(int)pair.Key}|{pair.Value}"));

    public static int SkillValue(string saved, eCraftingSkill skill) =>
        ParseSkills(saved).FirstOrDefault(pair => pair.Key == skill).Value;

    public static eCraftingSkill Primary(string saved) =>
        ParseSkills(saved).Select(pair => pair.Key).FirstOrDefault();

    /// <summary>Joining an order: the primary craft first, then what the order's master teaches, each at 1.</summary>
    public static string Join(eCraftingSkill primary, IEnumerable<eCraftingSkill> taught)
    {
        var skills = new List<KeyValuePair<eCraftingSkill, int>> { new(primary, 1) };
        foreach (eCraftingSkill skill in taught)
            if (skill != primary)
                skills.Add(new(skill, 1));
        return SerializeSkills(skills);
    }

    /// <summary>One more point in a skill; secondary skills stop at the sub-skill cap.</summary>
    public static string Gain(string saved, eCraftingSkill skill, bool primaryWork)
    {
        List<KeyValuePair<eCraftingSkill, int>> skills = ParseSkills(saved);
        int index = skills.FindIndex(pair => pair.Key == skill);
        if (index < 0)
            return saved;
        int value = skills[index].Value;
        if (!primaryWork && value >= SubSkillCap)
            return saved;
        skills[index] = new(skill, value + 1);
        return SerializeSkills(skills);
    }

    /// <summary>Which craft a class follows: archers fletch, casters tailor, the rest split between weapons and armor.</summary>
    public static eCraftingSkill ProfessionFor(eCharacterClass characterClass, eClassType classType, long botId)
    {
        if (characterClass is eCharacterClass.Scout or eCharacterClass.Hunter or eCharacterClass.Ranger)
            return eCraftingSkill.Fletching;
        if (classType == eClassType.ListCaster)
            return eCraftingSkill.Tailoring;
        return botId % 2 == 0 ? eCraftingSkill.WeaponCrafting : eCraftingSkill.ArmorCrafting;
    }

    public static void ForgetTrip(GameBot bot) => FinishedTrips.TryRemove(bot.DatabaseID, out _);

    public static void MarkTripDone(GameBot bot) => FinishedTrips[bot.DatabaseID] = bot.PersistentRecord?.ObjectiveAssignmentId ?? string.Empty;

    public static bool TripDone(GameBot bot) =>
        FinishedTrips.TryGetValue(bot.DatabaseID, out string assignment) && assignment == bot.PersistentRecord?.ObjectiveAssignmentId;

    public static bool IsTrained(GameBot bot) => !string.IsNullOrWhiteSpace(bot?.PersistentRecord?.SerializedCraftingSkills);

    #endregion

    #region Rules

    /// <summary>The station a recipe needs, by the rules of the crafts' CheckForTools: "forge", "lathe" or none.</summary>
    public static string StationFor(eCraftingSkill skill, int productObjectType, IEnumerable<int> materialModels) => skill switch
    {
        eCraftingSkill.WeaponCrafting or eCraftingSkill.ArmorCrafting or eCraftingSkill.MetalWorking => "forge",
        eCraftingSkill.Tailoring => materialModels.Contains(519) ? "forge" : null,
        eCraftingSkill.Fletching => productObjectType is (int)eObjectType.Arrow or (int)eObjectType.Bolt ? null : "lathe",
        _ => null,
    };

    /// <summary>The secondary skills a recipe asks for are high enough (CheckSecondCraftingSkillRequirement).</summary>
    public static bool MeetsSecondaryRequirement(AbstractCraftingSkill craft, Recipe recipe, string saved)
    {
        int minimum = craft.GetSecondaryCraftingSkillMinimumLevel(recipe);
        if (minimum <= 0)
            return true;
        foreach (Ingredient ingredient in recipe.Ingredients)
        {
            eCraftingSkill secondary = AbstractCraftingSkill.SecondarySkillForMaterial(ingredient.Material.Model);
            if (secondary != eCraftingSkill.NoCrafting && SkillValue(saved, secondary) < minimum)
                return false;
        }
        return true;
    }

    /// <summary>Recipes whose expected points per attempt are within this share of the best count as a tie: an orange
    /// recipe (84% to make, 55% to gain) and a red one (68%, 65%) teach about the same, so the harder one is taken.</summary>
    public const double GainTieShare = 0.95;
    /// <summary>A piece is useful to a wearer up to this many levels below the wearer's own level.</summary>
    public const int UsefulLevelWindow = 10;

    /// <summary>
    /// The recipe worth making at this skill, by the player's own tables (ChanceToMakeAt and BaseChanceToGainAt): only
    /// recipes that can still teach a point and be made, that the bot can pay for, from its own realm and with the
    /// materials on sale. Among those that teach about the best (<see cref="GainTieShare"/>), a piece the bot or its
    /// group could use comes first, then the hardest recipe, then the cheapest. Run of 2026-11-01: the cheapest-first
    /// rule kept level 45 crafters on level 1 gear and the top skill at 12.
    /// </summary>
    public static Choice ChooseRecipe(IEnumerable<Recipe> recipes, AbstractCraftingSkill craft, string saved, eRealm realm,
        long coin, Func<Recipe, bool> onSale, Func<Recipe, bool> useful = null)
    {
        int skill = SkillValue(saved, craft.eSkill);
        var teaching = new List<Choice>();
        foreach (Recipe recipe in recipes)
        {
            if (recipe.Product.Realm != 0 && recipe.Product.Realm != (int)realm)
                continue;
            int make = craft.ChanceToMakeAt(skill, recipe.Level);
            int gain = craft.BaseChanceToGainAt(skill, recipe.Level);
            if (make <= 0 || gain <= 0 || recipe.CostToCraft > coin || !MeetsSecondaryRequirement(craft, recipe, saved) || !onSale(recipe))
                continue;
            teaching.Add(new Choice(recipe, skill, make, gain));
        }
        if (teaching.Count == 0)
            return null;
        int best = teaching.Max(choice => choice.Make * choice.Gain);
        return teaching
            .Where(choice => choice.Make * choice.Gain >= best * GainTieShare)
            .OrderByDescending(choice => useful?.Invoke(choice.Recipe) == true)
            .ThenByDescending(choice => choice.Recipe.Level)
            .ThenBy(choice => choice.Recipe.CostToCraft)
            .First();
    }

    /// <summary>A piece fits a wearer of this level: no higher than the level, and not more than the window below it.</summary>
    public static bool FitsLevel(int productLevel, int wearerLevel) =>
        productLevel <= wearerLevel && productLevel + UsefulLevelWindow >= wearerLevel;

    /// <summary>
    /// Whether a wearer could put this product on or wield it now: armor and weapons of its level window that its class
    /// may use (a gamebot's melee weapons by its configured weapon skills, everything else by the server's item rules).
    /// </summary>
    public static bool CouldUse(GameLiving wearer, DbItemTemplate product)
    {
        if (wearer == null || product == null || product.IsStackable || !FitsLevel(product.Level, wearer.Level))
            return false;
        var type = (eObjectType)product.Object_Type;
        bool armor = type is >= eObjectType._FirstArmor and <= eObjectType._LastArmor || type == eObjectType.Shield;
        bool weapon = type is >= eObjectType._FirstWeapon and <= eObjectType._LastWeapon;
        if (!armor && !weapon)
            return false;
        try
        {
            if (wearer is GameBot bot && BotWeaponStats.IsMeleeWeapon(type))
                return BotWeaponStats.IsConfiguredMeleeWeapon(bot, product);
            return GameServer.ServerRules.CheckAbilityToUseItem(wearer, product);
        }
        catch
        {
            return false;
        }
    }

    /// <summary>The bot and its group members, the people a crafter's work is useful to.</summary>
    public static Func<Recipe, bool> UsefulTo(GameBot bot)
    {
        GameLiving[] wearers = bot?.Group?.GetMembersInTheGroup().Where(member => member != null).ToArray() ?? [];
        if (bot != null && !wearers.Contains(bot))
            wearers = wearers.Append(bot).ToArray();
        return recipe => wearers.Any(wearer => CouldUse(wearer, recipe.Product));
    }

    /// <summary>What must be bought for <paramref name="copies"/> of a recipe, given what the bot carries.</summary>
    public static List<Purchase> Shopping(Recipe recipe, int copies, Func<DbItemTemplate, int> carried)
    {
        var list = new List<Purchase>();
        foreach (Ingredient ingredient in recipe.Ingredients)
        {
            int missing = ingredient.Count * copies - carried(ingredient.Material);
            if (missing <= 0)
                continue;
            int pack = Math.Max(1, ingredient.Material.PackSize);
            int packs = (missing + pack - 1) / pack;
            list.Add(new Purchase(ingredient.Material, packs, packs * ingredient.Material.Price));
        }
        return list;
    }

    /// <summary>How many copies the bot's coin share pays for, within a session.</summary>
    public static int CopiesFor(Recipe recipe, long coin)
    {
        long budget = (long)(coin * ShareOfCoin);
        long cost = Math.Max(1, recipe.CostToCraft);
        return (int)Math.Clamp(budget / cost, 0, CraftsPerSession);
    }

    /// <summary>Whether a task break becomes a craft trip. A crafter with materials goes by the engine's rule.</summary>
    public static bool WantsTrip(bool trained, int level, int materialStacks, double roll)
    {
        if (!Enabled || level < MinimumBotLevel)
            return false;
        if (!trained)
            return roll < TrainChance;
        return AutonomousBotDecisionEngine.RollsCraft(true, materialStacks, roll) || roll < SessionChance;
    }

    #endregion

    #region Catalog

    private static Catalog EnsureCatalog()
    {
        Catalog catalog = _catalog;
        if (catalog == null && Interlocked.Exchange(ref _loading, 1) == 0)
            Task.Run(() =>
            {
                try
                {
                    _catalog = BuildCatalog();
                }
                catch (Exception exception)
                {
                    Log.Error("Gamebot crafting catalog failed; bots do not craft", exception);
                    _catalog = new Catalog();
                }
            });
        return catalog;
    }

    private static Catalog BuildCatalog()
    {
        var catalog = new Catalog();
        var wanted = new HashSet<eCraftingSkill>(Professions)
        {
            eCraftingSkill.MetalWorking, eCraftingSkill.LeatherCrafting, eCraftingSkill.ClothWorking, eCraftingSkill.WoodWorking,
        };
        ILookup<string, DbCraftedXItem> ingredients = GameServer.Database.SelectAllObjects<DbCraftedXItem>()
            .ToLookup(row => row.CraftedItemId_nb, StringComparer.OrdinalIgnoreCase);
        foreach (DbCraftedItem row in GameServer.Database.SelectAllObjects<DbCraftedItem>())
        {
            var skill = (eCraftingSkill)row.CraftingSkillType;
            if (!wanted.Contains(skill))
                continue;
            DbItemTemplate product = GameServer.Database.FindObjectByKey<DbItemTemplate>(row.Id_nb);
            if (product == null || !ingredients[row.Id_nb].Any())
                continue;
            var parts = new List<Ingredient>();
            foreach (DbCraftedXItem part in ingredients[row.Id_nb])
                if (GameServer.Database.FindObjectByKey<DbItemTemplate>(part.IngredientId_nb) is DbItemTemplate material)
                    parts.Add(new Ingredient(part.Count, material));
            if (parts.Count != ingredients[row.Id_nb].Count())
                continue;
            bool makeTemplated = row.MakeTemplated || product.IsStackable;
            var recipe = new Recipe(product, parts, skill, row.CraftingLevel, makeTemplated);
            if (!catalog.Recipes.TryGetValue(skill, out List<Recipe> list))
                catalog.Recipes[skill] = list = new List<Recipe>();
            list.Add(recipe);
            if (!catalog.MaterialsBySkill.TryGetValue(skill, out HashSet<string> materials))
                catalog.MaterialsBySkill[skill] = materials = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (Ingredient part in parts)
            {
                materials.Add(part.Material.Id_nb);
                catalog.Materials.Add(part.Material.Id_nb);
            }
        }
        foreach (Region region in WorldMgr.GetAllRegions())
        {
            if (region == null || region.IsHousing)
                continue;
            foreach (GameMerchant merchant in region.Merchants)
            {
                if (!AutonomousBotEconomy.SellsForCoin(merchant) || merchant.TradeItems == null)
                    continue;
                foreach (DbItemTemplate item in merchant.TradeItems.GetAllItems().Values.OfType<DbItemTemplate>())
                {
                    if (!catalog.Materials.Contains(item.Id_nb))
                        continue;
                    if (!catalog.Sellers.TryGetValue(item.Id_nb, out List<GameMerchant> sellers))
                        catalog.Sellers[item.Id_nb] = sellers = new List<GameMerchant>();
                    sellers.Add(merchant);
                }
            }
            foreach (GameObject item in region.Objects)
            {
                if (item is CraftNPC master)
                    catalog.Masters.Add(master);
                else if (item is GameStaticItem station)
                {
                    if (IsForge(station))
                        catalog.Forges.Add(station);
                    else if (IsLathe(station))
                        catalog.Lathes.Add(station);
                }
            }
        }
        if (Log.IsInfoEnabled)
            Log.Info($"AUTONOMOUS_CRAFT_CATALOG recipes={catalog.Recipes.Values.Sum(list => list.Count)} " +
                     $"materials={catalog.Materials.Count} onSale={catalog.Sellers.Count} masters={catalog.Masters.Count} " +
                     $"forges={catalog.Forges.Count} lathes={catalog.Lathes.Count}");
        return catalog;
    }

    private static bool IsForge(GameStaticItem item) => item.Model == 478 || item.Name.Equals("forge", StringComparison.OrdinalIgnoreCase);

    private static bool IsLathe(GameStaticItem item) => item.Model == 481 || item.Name.Equals("lathe", StringComparison.OrdinalIgnoreCase);

    public static IEnumerable<CraftNPC> MastersOf(eCraftingSkill skill, eRealm realm) =>
        EnsureCatalog()?.Masters.Where(master => master.TheCraftingSkill == skill && master.ObjectState == GameObject.eObjectState.Active &&
            (master.Realm == eRealm.None || master.Realm == realm)) ?? [];

    public static IEnumerable<GameStaticItem> Stations(string station) =>
        (station == "forge" ? EnsureCatalog()?.Forges : EnsureCatalog()?.Lathes) ?? [];

    public static IEnumerable<GameMerchant> Sellers(DbItemTemplate material, eRealm realm) =>
        EnsureCatalog() is Catalog catalog && catalog.Sellers.TryGetValue(material.Id_nb, out List<GameMerchant> sellers)
            ? sellers.Where(merchant => merchant.ObjectState == GameObject.eObjectState.Active &&
                                        (merchant.Realm == eRealm.None || merchant.Realm == realm))
            : [];

    /// <summary>Whether this stack is material for a craft the bot knows. While the catalog loads every stack counts,
    /// so nothing is sold by mistake on a bot's first stop after a start-up.</summary>
    public static bool IsMaterialFor(GameBot bot, DbInventoryItem item)
    {
        if (!IsTrained(bot) || item == null || !item.IsStackable)
            return false;
        Catalog catalog = EnsureCatalog();
        if (catalog == null)
            return true;
        foreach (KeyValuePair<eCraftingSkill, int> skill in ParseSkills(bot.PersistentRecord.SerializedCraftingSkills))
            if (catalog.MaterialsBySkill.TryGetValue(skill.Key, out HashSet<string> materials) && materials.Contains(item.Id_nb))
                return true;
        return false;
    }

    /// <summary>A finished piece this bot made.</summary>
    public static bool IsOwnWork(GameBot bot, DbInventoryItem item) =>
        item != null && item.IsCrafted && !item.IsStackable && item.Creator == bot?.Name;

    /// <summary>Pieces of its own work the bot still carries, unsold (a commissioned piece waiting for its buyer is not).</summary>
    public static int UnsoldWork(GameBot bot) =>
        bot?.Inventory == null ? 0 : bot.Inventory.GetItemRange(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack)
            .Count(item => IsOwnWork(bot, item) && !AutonomousBotCraftOrders.IsHeldForOrder(item));

    /// <summary>Recipes of one craft in the catalog (empty while it loads).</summary>
    public static IReadOnlyList<Recipe> RecipesOf(eCraftingSkill skill) =>
        EnsureCatalog() is Catalog catalog && catalog.Recipes.TryGetValue(skill, out List<Recipe> recipes) ? recipes : [];

    /// <summary>Whether every material of a recipe is sold for coin by a merchant of this realm.</summary>
    public static bool OnSale(Recipe recipe, eRealm realm) =>
        EnsureCatalog() is Catalog catalog && (catalog.AllOnSaleForTests || recipe.Ingredients.All(part => catalog.Sellers.TryGetValue(part.Material.Id_nb, out var sellers) &&
            sellers.Any(merchant => merchant.Realm == eRealm.None || merchant.Realm == realm)));

    /// <summary>Material stacks the bot carries, for the decision to craft.</summary>
    public static int MaterialStacks(GameBot bot)
    {
        if (!IsTrained(bot) || bot.Inventory == null)
            return 0;
        return bot.Inventory.GetItemRange(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack).Count(item => IsMaterialFor(bot, item));
    }

    #endregion

    #region Working

    private static int CarriedMaterial(GameBot bot, DbItemTemplate material) =>
        bot.Inventory.GetItemRange(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack)
            .Where(item => item != null && item.Name == material.Name).Sum(item => item.Count);

    public static void Train(GameBot bot, CraftNPC master)
    {
        OfflineWorldBotRecord record = bot.PersistentRecord;
        record.SerializedCraftingSkills = Join(master.TheCraftingSkill, master.TrainedSkills);
        bot.MarkAutonomousStateDirty();
        AutonomousBotStatusPersistence.Queue(bot, true);
        AutonomousBotEconomy.MarkInventoryChanged(bot);
        AutonomousStuckWatchdog.MarkProgress(bot, eAutonomousProgressKind.Crafting);
        Log.Info($"AUTONOMOUS_CRAFT_TRAINED bot=\"{bot.Name}\" id={bot.DatabaseID} level={bot.Level} craft={master.TheCraftingSkill} master=\"{master.Name}\"");
    }

    /// <summary>What the bot sets out to make now, or null when nothing fits its skill, coin or the market.</summary>
    public static Session PlanSession(GameBot bot)
    {
        Catalog catalog = EnsureCatalog();
        string saved = bot.PersistentRecord?.SerializedCraftingSkills;
        if (catalog == null || string.IsNullOrWhiteSpace(saved))
            return null;
        long coin = AutonomousBotEconomy.GetMoney(bot.DatabaseID);
        // A piece another bot paid for is made first, with the crafter's own materials (AutonomousBotCraftOrders).
        if (AutonomousBotCraftOrders.PlanOrder(bot, coin) is Session order)
            return order;
        // A session's worth still waiting for the Realm Exchange: selling it comes first.
        if (UnsoldWork(bot) >= CraftsPerSession)
            return null;
        bool Sold(Recipe recipe) => OnSale(recipe, bot.Realm);
        Func<Recipe, bool> useful = UsefulTo(bot);
        foreach (KeyValuePair<eCraftingSkill, int> skill in ParseSkills(saved))
        {
            if (CraftingMgr.getSkillbyEnum(skill.Key) is not AbstractCraftingSkill craft || !catalog.Recipes.TryGetValue(skill.Key, out List<Recipe> recipes))
                continue;
            // A primary craft held back by its secondary skills finds no recipe here, and the next skill in the list trains them.
            Choice choice = ChooseRecipe(recipes, craft, saved, bot.Realm, (long)(coin * ShareOfCoin), Sold, useful);
            if (choice == null)
                continue;
            int copies = CopiesFor(choice.Recipe, coin);
            if (copies > 0)
                return new Session(choice.Recipe, skill.Key, copies);
        }
        return null;
    }

    public static List<Purchase> ShoppingFor(GameBot bot, Session session) =>
        Shopping(session.Recipe, session.Copies, material => CarriedMaterial(bot, material));

    /// <summary>Buys one material from a real merchant the bot stands beside, at the merchant's price, as GameMerchant does.</summary>
    public static bool TryBuy(GameBot bot, GameMerchant merchant, Purchase purchase)
    {
        if (bot?.Inventory == null || merchant == null ||
            !merchant.IsWithinRadius(bot, Properties.WORLD_PICKUP_DISTANCE) || !AutonomousBotEconomy.TrySpend(bot.DatabaseID, purchase.Copper))
            return false;
        int amount = purchase.Packs * Math.Max(1, purchase.Material.PackSize);
        if (!bot.Inventory.AddTemplate(GameInventoryItem.Create(purchase.Material), amount, eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack))
        {
            AutonomousBotEconomy.AddMoney(bot.DatabaseID, purchase.Copper);
            return false;
        }
        AutonomousBotEconomy.MarkInventoryChanged(bot);
        bot.MarkAutonomousStateDirty();
        AutonomousBotStatusPersistence.Queue(bot, true);
        AutonomousStuckWatchdog.MarkProgress(bot, eAutonomousProgressKind.Money);
        RunTelemetry.Trade(bot, "craft-materials", merchant, null, purchase.Copper, amount);
        return true;
    }

    /// <summary>Seconds one attempt takes, by the craft's own clock and the server's crafting speed.</summary>
    public static int WorkSeconds(GameBot bot, Session session)
    {
        AbstractCraftingSkill craft = CraftingMgr.getSkillbyEnum(session.Skill);
        int skill = SkillValue(bot.PersistentRecord.SerializedCraftingSkills, session.Skill);
        double speed = Math.Max(0.01, Properties.CRAFTING_SPEED);
        return Math.Max(1, (int)(craft.CraftingTimeAt(skill, session.Recipe, bot.Realm) / speed));
    }

    /// <summary>
    /// One attempt, by CraftAction's rules: a failure costs nothing, a success takes the materials, makes the item and may
    /// teach a point. Returns the item made, or null.
    /// </summary>
    public static DbInventoryItem Attempt(GameBot bot, Session session, out bool failed)
    {
        failed = false;
        AbstractCraftingSkill craft = CraftingMgr.getSkillbyEnum(session.Skill);
        OfflineWorldBotRecord record = bot.PersistentRecord;
        int skill = SkillValue(record.SerializedCraftingSkills, session.Skill);
        Recipe recipe = session.Recipe;
        if (Shopping(recipe, 1, material => CarriedMaterial(bot, material)).Count > 0 ||
            !recipe.Product.IsStackable && bot.Inventory.FindFirstEmptySlot(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack) == eInventorySlot.Invalid)
        {
            failed = true;
            return null;
        }
        if (!Util.Chance(craft.ChanceToMakeAt(skill, recipe.Level)))
            return null;

        foreach (Ingredient ingredient in recipe.Ingredients)
            TakeMaterial(bot, ingredient);
        DbInventoryItem item = MakeProduct(bot, craft, recipe, skill);
        if (item == null)
        {
            failed = true;
            return null;
        }
        GainPoints(bot, craft, session, recipe);
        if (BotDiagnostics.Enabled) Log.Info($"AUTONOMOUS_CRAFT_MADE bot=\"{bot.Name}\" id={bot.DatabaseID} level={bot.Level} craft={session.Skill} skill={skill} " +
                 $"recipeLevel={recipe.Level} item=\"{item.Name}\" itemId=\"{item.Id_nb}\" quality={item.Quality}");
        AutonomousBotEconomy.MarkInventoryChanged(bot);
        bot.MarkAutonomousStateDirty();
        AutonomousBotStatusPersistence.Queue(bot, true);
        AutonomousStuckWatchdog.MarkProgress(bot, eAutonomousProgressKind.Crafting);
        // A commissioned piece is the buyer's: it waits in the bag for delivery and is never worn by its maker.
        if (session.OrderId != null && !item.IsStackable)
            AutonomousBotCraftOrders.OnMade(bot, session.OrderId, item);
        else if (!item.IsStackable)
            AutonomousBotEconomy.TryEquipOwnedUpgrade(bot, item, "crafted");
        return item;
    }

    private static void TakeMaterial(GameBot bot, Ingredient ingredient)
    {
        int count = ingredient.Count;
        foreach (DbInventoryItem item in bot.Inventory.GetItemRange(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack).ToList())
        {
            if (count <= 0 || item == null || item.Name != ingredient.Material.Name)
                continue;
            int take = Math.Min(count, item.Count);
            if (item.Count > take ? bot.Inventory.RemoveCountFromStack(item, take) : bot.Inventory.RemoveItem(item))
                count -= take;
        }
    }

    private static DbInventoryItem MakeProduct(GameBot bot, AbstractCraftingSkill craft, Recipe recipe, int skill)
    {
        DbItemTemplate product = recipe.Product;
        int count = Math.Max(1, product.PackSize);
        if (product.IsStackable)
        {
            DbInventoryItem stack = GameInventoryItem.Create(product);
            stack.IsCrafted = true;
            stack.Creator = bot.Name;
            return bot.Inventory.AddTemplate(stack, count, eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack) ? stack : null;
        }
        DbInventoryItem item;
        if (recipe.IsForUniqueProduct)
        {
            item = GameInventoryItem.Create(new DbItemUnique(product));
            item.Quality = craft.QualityAt(skill, recipe.Level);
        }
        else
            item = GameInventoryItem.Create(product);
        item.IsCrafted = true;
        item.Creator = bot.Name;
        item.Count = count;
        return bot.Inventory.AddItem(eInventorySlot.FirstEmptyBackpack, item) ? item : null;
    }

    private static void GainPoints(GameBot bot, AbstractCraftingSkill craft, Session session, Recipe recipe)
    {
        OfflineWorldBotRecord record = bot.PersistentRecord;
        int chance = craft.BaseChanceToGainAt(SkillValue(record.SerializedCraftingSkills, session.Skill), recipe.Level);
        if (chance > 0 && bot.CurrentRegion?.IsCapitalCity == true)
            chance = Math.Clamp(chance + Properties.CAPITAL_CITY_CRAFTING_SKILL_GAIN_BONUS, 0, 100);
        if (!Util.Chance(chance))
            return;
        bool profession = Professions.Contains(session.Skill);
        string saved = Gain(record.SerializedCraftingSkills, session.Skill, profession);
        if (profession)
            foreach (Ingredient ingredient in recipe.Ingredients)
            {
                eCraftingSkill secondary = AbstractCraftingSkill.SecondarySkillForMaterial(ingredient.Material.Model);
                if (secondary != eCraftingSkill.NoCrafting)
                    saved = Gain(saved, secondary, false);
            }
        record.SerializedCraftingSkills = saved;
    }

    #endregion

    /// <summary>Tests only.</summary>
    public static void SetCatalogForTests(IEnumerable<Recipe> recipes, eCraftingSkill skill, bool allOnSale = false)
    {
        var catalog = new Catalog { AllOnSaleForTests = allOnSale };
        Recipe[] all = recipes.ToArray();
        catalog.Recipes[skill] = all.ToList();
        catalog.MaterialsBySkill[skill] = new HashSet<string>(all.SelectMany(recipe => recipe.Ingredients).Select(part => part.Material.Id_nb), StringComparer.OrdinalIgnoreCase);
        catalog.Materials.UnionWith(catalog.MaterialsBySkill[skill]);
        _catalog = catalog;
        Interlocked.Exchange(ref _loading, 1);
    }
}
