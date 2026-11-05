#!/usr/bin/env python3
"""renumber_class_id.py <db-path> <old-id> <new-id> [--apply]

Moves every row that references character-class ID <old-id> onto <new-id>, across every table and
column in the world database that actually stores a real character-class ID - not a "ClassType"
(an unrelated DOL concept: a C# behavior-class name on Mob/NpcTemplate/ItemTemplate/ZonePoint/etc.,
nothing to do with eCharacterClass) or a class-name-keyed column (TimeXLevel.Character_Class,
offline_world_bots.ClassName, and similar - unaffected by a pure ID renumber, since the name itself
doesn't change).

This exists because giving a custom class a native client-creation slot means moving it onto
whatever class ID that slot's native class used to have - and that same migration bit this
project's own Drengr class three separate times, each only found by a live, reported, in-game
symptom:
    - StarterEquipment (starting gear silently wrong)
    - SpecXAbility (armor/weapon-type proficiency silently missing)
    - Style and StyleXSpell (melee styles silently stuck after level 1)
Those three were eventually found with a manual, one-off SQL sweep of every table with a
Class/ClassId/ClassID/CharClass-shaped column. This script is that sweep, made permanent and
repeatable, with the classification below baked in from that sweep and from auditing this
project's entire schema (every single "%lass%"-named column, not just the ones that happened to
bite before) - see docs/CHANGING-A-CLASS-ID.md for the full procedure this fits into.

Without --apply: dry run. Reports every matching row, table by table - review this before ever
using --apply; it changes nothing.
With --apply: backs up the whole database file next to itself first (<db>.bak-<timestamp>), then
applies every change in one transaction - a failure rolls back everything and the original file is
untouched either way (the backup is on top of that, not instead of it).

Rediscovers every "%lass%"-named column in the live schema on each run and checks it against the
classification below - refuses to run at all if it finds one that isn't classified yet, rather
than silently skip it. If a future schema change adds one, classify it in exactly one of
CLASS_ID_COLUMNS / CLASS_ID_LIST_COLUMNS / IGNORED_COLUMNS below before running this again.

Standard library only.
"""
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

# A bare class ID: an integer value (some columns are declared TEXT but still store it as a
# plain numeric string, e.g. StarterEquipment.Class - compared/bound as text either way, which
# SQLite's type affinity handles correctly for both INT- and TEXT-declared columns storing one).
CLASS_ID_COLUMNS = {
    ("ClassXRealmAbility_Atlas", "CharClass"),
    ("ClassXSpecialization", "ClassID"),
    ("DOLCharacters", "Class"),
    ("DOLCharactersBackup", "Class"),
    ("SpecXAbility", "ClassId"),
    ("SpellLine", "ClassIDHint"),
    ("StarterEquipment", "Class"),
    ("StartupLocation", "ClassID"),
    ("Style", "ClassId"),
    ("StyleXSpell", "ClassID"),
    ("bot_profiles", "ClassId"),
    ("offline_level50_loadouts", "ClassId"),
    ("offline_world_bots", "ClassId"),
}

# A delimited list of class IDs sharing one column (e.g. "2;9;11" or "2|3|10|5") - rewritten
# token by token, never as a blind substring replace (so renumbering 6 to 60 can't also corrupt
# an unrelated "60" or turn "2;6" into "2;60" by accident).
CLASS_ID_LIST_COLUMNS = {
    ("ItemTemplate", "AllowedClasses"): ";",
    ("ItemUnique", "AllowedClasses"): ";",
    ("DataQuest", "AllowedClasses"): "|",
}

# Known "%lass%"-named columns that are NOT a character-class ID reference, so the discovery
# sweep below can skip them without treating them as unclassified:
#   - every ClassType / LootGeneratorClass / ProtectorClassType is the unrelated DOL "ClassType"
#     concept (a C# behavior-class name - which NPC brain, which zone-point handler, etc.)
#   - every column storing the class's NAME, not its ID, which a pure ID renumber never touches
#     (only a rename would, and that's a separate, non-automatic step - see the docs)
IGNORED_COLUMNS = {
    ("Area", "ClassType"),
    ("DataQuest", "ClassType"),
    ("InstanceXElement", "ClassType"),
    ("ItemTemplate", "ClassType"),
    ("ItemUnique", "ClassType"),
    ("KeepHookPointItem", "ClassType"),
    ("KeepPosition", "ClassType"),
    ("LootGenerator", "LootGeneratorClass"),
    ("Minotaurrelic", "ProtectorClassType"),
    ("Mob", "ClassType"),
    ("NpcTemplate", "ClassType"),
    ("Regions", "ClassType"),
    ("WorldObject", "ClassType"),
    ("ZonePoint", "ClassType"),
    ("offline_classic165_removed_mobs", "ClassType"),
    # Name-keyed, not ID-keyed:
    ("DOLCharacters", "FlagClassName"),
    ("DOLCharactersBackup", "FlagClassName"),
    ("TimeXLevel", "Character_Class"),
    ("offline_bot_memory", "PlayerClass"),
    ("offline_bot_nemesis", "KillerClass"),
    ("offline_server_firsts", "ClassName"),
    ("offline_world_bots", "ClassName"),
    ("PlayerInfo", "Class"),
    # This script's own bookkeeping, and itself:
    ("ClassXRealmAbility_Atlas", "ClassXRealmAbility_Atlas_ID"),
    ("ClassXSpecialization", "ClassXSpecializationID"),
}

