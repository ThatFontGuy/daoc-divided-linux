"""Sluaghbinder visuals, part 2 (private rows only; stock spells/effects untouched).

  install : python -B install_sluagh_visuals2.py install
  rollback: python -B install_sluagh_visuals2.py rollback <backup-folder>

1. Cairn Oath ranks missed by the blood-shield install (Aegis, Bastion,
   Rampart, Citadel, Stronghold 59105-59109) now use the private blood shield
   (client spell 4569) instead of holy Shield of Zeal 1706.
2. The seven pet summons (59000-59005, 59030) get private copies of their
   Bonedancer visuals 9401-9407 with the stock "subtle green handglow"
   (493/494, the green twin of the shields' evil red handglow 471/472).
   The stock 9401-9407 rows stay, so Bonedancers and the Epic summons
   (59080-59084) are unchanged.
3. Those seven summons cast in 10 seconds instead of 20.
Only ClientEffect/CastTime of those twelve spells change. Run with the
launcher, client and server CLOSED.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install_blood_shield as bs  # noqa: E402  (shared guarded helpers)
from daoc_catalog import archive  # noqa: E402

CLIENT, DB = bs.CLIENT, bs.DB
BLOOD_SHIELD = 4569
CAIRN_OATH = {59105: 1706, 59106: 1706, 59107: 1706, 59108: 1706, 59109: 1706}
SUMMONS = {59000: 9401, 59001: 9402, 59002: 9403, 59003: 9404, 59004: 9405, 59005: 9406, 59030: 9407}
OLD_CAST, NEW_CAST = 20.0, 10.0
GREEN_HANDS = ("493", "494")


def free_block(tables, count, start=4570):
    used = {int(k) for k in tables["spells.csv"]}
    ident = start
    while any(ident + i in used for i in range(count)):
        ident += 1
    return list(range(ident, ident + count))


def plan():
    name, entries, files, tables = bs.catalogs()
    spells = tables["spells.csv"]
    bs.require(str(BLOOD_SHIELD) in spells, "Blood shield client row 4569 is missing; install it first")
    bs.require(all(k in tables["speffects.csv"] for k in GREEN_HANDS), "Green handglow rows missing")
    ids = free_block(tables, len(SUMMONS))
    mapping = dict(zip(SUMMONS, ids))
    rows = []
    for spell_id, new_id in mapping.items():
        row = list(spells[str(SUMMONS[spell_id])])
        row[0], row[1] = str(new_id), "Sluagh " + row[1].strip()
        row[6:8] = list(GREEN_HANDS)
        rows.append(row)
    data = files["spells.csv"]
    for row in rows:
        data = bs.add_row(data, row)
    new_entries = [archive.Entry(e.name, data if e.name.lower() == "spells.csv" else e.data, e.timestamp, e.flags)
                   for e in entries]
    blob = archive.write(name, new_entries)
    archive.verify_memory_image(blob)
    _, decoded = archive.read(blob)
    bs.require([e.name for e in decoded] == [e.name for e in entries], "Archive entry order changed")
    for old, new in zip(entries, decoded):
        bs.require((old.timestamp, old.flags) == (new.timestamp, new.flags), "Archive metadata changed")
        if old.name.lower() != "spells.csv":
            bs.require(old.data == new.data, f"Unrelated archive entry changed: {old.name}")
        else:
            added = [r for r in bs.rows_of(new.data) if r in rows]
            bs.require(len(added) == len(rows), "New rows missing")
            bs.require([r for r in bs.rows_of(new.data) if r not in rows] == bs.rows_of(old.data), "Stock row changed")
    return blob, mapping, rows


def expected_changes(mapping):
    changes = {i: {"ClientEffect": BLOOD_SHIELD} for i in CAIRN_OATH}
    changes.update({i: {"ClientEffect": mapping[i], "CastTime": NEW_CAST} for i in SUMMONS})
    return changes


def assert_delta(before, after, changes):
    bs.require(before.keys() == after.keys(), "Spell definitions added/removed")
    for ident, row in before.items():
        expected = dict(row)
        expected.update(changes.get(ident, {}))
        bs.require(after[ident] == expected, f"Unexpected spell change {ident}")


def install():
    bs.stopped()
    blob, mapping, rows = plan()
    game = CLIENT / "gamedata.mpk"
    with bs.read_db() as con:
        before = bs.spell_snapshot(con)
    for i, old in CAIRN_OATH.items():
        bs.require(before[i]["ClientEffect"] == old, f"{i} ClientEffect is not {old}; re-review")
    for i, old in SUMMONS.items():
        bs.require(before[i]["ClientEffect"] == old and float(before[i]["CastTime"]) == OLD_CAST,
                   f"{i} is not ClientEffect {old} / CastTime {OLD_CAST}; re-review")
    backup = HERE / "install-backups" / ("sluagh-visuals2-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(game, backup / "gamedata.mpk")
    with bs.db_session(DB) as con, bs.db_session(backup / "opendaoc.sqlite3.db") as destination:
        con.backup(destination)
        bs.require(destination.execute("PRAGMA quick_check").fetchone()[0] == "ok", "DB backup invalid")
    changes = expected_changes(mapping)
    manifest = {"root": str(bs.ROOT), "created": datetime.now().astimezone().isoformat(),
                "before_gamedata_sha256": bs.file_sha(game), "after_gamedata_sha256": bs.sha(blob),
                "client_rows": {str(k): v for k, v in mapping.items()},
                "before": {str(i): {c: before[i][c] for c in changes[i]} for i in changes},
                "after": {str(i): changes[i] for i in changes}}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bs.atomic_write(game, blob)
    with bs.db_session(DB) as con:
        con.row_factory = sqlite3.Row
        for ident, values in changes.items():
            sets = ", ".join(f"{column}=?" for column in values)
            con.execute(f"UPDATE Spell SET {sets} WHERE SpellID=?", (*values.values(), ident))
        assert_delta(before, bs.spell_snapshot(con), changes)
        bs.require(con.execute("PRAGMA quick_check").fetchone()[0] == "ok", "DB quick_check failed")
    bs.require(bs.file_sha(game) == manifest["after_gamedata_sha256"], "Installed catalog differs")
    print("New client rows:", mapping)
    print(f'Installed. Rollback with:\n  python -B "{Path(__file__).resolve()}" rollback "{backup}"')


def rollback(folder: Path):
    bs.stopped()
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    game = CLIENT / "gamedata.mpk"
    bs.require(bs.file_sha(game) in (m["before_gamedata_sha256"], m["after_gamedata_sha256"]),
               "Later catalog changes detected; refuse to overwrite them")
    with bs.db_session(DB) as con:
        con.row_factory = sqlite3.Row
        before = bs.spell_snapshot(con)
        for ident, values in m["after"].items():
            current = {c: before[int(ident)][c] for c in values}
            bs.require(current == values or current == m["before"][ident], f"Later change on {ident}; refuse")
        for ident, values in m["before"].items():
            sets = ", ".join(f"{column}=?" for column in values)
            con.execute(f"UPDATE Spell SET {sets} WHERE SpellID=?", (*values.values(), int(ident)))
    bs.atomic_write(game, (folder / "gamedata.mpk").read_bytes())
    bs.require(bs.file_sha(game) == m["before_gamedata_sha256"], "Rollback catalog mismatch")
    print("Rolled back", folder)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        install()
    elif len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "plan":
        _, mapping, rows = plan()
        print(mapping)
        for r in rows:
            print(r[:14])
    else:
        print(__doc__)
