using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS.Fishing;
using NUnit.Framework;

namespace DOL.GS.Tests;

[TestFixture]
public class UT_FishingCraft
{
    [Test]
    public void Templates_DontClashWithTheCatalogAndPolesAreTwoHandedGenericWeapons()
    {
        HashSet<string> ids = new(FishingCatalog.AllTemplates().Select(t => t.Id_nb), StringComparer.Ordinal);

        foreach (DbItemTemplate template in FishingCraft.AllTemplates())
        {
            Assert.That(ids.Add(template.Id_nb), Is.True, $"duplicate Id_nb {template.Id_nb}");
            Assert.That(template.Id_nb, Does.Match("^offline_[a-z0-9_]+$"), template.Id_nb);
            Assert.That(template.PackageID, Is.EqualTo(FishingCatalog.PackageId), template.Id_nb);
            Assert.That(template.Price, Is.GreaterThan(0), template.Id_nb);
            Assert.That(template.Model, Is.GreaterThan(0), template.Id_nb);
        }

        foreach (FishingPoleTier pole in FishingCraft.Poles)
        {
            Assert.That(ids, Does.Contain(pole.TemplateId));
        }

        foreach (DbItemTemplate pole in FishingCraft.AllTemplates().Where(t => FishingCraft.FindPole(t.Id_nb) != null))
        {
            Assert.That(pole.Object_Type, Is.EqualTo((int)eObjectType.GenericWeapon), pole.Id_nb);
            Assert.That(pole.Item_Type, Is.EqualTo((int)eInventorySlot.TwoHandWeapon), pole.Id_nb);
            Assert.That(pole.DPS_AF, Is.EqualTo(1), pole.Id_nb);
        }
    }

    [Test]
    public void Poles_GetBetterWithEachTierAndEachCanBeCraftedBeforeTheLastOneStopsTeaching()
    {
        for (int i = 1; i < FishingCraft.Poles.Count; i++)
        {
            FishingPoleTier previous = FishingCraft.Poles[i - 1];
            FishingPoleTier pole = FishingCraft.Poles[i];

            Assert.That(pole.Bonus, Is.GreaterThan(previous.Bonus), pole.Name);
            Assert.That(pole.SkillCap, Is.GreaterThanOrEqualTo(previous.SkillCap), pole.Name);
            Assert.That(pole.RequiredSkill, Is.LessThan(previous.SkillCap), $"{pole.Name} can't be reached with a {previous.Name}");
        }

        Assert.That(FishingCraft.Poles.Last().SkillCap, Is.EqualTo(FishingCraft.MaxSkill));
    }

    [Test]
    public void EveryPoleAndCampKitHasARecipeAndEveryRecipeMakesOne()
    {
        HashSet<string> made = new(FishingCraft.Recipes.Select(r => r.ResultTemplateId));

        foreach (FishingPoleTier pole in FishingCraft.Poles)
        {
            Assert.That(made, Does.Contain(pole.TemplateId), pole.Name);
        }

        foreach (FishingCampTier camp in FishingCraft.Camps)
        {
            Assert.That(made, Does.Contain(camp.TemplateId), camp.Name);
        }

        foreach (FishingRecipe recipe in FishingCraft.Recipes)
        {
            Assert.That(FishingCraft.FindPole(recipe.ResultTemplateId) != null || FishingCraft.FindCamp(recipe.ResultTemplateId) != null, Is.True, recipe.Name);
            Assert.That(recipe.Materials, Is.Not.Empty, recipe.Name);
            Assert.That(recipe.Materials.All(m => m.Count > 0 && !string.IsNullOrEmpty(m.TemplateId)), Is.True, recipe.Name);
            Assert.That(recipe.CraftSeconds, Is.GreaterThan(0), recipe.Name);
        }

        Assert.That(FishingCraft.Recipes.Min(r => r.RequiredSkill), Is.EqualTo(0), "a beginner must be able to make something");
    }

