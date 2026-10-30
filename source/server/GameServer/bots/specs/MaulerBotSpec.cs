namespace DOL.GS
{
    /// <summary>One plan for the three realm Maulers (60-62): a Mauler Staff or two Fist Wraps.</summary>
    public class MaulerBotSpec : BotSpec
    {
        public MaulerBotSpec(eSpecType spec)
        {
            SpecName = "MaulerBotSpec";

            bool staff = spec switch
            {
                eSpecType.TwoHanded => true,
                eSpecType.DualWield => false,
                _ => Util.Random(1) == 0,
            };

            if (staff)
            {
                // Fist Wraps stay the one-handed fallback until a staff drops.
                SpecType = eSpecType.TwoHanded;
                Is2H = true;
                WeaponOneType = eObjectType.FistWraps;
                WeaponTwoType = eObjectType.MaulerStaff;
                Add(Specs.Mauler_Staff, 50, 1.0f);
                Add(Specs.Aura_Manipulation, 30, 0.5f);
                Add(Specs.Magnetism, 28, 0.4f);
                Add(Specs.Power_Strikes, 18, 0.2f);
            }
            else
            {
                SpecType = eSpecType.DualWield;
                WeaponOneType = eObjectType.FistWraps;
                Add(Specs.Fist_Wraps, 50, 1.0f);
                Add(Specs.Power_Strikes, 30, 0.5f);
                Add(Specs.Aura_Manipulation, 28, 0.4f);
                Add(Specs.Magnetism, 18, 0.2f);
            }
        }
    }
}
