using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Reflection;
using System.Text.Json;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using DOL.AI.Brain;
using DOL.Events;
using DOL.GS.ServerProperties;
using DOL.Logging;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace DOL.GS
{
    /// <summary>
    /// Floating combat numbers: the server streams each hit, heal and avoided attack that matters to a player to the
    /// launcher, which draws them over the game window. A player sees what they, their pets and their group do, and
    /// what is done to them; nobody else's fights. Listens on 127.0.0.1 only, at the login port plus PORT_OFFSET, as a
    /// server-sent event stream per account. The design follows Eden's server-fed overlay; no code is taken.
    /// </summary>
    public static class CombatNumbers
    {
        private static readonly Logger log = LoggerManager.Create(MethodBase.GetCurrentMethod().DeclaringType);
        public const int PORT_OFFSET = 30; // The Passport Desk has +10, Bot Watch +20.
        private const int QUEUE_LENGTH = 256;

        public enum Kind { Out, In, HealOut, HealIn, AvoidOut, AvoidIn }
        public enum Who { Self, Pet, Group }

        /// <summary>One number or word to float. Damage type is the eDamageType number; Text is set for avoided attacks (Miss, Block, Parry, Evade, Resist).</summary>
        public sealed record Number(Kind Kind, Who Who, int Value, bool Critical, int DamageType, string Text);

        private static readonly ConcurrentDictionary<string, ConcurrentDictionary<Channel<string>, byte>> Listeners =
            new(StringComparer.OrdinalIgnoreCase);
        private static int _listenerCount;
        private static WebApplication _app;
        private static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

        public static void Start(GameServerConfiguration config)
        {
            if (!Properties.COMBAT_NUMBERS)
                return;

            try
            {
                WebApplicationBuilder builder = WebApplication.CreateSlimBuilder();
                builder.Logging.ClearProviders();
                builder.WebHost.ConfigureKestrel(options => options.Listen(IPAddress.Loopback, config.Port + PORT_OFFSET));

                _app = builder.Build();
                _app.Use(RefuseForeignHosts);
                _app.MapGet("/combat", Stream);
                _app.StartAsync().GetAwaiter().GetResult();

                if (log.IsInfoEnabled)
                    log.Info($"Combat numbers stream at http://127.0.0.1:{config.Port + PORT_OFFSET}/combat?account=<name>");
            }
            catch (Exception e)
            {
                if (log.IsErrorEnabled)
                    log.Error("Combat numbers could not start", e);
            }
        }

        [GameServerStoppedEvent]
        public static void Stop(DOLEvent e, object sender, EventArgs args)
        {
            WebApplication app = Interlocked.Exchange(ref _app, null);

            if (app == null)
                return;

            // The launcher's overlay keeps a stream open, and Kestrel would wait its default 30 seconds for it to end.
            using CancellationTokenSource timeout = new(TimeSpan.FromSeconds(2));

            try
            {
                app.StopAsync(timeout.Token).GetAwaiter().GetResult();
            }
            catch (OperationCanceledException)
            {
            }
        }

        // A page on another site could otherwise read the stream through a DNS name pointed at 127.0.0.1.
        private static async Task RefuseForeignHosts(HttpContext context, Func<Task> next)
        {
            string host = context.Request.Host.Host;

            if (host is not ("127.0.0.1" or "localhost"))
            {
                context.Response.StatusCode = StatusCodes.Status403Forbidden;
                return;
            }

            await next();
        }

        private static async Task Stream(HttpContext context)
        {
            string account = context.Request.Query["account"];

            if (string.IsNullOrWhiteSpace(account))
            {
                context.Response.StatusCode = StatusCodes.Status400BadRequest;
                return;
            }

            Channel<string> channel = Subscribe(account);

            try
            {
                context.Response.ContentType = "text/event-stream";
                context.Response.Headers.CacheControl = "no-store";
                await context.Response.WriteAsync(": open\n\n", context.RequestAborted);
                await context.Response.Body.FlushAsync(context.RequestAborted);

                while (!context.RequestAborted.IsCancellationRequested)
                {
                    using var wait = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);
                    wait.CancelAfter(TimeSpan.FromSeconds(15));
                    string line;

                    try
                    {
                        line = await channel.Reader.ReadAsync(wait.Token);
                    }
                    catch (OperationCanceledException) when (!context.RequestAborted.IsCancellationRequested)
                    {
                        line = ": idle\n\n"; // Keeps the connection from looking dead to the launcher.
                    }

                    await context.Response.WriteAsync(line, context.RequestAborted);
                    await context.Response.Body.FlushAsync(context.RequestAborted);
                }
            }
            catch (OperationCanceledException)
            {
            }
            finally
            {
                Unsubscribe(account, channel);
            }
        }

        public static Channel<string> Subscribe(string account)
        {
            Channel<string> channel = Channel.CreateBounded<string>(new BoundedChannelOptions(QUEUE_LENGTH)
            {
                FullMode = BoundedChannelFullMode.DropOldest,
                SingleReader = true
            });
            Listeners.GetOrAdd(account, _ => new())[channel] = 0;
            Interlocked.Increment(ref _listenerCount);
            EffectWindows.EnsureRunning();
            return channel;
        }

        public static void Unsubscribe(string account, Channel<string> channel)
        {
            if (Listeners.TryGetValue(account, out var channels) && channels.TryRemove(channel, out _))
                Interlocked.Decrement(ref _listenerCount);
        }

        /// <summary>Called from GameObject.TakeDamage once the damage is final.</summary>
        public static void Damage(GameObject target, GameObject source, eDamageType damageType, int damageAmount, int criticalAmount)
        {
            if (Volatile.Read(ref _listenerCount) == 0)
                return;

            int total = damageAmount + criticalAmount;

            if (total <= 0)
                return;

            Report(target, source, Kind.Out, Kind.In, total, criticalAmount > 0, (int)damageType, null);
            FightReports.Damage(target, source, total);
        }

        /// <summary>Called from GameLiving.ChangeHealth for heals other than natural regeneration.</summary>
        public static void Heal(GameLiving target, GameObject source, int amount)
        {
            if (Volatile.Read(ref _listenerCount) == 0 || amount <= 0)
                return;

            Report(target, source, Kind.HealOut, Kind.HealIn, amount, false, 0, null);
            FightReports.Heal(target, source, amount);
        }

        /// <summary>Called from GameLiving.OnAttackedByEnemy: misses, blocks, parries, evades and resisted spells.</summary>
        public static void Avoided(AttackData ad)
        {
            if (Volatile.Read(ref _listenerCount) == 0 || ad == null)
                return;

            string text = ad.IsSpellResisted ? "Resist" : ad.AttackResult switch
            {
                eAttackResult.Missed => "Miss",
                eAttackResult.Blocked => "Block",
                eAttackResult.Parried => "Parry",
                eAttackResult.Evaded => "Evade",
                _ => null
            };

            if (text != null)
                Report(ad.Target, ad.Attacker, Kind.AvoidOut, Kind.AvoidIn, 0, false, (int)ad.DamageType, text);
        }

        private static void Report(GameObject target, GameObject source, Kind outKind, Kind inKind, int value, bool critical,
            int damageType, string text)
        {
            GameLiving doer = Owner(source, out bool byPet);

            foreach ((GamePlayer viewer, bool done, Who who) in Viewers(doer, byPet, doer?.Group?.GetMembersInTheGroup(), target))
            {
                if (IsListening(viewer))
                    Publish(viewer, Frame(null, new Number(done ? outKind : inKind, who, value, critical, damageType, text)));
            }
        }

        /// <summary>Called from GameLiving.Die, once per death.</summary>
        public static void Died(GameLiving victim, GameObject killer)
        {
            if (Volatile.Read(ref _listenerCount) != 0)
                FightReports.Died(victim, killer);
        }

        public static bool AnyListening => Volatile.Read(ref _listenerCount) != 0;

        public static bool IsListening(GamePlayer player)
        {
            string account = player?.Client?.Account?.Name;
            return account != null && Listeners.TryGetValue(account, out var channels) && !channels.IsEmpty;
        }

        /// <summary>One server-sent event: a number when eventName is null, else the named event (such as "fight").</summary>
        public static string Frame(string eventName, object payload)
        {
            string data = $"data: {JsonSerializer.Serialize(payload, payload.GetType(), Json)}\n\n";
            return eventName == null ? data : $"event: {eventName}\n{data}";
        }

        public static void Publish(GamePlayer viewer, string frame)
        {
            string account = viewer?.Client?.Account?.Name;

            if (account == null || !Listeners.TryGetValue(account, out var channels))
                return;

            foreach (Channel<string> channel in channels.Keys)
                channel.Writer.TryWrite(frame);
        }

        /// <summary>
        /// Who sees a number, once each: the player who did it (or whose pet did), every player in that doer's group, and
        /// the player it was done to. Done is false only for the player it was done to. Bystanders see nothing.
        /// </summary>
        public static List<(GamePlayer Viewer, bool Done, Who Who)> Viewers(GameLiving doer, bool byPet,
            IEnumerable<GameLiving> doersGroup, GameObject target)
        {
            var viewers = new List<(GamePlayer, bool, Who)>();
            var seen = new HashSet<GamePlayer>();

            if (doersGroup != null)
            {
                foreach (GameLiving member in doersGroup)
                {
                    // A group mate healing you shows as a heal you received, below.
                    if (member is GamePlayer viewer && (member == doer || member != target) && seen.Add(viewer))
                        viewers.Add((viewer, true, member == doer ? (byPet ? Who.Pet : Who.Self) : Who.Group));
                }
            }

            if (doer is GamePlayer soloDoer && seen.Add(soloDoer))
                viewers.Add((soloDoer, true, byPet ? Who.Pet : Who.Self));

            // What is done to the player, by anyone. A self heal or a hit on yourself was already counted as theirs.
            if (target is GamePlayer victim && seen.Add(victim))
                viewers.Add((victim, false, Who.Self));

            return viewers;
        }

        /// <summary>The living that should get credit: a pet's owner (through pets of pets), or the source itself.</summary>
        public static GameLiving Owner(GameObject source, out bool byPet)
        {
            byPet = false;
            GameLiving living = source as GameLiving;

            for (int depth = 0; depth < 3 && living is GameNPC npc && npc.Brain is IControlledBrain brain &&
                 brain.GetLivingOwner() is GameLiving owner && owner != living; depth++)
            {
                living = owner;
                byPet = true;
            }

            return living;
        }
    }
}
