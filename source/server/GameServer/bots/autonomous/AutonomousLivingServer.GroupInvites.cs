using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using DOL.GS.ServerProperties;

namespace DOL.GS;

/// <summary>
/// Gamebots invite the player (owner 2026-10-30), with the yes/no window a real invitation opens. A bot near a player who
/// says they are LFG asks within seconds; one farming the same camp asks now and then. Saying yes puts the bot in the
/// player's group, led by the player, so it follows them and takes /bots orders; the leader of a bot group brings the whole
/// group along. Gaps keep it from nagging: one invitation at a time, minutes between them, and half an hour before the same
/// bot asks again. /bots invites off stops them for a player.
/// </summary>
public static partial class AutonomousLivingServer
{
    /// <summary>A bot this far off hears an LFG in its region and runs over; it can't cross regions.</summary>
    public const int LfgInviteRange = 16_000;
    /// <summary>"The same camp".</summary>
    public const int CampInviteRange = 1_500;
    public const int LfgInviteLevelGap = 5;
    public const int CampInviteLevelGap = 4;
    public const long InviteScanMs = 30_000;
    /// <summary>Scans the player must stay put through before a bot counts them as farming here (a minute).</summary>
    public const int CampScansToSettle = 2;
    public const int SettledRadius = 2_000;
    /// <summary>Both sides have fought monsters this recently: they are farming, not passing through.</summary>
    public const int FarmingWithinMs = 90_000;
    /// <summary>Per scan: about one invitation in five minutes of sharing a camp.</summary>
    public const double CampInviteChance = 0.10;
    /// <summary>Per scan while the LFG flag in the group window is up.</summary>
    public const double LfgFlagInviteChance = 0.35;
    public const long LfgInviteGapMs = 3 * 60_000;
    public const long CampInviteGapMs = 15 * 60_000;
    public const long InvitePairCooldownMs = 30 * 60_000;
    /// <summary>An invitation not answered in this long counts as ignored.</summary>
    public const long InviteAnswerWindowMs = 60_000;

    private sealed class InviteState
    {
        public long NextInvite;
        public long PendingUntil;
        public bool Muted;
        public int Settled;
        public ushort Region;
        public int X, Y;
    }

    private static readonly Dictionary<string, InviteState> Invites = new(StringComparer.OrdinalIgnoreCase);
    private static readonly Dictionary<(long BotId, string Player), long> LastInvitePair = new();
    private static long _nextInviteScan;

    public static bool GroupInvitesOn => Properties.BOT_INVITE_PLAYERS;

    private static InviteState InviteStateOf(GamePlayer player)
    {
        if (!Invites.TryGetValue(player.Name, out InviteState state))
            Invites[player.Name] = state = new InviteState();
        return state;
    }

    /// <summary>/bots invites on|off. For this login.</summary>
    public static void SetBotInvitesMuted(GamePlayer player, bool muted)
    {
        lock (Invites)
            InviteStateOf(player).Muted = muted;
    }

    public static bool BotInvitesMuted(GamePlayer player)
    {
        lock (Invites)
            return InviteStateOf(player).Muted;
    }

    /// <summary>"lfg 30 cleric", "looking for a group": the player says they want one. "not lfg", "lfm" (they have one) don't. Pure.</summary>
    public static bool SaysLookingForGroup(string message)
    {
        if (string.IsNullOrWhiteSpace(message))
            return false;
        string text = AutonomousChatQuestions.Normalize(message);
        return Regex.IsMatch(text, @"\b(lfg|looking for (a )?(group|grp|party)|lf (a )?(group|grp))\b") &&
               !Regex.IsMatch(text, @"\b(not|no|still no|hours|never) (lfg|looking)\b");
    }

    /// <summary>A bot asks only a player of about its level. Pure.</summary>
    public static bool FitsBotInvite(int botLevel, int playerLevel, int levelGap) => Math.Abs(botLevel - playerLevel) <= levelGap;

    /// <summary>The player has stayed about here for a scan more, or has moved on and starts over. Pure.</summary>
    public static int NextSettledCount(int settled, bool sameRegion, double movedBy) => sameRegion && movedBy <= SettledRadius ? settled + 1 : 0;

