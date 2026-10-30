namespace DOL.GS
{
    public class WarlockBotSpec : BotSpec
    {
        public WarlockBotSpec(eSpecType spec)
        {
            SpecName = "WarlockBotSpec";
            WeaponOneType = eObjectType.Staff;
            Is2H = true;

            SpecType = spec switch
            {
                eSpecType.HexingWarlock => eSpecType.HexingWarlock,
                eSpecType.WitchcraftWarlock => eSpecType.WitchcraftWarlock,
                _ => eSpecType.CursingWarlock,
            };

            switch (SpecType)
            {
                case eSpecType.CursingWarlock:
                Add(Specs.Cursing, 50, 1.0f);
                Add(Specs.Witchcraft, 20, 0.1f);
                Add(Specs.Hexing, 6, 0.0f);
                break;

                case eSpecType.HexingWarlock:
                Add(Specs.Hexing, 50, 1.0f);
                Add(Specs.Cursing, 20, 0.1f);
                Add(Specs.Witchcraft, 6, 0.0f);
                break;

                default:
                Add(Specs.Witchcraft, 50, 1.0f);
                Add(Specs.Cursing, 20, 0.1f);
                Add(Specs.Hexing, 6, 0.0f);
                break;
            }
        }
    }
}
