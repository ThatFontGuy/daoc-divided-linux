import os
"""Read-only helpers for the DAoC client catalog (gamedata.mpk CSVs + skin MPKs)."""
import csv
import importlib.util
import io
import sys
from pathlib import Path

TOOL = Path(os.environ.get("OFFLINE_DAOC_ARCHIVE_TOOL", Path(__file__).resolve().parents[1] / "asset-tool"))
# Client folder of the install you are editing: set OFFLINE_DAOC_CLIENT, or keep this tools/ folder
# inside the playable folder so ../../runtime/client-opendaoc/app is found.
CLIENT = Path(os.environ.get("OFFLINE_DAOC_CLIENT", Path(__file__).resolve().parents[2] / "runtime" / "client-opendaoc" / "app"))

_spec = importlib.util.spec_from_file_location("daoc_archive", TOOL / "archive.py")
archive = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(archive)


def mpk(path):
    name, entries = archive.read(Path(path).read_bytes())
    return name, entries


def gamedata():
    _, entries = mpk(CLIENT / "gamedata.mpk")
    return {e.name.lower(): e.data for e in entries}


def csv_rows(files, name):
    text = files[name].decode("latin1")
    return list(csv.reader(io.StringIO(text)))


if __name__ == "__main__":
    files = gamedata()
    for n in sys.argv[1:]:
        rows = csv_rows(files, n)
        print(f"== {n}: {len(rows)} rows")
        for r in rows[:8]:
            print(r)
