# Expansion races in the modern test

All 21 realm race IDs are now available in the private modern test. This includes
Half-Ogre, Frostalf, Shar, and each realm's Minotaur (Korazh, Deifrang, Graoch).
Use `START MODERN CLIENT TEST.exe`, start the server and create a character.
Existing class restrictions remain: this does not enable unfinished expansion
classes or allow every race to play every class. Minotaurs remain male-only.

The current bundled client already contains the race models and creation lists;
no further client binary changes were needed. Stormforged keeps its patched
seven-race choice. The server now accepts expansion-race choices observed in the
original 1.130 client, through the opt-in `classes/enable_modern_races` setting.
The setting defaults to False and is enabled only in the modern test database.
Classic/Stormforged installs have not been updated.

## Changes

- Restored the six expansion-race starting-stat entries, matching the existing
  `RaceStats` definitions. Stat point validation is retained.
- Added a player-creation-only allowance for native expansion-race/class pairs.
  Realm checks, class disables and gender checks remain in force. Bot population
  and companion class/race generation were not expanded.
- Removed the supported expansion race IDs from `disabled_races` in the private
  test database. Existing saved characters were not edited.
- Added 33 race/class starting-location rows, using that class's existing starting
  coordinates in its own realm. These are existing-world starts, not a retail
  tutorial reconstruction.

The shared source data is `source/server/GameServer/gameutils/modern-races-1130.json`.
It is embedded in GameServer.dll and used by the data migration. It comes from
static REA/Ghidra inspection of pristine game.dll SHA256
`3915a495253040a4cdfc79d265a8d268797304eb46b9a34d51a88d49a8445022`.
Evidence IDs: Albion `ev_407a2011838ba6d077e441817cdd9a7b3af0ad873236c412aa2bf9c5315b6205`,
Midgard `ev_4992ce685f9b391f68b9dc97ca450c2326e27abc10a9a8d5e1577fda56a36173`,
Hibernia `ev_fbea3ee9cbca5029c5f2a28a274218d6142da077079c68be3b953170056fd3b9`.
The retained private pseudocode records are under `artifacts/`.

## Reapply and rollback

With the test server stopped, preview with:

```powershell
python source/tools/enable_modern_races.py
```

Use `--apply` to make a consistent private database backup and apply the migration.
Reapplying does not duplicate locations. A matching tested server build must be
installed in the test runtime's three GameServer.dll locations.

Private reports: `artifacts/modern-client-test/modern-races-report.json` and
`modern-races-deployment.json`. They identify the pre-change database and binary
backups. To restrict new creation again without losing later progress, set
`enable_modern_races=False` and restore the previous `disabled_races` value from
the report, then restart. Avoid restoring an entire old database after further
play, because that would discard newer progress.

## Verification

170 focused tests passed, including creation validation for all 33 newly allowed
race/class pairs among enabled classes; each expansion race; classic-profile
restrictions; wrong-realm, invalid class/race, gender and stat-budget rejections;
Valkyrie creation and Stormforged regressions. The migration was previewed in
memory and verified idempotent. All three installed server DLLs match the tested
build. No server or client was started during this work.

Actual creation, models, entry into the world, starter equipment and relog remain
in-game checks. Try a Half-Ogre Armsman, Shar Hero and a Minotaur in each realm,
plus a Frostalf caster. This unlock does not claim complete progression for
disabled/unfinished classes.
