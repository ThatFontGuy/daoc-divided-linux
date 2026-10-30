# DAoC Divided (portable Linux server)

A self-contained [DividedRealms](https://github.com/rambodolphin13/DividedRealms) server for Linux. It needs no .NET install and
includes no game client. Unpack it anywhere: a normal Linux system, or a distrobox if your system is read-only (like SteamOS).

Requirements: x86-64 Linux with glibc 2.34 or newer (Ubuntu 22.04+, Debian 12+, Fedora 35+, SteamOS) and `libicu` (nearly every desktop
distro has it). Play with the original retail **1.130** client.

**Everything stays in this folder.** Config (`config/`), the world and all characters (`data/`), logs and runtime files live next to
the program. Nothing is written to `~/.config` or elsewhere in your home. Moving the folder is safe while the server is stopped.

## Run and manage it

```bash
./daoc-server.sh start
```

Starts the server in the background and opens the admin screen. First start creates the world (`data/opendaoc.sqlite3.db`) and the
config files from `defaults/`. Tabs:

- **Server**: status, Start / Stop / Restart. **Bots** / **Population**: create and delete bots, switch the population on/off.
- **Accounts**: create accounts, set player / GM / admin. **Options**, **Server Rules**: switches and XP / RP / BP / money / regen rates.
- **RvR**, **Console**: battlegrounds, keeps and relics; live server output.
- **Client**: patch your client and create `launcher.bat` (below).

**Ctrl+Q** closes the screen and asks whether to stop the server (it saves first) or leave it running. Reopen it with `./daoc-admin`.
Closing the terminal does not stop the server. The same actions work as commands:

```bash
./daoc-admin help
./daoc-admin bots create --realm all --count 10
./daoc-admin accounts set-role <account> admin       # or gm / player
./daoc-admin server stop                             # or: ./daoc-server.sh stop
./daoc-server.sh status
```

`./daoc-server.sh start --console` gives the raw console in the foreground; `--detach` starts it without the admin screen. Logs:
`logs/console.out` and `logs/server.log`. The admin tools use `run/admin.sock` and open no network port.

## Connect with the client

The server never starts the game. On the **Client** tab:

1. Enter your client folder (it must be a folder your terminal can see, e.g. inside your Wine prefix).
2. **Create launcher.bat** writes `launcher.bat` and `connect-local1130.exe` there. Leave account/password blank to be asked each time.
   Run `launcher.bat` with your own Wine setup (`wine launcher.bat`, Lutris, Steam, Bottles...). It connects to the server address
   from `config/serverconfig.xml` (default `127.0.0.1:10300`).
3. Accounts are created on first login, or with `./daoc-admin accounts create <name> <password>`.

For other machines on your network set `<RegionIP>` in `config/serverconfig.xml` to this machine's LAN address (or your public address
when port-forwarding TCP 10300 and UDP 10400), and put that address in the Client tab's server field.

### Battleground fix (needed for battlegrounds)

Without it, entering a battleground sends you to the login screen. On the Client tab, **Switch battleground fix on** replaces only `zones/zones.mpk` with the classic zone table
(the classic table ships in this folder's `tools/`; no other client is needed); the original is kept as `zones.mpk.orig`, and switching it off puts it back.

### Extra classes (optional client patch)

The six expansion classes (Vampiir, Bainshee, Heretic, Valkyrie, Warlock, Mauler) work on the stock client. DividedRealms' extra classes
(Death Knight, the Sovereigns, Stormforged) need a patched client: on the Client tab, **Switch to patched** changes only `game.dll` and
`pregame/character_creation.xml`, keeping `.orig` backups; **Switch to original** puts the originals back. No copy of the client is made.
It refuses anything but the pristine 1.130 files. Those classes are also off on the server until enabled in its settings.

## World Workshop editor

```bash
./daoc-server.sh stop
./world-editor.sh --client "/path/to/Dark Age of Camelot"    # remembered in config/client.json afterwards
```

A browser editor for NPCs, items, merchants, loot, spells, quests and settings, on `127.0.0.1` only. It reads the 3D art directly from your client
folder; its backups and caches go to `editor-data/`. Stop the server first, because the editor saves into the world database. The collision-floor
feature needs a Windows tool and is not available.

## Upgrading

Extract the new build **over** this folder. It contains no `data/` or `config/`, so your world, characters and settings are kept; only the
program files are replaced. On the next start the server sees the existing `data/opendaoc.sqlite3.db`, backs it up to
`backups/world-update-<version>-<time>/` and applies the new release's content changes (each step once; rows that play has changed are
left alone). `./daoc-server.sh world-update --check` shows what is pending. If you extract into a new folder, copy the old `data/` and
`config/` across first.

## Layout

```
bin/        the server (self-contained .NET) and daoc-admin     config/   serverconfig.xml, logconfig.xml, admins.json
data/       the world and all characters (back this up)         logs/     server logs
navmesh/    pathing meshes for NPCs and bots                    defaults/ templates copied into config/ and data/ on first start
python/ tui/ tools/   admin screen, connector, world updater        run/      pid file and admin socket
editor/ editor-data/  the World Workshop editor and its saves        backups/  world backups made before updates
```
