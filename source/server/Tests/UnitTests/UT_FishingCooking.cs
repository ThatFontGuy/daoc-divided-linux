using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.GS.Fishing;
using NUnit.Framework;

namespace DOL.GS.Tests;

[TestFixture]
public class UT_FishingCooking
{
    [Test]
    public void Dishes_HaveTheirOwnIdsAndStack()
    {
        HashSet<string> ids = new(FishingCatalog.AllTemplates().Concat(FishingCraft.AllTemplates()).Select(t => t.Id_nb), StringComparer.Ordinal);

        foreach (DbItemTemplate dish in FishingCooking.AllTemplates())
        {
            Assert.That(ids.Add(dish.Id_nb), Is.True, $"duplicate Id_nb {dish.Id_nb}");
            Assert.That(dish.MaxCount, Is.EqualTo(20), dish.Id_nb);
            Assert.That(FishingCooking.FindDish(dish.Id_nb).SpellIds, Is.Not.Empty, dish.Id_nb);
        }
    }

    [Test]
    public void DishFor_CooksRareAndTrophyFishIntoAFeastAndJunkIntoNothing()
    {
        Assert.That(FishingCooking.DishFor("offline_fish_alb_brown_trout_1").Name, Is.EqualTo("Grilled Fish"));
        Assert.That(FishingCooking.DishFor("offline_fish_alb_brown_trout_3").Name, Is.EqualTo("Smoked Fish"));
        Assert.That(FishingCooking.DishFor("offline_fish_alb_brown_trout_4").Name, Is.EqualTo("Angler's Feast"));
        Assert.That(FishingCooking.DishFor("offline_fish_alb_eel_1").Name, Is.EqualTo("Smoked Fish"));
        Assert.That(FishingCooking.DishFor("offline_fish_alb_salmon_1").Name, Is.EqualTo("Angler's Feast"));
        Assert.That(FishingCooking.DishFor(FishingCooking.ChestTemplateId), Is.Null);
        Assert.That(FishingCooking.DishFor(FishingCatalog.PoleTemplateId), Is.Null);
        Assert.That(FishingCooking.DishFor(null), Is.Null);
    }

    [Test]
    public void ChestCoins_GrowWithLevelAndOneChestInFourHoldsAnItem()
    {
        var rng = new Random(5);
        int items = 0;

        for (int i = 0; i < 4000; i++)
        {
            Assert.That(FishingCooking.RollChestCoins(1, rng), Is.InRange(20, 60));
            Assert.That(FishingCooking.RollChestCoins(50, rng), Is.InRange(50_000, 150_000));
            Assert.That(FishingCooking.RollChestCoins(80, rng), Is.InRange(50_000, 150_000));
            items += FishingCooking.RollChestItem(rng) ? 1 : 0;
        }

        Assert.That(items, Is.InRange(800, 1200));
    }

    [Test]
    public void Fish_SellForSilverNotCopper()
    {
        DbItemTemplate smallTrout = FishingCatalog.AllTemplates().Single(t => t.Id_nb == "offline_fish_alb_brown_trout_1");
        DbItemTemplate trophySturgeon = FishingCatalog.AllTemplates().Single(t => t.Id_nb == "offline_fish_alb_sturgeon_4");

        Assert.That(smallTrout.Price, Is.EqualTo(10 * FishingCatalog.FishValueScale));
        Assert.That(trophySturgeon.Price, Is.EqualTo(80 * 10 * FishingCatalog.FishValueScale));
    }

    [Test]
    public void Legendaries_AreAboutOneCastInAThousandForANovice()
    {
        var rng = new Random(11);
        int legendary = 0;

        for (int i = 0; i < 100_000; i++)
        {
            legendary += FishingCatalog.Roll(eRealm.Albion, 0, rng).Rarity == eFishingRarity.Legendary ? 1 : 0;
        }

        Assert.That(legendary, Is.InRange(40, 200));
    }
}
