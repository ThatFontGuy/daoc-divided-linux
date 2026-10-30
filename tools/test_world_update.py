#!/usr/bin/env python3
"""Test world_update.py against a DividedRealms release's clean world.
    python3 tools/test_world_update.py <clean world.sqlite> <world-updates folder>
Winds the clean world back to before the first step (reverse of every step), applies the update chain, and checks the result equals
the clean world; also that a row edited by play is kept, a second run does nothing, and a damaged step file is refused."""
import json, os, shutil, sqlite3, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_update as w

clean, updates = Path(sys.argv[1]), Path(sys.argv[2])
chain = json.loads((updates / "world-updates.json").read_text())
tmp = Path(tempfile.mkdtemp())
try:
    home = tmp / "srv"
    (home / "data").mkdir(parents=True)
    db = home / "data" / "opendaoc.sqlite3.db"
    shutil.copy2(clean, db)
    shutil.copytree(updates, home / "world-updates")

    con = sqlite3.connect(db, isolation_level=None)
    q = w.q
    touched = {}
    # --- wind back: newest step first
    for step in reversed(chain["Steps"]):
        doc = json.loads((updates / step["File"]).read_text())
        con.execute("BEGIN")
        for t in doc["Tables"]:
            table, cols, keys = t["Table"], t["Columns"], t["Key"]
            kidx = [cols.index(k) for k in keys]
            ign = {c.lower() for c in doc["IgnoreColumns"]} | {c.lower() for c in t.get("IgnoreCompare", [])}
            cmp = [i for i, c in enumerate(cols) if c.lower() not in ign]
            touched[table] = cols
            for row in t["Insert"]:
                con.execute(f"DELETE FROM {q(table)} WHERE " + " AND ".join(f"{q(cols[i])} IS ?" for i in kidx), [w.value(row[i]) for i in kidx])
            for row in t["Update"]:
                old, new = row["Old"], row["New"]
                if "Set" in row:
                    si = [cols.index(c) for c in row["Set"]]
                    con.execute(f"UPDATE {q(table)} SET " + ",".join(f"{q(cols[i])}=?" for i in si) + " WHERE " + " AND ".join(f"{q(cols[i])} IS ?" for i in kidx),
                                [w.value(old[i]) for i in si] + [w.value(new[i]) for i in kidx])
                else:
                    con.execute(f"UPDATE {q(table)} SET " + ",".join(f"{q(c)}=?" for c in cols) + " WHERE " + " AND ".join(f"{q(cols[i])} IS ?" for i in cmp),
                                [w.value(v) for v in old] + [w.value(new[i]) for i in cmp])
            for row in t["Delete"]:
                con.execute(f"INSERT OR IGNORE INTO {q(table)} ({','.join(map(q, cols))}) VALUES ({','.join('?' * len(cols))})", [w.value(v) for v in row])
        con.execute("DELETE FROM offline_patch_log WHERE Version=?", (step["Version"],))
        con.execute("COMMIT")
    con.close()
    first = w.pending_steps(db, chain)
    assert [s["Version"] for s in first] == [s["Version"] for s in chain["Steps"]], first

    # a row edited by play: pick a Mob "Set" update of the newest step that changes a column, edit that column
    doc = json.loads((updates / chain["Steps"][-1]["File"]).read_text())
    probe = None
    for t in doc["Tables"]:
        for row in t["Update"]:
            if "Set" in row and row["Set"] and t["Table"] == "Mob":
                probe = (t, row); break
        if probe: break
    if probe:
        t, row = probe
        cols = t["Columns"]; kidx = [cols.index(k) for k in t["Key"]]; col = row["Set"][0]
        con = sqlite3.connect(db, isolation_level=None)
        # the row must still hold its pre-step value; then play changes it
        con.execute(f"UPDATE {q('Mob')} SET {q(col)}=? WHERE " + " AND ".join(f"{q(cols[i])} IS ?" for i in kidx), ["PLAYEREDIT"] + [w.value(row["New"][i]) for i in kidx])
        con.close()

    # --- check, apply, compare
    pre, ref = sqlite3.connect(db), sqlite3.connect(clean)
    n_pre, n_ref = (c.execute("SELECT count(*) FROM MerchantItem").fetchone()[0] for c in (pre, ref))
    assert n_pre < n_ref, ("the wound-back world must be older than the clean one", n_pre, n_ref)
    pre.close(); ref.close()
    assert w.prepare(home, check_only=True) == [s["Version"] for s in chain["Steps"]]
    lines = []
    done = w.prepare(home, say=lines.append)
    assert done == [s["Version"] for s in chain["Steps"]], done
    assert any("Backed up" in l for l in lines) and (next((home / "backups").iterdir()) / "opendaoc.sqlite3.db").is_file()
    a, b = sqlite3.connect(db), sqlite3.connect(clean)
    ign = {c.lower() for c in doc["IgnoreColumns"]}
    bad = []
    for table, cols in touched.items():
        use = [c for c in cols if c.lower() not in ign]
        sel = f"SELECT {','.join(map(q, use))} FROM {q(table)}"
        ra, rb = sorted(map(repr, a.execute(sel))), sorted(map(repr, b.execute(sel)))
        if ra != rb:
            bad.append((table, len(set(ra) - set(rb)), len(set(rb) - set(ra))))
    if probe:
        assert [r for r in bad if r[0] == "Mob"], "the edited row should differ from the clean world"
        bad = [r for r in bad if r[0] != "Mob" or r[1] != 1 or r[2] != 1]
        left = a.execute(f"SELECT count(*) FROM {q('Mob')} WHERE {q(col)}='PLAYEREDIT'").fetchone()[0]
        assert left == 1, "the row edited by play was overwritten"
    assert not bad, bad
    log_versions = {r[0] for r in a.execute("SELECT Version FROM offline_patch_log")}
    assert {s["Version"] for s in chain["Steps"]} <= log_versions
    a.close(); b.close()
    assert w.prepare(home) == [], "second run must do nothing"

    # a damaged step file is refused, nothing changes
    con = sqlite3.connect(db); con.execute("DELETE FROM offline_patch_log WHERE Version=?", (chain["Steps"][-1]["Version"],)); con.commit(); con.close()
    (home / "world-updates" / chain["Steps"][-1]["File"]).write_text("{}")
    try:
        w.prepare(home); raise SystemExit("damaged step was applied")
    except w.UpdateError:
        pass
    print("OK world update:", ", ".join(done), "| compared tables:", ", ".join(sorted(touched)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
