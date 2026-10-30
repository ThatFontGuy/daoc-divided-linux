using System;
using System.Collections;
using System.Reflection;
using System.Runtime.CompilerServices;
using DOL.Database;
using DOL.GS;
using DOL.GS.PlayerClass;
using DOL.GS.PropertyCalc;
using DOL.GS.ServerProperties;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture]
public class UT_ModernItemBonuses
{
    private class Player : GamePlayer
    {
        private Player() : base(null, null) { }
        public ICharacterClass Class;
        public override ICharacterClass CharacterClass => Class;
        public override byte Level { get; set; }
        public override int GetBaseStat(eStat stat) => 60;
        public override int CalculateMaxMana(int level, int stat) => 100 + stat;
        public override bool HasAbility(string key) => false;
        public override int GetModified(eProperty property) => property >= eProperty.Stat_First && property <= eProperty.Stat_Last
            ? new StatCalculator().CalcValue(this, property) : 0;
    }

    private class Server : GameServer
    {
        protected override IObjectDatabase DataBaseImpl => DispatchProxy.Create<IObjectDatabase, UT_UnobservedConcentration.EmptyReads>();
    }

    private GameServer _previousServer;
    private bool _savedSetting;

    [OneTimeSetUp]
    public void Logging() => DOL.Logging.LoggerManager.InitializeWithExplicitLibrary(null, DOL.Logging.LogLibrary.None);

    [SetUp]
    public void SaveSetting()
    {
        _savedSetting = Properties.MODERN_ITEM_BONUSES;
        _previousServer = GameServer.Instance;
        GameServer.LoadTestDouble((Server) RuntimeHelpers.GetUninitializedObject(typeof(Server)));
    }

    [TearDown]
    public void RestoreSetting()
    {
        Properties.MODERN_ITEM_BONUSES = _savedSetting;
        GameServer.LoadTestDouble(_previousServer);
    }

    private static Player NewPlayer(ICharacterClass characterClass = null, byte level = 50)
    {
        var player = (Player) RuntimeHelpers.GetUninitializedObject(typeof(Player));
        player.Class = characterClass ?? new ClassThane();
        player.Level = level;
        foreach (string property in new[] { "ItemBonus", "AbilityBonus", "BaseBuffBonusCategory", "SpecBuffBonusCategory", "OtherBonus", "DebuffCategory", "SpecDebuffCategory", "BuffBonusMultCategory1" })
        {
            var field = typeof(GameLiving).GetField($"<{property}>k__BackingField", BindingFlags.Instance | BindingFlags.NonPublic);
            field.SetValue(player, Activator.CreateInstance(field.FieldType));
        }
        return player;
    }

    [TestCase(false, 200)]
    [TestCase(true, 400)]
    public void HitsCapIncreaseIs200ClassicAnd400Modern(bool modern, int expected)
    {
        Properties.MODERN_ITEM_BONUSES = modern;
        var player = NewPlayer();
        player.ItemBonus[eProperty.MaxHealthCapBonus] = 500;
        Assert.That(MaxHealthCalculator.GetItemBonusCapIncrease(player), Is.EqualTo(expected));
        Assert.That(MaxHealthCalculator.GetItemBonusCap(player) + expected, Is.EqualTo(modern ? 600 : 400));
    }

    [TestCase(false, 31)]
    [TestCase(true, 41)]
    public void ResistCapIncreaseIs5ClassicAnd15Modern(bool modern, int expected)
    {
        Properties.MODERN_ITEM_BONUSES = modern;
        var player = NewPlayer();
        player.ItemBonus[eProperty.Resist_Body] = 60;
        player.ItemBonus[eProperty.BodyResCapBonus] = 20;
        Assert.That(new ResistCalculator().CalcValueFromItems(player, eProperty.Resist_Body), Is.EqualTo(expected));
    }

    [Test]
    public void MythicalPhysicalDefenseRaisesCrushSlashThrustAndTheirCapsOnly()
    {
        Properties.MODERN_ITEM_BONUSES = true;
        var player = NewPlayer();
        player.ItemBonus[eProperty.MythicalPhysicalDefense] = 3;
        foreach (eProperty resist in new[] { eProperty.Resist_Crush, eProperty.Resist_Slash, eProperty.Resist_Thrust, eProperty.Resist_Heat })
            player.ItemBonus[resist] = 40;

        var calculator = new ResistCalculator();
        Assert.That(calculator.CalcValueFromItems(player, eProperty.Resist_Crush), Is.EqualTo(29), "26 base cap + 3 PD cap, filled by the PD resist");
        Assert.That(calculator.CalcValueFromItems(player, eProperty.Resist_Slash), Is.EqualTo(29));
        Assert.That(calculator.CalcValueFromItems(player, eProperty.Resist_Thrust), Is.EqualTo(29));
        Assert.That(calculator.CalcValueFromItems(player, eProperty.Resist_Heat), Is.EqualTo(26));

        Properties.MODERN_ITEM_BONUSES = false;
        Assert.That(calculator.CalcValueFromItems(player, eProperty.Resist_Crush), Is.EqualTo(26), "classic rules ignore mythical PD");
    }

