using System.Reflection;
using DOL.Events;
using DOL.GS.PacketHandler.Client.v168;

namespace DOL.GS.Admin
{
    /// <summary>
    /// The one hook between the server and this module. The server only scans its own assembly for
    /// [GameServerStartedEvent] and friends, so the host registers its handlers explicitly.
    /// Call once before the server starts.
    /// </summary>
    public static class AdminHost
    {
        public static void Register()
        {
            LoginRequestHandler.NewAccountPrivLevelProvider = AdminAccountRoles.PrivLevelForNewAccount;
            Assembly asm = typeof(AdminHost).Assembly;
            GameEventMgr.RegisterGlobalEvents(asm, typeof(GameServerStartedEventAttribute), GameServerEvent.Started);
            GameEventMgr.RegisterGlobalEvents(asm, typeof(GameServerStoppedEventAttribute), GameServerEvent.Stopped);
        }
    }
}
