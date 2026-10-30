# Valkyrie first play test — Offline DAoC modern sandbox

October 21, 2026. Player-only level-one development slice. This is not complete retail progression or bot support. Classic/Stormforged installs are unchanged.

Superseded in part by [VALKYRIE-PROGRESSION.md](VALKYRIE-PROGRESSION.md): the temporary test line has been replaced by nine native Odin's Will damage ranks, duplicate prototype heal wiring removed, and a trainer added in Mularn. Starter creation/equipment restrictions and incomplete full-kit status still apply. Follow the progression report for current test instructions.

## Try it

Use START MODERN CLIENT TEST.exe, start the server and create a **female Norse Valkyrie**, level 1, with default attributes first. Dwarf, Frostalf and Valkyn are also enabled. Test entering the world, starter sword/shield/armor, Whirling Blade, Odin's Heel and Minor Mending. The test spell line is labelled Valkyrie Test Spells. Heal is also present through the existing Mending baseline.

Odin's Heel: instant, 5 Spirit damage, 1500 range, 1 power, 20-second reuse. Check a valid hostile nearby target, cooldown, self-healing, death/release if desired, and relog persistence. Report the first failure. Existing characters were not converted. Do not treat higher-level leveling as a complete kit test yet.

## Implementation

- New source property classes/enable_valkyrie_test defaults False. It enables the four explicit race declarations only when True; original creation rules otherwise remain in place. Female-only, realm and stat validation retained.
- Test database removes only class 34 from disabled classes and race 17 (Frostalf) from disabled races. Other expansion-class restrictions remain. Frostalf availability is a realm-wide race restriction, so it is not technically scoped to Valkyrie alone; other classes still enforce their own race lists.
- Added class-specific level-one sword/spear/staff, studded armor and small-shield permissions. Starter templates already include class 34 and were reused, not replaced.
- Added one sword style from the existing Whirling Blade definition (class 34, level 1); no higher styles/procs claimed.
- Isolated baseline test line links new spell 64990 (Odin's Heel) and existing 3001 (Minor Mending). Spell ID collision is checked. The icon/client effect is copied from an existing Midgard spell and is not authenticated retail art. Spirit damage is explicitly encoded as 15, correcting the old OpenDAoC prototype's borrowed Energy type.
- Added a class-34 1.130 starting-location fallback using existing Norse Warrior coordinates in region 100. It is a test start, not a modern tutorial reconstruction.
- Existing Odin's Will/Mending specialization definitions remain; missing full spell/style progression, armor/shield upgrades, trainer placement, RAs, ML/CL and bot builds are not supplied by this slice.

Original prototype reused as a reference: Desktop/OpenDAoC/tools/valkyrie-level1.sql and docs/VALKYRIE-PLAYTEST.md. SQLite schema adaptation is in source/tools/enable_valkyrie_test.py; it refuses an occupied test port, makes a private consistent database backup, applies changes transactionally and uses idempotent keys. No accounts/characters/inventories are edited. Do not restore the whole backup after further play without preserving newer saves.

## Evidence and verification

[Official class reference](https://www.darkageofcamelot.com/class-library-valkyrie/) supports the level-one sword style and starter instant attack; it is undated, not a frozen complete modern kit. Valkyn eligibility follows the previously researched 1.125 live addition.

11 focused tests passed: eight Valkyrie eligibility/creation cases and three modern-client registration cases. Data migration applied and reapplied without duplicate test links or career grants; starter references and startup location checked. Updated development DLLs staged to all three locations with backups while port 10330 was unused. No server was started or gameplay executed during preparation. Actual player creation, combat, equipment and relog remain user acceptance checks.
