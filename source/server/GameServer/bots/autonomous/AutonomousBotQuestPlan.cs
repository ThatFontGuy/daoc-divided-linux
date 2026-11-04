using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using DOL.Database;
using DOL.GS.Quests;

namespace DOL.GS;

/// <summary>What a gamebot does to finish one quest step.</summary>
public enum eBotQuestAction
{
    /// <summary>Walk to the step's character and speak (Interact and Whisper steps).</summary>
    Talk,
    /// <summary>Hunt the step's monster.</summary>
    Kill,
    /// <summary>Bring the step's item to its character (Deliver, Collect and trade steps).</summary>
    HandIn,
    /// <summary>Walk to the point and search for the step's time.</summary>
    Search,
    /// <summary>Walk to the point and use the step's item there.</summary>
    UseItem,
    /// <summary>Reach the point.</summary>
    Travel,
    /// <summary>Tell the step's character which reward it wants.</summary>
    Choose,
    /// <summary>Finish other quests first (a nested quest); the bot runs them and comes back.</summary>
    FinishQuests,
    /// <summary>Be in a group of two or more.</summary>
    Grouped,
    /// <summary>Speak the step's words on its point, at night when the step says so.</summary>
    Say,
}

public sealed record BotQuestPoint(ushort Region, int X, int Y, int Z);

public sealed record BotQuestDrop(string Mob, string Item, int Chance);

/// <summary>One step of a quest as a gamebot runs it. Step numbers match the DataQuest row's (1-based).</summary>
public sealed class BotQuestStep
{
    public int Number { get; init; }
    public eBotQuestAction Action { get; init; }
    public bool Finishes { get; init; }
    public string TargetName { get; init; } = string.Empty;
    public ushort TargetRegion { get; init; }
    /// <summary>Where the step sends the bot when the target gives no better place: search area, item spot or map marker.</summary>
    public BotQuestPoint Point { get; init; }
    public int Radius { get; init; }
    public int SearchSeconds { get; init; }
    /// <summary>Items the bot is handed as the step begins (a delivery's parcel, a gift, the quest's own tool).</summary>
    public string[] GivenAtStart { get; init; } = [];
    /// <summary>Item the bot receives when the step ends, at <see cref="GivenChance"/> percent.</summary>
    public string GivenAtEnd { get; init; } = string.Empty;
    public int GivenChance { get; init; } = 100;
    /// <summary>Item taken at the end of the step (HandIn, or UseItem when it is used up).</summary>
    public string NeededItem { get; init; } = string.Empty;
    public int NeededCount { get; init; } = 1;
    public bool ConsumesItem { get; init; }
    public BotQuestDrop[] Drops { get; init; } = [];
    /// <summary>Trade step: wanted item -> what it is traded for (may be empty).</summary>
    public IReadOnlyDictionary<string, string> Trades { get; init; }
    /// <summary>Choose step: reward name -> item.</summary>
    public IReadOnlyDictionary<string, string> Choices { get; init; }
    public ClassicQuests.EventSpawn Spawn { get; init; }
    public long RewardMoney { get; init; }
    public long RewardXp { get; init; }
    public long RewardRp { get; init; }
    public double XpShare { get; init; }
    /// <summary>FinishQuests: the quest names, and how many of them must be finished.</summary>
    public string[] NestedQuests { get; init; } = [];
    public int NestedCount { get; init; }
    /// <summary>Say: the words, and whether they work only at night.</summary>
    public string Words { get; init; } = string.Empty;
    public bool NightOnly { get; init; }

    /// <summary>The monsters of this step that drop what it needs; the bot hunts them until it has the item.</summary>
    public string HuntForItem(Func<string, int> carried)
    {
        if (Drops.Length == 0)
            return null;
        if (Trades != null ? Trades.Keys.Any(item => carried(item) > 0) : carried(NeededItem) >= NeededCount)
            return null;
        return Drops[0].Mob;
    }
}

public sealed class BotQuestPlan
{
    public int Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public string GiverName { get; init; } = string.Empty;
    public ushort GiverRegion { get; init; }
    public int MinLevel { get; init; }
    public int MaxLevel { get; init; }
    public IReadOnlyList<int> AllowedClasses { get; init; } = [];
    public string[] Dependencies { get; init; } = [];
    public string[] FinalRewards { get; init; } = [];
    public ClassicQuests.QuestInfo Info { get; init; }
    public BotQuestStep[] Steps { get; init; } = [];

    public BotQuestStep Step(int number) => number >= 1 && number <= Steps.Length ? Steps[number - 1] : null;

    public IEnumerable<(string Name, ushort Region)> KillTargets() =>
        Steps.SelectMany(step => step.Action == eBotQuestAction.Kill
            ? [(step.TargetName, step.TargetRegion)]
            : step.Drops.Select(drop => (drop.Mob, step.TargetRegion)));

