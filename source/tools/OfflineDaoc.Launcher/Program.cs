namespace OfflineDaoc.Launcher;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--verify-modern-profile")
        {
            try
            {
                var profile = ModernClientProfile.Load(AppContext.BaseDirectory)
                    ?? throw new InvalidDataException("No modern client profile is installed.");
                _ = profile.CreateStartInfo("verification-only", "not-used");
                File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "modern-profile-verification.json"),
                    System.Text.Json.JsonSerializer.Serialize(new { Passed = true, profile.Endpoint, ServerStarted = false, ClientLaunched = false }));
            }
            catch { Environment.ExitCode = 1; }
            return;
        }
        if (args.Length == 2 && args[0] == "--setup-modern-client")
        {
            // Headless client setup (package tests): copy and patch the given 1.130 client, or bring an existing copy up to
            // this release's patch from it, then verify the profile.
            try
            {
                var profile = ModernClientProfile.Load(AppContext.BaseDirectory)
                    ?? throw new InvalidDataException("No modern client profile is installed.");
                var patch = ModernClientSetup.Load(AppContext.BaseDirectory);
                if (ModernClientSetup.IsSetUp(profile))
                    ModernClientSetup.Update(profile.ClientDirectory, patch, args[1]);
                else
                    ModernClientSetup.Install(args[1], profile.ClientDirectory, patch, null, CancellationToken.None);
                _ = profile.CreateStartInfo("verification-only", "not-used");
            }
            catch (Exception ex)
            {
                File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "modern-client-setup-error.txt"), ex.ToString());
                Environment.ExitCode = 1;
            }
            return;
        }
        if (args.Length == 1 && args[0] == "--prepare-world")
        {
            // Headless world preparation (package tests): make the world or apply this release's pending world updates.
            try
            {
                foreach (string line in WorldUpdates.Prepare(MainForm.ServerRootFor(AppContext.BaseDirectory)))
                    Console.WriteLine(line);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine(ex);
                Environment.ExitCode = 1;
            }
            return;
        }
        if (args.Length == 1 && args[0] == "--prepare-portable-account")
        {
            // the new client's launcher keeps its account with the game it plays (server_root.txt)
            PortableCredentials.ReadOrCreate(MainForm.ServerRootFor(AppContext.BaseDirectory));
            return;
        }
        if (args.Length == 1 && args[0] == "--apply-recommended-settings")
        {
            // Setup, after a first install: every Living Server feature on at the suggested settings (exit code 0 when saved).
            Environment.ExitCode = ApplyRecommendedSettings();
            return;
        }
        ApplicationConfiguration.Initialize();
        if (args.Length == 1 && args[0] == "--join")
        {
            // Join Friend.cmd: client only. No dashboard, no local server, no local save.
            try
            {
                string root = MainForm.ServerRootFor(AppContext.BaseDirectory);
                ModernClientProfile? modern = MainForm.IsNewClientFolder(AppContext.BaseDirectory) ? null : ModernClientProfile.Load(root);
                Application.Run(new JoinFriendForm(root, modern));
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Join Friend could not start", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            return;
        }
        try { Application.Run(new MainForm()); }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Divided Realms launcher could not start", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private static int ApplyRecommendedSettings()
    {
        string database = Path.Combine(MainForm.ServerRootFor(AppContext.BaseDirectory), "data", "opendaoc.sqlite3.db");
        try
        {
            bool stopped = System.Diagnostics.Process.GetProcessesByName("CoreServer").Length == 0;
            SocialExpansionSettings.Recommended.Save(database, null, () => stopped);
            var problems = new List<string>();
            bool saved = SocialExpansionSettings.Load(database, problems) == SocialExpansionSettings.Recommended && problems.Count == 0;
            Console.WriteLine(saved ? "Recommended Living Server settings saved in " + database
                                    : "Saved, but reading back differs: " + string.Join("; ", problems));
            return saved ? 0 : 2;
        }
        catch (Exception e)
        {
            Console.WriteLine("Recommended settings not saved: " + e.Message);
            return 1;
        }
    }
}