# Columns that hold a *spec keyname*, not a class ID at all - but this project's own convention
# (not a DB guarantee) is that a spec genuinely private to one class names itself
# "<name>_<classid>" (e.g. "vikingcareer_64"), so SpecXAbility.ClassId=0 (a wildcard - "any class
# training this exact spec", not literally class ID 0) is correct and normal for one of these:
# the spec keyname itself, not the ClassId column, is what actually ties it to one class. A pure
# ClassId-column renumber (above) does not and cannot rename these; this is reported separately,
# below, as advice, not applied - see docs/CHANGING-A-CLASS-ID.md for why it stays a manual,
# reviewed step (a keyname is free text, and "ends with _<id>" is this project's convention, not
# something safe to blindly string-replace across every row in the database).
#
# Unlike CLASS_ID_COLUMNS/CLASS_ID_LIST_COLUMNS/IGNORED_COLUMNS above, this set is NOT protected
# by discover_class_columns()'s "%lass%" sweep - none of these column names actually contain
# "lass" ("SpecKeyName", "LineName", "KeyName", bare "Spec"), so a new one added to the schema
# later would not be caught automatically the way an unclassified ClassId-shaped column is. Stay
# alert for a new column following this same naming convention when the schema changes.
KEYNAME_SUFFIX_COLUMNS = {
    ("ClassXSpecialization", "SpecKeyName"),
    ("Specialization", "KeyName"),
    ("SpecXAbility", "Spec"),
    ("SpellLine", "Spec"),
    ("SpellLine", "KeyName"),
    ("LineXSpell", "LineName"),
    ("Style", "SpecKeyName"),
}


class RenumberError(Exception):
    pass


def discover_class_columns(con):
    """Every "%lass%"-named column in the live schema right now - the thing that actually makes
    this safe over time: a new one found here that isn't in any of the three sets above stops the
    script instead of being silently skipped, which is exactly the bug class this script exists
    to prevent."""
    rows = con.execute(
        "SELECT m.name, p.name FROM sqlite_master m JOIN pragma_table_info(m.name) p "
        "WHERE m.type='table' AND (p.name LIKE '%lass%') ORDER BY m.name, p.name"
    ).fetchall()
    return [(t, c) for t, c in rows]


def classify(columns):
    unclassified = []
    id_cols, list_cols = [], []
    for table, col in columns:
        key = (table, col)
        if key in IGNORED_COLUMNS:
            continue
        if key in CLASS_ID_COLUMNS:
            id_cols.append(key)
        elif key in CLASS_ID_LIST_COLUMNS:
            list_cols.append(key)
        else:
            unclassified.append(key)
    return id_cols, list_cols, unclassified


def plan_id_column(con, table, col, old_id):
    count = con.execute(
        f'SELECT count(*) FROM "{table}" WHERE CAST("{col}" AS TEXT) = ?', (str(old_id),)
    ).fetchone()[0]
    return count


def apply_id_column(con, table, col, old_id, new_id):
    decl_type = next(
        r[2] for r in con.execute(f'PRAGMA table_info("{table}")') if r[1] == col
    )
    new_value = int(new_id) if "INT" in decl_type.upper() else str(new_id)
    cur = con.execute(
        f'UPDATE "{table}" SET "{col}" = ? WHERE CAST("{col}" AS TEXT) = ?',
        (new_value, str(old_id)),
    )
    return cur.rowcount


def plan_list_column(con, table, col, delim, old_id):
    old_tok = str(old_id)
    rows = con.execute(
        f'SELECT rowid, "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL AND "{col}" != \'\''
    ).fetchall()
    matches = []
    for rowid, value in rows:
        tokens = [t.strip() for t in str(value).split(delim)]
        if old_tok in tokens:
            matches.append((rowid, value))
    return matches


def apply_list_column(con, table, col, delim, old_id, new_id, matches):
    old_tok, new_tok = str(old_id), str(new_id)
    changed = 0
    for rowid, value in matches:
        tokens = [t.strip() for t in str(value).split(delim)]
        tokens = [new_tok if t == old_tok else t for t in tokens]
        con.execute(f'UPDATE "{table}" SET "{col}" = ? WHERE rowid = ?', (delim.join(tokens), rowid))
        changed += 1
    return changed


