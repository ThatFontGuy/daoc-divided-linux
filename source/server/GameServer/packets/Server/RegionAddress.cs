using System.Net;
using System.Net.Sockets;

namespace DOL.GS.PacketHandler
{
    /// <summary>
    /// The address a client is told to use for a region's game (UDP) connection.
    /// </summary>
    public static class RegionAddress
    {
        /// <summary>
        /// A configured region address that is not reachable from outside (any, loopback, private) is replaced per client:
        /// a client from the internet gets the server's public address (PublicIP, set in serverconfig.xml or found by
        /// UPnP), any other client (this PC, the home network, Tailscale) the address it connected to.
        /// </summary>
        public static string ForClient(GameClient client, string configured)
        {
            if (!IsPlaceholder(configured))
                return configured;

            IPAddress local = Normalize(((IPEndPoint) client.Socket.LocalEndPoint).Address);
            IPAddress publicIP = GameServer.Instance.Configuration.PublicIP;

            if (publicIP != null && client.Socket.RemoteEndPoint is IPEndPoint remote && IsInternet(Normalize(remote.Address)))
                return publicIP.ToString();

            return local.ToString();
        }

        public static bool IsPlaceholder(string ip)
        {
            if (ip is "any" or "0.0.0.0")
                return true;

            return IPAddress.TryParse(ip, out IPAddress address) && !IsInternet(address);
        }

        /// <summary>
        /// True for a public internet address; false for loopback, private, link-local and shared (CGNAT, Tailscale) ones.
        /// </summary>
        public static bool IsInternet(IPAddress address)
        {
            address = Normalize(address);

            if (address.AddressFamily != AddressFamily.InterNetwork || IPAddress.IsLoopback(address))
                return false;

            byte[] b = address.GetAddressBytes();
            return !(b[0] == 0
                || b[0] == 10
                || (b[0] == 100 && b[1] >= 64 && b[1] <= 127)
                || (b[0] == 169 && b[1] == 254)
                || (b[0] == 172 && b[1] >= 16 && b[1] <= 31)
                || (b[0] == 192 && b[1] == 168)
                || b[0] >= 224);
        }

        private static IPAddress Normalize(IPAddress address) =>
            address.IsIPv4MappedToIPv6 ? address.MapToIPv4() : address;
    }
}
