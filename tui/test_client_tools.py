"""Test the client helpers on a scratch copy of just the two client files (the real client is only read).
Run: python/bin/python3 -I tui/test_client_tools.py [path to a pristine 1.130 client folder]
Skips (exit 0) when no client folder is given or found; never modifies the client folder itself."""
import os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client_tools as c

BOTTLE = Path.home() / ".var/app/com.usebottles.bottles/data/bottles/bottles/dad_daoc/drive_c/Program Files (x86)/Electronic Arts/Dark Age of Camelot"
src = Path(sys.argv[1]) if len(sys.argv) > 1 else BOTTLE
if not (src / c.GAME_DLL).is_file():
    print("SKIP: no client folder"); sys.exit(0)
tmp = Path(tempfile.mkdtemp())
try:
    work = tmp / "client"
    (work / "pregame").mkdir(parents=True)
    def original(rel):  # a client that is currently patched keeps its pristine files as .orig
        orig = src / (str(rel) + c.BACKUP)
        return orig if orig.is_file() else src / rel
    shutil.copy2(original(c.GAME_DLL), work / c.GAME_DLL)
    shutil.copy2(original(c.LAYOUT), work / c.LAYOUT)
    info = c.inspect(work)
    assert info["can_patch"], info
    info = c.patch_client(work)
    assert info["game"] == info["layout"] == "patched" and info["backups"], info
    try:
        c.patch_client(work); raise SystemExit("double patch was allowed")
    except c.ClientError:
        pass
    assert c.restore_client(work) == ["game.dll", "pregame/character_creation.xml"]
    info = c.inspect(work)
    assert info["can_patch"] and info["backups"] and info["game"] == "pristine", info
    assert c.inspect(work)["game"] == "pristine"
    c.patch_client(work)  # switch back on without the original client
    assert c.inspect(work)["game"] == "patched"
    c.restore_client(work)
    assert c.sha256(work / c.GAME_DLL) == c.sha256(original(c.GAME_DLL))
    (work / c.GAME_DLL).write_bytes(b"x" * 10)
    assert not c.inspect(work)["can_patch"] and c.inspect(work)["game"] == "unknown"
    text = c.launcher_text("127.0.0.1:10300", "bob", "pw1")
    assert text == '@echo off\r\ncd /d "%~dp0"\r\nset DAOC_ACCOUNT=bob\r\nset DAOC_PASSWORD=pw1\r\nconnect-local1130.exe "game.dll" 127.0.0.1:10300 %DAOC_ACCOUNT% %DAOC_PASSWORD%\r\npause\r\n', text
    asked = c.launcher_text("10.0.0.5:10300")
    assert "set /p DAOC_ACCOUNT=" in asked and "set /p DAOC_PASSWORD=" in asked
    for args in (("bad server",), ("127.0.0.1:1", "bob smith"), ("127.0.0.1:1", "bob", 'p"w'), ("127.0.0.1:1", "bob", "p%w")):
        try:
            c.launcher_text(*args); raise SystemExit(f"accepted {args}")
        except c.ClientError:
            pass
    assert "connect.exe \"game.dll\"" in c.launcher_text("127.0.0.1:10350", "bob", "pw1", "connect.exe")
    try:
        c.launcher_text("127.0.0.1:1", "bob", "pw1", "bad name.exe"); raise SystemExit("bad connector name accepted")
    except c.ClientError:
        pass
    fake_connector = tmp / "connect-local1130.exe"; fake_connector.write_bytes(b"MZ")
    made = c.write_launcher(work, fake_connector, "127.0.0.1:10300", "bob")
    assert made.read_bytes().startswith(b"@echo off\r\n") and (work / c.CONNECTOR).read_bytes() == b"MZ"
    c.save_settings(tmp, {"client": str(work)}); assert c.load_settings(tmp)["client"] == str(work)
    # --- battleground fix, with small stand-in files (hashes passed in)
    import hashlib
    live_bytes, classic_bytes = b"live-table", b"classic-table"
    LIVE, CLASSIC = hashlib.sha256(live_bytes).hexdigest(), hashlib.sha256(classic_bytes).hexdigest()
    cli, src2 = tmp / "cli", tmp / "classic-client"
    (cli / "zones").mkdir(parents=True); (src2 / "zones").mkdir(parents=True)
    (cli / c.ZONES).write_bytes(live_bytes); (src2 / c.ZONES).write_bytes(classic_bytes)
    assert c.bgfix_state(cli, LIVE, CLASSIC) == "live" and c.bgfix_state(tmp / "nope", LIVE, CLASSIC) == "missing"
    try:
        c.bgfix_on(cli, None, LIVE, CLASSIC); raise SystemExit("switched on without a source")
    except c.ClientError:
        pass
    (src2 / c.ZONES).write_bytes(b"wrong")
    try:
        c.bgfix_on(cli, src2, LIVE, CLASSIC); raise SystemExit("accepted a wrong source file")
    except c.ClientError:
        pass
    (src2 / c.ZONES).write_bytes(classic_bytes)
    assert c.bgfix_on(cli, src2, LIVE, CLASSIC) == "classic" and (cli / c.ZONES).read_bytes() == classic_bytes
    assert (cli / (str(c.ZONES) + ".orig")).read_bytes() == live_bytes
    assert c.bgfix_off(cli, LIVE, CLASSIC) == "live" and (cli / c.ZONES).read_bytes() == live_bytes
    assert c.bgfix_on(cli, None, LIVE, CLASSIC) == "classic", "switching back on must not need the source folder"
    (cli / c.ZONES).write_bytes(b"something else")
    try:
        c.bgfix_on(cli, src2, LIVE, CLASSIC); raise SystemExit("replaced a file that is not the retail one")
    except c.ClientError:
        pass
    print("OK client tools")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
