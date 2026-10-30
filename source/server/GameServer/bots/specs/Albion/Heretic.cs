namespace DOL.GS
{
    public class HereticBotSpec : BotSpec
    {
        public HereticBotSpec(eSpecType spec)
        {
            SpecName = "HereticBotSpec";
            WeaponOneType = Util.Random(1) == 0 ? eObjectType.Flexible : eObjectType.CrushingWeapon;

            bool enhancement = spec != eSpecType.RejuvHeretic;
            SpecType = enhancement ? eSpecType.EnhanceHeretic : eSpecType.RejuvHeretic;

            if (enhancement)
            {
                Add(Specs.Enhancement, 50, 1.0f);
                Add(Specs.Rejuvenation, 28, 0.4f);
                Add(ObjToSpec(WeaponOneType), 30, 0.5f);
            }
            else
            {
                Add(Specs.Rejuvenation, 50, 1.0f);
                Add(Specs.Enhancement, 30, 0.5f);
                Add(ObjToSpec(WeaponOneType), 25, 0.4f);
            }
        }
    }
}