    /// <summary>The player is farming beside the bot, long enough for it to notice. Pure.</summary>
    public static bool SharesCamp(int settled, bool playerFarming, bool botFarming) =>
        settled >= CampScansToSettle && playerFarming && botFarming;

    private static bool PlayerOpenToInvite(GamePlayer player) =>
        GroupInvitesOn && player?.Client?.ClientState == GameClient.eClientState.Playing &&
        player.ObjectState == GameObject.eObjectState.Active && player.IsAlive && player.Group == null &&
        player.CustomDialogCallback == null && !AutonomousPlayerPilot.IsActive(player);

    /// <summary>The bots that join with this one: itself, or its whole group when it leads one. Empty when it can't invite.</summary>
    private static GameBot[] InvitingParty(GameBot bot)
    {
        if (bot.Group == null)
            return [bot];
        GameBot[] party = bot.Group.GetMembersInTheGroup().OfType<GameBot>().ToArray();
        return bot.Group.LivingLeader == bot && !GroupHasPlayer(bot.Group) && party.Length < Properties.GROUP_MAX_MEMBER &&
               party.All(member => member.PlayerGroupLeader == null && BotGroupInvite.DutyOf(member) == BotGroupInvite.Duty.None)
            ? party : [];
    }

    private static bool CanInvite(GameBot bot, GamePlayer player, int levelGap, long now)
    {
        if (!CanTalk(bot) || bot.PlayerGroupLeader != null || bot.IsOnStableMasterRoute || !FitsBotInvite(bot.Level, player.Level, levelGap) ||
            !ServerRules.HybridCoopRules.CanGroup(player, bot) || BotGroupInvite.DutyOf(bot) != BotGroupInvite.Duty.None ||
            InvitingParty(bot).Length == 0)
            return false;
        lock (Invites)
        {
            if (LastInvitePair.TryGetValue((bot.DatabaseID, player.Name), out long asked) && now - asked < InvitePairCooldownMs)
                return false;
        }
        return !TryRecall(bot, player, out OfflineBotMemoryRecord row) || MoodOf(row) != "cool";
    }

    /// <summary>
    /// The player said they are looking for a group: a bot nearby invites them a few seconds later. False when none will,
    /// so the caller can fall back on tells.
    /// </summary>
    public static bool TryInviteLookingPlayer(GamePlayer player)
    {
        if (!PlayerOpenToInvite(player))
            return false;
        long now = GameLoop.GameLoopTime;
        lock (Invites)
        {
            InviteState state = InviteStateOf(player);
            if (state.Muted || now < state.NextInvite || now < state.PendingUntil)
                return false;
        }
        GameBot bot = AutonomousBotRegistry.Snapshot()
            .Where(candidate => candidate.CurrentRegion == player.CurrentRegion && candidate.IsWithinRadius(player, LfgInviteRange) &&
                                CanInvite(candidate, player, LfgInviteLevelGap, now))
            .OrderBy(candidate => candidate.GetDistanceTo(player) + Random.Shared.Next(2_000)).FirstOrDefault();
        if (bot == null)
            return false;
        ScheduleInvite(bot, player, LfgInviteLevelGap, LfgInviteGapMs, 6_000 + Random.Shared.Next(14_000), false);
        return true;
    }

