using System;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS.Trials
{
    /// <summary>All trials. Each Master Level's content lives in its own file under Content.</summary>
    public static class TrialCatalog
    {
        private static readonly Lazy<List<TrialDefinition>> Trials = new(() =>
            Ml1.Trials().Concat(Ml2.Trials()).Concat(Ml3.Trials()).Concat(Ml4.Trials()).Concat(Ml5.Trials())
                .Concat(Ml6.Trials()).Concat(Ml7.Trials()).Concat(Ml8.Trials()).Concat(Ml9.Trials()).Concat(Ml10.Trials()).ToList());

        public static IReadOnlyList<TrialDefinition> All => Trials.Value;

        public static TrialDefinition Find(string key) => All.FirstOrDefault(trial => trial.Key == key);

        /// <summary>Mistakes in a trial's data. Empty when the catalog is sound.</summary>
        public static List<string> Validate()
        {
            List<string> errors = new();
            foreach (IGrouping<string, TrialDefinition> duplicate in All.GroupBy(trial => trial.Key).Where(group => group.Count() > 1))
                errors.Add($"{duplicate.Key}: defined {duplicate.Count()} times");

            foreach (TrialDefinition trial in All)
            {
                int steps = trial.ML == 10 ? 5 : 10;
                if (trial.ML is < 1 or > 10 || trial.Step < 1 || trial.Step > steps)
                    errors.Add($"{trial.Key}: no such step");
                if (string.IsNullOrWhiteSpace(trial.Name) || string.IsNullOrWhiteSpace(trial.StarterName) || string.IsNullOrWhiteSpace(trial.Intro))
                    errors.Add($"{trial.Key}: needs a name, a starter and an intro");
                if (trial.Anchor.X == 0 || trial.Anchor.Y == 0)
                    errors.Add($"{trial.Key}: no anchor");
                if (trial.Phases.Count == 0)
                    errors.Add($"{trial.Key}: no phases");
                if (TrialManager.Required(trial).Contains(trial.Step))
                    errors.Add($"{trial.Key}: requires itself");

                foreach (TrialPhase phase in trial.Phases)
                {
                    if (phase.Done == null && phase.SurviveSeconds <= 0 && !phase.Mobs.Any(mob => mob.Required))
                        errors.Add($"{trial.Key}: a phase with nothing to do");
                    foreach (TrialMobSpec mob in phase.Mobs)
                    {
                        if (string.IsNullOrWhiteSpace(mob.Name) || mob.Model == 0 || mob.Count < 1 || mob.Health < 1)
                            errors.Add($"{trial.Key}: bad monster '{mob.Name}'");
                    }
                }
            }
            return errors;
        }
    }
}
