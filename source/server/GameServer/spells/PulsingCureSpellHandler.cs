namespace DOL.GS.Spells
{
    /// <summary>
    /// Pulsing Cure Poison / Disease (live 1.81, Cleric, Druid, Healer, Friar, Warden): cures at once, then again
    /// every 3 seconds, Value more times (rank I once, rank II twice).
    /// </summary>
    public static class PulsingCure
    {
        public const int INTERVAL = 3000;

        public static void Repeat(GameLiving owner, GameLiving target, int times, System.Action<GameLiving> cure)
        {
            if (times <= 0 || owner == null || target == null)
                return;

            int left = times;
            new ECSGameTimer(owner, _ =>
            {
                if (!target.IsAlive || target.ObjectState != GameObject.eObjectState.Active)
                    return 0;

                cure(target);
                return --left > 0 ? INTERVAL : 0;
            }, INTERVAL);
        }
    }

    [SpellHandler(eSpellType.PulsingCurePoison)]
    public class PulsingCurePoisonSpellHandler(GameLiving caster, Spell spell, SpellLine line) : CurePoisonSpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"All damage over time effects (such as poisons) are removed from the target, and again {Spell.Value} more time(s), 3 seconds apart.";

        public override void OnDirectEffect(GameLiving target)
        {
            base.OnDirectEffect(target);
            PulsingCure.Repeat(Caster, target, (int) Spell.Value, base.OnDirectEffect);
        }
    }

    [SpellHandler(eSpellType.PulsingCureDisease)]
    public class PulsingCureDiseaseSpellHandler(GameLiving caster, Spell spell, SpellLine line) : CureDiseaseSpellHandler(caster, spell, line)
    {
        public override string ShortDescription =>
            $"All disease effects are removed from the target, and again {Spell.Value} more time(s), 3 seconds apart.";

        public override void OnDirectEffect(GameLiving target)
        {
            base.OnDirectEffect(target);
            PulsingCure.Repeat(Caster, target, (int) Spell.Value, base.OnDirectEffect);
        }
    }
}
