using System;
using System.Linq;
using DOL.Database;
using DOL.GS.Fishing;
using DOL.GS.PacketHandler;

namespace DOL.GS.Commands
{
    [CmdAttribute(
        "&fish",
        ePrivLevel.Player,
        "Relax and fish. Face open water with a fishing pole and type /fish.",
        "'/fish' - Fishes and casts again after each catch until you move or type /fish stop.",
        "'/fish active' - Like /fish, but you reel in each bite yourself: type /fish within 4 seconds.",
        "'/fish stop' - Reels in your line and stops fishing.",
        "'/fish stats' - Shows your fishing skill, pole, casts, catches and best catch.",
        "'/fish pole' - Gives you a fishing pole if you don't have one.",
        "'/fish craft' - Lists the poles and camp kits you can make; '/fish craft <number>' makes one.",
        "'/fish camp' - Shows how long your camp has left; '/fish camp break' packs it up. Use a camp kit from your backpack to make camp.",
        "'/fish cook' - Cooks up to 10 raw fish into food beside a burning campfire. Use the food from your backpack for 20 minutes of faster regeneration.",
        "'/fish spots' - Lists the fishing spots you can travel to.",
        "'/fish go <number>' - Travels to a fishing spot in your realm from the /fish spots list.",
        "'/fish mark <name>' - Saves the shore you stand on, facing open water, as a new fishing spot.",
        "'/fish unmark <number>' - Removes a fishing spot you marked.")]
    public class FishCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            GamePlayer player = client.Player;

            if (player == null)
            {
                return;
            }

            // A bare /fish during an active-mode bite must never be swallowed by the spam guard.
            if (args.Length < 2 && FishingManager.TryReelIn(player))
            {
                return;
            }

            if (IsSpammingCommand(player, "fish"))
            {
                return;
            }

            string sub = args.Length >= 2 ? args[1].ToLowerInvariant() : string.Empty;

