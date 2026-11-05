using System.Linq;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS.Commands
{
    [Cmd("&artifact",
         ePrivLevel.GM,
         "Test artifacts on your character or your target",
         "/artifact status - list artifact records",
         "/artifact level <0-10> - set the level of every artifact you carry",
         "/artifact encounter <artifactId> - give encounter credit")]
    public class ArtifactCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            GamePlayer player = client.Player.TargetObject as GamePlayer ?? client.Player;

            if (args.Length < 2)
            {
                DisplaySyntax(client);
                return;
            }

            switch (args[1].ToLower())
            {
                case "status":
                {
                    foreach (OfflineArtifactProgress row in ArtifactProgress.For(player).Values)
                        DisplayMessage(client, $"{ArtifactCatalog.NameOf(row.ArtifactID)}: encounter {row.EncounterDone}, claimed {row.Claimed}, level {ArtifactLevels.LevelFor(row.Experience)}");

                    foreach (ArtifactItem item in player.Inventory.AllItems.OfType<ArtifactItem>())
                        DisplayMessage(client, $"{item.Name}: slot {item.SlotPosition}, level {item.ArtifactLevel}, xp {item.Experience}");

                    break;
                }
                case "level":
                {
                    if (args.Length < 3 || !int.TryParse(args[2], out int level))
                    {
                        DisplaySyntax(client);
                        return;
                    }

                    foreach (ArtifactItem item in player.Inventory.AllItems.OfType<ArtifactItem>())
                        item.SetExperience(player, ArtifactLevels.XpForLevel(level));

                    DisplayMessage(client, $"Set {player.Name}'s artifacts to level {level}.");
                    break;
                }
                case "encounter":
                {
                    if (args.Length < 3)
                    {
                        DisplaySyntax(client);
                        return;
                    }

                    ArtifactProgress.Update(player, args[2], row => row.EncounterDone = true);
                    DisplayMessage(client, $"{player.Name} has credit for {ArtifactCatalog.NameOf(args[2])}.");
                    break;
                }
                default:
                    DisplaySyntax(client);
                    break;
            }
        }
    }
}
