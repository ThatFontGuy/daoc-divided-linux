using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;

namespace OfflineDaoc.Launcher;

/// <summary>
/// Host for Friends: lets friends on Tailscale, the home network or (internet mode) the internet join this game's server.
///
/// The server normally listens on 127.0.0.1 only. Hosting makes it listen on every interface (IP and UdpIP
/// 0.0.0.0) so this PC's own client keeps using 127.0.0.1 and friends reach it on the Tailscale address.
/// RegionIP stays 127.0.0.1: the server then sends each client the address that client connected to
/// (RegionAddress.ForClient in the server's packet libraries).
/// Windows Firewall rules (made by the host with administrator approval) only admit Tailscale and the local subnet.
///
/// Internet mode (no Tailscale) adds router port forwarding: the server asks the router over UPnP at start
/// (EnableUPnP) and removes the mapping when it stops. DetectRegionIP stays off; the server keeps the router's
/// internet address as PublicIP and gives it only to clients connecting from the internet. The firewall rules then
/// also admit the friends' internet addresses listed by the host, and no other internet address.
/// </summary>
public static class HostForFriends
{
    public const string Loopback = "127.0.0.1";
    public const string AllInterfaces = "0.0.0.0";
    public const string FriendRemoteAddresses = "100.64.0.0/10,LocalSubnet";
    public const string BackupFileName = "serverconfig.before-host-for-friends.xml";
    public const string SettingsFileName = "host-for-friends.json";

    public sealed record State(bool Hosting, int LoginPort, int UdpPort, bool AutoAccountCreation, bool Internet = false);

    /// <summary>The host's list of friends' internet addresses, and the list the firewall rules were last made for.</summary>
    public sealed class Settings
    {
        public List<string> FriendAddresses { get; set; } = [];
        public List<string> FirewallAppliedFor { get; set; } = [];
    }

    public static string ConfigPath(string runtime) => Path.Combine(runtime, "server", "config", "serverconfig.xml");

    // A server the launcher may start: loopback only, or Host for Friends.
    public static bool IsAllowedListenAddress(string? ip) => ip is Loopback or AllInterfaces;

    public static State Read(string runtime)
    {
        XElement server = LoadServer(ConfigPath(runtime), out _);
        return new State(
            Hosting: Value(server, "IP") == AllInterfaces,
            LoginPort: int.TryParse(Value(server, "Port"), out int port) ? port : 10300,
            UdpPort: int.TryParse(Value(server, "UdpPort"), out int udp) ? udp : 10400,
            AutoAccountCreation: !string.Equals(Value(server, "AutoAccountCreation"), "False", StringComparison.OrdinalIgnoreCase),
            Internet: Value(server, "IP") == AllInterfaces &&
                      string.Equals(Value(server, "EnableUPnP"), "True", StringComparison.OrdinalIgnoreCase));
    }

    public static void Enable(string runtime)
    {
        string path = ConfigPath(runtime);
        XElement server = LoadServer(path, out XDocument document);
        string backup = Path.Combine(Path.GetDirectoryName(path)!, BackupFileName);
        if (Value(server, "IP") != AllInterfaces)
            File.Copy(path, backup, overwrite: true);
        Set(server, "IP", AllInterfaces);
        Set(server, "UdpIP", AllInterfaces);
        Set(server, "EnableUPnP", "False");
        Set(server, "DetectRegionIP", "False");
        // Friends get their account on their first login, as the local player does.
        Set(server, "AutoAccountCreation", "True");
        Save(document, path);
    }

    public static void Disable(string runtime)
    {
        string path = ConfigPath(runtime);
        XElement server = LoadServer(path, out XDocument document);
        Set(server, "IP", Loopback);
        Set(server, "UdpIP", Loopback);
        Set(server, "EnableUPnP", "False");
        Save(document, path);
    }

