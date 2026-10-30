"""Sluaghbinder healer pet: zombie priest -> ghastly healer (badh ghost). Cosmetic only.

  preview : python -B install_ghastly_healer.py            (default, changes nothing)
  install : python -B install_ghastly_healer.py install
  rollback: python -B install_ghastly_healer.py rollback <backup.json>
Add --db <path> to target a database other than runtime/data/opendaoc.sqlite3.db.

* Pet template 60170006 is named "ghastly healer" and uses the badh's floating
  female ghost model (1885, anim set 295 "Classic Bainshee"). That set casts
  with the badh's own three-part spell animation and has hand nodes for spell
  glows and a held weapon.
* The pet keeps its Celtic Dirk (object 454) in the right hand; the badh's
  two-handed staff is not given to it. The badh's own robe pieces are added
  so the pet looks like the world badh.
* Spells renamed to match: "Raise Zombie Priest" -> "Raise Ghastly Healer"
  and the healer's "Priest's Mending" -> "Ghastly Mending" (names and
  descriptions only).

Spells, stats, AI, level, size and every other column stay the same. The
server must run CLAUDE VERSION 2ad9854 or later (the healer AI and stats
recognise the new name); install refuses otherwise.
"""
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "runtime" / "data" / "opendaoc.sqlite3.db"
SERVER_DLL = ROOT / "runtime" / "server" / "GameServer.dll"

TEMPLATE = 60170006
NAME = ("zombie priest", "ghastly healer")
MODEL = ("2498", "1885")
PRIVATE_MODEL = "2072"  # tools/pet-art/install_ghastly_healer_art.py
EQUIPMENT = "sluagh_zombie_priest_mace_buckler"  # internal key, kept stable
BADH_EQUIPMENT = "d3f7a84d-f150-4523-874d-a957ddb6a30d"
ROBE_SLOTS = (22, 23, 25, 27, 28)  # gloves, boots, torso, legs, arms; never the staff (12)
DAGGER = (10, 454)
# Spell renames: id -> (old name, new name, new description)
SPELL_TEXT = {
    59005: ("Raise Zombie Priest", "Raise Ghastly Healer", "Raises a ghastly healer to serve the Sluaghbinder."),
    59038: ("Priest's Mending", "Ghastly Mending", "A mournful keen that mends one ally."),
}


def fail(message):
    raise SystemExit(f"ERROR: {message}")


def server_stopped():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process CoreServer,OfflineDAoC -ErrorAction SilentlyContinue | Measure-Object).Count"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if out not in ("", "0"):
        fail("CoreServer or the OfflineDAoC launcher is running; stop them first")


def server_knows_new_name():
    return SERVER_DLL.exists() and "ghastly healer".encode("utf-16-le") in SERVER_DLL.read_bytes()


def plan(con):
    con.row_factory = sqlite3.Row
    template = con.execute("SELECT Name, Model, EquipmentTemplateID FROM NpcTemplate WHERE TemplateId=?",
                           (TEMPLATE,)).fetchone()
    if template is None:
        fail(f"Pet template {TEMPLATE} missing; seed the Sluaghbinder first")
    if template["EquipmentTemplateID"] != EQUIPMENT:
        fail(f"Pet equipment template is {template['EquipmentTemplateID']}, expected {EQUIPMENT}")
    changes = []
    for column, (old, new) in (("Name", NAME), ("Model", MODEL)):
        if column == "Model" and template[column] == PRIVATE_MODEL:
            continue  # the private ghastly healer art (pet-art) is already installed on top
        if template[column] != new:
            if template[column] != old:
                fail(f"Template {column} is {template[column]!r}, expected {old!r}; re-review")
            changes.append(("NpcTemplate", column, old, new))

    slots = {r["Slot"]: r for r in con.execute("SELECT * FROM NPCEquipment WHERE TemplateID=?", (EQUIPMENT,))}
    if slots.get(DAGGER[0]) is None or slots[DAGGER[0]]["Model"] != DAGGER[1]:
        fail(f"Pet right hand is not the Celtic Dirk ({DAGGER[1]}); re-review")
    if 12 in slots or 11 in slots:
        fail("Pet has a two-handed or left-hand item; re-review")
    badh = {r["Slot"]: r for r in con.execute("SELECT * FROM NPCEquipment WHERE TemplateID=?", (BADH_EQUIPMENT,))}
    if not all(slot in badh for slot in ROBE_SLOTS):
        fail("World badh equipment template changed; re-review")
    robes = []
    for slot in ROBE_SLOTS:
        if slot in slots:
            if (slots[slot]["Model"], slots[slot]["Color"]) != (badh[slot]["Model"], badh[slot]["Color"]):
                fail(f"Pet slot {slot} already holds another item; re-review")
            continue
        robes.append((slot, badh[slot]["Model"], badh[slot]["Color"]))

    for ident, (old_name, new_name, new_text) in SPELL_TEXT.items():
        spell = con.execute("SELECT Name, Description FROM Spell WHERE SpellID=?", (ident,)).fetchone()
        if spell is None:
            fail(f"Spell {ident} missing")
        if (spell["Name"], spell["Description"]) == (new_name, new_text):
            continue
        if spell["Name"] != old_name:
            fail(f"Spell {ident} is named {spell['Name']!r}, expected {old_name!r}; re-review")
        changes.append(("Spell", ident, [spell["Name"], spell["Description"]], [new_name, new_text]))
    return changes, robes