    [Test]
    public void PowerPoolUsesModernCapsAndLeavesEtherealBondUnamplified()
    {
        var player = NewPlayer();
        player.ItemBonus[eProperty.MaxMana] = 30;
        player.ItemBonus[eProperty.PowerPool] = 60;
        player.ItemBonus[eProperty.PowerPoolCapBonus] = 40;
        player.AbilityBonus[eProperty.MaxMana] = 10;
        int manaBase = 100 + 60; // CalculateMaxMana(level, Piety 60)

        Properties.MODERN_ITEM_BONUSES = true;
        Assert.That(new MaxManaCalculator().CalcValue(player, eProperty.MaxMana), Is.EqualTo((int) ((manaBase + 25) * 1.50 + 10)));

        Properties.MODERN_ITEM_BONUSES = false;
        Assert.That(new MaxManaCalculator().CalcValue(player, eProperty.MaxMana), Is.EqualTo((int) ((manaBase + 26 + 10) * 1.60)));
    }

    [Test]
    public void MythicalCrowdControlIsALaterMultiplicativeLayerCappedAt25()
    {
        var player = NewPlayer();
        player.ItemBonus[eProperty.StunDurationReduction] = 20;
        player.ItemBonus[eProperty.MythicalCrowdControlReduction] = 40;

        Properties.MODERN_ITEM_BONUSES = false;
        Assert.That(new StunDurationPercentCalculator().CalcValue(player, eProperty.StunDurationReduction), Is.EqualTo(80));

        Properties.MODERN_ITEM_BONUSES = true;
        Assert.That(new StunDurationPercentCalculator().CalcValue(player, eProperty.StunDurationReduction), Is.EqualTo(60));
        Assert.That(new MesmerizeDurationPercentCalculator().CalcValue(player, eProperty.MesmerizeDurationReduction), Is.EqualTo(75));
        Assert.That(new SpeedDecreaseDurationPercentCalculator().CalcValue(player, eProperty.SpeedDecreaseDurationReduction), Is.EqualTo(75));
    }

    [Test]
    public void ItemDpsAndConversionAreCappedAt10OnlyWithModernRules()
    {
        var player = NewPlayer();
        player.ItemBonus[eProperty.DPS] = 15;
        player.ItemBonus[eProperty.Conversion] = 30;

        Properties.MODERN_ITEM_BONUSES = false;
        Assert.That(new DPSCalculator().CalcValue(player, eProperty.DPS), Is.Zero);
        Assert.That(new ConversionPercentCalculator().CalcValue(player, eProperty.Conversion), Is.EqualTo(30));

        Properties.MODERN_ITEM_BONUSES = true;
        Assert.That(new DPSCalculator().CalcValue(player, eProperty.DPS), Is.EqualTo(10));
        Assert.That(new ConversionPercentCalculator().CalcValue(player, eProperty.Conversion), Is.EqualTo(10));
    }

    [Test]
    public void MythicalRegenIsFlatPerTickCappedAt50AndNeverFillsCombatPower()
    {
        var thane = NewPlayer();
        thane.ItemBonus[eProperty.MythicalHealthRegen] = 8;
        thane.ItemBonus[eProperty.MythicalPowerRegen] = 80;
        thane.ItemBonus[eProperty.MythicalEnduranceRegen] = 5;
        var vampiir = NewPlayer(new ClassVampiir());
        vampiir.ItemBonus[eProperty.MythicalPowerRegen] = 10;

        Properties.MODERN_ITEM_BONUSES = false;
        Assert.That(ModernItemBonusRules.MythicalRegen(thane, eProperty.HealthRegenerationAmount), Is.Zero);

        Properties.MODERN_ITEM_BONUSES = true;
        Assert.That(ModernItemBonusRules.MythicalRegen(thane, eProperty.HealthRegenerationAmount), Is.EqualTo(8));
        Assert.That(ModernItemBonusRules.MythicalRegen(thane, eProperty.PowerRegenerationAmount), Is.EqualTo(50));
        Assert.That(ModernItemBonusRules.MythicalRegen(thane, eProperty.EnduranceRegenerationAmount), Is.EqualTo(5));
        Assert.That(ModernItemBonusRules.MythicalRegen(vampiir, eProperty.PowerRegenerationAmount), Is.Zero);
    }

