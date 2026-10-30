"""Idempotently install the isolated Sluaghbinder Epic Spells line.

This changes only the new-class-test SQLite database.  It intentionally reuses
the existing reserved Sluaghbinder's Legacy line instead of adding a second
line, so old test databases remain easy to inspect and roll back.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


SPELLS = [
    (59080, "Raise Merchant", "Summons a stationary skeletal merchant for ten minutes.", 9401, 9401, 10),
    (59081, "Raise Hastener", "Summons a stationary skeletal hastener for ten minutes.", 9402, 9402, 20),
    (59082, "Raise Healer", "Summons a stationary skeletal healer for ten minutes.", 9403, 9403, 30),
    (59083, "Raise Teleporter", "Summons a stationary skeletal teleporter for ten minutes.", 9404, 9404, 40),
    (59084, "Raise Exchanger", "Summons a stationary skeletal realm exchange broker for ten minutes.", 9405, 9405, 50),
]


def install(db_path: Path) -> None:
    db_path = db_path.resolve()
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys=ON")

        # The seventh line was deliberately reserved during the original
        # Sluaghbinder work.  Rename it in place so no duplicate line can be
        # loaded by SkillBase.
        db.execute(
            "UPDATE Specialization SET KeyName=?, Name=?, Description=? "
            "WHERE lower(KeyName)=lower(?)",
            (
                "Epic Spells",
                "Epic Spells",
                "Permanent quest rewards: stationary skeletal quality-of-life services.",
                "Sluaghbinder's Legacy",
            ),
        )
        db.execute(
            "UPDATE SpellLine SET KeyName=?, Name=?, Spec=? WHERE lower(KeyName)=lower(?)",
            ("Epic Spells", "Epic Spells", "Epic Spells", "Sluaghbinder's Legacy"),
        )

        if db.execute("SELECT 1 FROM Specialization WHERE KeyName=?", ("Epic Spells",)).fetchone() is None:
            db.execute(
                "INSERT INTO Specialization "
                "(SpecializationID,KeyName,Name,Icon,Description,Implementation,LastTimeRowUpdated) "
                "VALUES (?,?,?,?,?,?,datetime('now'))",
                (243, "Epic Spells", "Epic Spells", 9407,
                 "Permanent quest rewards: stationary skeletal quality-of-life services.",
                 "DOL.GS.UntrainableSpecialization"),
            )
        if db.execute("SELECT 1 FROM SpellLine WHERE KeyName=?", ("Epic Spells",)).fetchone() is None:
            db.execute(
                "INSERT INTO SpellLine "
                "(SpellLineID,KeyName,Name,Spec,IsBaseLine,ClassIDHint,LastTimeRowUpdated) "
                "VALUES (?,?,?,?,?,?,datetime('now'))",
                (319, "Epic Spells", "Epic Spells", "Epic Spells", 0, 63),
            )

        for spell_id, name, description, effect, icon, level in SPELLS:
            # The database stores duration/recast in seconds; Spell converts
            # them to milliseconds when it builds the runtime Spell object.
            db.execute(
                "INSERT OR IGNORE INTO Spell "
                "(SpellID,ClientEffect,Icon,Name,Description,Target,Range,Power,CastTime,Damage,DamageType,Type,Duration,Frequency,Pulse,PulsePower,Radius,RecastDelay,ResurrectHealth,ResurrectMana,Value,Concentration,LifeDrainReturn,AmnesiaChance,Message1,Message2,Message3,Message4,InstrumentRequirement,SpellGroup,EffectGroup,SubSpellID,MoveCast,Uninterruptible,IsFocus,SharedTimerGroup,IsPrimary,IsSecondary,AllowBolt,PackageID,TooltipId,LastTimeRowUpdated,Spell_ID) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)",
                (
                    spell_id, effect, icon, name, description, "Self", 0, 0, 2.0, 0.0, 0,
                    "SluaghbinderEpicSummon", 600, 0, 0, 0, 0, 3600, 0, 0, 0.0, 0,
                    0, 0, "", "", "", "", 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, "Sluaghbinder_Epic", 29080 + (spell_id - 59080),
                    f"Sluaghbinder_{spell_id}",
                ),
            )
            db.execute(
                "INSERT OR IGNORE INTO LineXSpell(LineName,SpellID,Level,LastTimeRowUpdated,LineXSpell_ID) "
                "VALUES (?,?,?,datetime('now'),?)",
                ("Epic Spells", spell_id, level, f"Epic Spells_{spell_id}"),
            )

        # Existing test databases may already contain an earlier revision of
        # these rows.  Normalize the timer-group fields as well as new inserts:
        # every earned service has its own 60-minute recast, rather than one
        # shared lockout across all five services.
        db.execute(
            "UPDATE Spell SET SpellGroup=0, SharedTimerGroup=0 "
            "WHERE SpellID BETWEEN 59080 AND 59084"
        )

        db.commit()

        count = db.execute("SELECT count(*) FROM LineXSpell WHERE LineName='Epic Spells'").fetchone()[0]
        if count != 5:
            raise RuntimeError(f"Epic Spells line has {count} entries instead of 5")
        if db.execute("SELECT count(*) FROM Spell WHERE Type='SluaghbinderEpicSummon'").fetchone()[0] != 5:
            raise RuntimeError("Epic summon spell rows were not installed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[2] / "runtime" / "data" / "opendaoc.sqlite3.db")
    args = parser.parse_args()
    install(args.db)
    print(f"Installed Sluaghbinder Epic Spells in {args.db.resolve()}")
