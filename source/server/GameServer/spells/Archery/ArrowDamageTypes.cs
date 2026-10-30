using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Blunt / Slashing / Thrusting Arrows (live archery): an instant switch of the archer's shot damage type to the
    /// spell's damage type, kept until another switch. The Archery shots read it (Archery.DetermineSpellDamageType).
    /// </summary>
    [SpellHandler(eSpellType.ArrowDamageTypes)]
    public class ArrowDamageTypes : SpellHandler
    {
        public const string PROPERTY = "ARCHERY_DAMAGE_TYPE";

        public override string ShortDescription => $"Your archery shots deal {GlobalConstants.DamageTypeToName(Spell.DamageType)} damage.";

        public override bool UnstealthCasterOnFinish
        {
            get { return false; }
        }

        public override bool UnstealthCasterOnStart
        {
            get { return false; }
        }

        public override bool StartSpell(GameLiving target)
        {
            Caster.TempProperties.SetProperty(PROPERTY, (int) Spell.DamageType);
            MessageToCaster($"Your arrows now deal {GlobalConstants.DamageTypeToName(Spell.DamageType)} damage.", eChatType.CT_Spell);
            return true;
        }

        /// <summary>The archer's chosen shot damage type: Slash until a switch is used.</summary>
        public static eDamageType For(GameLiving archer) =>
            (eDamageType) (archer?.TempProperties.GetProperty(PROPERTY, (int) eDamageType.Slash) ?? (int) eDamageType.Slash);

        public ArrowDamageTypes(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
    }
}
