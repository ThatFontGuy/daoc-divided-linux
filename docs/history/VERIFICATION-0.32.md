# v0.32 Darkness Falls Beta verification

This page records what can be claimed for the **normal** v0.32 release. Keep
package checks, source tests, and actual client gameplay separate. Do not
reuse v0.31 test counts as v0.32 results.

## September 28 shared stability source checks

- The isolated normal Release server build completed with zero errors. The
  complete server suite passed **2,115/2,115** tests. `git diff --check`
  passed for the changed server source. A source scan found no Sluaghbinder
  references in normal GameServer or Tests code.
- These checks cover the current Savage, dungeon, meetup, frontier, merchant,
  helmet, companion-speed, and Darkness Falls exterior-route changes. They
  do not establish live bot outcome rates or a long Darkness Falls run.
- The three portal visuals are client-side map assets. Their in-client
  appearance and travel behavior are not proven by the server test suite.
- Package ZIP checks and final artifact hashes are recorded with the
  release assets, not inferred from this source test.

## Follow-up maintenance evidence

- The class-neutral follow-up source is staged against the normal v0.32
  branch, with no Sluaghbinder pet-spell code or client assets introduced.
  `git diff --check` passed, and 38 focused Darkness Falls, bounty, group
  recovery, and synthetic-charm lifecycle tests passed with zero failures.
- The full refreshed normal server suite passed **2,065/2,065**. The unchanged
  normal launcher source passed **97/97** tests. The matching tested
  `GameServer.dll` SHA-256 is
  `51156A6B8B649ACCACF0CC6176AEAAAA42D69C8AFA8439A72323E5DDBE7B80FC`
  in all three staged server locations.
- The updated clean public database passed SQLite `quick_check` and the
  public v0.32 world preflight. It contains only the narrow world-data delta
  below, not the author's account or save database.
- The intended world-data delta is narrow: nine additional level-10
  empyrean orbs near the Lough Derg camp, seven additional level-14 sneezers
  near the Domnann camp, and the insidious cniogcrag template plus one spawn
  changed from the invisible model choice to visible model 769. The author's
  live database must not be substituted for the clean release database.
- The source includes a guarded world-data script for this delta. Applied to
  a disposable copy of the previous clean v0.32 database, it produced the
  exact same Mob and NpcTemplate rows as the refreshed playable database;
  a second run changed zero rows.
- A disposable complete v0.32 installation accepted the refreshed normal
  update files. Its installed server DLL matched the tested SHA-256 above.
  The refreshed v0.32b patch then installed in a separate sibling copy;
  that install and rollback are described in the optional verification page.
- In-client confirmation is still outstanding for the new spawn density,
  cniogcrag visibility, nonrepeating bounty assignments, interrupted-charm
  cleanup, and a longer all-realm Darkness Falls bot run.

## Implementation evidence

- The server contains Darkness Falls entrance and realm-access checks, a
  shared-combat-dungeon policy for region 249, local opposing-realm PvP
  eligibility, and autonomous dungeon route and camp selection.
- The source has focused Darkness Falls policy tests for entrance authority,
  region edges, local PvP, and timed PvE assignments. These tests exercise
  policy decisions; they do not prove that bots finish a live route.
- The normal release must be checked for absence of Sluaghbinder class code,
  quests, patch tool, and optional client assets before the source or playable
  package is published.

## Earlier beta-maintenance package checks

The figures and hashes in this section describe the previously published
2026-09-26 beta-maintenance assets, not the refreshed files above.

- Isolated normal Release server build: successful, zero errors.
- Full normal server suite after the beta maintenance fixes: **2,051/2,051**
  passed. The earlier focused bot-combat regression subset: **57/57** passed.
- Normal launcher tests: **97/97** passed. The launcher displays 0.32.
- The staged public world database has no accounts, characters, inventory,
  or bot profiles. Its Darkness Falls rows, exit and seal-vendor settings,
  normal beach-rat camp, and 85 excluded raid NPCs passed the release-data
  verifier. This is a database check, not a live bot result.
- The normal server DLL's SHA-256 is
  `73C36868E4565B4D12D48D2FEB69FDC5E7A21A5D5856760CF8B0C50F8F82F171`.
  The same DLL hash is in all three staged runtime server locations.
- The 2026-09-26 hotfix update ZIP passed a full 3,739-entry CRC check; its
  entries match every staged file path and byte count. The source ZIP passed
  a full 4,129-entry CRC check and its changed files match the checkout.
  The manifest byte count and SHA-256 match the update archive. Neither ZIP
  contains Sluaghbinder class code or optional assets.
- A separate clean v0.32 base accepted the hotfix staging overlay and all
  three installed server DLL copies matched the tested Release DLL hash.
  The original local installation and earlier release assets were not modified.

Compare the published update ZIP and source ZIP against the release's
`SHA256SUMS.txt` and `download-manifest.json` before installing. The helper's
retry/path guards were syntax-checked and exercised in isolation for the
earlier release; a complete network downloader run and relocated in-client
launch for this hotfix were **not** performed.
These checks do **not** establish a long live autonomous Darkness Falls run.

## Live gameplay limits

The owner has not yet completed a long live bot test in Darkness Falls.
Darkness Falls raid AI is not implemented. Legion, the hardest level-70+
encounters, unreachable flying targets, and unverified routes/monsters are
excluded from ordinary autonomous bot goals.
Static navigation checks, policy tests, build success, and file hashes cannot
substitute for a live all-realm dungeon run. Please report reproducible bot
failures with the version, realm, location, and relevant log details; never
publish an account file or progress database to do so.

For historical verification records, see [v0.31](VERIFICATION.md) and
[v0.31b](VERIFICATION-0.31B.md). Their counts apply only to those builds.