def apply(con, changes, robes):
    for table, column, _, new in changes:
        if table == "NpcTemplate":
            con.execute(f"UPDATE NpcTemplate SET {column}=? WHERE TemplateId=?", (new, TEMPLATE))
        else:
            con.execute("UPDATE Spell SET Name=?, Description=? WHERE SpellID=?", (*new, column))
    for slot, model, color in robes:
        con.execute("INSERT INTO NPCEquipment (TemplateID, Slot, Model, Color, Effect, Extension, Emblem, "
                    "LastTimeRowUpdated, NPCEquipment_ID) VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?)",
                    (EQUIPMENT, slot, model, color, "2000-01-01 00:00:00", f"{EQUIPMENT}:{slot}"))


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
            for table, column, old, _ in saved["changes"]:
                if table == "NpcTemplate":
                    con.execute(f"UPDATE NpcTemplate SET {column}=? WHERE TemplateId=?", (old, TEMPLATE))
                else:
                    con.execute("UPDATE Spell SET Name=?, Description=? WHERE SpellID=?", (*old, column))
            for slot, _, _ in saved["robes"]:
                con.execute("DELETE FROM NPCEquipment WHERE TemplateID=? AND Slot=?", (EQUIPMENT, slot))
        print("Rolled back.")
        return

    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    changes, robes = plan(con)
    con.close()
    if not changes and not robes:
        print("Already up to date.")
        return
    for table, column, old, new in changes:
        print(f"  {table} {column}: {old!r} -> {new!r}")
    for slot, model, color in robes:
        print(f"  NPCEquipment {EQUIPMENT} slot {slot}: + badh robe model {model} color {color}")
    print(f"  Right hand stays the Celtic Dirk ({DAGGER[1]}); no staff.")
    if not server_knows_new_name():
        print("  NOTE: the deployed GameServer.dll does not know 'ghastly healer' yet; install will refuse.")
    if action != "install":
        print("Preview only. Run with 'install' to apply.")
        return

    server_stopped()
    if db == DB and not server_knows_new_name():
        fail("Deploy CLAUDE VERSION 2ad9854 or later first, or the renamed pet loses its healer AI and stats")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db.with_name(f"{db.stem}.before-ghastly-healer-{stamp}.db")
    with sqlite3.connect(db) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    record = backup.with_suffix(".json")
    record.write_text(json.dumps({"changes": changes, "robes": robes}, indent=2) + "\n", encoding="utf-8")
    con = sqlite3.connect(db)
    try:
        with con:  # one transaction: all or nothing
            apply(con, changes, robes)
        if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            fail("Database quick_check failed; restore " + str(backup))
    finally:
        con.close()
    print(f"Installed. Backup: {backup}")
    print(f'Rollback with: python -B "{Path(__file__).resolve()}" rollback "{record}"')


if __name__ == "__main__":
    main(sys.argv[1:])
