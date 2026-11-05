using System;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS.PacketHandler;
using DOL.Language;

namespace DOL.GS.Commands
{
	/// <summary>
	/// command handler for /boat command
	/// </summary>
	[Cmd(
		"&boat",
		new string[] { "&boatcommand" },
		ePrivLevel.Player,
		"Boat command (use /boat for options)",
		"/boat <option>")]
	public class BoatCommandHandler : AbstractCommandHandler, ICommandHandler
	{
		/// <summary>
		/// method to handle /boat commands from a client
		/// </summary>
		/// <param name="client"></param>
		/// <param name="args"></param>
		/// <returns></returns>
		public void OnCommand(GameClient client, string[] args)
		{
			if (IsSpammingCommand(client.Player, "boat"))
				return;

			try
			{
				switch (args[1])
				{
					case "summon":
						{
							GameBoat.Summon(client.Player);
							break;
						}
					case "unsummon":
						{
							GameBoat.PackUp(client.Player);
							break;
						}
					case "board":
						{
							GameBoat playerBoat = BoatMgr.GetBoatByName(client.Player.TargetObject.Name);
							if (client.Player.TargetObject == null)
							{
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.NoBoatSelected"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
								break;
							}

							if (playerBoat.MAX_PASSENGERS > 1)
							{
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.YouBoard", playerBoat.Name), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
								client.Player.MountSteed(playerBoat, true);
							}
							else
							{
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.FullBoat"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
							}
							break;
						}
					case "follow":
						{
							GameBoat targetBoat = BoatMgr.GetBoatByName(client.Player.TargetObject.Name);

							if (client.Player.Steed.OwnerID == client.Player.InternalID)// needs to be player on own boat
							{
								if (client.Player.TargetObject == null)
								{
									client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.NoBoatSelected"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
									break;
								}

								client.Player.Steed.Follow(targetBoat, 800, 5000);
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.MoveFollow", client.Player.TargetObject.Name), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
							}
							else
							{
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.NotOwnBoat"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
							}
							break;
						}
					case "stopfollow":
						{
							if (client.Player.Steed.OwnerID == client.Player.InternalID)// needs to be player on own boat
							{
								client.Player.Steed.StopFollowing();
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.StopFollow"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
							}
							else
							{
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.NotOwnBoat"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
							}
							break;
						}
					case "invite":
						{
							break;
						}
					case "delete":
						{
							if (client.Player.TargetObject == null)
							{
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.NoBoatSelected"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
								break;
							}
							GameBoat playerBoat = BoatMgr.GetBoatByName(client.Player.TargetObject.Name);

							if (client.Player.InternalID == playerBoat.OwnerID)
								client.Player.Out.SendCustomDialog(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.DeleteConfirmation", playerBoat.Name), new CustomDialogResponse(BoatDeleteConfirmation));
							else
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.NotOwnBoat"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);

							break;
						}
					case "boot":
						{
							GameBoat playerBoat = BoatMgr.GetBoatByOwner(client.Player.InternalID);

							if (client.Player.InternalID == playerBoat.OwnerID)
							{
								if (client.Player.TargetObject == null)
								{
									// no player selected
									break;
								}

								GamePlayer target = (client.Player.TargetObject as GamePlayer);
								if (playerBoat.RiderSlot(target) != -1)
								{
									target.DismountSteed(true);
									target.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.BootedBy", client.Player.Name), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
									client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.BootedTarget", target.Name), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
								}
								else
								{
									client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.TargetNotInBoat", target.Name), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
								}
							}
							else
							{
								client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.NotOwnBoat"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
							}
							break;
						}
					default:
						{
							client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.UnknownCommand"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
							DisplayHelp(client);
						}
						break;
				}
			}
			catch (Exception)
			{
				DisplayHelp(client);
			}
		}
		public void DisplayHelp(GameClient client)
		{
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Usage"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Help.Summon"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Help.Unsummon"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Help.Follow"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Help.StopFollow"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Help.Board"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Help.Boot"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
			client.Player.Out.SendMessage(LanguageMgr.GetTranslation(client.Account.Language, "Scripts.Player.Boat.Help.Delete"), eChatType.CT_Guild, eChatLoc.CL_SystemWindow);
		}

		protected void BoatDeleteConfirmation(GamePlayer player, byte response)
		{
			if (response != 0x01) return;

			GameBoat playerBoat = BoatMgr.GetBoatByOwner(player.InternalID);

			playerBoat.RemoveFromWorld();
			BoatMgr.DeleteBoat(playerBoat.Name);
		}
	}
}