            switch (sub)
            {
                case "":
                {
                    FishingManager.TryStart(player, false);

                    break;
                }
                case "active":
                {
                    FishingManager.TryStart(player, true);

                    break;
                }
                case "stop":
                {
                    if (!FishingManager.IsFishing(player))
                    {
                        player.Out.SendMessage("You aren't fishing.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                        break;
                    }

                    FishingManager.Stop(player, "You reel in your line and stop fishing.");

                    break;
                }
                case "stats":
                {
                    FishingProgress progress = FishingProgressStore.Load(player);
                    string best = "none yet";

                    if (!string.IsNullOrEmpty(progress.BestCatchName))
                    {
                        best = $"{progress.BestCatchName} ({progress.BestWeightTenths / 10}.{progress.BestWeightTenths % 10} lbs)";
                    }

                    FishingPoleTier pole = FishingManager.GetPole(player);
                    string poleText = pole == null ? "none (type /fish pole)" : $"{pole.Name} (+{pole.Bonus}, teaches up to {pole.SkillCap})";

                    player.Out.SendMessage($"Fishing skill: {progress.Skill} / {FishingCraft.MaxSkill}", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                    player.Out.SendMessage($"Pole: {poleText}", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                    player.Out.SendMessage($"Casts: {progress.Casts}   Catches: {progress.Catches}", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                    player.Out.SendMessage($"Best catch: {best}", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                    break;
                }
                case "pole":
                {
                    // The starter pole is free; better ones are made with /fish craft.
                    if (FishingManager.HasFishingPole(player))
                    {
                        player.Out.SendMessage("You already have a fishing pole.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                        break;
                    }

                    DbItemTemplate template = GameServer.Database.FindObjectByKey<DbItemTemplate>(FishingCatalog.PoleTemplateId);

                    if (template == null)
                    {
                        player.Out.SendMessage("Fishing poles aren't available right now.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                        break;
                    }

                    DbInventoryItem pole = GameInventoryItem.Create(template);

                    if (!player.Inventory.AddItem(eInventorySlot.FirstEmptyBackpack, pole))
                    {
                        player.Out.SendMessage("You need a free backpack slot for the fishing pole.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                        break;
                    }

                    InventoryLogging.LogInventoryAction("(fishing)", player, eInventoryActionType.Other, pole.Template, pole.Count);
                    player.Out.SendMessage("You receive a fishing pole. Face open water and type /fish to cast.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                    break;
                }
                case "craft":
                {
                    if (args.Length >= 3)
                    {
                        FishingWorkbench.TryCraft(player, args[2]);
                    }
                    else
                    {
                        FishingWorkbench.ShowRecipes(player);
                    }

                    break;
                }
                case "setskill":
                {
                    // Testing aid for GMs and admins: sets their own fishing skill.
                    if (client.Account.PrivLevel < (uint)ePrivLevel.GM)
                    {
                        DisplaySyntax(client);

                        break;
                    }

                    if (args.Length < 3 || !int.TryParse(args[2], out int skill))
                    {
                        player.Out.SendMessage($"Usage: /fish setskill <0-{FishingCraft.MaxSkill}>", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                        break;
                    }

                    FishingProgress progress = FishingProgressStore.Load(player);
                    progress.Skill = Math.Clamp(skill, 0, FishingCraft.MaxSkill);
                    FishingProgressStore.Save(progress);
                    player.Out.SendMessage($"Your fishing skill is now {progress.Skill}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                    break;
                }
                case "preview":
                {
                    // Testing aid for GMs: shows an objects.csv model on the ground in front of them for a while.
                    if (client.Account.PrivLevel < (uint)ePrivLevel.GM)
                    {
                        DisplaySyntax(client);

                        break;
                    }

                    if (args.Length < 3 || !ushort.TryParse(args[2], out ushort model))
                    {
                        player.Out.SendMessage("Usage: /fish preview <objects.csv model> [seconds]", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                        break;
                    }

                    int seconds = args.Length >= 4 && int.TryParse(args[3], out int s) ? Math.Clamp(s, 5, 600) : 60;
                    Point2D spot = player.GetPointFromHeading(player.Heading, 250);
                    GameStaticItem preview = new()
                    {
                        CurrentRegion = player.CurrentRegion,
                        X = spot.X,
                        Y = spot.Y,
                        Z = player.Z,
                        Heading = player.Heading,
                        Realm = player.Realm,
                        Model = model,
                        Name = $"model {model}"
                    };

                    if (!preview.AddToWorld())
                    {
                        player.Out.SendMessage($"Model {model} could not be placed here.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                        break;
                    }

                    new ECSGameTimer(preview, _ =>
                    {
                        preview.Delete();

                        return 0;
                    }, seconds * 1000);
                    player.Out.SendMessage($"Showing model {model} 250 units ahead for {seconds} seconds.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                    break;
                }
                case "cook":
                {
                    FishingCooking.TryCook(player);

                    break;
                }
                case "camp":
                {
                    if (args.Length >= 3 && args[2].ToLowerInvariant() == "break")
                    {
                        FishingCamp.BreakCamp(player, "You put out your campfire and pack up.");
                    }
                    else
                    {
                        FishingCamp.ShowStatus(player);
                    }

                    break;
                }
                case "spots":
                {
                    FishingSpots.ShowList(player);

                    break;
                }
                case "go":
                {
                    FishingSpots.TryTravel(player, args.Length >= 3 ? args[2] : string.Empty);

                    break;
                }
                case "mark":
                {
                    FishingSpots.TryMark(player, string.Join(' ', args.Skip(2)));

                    break;
                }
                case "unmark":
                {
                    FishingSpots.TryUnmark(player, args.Length >= 3 ? args[2] : string.Empty);

                    break;
                }
                default:
                {
                    DisplaySyntax(client);

                    break;
                }
            }
        }
    }
}
