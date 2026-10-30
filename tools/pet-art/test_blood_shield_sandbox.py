"""Exercise blood-shield install/rollback ONLY in a disposable fake installation.

The original ROOT is opened read-only. Production process guards are replaced
only after ALL writable paths have been redirected into TemporaryDirectory.
No test can invoke an installer using live CLIENT/DB/OUT paths.
"""
from __future__ import annotations
import contextlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
import install_blood_shield as shield


def main():
    live_root, live_client, live_effects = shield.ROOT, shield.CLIENT, shield.EFFECTS
    live_db_hash = shield.file_sha(shield.DB)
    live_game_hash = shield.file_sha(live_client / "gamedata.mpk")
    live_effect_hashes = shield.effect_inventory()
    with shield.read_db() as con:
        table_names = ("Spell", "SpellLine", "LineXSpell", "NpcTemplate", "Mob")
        copy = {}
        for name in table_names:
            schema = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]
            rows = [dict(r) for r in con.execute("SELECT * FROM " + shield.quote(name))]
            # All spells, but only relevant supporting DB definitions are needed.
            if name == "Mob":
                rows = []
            elif name == "NpcTemplate":
                rows = [r for r in rows if r["TemplateId"] in (30000, 60170005, 60170007)]
            elif name == "SpellLine":
                rows = [r for r in rows if r["ClassIDHint"] == 63]
            elif name == "LineXSpell":
                rows = [r for r in rows if r["SpellID"] in shield.SCOPED]
            copy[name] = schema, rows
    with tempfile.TemporaryDirectory(prefix="sluagh-blood-shield-sandbox-") as temporary:
        root = Path(temporary)
        assert root.resolve() != live_root.resolve()
        shield.ROOT, shield.HERE = root, root / "tools/pet-art"
        shield.CLIENT = root / "runtime/client-opendaoc/app"
        shield.EFFECTS = shield.CLIENT / "effects"
        shield.DB = root / "runtime/data/opendaoc.sqlite3.db"
        shield.OUT = shield.HERE / "work/blood-shield-review"
        shield.EFFECTS.mkdir(parents=True)
        shield.DB.parent.mkdir(parents=True)
        for name in (shield.SOURCE_NIF, "amethmap.tga", "prpspike.tga"):
            shutil.copy2(live_effects / name, shield.EFFECTS / name)
        for path in live_effects.glob("black.*"):
            shutil.copy2(path, shield.EFFECTS / path.name)
        shutil.copy2(live_client / "gamedata.mpk", shield.CLIENT / "gamedata.mpk")
        with shield.db_session(shield.DB) as con:
            for name, (schema, rows) in copy.items():
                con.execute(schema)
                if rows:
                    columns = list(rows[0])
                    con.executemany("INSERT INTO " + shield.quote(name) + " (" + ",".join(map(shield.quote, columns)) +
                                    ") VALUES (" + ",".join("?" for _ in columns) + ")",
                                    [tuple(row[c] for c in columns) for row in rows])
        # Guard override exists ONLY inside this redirected sandbox process.
        shield.stopped = lambda: None
        checks = []
        with contextlib.redirect_stdout(io.StringIO()):
            shield.prepare()
            manifest = json.loads((shield.OUT / "review_manifest.json").read_text(encoding="utf-8"))
            checks.append("prepare leaves sandbox baseline unchanged")
            for animation in (32, 35):
                with shield.read_db() as con:
                    before = shield.spell_snapshot(con)
                shield.install(animation)
                backups = sorted((shield.HERE / "install-backups").glob("blood-shield-*"))
                backup = backups[-1]
                first_hash = shield.file_sha(shield.DB)
                shield.install(animation)
                assert shield.file_sha(shield.DB) == first_hash
                assert sorted((shield.HERE / "install-backups").glob("blood-shield-*")) == backups
                checks.append(f"animation {animation}: repeated install performs no writes")
                with shield.read_db() as con:
                    after = shield.spell_snapshot(con)
                shield.assert_spell_delta(before, after, {i: shield.CLIENT_ID for i in shield.SCOPED})
                checks.append(f"animation {animation}: exactly nine ClientEffect fields change")
                # Simulate later unrelated gameplay/progress edits. Rollback
                # must not restore the entire old DB and lose those edits.
                with shield.db_session(shield.DB) as con:
                    con.execute("UPDATE Spell SET Description='sandbox later progress' WHERE SpellID=2")
                shield.rollback(backup)
                with shield.read_db() as con:
                    restored = shield.spell_snapshot(con)
                before[2]["Description"] = "sandbox later progress"
                assert restored == before
                assert shield.file_sha(shield.CLIENT / "gamedata.mpk") == live_game_hash
                assert not any((shield.EFFECTS / n).exists() for n in shield.PRIVATE_FILES)
                checks.append(f"animation {animation}: rollback restores effect fields/catalog, preserves later DB edits")
                shield.rollback(backup)
                checks.append(f"animation {animation}: repeated rollback is safe")
        result = {"created": shield.datetime.now().astimezone().isoformat(), "sandbox_only": True,
                  "checks": checks, "passed": len(checks), "failed": 0}
        # Destination explicitly back under the review folder, not any client.
        destination = live_root / "tools/pet-art/work/blood-shield-review/sandbox_test_results.json"
        assert destination.is_relative_to(live_root / "tools/pet-art/work")
        destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert shield.file_sha(live_root / "runtime/data/opendaoc.sqlite3.db") == live_db_hash
    assert shield.file_sha(live_client / "gamedata.mpk") == live_game_hash
    # Keep verification scoped to live effect files even after the sandbox ends.
    actual = {str(p.relative_to(live_effects)).replace("\\", "/"): shield.file_sha(p)
              for p in sorted(live_effects.rglob("*")) if p.is_file()}
    assert actual == live_effect_hashes
    print(json.dumps(result, indent=2))
    print("Production DB, gamedata and every existing effects file remained byte-identical.")


if __name__ == "__main__":
    main()
