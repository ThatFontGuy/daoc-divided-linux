using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Cleric Virtuous / Heavenly / Rapturous / Radiant Reflection (live 1.123): Value% of all damage the caster
    /// receives, melee and spell, is returned to the attacker as Spirit damage. The hit itself is not reduced.
    /// LifeDrainReturn 1 reflects melee only (Shaman Caustic Carapace: 250% of melee damage, live 1.130a).
    /// </summary>
    [SpellHandler(eSpellType.DamageReflection)]
    public class DamageReflectionSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Reflects {Spell.Value}% of all damage received back to the attacker.";

        /// <summary>The damage <paramref name="owner"/> returns for a hit of <paramref name="damage"/>: its strongest reflection's share.</summary>
        public static int Reflected(GameLiving owner, int damage)
        {
            if (owner == null || damage <= 0)
                return 0;

            return Reflected(owner, damage, true);
        }

        private static int Reflected(GameLiving owner, int damage, bool melee)
        {
            int best = 0;
            foreach (ECSGameSpellEffect effect in owner.effectListComponent.GetSpellEffects(eEffect.DamageReflection))
            {
                if (effect.IsActive && (melee || effect.SpellHandler.Spell.LifeDrainReturn != 1))
                    best = System.Math.Max(best, (int) effect.SpellHandler.Spell.Value);
            }

            return damage * best / 100;
        }

        /// <summary>Returns the reflected share of a landed hit to its attacker (GameLiving.OnAttackedByEnemy, after ablatives).</summary>
        public static void OnAttacked(GameLiving owner, AttackData ad)
        {
            if (ad == null || !ad.IsHit || ad.Attacker is not GameLiving attacker || attacker == owner || !attacker.IsAlive)
                return;

            int returned = Reflected(owner, ad.Damage + ad.CriticalDamage, ad.AttackType is not AttackData.eAttackType.Spell);
            if (returned <= 0)
                return;

            attacker.TakeDamage(owner, eDamageType.Spirit, returned, 0);
            (owner as GamePlayer)?.Out.SendMessage($"You reflect {returned} damage back to {attacker.GetName(0, false)}!", eChatType.CT_YouHit, eChatLoc.CL_SystemWindow);
            (attacker as GamePlayer)?.Out.SendMessage($"{owner.GetName(0, true)} reflects {returned} damage back at you!", eChatType.CT_Damaged, eChatLoc.CL_SystemWindow);
        }
    }
}
