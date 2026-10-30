using System.Linq;
using DOL.AI.Brain;
using DOL.GS.Effects;
using DOL.GS.Keeps;
using DOL.GS.PacketHandler;
using DOL.GS.ServerProperties;
using DOL.Language;

namespace DOL.GS.Spells
{
    [SpellHandler(eSpellType.SummonAnimistFnF)]
    public class SummonAnimistFnF : SummonAnimistPet
    {
        public override string ShortDescription => Spell.ID is >= 62000 and <= 62159
            ? "Places a lightning storm at your ground target for 120 seconds. Fires ranged area lightning and a 350-radius PBAoE every four seconds. No summon recast delay; up to 16 owned lightning storms, including in one area."
            : "Summons an elemental spirit to attack the target.";

        public SummonAnimistFnF(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            return IsValidSummonLocation() && base.CheckBeginCast(selectedTarget);
        }

        public override bool CheckEndCast(GameLiving target)
        {
            return IsValidSummonLocation() && base.CheckEndCast(target);
        }

        private bool IsValidSummonLocation()
        {
            int count = 0;
            Region region = WorldMgr.GetRegion(Caster.CurrentRegion.ID);
            GamePlayer playerCaster = Caster as GamePlayer;

            if (region == null || region.GetZone(Caster.GroundTarget.X, Caster.GroundTarget.Y) == null)
            {
                if (playerCaster != null)
                    MessageToCaster(LanguageMgr.GetTranslation(playerCaster.Client, "SummonAnimistFnF.CheckBeginCast.NoGroundTarget"), eChatType.CT_SpellResisted);

                return false;
            }

            // Limit the height of FnF Shrooms if in a keep area.
            foreach (AbstractArea area in region.GetAreasOfSpot(Caster.GroundTarget))
            {
                if (area is KeepArea)
                {
                    if (Caster.GroundTarget.Z - Caster.Z > 200)
                    {
                        if (playerCaster != null)
                            MessageToCaster("Cannot summon a turret this high near a keep!", eChatType.CT_SpellResisted);

                        return false;
                    }
                }
            }

            bool stormSummon = StormforgedTurretRules.IsStormSummon(Caster, Spell);
            if (stormSummon && !StormforgedTurretRules.CanSummon(AutonomousPetSupport.OwnedFieldTurrets(Caster)
                    .Count(entry => StormforgedTravel.IsOwnedStorm(Caster, entry.Turret))))
            {
                MessageToCaster("You already control 16 lightning storms. Release a clump before summoning more.", eChatType.CT_SpellResisted);
                return false;
            }
            if (!stormSummon && Properties.TURRET_AREA_CAP_COUNT > 0)
            {
                foreach (GameNPC npc in Caster.CurrentRegion.GetNPCsInRadius(Caster.GroundTarget, (ushort) Properties.TURRET_AREA_CAP_RADIUS))
                {
                    if (npc.Brain is TurretFNFBrain && !StormforgedTurretRules.IsStorm(npc) && ++count >= Properties.TURRET_AREA_CAP_COUNT)
                    {
                        if (playerCaster != null)
                            MessageToCaster(LanguageMgr.GetTranslation(playerCaster.Client, "SummonAnimistFnF.CheckBeginCast.TurretAreaCap"), eChatType.CT_SpellResisted);

                        return false;
                    }
                }
            }

            if (!stormSummon && Properties.TURRET_PLAYER_CAP_COUNT > 0 && Caster.PetCount >= Properties.TURRET_PLAYER_CAP_COUNT)
            {
                if (playerCaster != null)
                    MessageToCaster(LanguageMgr.GetTranslation(playerCaster.Client, "SummonAnimistFnF.CheckBeginCast.TurretPlayerCap"), eChatType.CT_SpellResisted);

                return false;
            }

            return true;
        }

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            base.ApplyEffectOnTarget(target);

            if (Spell.SubSpellID > 0 && m_pet.Spells != null && SkillBase.GetSpellByID(Spell.SubSpellID) != null)
                m_pet.Spells.Add(SkillBase.GetSpellByID(Spell.SubSpellID));

            if (m_pet.Spells.Count > 0)
                (m_pet as TurretPet).TurretSpell = m_pet.Spells[0];

            (m_pet.Brain as TurretBrain).IsMainPet = false;
            Caster.UpdatePetCount(m_pet, true);
            AutonomousPetSupport.RegisterFieldTurret(Caster, m_pet as TurretPet, Spell.Duration);
        }

        protected override void SetBrainToOwner(IControlledBrain brain) { }

        public override int OnEffectExpires(GameSpellEffect effect, bool noMessages)
        {
            AutonomousPetSupport.UnregisterFieldTurret(Caster, m_pet as TurretPet);
            Caster.UpdatePetCount(m_pet, false);
            return base.OnEffectExpires(effect, noMessages);
        }

        protected override GameSummonedPet GetGamePet(INpcTemplate template)
        {
            return new TurretFnfPet(template);
        }

        protected override IControlledBrain GetPetBrain(GameLiving owner)
        {
            return Spell.ID is >= 62000 and <= 62159
                ? new StormforgedBombBrain(owner)
                : new TurretFNFBrain(owner);
        }

        public override void CastSubSpells(GameLiving target) { }
    }
}
