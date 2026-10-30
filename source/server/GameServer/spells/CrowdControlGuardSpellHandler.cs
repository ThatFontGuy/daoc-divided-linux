using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Skald Sleep Guard / Stun Guard (live 1.121): wards a realm ally (not the caster) against the next mesmerize
    /// (Value 1) or magical stun (Value 2) for 5 minutes; the ward is used up by the spell it stops.
    /// </summary>
    [SpellHandler(eSpellType.CrowdControlGuard)]
    public class CrowdControlGuardSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public const int MEZ = 1;
        public const int STUN = 2;

        public override string ShortDescription =>
            $"Wards the target against the next {(Spell.Value == STUN ? "magical stun" : "mesmerize")} spell for {Spell.Duration / 1000 / 60} minutes. Cannot be cast on yourself.";

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if (selectedTarget == Caster || selectedTarget == null)
            {
                MessageToCaster("You must choose another member of your realm.", eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }

        /// <summary>
        /// Whether <paramref name="handler"/> is stopped by a ward on <paramref name="target"/>; the ward ends if so.
        /// </summary>
        public static bool Blocks(ISpellHandler handler, GameLiving target) => Blocks(handler.Spell, target);

        /// <summary>The ward kind that stops <paramref name="spell"/>: mesmerize or magical stun, else 0.</summary>
        public static int WardKind(Spell spell) => spell?.SpellType switch
        {
            eSpellType.Mesmerize => MEZ,
            eSpellType.Stun => STUN,
            _ => 0,
        };

        public static bool Blocks(Spell spell, GameLiving target)
        {
            int kind = WardKind(spell);

            if (kind == 0 || target == null)
                return false;

            foreach (ECSGameSpellEffect ward in target.effectListComponent.GetSpellEffects(eEffect.CrowdControlGuard))
            {
                if (ward.IsActive && (int) ward.SpellHandler.Spell.Value == kind)
                {
                    ward.End();
                    return true;
                }
            }

            return false;
        }
    }
}
