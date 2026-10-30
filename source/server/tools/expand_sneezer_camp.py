"""Idempotently expand the Domnann sneezer camp in the isolated runtime DB.

Run only with the new class test server stopped and after a consistent DB backup.
All seven additions clone the original sneezer so their model, level, behavior,
loot, and respawn rules remain identical. Coordinates are global database values.
"""

import argparse
import sqlite3
from pathlib import Path


ORIGINAL_ID = "100024390"
SPAWNS = (
    (417650, 408050, 4378),
    (418300, 408100, 4379),
    (417520, 408420, 4378),
    (418420, 408410, 4382),
    (417700, 408730, 4382),
    (418150, 408800, 4387),
    (418450, 408850, 4391),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("The runtime database failed its pre-change integrity check")

        source = connection.execute(
            "SELECT * FROM Mob WHERE Mob_ID = ?", (ORIGINAL_ID,)
        ).fetchone()
        expected = ("sneezer", 181, 417984, 408257, 4378, 14, 906, 60166277)
        actual = tuple(source[key] for key in (
            "Name", "Region", "X", "Y", "Z", "Level", "Model", "NPCTemplateID"
        )) if source else None
        if actual != expected:
            raise RuntimeError(f"Original sneezer changed; expected {expected}, got {actual}")

        columns = tuple(source.keys())
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        inserted = 0
        with connection:
            for index, (x, y, z) in enumerate(SPAWNS, start=1):
                mob_id = f"sneezer-domnann-20260926-{index:02d}"
                if connection.execute(
                    "SELECT 1 FROM Mob WHERE Mob_ID = ?", (mob_id,)
                ).fetchone():
                    continue
                clone = dict(source)
                clone.update(Mob_ID=mob_id, X=x, Y=y, Z=z)
                connection.execute(
                    f"INSERT INTO Mob ({quoted_columns}) VALUES ({placeholders})",
                    tuple(clone[column] for column in columns),
                )
                inserted += 1

        result = connection.execute(
            "SELECT Mob_ID, Name, X, Y, Z, Level, Model, RespawnInterval "
            "FROM Mob WHERE Region = 181 AND Name = 'sneezer' "
            "AND X BETWEEN 417000 AND 418499 AND Y BETWEEN 408000 AND 409499 "
            "ORDER BY Mob_ID"
        ).fetchall()
        if len(result) != 8:
            raise RuntimeError(f"Expected eight sneezers in this camp, found {len(result)}")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("The runtime database failed its post-change integrity check")
        print(f"Inserted {inserted}; camp now has {len(result)} sneezer spawns")
        for row in result:
            print(tuple(row))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