    /// <summary>Internet mode: the server opens its ports on the router (UPnP) while it runs. Needs hosting on.</summary>
    public static void EnableInternet(string runtime)
    {
        string path = ConfigPath(runtime);
        XElement server = LoadServer(path, out XDocument document);
        if (Value(server, "IP") != AllInterfaces)
            throw new InvalidOperationException("Turn hosting on first.");
        Set(server, "EnableUPnP", "True");
        Set(server, "DetectRegionIP", "False");
        if (server.Element("PublicIP") == null)
            Set(server, "PublicIP", "auto");
        Save(document, path);
    }

    public static void DisableInternet(string runtime)
    {
        string path = ConfigPath(runtime);
        XElement server = LoadServer(path, out XDocument document);
        Set(server, "EnableUPnP", "False");
        Save(document, path);
    }

    public static string SettingsPath(string runtime) => Path.Combine(runtime, SettingsFileName);

    public static Settings LoadSettings(string runtime)
    {
        try
        {
            string path = SettingsPath(runtime);
            return File.Exists(path) ? JsonSerializer.Deserialize<Settings>(File.ReadAllText(path)) ?? new Settings() : new Settings();
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or JsonException)
        {
            return new Settings();
        }
    }

    public static void SaveSettings(string runtime, Settings settings) =>
        File.WriteAllText(SettingsPath(runtime), JsonSerializer.Serialize(settings, new JsonSerializerOptions { WriteIndented = true }));

    /// <summary>Friends' internet addresses: IPv4 addresses separated by commas, spaces or new lines.</summary>
    public static bool TryParseFriendAddresses(string text, out List<string> addresses, out string error)
    {
        addresses = [];
        foreach (string part in text.Split([',', ';', ' ', '\r', '\n', '\t'], StringSplitOptions.RemoveEmptyEntries))
        {
            if (!IPAddress.TryParse(part, out IPAddress? address) || address.AddressFamily != AddressFamily.InterNetwork ||
                address.ToString() != part)
            {
                error = $"\"{part}\" is not an IPv4 address such as 203.0.113.25.";
                return false;
            }
            if (!IsInternet(address))
            {
                error = $"{part} is not an internet address. Friends on Tailscale or your home network are already allowed.";
                return false;
            }
            if (!addresses.Contains(part))
                addresses.Add(part);
        }
        error = string.Empty;
        return true;
    }

    /// <summary>True for a public internet address; false for loopback, private, link-local and shared (CGNAT, Tailscale) ones.</summary>
    public static bool IsInternet(IPAddress address)
    {
        if (address.IsIPv4MappedToIPv6)
            address = address.MapToIPv4();
        if (address.AddressFamily != AddressFamily.InterNetwork || IPAddress.IsLoopback(address))
            return false;
        byte[] b = address.GetAddressBytes();
        return !(b[0] == 0 || b[0] == 10 || (b[0] == 100 && b[1] is >= 64 and <= 127) || (b[0] == 169 && b[1] == 254) ||
                 (b[0] == 172 && b[1] is >= 16 and <= 31) || (b[0] == 192 && b[1] == 168) || b[0] >= 224);
    }

    public sealed record RouterCheck(bool Usable, IPAddress? InternetAddress, string Message);

    /// <summary>Asks the router over UPnP for its internet address, as the server does at start. Blocks a few seconds.</summary>
    public static RouterCheck CheckRouter(State state)
    {
        try
        {
            var nat = new UpnpNat();
            if (!nat.Discover())
                return new RouterCheck(false, null, NoUpnp(state));
            IPAddress external = nat.GetExternalIP();
            if (!IsInternet(external))
                return new RouterCheck(false, external,
                    $"Your router's internet address is {external}: your provider shares addresses between customers (CGNAT), " +
                    "or another router sits in front of yours. Friends can't reach you this way; use Tailscale.");
            return new RouterCheck(true, external,
                $"Router OK (UPnP). Friends join at  {external}. The server opens TCP {state.LoginPort} and UDP {state.UdpPort} " +
                $"on the router while it runs, to {nat.LocalAddress}.");
        }
        catch (Exception exception) when (exception is SocketException or WebException or IOException or
                                          System.Xml.XmlException or InvalidOperationException or FormatException or NullReferenceException)
        {
            return new RouterCheck(false, null, NoUpnp(state));
        }
    }

