namespace DOL.GS.Commands
{
    [CmdAttribute("&flight", ePrivLevel.Player, "Switch a flying mount between running and flying", "/flight - take off or land (put it in a macro for a quickbar key)")]
    public sealed class FlightCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            GamePlayer player = client?.Player;
            if (player == null || IsSpammingCommand(player, "flight", 500))
                return;

            player.ToggleMountFlight();
        }
    }
}