    public IEnumerable<string> PlaceNames() =>
        Steps.Select(step => step.TargetName).Append(GiverName).Where(name => !string.IsNullOrEmpty(name));

    public IEnumerable<string> NestedQuestNames() => Steps.SelectMany(step => step.NestedQuests);
}

/// <summary>
/// Turns a classic DataQuest row and its classic-quests.json entry into a <see cref="BotQuestPlan"/>, or says why a
/// gamebot cannot run it. Pure: no world, no database. The step rules are DataQuest's and ClassicQuests' own:
/// a Kill step advances on one kill of its target, a delivery's item is handed when its step begins, a Collect step takes
/// the item another step gave or its monsters dropped, a step's rewards come when it ends.
/// </summary>
public static class AutonomousBotQuestPlanner
{
    /// <summary>A quest is in level for a bot from its MinLevel up to this many levels past it (the row's MaxLevel is
    /// nearly always 50, which would send level 45 bots to level 2 errands).</summary>
    public const int LevelWindow = 6;

    public const string SkipStepGroup = "needs a group";
    public const string SkipStepDieTo = "must die to a monster";
    public const string SkipStepNestedQuest = "waits on a nested quest";
    public const string SkipStepSay = "words spoken at night";
    public const string SkipNoTarget = "step has no target";
    public const string SkipNoSearchArea = "search step has no area";
    public const string SkipItemNoSource = "item has no source";
    public const string SkipUnknownStep = "unknown step type";

    public static bool InLevelWindow(int level, int minLevel, int maxLevel) =>
        level >= minLevel && level <= maxLevel && level <= minLevel + LevelWindow;

