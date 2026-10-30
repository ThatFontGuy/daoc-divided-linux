namespace DOL.GS
{
    /// <summary>A melee list caster like the Valewalker, but with a one-handed piercing weapon and no shield.</summary>
    public class VampiirBotSpec : BotSpec
    {
        public VampiirBotSpec()
        {
            SpecName = "VampiirBotSpec";
            WeaponOneType = eObjectType.Piercing;
            SpecType = eSpecType.OneHanded;

            Add(Specs.Piercing, 45, 0.9f);
            Add(Specs.VampiiricEmbrace, 40, 1.0f);
            Add(Specs.ShadowMastery, 30, 0.5f);
            Add(Specs.Dementia, 20, 0.2f);
        }
    }
}
