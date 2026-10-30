using System;
using DOL.GS.ServerProperties;

namespace DOL.GS.Commands
{
    [CmdAttribute("&bottester",
        ePrivLevel.Player,
        "Bot tester log: write the report now and show the top findings",
        "/bottester",
        "/bottester verbose <on|off>",
        "/bottester reset")]
    public class BotTesterCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            if (IsSpammingCommand(client.Player, "bottester"))
                return;

            if (!BotTesterLog.Enabled)
            {
                DisplayMessage(client, "The bot tester log is off (server property bot_tester / bot_tester_log).");
                return;
            }

            if (args.Length >= 3 && args[1].Equals("verbose", StringComparison.OrdinalIgnoreCase))
            {
                // Until the next restart; the saved server property stays as it is.
                BotTesterProperties.VERBOSE = args[2].Equals("on", StringComparison.OrdinalIgnoreCase);
                DisplayMessage(client, $"Bot tester verbose logging is {(BotTesterProperties.VERBOSE ? "on" : "off")} until the server restarts.");
                return;
            }

            if (args.Length >= 2 && args[1].Equals("reset", StringComparison.OrdinalIgnoreCase))
            {
                BotTesterLog.WriteReport();
                BotTesterLog.Reset();
                DisplayMessage(client, "Bot tester statistics cleared; the previous report was written first.");
                return;
            }

            BotTesterLog.WriteReport();
            DisplayMessage(client, $"Bot tester: {BotTesterLog.Totals()}.");
            foreach (string line in BotTesterLog.TopFindings(8))
                DisplayMessage(client, line);
            DisplayMessage(client, $"Full report: {BotTesterLog.Folder}\\REPORT.txt");
        }
    }
}
