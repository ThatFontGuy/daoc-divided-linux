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
    /// Buff, debuff and pet windows: once a second every listening player gets an "effects" event on the combat numbers
    /// stream with the effects on them, their pets' health and effects, and their target's health and effects, each with
    /// its time left and whether they or their pets cast it. The launcher overlay draws them. The idea is Eden's buff,
    /// debuff and group pet windows; no code is taken.
    /// </summary>
    public static class EffectWindows
    {
        private static readonly Logger log = LoggerManager.Create(MethodBase.GetCurrentMethod().DeclaringType);
        private const int SEND_MILLISECONDS = 1000;
        public const int MAX_EFFECTS = 16;
        public const int ENDLESS_SECONDS = 65535;

        /// <summary>Seconds and Total are 0 for an effect without an end (a toggle, an aura, a concentration buff).</summary>
        public sealed record Effect(string Name, int Icon, int Seconds, int Total, bool Good, bool Mine);
        public sealed record Unit(string Name, int Level, int Health, Effect[] Effects);
        public sealed record Snapshot(Effect[] Self, Unit[] Pets, Unit Target);

        private static Timer _timer;

        /// <summary>Starts the once-a-second send; called when the first stream opens.</summary>
        public static void EnsureRunning()
        {
            if (Volatile.Read(ref _timer) != null)
                return;

            var timer = new Timer(_ => Send(), null, Timeout.Infinite, Timeout.Infinite);

            if (Interlocked.CompareExchange(ref _timer, timer, null) == null)
                timer.Change(SEND_MILLISECONDS, SEND_MILLISECONDS);
            else
                timer.Dispose();
        }

        private static void Send()
        {
            try
            {
                if (!CombatNumbers.AnyListening)
                    return;

                foreach (GamePlayer player in ClientService.Instance.GetPlayers())
                {
                    if (CombatNumbers.IsListening(player) && player.ObjectState == GameObject.eObjectState.Active)
                        CombatNumbers.Publish(player, CombatNumbers.Frame("effects", Of(player)));
                }
            }
            catch (Exception e)
            {
                // A timer callback that throws would end the server.
                if (log.IsErrorEnabled)
                    log.Error("Effect windows send failed", e);
            }
        }

        public static Snapshot Of(GamePlayer player)
        {
            HashSet<GameLiving> mine = new() { player };
            List<GameNPC> pets = Pets(player).ToList();
            mine.UnionWith(pets);

            Unit target = player.TargetObject is GameLiving living && living != player && !pets.Contains(living)
                ? ToUnit(living, mine) : null;

            return new Snapshot(Effects(player, mine), pets.Select(pet => ToUnit(pet, mine)).ToArray(), target);
        }

        /// <summary>The player's pets and, for a Bonedancer's commander, the commander's own pets.</summary>
        private static IEnumerable<GameNPC> Pets(GamePlayer player)
        {
            if (player.ControlledBrain?.Body is not GameNPC pet)
                yield break;

            yield return pet;

            foreach (IControlledBrain brain in pet.ControlledNpcList ?? Array.Empty<IControlledBrain>())
            {
                if (brain?.Body is GameNPC subPet && subPet.IsAlive)
                    yield return subPet;
            }
        }

        private static Unit ToUnit(GameLiving living, HashSet<GameLiving> mine) =>
            new(living.Name, living.Level, living.HealthPercent, Effects(living, mine));

        private static Effect[] Effects(GameLiving living, HashSet<GameLiving> mine)
        {
            var effects = new List<Effect>();

            foreach (ECSGameEffect effect in living.effectListComponent.GetEffects())
            {
                if (!effect.IsActive || effect.Icon == 0)
                    continue;

                // Spell effects keep their handler in a field of their own that hides the base one.
                GameLiving caster = (effect as ECSGameSpellEffect)?.SpellHandler?.Caster ?? effect.SpellHandler?.Caster;
                // Pet summons and the like use 65535 seconds as "no end".
                bool timed = effect.Duration > 0 && effect.Duration < ENDLESS_SECONDS * 1000L;
                int seconds = timed ? (int)Math.Max(0, (effect.GetRemainingTimeForClient() + 999) / 1000) : 0;
                effects.Add(new Effect(effect.Name, effect.Icon, seconds, timed ? (int)(effect.Duration / 1000) : 0, effect.HasPositiveEffect,
                    caster != null && mine.Contains(caster)));
            }

            return Order(effects).Take(MAX_EFFECTS).ToArray();
        }

        /// <summary>Harmful first, then the ones you cast, then the ones ending soonest; endless ones last.</summary>
        public static IEnumerable<Effect> Order(IEnumerable<Effect> effects) =>
            effects.OrderBy(effect => effect.Good)
                .ThenByDescending(effect => effect.Mine)
                .ThenBy(effect => effect.Seconds == 0 ? int.MaxValue : effect.Seconds);
    }
}
