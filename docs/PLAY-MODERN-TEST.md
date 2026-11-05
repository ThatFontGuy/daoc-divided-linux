# Playing the modern test (original 1.130 client)

The modern test is Divided Realms for the **original retail 1.130 client**. It includes the live 1.130a class work, the
expansion and royal classes, Master and Champion Levels and the other changes in
[PROGRESS-2026-10.md](PROGRESS-2026-10.md). It is a development test build.

The download contains **no game client**. You use your own Dark Age of Camelot install.

## What you need
- **Your client:** Dark Age of Camelot installed, at the **1.130** client version. The setup checks your `game.dll`
  and accepts only the 1.130 build this game is made for (SHA256 `3915a495…`). A newer or modified client is refused
  and nothing is changed.
- **.NET Framework 3.5:** the Windows feature, for the client's connector. Turn it on in Control Panel → Programs →
  Turn Windows features on or off. The game's own .NET runtime is included.
- **Disk:** about 7 GB free where you extract the game, since your client is copied into it.

## First start
1. Extract the whole download, then double-click **START DIVIDED REALMS.cmd**.
2. The launcher asks you to set up your client. Choose your Dark Age of Camelot folder: the one with `game.dll` and
   `camelot.exe`.
3. It copies the client into `runtime/client-modern/app` and patches the copy. The patch changes three files:
   - `game.dll`: native class slots for the custom and expansion classes.
   - `pregame/character_creation.xml`: room for the extra class buttons.
   - `pregame/splash.mpk`: the Divided Realms loading screen.

   **Your own install is not changed**, so you can still play live with it. Your login and logs aren't copied.
4. **START SERVER**, then **ENTER REALM**. The server creates your account on the first login.

If the setup is cancelled or fails, nothing is set up. It asks again on the next start, or when you press ENTER REALM.

## Notes
- **Ports:** the server listens only on this computer, on port 10330.
- **Saves:** your characters and bots are saved in `runtime/data`. To move to a new version of this test, keep that
  folder, or use the progress importer once one ships for this edition.
- **Patch file:** the client patch is `runtime/client-patch.json`, made by `source/tools/make_client_patch.py` from the
  class-slot patch `source/tools/classslots/patch_class_slots.py`. It holds this project's changes, plus the two small
  Marfach Caverns zone files that the 1.130 client lacks. No other Broadsword file is in the download.
