"""READ-ONLY: find every helmet sharing a model's mesh, and which extensions real items use.

  python tools\\helmet_face_check.py <helmet model id> [<model id> ...]

See "HELMET INVISIBLE FACE - HOW TO FIX.txt" in the CLAUDE VERSION root.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pet-art"))
from daoc_catalog import csv_rows, gamedata  # noqa: E402

DB = HERE.parents[1] / "runtime" / "data" / "opendaoc.sqlite3.db"
NIF, HEAD, ALT1, ALT2 = 2, 13, 24, 28   # objects.csv columns


def main(models):
    g = gamedata()
    objects = {r[0].strip(): r for r in csv_rows(g, "objects.csv") if r and r[0].strip().isdigit()}
    items = {r[0].strip(): r for r in csv_rows(g, "items.csv") if r and r[0].strip().isdigit()}
    con = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)
    for model in models:
        row = objects.get(str(model))
        if not row:
            print(f"{model}: no objects.csv row")
            continue
        key = (row[NIF], row[HEAD], row[ALT1], row[ALT2])
        mesh = items.get(row[NIF].strip(), ["", "", "?"])[2]
        family = sorted((int(r[0]) for r in objects.values()
                         if len(r) > ALT2 and (r[NIF], r[HEAD], r[ALT1], r[ALT2]) == key), key=int)
        print(f"model {model} '{row[1]}': mesh items.csv {row[NIF]} ({mesh}), Head # {row[HEAD]}, "
              f"alternates {row[ALT1]}/{row[ALT2]}")
        print(f"  same-mesh family ({len(family)}): {', '.join(map(str, family))}")
        used = con.execute(
            f"SELECT Model, Extension, COUNT(*) FROM ItemTemplate WHERE Item_Type=21 AND Model IN "
            f"({','.join(map(str, family))}) GROUP BY Model, Extension ORDER BY Model, Extension").fetchall()
        print("  helmet items by model/extension:", ", ".join(f"{m}/ext{e}={n}" for m, e, n in used) or "none")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        main([int(a) for a in sys.argv[1:]])
