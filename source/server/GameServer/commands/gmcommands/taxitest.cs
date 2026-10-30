using System.Linq;

namespace DOL.GS.Commands
{
    /// <summary>
    /// In-game test for how the client seats riders on stable horses. Changes last until the server restarts.
    /// </summary>
    [Cmd("&taxitest",
        ePrivLevel.GM,
        "Test rider seating on a stable horse",
        "/taxitest seat <n> - resend the riding packet with seat n for every taxi (0 is the default)",
        "/taxitest model <id> - change the horse you ride to monster model id",
        "/taxitest remount - recreate your horse on your client, then seat you again",
        "/taxitest spawn <id> - model new stable horses are created with (then buy a ticket and ride)",
        "/taxitest delay <ms> - wait before seating the rider of a new stable horse (400 is the default)",
        "/taxitest flag <n> - riding packet mount flag for taxis (1 is the default)",
        "/taxitest extra <n> - riding packet trailing value for taxis (0 is the default)",
        "/taxitest reset - back to the default riding packet")]
    public class TaxiTestCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            GamePlayer player = client.Player;
            if (args.Length < 2)
            {
                DisplaySyntax(client);
                return;
            }

            GameNPC horse = player.Steed;
            switch (args[1].ToLower())
            {
                case "seat":
                    if (args.Length < 3 || !int.TryParse(args[2], out int seat) || seat < 0 || seat > 15)
                    {
                        DisplayMessage(client, "Use /taxitest seat <0-15>.");
                        return;
                    }

                    GameTaxi.SeatOverride = seat == 0 ? null : seat;
                    DisplayMessage(client, $"Taxi seat is now {seat}.");
                    break;
                case "model":
                    if (horse == null || args.Length < 3 || !ushort.TryParse(args[2], out ushort model))
                    {
                        DisplayMessage(client, "Ride a horse and use /taxitest model <id>.");
                        return;
                    }

                    horse.Model = model;
                    foreach (GamePlayer viewer in horse.GetPlayersInRadius(WorldMgr.VISIBILITY_DISTANCE))
                        ClientService.CreateObjectForPlayer(viewer, horse);
                    DisplayMessage(client, $"Horse model is now {model}.");
                    break;
                case "remount":
                    if (horse == null)
                    {
                        DisplayMessage(client, "Ride a horse first.");
                        return;
                    }

                    ClientService.CreateObjectForPlayer(player, horse);
                    break;
                case "spawn":
                    if (args.Length < 3 || !ushort.TryParse(args[2], out ushort spawn))
                    {
                        DisplayMessage(client, "Use /taxitest spawn <model id>.");
                        return;
                    }

                    GameTaxi.SpawnModelOverride = spawn;
                    DisplayMessage(client, $"New stable horses will be model {spawn}. Buy a ticket and ride to test.");
                    return;
                case "delay":
                    if (args.Length < 3 || !int.TryParse(args[2], out int delay) || delay < 100 || delay > 10000)
                    {
                        DisplayMessage(client, "Use /taxitest delay <100-10000>.");
                        return;
                    }

                    GameTaxi.MountDelay = delay;
                    DisplayMessage(client, $"Riders of new stable horses are seated after {delay} ms.");
                    return;
                case "flag":
                case "extra":
                    if (args.Length < 3 || !ushort.TryParse(args[2], out ushort value) || (args[1] == "flag" && value > 255))
                    {
                        DisplayMessage(client, $"Use /taxitest {args[1]} <number>.");
                        return;
                    }

                    if (args[1].ToLower() == "flag")
                        GameTaxi.MountFlagOverride = (byte) value;
                    else
                        GameTaxi.TrailingOverride = value;
                    DisplayMessage(client, $"Taxi riding {args[1]} is now {value}.");
                    break;
                case "reset":
                    GameTaxi.SeatOverride = null;
                    GameTaxi.MountFlagOverride = null;
                    GameTaxi.TrailingOverride = null;
                    GameTaxi.SpawnModelOverride = null;
                    GameTaxi.MountDelay = 400;
                    DisplayMessage(client, "Taxi riding packet is back to its defaults.");
                    break;
                default:
                    DisplaySyntax(client);
                    return;
            }

            // Seat every rider of this horse again, as everyone nearby sees it.
            if (horse != null)
            {
                foreach (GamePlayer rider in horse.CurrentRiders.Where(r => r != null))
                    foreach (GamePlayer viewer in horse.GetPlayersInRadius(WorldMgr.VISIBILITY_DISTANCE))
                        viewer.Out.SendRiding(rider, horse, false);
                DisplayMessage(client, $"Seat sent: {horse.RiderSlot(player)} on model {horse.Model}.");
            }
        }
    }
}
