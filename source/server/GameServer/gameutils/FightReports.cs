using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using DOL.AI.Brain;
using DOL.Logging;

namespace DOL.GS
{
    /// <summary>
    /// Fight reports: for each listening player's party (their group, or just them), a fight starts at the first hit
    /// given or taken and ends after QUIET_MILLISECONDS without one. Then every listening player in the party gets one
    /// "fight" event on the combat numbers stream: how long it lasted, and for each of their side (players, companions,
    /// pets) and each kind of enemy the damage done and taken, healing done and received, kills and deaths.
    /// The idea is Eden's fight window; no code is taken.
    /// </summary>
    public static class FightReports
    {
        public const int QUIET_MILLISECONDS = 8000;
        private const int SWEEP_MILLISECONDS = 1000;

        public sealed record Row(string Name, string Class, int Level, string Kind, int Count, long Done, long Taken,
            long Healed, long HealedTaken, int Kills, int Deaths);
        public sealed record Report(int Seconds, Row[] Allies, Row[] Enemies);

        private static readonly Logger log = LoggerManager.Create(MethodBase.GetCurrentMethod().DeclaringType);
        private static readonly FightBook Book = new(EnemyKey);
        private static readonly Lock BookLock = new();
        private static Timer _sweep;

        public static void Damage(GameObject target, GameObject source, int amount)
        {
            if (target is not GameLiving victim || source is not GameLiving attacker || victim == attacker)
                return;

            object attackerParty = TrackedParty(attacker);
            object victimParty = TrackedParty(victim);

            if (attackerParty == null && victimParty == null)
                return;

            lock (BookLock)
                Book.Hit(attackerParty, attacker, victimParty, victim, amount, Now);

            EnsureSweeping();
        }

        public static void Heal(GameLiving target, GameObject source, int amount)
        {
            object targetParty = TrackedParty(target);
            object healerParty = source is GameLiving healer ? TrackedParty(healer) : null;

            if (targetParty == null && healerParty == null)
                return;

            lock (BookLock)
                Book.Heal(healerParty, source as GameLiving, targetParty, target, amount, Now);
        }

        public static void Died(GameLiving victim, GameObject killer)
        {
            GameLiving killerLiving = killer as GameLiving;
            object victimParty = TrackedParty(victim);
            object killerParty = killerLiving != null ? TrackedParty(killerLiving) : null;

            if (victimParty == null && killerParty == null)
                return;

            lock (BookLock)
                Book.Died(victimParty, victim, killerParty, killerLiving, Now);
        }

        private static long Now => Environment.TickCount64;

        private static void EnsureSweeping()
        {
            if (Volatile.Read(ref _sweep) != null)
                return;

            var timer = new Timer(_ => Sweep(), null, Timeout.Infinite, Timeout.Infinite);

            if (Interlocked.CompareExchange(ref _sweep, timer, null) == null)
                timer.Change(SWEEP_MILLISECONDS, SWEEP_MILLISECONDS);
            else
                timer.Dispose();
        }

        private static void Sweep()
        {
            try
            {
                SweepEnded();
            }
            catch (Exception e)
            {
                // A timer callback that throws would end the server.
                if (log.IsErrorEnabled)
                    log.Error("Fight reports sweep failed", e);
            }
        }

        private static void SweepEnded()
        {
            List<(object Party, FightBook.Fight Fight)> ended;

            lock (BookLock)
                ended = Book.Close(Now, QUIET_MILLISECONDS);

            foreach ((object party, FightBook.Fight fight) in ended)
            {
                string frame = null;

                foreach (GamePlayer viewer in Players(party))
                {
                    if (!CombatNumbers.IsListening(viewer))
                        continue;

                    frame ??= CombatNumbers.Frame("fight", ToReport(fight));
                    CombatNumbers.Publish(viewer, frame);
                }
            }
        }

        public static Report ToReport(FightBook.Fight fight)
        {
            Row[] allies = fight.Allies.Select(entry => ToRow(entry.Key, entry.Value))
                .OrderByDescending(row => row.Done + row.Healed).ToArray();
            Row[] enemies = fight.Enemies.Values.Select(tally => ToRow(tally.First, tally))
                .OrderByDescending(row => row.Taken).ToArray();
            return new Report(fight.Seconds, allies, enemies);
        }

        private static Row ToRow(object who, FightBook.Tally tally)
        {
            GameLiving living = who as GameLiving;
            string kind = living switch
            {
                GamePlayer => "player",
                GameBot => "companion",
                GameNPC { Brain: IControlledBrain } => "pet",
                _ => "npc"
            };
            string className = living switch
            {
                GamePlayer player => player.CharacterClass?.Name,
                GameBot bot => bot.CharacterClass?.Name,
                _ => null
            };

            return new Row(living?.Name ?? who?.ToString(), className, living?.Level ?? 0, kind, tally.Members.Count,
                tally.Done, tally.Taken, tally.Healed, tally.HealedTaken, tally.Kills, tally.Deaths);
        }

