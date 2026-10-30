namespace DOL.GS.Spells
{
    /// <summary>Eagle Eye (live 1.127, free to archers at 45): +Value% archery damage for 30 minutes (Archery shots).</summary>
    [SpellHandler(eSpellType.ArcheryDamageBuff)]
    public class ArcheryDamageBuffSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Increases your archery damage by {Spell.Value}%.";

        public override bool UnstealthCasterOnStart => false;
        public override bool UnstealthCasterOnFinish => false;

        /// <summary>The archery damage bonus, in percent, on <paramref name="archer"/>.</summary>
        public static int Bonus(GameLiving archer)
        {
            int best = 0;
            if (archer == null)
                return best;

            foreach (ECSGameSpellEffect effect in archer.effectListComponent.GetSpellEffects(eEffect.ArcheryDamageBuff))
            {
                if (effect.IsActive)
                    best = System.Math.Max(best, (int) effect.SpellHandler.Spell.Value);
            }

            return best;
        }
    }

    /// <summary>Bola Shot (live 1.121): a drawn-bow shot that roots the target.</summary>
    [SpellHandler(eSpellType.BolaShot)]
    public class BolaShotSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpeedDecreaseSpellHandler(caster, spell, line)
    {
        public override bool UnstealthCasterOnStart => false;

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if (Caster is GamePlayer && (Caster.ActiveWeapon == null || !GlobalConstants.IsBowWeapon((eObjectType) Caster.ActiveWeapon.Object_Type)))
            {
                MessageToCaster("You must be wielding a bow to use this ability!", PacketHandler.eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }
    }
}
