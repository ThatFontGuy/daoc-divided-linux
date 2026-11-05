using System;
using System.Collections.Generic;
using DOL.Database;

namespace DOL.GS.Fishing
{
    /// <summary>One fishing pole tier: the skill to craft it, the skill it lets you reach and the bonus it gives.</summary>
    public sealed class FishingPoleTier
    {
        public string TemplateId;
        public string Name;
        public int Model;

        /// <summary>Fishing skill needed to craft the pole. Anyone can fish with any pole.</summary>
        public int RequiredSkill;

        /// <summary>Fishing skill stops rising at this value while fishing with this pole.</summary>
        public int SkillCap;

        /// <summary>Points added to the angler's skill (0-1000) for the catch and bite rolls.</summary>
        public int Bonus;

        public int PriceCopper;
    }

    /// <summary>One camp kit tier: how long the camp stands and how fast it restores those resting at it.</summary>
    public sealed class FishingCampTier
    {
        public string TemplateId;
        public string Name;

        /// <summary>objects.csv id of the kit in the backpack.</summary>
        public int KitModel;

        public int Minutes;

        /// <summary>Percent of max health, power and endurance restored per camp tick; doubled while sitting.</summary>
        public int RestorePercent;

        /// <summary>objects.csv id of the shelter put up beside the fire (0 = fire only).</summary>
        public int ShelterModel;

        public string ShelterName;
        public int PriceCopper;

        /// <summary>Points added to an angler's skill (0-1000) for the catch and bite rolls while fishing beside this camp.</summary>
        public int FishingBonus;
    }

    /// <summary>A stock crafting material a recipe uses. Every one is sold by crafting merchants in all three realms.</summary>
    public sealed class FishingMaterial
    {
        public string TemplateId;
        public string Name;
        public int Count;
    }

    /// <summary>A server-side recipe made with the Fishing skill (/fish craft): a pole or a camp kit.</summary>
    public sealed class FishingRecipe
    {
        public string ResultTemplateId;
        public string Name;
        public int RequiredSkill;
        public int CraftSeconds;
        public FishingMaterial[] Materials;
    }

    /// <summary>
    /// Fishing as a trade skill: the 1-1000 skill scale and how it rises, the pole tiers, the camp kits and the recipes
    /// that make them. Pure logic like FishingCatalog: nothing here touches the database or a player, so it is unit tested
    /// directly. The skill is kept in offline_fishing (FishingProgress), not in eCraftingSkill, so the stock crafting code,
    /// craft titles and bot crafting never see it. The client's trade skill window names its lines by id from tdl.crf, so
    /// Fishing is only listed there when the fishing_trade_skill_id server setting gives it an id; /fish stats shows it.
    ///
    /// The client draws recipes in its crafting window from its own tdl.crf, which has no fishing recipes, so these are
    /// listed and made through /fish craft instead.
    /// </summary>
    public static class FishingCraft
    {
        public const int MaxSkill = 1000;

        /// <summary>The skill's name in messages (and the name sent with the trade skill window line, which the client ignores).</summary>
        public const string SkillName = "Fishing";

        // The stock quarterstaff for every tier; the fishing_pole_model server setting swaps in the private rod (4927) at start.
        private const int PoleModel = 442;

        // objects.csv 2656 "Campfire" (items.csv 1064 with fire effect 74).
        public const int CampfireModel = 2656;
        // 1882 "bedroll pillow" has an icon (2238) but no mesh, so it stays the kit's bag look; on the ground it drew as a
        // loot bag (owner, 2026-11-04). 3869 "Cot Prop" (cot_prop.nif) is a real camp cot.
        public const int BedrollModel = 1882;
        public const int CotModel = 3869;
        // 3401 "Fest_refugeetent" (owner's pick, 2026-11-04 with /fish preview): a plain canvas tent about 200 x 280 units,
        // centred by its shapes' own offset. 4237 "Summer_tentRound" (a striped festival pavilion) was used first.
        public const int TentModel = 3401;

        /// <summary>Pole tiers, weakest first. The first is the stock fishing pole that /fish pole hands out.</summary>
        public static readonly IReadOnlyList<FishingPoleTier> Poles = new[]
        {
            new FishingPoleTier { TemplateId = FishingCatalog.PoleTemplateId, Name = "Fishing Pole", Model = PoleModel, RequiredSkill = 0, SkillCap = 250, Bonus = 0, PriceCopper = 500 },
            new FishingPoleTier { TemplateId = "offline_fishing_pole_oak", Name = "Oaken Fishing Pole", Model = PoleModel, RequiredSkill = 150, SkillCap = 500, Bonus = 50, PriceCopper = 2000 },
            new FishingPoleTier { TemplateId = "offline_fishing_pole_ironwood", Name = "Ironwood Fishing Pole", Model = PoleModel, RequiredSkill = 400, SkillCap = 750, Bonus = 100, PriceCopper = 8000 },
            new FishingPoleTier { TemplateId = "offline_fishing_pole_heartwood", Name = "Heartwood Fishing Pole", Model = PoleModel, RequiredSkill = 650, SkillCap = MaxSkill, Bonus = 150, PriceCopper = 30000 },
            new FishingPoleTier { TemplateId = "offline_fishing_pole_runewood", Name = "Runewood Angler's Pole", Model = PoleModel, RequiredSkill = 900, SkillCap = MaxSkill, Bonus = 250, PriceCopper = 100000 },
        };

