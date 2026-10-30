namespace DOL.GS
{
    public class BainsheeBotSpec : BotSpec
    {
        public BainsheeBotSpec(eSpecType spec)
        {
            SpecName = "BainsheeBotSpec";
            WeaponOneType = eObjectType.Staff;
            Is2H = true;

            SpecType = spec switch
            {
                eSpecType.WailBainshee => eSpecType.WailBainshee,
                eSpecType.GuardBainshee => eSpecType.GuardBainshee,
                _ => eSpecType.ShriekBainshee,
            };

            switch (SpecType)
            {
                case eSpecType.ShriekBainshee:
                Add(Specs.EtherealShriek, 50, 1.0f);
                Add(Specs.SpectralGuard, 20, 0.1f);
                Add(Specs.PhantasmalWail, 6, 0.0f);
                break;

                case eSpecType.WailBainshee:
                Add(Specs.PhantasmalWail, 50, 1.0f);
                Add(Specs.SpectralGuard, 20, 0.1f);
                Add(Specs.EtherealShriek, 6, 0.0f);
                break;

                default:
                Add(Specs.SpectralGuard, 50, 1.0f);
                Add(Specs.EtherealShriek, 20, 0.1f);
                Add(Specs.PhantasmalWail, 6, 0.0f);
                break;
            }
        }
    }
}
