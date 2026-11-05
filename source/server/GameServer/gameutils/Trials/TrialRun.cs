using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using DOL.AI.Brain;
using DOL.GS.PacketHandler;

namespace DOL.GS.Trials
{
    public enum TrialRunState
    {
        Running,
        Completed,
        Failed,
    }

    /// <summary>
    /// One attempt at a trial. Everything that changes the world happens on its one-second tick: deaths and
    /// clicks arrive from other threads and only queue, so phase hooks never race each other.
    /// </summary>
    public sealed class TrialRun
    {
        private const int AbandonSeconds = 30;

        private readonly List<TrialMob> _mobs = new();
        private readonly ConcurrentQueue<TrialMob> _finished = new();
        private readonly Dictionary<string, object> _state = new();
        private readonly HashSet<GamePlayer> _players;
        private readonly HashSet<GamePlayer> _breathing = new();
        private ECSGameTimer _timer;
        private int _elapsed, _phaseElapsed, _phaseFinished, _abandoned;
        private int _phaseIndex = -1;

        public TrialDefinition Definition { get; }
        public TrialStarter Starter { get; }
        public GamePlayer Leader { get; }
        public TrialRunState State { get; private set; } = TrialRunState.Running;
        public double HealthScale { get; }
        public double DamageScale { get; }
        public int PartySize { get; }
        /// <summary>Test mode: each tick clears the phase, and phases that won't end are noted and passed.</summary>
        public bool Sweeping { get; set; }
        public List<string> SweepNotes { get; } = new();
        public TrialPhase Phase => _phaseIndex >= 0 && _phaseIndex < Definition.Phases.Count ? Definition.Phases[_phaseIndex] : null;
        public IReadOnlyCollection<GamePlayer> Players => _players;

        /// <summary>Scratch space for a trial's own hooks.</summary>
        public T Get<T>(string key, T fallback = default) => _state.TryGetValue(key, out object value) ? (T)value : fallback;
        public void Set(string key, object value) => _state[key] = value;

        public TrialRun(TrialStarter starter, GamePlayer leader)
        {
            Definition = starter.Definition;
            Starter = starter;
            Leader = leader;
            bool alone = Definition.Scope == TrialScope.Solo || leader.Group == null;
            _players = alone ? new() { leader }
                : leader.Group.GetPlayersInTheGroup().Where(player => player.IsWithinRadius(starter, Definition.LeashRange)).ToHashSet();
            _players.Add(leader);
            PartySize = alone ? 1 : leader.Group.GetMembersInTheGroup().Count(member => member.IsWithinRadius(starter, Definition.LeashRange));
            HealthScale = TrialScaling.HealthScale(Definition.Scope, PartySize);
            DamageScale = TrialScaling.DamageScale(Definition.Scope, PartySize);
        }

        public void Start()
        {
            Tell($"{Definition.Name} begins.");
            GrantBreath();
            _timer = new ECSGameTimer(Starter, Tick, 1000);
            NextPhase();
        }

        public bool IsParticipant(GamePlayer player) => _players.Contains(player) ||
            Definition.Scope != TrialScope.Solo && player.Group != null && player.Group == Leader.Group;

        /// <summary>In a solo trial only the starter and their pets count.</summary>
        public bool MayHurt(GameObject source)
        {
            if (Definition.Scope != TrialScope.Solo)
                return true;
            GameObject root = source is GameNPC { Brain: IControlledBrain controlled } ? controlled.GetPlayerOwner() : source;
            return root == Leader;
        }

        public void MobFinished(TrialMob mob) => _finished.Enqueue(mob);

        public IEnumerable<TrialMob> Mobs(string tag = null) =>
            _mobs.Where(mob => mob.IsAlive && mob.ObjectState == GameObject.eObjectState.Active && !mob.Finished && (tag == null || mob.Spec.Tag == tag));

        public void SetImmune(string tag, bool immune)
        {
            foreach (TrialMob mob in Mobs(tag))
                mob.Immune = immune;
        }