    [Test]
    public void RollSkill_AddsThePoleBonusAndScalesToTheCatalogsHundred()
    {
        Assert.That(FishingCraft.RollSkill(0, null), Is.EqualTo(0));
        Assert.That(FishingCraft.RollSkill(500, FishingCraft.Poles[0]), Is.EqualTo(50));
        Assert.That(FishingCraft.RollSkill(500, FishingCraft.Poles[2]), Is.EqualTo(60));
        Assert.That(FishingCraft.RollSkill(1000, FishingCraft.Poles.Last()), Is.EqualTo(100));
        Assert.That(FishingCraft.RollSkill(500, FishingCraft.Poles[0], FishingCraft.Camps.Last()), Is.EqualTo(60));
    }

    [Test]
    public void CatchGain_StopsAtThePolesCapAndJunkTeachesNothing()
    {
        var rng = new Random(1);
        FishingPoleTier starter = FishingCraft.Poles[0];

        for (int i = 0; i < 1000; i++)
        {
            int gain = FishingCraft.RollCatchGain(starter.SkillCap - 2, 10, starter, rng);

            Assert.That(gain, Is.InRange(0, 2));
            Assert.That(FishingCraft.RollCatchGain(starter.SkillCap, 10, starter, rng), Is.EqualTo(0));
            Assert.That(FishingCraft.RollCatchGain(0, 0, starter, rng), Is.EqualTo(0));
        }
    }

    [Test]
    public void GainChance_IsCertainForABeginnerAndAQuarterAtTheTop()
    {
        Assert.That(FishingCraft.GainChance(0), Is.EqualTo(1.0));
        Assert.That(FishingCraft.GainChance(FishingCraft.MaxSkill), Is.EqualTo(0.25).Within(1e-9));
        Assert.That(FishingCraft.GainChance(500), Is.LessThan(FishingCraft.GainChance(100)));
    }

    [Test]
    public void ReachingTheTopTakesHoursOfOrdinaryCatchesNotMinutes()
    {
        // Common catches only (1 point each), always with the best pole available at the skill.
        var rng = new Random(7);
        int skill = 0;
        int catches = 0;

        while (skill < FishingCraft.MaxSkill && catches < 100_000)
        {
            FishingPoleTier pole = FishingCraft.Poles.Last(p => p.RequiredSkill <= skill);
            skill += FishingCraft.RollCatchGain(skill, 1, pole, rng);
            catches++;
        }

        Assert.That(skill, Is.EqualTo(FishingCraft.MaxSkill));
        Assert.That(catches, Is.InRange(1500, 2500));
    }

    [Test]
    public void CraftGain_StopsOnceTheRecipeIsGrey()
    {
        var rng = new Random(3);
        FishingRecipe recipe = FishingCraft.Recipes[0];

        for (int i = 0; i < 1000; i++)
        {
            Assert.That(FishingCraft.RollCraftGain(0, recipe, rng), Is.InRange(1, 3));
            Assert.That(FishingCraft.RollCraftGain(recipe.RequiredSkill + FishingCraft.RecipeGreyMargin, recipe, rng), Is.EqualTo(0));
        }
    }

    [Test]
    public void Camps_LastLongerAndRestoreMoreWithEachTierAndSittingDoublesIt()
    {
        for (int i = 1; i < FishingCraft.Camps.Count; i++)
        {
            Assert.That(FishingCraft.Camps[i].Minutes, Is.GreaterThan(FishingCraft.Camps[i - 1].Minutes));
            Assert.That(FishingCraft.Camps[i].RestorePercent, Is.GreaterThan(FishingCraft.Camps[i - 1].RestorePercent));
        }

        for (int i = 1; i < FishingCraft.Camps.Count; i++)
        {
            Assert.That(FishingCraft.Camps[i].FishingBonus, Is.GreaterThan(FishingCraft.Camps[i - 1].FishingBonus));
        }

        Assert.That(FishingCraft.Camps.All(c => c.ShelterModel != FishingCraft.BedrollModel), Is.True, "1882 has no mesh: it draws as a loot bag");

        FishingCampTier tent = FishingCraft.Camps.Last();

        Assert.That(FishingCamp.RestorePercent(tent, true), Is.EqualTo(2 * FishingCamp.RestorePercent(tent, false)));
        Assert.That(FishingCamp.IsCampKit(tent.TemplateId), Is.True);
        Assert.That(FishingCamp.IsCampKit(FishingCatalog.PoleTemplateId), Is.False);
    }
}
