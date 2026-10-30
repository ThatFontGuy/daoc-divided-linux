using System.Data.SQLite;
using System.Text.Json;

namespace OfflineDaoc.Patcher;

/// <summary>
/// Applies db-&lt;edition&gt;.json: new tables and columns, then per table the released rows that were added, changed or
/// removed. A change or removal only happens where the player's row still has its released values (volatile columns
/// such as LastTimeRowUpdated are ignored), so rows the running game has rewritten are left as they are.
/// </summary>
internal sealed class WorldUpdate(string database, string updateFile, string version, Action<string> say)
{
    public void Apply()
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(updateFile));
        var root = doc.RootElement;
        using var c = new SQLiteConnection($"Data Source={database};Pooling=False");
        c.Open();
        Exec(c, "CREATE TABLE IF NOT EXISTS offline_patch_log (Version TEXT PRIMARY KEY, AppliedUtc TEXT, Notes TEXT)");
        using (var check = c.CreateCommand())
        {
            check.CommandText = "SELECT count(*) FROM offline_patch_log WHERE Version=@v";
            check.Parameters.AddWithValue("@v", version);
            if (Convert.ToInt64(check.ExecuteScalar()) > 0)
            {
                say($"World data: already updated to {version}.");
                return;
            }
        }
        using var tx = c.BeginTransaction();
        foreach (var t in root.GetProperty("NewTables").EnumerateArray())
        {
            Exec(c, t.GetProperty("Create").GetString()!, tx, ignoreExists: true);
            if (t.TryGetProperty("Indexes", out var indexes))
                foreach (var index in indexes.EnumerateArray())
                    Exec(c, index.GetString()!, tx, ignoreExists: true);
        }
        foreach (var col in root.GetProperty("NewColumns").EnumerateArray())
        {
            string table = col.GetProperty("Table").GetString()!, name = col.GetProperty("Column").GetString()!;
            if (!Columns(c, table, tx).Contains(name, StringComparer.OrdinalIgnoreCase))
                Exec(c, $"ALTER TABLE {Q(table)} ADD COLUMN {Q(name)} {col.GetProperty("Decl").GetString()}", tx);
        }
        var ignored = root.GetProperty("IgnoreColumns").EnumerateArray().Select(e => e.GetString()!).ToHashSet(StringComparer.OrdinalIgnoreCase);
        long added = 0, changed = 0, removed = 0, kept = 0, already = 0;
        var notes = new List<string>();
        foreach (var t in root.GetProperty("Tables").EnumerateArray())
        {
            string table = t.GetProperty("Table").GetString()!;
            string[] cols = t.GetProperty("Columns").EnumerateArray().Select(e => e.GetString()!).ToArray();
            string[] keys = t.GetProperty("Key").EnumerateArray().Select(e => e.GetString()!).ToArray();
            int[] keyIdx = keys.Select(k => Array.IndexOf(cols, k)).ToArray();
            var tableIgnore = t.TryGetProperty("IgnoreCompare", out var ic) ? ic.EnumerateArray().Select(e => e.GetString()!).ToHashSet(StringComparer.OrdinalIgnoreCase) : [];
            int[] cmpIdx = Enumerable.Range(0, cols.Length).Where(i => !ignored.Contains(cols[i]) && !tableIgnore.Contains(cols[i])).ToArray();
            string where(int[] idx, string prefix) => string.Join(" AND ", idx.Select(i => $"{Q(cols[i])} IS @{prefix}{i}"));
            long tableKept = 0;
            // a row that already has this version's values (an earlier build of the same update ran here) is up to date
            bool has(int[] idx, JsonElement row)
            {
                using var q = Cmd(c, tx, $"SELECT count(*) FROM {Q(table)} WHERE {where(idx, "h")}");
                Bind(q, "h", row, idx);
                return Convert.ToInt64(q.ExecuteScalar()) > 0;
            }

            foreach (var row in t.GetProperty("Insert").EnumerateArray())
            {
                using var cmd = Cmd(c, tx, $"INSERT OR IGNORE INTO {Q(table)} ({string.Join(",", cols.Select(Q))}) VALUES ({string.Join(",", cols.Select((_, i) => "@n" + i))})");
                Bind(cmd, "n", row);
                if (cmd.ExecuteNonQuery() == 1) added++;
                else if (keyIdx.Length > 0 && keyIdx.All(i => i >= 0) && has(keyIdx, row)) already++;
                else tableKept++;
            }
            foreach (var row in t.GetProperty("Update").EnumerateArray())
            {
                var oldRow = row.GetProperty("Old");
                var newRow = row.GetProperty("New");
                SQLiteCommand cmd;
                if (row.TryGetProperty("Set", out var set))
                {
                    // field update: only the fields this version changes, where they still have their released values
                    // (the running server rewrites other fields itself, e.g. monster size, level and stats)
                    int[] setIdx = set.EnumerateArray().Select(e => Array.IndexOf(cols, e.GetString()!)).ToArray();
                    if (setIdx.Length == 0) continue;
                    int[] matchIdx = keyIdx.Concat(setIdx).Distinct().ToArray();
                    cmd = Cmd(c, tx, $"UPDATE {Q(table)} SET {string.Join(",", setIdx.Select(i => $"{Q(cols[i])}=@n{i}"))} WHERE {where(matchIdx, "o")}");
                    Bind(cmd, "n", newRow, setIdx);
                    Bind(cmd, "o", oldRow, matchIdx);
                }
                else
                {
                    cmd = Cmd(c, tx, $"UPDATE {Q(table)} SET {string.Join(",", cols.Select((n, i) => $"{Q(n)}=@n{i}"))} WHERE {where(cmpIdx, "o")}");
                    Bind(cmd, "n", newRow);
                    Bind(cmd, "o", oldRow, cmpIdx);
                }
                using (cmd)
                {
                    if (cmd.ExecuteNonQuery() > 0) changed++;
                    else if (row.TryGetProperty("Set", out var done) &&
                             has(keyIdx.Concat(done.EnumerateArray().Select(e => Array.IndexOf(cols, e.GetString()!))).Distinct().ToArray(), newRow)) already++;
                    else tableKept++;
                }
            }
            foreach (var row in t.GetProperty("Delete").EnumerateArray())
            {
                using var cmd = Cmd(c, tx, $"DELETE FROM {Q(table)} WHERE {where(cmpIdx, "o")}");
                Bind(cmd, "o", row, cmpIdx);
                if (cmd.ExecuteNonQuery() > 0) removed++; else tableKept++;
            }
            if (tableKept > 0) notes.Add($"{table}: {tableKept} row(s) left as the game had them");
            kept += tableKept;
        }
        using (var log = Cmd(c, tx, "INSERT INTO offline_patch_log (Version, AppliedUtc, Notes) VALUES (@v, @t, @n)"))
        {
            log.Parameters.AddWithValue("@v", version);
            log.Parameters.AddWithValue("@t", DateTime.UtcNow.ToString("o"));
            log.Parameters.AddWithValue("@n", string.Join("; ", notes));
            log.ExecuteNonQuery();
        }
        tx.Commit();
        say($"World data updated to {version}: {added} added, {changed} changed, {removed} removed, {already} already up to date, " +
            $"{kept} left as the game had them.");
        foreach (string note in notes) say("  " + note);
    }

    static string Q(string name) => "\"" + name.Replace("\"", "\"\"") + "\"";

    static SQLiteCommand Cmd(SQLiteConnection c, SQLiteTransaction tx, string sql)
    {
        var cmd = c.CreateCommand();
        cmd.Transaction = tx;
        cmd.CommandText = sql;
        return cmd;
    }

    static void Exec(SQLiteConnection c, string sql, SQLiteTransaction? tx = null, bool ignoreExists = false)
    {
        using var cmd = c.CreateCommand();
        cmd.Transaction = tx;
        cmd.CommandText = !ignoreExists ? sql : sql
            .Replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", StringComparison.OrdinalIgnoreCase)
            .Replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", StringComparison.OrdinalIgnoreCase)
            .Replace("CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", StringComparison.OrdinalIgnoreCase);
        cmd.ExecuteNonQuery();
    }

    static List<string> Columns(SQLiteConnection c, string table, SQLiteTransaction tx)
    {
        using var cmd = Cmd(c, tx, $"PRAGMA table_info({Q(table)})");
        using var r = cmd.ExecuteReader();
        var result = new List<string>();
        while (r.Read()) result.Add(r.GetString(1));
        return result;
    }

    static void Bind(SQLiteCommand cmd, string prefix, JsonElement row, int[]? only = null)
    {
        var values = row.EnumerateArray().ToArray();
        foreach (int i in only ?? Enumerable.Range(0, values.Length).ToArray())
            cmd.Parameters.AddWithValue($"@{prefix}{i}", Value(values[i]));
    }

    // JSON values from make_patch: numbers as written by SQLite (integers stay integers), text, null, {"$b64": blob}
    static object Value(JsonElement v) => v.ValueKind switch
    {
        JsonValueKind.Null => DBNull.Value,
        JsonValueKind.String => v.GetString()!,
        JsonValueKind.Number => v.TryGetInt64(out long l) && !v.GetRawText().Contains('.') && !v.GetRawText().Contains('e') && !v.GetRawText().Contains('E')
            ? l : v.GetDouble(),
        JsonValueKind.True => 1L,
        JsonValueKind.False => 0L,
        JsonValueKind.Object => Convert.FromBase64String(v.GetProperty("$b64").GetString()!),
        _ => throw new InvalidDataException("Unexpected value in the world update: " + v.GetRawText()),
    };
}
