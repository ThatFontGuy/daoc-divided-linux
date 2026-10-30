using DOL.GS.PacketHandler;
using DOL.GS.ServerRules;

namespace DOL.GS.Commands
{
    [CmdAttribute("&coop", ePrivLevel.Player, "Show co-op and guild warfare rules for your location", "/coop")]
    public class CoopRulesCommand : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            if (client?.Player == null) return;
            var player = client.Player;
            if (!HybridCoopRules.Enabled)
            {
                player.Out.SendMessage("Hybrid co-op mode is not enabled on this server.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            string location = HybridCoopRules.IsWarLocation(player)
                ? "Realm war area: other realms are enemies, as normal. Your group stays friendly. Safe areas and portal keeps remain protected."
                : "Co-op area: every realm is friendly, and players and their pets cannot attack one another.";
            player.Out.SendMessage(location, eChatType.CT_System, eChatLoc.CL_SystemWindow);
            player.Out.SendMessage("Outside the frontiers, Darkness Falls and the battlegrounds you can group, guild, trade and talk with any realm, and the capital teleporters reach every capital. Darkness Falls is open to every realm.",
                eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }
    }
}
