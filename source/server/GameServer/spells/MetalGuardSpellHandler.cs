using System.Collections.Generic;

namespace DOL.GS.Spells
{
    [SpellHandler(eSpellType.MetalGuard)]
    public class MetalGuardSpellHandler : ArmorAbsorptionBuff
    {
        public override List<GameLiving> SelectTargets(GameObject castTarget) => TankShoutTargets.GroupAround(Caster, Spell);

        public MetalGuardSpellHandler(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
    }
}
