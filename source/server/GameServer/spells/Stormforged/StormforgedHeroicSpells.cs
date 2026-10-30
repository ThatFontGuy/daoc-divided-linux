namespace DOL.GS.Spells
{
    [SpellHandler(eSpellType.StormforgedAvatar)]
    public class StormforgedAvatar : StormforgedMaintainedSpell
    {
        public StormforgedAvatar(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override bool UnstealthCasterOnStart => true;
        public override bool UnstealthCasterOnFinish => true;
        public override string ShortDescription => StormSovereignAbilities.Owns(Spell.ID) ? Spell.Description : "Become a Frost Giant avatar for 60 seconds: double lightning damage, custom spells cast in at most 0.25 seconds, 15% health/power/endurance regeneration and 350-radius lightning every two seconds. Three-minute reuse timer.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new StormforgedAvatarEffect(i));
    }

    [SpellHandler(eSpellType.StormforgedSecondThunder)]
    public class StormforgedSecondThunder : StormforgedMaintainedSpell
    {
        public StormforgedSecondThunder(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => "Until cancelled: a fatal damage hit instead restores full health, power and endurance and unleashes lightning within 500 units. Triggers once every two minutes; recasting does not reset the cooldown.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new StormforgedSecondThunderEffect(i));
    }

    [SpellHandler(eSpellType.StormforgedStormguard)]
    public class StormforgedStormguard : StormforgedMaintainedSpell
    {
        public StormforgedStormguard(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => "Until cancelled: blocking a melee attack blasts the attacker and enemies within 350 units with lightning. Each damaging hit restores 50% as health and 15% as power and endurance.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams) =>
            ECSGameEffectFactory.Create(initParams, static (in i) => new StormforgedStormguardEffect(i));
    }
}
