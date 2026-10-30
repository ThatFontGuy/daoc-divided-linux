"""Copy the stock Catacombs meshes the Dubh Sluagh painters need into ./nif (read-only on the client).

python -B extract_meshes.py

Body01-08, Arms01, Legs01, Gloves01-08, Boots01-08 and the Dragonsworn heavy helm for Celt (BC) and
Firbolg (Fir), male and female; Cloak01-03 from fig012 (the archive fig3parts.csv names for cloaks);
plus the heads used by the preview scripts. Stock meshes are never redistributed: run this against
your own client.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import daoc_catalog as d  # noqa: E402
from daoc_catalog import archive  # noqa: E402

OUT = HERE / "nif"


def wanted():
    names = {}
    for race in ("BC", "Fir"):
        for sex in ("m", "f"):
            for part in ("Body", "Gloves", "Boots"):
                for i in range(1, 9):
                    names[f"{part}{i:02d}_{race}_{sex}.nif".lower()] = None
            for part in ("Arms01", "Legs01", "ADR_Dragonsworn_Helm_Heavy"):
                names[f"{part}_{race}_{sex}.nif".lower()] = None
    for race in ("cel", "fir"):
        for sex in ("m", "f"):
            for i in (1, 2, 3):
                names[f"cloak{i:02d}_{race}_{sex}.nif"] = "fig012"
    for head in ("bri_m_head01", "bri_f_head01", "fir_m_head01", "fir_f_head01"):
        names[f"{head}.nif"] = None
    return names


def main():
    OUT.mkdir(exist_ok=True)
    want = wanted()
    got = {}
    for mpk in sorted((d.CLIENT / "figures" / "fig3").glob("*.mpk")):
        _, entries = archive.read(mpk.read_bytes())
        for e in entries:
            key = e.name.lower()
            if key in want and (want[key] is None or want[key] == mpk.stem.lower()):
                if key not in got or want[key] is not None:
                    got[key] = (e.name, e.data)
    for key, (name, data) in sorted(got.items()):
        (OUT / name).write_bytes(data)
    missing = sorted(set(want) - set(got))
    print(f"copied {len(got)} meshes to {OUT}")
    if missing:
        print("not found (fine if your client lacks them):", ", ".join(missing))


if __name__ == "__main__":
    main()