        public void Tell(string message)
        {
            foreach (GamePlayer player in _players.Concat(Leader.Group?.GetPlayersInTheGroup() ?? Enumerable.Empty<GamePlayer>()).Distinct().Where(player => player.ObjectState == GameObject.eObjectState.Active))
                player.Out.SendMessage(message, eChatType.CT_ScreenCenter, eChatLoc.CL_SystemWindow);
        }

        public TrialMob Spawn(TrialMobSpec spec)
        {
            TrialMob last = null;
            for (int i = 0; i < spec.Count; i++)
                last = SpawnOne(spec, i);
            return last;
        }

        private TrialMob SpawnOne(TrialMobSpec spec, int index)
        {
            TrialMob mob = new(this, spec, TrialScaling.Health(spec.Health, HealthScale))
            {
                Name = spec.Name,
                Model = spec.Model,
                Level = spec.Level,
                Size = spec.Size,
                Realm = eRealm.None,
                RespawnInterval = -1,
                MeleeDamageType = spec.MeleeDamage,
                DamageFactor = spec.DamageFactor * DamageScale,
                TetherRange = Definition.LeashRange,
                CurrentRegion = Starter.CurrentRegion,
            };
            TrialPoint point = spec.At ?? Around(Definition.Anchor, spec.Spread, index, spec.Count);
            mob.X = point.X;
            mob.Y = point.Y;
            mob.Z = point.Z;
            mob.Heading = point.Heading;

            if (spec.Objective)
                mob.Flags = GameNPC.eFlags.PEACE;
            else
                mob.SetOwnBrain(new StandardMobBrain { AggroLevel = 100, AggroRange = spec.AggroRange });

            mob.AddToWorld();
            mob.Health = mob.MaxHealth;
            _mobs.Add(mob);
            return mob;
        }

        private static TrialPoint Around(TrialPoint anchor, int spread, int index, int count)
        {
            double angle = 2 * Math.PI * index / Math.Max(1, count);
            return new TrialPoint(anchor.X + (int)(spread * Math.Cos(angle)), anchor.Y + (int)(spread * Math.Sin(angle)), anchor.Z, anchor.Heading);
        }

        private int Tick(ECSGameTimer timer)
        {
            try
            {
                if (State != TrialRunState.Running)
                    return 0;

                _elapsed++;
                _phaseElapsed++;

                while (_finished.TryDequeue(out TrialMob mob))
                {
                    if (mob.Spec.Required)
                        _phaseFinished++;
                    mob.Spec.OnDeath?.Invoke(this, mob);
                }

                if (_elapsed >= Definition.TimeLimitSeconds)
                {
                    End(false, "You ran out of time.");
                    return 0;
                }

                if (PartyGone())
                    return 0;

                GrantBreath();
                Pulse();
                Phase?.OnTick?.Invoke(this);
                if (Sweeping)
                    SweepPhase();

                if (State == TrialRunState.Running && PhaseComplete())
                    NextPhase();

                return State == TrialRunState.Running ? 1000 : 0;
            }
            catch (Exception e)
            {
                TrialManager.Log.Error($"Trial {Definition.Key} failed on tick", e);
                End(false, "The trial falters and fades away.");
                return 0;
            }
        }

        /// <summary>Many trials are fought on the sea floor, and a long fight must not end in drowning.</summary>
        private void GrantBreath()
        {
            foreach (GamePlayer player in _players.Where(player => !player.CanBreathUnderWater))
            {
                player.CanBreathUnderWater = true;
                _breathing.Add(player);
            }
        }

        private bool PartyGone()
        {
            bool here = _players.Any(player => player.IsAlive && player.ObjectState == GameObject.eObjectState.Active &&
                player.CurrentRegion == Starter.CurrentRegion && player.IsWithinRadius(Starter, Definition.LeashRange));
            bool bots = Definition.Scope != TrialScope.Solo && Leader.Group?.GetMembersInTheGroup()
                .Any(member => member is GameBot && member.IsAlive && member.IsWithinRadius(Starter, Definition.LeashRange)) == true;

            _abandoned = here || bots ? 0 : _abandoned + 1;
            if (_abandoned < AbandonSeconds)
                return false;
            End(false, "Your party has fallen or fled. The trial resets.");
            return true;
        }

