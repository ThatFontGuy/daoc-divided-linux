using System;
using System.IO;
using System.Threading;
using DOL.Logging;

namespace DOL.GS;

/// <summary>
/// The launcher's Bot AI diagnostics switch. Off (the default) the per-bot diagnostic log lines are neither built nor
/// written, which is what a normal player wants; on, everything AI testing and the overnight reports read is logged.
/// The switch is a file beside bot-goals.json, so the launcher can flip it while the server runs: it is checked every
/// few seconds, and nothing else about the bots changes either way.
/// </summary>
public static class BotDiagnostics
{
    public const string FileName = "bot-diagnostics.on";
    private const int CheckMilliseconds = 5_000;

    private static string _path;
    private static Timer _timer;

    public static bool Enabled => Logger.BotDiagnosticsEnabled;

    public static void Initialize(string rootDirectory)
    {
        _path = string.IsNullOrEmpty(rootDirectory) ? null : Path.Combine(rootDirectory, FileName);
        Refresh(null);
        _timer ??= new Timer(Refresh, null, CheckMilliseconds, CheckMilliseconds);
    }

    private static void Refresh(object state)
    {
        try
        {
            Logger.BotDiagnosticsEnabled = _path != null && File.Exists(_path);
        }
        catch (Exception)
        {
        }
    }
}
