using System.Collections.Concurrent;
using DOL.Database;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Live 1.129 barrier heals (Cleric, Druid): heals Value, then shields each healed target with a barrier that
    /// absorbs all damage up to Damage for 10 seconds (the live barrier's duration).
    /// </summary>
    [SpellHandler(eSpellType.BarrierHeal)]
    public class BarrierHealSpellHandler(GameLiving caster, Spell spell, SpellLine line) : HealSpellHandler(caster, spell, line)
    {
        public const int BARRIER_SECONDS = 10;
        private static readonly ConcurrentDictionary<int, Spell> Barriers = new();

        public override string ShortDescription =>
            $"Heals the target for {Spell.Value} and shields them from the next {Spell.Damage} damage for {BARRIER_SECONDS} seconds.";

        public override bool HealTarget(GameLiving target, double amount, bool affectedByDisease)
        {
            bool healed = base.HealTarget(target, amount, affectedByDisease);

            if (Spell.Damage > 0 && target is { IsAlive: true })
                ScriptMgr.CreateSpellHandler(Caster, Barrier(Spell), SpellLine)?.StartSpell(target);

            return healed;
        }

        /// <summary>The barrier a heal lays: all damage absorbed, up to the heal's Damage.</summary>
        public static Spell Barrier(Spell heal) => Barriers.GetOrAdd(heal.ID, _ => new Spell(new DbSpell
        {
            SpellID = heal.ID * 1000 + 1, Name = heal.Name, Type = eSpellType.BothAblativeArmor.ToString(), Target = "Realm",
            Value = heal.Damage, Damage = 100, Duration = BARRIER_SECONDS, Icon = heal.Icon, ClientEffect = heal.ClientEffect
        }, heal.Level) { InternalID = heal.InternalID });
    }
}