        private void Pulse()
        {
            if (Phase == null)
                return;
            foreach (TrialPulse pulse in Phase.Pulses)
            {
                if (_phaseElapsed % Math.Max(1, pulse.IntervalSeconds) != 0)
                    continue;
                IEnumerable<GameLiving> sources = pulse.SourceTag == null ? new GameLiving[] { Starter } : Mobs(pulse.SourceTag);
                int damage = (int)(pulse.Damage * DamageScale);
                foreach (GameLiving source in sources.ToList())
                {
                    foreach (GameLiving target in Hostiles(source, pulse.Radius))
                        target.TakeDamage(source, pulse.DamageType, damage, 0);
                }
                if (!string.IsNullOrEmpty(pulse.Message))
                    Tell(pulse.Message);
            }
        }

        /// <summary>Players, bots and pets near a point. Use for a trial's own area effects.</summary>
        public IEnumerable<GameLiving> Hostiles(GameObject center, int radius)
        {
            ushort range = (ushort)Math.Min(radius, ushort.MaxValue);
            return center.GetPlayersInRadius(range).Where(player => player.IsAlive).Cast<GameLiving>()
                .Concat(center.GetNPCsInRadius(range).Where(npc => npc.IsAlive && (npc is GameBot || npc.Brain is IControlledBrain)))
                .ToList();
        }

        private void SweepPhase()
        {
            foreach (TrialMob mob in Mobs().ToList())
            {
                if (mob.Spec.Objective)
                    mob.Complete();
                else
                    mob.Die(Leader);
            }
            if (_phaseElapsed < 6 || Phase == null || PhaseComplete())
                return;
            if (Phase.SurviveSeconds <= 0)
                SweepNotes.Add($"phase {_phaseIndex + 1} did not end after clearing it");
            NextPhase();
        }

        private bool PhaseComplete()
        {
            TrialPhase phase = Phase;
            if (phase == null)
                return true;
            if (phase.Done != null)
                return phase.Done(this);
            if (phase.SurviveSeconds > 0)
                return _phaseElapsed >= phase.SurviveSeconds;
            if (phase.KillCount > 0)
                return _phaseFinished >= phase.KillCount;
            return !_mobs.Any(mob => mob.Spec.Required && !mob.Finished && mob.IsAlive && mob.ObjectState == GameObject.eObjectState.Active);
        }

        private void NextPhase()
        {
            _phaseIndex++;
            _phaseElapsed = _phaseFinished = 0;
            if (_phaseIndex >= Definition.Phases.Count)
            {
                End(true, Definition.Victory ?? $"You have completed {Definition.Name}!");
                return;
            }
            TrialPhase phase = Phase;
            if (!string.IsNullOrEmpty(phase.Announce))
                Tell(phase.Announce);
            foreach (TrialMobSpec spec in phase.Mobs)
                Spawn(spec);
            phase.OnStart?.Invoke(this);
        }

        public void End(bool success, string message)
        {
            if (State != TrialRunState.Running)
                return;
            State = success ? TrialRunState.Completed : TrialRunState.Failed;
            Tell(message);
            _timer?.Stop();
            try
            {
                Definition.OnEnd?.Invoke(this, success);
            }
            catch (Exception e)
            {
                TrialManager.Log.Error($"Trial {Definition.Key} failed as it ended", e);
            }
            foreach (TrialMob mob in _mobs.Where(mob => mob.ObjectState == GameObject.eObjectState.Active).ToList())
                mob.Delete();
            foreach (GamePlayer player in _breathing)
                player.CanBreathUnderWater = false;
            if (success)
                TrialManager.Award(this);
            TrialManager.Finished(this);
        }
    }
}
