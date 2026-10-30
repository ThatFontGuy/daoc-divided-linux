namespace DOL.GS.Spells
{
    /// <summary>The Champion, Minstrel and Skald siege-protection songs: the group takes Value% less siege damage (SiegeDefense).</summary>
    [SpellHandler(eSpellType.SiegeProtection)]
    public class SiegeProtectionSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"The group takes {Spell.Value}% less damage from siege weapons.";
    }
}
