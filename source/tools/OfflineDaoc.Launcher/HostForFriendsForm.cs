using System.ComponentModel;
using System.Diagnostics;
using System.Net;

namespace OfflineDaoc.Launcher;

/// <summary>
/// The host's side of playing together: open this server to friends (Tailscale and the home network, and with
/// internet mode friends' internet addresses through the router), and the firewall rules for it.
/// </summary>
internal sealed class HostForFriendsForm : Form
{
    private readonly string _runtime;
    private readonly Func<bool> _serverRunning;
    private readonly Label _state = Line(13f, FontStyle.Bold, DaocTheme.GoldLight);
    private readonly Label _address = Line(9.5f, FontStyle.Bold, DaocTheme.Text);
    private readonly Label _internetState = Line(10f, FontStyle.Bold, DaocTheme.GoldLight);
    private readonly Label _router = Line(8.5f, FontStyle.Regular, DaocTheme.Parchment);
    private readonly TextBox _friends = new()
    {
        Dock = DockStyle.Fill,
        BackColor = DaocTheme.PanelAlt,
        ForeColor = DaocTheme.Text,
        BorderStyle = BorderStyle.FixedSingle,
        Font = new Font("Georgia", 9f),
        Margin = new Padding(0, 3, 0, 0),
    };
    private readonly Label _firewall = Line(9f, FontStyle.Regular, DaocTheme.Parchment);
    private readonly Label _status = Line(8.5f, FontStyle.Regular, DaocTheme.GoldLight);
    private readonly Button _toggle = Action("TURN ON", Color.FromArgb(110, 128, 70));
    private readonly Button _internetToggle = Action("INTERNET: TURN ON", Color.FromArgb(150, 112, 52));
    private readonly Button _firewallButton = Action("ADD FIREWALL RULES", Color.FromArgb(65, 94, 145));
    private readonly Button _copy = Action("COPY ADDRESS", Color.FromArgb(92, 84, 128));
    private readonly Button _close = Action("CLOSE", DaocTheme.Iron);
    private HostForFriends.State _current = new(false, 10300, 10400, true);
    private HostForFriends.Settings _settings = new();
    private HostForFriends.RouterCheck? _routerCheck;
    private bool _rulesPresent;