    private static string NoUpnp(State state) =>
        "Your router did not answer UPnP (it may be off in the router's settings). Turn UPnP on, or forward " +
        $"TCP {state.LoginPort} and UDP {state.UdpPort} to this PC by hand and set PublicIP in server\\config\\serverconfig.xml " +
        "to your internet address.";

    /// <summary>This PC's Tailscale IPv4 addresses (100.64.0.0/10) on interfaces that are up.</summary>
    public static IReadOnlyList<IPAddress> TailscaleAddresses()
    {
        try
        {
            return NetworkInterface.GetAllNetworkInterfaces()
                .Where(network => network.OperationalStatus == OperationalStatus.Up)
                .SelectMany(network => network.GetIPProperties().UnicastAddresses)
                .Select(unicast => unicast.Address)
                .Where(IsTailscale)
                .Distinct()
                .ToList();
        }
        catch (NetworkInformationException)
        {
            return [];
        }
    }

    public static bool IsTailscale(IPAddress address)
    {
        if (address.AddressFamily != AddressFamily.InterNetwork)
            return false;
        byte[] b = address.GetAddressBytes();
        return b[0] == 100 && b[1] is >= 64 and <= 127;
    }

    public static string FirewallRuleName(State state, string protocol) =>
        $"Divided Realms friends {protocol} {(protocol == "TCP" ? state.LoginPort : state.UdpPort)}";

    /// <summary>
    /// The netsh lines that admit friends. Rules are tied to this install's CoreServer.exe, so Windows does not
    /// show its own (unrestricted) "allow access" prompt when the server first listens on the network.
    /// </summary>
    public static string FirewallScript(string runtime, State state, bool add, IReadOnlyCollection<string>? internetFriends = null)
    {
        string remote = FriendRemoteAddresses + string.Concat((internetFriends ?? []).Select(address => "," + address));
        string program = Path.Combine(runtime, "server", "CoreServer.exe");
        var script = new StringBuilder();
        script.AppendLine("@echo off");
        script.AppendLine(add
            ? "rem Divided Realms: let friends on Tailscale or this home network reach the game server."
            : "rem Divided Realms: remove the Host for Friends firewall rules.");
        foreach (var (protocol, port) in new[] { ("TCP", state.LoginPort), ("UDP", state.UdpPort) })
        {
            string name = FirewallRuleName(state, protocol);
            script.AppendLine($"netsh advfirewall firewall delete rule name=\"{name}\" >nul 2>&1");
            if (add)
                script.AppendLine($"netsh advfirewall firewall add rule name=\"{name}\" dir=in action=allow protocol={protocol} " +
                                  $"localport={port} remoteip={remote} program=\"{program}\" profile=any");
        }
        return script.ToString();
    }

    private static XElement LoadServer(string path, out XDocument document)
    {
        document = XDocument.Load(path, LoadOptions.PreserveWhitespace);
        return document.Root?.Element("Server") ?? throw new InvalidDataException("serverconfig.xml has no <Server> section.");
    }

    private static string? Value(XElement server, string name) => server.Element(name)?.Value.Trim();

    private static void Set(XElement server, string name, string value)
    {
        XElement? element = server.Element(name);
        if (element != null)
        {
            element.Value = value;
            return;
        }
        // A new setting goes on its own line after the last one, with the same indentation.
        XElement? last = server.Elements().LastOrDefault();
        if (last?.PreviousNode is XText { Value: var indent } && string.IsNullOrWhiteSpace(indent))
            last.AddAfterSelf(new XText(indent), new XElement(name, value));
        else
            server.Add(new XElement(name, value));
    }

    private static void Save(XDocument document, string path)
    {
        string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            document.Save(temporary, SaveOptions.DisableFormatting);
            File.Move(temporary, path, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporary))
                File.Delete(temporary);
        }
    }
}
