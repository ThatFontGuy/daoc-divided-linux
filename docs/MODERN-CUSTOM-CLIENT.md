# Bundled modern client and custom classes

The private modern test installation owns its 1.130 client under
`artifacts/modern-client-test/runtime/client-modern/app`. Start it with the workspace's
`START MODERN CLIENT TEST.exe`, then use Start Server / Enter Realm.
The account, characters and world remain in the same test runtime and database.

The launcher profile resolves relative client/helper paths from its runtime directory
and verifies their hashes before launch. The bootstrap's verification mode reads the
same profile. The server configuration still contains its existing absolute database
path: moving the test installation requires updating that configuration too.
This local bundle is not a portable public release archive.

## Stormforged patch

`source/tools/stormforged/patch_modern_client.py` accepts only original SHA256
`3915a495253040a4cdfc79d265a8d268797304eb46b9a34d51a88d49a8445022`.
Its deterministic output is
`b67c4a92f5ef245348cda4b192252ea7a5fb5519c85933480982782e369f0440`.

It redirects the Midgard Mauler name, creation description and realm class-group
caption to private Stormforged strings and registers Norseman, Troll, Dwarf,
Kobold, Valkyn, Frostalf and Deifrang. Albion and Hibernia Maulers retain their
original registrations. The client still sends class 61; the existing enabled
Stormforged server handler converts it to 64. Spells and class rules remain
server controlled. This patch does not add art, equipment models or spell icons.

The original binary is untouched. A private `.custom` PE section contains the new
strings and code. Fixed instruction replacements and the source hash are checked
before output. Do not run the retail patcher against this bundled copy.

## Rebuilding a local bundle

With the test server/client/launcher closed, run from the repository:

```powershell
python source/tools/bundle_modern_client.py 'C:/path/to/pristine/1.130/client' artifacts/modern-client-test
```

The destination must not already exist. The script verifies the connector, copies
and hashes assets, omits logs and account/settings files, writes a file manifest,
backs up the previous profile and pristine binary, then switches the profile after
verification. It never starts a server or edits the database. Use a launcher build
containing relative modern-profile path support.

Rollback: close the test programs and restore `modern-client.json` from
`backups/client-bundle-*` to `runtime/modern-client.json`. That profile points back
to the original external client. Launcher backups are in
`backups/launcher-bundle-*`. Database rollback is not needed.

## Adding another custom class

Client changes are not automatic when a server class is added. Each new class
needs a native client slot, server creation/packet mapping, client display and race
registration, and any required icons/models. Extend the version-specific patch
against the pristine input, build the combined patch once, then update the bundle's
expected hash. Do not stack binary patches or replace all shared Mauler strings.
Separate server class IDs do not create unlimited native client slots. Use a
separate verified profile for each supported class edition.

## Verification and limits

113 launcher tests passed, including relative-path resolution and changed-binary
rejection. Offline Unicorn x86 emulation checked the name trampoline, preserved
registers, seven race insertions and balanced stacks. Unknown inputs and double
patches were rejected. Original image changes were limited to declared patch
regions and PE headers. Private reports are under `artifacts/`.

REA/Ghidra evidence: strings `ev_8958e0e07b3ca1efb88f965fef80f1c811cfa96fc01ee496a4a90f2f1a4e19f8`,
Midgard registration `ev_4992ce685f9b391f68b9dc97ca450c2326e27abc10a9a8d5e1577fda56a36173`,
localization fallback `ev_23aa0599c58d7060e28370d25149f8b3776f68f428556181188cda827cb3de38`,
list insertion `ev_d782011d29b350dc4ddf8e277e7cfbfacaa18a3f8f78bba26f2f21fcce1bc71e`.
These are static observations, not gameplay evidence.

No server or game was started during preparation. Verify creation-screen name,
description, all seven race choices, existing-character labels, entry into the
world, spells/hotbars, equipment and relog in game. This local test includes saved
progress; public distribution must use sanitized release builders, not an archive
of this installation.

## Storm Sovereign replacement — October 22, 2026

The modern test installation now uses Storm Sovereign in the existing Stormforged slot.
The verified modern client SHA256 is
`63cb47bbba3415835a926e86de56d2aee84b4d9bc57ea88c72f91840e36ca13c`.
Its profile was updated together with the client; the original Thane and other realms are untouched.
See [STORM-SOVEREIGN.md](STORM-SOVEREIGN.md) for abilities, migration and acceptance checks.
All 3,116 server tests and eight migration/client/installer tests passed before installation.
The installer verified identical contents in all 37 saved-progress tables and backed up every
replaced file under `backups/storm-sovereign-20261022-173249-554952` in the test installation.
No server or client was started. Refresh obsolete Stormforged hotbar buttons before playtesting.
