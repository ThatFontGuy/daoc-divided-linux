using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Cleric Helping Hand line (live 1.123): a debuff on an enemy whose melee hits heal their own victim for Value.
    /// </summary>
    [SpellHandler(eSpellType.HelpingHand)]
    public class HelpingHandSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Causes the target's melee attacks to heal its target for {Spell.Value} hit points.";

        /// <summary>The heal the attacker's Helping Hand grants each melee victim: its strongest rank, or 0.</summary>
        public static int HealFor(GameLiving attacker)
        {
            int best = 0;
            if (attacker == null)
                return best;

            foreach (ECSGameSpellEffect effect in attacker.effectListComponent.GetSpellEffects(eEffect.HelpingHand))
            {
                if (effect.IsActive)
                    best = System.Math.Max(best, (int) effect.SpellHandler.Spell.Value);
            }

            return best;
        }

        /// <summary>Heals the victim of a landed melee hit by a Helping Hand on its attacker (GameLiving.OnAttackedByEnemy).</summary>
        public static void OnAttacked(GameLiving victim, AttackData ad)
        {
            if (ad == null || !ad.IsHit || !ad.IsMeleeAttack || ad.Attacker is not GameLiving attacker || !victim.IsAlive)
                return;

            int heal = HealFor(attacker);
            if (heal > 0)
                victim.ChangeHealth(attacker, eHealthChangeType.Spell, heal);
        }
    }

    /// <summary>
    /// Archery Track (live 1.121): while stealthed and standing still, raises stealth detection by Value% for its
    /// Duration; moving ends it (GamePlayer.OnPlayerMove).
    /// </summary>
    [SpellHandler(eSpellType.TrackStealth)]
    public class TrackStealthSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"While stealthed and still, your stealth detection is {Spell.Value}% greater.";

        public override bool UnstealthCasterOnStart => false;
        public override bool UnstealthCasterOnFinish => false;

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if (!Caster.IsStealthed || Caster.IsMoving)
            {
                MessageToCaster("You must be stealthed and standing still to track.", eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }

        public static int Bonus(GameLiving living)
        {
            int best = 0;
            if (living == null)
                return best;

            foreach (eEffect type in new[] { eEffect.TrackStealth, eEffect.StealthDetectionAura })
            {
                foreach (ECSGameSpellEffect effect in living.effectListComponent.GetSpellEffects(type))
                {
                    if (effect.IsActive)
                        best = System.Math.Max(best, (int) effect.SpellHandler.Spell.Value);
                }
            }

            return best;
        }

        /// <summary>Moving ends the focus.</summary>
        public static void OnMove(GameLiving living)
        {
            foreach (ECSGameSpellEffect effect in living.effectListComponent.GetSpellEffects(eEffect.TrackStealth))
                effect.End();
        }
    }

    /// <summary>
    /// A snare-totem pulse (live 1.122C): snares for its Duration, ignores root and snare immunity and grants none
    /// (TotemSnare has no immunity in EffectHelper.GetImmunityEffectFromSpell).
    /// </summary>
    [SpellHandler(eSpellType.TotemSnare)]
    public class TotemSnareSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpeedDecreaseSpellHandler(caster, spell, line)
    {
        protected override bool RespectsSnareImmunity => false;
    }

    /// <summary>
    /// Champion's Call (Call of the Champion, live 1.121): the melee damage of everyone affected becomes the spell's
    /// damage type (Energy) for its Duration (AttackComponent.AttackDamageType).
    /// </summary>
    [SpellHandler(eSpellType.MeleeDamageTypeAura)]
    public class MeleeDamageTypeAuraSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Melee damage becomes {GlobalConstants.DamageTypeToName(Spell.DamageType)}.";

        public static eDamageType? For(GameLiving living)
        {
            if (living == null)
                return null;

            foreach (ECSGameSpellEffect effect in living.effectListComponent.GetSpellEffects(eEffect.MeleeDamageTypeAura))
            {
                if (effect.IsActive)
                    return effect.SpellHandler.Spell.DamageType;
            }

            return null;
        }
    }
}
