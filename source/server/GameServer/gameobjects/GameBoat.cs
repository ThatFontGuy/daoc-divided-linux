using System;
using System.Reflection;
using DOL.AI.Brain;
using DOL.Database;
using DOL.GS.PacketHandler;
using DOL.GS.PacketHandler.Client.v168;
using DOL.Language;
using DOL.Logging;

namespace DOL.GS
{
    public class GameBoat : GameMovingObject
    {
        private static readonly Logger log = LoggerManager.Create(MethodBase.GetCurrentMethod().DeclaringType);

        private readonly record struct BoatKind(string ItemId, string DisplayName, ushort Model, short Speed, int Riders);

        private static readonly BoatKind[] BOAT_KINDS =
        [
            new("scout_boat", "scout boat", 2648, 500, 8),
            new("warship", "warship", 2647, 400, 32),
            new("galleon", "galleon", 2646, 300, 16),
            new("skiff", "skiff", 1616, 250, 8),
            new("Viking_Longship", "Viking longship", 1615, 500, 32),
            new("ps_longship", "Longship", 1595, 600, 31),
            new("stygian_ship", "Stygian ship", 1612, 500, 24),
            new("atlantean_ship", "Atlantean ship", 1613, 800, 64),
            new("British_Cog", "British Cog", 1614, 700, 33),
            new("Elvish_Caravel", "Elvish Caravel", 1657, 700, 33),
        ];

        // Shipwrights in Atlantis sold realm copies such as skiff3, and players may still hold them.
        private static BoatKind? FindKind(string itemId)
        {
            string baseId = itemId?.TrimEnd('0', '1', '2', '3', '4', '5', '6', '7', '8', '9');

            foreach (BoatKind kind in BOAT_KINDS)
            {
                if (string.Equals(kind.ItemId, baseId, StringComparison.OrdinalIgnoreCase))
                    return kind;
            }

            return null;
        }

        public static bool IsBoatItem(string itemId) => FindKind(itemId) != null;

        public static void Summon(GamePlayer player, DbInventoryItem item = null)
        {
            string language = player.Client.Account.Language;

            if (!PlayerPositionUpdateHandler.IsSwimmingState(player.StateFlags))
            {
                if (log.IsInfoEnabled)
                    log.Info($"BOAT_NOT_IN_WATER player={player.Name} state={(byte) player.StateFlags} diving={player.IsDiving}");

                player.Out.SendMessage(LanguageMgr.GetTranslation(language, "Scripts.Player.Boat.NotInWater"), eChatType.CT_Guild, eChatLoc.CL_ChatWindow);
                return;
            }

            GameBoat boat = BoatMgr.GetBoatByOwner(player.InternalID);

            if (boat == null)
            {
                item ??= FindBoatItem(player);

                if (item == null || FindKind(item.Id_nb) is not BoatKind kind)
                {
                    player.Out.SendMessage(LanguageMgr.GetTranslation(language, "Scripts.Player.Boat.NotOwnBoat"), eChatType.CT_Guild, eChatLoc.CL_ChatWindow);
                    return;
                }

                boat = new GameBoat
                {
                    BoatID = Guid.NewGuid().ToString(),
                    Name = $"{player.Name}'s {kind.DisplayName}",
                    Model = kind.Model,
                    OwnerID = player.InternalID,
                    MaxSpeedBase = kind.Speed,
                    Riders = new GamePlayer[kind.Riders]
                };

                PlaceBeside(boat, player);
                boat = BoatMgr.CreateBoat(player, boat);

                if (boat == null)
                    return;

                player.Inventory.RemoveItem(item);
                InventoryLogging.LogInventoryAction(player, "(ground)", eInventoryActionType.Other, item.Template, item.Count);
            }
            else
            {
                PlaceBeside(boat, player);
                boat.Riders = new GamePlayer[32];
            }

            if (player.Guild != null)
            {
                if (player.Guild.Emblem != 0)
                    boat.Emblem = (ushort) player.Guild.Emblem;

                boat.GuildName = player.Guild.Name;
            }

            boat.AddToWorld();
            player.MountSteed(boat, true);
            player.Out.SendMessage(LanguageMgr.GetTranslation(language, "Scripts.Player.Boat.Summoned", boat.Name), eChatType.CT_Guild, eChatLoc.CL_ChatWindow);
            BoatMgr.SaveAllBoats();
        }

        public static string ItemIdForModel(ushort model)
        {
            foreach (BoatKind kind in BOAT_KINDS)
            {
                if (kind.Model == model)
                    return kind.ItemId;
            }

            return null;
        }

        /// <summary>
        /// Turns the player's boat back into the item it was launched from. A free slot is checked first, then the
        /// saved boat goes before the item is given, so the player can never hold both.
        /// </summary>
        public static void PackUp(GamePlayer player)
        {
            string language = player.Client.Account.Language;
            GameBoat boat = BoatMgr.GetBoatByOwner(player.InternalID);

            if (boat == null)
            {
                player.Out.SendMessage(LanguageMgr.GetTranslation(language, "Scripts.Player.Boat.NotOwnBoat"), eChatType.CT_Guild, eChatLoc.CL_ChatWindow);
                return;
            }

            DbItemTemplate template = GameServer.Database.FindObjectByKey<DbItemTemplate>(ItemIdForModel(boat.Model));

            if (template == null)
            {
                if (log.IsErrorEnabled)
                    log.Error($"No item for boat model {boat.Model} (Owner: {player.Name})");

                return;
            }

            lock (player.Inventory.Lock)
            {
                if (!player.Inventory.IsSlotsFree(1, eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack))
                {
                    player.Out.SendMessage("You need a free backpack slot to pack up your boat.", eChatType.CT_Guild, eChatLoc.CL_ChatWindow);
                    return;
                }

                string name = boat.Name;
                boat.RemoveFromWorld();

                if (!BoatMgr.DeleteBoat(name))
                    return;

                player.Inventory.AddTemplate(GameInventoryItem.Create(template), 1, eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack);
                InventoryLogging.LogInventoryAction("(ground)", player, eInventoryActionType.Other, template, 1);
                player.Out.SendMessage(LanguageMgr.GetTranslation(language, "Scripts.Player.Boat.Unsummoned", name), eChatType.CT_Guild, eChatLoc.CL_ChatWindow);
            }
        }

