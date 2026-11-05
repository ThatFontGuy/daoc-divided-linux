using System.Collections.Generic;
using System.Linq;
using DOL.GS.PacketHandler;

namespace DOL.GS.Trials
{
    /// <summary>
    /// Walks a tester through every trial, running each phase's hooks and clearing its monsters. It proves
    /// the trials run and can end, not that they are fair. Results go to the server log and the tester.
    /// </summary>
    public sealed class TrialSweep
    {
        private const int SettleSeconds = 3;

        private readonly GamePlayer _player;
        private readonly Queue<TrialDefinition> _trials;
        private TrialRun _run;
        private TrialStarter _starter;
        private int _settling;
        private int _passed, _failed;

        public TrialSweep(GamePlayer player, int firstLevel)
        {
            _player = player;
            _trials = new(TrialCatalog.All.Where(trial => trial.ML >= firstLevel).OrderBy(trial => trial.ML).ThenBy(trial => trial.Step));
        }

        public void Start() => new ECSGameTimer(_player, Tick, 1000);

        private void Report(string message)
        {
            TrialManager.Log.Info($"Trial sweep: {message}");
            _player.Out.SendMessage($"Trial sweep: {message}", eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        private int Tick(ECSGameTimer timer)
        {
            if (_player.ObjectState != GameObject.eObjectState.Active)
                return 0;
            if (!_player.IsAlive)
            {
                Report($"stopped: the tester died in {_run?.Definition.Key}");
                return 0;
            }
            _player.Health = _player.MaxHealth;
            _player.StartInvulnerabilityTimer(3000, null);

            if (_run != null)
            {
                if (_run.State == TrialRunState.Running)
                    return 1000;
                bool clean = _run.State == TrialRunState.Completed && _run.SweepNotes.Count == 0;
                _passed += clean ? 1 : 0;
                _failed += clean ? 0 : 1;
                Report($"{_run.Definition.Key} {_run.State}, ML {_player.MLLevel} {string.Join("; ", _run.SweepNotes)}");
                _run = null;
                return 1000;
            }

            if (_starter != null)
            {
                if (--_settling > 0)
                    return 1000;
                _run = new TrialRun(_starter, _player) { Sweeping = true };
                _starter.Run = _run;
                _starter = null;
                _run.Start();
                return 1000;
            }

            if (!_trials.TryDequeue(out TrialDefinition next))
            {
                Report($"done, {_passed} clean, {_failed} not, final ML {_player.MLLevel}");
                return 0;
            }
            _starter = TrialManager.StarterFor(_player, next);
            if (_starter == null || _starter.Run != null)
            {
                Report($"{next.Key} has no free starter");
                _failed++;
                _starter = null;
                return 1000;
            }
            _settling = SettleSeconds;
            _player.MoveTo(_starter.CurrentRegionID, _starter.X, _starter.Y, _starter.Z, _starter.Heading);
            return 1000;
        }
    }
}
