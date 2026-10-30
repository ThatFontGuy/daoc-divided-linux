using DOL.GS;

namespace DOL.AI.Brain
{
    /// <summary>Private field storms retain native FnF ranged attacks and add an independent instant pulse.</summary>
    public class StormforgedBombBrain : TurretFNFBrain
    {
        public StormforgedBombBrain(GameLiving owner) : base(owner) { }

        protected virtual Spell StormPulse => Body is TurretPet { TurretSpell: { } ranged }
            ? SkillBase.GetSpellByID(ranged.ID + 4) : null;

        public override void Think()
        {
            base.Think();
            TryCastStormPulse();
        }

        public bool TryCastStormPulse()
        {
            if (Body == null || !Body.IsAlive || AggressionState == eAggressionState.Passive)
                return false;
            Spell pulse = StormPulse;
            if (pulse == null || !pulse.IsPBAoE || !pulse.IsInstantCast || Body.GetSkillDisabledDuration(pulse) != 0)
                return false;
            return Body.CastSpell(pulse, m_mobSpellLine);
        }
    }
}