        /// <summary>Monsters of one name are one enemy row; players and companions each have their own.</summary>
        private static object EnemyKey(object who) => who is GameNPC npc and not GameBot ? "npc:" + npc.Name : who;

        /// <summary>The party a fight belongs to (the group, or a lone player), when a player in it is listening.</summary>
        private static object TrackedParty(GameLiving living)
        {
            GameLiving owner = CombatNumbers.Owner(living, out _);

            if (owner?.Group is Group group)
                return Players(group).Any(CombatNumbers.IsListening) ? group : null;

            return owner is GamePlayer player && CombatNumbers.IsListening(player) ? player : null;
        }

        private static IEnumerable<GamePlayer> Players(object party) => party switch
        {
            Group group => group.GetMembersInTheGroup().OfType<GamePlayer>(),
            GamePlayer player => new[] { player },
            _ => Array.Empty<GamePlayer>()
        };
    }

    /// <summary>
    /// The bookkeeping behind fight reports, on plain objects so it can be tested without a world: parties, the livings
    /// on their side, and the enemies they meet, merged by enemyKey.
    /// </summary>
    public sealed class FightBook
    {
        public sealed class Tally
        {
            public object First;
            public readonly HashSet<object> Members = new();
            public long Done, Taken, Healed, HealedTaken;
            public int Kills, Deaths;
        }

        public sealed class Fight
        {
            public long Started, LastActive;
            public readonly Dictionary<object, Tally> Allies = new();
            public readonly Dictionary<object, Tally> Enemies = new();
            public int Seconds => (int)Math.Max(1, (LastActive - Started + 999) / 1000);
        }

        private readonly Func<object, object> _enemyKey;
        private readonly Dictionary<object, Fight> _open = new();

        public FightBook(Func<object, object> enemyKey) => _enemyKey = enemyKey;

        public int OpenFights => _open.Count;

        /// <summary>A hit starts or continues a fight for each tracked side. A null party is a side nobody is listening for.</summary>
        public void Hit(object attackerParty, object attacker, object targetParty, object target, int amount, long now)
        {
            if (attackerParty != null)
            {
                Fight fight = Open(attackerParty, now);
                Ally(fight, attacker).Done += amount;

                if (targetParty != attackerParty)
                    Enemy(fight, target).Taken += amount;
            }

            if (targetParty != null && targetParty != attackerParty)
            {
                Fight fight = Open(targetParty, now);
                Ally(fight, target).Taken += amount;
                Enemy(fight, attacker).Done += amount;
            }
        }

        /// <summary>Heals count only inside a fight already going; healing out of combat starts nothing.</summary>
        public void Heal(object healerParty, object healer, object targetParty, object target, int amount, long now)
        {
            if (healerParty != null && healer != null && _open.TryGetValue(healerParty, out Fight healers))
            {
                healers.LastActive = now;
                Ally(healers, healer).Healed += amount;

                if (targetParty == healerParty)
                    Ally(healers, target).HealedTaken += amount;
            }

            if (targetParty != null && targetParty != healerParty && _open.TryGetValue(targetParty, out Fight healed))
            {
                healed.LastActive = now;
                Ally(healed, target).HealedTaken += amount;

                if (healer != null)
                    Enemy(healed, healer).Healed += amount;
            }
        }

        public void Died(object victimParty, object victim, object killerParty, object killer, long now)
        {
            if (victimParty != null && _open.TryGetValue(victimParty, out Fight lost))
            {
                lost.LastActive = now;
                Ally(lost, victim).Deaths++;

                if (killer != null && killerParty != victimParty)
                    Enemy(lost, killer).Kills++;
            }

            if (killerParty != null && killerParty != victimParty && _open.TryGetValue(killerParty, out Fight won))
            {
                won.LastActive = now;
                Ally(won, killer).Kills++;
                Enemy(won, victim).Deaths++;
            }
        }

        /// <summary>Removes and returns the fights quiet for at least quietMilliseconds.</summary>
        public List<(object Party, Fight Fight)> Close(long now, int quietMilliseconds)
        {
            var ended = _open.Where(entry => now - entry.Value.LastActive >= quietMilliseconds)
                .Select(entry => (entry.Key, entry.Value)).ToList();

            foreach ((object party, _) in ended)
                _open.Remove(party);

            return ended;
        }

        private Fight Open(object party, long now)
        {
            if (!_open.TryGetValue(party, out Fight fight))
                _open[party] = fight = new Fight { Started = now };

            fight.LastActive = now;
            return fight;
        }

        private static Tally Ally(Fight fight, object who) => Get(fight.Allies, who, who);

        private Tally Enemy(Fight fight, object who) => Get(fight.Enemies, _enemyKey(who), who);

        private static Tally Get(Dictionary<object, Tally> tallies, object key, object who)
        {
            if (!tallies.TryGetValue(key, out Tally tally))
                tallies[key] = tally = new Tally { First = who };

            tally.Members.Add(who);
            return tally;
        }
    }
}
