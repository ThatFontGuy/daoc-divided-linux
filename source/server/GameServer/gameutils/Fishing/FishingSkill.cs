using DOL.GS.PacketHandler;

namespace DOL.GS.Fishing
{
    /// <summary>Raises a player's fishing skill, tells them like a trade skill gain does and refreshes the trade skill window.</summary>
    public static class FishingSkill
    {
        public static void Gain(GamePlayer player, FishingProgress progress, int points)
        {
            int before = progress.Skill;
            progress.AddSkill(points);
            FishingProgressStore.Save(progress);

            if (progress.Skill <= before)
            {
                return;
            }

            player.Out.SendMessage($"You gain skill in {FishingCraft.SkillName}! ({progress.Skill}).", eChatType.CT_Important, eChatLoc.CL_SystemWindow);

            if (ServerProperties.Properties.FISHING_TRADE_SKILL_ID != 0)
            {
                player.Out.SendUpdateCraftingSkills();
            }

            if (before < FishingCraft.MaxSkill && progress.Skill >= FishingCraft.MaxSkill)
            {
                player.Out.SendMessage("You are now a master angler!", eChatType.CT_Important, eChatLoc.CL_SystemWindow);
            }
        }
    }
}
