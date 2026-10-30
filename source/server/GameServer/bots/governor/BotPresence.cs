using System;
using System.Reflection;
using System.Threading;
using DOL.Events;
using DOL.GS.ServerProperties;
using DOL.Logging;

namespace DOL.GS
{
    /// <summary>Settings for the "no players, no bots" rule (daoc-divided-linux addition, not part of DividedRealms).</summary>
    public static class BotPresenceProperties
    {
        [ServerProperty("bots", "bots_only_with_players", "Log the ordinary bots out when no player is in the world, and bring them back when one arrives. Bracket bots have their own rule.", true)]
        public static bool ONLY_WITH_PLAYERS;

        [ServerProperty("bots", "bots_only_with_players_grace_seconds", "How long the bots stay after the last player leaves the world before they log out.", 120)]
        public static int GRACE_SECONDS;
    }

    /// <summary>
    /// Tracks whether any real player is in the world. Used by AutonomousBotSchedule (Living Server), which already knows how to
    /// log bots out safely and keep the population controller from logging them back in. Hooks elsewhere: AutonomousBotSchedule
    /// <c>Active</c>, <c>Pulse</c> and <c>WantsOnline</c> (see UPSTREAM.md).
    /// </summary>
    public static class BotPresence
    {
        private static readonly Logger Log = LoggerManager.Create(MethodBase.GetCurrentMethod().DeclaringType);
        private static Timer _timer;
        private static long _lastPlayerSeenTicks = long.MinValue; // UtcNow ticks; MinValue = none seen since the server started
        private static volatile bool _noPlayers = true;

        public static bool Enabled => BotPresenceProperties.ONLY_WITH_PLAYERS;

        /// <summary>True when the rule is on and no player has been in the world for the grace period (nor since the server started).</summary>
        public static bool NoPlayers => Enabled && _noPlayers;

        [GameServerStartedEvent]
        public static void OnServerStarted(DOLEvent e, object sender, EventArgs args)
        {
            _timer = new Timer(Tick, null, 2_000, 5_000);
        }

        [GameServerStoppedEvent]
        public static void OnServerStopped(DOLEvent e, object sender, EventArgs args)
        {
            _timer?.Dispose();
            _timer = null;
        }

        /// <summary>The rule itself, apart from the clock and the server, so it can be tested.</summary>
        public static bool ComputeNoPlayers(DateTime nowUtc, long lastPlayerSeenTicks, bool playerPresent, int graceSeconds, out long newLastSeenTicks)
        {
            newLastSeenTicks = playerPresent ? nowUtc.Ticks : lastPlayerSeenTicks;
            if (playerPresent)
                return false;
            if (newLastSeenTicks == long.MinValue)
                return true;
            return (nowUtc - new DateTime(newLastSeenTicks, DateTimeKind.Utc)).TotalSeconds >= Math.Max(0, graceSeconds);
        }

        private static void Tick(object state)
        {
            try
            {
                bool present = false;
                foreach (GamePlayer player in ClientService.Instance.GetPlayers())
                {
                    if (player.ObjectState == GameObject.eObjectState.Active)
                    {
                        present = true;
                        break;
                    }
                }
                bool was = _noPlayers;
                _noPlayers = ComputeNoPlayers(DateTime.UtcNow, _lastPlayerSeenTicks, present, BotPresenceProperties.GRACE_SECONDS, out long seen);
                _lastPlayerSeenTicks = seen;
                if (Enabled && was != _noPlayers)
                    Log.Info(_noPlayers ? "BOT_PRESENCE no players in the world: bots will log out" : "BOT_PRESENCE a player is in the world: bots may log in");
            }
            catch (Exception exception)
            {
                Log.Warn("Bot presence tick failed", exception);
            }
        }
    }
}
