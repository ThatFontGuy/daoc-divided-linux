using System.Collections.Generic;

namespace DOL.GS.Spells
{
    [SpellHandler(eSpellType.BolsteringRoar)]
    public class BolsteringRoarSpellHandler : RemoveSpellEffectHandler
    {
        public override List<GameLiving> SelectTargets(GameObject castTarget) => TankShoutTargets.GroupAround(Caster, Spell);

        // constructor
        public BolsteringRoarSpellHandler(GameLiving caster, Spell spell, SpellLine line)
            : base(caster, spell, line)
        {
 			// RR4: now it's a list
			m_spellTypesToRemove = new List<string>();       	
            m_spellTypesToRemove.Add("Mesmerize");
            m_spellTypesToRemove.Add("SpeedDecrease");
            m_spellTypesToRemove.Add("StyleSpeedDecrease");
            m_spellTypesToRemove.Add("DamageSpeedDecrease");
            m_spellTypesToRemove.Add("HereticSpeedDecrease");
            m_spellTypesToRemove.Add("HereticDamageSpeedDecreaseLOP");
            m_spellTypesToRemove.Add("VampiirSpeedDecrease");
            m_spellTypesToRemove.Add("ValkyrieSpeedDecrease");
            m_spellTypesToRemove.Add("WarlockSpeedDecrease");
        }
    }
}