        /// <summary>Camp kits, smallest first.</summary>
        public static readonly IReadOnlyList<FishingCampTier> Camps = new[]
        {
            new FishingCampTier { TemplateId = "offline_camp_kit_fire", Name = "Campfire Kit", KitModel = CampfireModel, Minutes = 15, RestorePercent = 2, ShelterModel = 0, PriceCopper = 300, FishingBonus = 30 },
            new FishingCampTier { TemplateId = "offline_camp_kit_bedroll", Name = "Bedroll Camp Kit", KitModel = BedrollModel, Minutes = 20, RestorePercent = 3, ShelterModel = CotModel, ShelterName = "bedroll", PriceCopper = 2500, FishingBonus = 60 },
            new FishingCampTier { TemplateId = "offline_camp_kit_tent", Name = "Tent Camp Kit", KitModel = BedrollModel, Minutes = 30, RestorePercent = 4, ShelterModel = TentModel, ShelterName = "tent", PriceCopper = 10000, FishingBonus = 100 },
        };

        // Stock materials (realm 0 rows sold by crafting merchants in every realm).
        private static FishingMaterial M(string id, string name, int count) => new() { TemplateId = id, Name = name, Count = count };

        /// <summary>Everything /fish craft can make, in the order it lists them.</summary>
        public static readonly IReadOnlyList<FishingRecipe> Recipes = new[]
        {
            new FishingRecipe { ResultTemplateId = Poles[0].TemplateId, Name = Poles[0].Name, RequiredSkill = 0, CraftSeconds = 5,
                Materials = new[] { M("elm_wooden_boards", "elm wooden boards", 2), M("woolen_heavy_thread", "woolen heavy thread", 1) } },
            new FishingRecipe { ResultTemplateId = Camps[0].TemplateId, Name = Camps[0].Name, RequiredSkill = 50, CraftSeconds = 5,
                Materials = new[] { M("elm_wooden_boards", "elm wooden boards", 3), M("woolen_cloth_squares", "woolen cloth square", 1) } },
            new FishingRecipe { ResultTemplateId = Poles[1].TemplateId, Name = Poles[1].Name, RequiredSkill = Poles[1].RequiredSkill, CraftSeconds = 8,
                Materials = new[] { M("oak_wooden_boards", "oaken wooden boards", 3), M("linen_heavy_thread", "linen heavy thread", 2), M("tanned_leather_squares", "tanned leather square", 1) } },
            new FishingRecipe { ResultTemplateId = Camps[1].TemplateId, Name = Camps[1].Name, RequiredSkill = 300, CraftSeconds = 10,
                Materials = new[] { M("oak_wooden_boards", "oaken wooden boards", 4), M("linen_cloth_squares", "linen cloth square", 3), M("tanned_leather_squares", "tanned leather square", 2) } },
            new FishingRecipe { ResultTemplateId = Poles[2].TemplateId, Name = Poles[2].Name, RequiredSkill = Poles[2].RequiredSkill, CraftSeconds = 10,
                Materials = new[] { M("ironwood_wooden_boards", "ironwood wooden boards", 3), M("brocade_heavy_thread", "brocade heavy thread", 2), M("cured_leather_squares", "cured leather square", 1) } },
            new FishingRecipe { ResultTemplateId = Camps[2].TemplateId, Name = Camps[2].Name, RequiredSkill = 600, CraftSeconds = 15,
                Materials = new[] { M("ironwood_wooden_boards", "ironwood wooden boards", 5), M("brocade_cloth_squares", "brocade cloth square", 4), M("cured_leather_squares", "cured leather square", 3) } },
            new FishingRecipe { ResultTemplateId = Poles[3].TemplateId, Name = Poles[3].Name, RequiredSkill = Poles[3].RequiredSkill, CraftSeconds = 12,
                Materials = new[] { M("heartwood_wooden_boards", "heartwood wooden boards", 3), M("silk_heavy_thread", "silk heavy thread", 2), M("hard_leather_squares", "hard leather square", 1) } },
            new FishingRecipe { ResultTemplateId = Poles[4].TemplateId, Name = Poles[4].Name, RequiredSkill = Poles[4].RequiredSkill, CraftSeconds = 15,
                Materials = new[] { M("runewood_wooden_boards", "runewood wooden boards", 3), M("gossamer_heavy_thread", "gossamer heavy thread", 2), M("rigid_leather_squares", "rigid leather square", 1) } },
        };

        /// <summary>A recipe stops teaching once the crafter's skill is this far past what it needs (it has gone grey).</summary>
        public const int RecipeGreyMargin = 150;

