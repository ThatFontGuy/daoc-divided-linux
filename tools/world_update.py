#!/usr/bin/env python3
"""world_update.py <server folder> [--check] - bring an existing world up to this release's content, keeping the saves.

A Linux port of DividedRealms' WorldUpdate (OfflineDaoc.Patcher/WorldUpdate.cs) and WorldUpdates.Prepare (launcher). The world
file data/opendaoc.sqlite3.db holds both the world content and the characters. Each release ships world-updates/: a list
(world-updates.json) and one JSON file per release step. A step is applied once (recorded in the table offline_patch_log) and
only changes rows that still have their released values, so what play has changed in the game is left alone.

    - no data/opendaoc.sqlite3.db: nothing to do (daoc-server.sh makes a new world from defaults/world.sqlite);
    - otherwise: verify the steps' SHA-256, back the world up to backups/world-update-<version>-<time>/, apply the pending steps
      in order, each in one transaction (a failure rolls that step back and stops).
The server must not be running. Standard library only.
"""
import base64
import hashlib
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


class UpdateError(Exception):
    pass


def q(name):
    return '"' + name.replace('"', '""') + '"'


def value(v):
    """JSON value from the update files -> SQLite value (integers stay integers, {"$b64": ...} is a blob)."""
    if isinstance(v, dict):
        return base64.b64decode(v["$b64"])
    if v is True:
        return 1
    if v is False:
        return 0
    return v


def pending_steps(db_path, chain):
    if not Path(db_path).is_file():
        return list(chain["Steps"])
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        if not con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='offline_patch_log'").fetchone()[0]:
            return list(chain["Steps"])
        done = {r[0] for r in con.execute("SELECT Version FROM offline_patch_log")}
    finally:
        con.close()
    return [s for s in chain["Steps"] if s["Version"] not in done]


def apply_step(db_path, update_file, version, say):
    doc = json.loads(Path(update_file).read_text(encoding="utf-8"))
    con = sqlite3.connect(db_path, isolation_level=None)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS offline_patch_log (Version TEXT PRIMARY KEY, AppliedUtc TEXT, Notes TEXT)")
        if con.execute("SELECT count(*) FROM offline_patch_log WHERE Version=?", (version,)).fetchone()[0]:
            say(f"World data: already updated to {version}.")
            return
        con.execute("BEGIN")
        try:
            _apply(con, doc, version, say)
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    finally:
        con.close()


