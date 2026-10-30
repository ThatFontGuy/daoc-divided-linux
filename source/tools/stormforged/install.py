"""Preview or install the Stormforged development build into a stopped classic 0.36 game.

Usage: python install.py <game-folder> [--apply]
       python install.py <game-folder> --rollback <backup-folder>
No server or client is started by this tool.
"""
import argparse
from contextlib import closing
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

from patch_client import patch
from seed_stormforged import seed

REPO = Path(__file__).resolve().parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stopped(root):
    command = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object Name,ExecutablePath | ConvertTo-Json -Compress"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True)
    rows = json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(rows, dict):
        rows = [rows]
    for process in rows:
        executable = process.get("ExecutablePath")
        if executable and Path(executable).resolve().is_relative_to(root):
            raise RuntimeError(f"Close {process['Name']} in the selected installation first")


def validate_path(root, relative):
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("Target redirects outside the selected game folder")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--enable-coop-pvp", action="store_true", help="Enable the validated co-op/guild warfare rules in this installation")
    parser.add_argument("--disable-coop-pvp", action="store_true", help="Restore normal RvR and default keep-claim settings")
    parser.add_argument("--rollback", type=Path)
    args = parser.parse_args()
    if args.enable_coop_pvp and args.disable_coop_pvp:
        parser.error("Choose enable or disable co-op rules")
    if args.apply and args.rollback:
        parser.error("Choose apply or rollback")
    root = args.game.resolve(strict=True)
    database = validate_path(root, "runtime/data/opendaoc.sqlite3.db")
    if args.apply:
        stopped(root)
        # Fold any final clean-shutdown writes into the database using SQLite itself.
        # Read-only previews can leave an empty WAL behind; its existence alone is not a writer.
        with closing(sqlite3.connect(database, timeout=5)) as checkpoint:
            if checkpoint.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] != 0:
                raise ValueError("Database is still busy; close the server cleanly before installing")
    if args.rollback:
        stopped(root)
        backup = args.rollback.resolve(strict=True)
        record = json.loads((backup/"manifest.json").read_text())
        if record["installation"] != str(root):
            raise ValueError("Backup belongs to another installation")
        # Check ALL targets before restoring any file. In particular, refuse to erase newer play.
        for entry in record["files"]:
            if digest(validate_path(root, entry["path"])) != entry["installed_sha256"]:
                raise ValueError(f"File changed after installation; manual recovery needed: {entry['path']}")
            if digest(validate_path(backup, entry["backup"])) != entry["original_sha256"]:
                raise ValueError("Backup hash mismatch")
        for entry in record["files"]:
            shutil.copy2(backup/entry["backup"], validate_path(root, entry["path"]))
        print("Restored the original files. Backup retained:", backup)
        return

    build = REPO/"source/server/Release/lib/GameServer.dll"
    if not build.is_file():
        raise ValueError("Build the Release server first")
    client = validate_path(root, "runtime/client-opendaoc/app/game.dll")
    original_client = client.read_bytes()
    # Updates reuse only the exact client produced by our verified v1 patch.
    # Other patched/unknown clients remain rejected by patch().
    client_bytes = original_client if hashlib.sha256(original_client).hexdigest() == "01d6a77803cbbc94487c8263fffdc105958856a07d39316347d9da0a0ef61df9" else patch(original_client)
    # Prepare and validate a private database before changing the selected installation.
    artifacts = REPO/"artifacts"
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stormforged-", dir=artifacts) as temp:
        temp = Path(temp)
        world = temp/"world.db"
        with closing(sqlite3.connect(database.as_uri()+"?mode=ro", uri=True)) as source, closing(sqlite3.connect(world)) as out:
            source.backup(out)
        with closing(sqlite3.connect(world)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            summary = seed(db)
            if args.enable_coop_pvp:
                from seed_hybrid_coop import enable
                summary.update(enable(db))
            if args.disable_coop_pvp:
                from seed_hybrid_coop import disable
                summary.update(disable(db))
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("World integrity check failed")
        patched = temp/"game.dll"
        patched.write_bytes(client_bytes)
        files = [("runtime/client-opendaoc/app/game.dll", patched), ("runtime/data/opendaoc.sqlite3.db", world)]
        for directory in ("runtime/server", "runtime/server/lib", "runtime/server/win-x64"):
            files.append((directory+"/GameServer.dll", build))
            symbols = build.with_suffix(".pdb")
            if symbols.is_file() and (root/directory/"GameServer.pdb").is_file():
                files.append((directory+"/GameServer.pdb", symbols))
        for relative, _ in files:
            validate_path(root, relative)
        print(json.dumps({"preview": not args.apply, "installation": str(root), **summary,
                          "files": [r for r, _ in files], "server_sha256": digest(build),
                          "client_sha256": hashlib.sha256(client_bytes).hexdigest()}, indent=2))
        if not args.apply:
            print("No game files changed. Stop the game, launcher and server before --apply.")
            return
        stopped(root)
        # A preview while playing is safe; installation must recheck the source after stopping.
        if any(path.stat().st_size > 0 for path in database.parent.glob(database.name+"-wal")):
            raise ValueError("SQLite WAL remains; close the server cleanly before installing")
        backup = root/("stormforged-backup-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        backup.mkdir(exist_ok=False)
        record = {"installation": str(root), "files": []}
        for index, (relative, source) in enumerate(files):
            target = validate_path(root, relative)
            saved = str(index)+"-"+target.name
            shutil.copy2(target, backup/saved)
            record["files"].append({"path": relative, "backup": saved, "original_sha256": digest(target),
                                    "installed_sha256": digest(source)})
        (backup/"manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        try:
            for relative, source in files:
                shutil.copy2(source, root/relative)
            for entry in record["files"]:
                if digest(root/entry["path"]) != entry["installed_sha256"]:
                    raise ValueError("Post-install verification failed")
        except Exception:
            for entry in record["files"]:
                shutil.copy2(backup/entry["backup"], root/entry["path"])
            raise
        print("Installed. Backup and guarded rollback manifest:", backup)


if __name__ == "__main__":
    main()