    private static GameBot NewBot(byte level = 50)
    {
        var bot = (GameBot) RuntimeHelpers.GetUninitializedObject(typeof(GameBot));
        typeof(GameNPC).GetField("m_brains", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(bot, new ArrayList(1));
        typeof(GameObject).GetField("m_level", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(bot, level);
        foreach (string property in new[] { "ItemBonus", "AbilityBonus", "BaseBuffBonusCategory", "SpecBuffBonusCategory", "OtherBonus", "DebuffCategory", "SpecDebuffCategory", "BuffBonusMultCategory1" })
        {
            var field = typeof(GameLiving).GetField($"<{property}>k__BackingField", BindingFlags.Instance | BindingFlags.NonPublic);
            field.SetValue(bot, Activator.CreateInstance(field.FieldType));
        }
        return bot;
    }

    [Test]
    public void NpcBackedBotsGetTheirGearResistsHasteArmorAndSyphon()
    {
        Properties.MODERN_ITEM_BONUSES = false;
        var bot = NewBot();
        var bareBot = NewBot();
        bot.ItemBonus[eProperty.Resist_Body] = 20;
        bot.ItemBonus[eProperty.MeleeSpeed] = 15;
        bot.ItemBonus[eProperty.ArmorFactor] = 30;
        bot.ItemBonus[eProperty.ArcaneSyphon] = 30;

        Assert.That(new ResistCalculator().CalcValueFromItems(bot, eProperty.Resist_Body), Is.EqualTo(20));
        Assert.That(new MeleeSpeedPercentCalculator().CalcValue(bot, eProperty.MeleeSpeed), Is.EqualTo(90), "item haste capped at 10%");
        Assert.That(new ArmorFactorCalculator().CalcValue(bot, eProperty.ArmorFactor) - new ArmorFactorCalculator().CalcValue(bareBot, eProperty.ArmorFactor), Is.EqualTo(30));
        Assert.That(new ArcaneSyphonCalculator().CalcValue(bot, eProperty.ArcaneSyphon), Is.EqualTo(25));
    }

    [Test]
    public void DamageConversionProtectsNpcBackedBots()
    {
        Properties.MODERN_ITEM_BONUSES = false;
        var bot = NewBot();
        bot.ItemBonus[eProperty.Conversion] = 10;
        Assert.That(new ConversionPercentCalculator().CalcValue(bot, eProperty.Conversion), Is.EqualTo(10));

        // Unit tests have no started server, so register the calculator GetModified uses.
        var calculators = (IPropertyCalculator[]) typeof(GameLiving).GetField("m_propertyCalc", BindingFlags.Static | BindingFlags.NonPublic).GetValue(null);
        IPropertyCalculator previous = calculators[(int) eProperty.Conversion];
        calculators[(int) eProperty.Conversion] = new ConversionPercentCalculator();
        try
        {
            Assert.That(AttackComponent.CalculateTargetConversionFactor(bot), Is.EqualTo(0.9).Within(1e-9));
        }
        finally
        {
            calculators[(int) eProperty.Conversion] = previous;
        }
    }

    [Test]
    public void OrdinaryNpcsStillIgnoreItemBonuses()
    {
        var npc = (GameNPC) RuntimeHelpers.GetUninitializedObject(typeof(GameNPC));
        typeof(GameObject).GetField("m_level", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(npc, (byte) 50);
        foreach (string property in new[] { "ItemBonus", "AbilityBonus", "BaseBuffBonusCategory", "SpecBuffBonusCategory", "OtherBonus", "DebuffCategory", "SpecDebuffCategory", "BuffBonusMultCategory1" })
        {
            var field = typeof(GameLiving).GetField($"<{property}>k__BackingField", BindingFlags.Instance | BindingFlags.NonPublic);
            field.SetValue(npc, Activator.CreateInstance(field.FieldType));
        }
        npc.ItemBonus[eProperty.Resist_Body] = 20;
        npc.ItemBonus[eProperty.MeleeSpeed] = 15;
        npc.ItemBonus[eProperty.ArcaneSyphon] = 30;
        Assert.That(new ResistCalculator().CalcValueFromItems(npc, eProperty.Resist_Body), Is.Zero);
        Assert.That(new MeleeSpeedPercentCalculator().CalcValue(npc, eProperty.MeleeSpeed), Is.EqualTo(100));
        Assert.That(new ArcaneSyphonCalculator().CalcValue(npc, eProperty.ArcaneSyphon), Is.Zero);
        Assert.That(AttackComponent.CalculateTargetConversionFactor(npc), Is.EqualTo(1.0));
    }

    [TestCase(false, (byte) 35, 10, 25)]
    [TestCase(true, (byte) 35, 7, 17)]
    [TestCase(true, (byte) 39, 7, 19)]
    [TestCase(true, (byte) 50, 10, 25)]
    public void PercentItemCapsScaleWithLevelUnderModernRules(bool modern, byte level, int cap10, int cap25)
    {
        Properties.MODERN_ITEM_BONUSES = modern;
        var player = NewPlayer(level: level);
        player.ItemBonus[eProperty.MeleeDamage] = 30;
        player.ItemBonus[eProperty.StyleDamage] = 30;
        player.ItemBonus[eProperty.SpellDuration] = 40;
        player.ItemBonus[eProperty.HealingEffectiveness] = 40;

        Assert.That(new MeleeDamagePercentCalculator().CalcValue(player, eProperty.MeleeDamage), Is.EqualTo(cap10));
        Assert.That(new StyleDamagePercentCalculator().CalcValue(player, eProperty.StyleDamage), Is.EqualTo(cap10));
        Assert.That(new SpellDurationPercentCalculator().CalcValue(player, eProperty.SpellDuration), Is.EqualTo(cap25));
    }

    [Test]
    public void BowsShareArcheryAndCasterItemBonusesUnderOneCap()
    {
        var player = NewPlayer();
        player.ItemBonus[eProperty.CastingSpeed] = 6;
        player.ItemBonus[eProperty.ArcherySpeed] = 8;
        player.ItemBonus[eProperty.RangedDamage] = 3;
        player.ItemBonus[eProperty.SpellDamage] = 10;

        Properties.MODERN_ITEM_BONUSES = false;
        Assert.That(ModernItemBonusRules.BowSpeedAlias(player), Is.Zero);
        Assert.That(ModernItemBonusRules.BowDamageAlias(player), Is.Zero);

        Properties.MODERN_ITEM_BONUSES = true;
        Assert.That(ModernItemBonusRules.BowSpeedAlias(player), Is.EqualTo(4), "6 casting + 8 archery share one 10% cap");
        Assert.That(ModernItemBonusRules.BowDamageAlias(player), Is.EqualTo(7), "3 archery + 10 spell damage share one 10% cap");
    }

    [Test]
    public void MythirianDropChanceUsesTheNamedMultiplier()
    {
        double baseChance = Properties.LOOTGENERATOR_MYTHIRIAN_BASE_CHANCE;
        double multiplier = Properties.LOOTGENERATOR_MYTHIRIAN_NAMED_MULTIPLIER;
        try
        {
            Properties.LOOTGENERATOR_MYTHIRIAN_BASE_CHANCE = 1.0;
            Properties.LOOTGENERATOR_MYTHIRIAN_NAMED_MULTIPLIER = 5.0;
            var trash = (GameNPC) RuntimeHelpers.GetUninitializedObject(typeof(GameNPC));
            var named = (GameNPC) RuntimeHelpers.GetUninitializedObject(typeof(GameNPC));
            typeof(GameNPC).GetField("m_brains", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(trash, new ArrayList(1));
            typeof(GameNPC).GetField("m_brains", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(named, new ArrayList(1));
            trash.Name = "sobekite hulk";
            named.Name = "Cetus";

            Assert.That(LootGeneratorMythirian.DropChance(trash), Is.EqualTo(1.0));
            Assert.That(LootGeneratorMythirian.DropChance(named), Is.EqualTo(5.0));

            Properties.LOOTGENERATOR_MYTHIRIAN_BASE_CHANCE = 50.0;
            Assert.That(LootGeneratorMythirian.DropChance(named), Is.EqualTo(100.0));
        }
        finally
        {
            Properties.LOOTGENERATOR_MYTHIRIAN_BASE_CHANCE = baseChance;
            Properties.LOOTGENERATOR_MYTHIRIAN_NAMED_MULTIPLIER = multiplier;
        }
    }
}
