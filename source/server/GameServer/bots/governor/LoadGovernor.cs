using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using DOL.Events;
using DOL.GS.ServerProperties;
using DOL.Logging;

namespace DOL.GS
{
    /// <summary>
    /// Settings for the bot load governor (daoc-divided-linux addition, not part of DividedRealms).
    /// </summary>
    public static class LoadGovernorProperties
    {
        [ServerProperty("load_governor", "load_governor_enabled", "Protect the server from bot overload: stop logging bots in while the game loop runs slow or free memory is low, and log some bots out if it stays that way.", true)]
        public static bool ENABLED;

        [ServerProperty("load_governor", "load_governor_min_tps_percent", "Stop logging bots in when the game loop's 30-second tick rate falls below this percent of its target.", 90)]
        public static int MIN_TPS_PERCENT;

        [ServerProperty("load_governor", "load_governor_resume_tps_percent", "Resume logging bots in once the tick rate is back at or above this percent (for a full minute).", 95)]
        public static int RESUME_TPS_PERCENT;

        [ServerProperty("load_governor", "load_governor_min_free_mb", "Stop logging bots in when the machine has less than this many MB of memory available (Linux only; 0 = ignore memory).", 1500)]
        public static int MIN_FREE_MB;

        [ServerProperty("load_governor", "load_governor_shed_after_seconds", "If the server stays overloaded this long with logins stopped, log out a few bots at a time (only bots that can leave safely) until it recovers.", 120)]
        public static int SHED_AFTER_SECONDS;
    }

    /// <summary>The decision logic of the governor, free of the clock and the server so it can be unit tested.</summary>
    public sealed class LoadGovernorPolicy
    {
        public const int ResumeAfterSeconds = 60;
        public const int ShedEverySeconds = 30;
        public const int ShedBatch = 3;
        public const int MemoryHysteresisMb = 300;

        public readonly record struct Decision(bool HoldLogins, int Shed, bool Changed);

        private DateTime _holdSince;
        private DateTime? _healthySince;
        private DateTime _nextShed;

        public bool Holding { get; private set; }

        /// <param name="tpsPercent">30-second game loop rate as a percent of target (100 when unknown).</param>
        /// <param name="freeMb">Available memory in MB, or -1 when unknown.</param>
        public Decision Update(DateTime now, double tpsPercent, long freeMb, int minTpsPercent, int resumeTpsPercent, int minFreeMb, int shedAfterSeconds)
        {
            resumeTpsPercent = Math.Max(resumeTpsPercent, minTpsPercent); // a resume level below the hold level would flip-flop
            bool memoryKnown = freeMb >= 0 && minFreeMb > 0;
            bool unhealthy = tpsPercent < minTpsPercent || (memoryKnown && freeMb < minFreeMb);
            bool recovered = tpsPercent >= resumeTpsPercent && (!memoryKnown || freeMb >= minFreeMb + MemoryHysteresisMb);
            bool changed = false;

            if (!Holding)
            {
                if (unhealthy)
                {
                    Holding = true;
                    _holdSince = now;
                    _healthySince = null;
                    _nextShed = now.AddSeconds(Math.Max(0, shedAfterSeconds));
                    changed = true;
                }
            }
            else if (recovered)
            {
                _healthySince ??= now;
                if ((now - _healthySince.Value).TotalSeconds >= ResumeAfterSeconds)
                {
                    Holding = false;
                    _healthySince = null;
                    changed = true;
                }
            }
            else
            {
                _healthySince = null;
            }

            int shed = 0;
            if (Holding && unhealthy && now >= _nextShed)
            {
                shed = ShedBatch;
                _nextShed = now.AddSeconds(ShedEverySeconds);
            }
            return new Decision(Holding, shed, changed);
        }
    }

    /// <summary>
    /// Bot load governor: every 10 seconds it reads the game loop's tick rate (and free memory on Linux). Below the limit it stops
    /// the population controller from logging more bots in; if the overload lasts it logs a few bots out at a time, using the
    /// same safe-to-leave test as the Living Server schedule. Only hook elsewhere: <see cref="HoldLogins"/> in
    /// AutonomousPopulationController.Poll.
    /// </summary>
    public static class LoadGovernor
    {
        private static readonly Logger Log = LoggerManager.Create(MethodBase.GetCurrentMethod().DeclaringType);
        private const int StartupGraceSeconds = 120; // the world is still loading and the first bots are logging in
        private static readonly LoadGovernorPolicy Policy = new();
        private static Timer _timer;
        private static int _busy;
        private static DateTime _startedUtc;
        private static volatile bool _hold;

