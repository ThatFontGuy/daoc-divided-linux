using System.Collections.Generic;

namespace DOL.GS;

/// <summary>
/// Stops a bot recasting one buff for ever out of combat (owner 2026-10-30: a Healer in Jordheim cast non-stop and no buff
/// showed on anyone, and every cast also stopped her walking). A buff lasts a minute or more, so a third cast at the same
/// target inside a minute means the bot's check can't see what the spell did. It then leaves that buff alone for five
/// minutes, whatever the reason, and the bot's log line names the spell. Target is 0 for a buff that doesn't go to one
/// chosen target (self, group), so buffing eight people in turn never trips it.
/// </summary>
public sealed class BotBuffRecastGuard
{
    public const int CastsToTrip = 3;
    public const long WindowMs = 60_000;
    public const long BlockMs = 5 * 60_000;

    private sealed class Entry
    {
        public int Casts;
        public long WindowStart;
        public long BlockedUntil;
    }

    private readonly Dictionary<(int Spell, int Target), Entry> _entries = new();

    public bool Blocks(int spellId, int targetId, long now) =>
        _entries.TryGetValue((spellId, targetId), out Entry entry) && now < entry.BlockedUntil;

    /// <summary>A cast started. True when this one trips the guard.</summary>
    public bool Record(int spellId, int targetId, long now)
    {
        if (!_entries.TryGetValue((spellId, targetId), out Entry entry))
            _entries[(spellId, targetId)] = entry = new Entry();
        if (now - entry.WindowStart > WindowMs)
        {
            entry.WindowStart = now;
            entry.Casts = 0;
        }
        if (++entry.Casts < CastsToTrip)
            return false;
        entry.Casts = 0;
        entry.BlockedUntil = now + BlockMs;
        return true;
    }

    /// <summary>The buffs this applies to: kept-up ones that end or pulse on their own terms are left out, as are heals. Pure.</summary>
    public static bool Applies(bool maintainableBuff, bool harmful, bool healing, bool pulsing) =>
        maintainableBuff && !harmful && !healing && !pulsing;
}