    /// <summary>The SEARCH entries of a row's SourceName: step -> point, radius and seconds.</summary>
    public static Dictionary<int, (BotQuestPoint Point, int Radius, int Seconds)> SearchAreas(string sourceName)
    {
        var areas = new Dictionary<int, (BotQuestPoint, int, int)>();
        foreach (string entry in (sourceName ?? string.Empty).Split('|'))
        {
            // COMMAND;step;text;region;x;y;radius;seconds
            string[] parts = entry.Split(';');
            if (parts.Length != 8 || !parts[0].Equals("SEARCH", StringComparison.OrdinalIgnoreCase) ||
                !int.TryParse(parts[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out int step) ||
                !ushort.TryParse(parts[3], out ushort region) || !int.TryParse(parts[4], out int x) ||
                !int.TryParse(parts[5], out int y) || !int.TryParse(parts[6], out int radius) ||
                !int.TryParse(parts[7], out int seconds))
                continue;
            areas[step] = (new BotQuestPoint(region, x, y, 0), radius, seconds);
        }
        return areas;
    }

    private static string At(string[] values, int index) => index < values.Length ? values[index] ?? string.Empty : string.Empty;

    private static long Reward(string[] values, int index) =>
        index < values.Length && long.TryParse(values[index], out long value) ? value : 0;

    private static string[] Split(string column) => (column ?? string.Empty).Split('|');

    /// <summary>A step item entry "id;chance": a Kill or Search step's item drops at that chance.</summary>
    private static (string Id, int Chance) ItemWithChance(string entry)
    {
        string[] parts = (entry ?? string.Empty).Split(';');
        int chance = parts.Length > 1 && int.TryParse(parts[1], out int value) ? value : 100;
        return (parts[0].Trim(), chance);
    }

    public static BotQuestPlan Build(DbDataQuest row, ClassicQuests.QuestInfo info, out string skip)
    {
        skip = null;
        byte[] types;
        try
        {
            types = Split(row.StepType).Where(text => text.Length > 0).Select(byte.Parse).ToArray();
        }
        catch (FormatException)
        {
            skip = SkipUnknownStep;
            return null;
        }
        string[] targets = Split(row.TargetName), stepItems = Split(row.StepItemTemplates), collects = Split(row.CollectItemTemplate);
        string[] money = Split(row.RewardMoney), xp = Split(row.RewardXP), rp = Split(row.RewardRP);
        var searches = SearchAreas(row.SourceName);
        var held = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var steps = new List<BotQuestStep>(types.Length);
        for (int index = 0; index < types.Length; index++)
        {
            int number = index + 1;
            var type = (DataQuest.eStepType)types[index];
            ClassicQuests.StepInfo stepInfo = info?.Steps != null && number < info.Steps.Count ? info.Steps[number] : null;
            ClassicQuests.CustomStep custom = stepInfo?.Custom;
            string[] target = At(targets, index).Split(';');
            string targetName = target[0].Trim();
            ushort targetRegion = target.Length > 1 && ushort.TryParse(target[1], out ushort region) ? region : (ushort)0;
            (string stepItem, int chance) = ItemWithChance(At(stepItems, index));
            bool finishes = (int)type % 2 == 1;
            BotQuestPoint marker = stepInfo?.Marker is { } point ? new BotQuestPoint(point.Region, point.X, point.Y, point.Z) : null;

            var given = new List<string>();
            foreach (string id in stepInfo?.Grant ?? [])
                if (!string.IsNullOrEmpty(id))
                    given.Add(id);
            if (custom?.Give == true && !string.IsNullOrEmpty(custom.Item))
                given.Add(custom.Item);
            if (!string.IsNullOrEmpty(stepInfo?.NeedsItem) && !string.IsNullOrEmpty(stepInfo.Issuer) && !held.Contains(stepInfo.NeedsItem))
                given.Add(stepInfo.NeedsItem);

            eBotQuestAction action;
            string needed = string.Empty;
            int count = 1;
            bool consumes = false;
            BotQuestPoint place = marker;
            int radius = 0, seconds = 0;
            string gaveAtEnd = stepItem;
            int gaveChance = 100;
            IReadOnlyDictionary<string, string> trades = null, choices = null;
            string[] nested = [];
            int nestedCount = 0;
            string words = string.Empty;
            bool nightOnly = false;
            BotQuestDrop[] drops = (custom?.Drops ?? []).Where(drop => !string.IsNullOrEmpty(drop.Item) && !string.IsNullOrEmpty(drop.Mob))
                .Select(drop => new BotQuestDrop(drop.Mob, drop.Item, drop.Chance)).ToArray();

            switch (custom?.Kind)
            {
                case "die_to": skip = SkipStepDieTo; return null;
                case "group":
                    action = eBotQuestAction.Grouped;
                    break;
                case "quest":
                    nested = (custom.Quest ?? string.Empty).Split('|', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                    if (nested.Length == 0)
                    {
                        skip = SkipStepNestedQuest;
                        return null;
                    }
                    action = eBotQuestAction.FinishQuests;
                    nestedCount = custom.Count > 0 ? Math.Min(custom.Count, nested.Length) : nested.Length;
                    break;
                case "say":
                    if (string.IsNullOrWhiteSpace(custom.Words))
                    {
                        skip = SkipStepSay;
                        return null;
                    }
                    action = eBotQuestAction.Say;
                    words = custom.Words;
                    nightOnly = custom.NightOnly;
                    (place, radius) = CustomPlace(custom, marker);
                    break;
                case "use_item":
                    action = eBotQuestAction.UseItem;
                    needed = custom.Item;
                    consumes = custom.Consume;
                    (place, radius) = CustomPlace(custom, marker);
                    break;
                case "travel":
                case "has_item":
                    action = eBotQuestAction.Travel;
                    (place, radius) = CustomPlace(custom, marker);
                    break;
                case "choose":
                    action = eBotQuestAction.Choose;
                    targetName = custom.Target;
                    choices = custom.Choices;
                    break;
                case "trade":
                    action = eBotQuestAction.HandIn;
                    targetName = custom.Target;
                    trades = custom.Trades;
                    break;
                default:
                    switch (type)
                    {
                        case DataQuest.eStepType.Kill:
                        case DataQuest.eStepType.KillFinish:
                            action = eBotQuestAction.Kill;
                            gaveChance = chance;
                            break;
                        case DataQuest.eStepType.Interact:
                        case DataQuest.eStepType.InteractFinish:
                        case DataQuest.eStepType.Whisper:
                        case DataQuest.eStepType.WhisperFinish:
                            action = eBotQuestAction.Talk;
                            break;
                        case DataQuest.eStepType.Deliver:
                        case DataQuest.eStepType.DeliverFinish:
                        case DataQuest.eStepType.Collect:
                        case DataQuest.eStepType.CollectFinish:
                            action = eBotQuestAction.HandIn;
                            (needed, count) = QuestDeliveryItems.CollectEntry(At(collects, index));
                            needed = needed?.Trim() ?? string.Empty;
                            if (type is DataQuest.eStepType.Deliver or DataQuest.eStepType.DeliverFinish)
                            {
                                gaveAtEnd = string.Empty; // a delivery's item comes at its start and is taken by its target
                                if (needed.Length == 0)
                                    needed = stepItem;
                                if (stepItem.Length > 0 && !held.Contains(stepItem) &&
                                    !QuestDeliveryItems.BringsToGiver(number, targetName, row.StartName))
                                    given.Add(stepItem);
                            }
                            break;
                        case DataQuest.eStepType.Search:
                        case DataQuest.eStepType.SearchFinish:
                            if (!searches.TryGetValue(number, out var area))
                            {
                                skip = SkipNoSearchArea;
                                return null;
                            }
                            action = eBotQuestAction.Search;
                            (place, radius, seconds) = area;
                            gaveChance = chance;
                            break;
                        default:
                            skip = SkipUnknownStep;
                            return null;
                    }
                    break;
            }

            if (action is eBotQuestAction.Talk or eBotQuestAction.Kill or eBotQuestAction.HandIn or eBotQuestAction.Choose &&
                string.IsNullOrEmpty(targetName))
            {
                skip = SkipNoTarget;
                return null;
            }
            foreach (string id in given)
                held.Add(id);
            foreach (BotQuestDrop drop in drops)
                held.Add(drop.Item);
            bool hasSource = needed.Length == 0 || held.Contains(needed) || trades != null;
            if (!hasSource)
            {
                skip = SkipItemNoSource;
                return null;
            }
            if (!string.IsNullOrEmpty(gaveAtEnd))
                held.Add(gaveAtEnd);

            steps.Add(new BotQuestStep
            {
                Number = number,
                Action = action,
                Finishes = finishes,
                TargetName = targetName ?? string.Empty,
                TargetRegion = targetRegion,
                Point = place,
                Radius = radius,
                SearchSeconds = seconds,
                GivenAtStart = given.Distinct(StringComparer.OrdinalIgnoreCase).ToArray(),
                GivenAtEnd = gaveAtEnd ?? string.Empty,
                GivenChance = gaveChance,
                NeededItem = needed,
                NeededCount = Math.Max(1, count),
                ConsumesItem = consumes,
                Drops = drops,
                Trades = trades,
                Choices = choices,
                Spawn = stepInfo?.Spawn,
                RewardMoney = Reward(money, index),
                RewardXp = Reward(xp, index),
                RewardRp = Reward(rp, index),
                XpShare = info?.XpShares != null && index < info.XpShares.Count ? info.XpShares[index] : 0,
                NestedQuests = nested,
                NestedCount = nestedCount,
                Words = words,
                NightOnly = nightOnly,
            });
        }
        if (steps.Count == 0)
        {
            skip = SkipUnknownStep;
            return null;
        }
        return new BotQuestPlan
        {
            Id = row.ID,
            Name = row.Name ?? string.Empty,
            GiverName = row.StartName ?? string.Empty,
            GiverRegion = row.StartRegionID,
            MinLevel = row.MinLevel,
            MaxLevel = row.MaxLevel,
            AllowedClasses = Split(row.AllowedClasses).Where(text => int.TryParse(text, out _)).Select(int.Parse).ToArray(),
            Dependencies = Split(row.QuestDependency).Where(text => text.Length > 0).ToArray(),
            FinalRewards = Split(row.FinalRewardItemTemplates).Where(text => text.Length > 0).ToArray(),
            Info = info,
            Steps = steps.ToArray(),
        };
    }

    private static (BotQuestPoint Place, int Radius) CustomPlace(ClassicQuests.CustomStep custom, BotQuestPoint marker) =>
        custom.Region != 0 ? (new BotQuestPoint(custom.Region, custom.X, custom.Y, custom.Z), custom.Radius) : (marker, 0);

    /// <summary>A plan's dependencies a bot can meet: every one names a quest (or quests) it can itself run, or closes
    /// the quest off. A scripted quest or a skipped one is never finished by a bot.</summary>
    public static bool DependenciesRunnable(BotQuestPlan plan, ICollection<string> planNames, ICollection<int> planIds)
    {
        foreach (string entry in plan.Dependencies)
        {
            if (!QuestDependencies.IsIdEntry(entry))
            {
                if (!planNames.Contains(entry.Trim()))
                    return false;
                continue;
            }
            if (!QuestDependencies.TryParseIds(entry, out int[] ids, out bool closes))
                return false;
            if (!closes && !ids.Any(planIds.Contains))
                return false;
        }
        // A nested-quest step needs enough of its quests to be ones a bot can run.
        foreach (BotQuestStep step in plan.Steps.Where(step => step.Action == eBotQuestAction.FinishQuests))
            if (step.NestedQuests.Count(planNames.Contains) < step.NestedCount)
                return false;
        return true;
    }

    /// <summary>Removes plans whose dependencies no bot can meet, repeatedly: a chain is only as runnable as its first link.</summary>
    public static List<BotQuestPlan> KeepRunnableChains(IEnumerable<BotQuestPlan> plans, out int removed)
    {
        List<BotQuestPlan> kept = plans.ToList();
        int before = kept.Count;
        while (true)
        {
            var names = new HashSet<string>(kept.Select(plan => plan.Name), StringComparer.OrdinalIgnoreCase);
            var ids = new HashSet<int>(kept.Select(plan => plan.Id));
            int count = kept.Count;
            kept.RemoveAll(plan => !DependenciesRunnable(plan, names, ids));
            if (kept.Count == count)
                break;
        }
        removed = before - kept.Count;
        return kept;
    }
}