def report_keyname_suffixes(con, old_id):
    """Advisory only, never applied: every distinct value in a known spec-keyname column that
    ends with (or, for the compound LineXSpell.LineName/SpellLine.KeyName form, contains)
    "_<old_id>" by this project's own naming convention - a human (or a future session, told to
    follow docs/CHANGING-A-CLASS-ID.md) still has to decide what each should be renamed to and
    make that change itself; seeing the full list up front is the point, so it isn't discovered
    one broken spec at a time like it was for Drengr."""
    suffix = f"_{old_id}"
    existing_tables = {
        r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    findings = []
    for table, col in sorted(KEYNAME_SUFFIX_COLUMNS):
        if table not in existing_tables:
            continue
        rows = con.execute(
            f'SELECT DISTINCT "{col}" FROM "{table}" WHERE "{col}" LIKE ?', (f"%{suffix}%",)
        ).fetchall()
        # A plain "ends with" match for a bare keyname column; LineXSpell.LineName and
        # SpellLine.KeyName are "<spec>_<line display name>" compounds, so require "_<old_id>_"
        # or "_<old_id>" immediately followed by another underscore-joined segment instead.
        values = [r[0] for r in rows if r[0].endswith(suffix) or f"{suffix}_" in r[0]]
        if values:
            findings.append((table, col, values))
    return findings


def run(db_path, old_id, new_id, apply):
    # Plain connection, not a read-only URI: this phase only ever SELECTs, so there's nothing a
    # read-write handle can damage, and it sidesteps a real WAL-mode quirk - a bare "mode=ro" URI
    # needs the database's own -wal/-shm files reachable (present on a live server actually
    # running in WAL mode, but not e.g. a single copied-out .db file), and fails to open at all
    # otherwise.
    con = sqlite3.connect(db_path)
    try:
        columns = discover_class_columns(con)
        id_cols, list_cols, unclassified = classify(columns)
        if unclassified:
            names = ", ".join(f"{t}.{c}" for t, c in unclassified)
            raise RenumberError(
                f"Found column(s) not yet classified: {names}. Add each one to exactly one of "
                "CLASS_ID_COLUMNS, CLASS_ID_LIST_COLUMNS, or IGNORED_COLUMNS in this script "
                "(check what it actually stores first - see the docstring), then run again. "
                "Refusing to guess."
            )

        print(f"Checking class ID {old_id} -> {new_id} in {db_path}\n")
        id_plan = [(t, c, plan_id_column(con, t, c, old_id)) for t, c in sorted(id_cols)]
        list_plan = [
            (t, c, CLASS_ID_LIST_COLUMNS[(t, c)], plan_list_column(con, t, c, CLASS_ID_LIST_COLUMNS[(t, c)], old_id))
            for t, c in sorted(list_cols)
        ]
        total = 0
        for table, col, count in id_plan:
            if count:
                print(f"  {table}.{col}: {count} row(s)")
                total += count
        for table, col, delim, matches in list_plan:
            if matches:
                print(f"  {table}.{col}: {len(matches)} row(s) (delimited list, token-rewritten)")
                total += len(matches)
        if total:
            print(f"\n{total} row(s) total across {sum(1 for _, _, c in id_plan if c) + sum(1 for *_, m in list_plan if m)} column(s).")
        else:
            print("Nothing references that class ID in any known ClassId-style column.")

        suffix_findings = report_keyname_suffixes(con, old_id)
        if suffix_findings:
            print(
                f"\nNOT changed above (these are spec KEYNAMES, not a ClassId column - see this "
                f"script's KEYNAME_SUFFIX_COLUMNS comment and docs/CHANGING-A-CLASS-ID.md):\n"
                f"found {sum(len(v) for *_, v in suffix_findings)} value(s) using the "
                f"\"_{old_id}\" naming convention - review whether each should be renamed to "
                f"\"_{new_id}\" (and every table referencing it updated to match):"
            )
            for table, col, values in suffix_findings:
                for v in values:
                    print(f"  {table}.{col}: {v}")

        if not total and not suffix_findings:
            return 0
    finally:
        con.close()

    if not apply:
        print("\nDry run only - nothing changed. Re-run with --apply to make these changes.")
        return 0

    backup = Path(db_path).with_name(f"{Path(db_path).name}.bak-{time.strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(db_path, backup)
    print(f"\nBacked up to {backup}")

    con = sqlite3.connect(db_path, isolation_level=None)
    try:
        con.execute("BEGIN")
        try:
            for table, col, count in id_plan:
                if count:
                    changed = apply_id_column(con, table, col, old_id, new_id)
                    print(f"  {table}.{col}: {changed} row(s) updated")
            for table, col, delim, matches in list_plan:
                if matches:
                    changed = apply_list_column(con, table, col, delim, old_id, new_id, matches)
                    print(f"  {table}.{col}: {changed} row(s) updated")
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    finally:
        con.close()
    print("\nDone. The database was changed in place; the pre-change backup is at", backup)
    return 0


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 3:
        print(__doc__)
        return 2
    db_path, old_id, new_id = args[0], args[1], args[2]
    if not re.fullmatch(r"-?\d+", old_id) or not re.fullmatch(r"-?\d+", new_id):
        print("renumber_class_id: <old-id> and <new-id> must be plain integers", file=sys.stderr)
        return 2
    try:
        return run(db_path, int(old_id), int(new_id), apply="--apply" in argv)
    except (RenumberError, sqlite3.Error, OSError) as exc:
        print(f"renumber_class_id failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