        private static DbInventoryItem FindBoatItem(GamePlayer player)
        {
            foreach (DbInventoryItem item in player.Inventory.GetItemRange(eInventorySlot.Min_Inv, eInventorySlot.Max_Inv))
            {
                if (IsBoatItem(item.Id_nb))
                    return item;
            }

            return null;
        }

        private static void PlaceBeside(GameBoat boat, GamePlayer player)
        {
            boat.X = player.X;
            boat.Y = player.Y;
            boat.Z = player.Z;
            boat.Heading = player.Heading;
            boat.Realm = player.Realm;
            boat.CurrentRegionID = player.CurrentRegionID;
            boat.SetOwnBrain(new BlankBrain());
        }

        private byte m_boatType = 0;
        protected DbPlayerBoat m_dbBoat;
        private string m_boatID;
        private string m_boatOwner;
        private string m_boatName;
        private ushort m_boatModel;
        private short m_boatMaxSpeedBase;
        private ECSGameTimer m_removeTimer = null;

        public GameBoat() : base(new BlankBrain())
        {
            base.OwnerID = BoatOwner;
        }

        public GameBoat(byte type) : this()
        {
            m_boatType = type;
        }

        public override bool AddToWorld()
        {
            return base.AddToWorld();
        }

        /// <summary>
        /// Gets or sets the boats db
        /// </summary>
        public DbPlayerBoat DBBoat
        {
            get => m_dbBoat;
            set => m_dbBoat = value;
        }

        public string BoatID
        {
            get => m_boatID;
            set => m_boatID = value;
        }

        public override string Name
        {
            get => m_boatName;
            set => m_boatName = value;
        }

        public override ushort Model
        {
            get => m_boatModel;
            set => m_boatModel = value;
        }

        public override short MaxSpeedBase
        {
            get => m_boatMaxSpeedBase;
            set => m_boatMaxSpeedBase = value;
        }

        public string BoatOwner
        {
            get => m_boatOwner;
            set => m_boatOwner = value;
        }

        public override int MAX_PASSENGERS => m_boatType switch
        {
            0 => 8,
            1 => 8,
            2 => 16,
            3 => 32,
            4 => 32,
            5 => 31,
            6 => 24,
            7 => 64,
            8 => 33,
            _ => 2,
        };

        public override int REQUIRED_PASSENGERS => m_boatType switch
        {
            0 => 1,
            1 => 1,
            2 => 1,
            3 => 1,
            4 => 1,
            5 => 1,
            6 => 1,
            7 => 1,
            8 => 1,
            _ => 1,
        };

        public override int SLOT_OFFSET => 1;

        public override bool RiderMount(GamePlayer rider, bool forced)
        {
            if (!base.RiderMount(rider, forced))
                return false;

            if (m_removeTimer != null && m_removeTimer.IsAlive)
                m_removeTimer.Stop();

            return true;
        }

        public override bool RiderDismount(bool forced, GamePlayer player)
        {
            if (!base.RiderDismount(forced, player))
                return false;

            if (CurrentRiders.Length == 0)
            {
                if (m_removeTimer == null)
                    m_removeTimer = new ECSGameTimer(this, new ECSGameTimer.ECSTimerCallback(RemoveCallback));
                else if (m_removeTimer.IsAlive)
                    m_removeTimer.Stop();

                m_removeTimer.Start(15 * 60 * 1000);
            }

            return true;
        }

        protected int RemoveCallback(ECSGameTimer timer)
        {
            m_removeTimer.Stop();
            m_removeTimer = null;
            RemoveFromWorld();
            return 0;
        }

        public override bool Interact(GamePlayer player)
        {
            return OwnerID != string.Empty ? false : base.Interact(player);
        }

        public override void LoadFromDatabase(DataObject obj)
        {
            if (obj is not DbPlayerBoat)
                return;

            m_dbBoat = (DbPlayerBoat) obj;
            m_boatID = m_dbBoat.ObjectId;
            m_boatName = m_dbBoat.BoatName;
            m_boatMaxSpeedBase = m_dbBoat.BoatMaxSpeedBase;
            m_boatModel = m_dbBoat.BoatModel;
            m_boatOwner = m_dbBoat.BoatOwner;

            switch (m_boatModel)
            {
                case 1616: m_boatType = 0; break;
                case 2648: m_boatType = 1; break;
                case 2646: m_boatType = 2; break;
                case 2647: m_boatType = 3; break;
                case 1615: m_boatType = 4; break;
                case 1595: m_boatType = 5; break;
                case 1612: m_boatType = 6; break;
                case 1613: m_boatType = 7; break;
                case 1614: m_boatType = 8; break;
                case 1657: m_boatType = 8; break;
            }

            DBBoat = m_dbBoat;
            base.LoadFromDatabase(obj);
        }

        public override void SaveIntoDatabase()
        {
            GameServer.Database.SaveObject(DBBoat);
        }
    }
}
