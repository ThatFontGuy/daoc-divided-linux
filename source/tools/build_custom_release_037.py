"""Build a clean playable package of this fork on the classic 0.37 game, with or without the Stormforged class.

    python build_custom_release_037.py --base <classic 0.37 game folder> --repo <this repository>
                                       --out <new package folder> --edition classic|stormforged

The base is a released classic 0.36 folder brought to 0.37 by upstream's update (its world data at 0.37). It is only
read. The package is that game with this repository's server, launcher, progress importer, docs and source, a clean
world (built by build_release_037.py's own clean_world and checks: no account, character, bot or save; default keeps,
doors and relics; zero-bot start, GM off, 1x XP, automatic account creation) and:
  classic       no custom class: enable_stormforged off, the stock classic client.
Both drop the retired Sluaghbinder's world rows (remove_sluaghbinder.py) and keep its edition switch off.
  stormforged   the Midgard Stormforged class: seed_stormforged.py's world rows (enable_stormforged on) and the client
                patched by patch_client.py, which accepts only the verified classic client.
The co-op / guild-warfare rules ship switched off in both (seed_hybrid_coop.py enables them in an installation).
Nothing is started; a build report with every file's hash is written next to the package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "stormforged"))
import build_release_037 as release  # noqa: E402  (reused, unchanged)
import remove_sluaghbinder  # noqa: E402
import assemble_release_037 as assemble  # noqa: E402
from patch_client import patch as patch_stormforged_client  # noqa: E402
from seed_stormforged import seed as seed_stormforged  # noqa: E402

CLASSIC_CLIENT_SHA256 = release.EDITION_GAME_DLL_SHA256
STORMFORGED_CLIENT_SHA256 = "01d6a77803cbbc94487c8263fffdc105958856a07d39316347d9da0a0ef61df9"
EDITION_TEXT = {
    "classic": "Offline DAoC 0.37 (custom build) - no custom class (Classic + Shrouded Isles classes only).",
    "stormforged": "Offline DAoC 0.37 (custom build) - with the Midgard Stormforged class.",
}
# The base package's own parts that this repository replaces, plus run state that never ships.
BASE_ROOT_SKIP = {"runtime", "source", "docs", "editions", "patch-backups", "PACKAGE MANIFEST.sha256", "EDITION.txt"}
BASE_TOOLS_SKIP = {"pet-art", "claude-version", "asset-tool", "ProgressImporter"}
PRIVATE_DOCS = {"PROJECT-HANDOFF.md"}


def set_property(con: sqlite3.Connection, key: str, value: str):
    con.execute("UPDATE ServerProperty SET Value=? WHERE `Key`=?", (value, key))


def classic_world(con: sqlite3.Connection) -> dict:
    """clean_world switches upstream's Sluaghbinder on (its 0.37b package); this fork has retired the class, so its
    switch stays off (the launcher reads it for the edition label) and its world rows go."""
    release.set_edition(con, False)
    set_property(con, "enable_stormforged", "False")
    return remove_sluaghbinder.apply(con)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--edition", choices=sorted(EDITION_TEXT), required=True)
    args = parser.parse_args()
    base, repo, out = args.base.resolve(), args.repo.resolve(), args.out.resolve()
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite a package folder")
    base_runtime = base / "runtime"
    base_client = base_runtime / "client-opendaoc/app/game.dll"
    if release.sha(base_client) != CLASSIC_CLIENT_SHA256:
        raise SystemExit("The base client is not the verified classic 0.37 client")
    with sqlite3.connect((base_runtime / "data/opendaoc.sqlite3.db").as_uri() + "?mode=ro", uri=True) as con:
        patched = con.execute("SELECT Version FROM offline_patch_log").fetchall()
    if ("0.37",) not in patched:
        raise SystemExit("The base world has not been updated to 0.37")
    policy = json.loads((repo / "source/tools/OfflineDaoc.ProgressImport/progress-policy.json").read_text())
    defaults = json.loads((repo / "source/tools/release-world-defaults.json").read_text(encoding="utf-8"))

    print("Copying the base game (personal, diagnostic and run-state files excluded)...", flush=True)
    copied = release.copy_tree(base_runtime, out / "runtime", release.include)
    for path in sorted(base.iterdir()):
        if path.name in BASE_ROOT_SKIP:
            continue
        if path.is_dir():
            keep = (lambda rel: rel.parts[0] not in BASE_TOOLS_SKIP) if path.name == "tools" else (lambda rel: True)
            copied.update({f"{path.name}/{k}": v for k, v in release.copy_tree(path, out / path.name, keep).items()})
        else:
            shutil.copy2(path, out / path.name)
            copied[path.name] = release.sha(path)

    print("Building the clean world database...", flush=True)
    database = out / "runtime/data/opendaoc.sqlite3.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect((base_runtime / "data/opendaoc.sqlite3.db").as_uri() + "?mode=ro", uri=True) as src, \
            sqlite3.connect(database) as dst:
        src.backup(dst)
    world = release.clean_world(database, policy, defaults)
    con = sqlite3.connect(database)
    edition = classic_world(con)
    if args.edition == "stormforged":
        edition["stormforged"] = seed_stormforged(con)
    con.commit()
    con.execute("VACUUM")
    con.commit()
    assert con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    world["final_check"] = release.verify_clean(con, policy, defaults)
    switches = dict(con.execute("SELECT `Key`,Value FROM ServerProperty WHERE `Key` IN "
                                "('enable_sluaghbinder','enable_stormforged')"))
    con.close()
    assert switches.get("enable_sluaghbinder") == "False", switches
    assert switches.get("enable_stormforged", "False") == ("True" if args.edition == "stormforged" else "False"), switches
    world_data = release.check_world_data(database, repo)

    client = out / "runtime/client-opendaoc/app/game.dll"
    if args.edition == "stormforged":
        client.write_bytes(patch_stormforged_client(base_client.read_bytes()))
    expected_client = STORMFORGED_CLIENT_SHA256 if args.edition == "stormforged" else CLASSIC_CLIENT_SHA256
    assert release.sha(client) == expected_client, "unexpected client after the edition step"

    release.set_auto_account_creation(out / "runtime/server/config/serverconfig.xml")
    (out / "runtime/client-opendaoc/app/paths.dat").write_bytes(
        f"[paths]\r\nsettings={release.CLIENT_PROFILE}".encode("ascii"))

    print("Installing this repository's server and launcher builds...", flush=True)
    replaced = {}
    server_build = repo / "source/server/Release/lib"
    for folder in ("server", "server/lib", "server/win-x64"):
        for name in ("GameServer.dll", "GameServer.pdb"):
            target = out / "runtime" / folder / name
            if target.exists():
                shutil.copy2(server_build / name, target)
                replaced[f"runtime/{folder}/{name}"] = release.sha(target)
    launcher_build = repo / "source/tools/OfflineDaoc.Launcher/bin/Release/net10.0-windows"
    for name in ("OfflineDAoC.dll", "OfflineDAoC.exe", "OfflineDAoC.pdb", "OfflineDAoC.deps.json",
                 "OfflineDAoC.runtimeconfig.json"):
        shutil.copy2(launcher_build / name, out / "runtime" / name)
        replaced[f"runtime/{name}"] = release.sha(out / "runtime" / name)
    release.check_runtime_files(out / "runtime")

    print("Adding the player files, docs, source and tools from this repository...", flush=True)
    counts = {"player files": assemble.copy_tree(repo / "package-files", out)}
    for name in assemble.ROOT_FILES:
        shutil.copy2(repo / name, out / name)
    # PROJECT-HANDOFF.md is the developer's own session hand-off (it names local folders); it is kept local, never shipped.
    counts["docs"] = assemble.copy_tree(repo / "docs", out / "docs", lambda rel: rel.as_posix() not in PRIVATE_DOCS)
    counts["source"] = assemble.copy_tree(repo / "source", out / "source", assemble.keep)
    for tool in ("pet-art", "claude-version", "asset-tool"):
        counts[f"tools/{tool}"] = assemble.copy_tree(repo / "tools" / tool, out / "tools" / tool, assemble.keep)
    counts["tools/ProgressImporter"] = assemble.copy_tree(
        repo / "source/tools/OfflineDaoc.ProgressImport/bin/Release/net10.0-windows", out / "tools/ProgressImporter")
    (out / "EDITION.txt").write_text(EDITION_TEXT[args.edition] + "\r\n", encoding="utf-8-sig")

    print("Checking the package for personal or run-state files...", flush=True)
    forbidden = [p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file() and (
        p.name.lower() == "account.txt"
        or p.suffix.lower() in {".log", ".dmp", ".trx"}
        or p.suffix.lower() in {".db", ".sqlite3", ".db-wal", ".db-shm"} and p != database
        and p.name.lower() != "thumbs.db")]  # Windows' thumbnail cache, part of the released client
    assert not forbidden, f"files that must not ship: {forbidden[:20]}"
    assert not (out / "source/server/CoreServer/config/serverconfig.xml").exists(), "a local server config would ship"

    manifest = {p.relative_to(out).as_posix(): release.sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "PACKAGE MANIFEST.sha256").write_text(
        "".join(f"{digest}  {name}\r\n" for name, digest in manifest.items()), encoding="utf-8")
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "edition": args.edition,
        "base": str(base),
        "base_patch_log": patched,
        "world": world,
        "edition_world": edition,
        "world_data": world_data,
        "switches": switches,
        "client_sha256": release.sha(client),
        "replaced_on_purpose": replaced,
        "assembled": counts,
        "files": len(manifest),
        "bytes": sum((out / name).stat().st_size for name in manifest),
    }
    (out.parent / f"{out.name}-build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"replaced_on_purpose"}}, indent=2), flush=True)


if __name__ == "__main__":
    main()
