using System;
using System.Net;
using System.Security.Cryptography;
using System.Text;

namespace DOL.GS.PacketHandler.Client.v168
{
    /// <summary>
    /// The password a host sets in Host for Friends. The login packet carries only an account and a password, so a new
    /// account must be made with the host's password; the friend then logs in with it like any other account. Accounts
    /// that already exist are unaffected, and so is this PC. The launcher writes the same hash (HostForFriends).
    /// </summary>
    public static class HostPassword
    {
        private const string Salt = "DividedRealmsHost:";

        public static string Hash(string password)
        {
            return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Salt + password))).ToLowerInvariant();
        }

        public static bool AllowsNewAccount(string storedHash, string password, string clientAddress)
        {
            if (string.IsNullOrEmpty(storedHash))
            {
                return true;
            }

            if (IPAddress.TryParse(clientAddress, out IPAddress address) && IPAddress.IsLoopback(address))
            {
                return true;
            }

            return !string.IsNullOrEmpty(password) && Hash(password) == storedHash;
        }
    }
}
