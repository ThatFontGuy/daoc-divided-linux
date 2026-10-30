namespace DOL.GS
{
    public class ValkyrieBotSpec : BotSpec
    {
        public ValkyrieBotSpec(eSpecType spec)
        {
            SpecName = "ValkyrieBotSpec";
            WeaponOneType = eObjectType.Sword;

            bool spear = spec switch
            {
                eSpecType.TwoHanded => true,
                eSpecType.OneHandAndShield => false,
                _ => Util.Random(1) == 0,
            };

            if (spear)
            {
                SpecType = eSpecType.TwoHanded;
                Is2H = true;
                WeaponTwoType = eObjectType.Spear;
                Add(Specs.Spear, 44, 1.0f);
                Add(Specs.OdinsWill, 44, 0.9f);
                Add(Specs.Mending, 28, 0.3f);
                Add(Specs.Parry, 18, 0.1f);
            }
            else
            {
                SpecType = eSpecType.OneHandAndShield;
                Add(Specs.Sword, 39, 0.8f);
                Add(Specs.OdinsWill, 44, 1.0f);
                Add(Specs.Shields, 35, 0.5f);
                Add(Specs.Mending, 20, 0.2f);
                Add(Specs.Parry, 6, 0.0f);
            }
        }
    }
}
