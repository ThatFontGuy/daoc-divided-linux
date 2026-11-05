namespace DOL.GS.Commands
{
    [CmdAttribute("&ml",
        new[] { "&masterlevel" },
        ePrivLevel.Player,
        "Show your Master Level progress or choose a Master Level path",
        "/ml",
        "/ml path <Banelord|Battlemaster|Convoker|Perfecter|Sojourner|Spymaster|Stormlord|Warlord>",
        "/ml trials [level]")]
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

            if (args.Length >= 2 && args[1].Equals("trials", System.StringComparison.OrdinalIgnoreCase))
            {
                int level = args.Length >= 3 && int.TryParse(args[2], out int chosen) ? chosen : client.Player.MLLevel + 1;
                DisplayMessage(client, DOL.GS.Trials.TrialManager.Describe(client.Player, level));
                return;
            }

            DisplayMessage(client, MasterLevelRules.Describe(client.Player));
        }
    }
}
