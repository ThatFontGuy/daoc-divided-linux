"""Client helpers for the admin screen: check a DAoC 1.130 client folder and switch its two files between patched and original.

Only the standard library is used. The patching itself is source/tools/classslots/patch_class_slots.py (bundled next to this
file as classslots/ in a release). Nothing here touches a file unless the caller asks, and a patch is refused unless both
files are the pristine 1.130 ones. Originals are kept as <name>.orig next to the patched file, so switching back and
forth never needs the original client again.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
from pathlib import Path

GAME_DLL = "game.dll"
LAYOUT = Path("pregame") / "character_creation.xml"
BACKUP = ".orig"


class ClientError(Exception):
    pass


def _patcher():
    here = Path(__file__).resolve().parent
    for candidate in (here / "classslots", here.parent / "source" / "tools" / "classslots"):
        file = candidate / "patch_class_slots.py"
        if file.is_file():
            spec = importlib.util.spec_from_file_location("patch_class_slots", file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ClientError("patch_class_slots.py was not found next to the admin screen")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _state(path, pristine_hash, patched_hashes):
    """missing | pristine | patched | unknown for one file."""
    if not path.is_file():
        return "missing"
    digest = sha256(path)
    if digest == pristine_hash:
        return "pristine"
    return "patched" if digest in patched_hashes else "unknown"


def _patched_hashes(root, patcher):
    """Hashes a patched game.dll / layout can have: the known native builds, plus what patching the saved .orig gives."""
    dll, layout = set(patcher.KNOWN_NATIVE_CLIENTS), set()
    for rel, kind in ((GAME_DLL, "dll"), (LAYOUT, "layout")):
        orig = root / (str(rel) + BACKUP)
        if not orig.is_file():
            continue
        data = orig.read_bytes()
        try:
            if kind == "dll":
                dll.add(hashlib.sha256(patcher.patch(data)[0]).hexdigest())
            else:
                layout.add(hashlib.sha256(patcher.patch_layout(data)).hexdigest())
        except ValueError:
            pass
    return dll, layout


def inspect(folder):
    """-> {"folder", "game": state, "layout": state, "backups": bool, "can_patch": bool, "message": str}"""
    root = Path(folder).expanduser()
    if not root.is_dir():
        return {"folder": str(root), "game": "missing", "layout": "missing", "backups": False, "can_patch": False,
                "message": "That folder does not exist."}
    patcher = _patcher()
    dll_hashes, layout_hashes = _patched_hashes(root, patcher)
    game = _state(root / GAME_DLL, patcher.SUPPORTED, dll_hashes)
    layout = _state(root / LAYOUT, patcher.LAYOUT_SUPPORTED, layout_hashes)
    backups = (root / (GAME_DLL + BACKUP)).is_file() and (root / (str(LAYOUT) + BACKUP)).is_file()
    if "missing" in (game, layout):
        message = "Not a DAoC client folder (game.dll or pregame/character_creation.xml is missing)."
    elif game == layout == "pristine":
        message = "Original 1.130 files" + (" (backups kept). Switch to patched to enable the extra classes." if backups else ". Ready to patch.")
    elif game == layout == "patched":
        message = "Already patched for the extra classes." + (" Backups are present." if backups else "")
    elif "unknown" in (game, layout):
        message = "Not the pristine 1.130 client (different version, or changed by something else). It will not be patched."
    else:
        message = "Half patched. Restore the backups first."
    return {"folder": str(root), "game": game, "layout": layout, "backups": backups,
            "can_patch": game == layout == "pristine", "message": message}


def patch_client(folder):
    """Patch game.dll and the creation layout in folder. Keeps <file>.orig. Refuses anything but the pristine pair."""
    info = inspect(folder)
    if not info["can_patch"]:
        raise ClientError(info["message"])
    root, patcher = Path(folder).expanduser(), _patcher()
    dll_path, layout_path = root / GAME_DLL, root / LAYOUT
    new_dll = patcher.patch(dll_path.read_bytes())[0]
    new_layout = patcher.patch_layout(layout_path.read_bytes())
    for p, data in ((dll_path, new_dll), (layout_path, new_layout)):
        if not Path(str(p) + BACKUP).exists():  # keep the first backup; it is the pristine file
            shutil.copy2(p, str(p) + BACKUP)
        tmp = Path(str(p) + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, p)
    after = inspect(folder)
    if not (after["game"] == after["layout"] == "patched"):
        raise ClientError("The patched files did not verify; use Restore.")
    return after


def restore_client(folder):
    root = Path(folder).expanduser()
    restored = []
    for rel in (GAME_DLL, LAYOUT):
        orig = root / (str(rel) + BACKUP)
        if orig.is_file():
            shutil.copy2(orig, root / rel)  # the .orig stays, so the patch can be switched back on
            restored.append(str(rel))
    if not restored:
        raise ClientError("There are no .orig backups in that folder (it was never patched).")
    return restored


# --- Battleground fix: the classic zone table -------------------------------------------------------------------------

ZONES = Path("zones") / "zones.mpk"
BGFIX_COPY = ".bgfix"  # the classic table is kept next to the file, so switching back on needs no source folder
LIVE_ZONES_SHA = "4f477c2cf99ffe718c11fb04633acff949cea7b691bfa1eb53dbc50b5a314758"     # retail 1.130 zones/zones.mpk
CLASSIC_ZONES_SHA = "aa72c53ac551827f1f7e1d125a182f10827c90ada2354c5497764ef5b5e346c2"  # classic OpenDAoC client zones/zones.mpk
CLASSIC_ZONES_FILE = "zones-classic.mpk"  # shipped in the server folder's tools/ (a copy of that file)


def bgfix_state(folder, live_sha=LIVE_ZONES_SHA, classic_sha=CLASSIC_ZONES_SHA):
    """missing | live (retail 1.130, battlegrounds kick you) | classic (battleground fix on) | other."""
    path = Path(folder).expanduser() / ZONES
    if not path.is_file():
        return "missing"
    digest = sha256(path)
    return "live" if digest == live_sha else "classic" if digest == classic_sha else "other"


def bgfix_on(folder, source_folder=None, live_sha=LIVE_ZONES_SHA, classic_sha=CLASSIC_ZONES_SHA, bundled=None):
    """Replace zones/zones.mpk with the classic table (keeps zones.mpk.orig). The classic file comes from the copy kept next to it, else from
    the copy shipped with the server (bundled), else from a classic OpenDAoC client folder. Only the retail file is replaced."""
    root = Path(folder).expanduser()
    state = bgfix_state(root, live_sha, classic_sha)
    if state == "classic":
        return state
    if state != "live":
        raise ClientError("zones/zones.mpk is " + ("missing." if state == "missing" else "not the retail 1.130 file, so it will not be replaced."))
    target = root / ZONES
    saved = Path(str(target) + BGFIX_COPY)
    if saved.is_file() and sha256(saved) == classic_sha:
        source = saved
    elif bundled and Path(bundled).is_file() and sha256(bundled) == classic_sha:
        source = Path(bundled)
    else:
        if not source_folder:
            raise ClientError("The classic zone table is missing from the server's tools folder. Enter a classic OpenDAoC client folder to take the file from.")
        source = Path(source_folder).expanduser() / ZONES
        if not source.is_file() or sha256(source) != classic_sha:
            raise ClientError("That folder has no classic zones/zones.mpk (wrong file or version).")
    orig = Path(str(target) + BACKUP)
    if not orig.exists():
        shutil.copy2(target, orig)
    if source != saved:
        shutil.copy2(source, saved)
    tmp = Path(str(target) + ".part")
    shutil.copy2(saved, tmp)
    os.replace(tmp, target)
    if bgfix_state(root, live_sha, classic_sha) != "classic":
        raise ClientError("The new zones.mpk did not verify; switch the battleground fix off to restore the original.")
    return "classic"


def bgfix_off(folder, live_sha=LIVE_ZONES_SHA, classic_sha=CLASSIC_ZONES_SHA):
    root = Path(folder).expanduser()
    target = root / ZONES
    orig = Path(str(target) + BACKUP)
    if not orig.is_file():
        raise ClientError("There is no zones.mpk.orig backup in that folder (the fix was never switched on).")
    if sha256(orig) != live_sha:
        raise ClientError("zones.mpk.orig is not the retail 1.130 file; restore it by hand.")
    shutil.copy2(orig, target)
    return bgfix_state(root, live_sha, classic_sha)


# --- launcher.bat: how the user starts the game client (the server never starts it) ---

CONNECTOR = "connect-local1130.exe"
LAUNCHER = "launcher.bat"


def launcher_text(server, account="", password="", connector=CONNECTOR):
    """Text of launcher.bat (CRLF). Blank account/password are asked for when the .bat runs, so nothing secret has to be stored."""
    if not re.fullmatch(r"[A-Za-z0-9.\-]+:\d{1,5}", server or ""):
        raise ClientError("Server: host:port, for example 127.0.0.1:10300.")
    if account and not re.fullmatch(r"[A-Za-z0-9_-]+", account):
        raise ClientError("Account: letters, numbers, underscore or dash only.")
    if password and re.search(r"[\s\"%^&|<>!]", password):
        raise ClientError("Password: no spaces, quotes or the characters % ^ & | < > !")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.exe", connector or ""):
        raise ClientError("Connector: the file name of a .exe in the client folder, for example connect-local1130.exe.")
    lines = ["@echo off", 'cd /d "%~dp0"']
    if account:
        lines.append(f"set DAOC_ACCOUNT={account}")
    else:
        lines.append("set /p DAOC_ACCOUNT=Account: ")
    if password:
        lines.append(f"set DAOC_PASSWORD={password}")
    else:
        lines.append("set /p DAOC_PASSWORD=Password: ")
    lines += [f'{connector} "game.dll" {server} %DAOC_ACCOUNT% %DAOC_PASSWORD%', "pause"]
    return "\r\n".join(lines) + "\r\n"


def write_launcher(folder, connector_source, server, account="", password="", connector=CONNECTOR):
    """Put launcher.bat (and, for the default connector, the connector) in the client folder. Overwrites an old launcher.bat, never an existing connector."""
    root = Path(folder).expanduser()
    if not (root / GAME_DLL).is_file():
        raise ClientError("That folder has no game.dll; it is not a DAoC client folder.")
    text = launcher_text(server, account, password, connector)
    target = root / connector
    if not target.exists():
        if connector != CONNECTOR or not Path(connector_source or "").is_file():
            raise ClientError(f"{connector} was not found in the client folder" + (" or the server folder (tools/)." if connector == CONNECTOR else "."))
        shutil.copy2(connector_source, target)
    (root / LAUNCHER).write_bytes(text.encode("ascii"))
    return root / LAUNCHER


# --- the remembered client path (config lives next to the server, never in the user's home) ---

def _config_file(home):
    return Path(home) / "config" / "client.json"


def load_settings(home):
    try:
        return json.loads(_config_file(home).read_text())
    except (OSError, ValueError):
        return {}


def save_settings(home, settings):
    f = _config_file(home)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(settings, indent=2))