    public HostForFriendsForm(string runtime, Func<bool> serverRunning)
    {
        _runtime = runtime;
        _serverRunning = serverRunning;

        Text = "Host for Friends — Divided Realms";
        ClientSize = new Size(700, 640);
        MinimumSize = new Size(660, 620);
        StartPosition = FormStartPosition.CenterParent;
        BackColor = DaocTheme.Void;
        ForeColor = DaocTheme.Text;
        Font = new Font("Georgia", 8.5f);
        AutoScaleMode = AutoScaleMode.Dpi;

        var frame = new StoneSurface { Dock = DockStyle.Fill, Padding = new Padding(14) };
        Controls.Add(frame);
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 12, BackColor = Color.Transparent, Padding = new Padding(4) };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        foreach (float height in new[] { 38f, 28f, 40f, 72f, 26f, 48f, 22f, 26f, 40f })
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 43));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 43));

        layout.Controls.Add(new Label
        {
            Text = "HOST FOR FRIENDS",
            Dock = DockStyle.Fill,
            ForeColor = DaocTheme.GoldLight,
            Font = new Font("Georgia", 18f, FontStyle.Bold),
            TextAlign = ContentAlignment.MiddleLeft,
        }, 0, 0);
        layout.Controls.Add(_state, 0, 1);
        layout.Controls.Add(_address, 0, 2);
        layout.Controls.Add(Note(
            "Turn hosting on, add the firewall rules (Windows asks for permission), then start the server. Friends open " +
            "JOIN FRIEND with your address and pick an account name and password for your server; their characters are " +
            "saved in YOUR world. With Tailscale (both install it) or in your house, that's all."), 0, 3);
        layout.Controls.Add(_internetState, 0, 4);
        layout.Controls.Add(_router, 0, 5);
        layout.Controls.Add(Note("Friends' internet addresses (they search \"what is my IP\"), separated by commas:", bold: true), 0, 6);
        layout.Controls.Add(_friends, 0, 7);
        layout.Controls.Add(_firewall, 0, 8);
        layout.Controls.Add(_status, 0, 9);

        var row1 = Buttons();
        row1.Controls.Add(_firewallButton);
        row1.Controls.Add(_internetToggle);
        row1.Controls.Add(_toggle);
        layout.Controls.Add(row1, 0, 10);
        var row2 = Buttons();
        row2.Controls.Add(_close);
        row2.Controls.Add(_copy);
        layout.Controls.Add(row2, 0, 11);
        frame.Controls.Add(layout);

        _toggle.Click += (_, _) => Toggle();
        _internetToggle.Click += (_, _) => ToggleInternet();
        _firewallButton.Click += async (_, _) => await ChangeFirewallAsync();
        _copy.Click += (_, _) => CopyAddress();
        _close.Click += (_, _) => Close();
        _friends.TextChanged += (_, _) => ShowFirewallState();
        CancelButton = _close;
        Shown += async (_, _) =>
        {
            _settings = HostForFriends.LoadSettings(_runtime);
            _friends.Text = string.Join(", ", _settings.FriendAddresses);
            await RefreshStateAsync();
        };
    }

    private async Task RefreshStateAsync()
    {
        try
        {
            _current = HostForFriends.Read(_runtime);
        }
        catch (Exception exception)
        {
            SetStatus($"Could not read serverconfig.xml: {exception.Message}", DaocTheme.Danger);
            _toggle.Enabled = _internetToggle.Enabled = _firewallButton.Enabled = false;
            return;
        }
        _state.Text = _current.Hosting ? "Hosting is ON: friends can join while your server runs." : "Hosting is OFF: only this PC can join your server.";
        _state.ForeColor = _current.Hosting ? DaocTheme.Success : DaocTheme.GoldLight;
        _toggle.Text = _current.Hosting ? "TURN OFF" : "TURN ON";

        var tailscale = HostForFriends.TailscaleAddresses();
        _address.Text = tailscale.Count > 0
            ? $"Tailscale friends join at  {string.Join("  or  ", tailscale)}   (login port {_current.LoginPort})"
            : "Tailscale is not running on this PC. Friends in your house can use this PC's home-network address, others the internet mode below.";
        _address.ForeColor = tailscale.Count > 0 ? DaocTheme.Text : DaocTheme.Muted;

        _internetToggle.Enabled = _current.Hosting;
        _internetToggle.Text = _current.Internet ? "INTERNET: TURN OFF" : "INTERNET: TURN ON";
        _internetState.Text = _current.Internet
            ? "Internet (no Tailscale) is ON: your router lets in the friends listed below."
            : "Internet (no Tailscale) is OFF.";
        _internetState.ForeColor = _current.Internet ? DaocTheme.Success : DaocTheme.GoldLight;
        _friends.Enabled = _current.Internet;
        _router.Text = _current.Internet ? "Asking your router…" : "Turn hosting on, then INTERNET to open your router (UPnP) for friends who don't use Tailscale.";
        _router.ForeColor = DaocTheme.Parchment;
        _routerCheck = null;
        UpdateCopyButton();

        _rulesPresent = await RulesPresentAsync();
        if (IsDisposed)
            return;
        ShowFirewallState();

        if (_current.Internet)
        {
            HostForFriends.State asked = _current;
            HostForFriends.RouterCheck check = await Task.Run(() => HostForFriends.CheckRouter(asked));
            if (IsDisposed)
                return;
            _routerCheck = check;
            _router.Text = check.Message;
            _router.ForeColor = check.Usable ? DaocTheme.Success : DaocTheme.Danger;
            UpdateCopyButton();
        }
    }

    private void ShowFirewallState()
    {
        bool friendsValid = HostForFriends.TryParseFriendAddresses(_friends.Text, out List<string> friends, out string error);
        List<string> wanted = _current.Internet ? friends : [];
        bool upToDate = _rulesPresent && wanted.Order().SequenceEqual(_settings.FirewallAppliedFor.Order());

        if (!friendsValid && _current.Internet)
        {
            _firewall.Text = error;
            _firewall.ForeColor = DaocTheme.Danger;
            _firewallButton.Enabled = false;
            return;
        }
        _firewallButton.Enabled = true;
        if (!_rulesPresent)
        {
            _firewall.Text = $"Firewall: no rules yet. Friends cannot connect until you add them (TCP {_current.LoginPort}, UDP {_current.UdpPort}).";
            _firewall.ForeColor = DaocTheme.Parchment;
            _firewallButton.Text = "ADD FIREWALL RULES";
        }
        else if (!upToDate)
        {
            _firewall.Text = "Firewall: the rules don't match the friends listed. Press UPDATE FIREWALL RULES.";
            _firewall.ForeColor = DaocTheme.Danger;
            _firewallButton.Text = "UPDATE FIREWALL RULES";
        }
        else
        {
            string who = wanted.Count == 0 ? "Tailscale and home network only" : $"Tailscale, home network and {string.Join(", ", wanted)}";
            _firewall.Text = $"Firewall: rules in place (TCP {_current.LoginPort}, UDP {_current.UdpPort}; {who}).";
            _firewall.ForeColor = DaocTheme.Success;
            _firewallButton.Text = "REMOVE FIREWALL RULES";
        }
        if (_current.Internet && friends.Count == 0)
        {
            _firewall.Text += " Add a friend's internet address so they can get in.";
            _firewall.ForeColor = DaocTheme.GoldLight;
        }
    }

    private void Toggle()
    {
        try
        {
            if (_current.Hosting)
                HostForFriends.Disable(_runtime);
            else
                HostForFriends.Enable(_runtime);
        }
        catch (Exception exception)
        {
            SetStatus($"Could not change serverconfig.xml: {exception.Message}", DaocTheme.Danger);
            return;
        }
        bool nowHosting = !_current.Hosting;
        SetStatus((nowHosting
            ? $"Hosting turned on. The previous settings are saved as server\\config\\{HostForFriends.BackupFileName}."
            : "Hosting turned off: the server listens on this PC only again.") + RestartNote(), DaocTheme.Success);
        _ = RefreshStateAsync();
    }

    private void ToggleInternet()
    {
        try
        {
            if (_current.Internet)
                HostForFriends.DisableInternet(_runtime);
            else
                HostForFriends.EnableInternet(_runtime);
        }
        catch (Exception exception)
        {
            SetStatus($"Could not change serverconfig.xml: {exception.Message}", DaocTheme.Danger);
            return;
        }
        SetStatus((_current.Internet
            ? "Internet mode turned off: the server no longer opens your router."
            : "Internet mode turned on: the server opens your router while it runs and closes it when it stops. " +
              "List your friends' internet addresses and update the firewall rules.") + RestartNote(), DaocTheme.Success);
        _ = RefreshStateAsync();
    }

    private string RestartNote() => _serverRunning() ? " Stop and start the server for it to take effect." : string.Empty;

    private async Task ChangeFirewallAsync()
    {
        if (!HostForFriends.TryParseFriendAddresses(_friends.Text, out List<string> friends, out string error))
        {
            SetStatus(error, DaocTheme.Danger);
            return;
        }
        List<string> wanted = _current.Internet ? friends : [];
        bool remove = _rulesPresent && wanted.Order().SequenceEqual(_settings.FirewallAppliedFor.Order());
        string script = Path.Combine(_runtime, "host-for-friends-firewall.cmd");
        try
        {
            File.WriteAllText(script, HostForFriends.FirewallScript(_runtime, _current, add: !remove, wanted));
            using Process? process = Process.Start(new ProcessStartInfo("cmd.exe")
            {
                ArgumentList = { "/c", script },
                Verb = "runas",
                UseShellExecute = true,
                WindowStyle = ProcessWindowStyle.Hidden,
            });
            if (process != null)
                await process.WaitForExitAsync();
        }
        catch (Win32Exception exception) when (exception.NativeErrorCode == 1223)
        {
            SetStatus("Windows permission was declined; the firewall was not changed.", DaocTheme.Danger);
            return;
        }
        catch (Exception exception)
        {
            SetStatus($"Could not change the firewall: {exception.Message}", DaocTheme.Danger);
            return;
        }

        bool present = await RulesPresentAsync();
        if (present == !remove)
        {
            _settings.FriendAddresses = friends;
            _settings.FirewallAppliedFor = remove ? [] : wanted;
            try
            {
                HostForFriends.SaveSettings(_runtime, _settings);
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                SetStatus($"The firewall changed, but the friend list could not be saved: {exception.Message}", DaocTheme.Danger);
            }
            SetStatus(remove ? "Firewall rules removed." : "Firewall rules saved.", DaocTheme.Success);
        }
        else
        {
            SetStatus($"The firewall did not change. You can run {script} as administrator yourself.", DaocTheme.Danger);
        }
        await RefreshStateAsync();
    }

    private async Task<bool> RulesPresentAsync()
    {
        try
        {
            foreach (string protocol in new[] { "TCP", "UDP" })
            {
                using Process? process = Process.Start(new ProcessStartInfo("netsh")
                {
                    ArgumentList = { "advfirewall", "firewall", "show", "rule", $"name={HostForFriends.FirewallRuleName(_current, protocol)}" },
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                });
                if (process == null)
                    return false;
                await process.StandardOutput.ReadToEndAsync();
                await process.WaitForExitAsync();
                if (process.ExitCode != 0)
                    return false;
            }
            return true;
        }
        catch (Exception exception) when (exception is Win32Exception or InvalidOperationException)
        {
            return false;
        }
    }

    // Internet mode with a working router: the internet address; otherwise this PC's Tailscale address.
    private IPAddress? AddressToShare()
    {
        if (_current.Internet && _routerCheck is { Usable: true, InternetAddress: { } internet })
            return internet;
        var tailscale = HostForFriends.TailscaleAddresses();
        return tailscale.Count > 0 ? tailscale[0] : null;
    }

    private void UpdateCopyButton() => _copy.Enabled = AddressToShare() != null;

    private void CopyAddress()
    {
        IPAddress? address = AddressToShare();
        if (address == null)
            return;
        Clipboard.SetText(address.ToString());
        SetStatus($"Copied {address}. Send it to your friend for JOIN FRIEND.", DaocTheme.Success);
    }

    private void SetStatus(string text, Color color)
    {
        _status.Text = text;
        _status.ForeColor = color;
    }

    private static Label Line(float size, FontStyle style, Color color) => new()
    {
        AutoSize = false,
        Dock = DockStyle.Fill,
        ForeColor = color,
        Font = new Font("Georgia", size, style),
        TextAlign = ContentAlignment.MiddleLeft,
    };

    private static Label Note(string text, bool bold = false) => new()
    {
        Text = text,
        Dock = DockStyle.Fill,
        ForeColor = DaocTheme.Parchment,
        Font = new Font("Georgia", 8.5f, bold ? FontStyle.Bold : FontStyle.Regular),
        TextAlign = ContentAlignment.MiddleLeft,
    };

    private static Button Action(string text, Color accent) => new RuneButton
    {
        Text = text,
        Width = 210,
        Height = 34,
        Accent = accent,
        Margin = new Padding(4),
    };

    private static FlowLayoutPanel Buttons() => new()
    {
        Dock = DockStyle.Fill,
        FlowDirection = FlowDirection.RightToLeft,
        WrapContents = false,
        BackColor = Color.Transparent,
    };
}
