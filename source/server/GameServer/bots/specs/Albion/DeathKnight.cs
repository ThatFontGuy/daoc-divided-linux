namespace DOL.GS
{
    /// <summary>The live Necromancer (class 66): a staff caster with its own servant, not the classic shade.</summary>
    public class DeathKnightBotSpec : BotSpec
    {
        public DeathKnightBotSpec(eSpecType spec)
        {
            SpecName = "DeathKnightBotSpec";
            WeaponOneType = eObjectType.Staff;
            Is2H = true;

            SpecType = spec switch
            {
                eSpecType.PainworkingDeathKnight => eSpecType.PainworkingDeathKnight,
                eSpecType.ServantDeathKnight => eSpecType.ServantDeathKnight,
                _ => eSpecType.DeathsightDeathKnight,
            };

            switch (SpecType)
            {
                case eSpecType.DeathsightDeathKnight:
                Add(Specs.Deathsight, 49, 1.0f);
                Add(Specs.Death_Servant, 22, 0.2f);
                Add(Specs.Painworking, 6, 0.0f);
                break;

                case eSpecType.PainworkingDeathKnight:
                Add(Specs.Painworking, 49, 1.0f);
                Add(Specs.Deathsight, 22, 0.2f);
                Add(Specs.Death_Servant, 6, 0.0f);
                break;

                default:
                Add(Specs.Death_Servant, 49, 1.0f);
                Add(Specs.Deathsight, 22, 0.2f);
                Add(Specs.Painworking, 6, 0.0f);
                break;
            }
        }
    }
}
