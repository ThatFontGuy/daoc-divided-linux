using System.Diagnostics;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;

namespace OfflineDaoc.ModernClientLauncher;

internal static class Program
{
    internal static readonly string Workspace = AppContext.BaseDirectory;
    internal static readonly string TestRoot = Path.Combine(Workspace, "Source", "artifacts", "modern-client-test");
    internal static readonly string ServerRoot = Path.Combine(TestRoot, "runtime", "server");
    internal static string ClientRoot => ProfilePath("ClientDirectory");

    private static JsonElement ReadProfile() => JsonSerializer.Deserialize<JsonElement>(
        File.ReadAllText(Path.Combine(TestRoot, "runtime", "modern-client.json")));

    private static string ProfilePath(string key) => Path.GetFullPath(
        ReadProfile().GetProperty(key).GetString()!, Path.Combine(TestRoot, "runtime"));

    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Contains("--verify"))
        {
            try
            {
                ValidateConfiguration();
                ValidateClient();
                File.WriteAllText(Path.Combine(TestRoot, "launcher-verification.json"), JsonSerializer.Serialize(new
                {
                    Passed = true, TcpPort = 10330, ClientVersion = "1.130 hash verified",
                    ServerStarted = false, ClientLaunched = false, Timestamp = DateTimeOffset.UtcNow
                }));
            }
            catch (Exception e)
            {
                Environment.ExitCode = 1;
                File.WriteAllText(Path.Combine(Workspace, "modern-launcher-verification-error.txt"), e.Message);
            }
            return;
        }
        string fullLauncher = Path.Combine(TestRoot, "runtime", "OfflineDAoC.exe");
        if (File.Exists(fullLauncher))
        {
            Process.Start(new ProcessStartInfo(fullLauncher)
            {
                WorkingDirectory = Path.GetDirectoryName(fullLauncher)!, UseShellExecute = true
            });
            return;
        }
        ApplicationConfiguration.Initialize();
        Application.Run(new LauncherForm());
    }

    internal static void ValidateConfiguration()
    {
        string database = Path.GetFullPath(Path.Combine(TestRoot, "runtime", "data", "opendaoc.sqlite3.db"));
        var server = XDocument.Load(Path.Combine(ServerRoot, "config", "serverconfig.xml")).Root?.Element("Server")
            ?? throw new InvalidOperationException("Test server configuration is missing.");
        string Value(string key) => server.Element(key)?.Value ?? "";
        // Parse the value, not a substring: a path sharing the prefix is not our test database.
        var connection = new System.Data.Common.DbConnectionStringBuilder { ConnectionString = Value("DBConnectionString") };
        string configuredDatabase = connection.TryGetValue("Data Source", out object? value) ? Convert.ToString(value) ?? "" : "";
        // 0.0.0.0: the main launcher's Host for Friends; the test client still connects on loopback.
        if (Value("Port") != "10330" || Value("IP") is not ("127.0.0.1" or "0.0.0.0") || Value("DBType") != "SQLITE" ||
            !string.Equals(Path.GetFullPath(configuredDatabase), database, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Configuration does not point to the isolated test server/database.");
        if (!File.Exists(database) || !File.Exists(Path.Combine(ServerRoot, "CoreServer.exe")))
            throw new FileNotFoundException("The prepared test server or database is missing.");
    }

    internal static void ValidateClient()
    {
        var profile = ReadProfile();
        CheckHash(Path.Combine(ClientRoot, "game.dll"), profile.GetProperty("GameSha256").GetString()!);
        CheckHash(ProfilePath("ConnectorPath"), profile.GetProperty("ConnectorSha256").GetString()!);
    }

    private static void CheckHash(string path, string expected)
    {
        using var stream = File.OpenRead(path);
        if (!Convert.ToHexString(SHA256.HashData(stream)).Equals(expected, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException($"Unrecognized client/helper build: {Path.GetFileName(path)}. No files were patched.");
    }

    internal static bool PortListening() => IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners()
        .Any(x => x.Port == 10330 && (x.Address.Equals(IPAddress.Loopback) || x.Address.Equals(IPAddress.Any)));
}

internal sealed class LauncherForm : Form
{
    private readonly TextBox account = new() { Width = 280, PlaceholderText = "New disposable test account" };
    private readonly TextBox password = new() { Width = 280, UseSystemPasswordChar = true };
    private readonly TextBox output = new() { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill };
    private readonly Label status = new() { AutoSize = true, Text = "Start the test server, then wait for startup completion below." };
    private readonly Button start = new() { Text = "Start test server", AutoSize = true };
    private readonly Button play = new() { Text = "Launch modern client", AutoSize = true };
    private StreamWriter? log;
    private Process? ownedServer;
    private readonly System.Windows.Forms.Timer timer = new() { Interval = 2000 };

    internal LauncherForm()
    {
        Text = "Divided Realms — Modern Client Test (1.130)";
        ClientSize = new Size(800, 550);
        MinimumSize = new Size(740, 500);
        StartPosition = FormStartPosition.CenterScreen;
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(18), ColumnCount = 1, RowCount = 7 };
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 32));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 42));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 42));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 45));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.Controls.Add(new Label { Text = "Modern client 1.130 • isolated test world", AutoSize = true, Font = new Font(Font.FontFamily, 17, FontStyle.Bold) });
        layout.Controls.Add(new Label { Text = "127.0.0.1:10330 • Uses the verified OpenDAoC client • Test credentials are not saved", AutoSize = true });
        layout.Controls.Add(InputRow("Account", account));
        layout.Controls.Add(InputRow("Password", password));
        var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill };
        buttons.Controls.Add(start);
        buttons.Controls.Add(play);
        var stop = new Button { Text = "Stop test server", AutoSize = true };
        stop.Click += (_, _) => Guard(() =>
        {
            if (ownedServer is not { HasExited: false })
                throw new InvalidOperationException("This launcher does not own a running test server. No other process will be stopped.");
            ownedServer.StandardInput.WriteLine("exit");
            ownedServer.StandardInput.Flush();
            status.Text = "Graceful shutdown requested — wait for the server to exit.";
        });
        buttons.Controls.Add(stop);
        var logs = new Button { Text = "Open test folder", AutoSize = true };
        logs.Click += (_, _) => Process.Start(new ProcessStartInfo(Program.TestRoot) { UseShellExecute = true });
        buttons.Controls.Add(logs);
        layout.Controls.Add(buttons);
        layout.Controls.Add(status);
        layout.Controls.Add(output);
        Controls.Add(layout);
        start.Click += (_, _) => Guard(StartServer);
        play.Click += async (_, _) =>
        {
            play.Enabled = false;
            try { await LaunchClient(); }
            catch (Exception e) { ShowError(e); }
            finally { play.Enabled = true; }
        };
        timer.Tick += (_, _) => { try { start.Enabled = !Program.PortListening() && (ownedServer == null || ownedServer.HasExited); } catch { } };
        timer.Start();
        FormClosing += (_, e) =>
        {
            if (ownedServer is { HasExited: false } && MessageBox.Show(this,
                "The test server will keep running after this launcher closes. Close the launcher?",
                "Test server is running", MessageBoxButtons.YesNo) != DialogResult.Yes) e.Cancel = true;
        };
    }

    private static Control InputRow(string name, Control input)
    {
        var row = new FlowLayoutPanel { Dock = DockStyle.Fill };
        row.Controls.Add(new Label { Text = name, Width = 110, Padding = new Padding(0, 5, 0, 0) });
        row.Controls.Add(input);
        return row;
    }

    private void StartServer()
    {
        Program.ValidateConfiguration();
        if (Program.PortListening() || ownedServer is { HasExited: false })
            throw new InvalidOperationException("Test port is already occupied or this server is starting. No existing process was stopped.");
        log?.Dispose();
        log = new StreamWriter(Path.Combine(Program.TestRoot, "server-console.log"), append: true) { AutoFlush = true };
        var info = new ProcessStartInfo(Path.Combine(Program.ServerRoot, "CoreServer.exe"))
        {
            WorkingDirectory = Program.ServerRoot, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true, RedirectStandardInput = true
        };
        info.ArgumentList.Add("--start");
        ownedServer = new Process { StartInfo = info, EnableRaisingEvents = true };
        ownedServer.OutputDataReceived += (_, e) => Append(e.Data);
        ownedServer.ErrorDataReceived += (_, e) => Append(e.Data);
        ownedServer.Exited += (_, _) => Append("Test server exited. Check the messages above.");
        ownedServer.Start();
        ownedServer.BeginOutputReadLine();
        ownedServer.BeginErrorReadLine();
        status.Text = "Test server starting — wait for startup completion in the output.";
        start.Enabled = false;
    }

    private async Task LaunchClient()
    {
        Program.ValidateConfiguration();
        Program.ValidateClient();
        if (!Regex.IsMatch(account.Text, "^[A-Za-z0-9_-]+$") || password.Text.Length == 0 || Regex.IsMatch(password.Text, "[\\s\"]"))
            throw new InvalidOperationException("Enter an account using letters, numbers, underscore or dash, and a password without spaces or quotes.");
        using var tcp = new TcpClient();
        await tcp.ConnectAsync(IPAddress.Loopback, 10330).WaitAsync(TimeSpan.FromSeconds(2));
        var info = new ProcessStartInfo(Path.Combine(Program.TestRoot, "tools", "connect-local1130.exe"))
        { WorkingDirectory = Program.ClientRoot, UseShellExecute = false, CreateNoWindow = true };
        foreach (string arg in new[] { Path.Combine(Program.ClientRoot, "game.dll"), "127.0.0.1:10330", account.Text, password.Text })
            info.ArgumentList.Add(arg);
        Process.Start(info);
        password.Clear();
        status.Text = "Modern client launched. Test login, character creation and world entry.";
    }

    private void Append(string? text)
    {
        if (text == null) return;
        lock (this) { log?.WriteLine(text); }
        if (IsDisposed || !IsHandleCreated) return;
        try { BeginInvoke(() => { if (output.TextLength > 100000) output.Clear(); output.AppendText(text + Environment.NewLine); }); }
        catch (InvalidOperationException) { }
    }

    private void Guard(Action action) { try { action(); } catch (Exception e) { ShowError(e); } }
    private void ShowError(Exception e) => MessageBox.Show(this, e.Message, "Modern client test", MessageBoxButtons.OK, MessageBoxIcon.Error);
}
