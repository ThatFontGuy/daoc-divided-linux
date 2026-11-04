using System.Linq;
using DOL.GS.Trials;

namespace DOL.GS.Commands
{
    [CmdAttribute("&mltrial",
        ePrivLevel.GM,
        "Test Master Level trials",
        "/mltrial list [ml] - List trials",
        "/mltrial goto <key> - Go to a trial's starter in your realm's copy",
        "/mltrial start <key> - Start it at once, ignoring requirements and resets",
        "/mltrial win - Finish the nearest run",
        "/mltrial fail - Fail the nearest run",
        "/mltrial sweep [ml] - Run every trial from a Master Level on, clearing each phase, and log what breaks")]
    public class MasterLevelTrialCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            if (args.Length < 2)
            {
                DisplaySyntax(client);
                return;
            }

            GamePlayer player = client.Player;
            switch (args[1].ToLowerInvariant())
            {
                case "list":
                    int ml = args.Length > 2 && int.TryParse(args[2], out int chosen) ? chosen : player.MLLevel + 1;
                    DisplayMessage(client, TrialManager.Describe(player, ml));
                    return;
                case "goto" when args.Length > 2:
                    if (TrialCatalog.Find(args[2]) is { } goal && TrialManager.StarterFor(player, goal) is TrialStarter destination)
                        player.MoveTo(destination.CurrentRegionID, destination.X, destination.Y, destination.Z, destination.Heading);
                    else
                        DisplayMessage(client, "No starter for that trial.");
                    return;
                case "start" when args.Length > 2:
                    if (TrialCatalog.Find(args[2]) is not { } trial || TrialManager.StarterFor(player, trial) is not TrialStarter starter || starter.Run != null)
                    {
                        DisplayMessage(client, "No free starter for that trial.");
                        return;
                    }
                    starter.Run = new TrialRun(starter, player);
                    starter.Run.Start();
                    return;
                case "sweep":
                    new TrialSweep(player, args.Length > 2 && int.TryParse(args[2], out int first) ? first : player.MLLevel + 1).Start();
                    return;
                case "win":
                case "fail":
                    TrialStarter nearest = TrialManager.AllStarters.Where(s => s.Run != null && s.CurrentRegionID == player.CurrentRegionID)
                        .OrderBy(s => s.GetDistanceTo(player)).FirstOrDefault();
                    if (nearest == null)
                        DisplayMessage(client, "No run in this region.");
                    else
                        nearest.Run.End(args[1].ToLowerInvariant() == "win", "A greater power ends the trial.");
                    return;
                default:
                    DisplaySyntax(client);
                    return;
            }
        }
    }
}