        /// <summary>True while the server is overloaded: no more bots should be logged in.</summary>
        public static bool HoldLogins => _hold && LoadGovernorProperties.ENABLED;

        [GameServerStartedEvent]
        public static void OnServerStarted(DOLEvent e, object sender, EventArgs args)
        {
            _startedUtc = DateTime.UtcNow;
            _timer = new Timer(Tick, null, 10_000, 10_000);
        }

        [GameServerStoppedEvent]
        public static void OnServerStopped(DOLEvent e, object sender, EventArgs args)
        {
            _timer?.Dispose();
            _timer = null;
        }

        private static void Tick(object state)
        {
            if (Interlocked.Exchange(ref _busy, 1) != 0)
                return;
            try
            {
                DateTime now = DateTime.UtcNow;
                if (!LoadGovernorProperties.ENABLED || (now - _startedUtc).TotalSeconds < StartupGraceSeconds)
                {
                    _hold = false;
                    return;
                }

                double tpsPercent = CurrentTpsPercent();
                long freeMb = AvailableMemoryMb();
                LoadGovernorPolicy.Decision decision = Policy.Update(now, tpsPercent, freeMb,
                    LoadGovernorProperties.MIN_TPS_PERCENT, LoadGovernorProperties.RESUME_TPS_PERCENT,
                    LoadGovernorProperties.MIN_FREE_MB, LoadGovernorProperties.SHED_AFTER_SECONDS);
                _hold = decision.HoldLogins;
                if (decision.Changed)
                    Log.Warn($"LOAD_GOVERNOR {(decision.HoldLogins ? "holding bot logins" : "resuming bot logins")} tps={tpsPercent:F1}% freeMb={freeMb} bots={AutonomousBotRegistry.Count}");
                if (decision.Shed > 0)
                    Shed(decision.Shed, tpsPercent, freeMb);
            }
            catch (Exception exception)
            {
                Log.Warn("Load governor tick failed", exception);
            }
            finally
            {
                Volatile.Write(ref _busy, 0);
            }
        }

        // The 30-second average; 0 means the game loop has too few samples yet, which counts as healthy.
        private static double CurrentTpsPercent()
        {
            double target = ServerProperties.Properties.GAME_LOOP_TICK_RATE;
            if (target <= 0)
                return 100;
            foreach ((int interval, double tps) in GameLoop.GetAverageTps())
            {
                if (interval == 30_000)
                    return tps <= 0 ? 100 : tps / target * 100.0;
            }
            return 100;
        }

        private static long AvailableMemoryMb()
        {
            try
            {
                const string path = "/proc/meminfo";
                if (!File.Exists(path))
                    return -1;
                foreach (string line in File.ReadLines(path))
                {
                    if (line.StartsWith("MemAvailable:", StringComparison.Ordinal))
                        return long.Parse(line.Split(' ', StringSplitOptions.RemoveEmptyEntries)[1]) / 1024;
                }
            }
            catch
            {
            }
            return -1;
        }

        private static void Shed(int count, double tpsPercent, long freeMb)
        {
            GameBot[] leaving = AutonomousBotRegistry.Snapshot()
                .Where(AutonomousBotSchedule.CanLogOut)
                .OrderBy(_ => Random.Shared.Next())
                .Take(count)
                .ToArray();
            foreach (GameBot bot in leaving)
            {
                _ = new ECSGameTimer(bot, timer =>
                {
                    try
                    {
                        if (AutonomousBotSchedule.CanLogOut(bot))
                        {
                            Log.Warn($"LOAD_GOVERNOR_LOGOUT bot=\"{bot.Name}\" id={bot.DatabaseID} tps={tpsPercent:F1}% freeMb={freeMb}");
                            bot.Delete();
                        }
                    }
                    catch (Exception exception)
                    {
                        Log.Warn($"Load governor: {bot.Name} could not log out", exception);
                    }
                    return 0;
                }, 1_000 + Random.Shared.Next(2_000));
            }
        }
    }
}
