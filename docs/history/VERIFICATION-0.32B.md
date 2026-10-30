# v0.32b Darkness Falls Beta verification

This page is for the optional Sluaghbinder source and package. The normal
v0.32 verification record is [separate](VERIFICATION-0.32.md).

## September 28 isolated source checks

- The optional Release GameServer build completed with zero errors, and
  **2,130/2,130** server tests passed in the staged source checkout.
- The staged optional `GameServer.dll` SHA-256 is
  `1573A706C28E677F6342DCEAC2E4636F89D16EA2F6B8456AC64B1555E7611553`.
  This identifies the new build, not the previous September 26 package.
- These checks cover the current shared bot-routing, grouping, economy,
  helmet, and companion-speed source plus Sluaghbinder. They do not by
  themselves establish a packaged-install check or a long live gameplay run.

## Previous September 26 isolated source checks

- The refreshed optional Release server build completed with zero errors.
  Its broader suite passed **2,072/2,072** tests, excluding five known
  player-charm menu tests whose isolated harness lacks an initialized server
  database. The optional server DLL SHA-256 is
  `C00B2C49EE46602050D7913D4CAC89A2441CA72C7336D02BA0B625A3EE11F8EC`
  in the staged optional patch's three runtime locations.
- The optional launcher tests passed **96/96**; its displayed version is 0.32b.
- The current optional patch manifest seals against the refreshed normal
  v0.32 server hash. The shared clean world passed SQLite `quick_check`
  and public-world preflight; no live account, character, or bot save database
  was used as a release base.
- A focused check covered **24 non-Darkness Falls dungeon route regions**;
  it passed. That protects the unrelated route catalog against the new
  Darkness Falls policy in the tested source.

## Previous September 26 refreshed package install and rollback

The checks below apply to the older September 26 refresh. They do not verify
the September 28 ZIP merely because the version number remains v0.32b.

- A disposable complete normal v0.32 folder accepted the refreshed normal
  update. The refreshed optional patch verified that base and installed into
  a separate sibling copy; the original base server DLL stayed at SHA-256
  `51156A6B8B649ACCACF0CC6176AEAAAA42D69C8AFA8439A72323E5DDBE7B80FC`.
- The optional copy used the tested optional server DLL SHA-256 above. Its
  clean database passed SQLite `quick_check`, kept the ten-orb camp, and
  contained Sluaghbinder specializations. Running the supplied rollback on
  that copy restored the normal server DLL, removed the class rows, and
  passed SQLite `quick_check` again. The normal sibling was not changed.
- The source world-data script applied to a disposable copy of the previous
  clean v0.32 database produced precisely the refreshed Mob and NpcTemplate
  rows; repeating it made zero further changes. No server or client was
  launched for this smoke test, so in-game behavior remains unverified.

## Earlier disposable package install and rollback

The figures in this section describe the **first September 26 maintenance
package**, not the refreshed patch. They remain as historical evidence and
must not be read as a live or install test of the newest archive.

- The September 26 patch was sealed against a complete, clean normal v0.32
  installation with the new Bard/Oro/Bounty fixes. Its manifest records the
  exact normal launcher/server hashes and **74 optional payload files**.
- The exact patch ZIP installed into a new sibling copy. All **79/79** file
  receipts matched after installation; all **80** checked base fingerprints
  (including the database and game/documentation files) remained unchanged.
  The optional database passed SQLite `quick_check` and contained nine class
  specializations, seven pet templates, 39 styles, and 89 class spells. The
  private Dullahan and Zombie Defender NIFs were present. The normal base
  retained its original launcher and server hashes.
- Rollback of that disposable optional copy restored **79/79** receipts with
  no hash mismatches, removed all **18** patch-created files, and restored
  the database byte-for-byte to its original SHA-256. An earlier exploratory
  run overlapped a documentation update to the disposable normal copy; the
  final clean run above had no such overlap or mismatch.
- The Windows PowerShell 5.1 installer, manifest sealer, and rollback were
  checked with extended paths so deeply nested Desktop folders work.

The earlier staged optional launcher DLL SHA-256 was
`49011B42074292CFCE2084827CFF2429525F2FFD449FF017C32C929136216812`;
the earlier optional server DLL SHA-256 was
`BBE31AA4409FD8C44C17ECEB7DDCDCC8D1EB5D449BE6774859AD860F7A83D3D7`.
The release manifest and `SHA256SUMS.txt` identify the final uploaded ZIPs.
These package checks do **not** establish a successful in-client launch or a
long live autonomous Darkness Falls run.

## Live gameplay limits

The owner has not yet completed a long live bot test in Darkness Falls.
Darkness Falls raid AI is not implemented. Legion, the hardest level-70+
encounters, unreachable flying targets, and unverified content are excluded
from ordinary autonomous bot goals.
The optional Sluaghbinder build shares those limits. The class features
described in [v0.31b verification](VERIFICATION-0.31B.md) are historical
results for that older build and do not prove this new package.
