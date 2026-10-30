# Original retail client 1.130 compatibility test

Update: the client is now copied into the private test package and patched for
Stormforged. See [bundled client and custom-class patch notes](MODERN-CUSTOM-CLIENT.md).
The external-client and unpatched-client descriptions below record the earlier setup.

Expansion races are now enabled with their normal class choices in this test;
see [modern race setup and verification](MODERN-RACES.md).

October 21, 2026. This concerns the original modern DAoC game client, not the Godot client.

The previous Desktop/OpenDAoC project demonstrated login to character selection with an identified 1.130 client and derived connector. This source tree now registers Version1130/PacketLib1130, inheriting 1129 packet writers as that project did. Three focused registration tests pass. Existing dirty gameplay changes were preserved and are included in the development build; they are not part of this protocol change. No full-game compatibility claim follows from registration.

## Isolated staging

Modern creation behavior: the test database sets startup/start_as_base_class=False, so new characters keep their selected advanced class at level 1. The existing StartAsBaseClass event returns without downgrading them. This does not promote existing characters, unlock disabled classes/races, or modernize early-level skill/equipment progression. Restart the test server after changing the setting. The original setting is recorded privately in start-as-base-class-previous.json. Classic/Stormforged installs and the source default remain unchanged.

Private folder: `Source/artifacts/modern-client-test` (ignored by Git).

- TCP 127.0.0.1:10330; UDP/region 127.0.0.1:10430; UPnP disabled.
- Independent SQLite database copied read-only from Classic and cleaned using the existing release clean_world policy. Saved accounts/characters/inventories/bots cleared; original databases unchanged. Zero initial bot population. Custom Sluaghbinder creation disabled for the unmodified retail client.
- Development server binaries staged separately; no Classic/Stormforged binaries replaced.
- Navigation junction references the Classic assets for reads; no navigation modifications planned.
- Existing OpenDAoC modern client is reused without binary edits. The new launcher verifies game.dll SHA256 3915A495253040A4CDFC79D265A8D268797304EB46B9A34D51A88D49A8445022 and connector SHA256 18AB2F8A95BE682E0F6ACBBB6C7332E9EF05F1586872626F63A3122782F6BA70. Client settings may follow that existing client's normal behavior. Credentials are requested interactively and not saved by the script; the legacy helper receives them as process arguments.

## Manual test, once startup is authorized

Latest launcher update: the root `START MODERN CLIENT TEST.exe` now opens the full Offline DAoC launcher staged at `artifacts/modern-client-test/runtime/OfflineDAoC.exe`. It uses the normal dashboard, bot controls, settings, local-account bootstrap, Start/Stop and Enter Realm workflow. An opt-in `modern-client.json` profile directs only this test installation to its hash-verified modern client/helper and port 10330. Normal releases without that profile retain their previous behavior, including Godot mode.

This full launcher stores its local account in the test runtime's account.txt through the normal PortableCredentials mechanism. It never reads the Classic/Stormforged account files. Earlier manually entered test accounts/characters remain in the test database; if a different account was used, its characters will not appear under the automatically generated offline account. To use that existing test account, edit only the private test runtime account.txt locally; do not share its credentials.

Full launcher verification: 112 launcher tests passed (five new modern-profile cases). Packaged profile verification passed without starting a server/client. Initial sandboxed test hosts failed to connect; elevated test execution completed. User reports entering the world with the previous minimal launcher; the new full-launcher interactive workflow and its modern-client management functions still need in-game acceptance. The existing development server binaries/data were not changed by this launcher update.

Double-click `START MODERN CLIENT TEST.exe` in the DAoC Offline workspace, then use START SERVER and ENTER REALM in the full dashboard. Keep the root EXE in place so it finds the prepared test folder. The earlier minimal account/password window is retained only as a bootstrap fallback if the full launcher is absent; its memory-only credentials behavior does not describe the full launcher's saved account workflow.

Launcher source: `source/tools/OfflineDaoc.ModernClientLauncher/`. Publish as a framework-dependent single-file win-x64 EXE using the installed .NET 10 Desktop Runtime. Packaged `--verify` check passed: validates isolated configuration and exact client/helper hashes without starting server or client. The interactive screen and actual login have not been exercised here.

1. Run `Start-Test-Server.ps1` in the private folder. Its console runs only the staged server; wait for startup completion.
2. Run `Launch-Modern-Client.ps1`. Enter a disposable new local test account.
3. Check login/realm selection, character creation on each realm, world entry, movement and UDP updates, inventory/equipment, spells/abilities, zoning and relog persistence. Start with ordinary existing classes, not expansion enablement.
4. Record the first failed state and corresponding server packet/error, without sharing credentials or private saves. Fix confirmed protocol differences in PacketLib1130 or appropriately versioned incoming handlers; preserve old clients.

Neither script has been launched during preparation. An existing other server is not stopped. No startup/deployment authorization is assumed from source preparation. Stop only the staged process after tests, through its console's normal shutdown mechanism.

## Verification

`dotnet test Tests/Tests.csproj -c Release --filter FullyQualifiedName~UT_ModernClientPacketRegistration --no-restore -m:1`: 3 passed. Build completed with existing warnings. Tests cover unique 1129/1130 concrete registrations, instantiation and absence of uninvestigated 1131 registration. They do not establish handshake/world-entry success here.

Staging initially hit a VACUUM-in-transaction error; the script was corrected to commit first and staging was completed. Source/refreshed packet registration, sanitized table counts, loopback configuration and helper hashes were checked. No server startup or client launch has occurred in this folder yet.

## Stormforged in the modern test world

October 21, 2026. `source/tools/stormforged/seed_stormforged.py --apply` was run against the stopped test database only (backup beside it: `opendaoc.sqlite3.db.before-stormforged-20261021-163622.bak`). It set `enable_stormforged=True`, added the 172 Stormforged spells, class-64 specializations, pet templates, the Stormkeeper trainer beside Frode in Jordheim, and class-64 copies of the Thane start locations (MinVersion 0, so the 1.130 client uses them). Existing test characters were not changed. The staged GameServer.dll already matched the current Release build, so no server files were replaced. Classic/Stormforged installs are unchanged.

The 1.130 client is not patched, so Stormforged appears under its native Midgard **Mauler** slot and is labelled Mauler in the client's creation screen; the server converts it to class 64 on creation, exactly as in the classic Stormforged build. Disabled-class 61 stays disabled for ordinary Maulers; the check runs after the conversion to 64.

Races: the server now accepts Stormforged for every Midgard race, and skips the disabled-race list for it only (Deifrang is disabled for everything else). A class-64 any-race start row (the Norseman Thane spot) places Kobold, Valkyn, Frostalf and Deifrang; Norseman, Troll and Dwarf keep their own Thane spots. The unmodified client still decides which races it shows Mauler for (retail: Kobold, Deifrang, Norseman), so Troll, Dwarf, Valkyn and Frostalf may not be selectable in this client even though the server would accept them. The new GameServer.dll was staged to all three server folders with a backup under `backups/gameserver-before-stormforged-races-20261021-163901`, and the seed re-applied (backup `opendaoc.sqlite3.db.before-stormforged-20261021-163902.bak`).

Restart the test server after seeding. Use the Stormforged acceptance list in STORMFORGED.md. Hotbar spell addressing (line + level) has only been exercised with the classic client.
