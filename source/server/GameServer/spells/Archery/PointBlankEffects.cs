namespace DOL.GS.Spells
{
    /// <summary>
    /// What a live Point Blank Shot (1.121) fires on the archer. The buff is the shot's SubSpellID. A Hunter's buff carries a
    /// bladeturn as its own SubSpellID, cast again each time it lapses until the buff's duration is over.
    /// </summary>
    public static class PointBlankEffects
    {
        public static void Start(GameLiving archer, Spell buff)
        {
            Cast(archer, buff);

            if (buff.SubSpellID == 0 || SkillBase.GetSpellByID(buff.SubSpellID) is not Spell bladeturn)
                return;

            int pulses = bladeturn.Duration > 0 ? buff.Duration / bladeturn.Duration : 0;
            Cast(archer, bladeturn);

            if (pulses < 2)
                return;

            new ECSGameTimer(archer, timer =>
            {
                if (--pulses <= 0 || !archer.IsAlive)
                    return 0;

                Cast(archer, bladeturn);
                return bladeturn.Duration;
            }, bladeturn.Duration);
        }

        private static void Cast(GameLiving archer, Spell spell)
        {
            ScriptMgr.CreateSpellHandler(archer, spell, SkillBase.GetSpellLine(GlobalSpellsLines.Item_Effects))?.StartSpell(archer);
        }
    }
}
