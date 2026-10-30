namespace DOL.GS.Commands
{
    [CmdAttribute("&ml",
        new[] { "&masterlevel" },
        ePrivLevel.Player,
        "Show your Master Level progress or choose a Master Level path",
        "/ml",
        "/ml path <Banelord|Battlemaster|Convoker|Perfecter|Sojourner|Spymaster|Stormlord|Warlord>")]
    public class MasterLevelCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            if (IsSpammingCommand(client.Player, "ml"))
                return;

            if (args.Length >= 3 && args[1].Equals("path", System.StringComparison.OrdinalIgnoreCase))
            {
                MasterLevelRules.ChoosePath(client.Player, args[2], out string message);
                DisplayMessage(client, message);
                return;
            }

            DisplayMessage(client, MasterLevelRules.Describe(client.Player));
        }
    }
}