def _apply(con, doc, version, say):
    for table in doc["NewTables"]:
        for sql in [table["Create"], *table.get("Indexes", [])]:
            sql = re.sub(r"(?i)CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", sql, count=1) \
                if re.match(r"(?i)CREATE UNIQUE INDEX ", sql) else \
                re.sub(r"(?i)^CREATE (TABLE|INDEX) ", r"CREATE \1 IF NOT EXISTS ", sql, count=1)
            con.execute(sql)
    for col in doc["NewColumns"]:
        have = {r[1].lower() for r in con.execute(f"PRAGMA table_info({q(col['Table'])})")}
        if col["Column"].lower() not in have:
            con.execute(f"ALTER TABLE {q(col['Table'])} ADD COLUMN {q(col['Column'])} {col['Decl']}")
    ignored = {c.lower() for c in doc["IgnoreColumns"]}
    added = changed = removed = kept = already = 0
    notes = []
    for t in doc["Tables"]:
        table, cols, keys = t["Table"], t["Columns"], t["Key"]
        key_idx = [cols.index(k) if k in cols else -1 for k in keys]
        table_ignore = {c.lower() for c in t.get("IgnoreCompare", [])}
        cmp_idx = [i for i, c in enumerate(cols) if c.lower() not in ignored and c.lower() not in table_ignore]

        def where(idx, prefix):
            return " AND ".join(f"{q(cols[i])} IS :{prefix}{i}" for i in idx)

        def bind(row, prefix, idx=None):
            return {f"{prefix}{i}": value(row[i]) for i in (range(len(row)) if idx is None else idx)}

        def has(idx, row):
            return con.execute(f"SELECT count(*) FROM {q(table)} WHERE {where(idx, 'h')}", bind(row, "h", idx)).fetchone()[0] > 0

        table_kept = 0
        for row in t["Insert"]:
            cur = con.execute(f"INSERT OR IGNORE INTO {q(table)} ({','.join(map(q, cols))}) VALUES ({','.join(':n%d' % i for i in range(len(cols)))})",
                              bind(row, "n"))
            if cur.rowcount == 1:
                added += 1
            elif key_idx and all(i >= 0 for i in key_idx) and has(key_idx, row):
                already += 1
            else:
                table_kept += 1
        for row in t["Update"]:
            old, new = row["Old"], row["New"]
            if "Set" in row:
                set_idx = [cols.index(c) for c in row["Set"]]
                if not set_idx:
                    continue
                match_idx = list(dict.fromkeys([*key_idx, *set_idx]))
                cur = con.execute(f"UPDATE {q(table)} SET {','.join(f'{q(cols[i])}=:n{i}' for i in set_idx)} WHERE {where(match_idx, 'o')}",
                                  {**bind(new, "n", set_idx), **bind(old, "o", match_idx)})
            else:
                cur = con.execute(f"UPDATE {q(table)} SET {','.join(f'{q(n)}=:n{i}' for i, n in enumerate(cols))} WHERE {where(cmp_idx, 'o')}",
                                  {**bind(new, "n"), **bind(old, "o", cmp_idx)})
            if cur.rowcount > 0:
                changed += 1
            elif "Set" in row and has(list(dict.fromkeys([*key_idx, *[cols.index(c) for c in row["Set"]]])), new):
                already += 1
            else:
                table_kept += 1
        for row in t["Delete"]:
            cur = con.execute(f"DELETE FROM {q(table)} WHERE {where(cmp_idx, 'o')}", bind(row, "o", cmp_idx))
            if cur.rowcount > 0:
                removed += 1
            else:
                table_kept += 1
        if table_kept:
            notes.append(f"{table}: {table_kept} row(s) left as the game had them")
        kept += table_kept
    con.execute("INSERT INTO offline_patch_log (Version, AppliedUtc, Notes) VALUES (?, ?, ?)",
                (version, datetime.now(timezone.utc).isoformat(), "; ".join(notes)))
    say(f"World data updated to {version}: {added} added, {changed} changed, {removed} removed, {already} already up to date, "
        f"{kept} left as the game had them.")
    for note in notes:
        say("  " + note)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(home, check_only=False, say=print):
    """-> list of pending versions (check_only), or the log lines of what was done."""
    home = Path(home)
    database = home / "data" / "opendaoc.sqlite3.db"
    index = home / "world-updates" / "world-updates.json"
    if not database.is_file() or not index.is_file():
        return []
    chain = json.loads(index.read_text(encoding="utf-8"))
    if chain.get("Format") != 1:
        raise UpdateError("This server does not know the world update list's format.")
    todo = pending_steps(database, chain)
    if check_only or not todo:
        return [s["Version"] for s in todo]
    for step in todo:
        f = home / "world-updates" / step["File"]
        if not f.is_file() or sha256(f).upper() != step["Sha256"].upper():
            raise UpdateError(f"The world update {step['File']} is missing or damaged. Extract the whole release again.")
    backup = home / "backups" / f"world-update-{todo[-1]['Version']}-{time.strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True)
    src, dst = sqlite3.connect(f"file:{database}?mode=ro", uri=True), sqlite3.connect(backup / "opendaoc.sqlite3.db")
    try:
        src.backup(dst)
    finally:
        src.close(); dst.close()
    log = [f"Backed up the world to {backup}."]
    say(log[0])
    def record(line):
        log.append(line); say(line)
    for step in todo:
        apply_step(database, home / "world-updates" / step["File"], step["Version"], record)
    (backup / "UPDATE-REPORT.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    return [s["Version"] for s in todo]


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        todo = prepare(args[0], check_only="--check" in argv)
    except (UpdateError, sqlite3.Error, OSError, ValueError, KeyError) as exc:
        print(f"World update failed: {exc}", file=sys.stderr)
        return 1
    if "--check" in argv:
        print("Pending world updates: " + (", ".join(todo) if todo else "none"))
    elif not todo:
        print("World data is up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