        public static FishingPoleTier FindPole(string templateId)
        {
            if (string.IsNullOrEmpty(templateId))
            {
                return null;
            }

            foreach (FishingPoleTier pole in Poles)
            {
                if (pole.TemplateId == templateId)
                {
                    return pole;
                }
            }

            return null;
        }

        public static FishingCampTier FindCamp(string templateId)
        {
            if (string.IsNullOrEmpty(templateId))
            {
                return null;
            }

            foreach (FishingCampTier camp in Camps)
            {
                if (camp.TemplateId == templateId)
                {
                    return camp;
                }
            }

            return null;
        }

        /// <summary>
        /// The 0-100 skill FishingCatalog rolls with: the angler's 0-1000 skill plus the pole's bonus and the bonus of a camp
        /// burning beside them, scaled down.
        /// </summary>
        public static int RollSkill(int skill, FishingPoleTier pole, FishingCampTier camp = null)
        {
            int bonus = (pole?.Bonus ?? 0) + (camp?.FishingBonus ?? 0);

            return Math.Clamp((Math.Clamp(skill, 0, MaxSkill) + bonus) / 10, 0, 100);
        }

        /// <summary>
        /// Chance that a catch or a craft raises the skill: certain for a beginner, one in four at the top. About 1,200
        /// ordinary catches take a beginner to 1000.
        /// </summary>
        public static double GainChance(int skill)
        {
            double mastery = Math.Clamp(skill, 0, MaxSkill) / (double)MaxSkill;

            return 1.0 - 0.75 * mastery;
        }

        /// <summary>
        /// Skill points a catch is worth, from its rarity's base points (FishingCatch.SkillGain from FishingCatalog: 1 common,
        /// 2 uncommon, 4 rare, 10 legendary, 0 junk). Never takes the skill past the pole's cap.
        /// </summary>
        public static int RollCatchGain(int skill, int basePoints, FishingPoleTier pole, Random rng)
        {
            int cap = pole?.SkillCap ?? Poles[0].SkillCap;

            if (basePoints <= 0 || skill >= cap)
            {
                return 0;
            }

            if (rng.NextDouble() >= GainChance(skill))
            {
                return 0;
            }

            return Math.Min(basePoints, cap - skill);
        }

        /// <summary>Skill points a finished craft is worth: 1-3 while the recipe isn't grey, never past 1000.</summary>
        public static int RollCraftGain(int skill, FishingRecipe recipe, Random rng)
        {
            if (recipe == null || skill >= MaxSkill || skill >= recipe.RequiredSkill + RecipeGreyMargin)
            {
                return 0;
            }

            if (rng.NextDouble() >= GainChance(skill))
            {
                return 0;
            }

            return Math.Min(1 + rng.Next(3), MaxSkill - skill);
        }

        /// <summary>The pole and camp kit item templates (the first pole is FishingCatalog's).</summary>
        public static IReadOnlyList<DbItemTemplate> AllTemplates()
        {
            var templates = new List<DbItemTemplate>();

            for (int i = 1; i < Poles.Count; i++)
            {
                FishingPoleTier pole = Poles[i];
                templates.Add(CreatePoleTemplate(pole.TemplateId, pole.Name, pole.Model, pole.PriceCopper));
            }

            foreach (FishingCampTier camp in Camps)
            {
                templates.Add(new DbItemTemplate
                {
                    Id_nb = camp.TemplateId,
                    Name = camp.Name,
                    Level = 1,
                    Object_Type = (int)eObjectType.GenericItem,
                    Item_Type = (int)eInventorySlot.FirstBackpack,
                    Model = camp.KitModel,
                    Weight = 40,
                    Price = camp.PriceCopper,
                    MaxCount = 5,
                    PackSize = 1,
                    IsPickable = true,
                    IsDropable = true,
                    IsTradable = true,
                    PackageID = FishingCatalog.PackageId,
                });
            }

            return templates;
        }

        /// <summary>
        /// A fishing pole: a GenericWeapon rather than a Staff, so every class can hold it
        /// (AbstractServerRules.CheckAbilityToUseItem), two-handed with 0.1 DPS so it is no use in a fight.
        /// </summary>
        public static DbItemTemplate CreatePoleTemplate(string id, string name, int model, int price)
        {
            return new DbItemTemplate
            {
                Id_nb = id,
                Name = name,
                Level = 1,
                Object_Type = (int)eObjectType.GenericWeapon,
                Item_Type = (int)eInventorySlot.TwoHandWeapon,
                Hand = 1,
                Type_Damage = (int)eDamageType.Crush,
                DPS_AF = 1,
                SPD_ABS = 40,
                Model = model,
                Weight = 30,
                Price = price,
                Quality = 100,
                Condition = 50000,
                MaxCondition = 50000,
                Durability = 50000,
                MaxDurability = 50000,
                MaxCount = 1,
                PackSize = 1,
                IsPickable = true,
                IsDropable = true,
                IsTradable = true,
                PackageID = FishingCatalog.PackageId,
            };
        }
    }
}
