"""Sluaghbinder life-drain update for an existing 0.34b world (database only).

* All life drains (Steal/Drink/Siphon/Plunder/Devour Vitality, Guardian Lifesteal,
  Dullahan's Blood Tithe) play the naburite drinker's drain animation (10079).
* The five Abhartach's Bane drains share one recast timer, so casting any rank
  puts every rank on its 4 second recast.
* Dullahan's Grave Rot (the Dullahan pet's DoT) gets its own effect group.
* The Abhartach's Bane DoTs play the Plague Spores cloud (3425), cosmetic only.

Usage (server stopped):
    python -B install_bane_drain_update.py              preview
    python -B install_bane_drain_update.py install      apply (backs up first)
    python -B install_bane_drain_update.py rollback <backup.json>
Add --db <path> to target a database other than runtime/data/opendaoc.sqlite3.db.
"""
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "runtime" / "data" / "opendaoc.sqlite3.db"

OLD_EFFECT, DRAIN_EFFECT = 662, 10079
DRAINS = (59019, 59020, 59021, 59022, 59023, 59034, 59072)
BANE_DRAINS = (59019, 59020, 59021, 59022, 59023)
BANE_TIMER_GROUP = 59019
# The Dullahan pet's Grave Rot gets its own effect group so it always stacks
# beside its owner's Rot and Bane damage over time.
GRAVE_ROT, GRAVE_ROT_GROUP = 59070, 59070
# The five Abhartach's Bane DoTs play the Plague Spores cloud instead of the
# baseline Abhartach's Rot animation.
OLD_DOT_EFFECT, BANE_DOT_EFFECT = 511, 3425
BANE_DOTS = (59014, 59015, 59016, 59017, 59018)


def fail(message):
    raise SystemExit(f"ERROR: {message}")


def server_stopped():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process CoreServer,OfflineDAoC -ErrorAction SilentlyContinue | Measure-Object).Count"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if out not in ("", "0"):
        fail("CoreServer or the OfflineDAoC launcher is running; stop them first")


def plan(con):
    con.row_factory = sqlite3.Row
    ids = DRAINS + (GRAVE_ROT,) + BANE_DOTS
    rows = {r["SpellID"]: r for r in con.execute(
        "SELECT SpellID, Name, ClientEffect, SharedTimerGroup, EffectGroup FROM Spell "
        f"WHERE SpellID IN ({','.join('?' * len(ids))})", ids)}
    missing = [i for i in ids if i not in rows]
    if missing:
        fail(f"Sluaghbinder spells missing: {missing}; seed the Sluaghbinder first")
    other = con.execute("SELECT SpellID FROM Spell WHERE SharedTimerGroup=? AND SpellID NOT IN "
                        f"({','.join('?' * len(BANE_DRAINS))})", (BANE_TIMER_GROUP, *BANE_DRAINS)).fetchall()
    if other:
        fail(f"Timer group {BANE_TIMER_GROUP} is already used by {[r[0] for r in other]}; re-review")
    other = con.execute("SELECT SpellID FROM Spell WHERE EffectGroup=? AND SpellID<>?",
                        (GRAVE_ROT_GROUP, GRAVE_ROT)).fetchall()
    if other:
        fail(f"Effect group {GRAVE_ROT_GROUP} is already used by {[r[0] for r in other]}; re-review")
    updates = {}
    for ident in ids:
        row = rows[ident]
        change = {}
        if ident in DRAINS and row["ClientEffect"] != DRAIN_EFFECT:
            if row["ClientEffect"] != OLD_EFFECT:
                fail(f"{ident} {row['Name']} has animation {row['ClientEffect']}, expected {OLD_EFFECT}; re-review")
            change["ClientEffect"] = DRAIN_EFFECT
        if ident in BANE_DRAINS and row["SharedTimerGroup"] != BANE_TIMER_GROUP:
            change["SharedTimerGroup"] = BANE_TIMER_GROUP
        if ident == GRAVE_ROT and row["EffectGroup"] != GRAVE_ROT_GROUP:
            change["EffectGroup"] = GRAVE_ROT_GROUP
        if ident in BANE_DOTS and row["ClientEffect"] != BANE_DOT_EFFECT:
            if row["ClientEffect"] != OLD_DOT_EFFECT:
                fail(f"{ident} {row['Name']} has animation {row['ClientEffect']}, expected {OLD_DOT_EFFECT}; re-review")
            change["ClientEffect"] = BANE_DOT_EFFECT
        if change:
            updates[ident] = (row["Name"], {c: row[c] for c in change}, change)
    return updates


def main(argv):
    db = DB
    if "--db" in argv:
        i = argv.index("--db")
        db = Path(argv[i + 1]).resolve()
        argv = argv[:i] + argv[i + 2:]
    if not db.exists():
        fail(f"Database not found: {db}")
    action = argv[0] if argv else "preview"

    if action == "rollback":
        server_stopped()
        saved = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        with sqlite3.connect(db) as con:
            for ident, values in saved["before"].items():
                sets = ", ".join(f"{c}=?" for c in values)
                con.execute(f"UPDATE Spell SET {sets} WHERE SpellID=?", (*values.values(), int(ident)))
        print("Rolled back.")
        return

    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    updates = plan(con)
    con.close()
    if not updates:
        print("Already up to date.")
        return
    for ident, (name, before, after) in updates.items():
        print(f"  {ident} {name}: " + ", ".join(f"{c} {before[c]} -> {after[c]}" for c in after))
    if action != "install":
        print("Preview only. Run with 'install' to apply.")
        return

    server_stopped()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db.with_name(f"{db.stem}.before-bane-drain-{stamp}.db")
    with sqlite3.connect(db) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    record = backup.with_suffix(".json")
    record.write_text(json.dumps({"before": {str(i): b for i, (_, b, _) in updates.items()}}, indent=2) + "\n",
                      encoding="utf-8")
    con = sqlite3.connect(db)
    try:
        with con:  # one transaction: all or nothing
            for ident, (_, _, after) in updates.items():
                sets = ", ".join(f"{c}=?" for c in after)
                con.execute(f"UPDATE Spell SET {sets} WHERE SpellID=?", (*after.values(), ident))
        if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            fail("Database quick_check failed; restore " + str(backup))
    finally:
        con.close()
    print(f"Installed. Backup: {backup}")
    print(f'Rollback with: python -B "{Path(__file__).resolve()}" rollback "{record}"')


if __name__ == "__main__":
    main(sys.argv[1:])