    /// <summary>The scan behind the group window's LFG flag and shared camps. Cheap: players only, every 30 seconds.</summary>
    private static void InvitePulse(long now)
    {
        if (!GroupInvitesOn || now < _nextInviteScan)
            return;
        _nextInviteScan = now + InviteScanMs;
        foreach (GamePlayer player in ClientService.Instance.GetPlayers())
        {
            bool open = PlayerOpenToInvite(player);
            int settled;
            lock (Invites)
            {
                InviteState state = InviteStateOf(player);
                double moved = state.Region == player.CurrentRegionID ? player.GetDistanceTo(new Point3D(state.X, state.Y, player.Z)) : double.MaxValue;
                settled = state.Settled = open ? NextSettledCount(state.Settled, state.Region == player.CurrentRegionID, moved) : 0;
                if (settled == 0)
                    (state.Region, state.X, state.Y) = (player.CurrentRegionID, player.X, player.Y);
                if (!open || state.Muted || now < state.NextInvite || now < state.PendingUntil)
                    continue;
            }
            if (player.LookingForGroup)
            {
                if (Random.Shared.NextDouble() < LfgFlagInviteChance)
                    TryInviteLookingPlayer(player);
                continue;
            }
            bool farming = player.InCombatPvEInLast(FarmingWithinMs);
            if (!SharesCamp(settled, farming, true) || Random.Shared.NextDouble() >= CampInviteChance)
                continue;
            GameBot bot = player.GetNPCsInRadius(CampInviteRange).OfType<GameBot>()
                .Where(candidate => SharesCamp(settled, farming, candidate.InCombatPvEInLast(FarmingWithinMs)) &&
                                    CanInvite(candidate, player, CampInviteLevelGap, now))
                .OrderBy(_ => Random.Shared.Next()).FirstOrDefault();
            if (bot != null)
                ScheduleInvite(bot, player, CampInviteLevelGap, CampInviteGapMs, 2_000 + Random.Shared.Next(6_000), true);
        }
    }

    private static void ScheduleInvite(GameBot bot, GamePlayer player, int levelGap, long gapMs, int delayMs, bool camp)
    {
        long now = GameLoop.GameLoopTime;
        lock (Invites)
        {
            InviteState state = InviteStateOf(player);
            state.PendingUntil = now + delayMs + InviteAnswerWindowMs;
            state.NextInvite = now + delayMs + gapMs;
            LastInvitePair[(bot.DatabaseID, player.Name)] = now;
        }
        // The pair cooldown above is what this check would trip on, so only what can change in the delay is checked again.
        Later(bot, delayMs, () => CanTalk(bot) && PlayerOpenToInvite(player) && BotGroupInvite.DutyOf(bot) == BotGroupInvite.Duty.None &&
                                  InvitingParty(bot).Length > 0, () => SendInvite(bot, player, camp));
    }

    private static string InviteLine(bool withGroup, bool camp, Random random)
    {
        string[] lines = camp
            ? withGroup
                ? ["hey we got room if u wanna join us", "want in? more xp with us", "join up, were farming the same stuff anyway"]
                : ["hey wanna group up here?", "want to duo? better xp", "lets just group, were on the same mobs"]
            : withGroup
                ? ["saw ur lfg, we got room", "looking for one more, u in?", "hey join us, we have a spot"]
                : ["saw ur lfg, wanna duo?", "lfg too, want to team up?", "hey want to group?"];
        return lines[random.Next(lines.Length)];
    }

    private static void SendInvite(GameBot bot, GamePlayer player, bool camp)
    {
        Tell(bot, player, AutonomousBotVoices.StyleFor(bot, InviteLine(bot.Group != null, camp, Random.Shared)));
        ChatUtil.SendSystemMessage(player, $"{bot.Name} has invited you to join {bot.GetPronoun(1, false)} group.");
        player.Out.SendCustomDialog($"{bot.Name} has invited you to join\n{bot.GetPronoun(1, false)} group. Do you wish to join?",
            (answering, response) => AnswerInvite(bot, answering, response));
    }

    private static void AnswerInvite(GameBot bot, GamePlayer player, byte response)
    {
        lock (Invites)
            InviteStateOf(player).PendingUntil = 0;
        if (response != 0x01)
            return;
        if (player.Group != null)
        {
            ChatUtil.SendSystemMessage(player, "You are still in a group.");
            return;
        }
        GameBot[] party = bot.ObjectState == GameObject.eObjectState.Active ? InvitingParty(bot) : [];
        if (party.Length == 0)
        {
            ChatUtil.SendSystemMessage(player, $"{bot.Name} can't take you along right now.");
            return;
        }
        foreach (GameBot member in party)
            BotGroupInvite.TryInvite(player, member, true);
    }
}
