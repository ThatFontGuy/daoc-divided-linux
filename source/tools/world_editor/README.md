# DAoC World Workshop

A local Windows program for editing the server world and game content while viewing the selected client's textured scenery, NPC/mob appearances, and collision geometry. It runs offline, serves its UI only on `127.0.0.1`, and starts no game or server.

It has three modes (buttons in the header):

- **3D world**: place, add, copy and delete NPCs, objects, doors, zone points, bind points, teleports, jump points, keeps, relics, areas, start locations and NPC path waypoints.
- **Game data**: search and edit content tables such as NPC templates, items, merchant lists, loot, equipment, spells, styles, quests and server properties. You can also add, copy and delete rows.
- **Server files**: edit the server's settings, bot configuration and language text files, with a backup kept on every save.
- **Items**: browse server items and every item appearance in the client (weapons, armor, cloaks, shields, housing decorations), preview them, edit stats, and create server items from client appearances the server doesn't use yet.
- **Merchants**: build merchant item lists page by page, choose coins or any item as the currency, and assign the list to NPCs.
- **Custom looks**: add new private NPC models to the client, made from a stock model with your own painted textures (and optionally your own NIF mesh).

All database changes from both 3D world and Game data go into one list of pending edits. **Review & save** writes them together.

## Two versions

**Built into a game (launcher button).** The launcher's **WORLD EDITOR** button (under Start / Stop / Enter Realm) opens `runtime\world-workshop\WorldWorkshop.exe` for that game. Saved state goes to `runtime\world-workshop-data` (backups, previews, caches), so nothing is added to the game's top folder. The launcher explains when the editor isn't installed. The button is added by `patch_launcher_button.py`, applied to the exact launcher source an install was built from.

**Standalone (for other Offline DAoC players).** `artifacts\world-workshop-package\WorldWorkshop-<version>.zip`. Unzip anywhere and run `WorldWorkshop.exe`. The first time it asks for the Offline DAoC game folder (remembered in `%LOCALAPPDATA%\WorldWorkshop`); `--game PATH` picks one directly. No Python is needed. Collision floors use the bundled BuildNav exporter on the game's own `tools\dotnet` .NET 10 runtime. On a server without `GameCustomCurrencyMerchant` in `GameServer.dll`, the item-currency option is disabled with a note.

Both are the same build:

```powershell
# Python 3.12 with NumPy, Pillow and PyInstaller (PYTHONPATH may point at a folder holding PyInstaller)
python source/tools/world_editor/build_package.py --zip
```

It writes `WorldWorkshop\` (about 170 MB, 73 MB zipped) with `README.txt`, the licences and `MANIFEST.sha256`. It contains the editor, its workers, the pipeline modules it uses, Three.js, a snapshot of the server's item-name enums, and BuildNav (win-x64 only). It contains no game files, databases or caches. `app.py` is the packaged entry point: the preview and custom-look workers run in the same program (`--worker`).

To put it in a game: copy `WorldWorkshop\` to `<game>\runtime\world-workshop\` and use a launcher with the button.

## Launch

Double-click **START WORLD EDITOR.cmd** in the DAoC Offline folder and choose Classic, Stormforged, or Modern client test. Python 3.10+ is required; this workspace already has Python 3.12. The bundled Three.js renderer needs no network connection. Keep the console open while editing; Ctrl+C closes the local editor.

For another install:

```powershell
python Source/source/tools/world_editor/editor.py --db "GAME/runtime/data/opendaoc.sqlite3.db" --client "GAME/runtime/client-opendaoc/app" --target-client "OTHER CLIENT/app"
```

The selected database and reference client are shown in the header. The reference client determines what geometry you see, and which world files client sync copies. Modern clients can contain different terrain and buildings from the classic server; selecting that profile does not automatically fix server placements.

## Place NPCs and objects

1. Choose a zone. Textured ground, buildings, trees, NPC/mob previews, and collision geometry load automatically. First conversion runs in the background and may take a few minutes; later visits use the cache. Zone assets and the server database are read-only during browsing.
2. Search by NPC name, title (such as Weapon Merchant), or ID. Click a model, name label, or list entry. Double-click the list entry, use **Focus**, or press **F** to move the camera closer. The town filter narrows the list to NPCs with titles.
3. Choose **Move** (**W**) and drag an NPC/model marker. **Select** (**Q**) restores selection/orbit behavior. **Shift+drag** still moves an NPC in either mode. **Ctrl+click** selects a group. The arrow buttons nudge the selection by the step value in world units; **Z −/+** adjusts height, **↶/↷** turns it by 45°, and **To floor** snaps it to a nearby floor. Numeric X/Y/Z and Heading fields allow exact placement. Normal DAoC heading is 0–4095, not degrees; legacy NPC rows with larger unsigned-short headings remain supported for exact restore.
4. Use **Check visible placements** to find missing floors or height differences. This is a review aid, not a navigation or encounter validator. Multi-level buildings need visual review.
5. **Review & save** shows every changed value before writing. Close the game and server first. A database snapshot and reversible row patch are stored under `Source/artifacts/world-editor/<profile>/backups/`. Restart the game server yourself to load the saved positions.

**Undo / Redo** affect pending edits. **Restore edits** reverts the fields changed by a previous save, refusing later conflicting world changes and preserving unrelated player progress. Export pending edits before closing the editor; pending edits are held in browser memory.

The **Textured world / Collision view** selector switches between client art and the placement geometry. **Names** toggles nearby labels (the selected name remains visible), **Trees** reduces vegetation clutter, **Top / 3D** changes the camera angle, and **Cutaway** clips scenery above a plane three metres over the camera target so building interiors are easier to inspect. Ground snap still uses collision floors, never decorative leaves or labels. It searches from just above the reference height so a roof far overhead is not mistaken for the intended floor.

Textured assets are derived from the selected client, including New Towns overrides for the modern test world. NPCs use catalog model/skin data and idle animation where supported. These are appearance previews: equipment, NPC-template overrides, all effects, and every in-game material layer are not reproduced. Missing appearances use a humanoid editor placeholder with a label tooltip saying so; movable server objects and doors use simple boxes. Detailed models load around the camera (up to 100 nearby entities); distant spawns remain small colored markers. Some legacy NIF formats are unsupported; expand **Geometry details** for conversion warnings.

The preview worker needs NumPy and Pillow. It automatically finds the bundled Python runtime on this machine; on another machine set `WORLD_EDITOR_RENDER_PYTHON` to a Python interpreter containing those libraries. It runs as a separate process and writes only under `artifacts/world-editor/<profile>/visuals/`, leaving client files unchanged. Cached scenery is tied to the world hash/catalog/model list, and used figure/texture inputs are checked before a later session reuses it. If you edit a Model ID to one not yet previewed, use **Reload textured view** to convert that appearance.

### More world layers, adding and deleting

The **Layers** box turns on each kind of world record. Each kind has its own marker colour. Bind points and areas also show their radius, and path waypoints are joined by a line in step order. Areas, start locations and path waypoints start switched off. Moving a waypoint changes the route an NPC walks.

- **Duplicate** (Ctrl+D) copies the selected rows 64 units east with new IDs.
- **Place copy** (E) copies the selected row to the spot you click on the ground (snapped to the floor if *Snap moves to ground* is on).
- **Delete** (Del key) marks rows for deletion; Undo brings them back. Nothing is removed until Review & save.
- The inspector shows every column of the selected row. The main ones are at the top and the rest are under **All columns**.
- **Related data** buttons jump to linked rows, such as the NPC template, merchant item list, equipment, loot tables, path or faction. **Open in data** shows the row in Game data.

### Walk paths

To make an NPC walk around, select it and click **Create walk path** in the *Walk path* panel (or press **P**). This:

- adds a `Path` row (type Loop) and sets the NPC's `PathID`
- adds the NPC's own position as waypoint 1
- sets `Speed` to 200 if it was 0
- switches to the **Waypoints** tool

Each click on the ground adds the next waypoint (snapped to the floor). **Esc** stops. Choose the path type in the panel: *Walk once*, *Back and forth* or *Loop*.

- **New waypoint speed** sets `MaxSpeed`, which caps the NPC's walking speed on that leg.
- **Wait** sets `WaitTime`, the pause at that point in tenths of a second.
- Select a waypoint and use **Insert waypoints after this** to add points in the middle; later steps are renumbered.
- Drag waypoints with the Move tool, or delete them with Del.
- **Stop walking** clears the NPC's `PathID` and leaves the path rows in place.

The server walks a standard NPC (normal mob brain) along its path; scripted NPCs or brains may ignore it. A path is loaded when the server starts.

## Items

**Server items** lists `ItemTemplate` rows. Filter them by kind (weapons, armor, cloaks, shields, jewelry, housing, other), realm, name or ID. Each row shows its inventory icon from the client's icon sheets. Selecting an item shows:

- a 3D preview for meshes (weapons, shields, housing decorations)
- the textures for worn armor and cloaks (the classic skin, plus the Catacombs textures players actually wear)
- the merchant lists that sell it
- the full stat editor, with names for object type, slot, damage type, realm and the ten bonus types (read from the server's enums)

Use **Copy** to make a variant, **Add to merchant list…** to sell it, and **Delete** to remove it.

**Finding items.** Besides kind and realm, server items filter by equipment slot and level range. They sort by name, level (low→high or high→low), price, type or realm. Each row shows level, type, slot, realm, price and its first bonuses. **Check** lists items that need attention:

- the appearance is missing from this client (the item would be invisible)
- the object type and slot don't match (it can't be equipped)
- the price is 0
- nothing gives it: no merchant, loot table, one-time drop, crafting recipe, artifact, starter kit or quest. Server scripts and generated loot can still hand such items out.

Filters and sort are remembered in the browser, and **Reset filters** clears them. The ↑/↓ arrow keys step through the list.

**Item summary and sources.** Above the editor, a summary reads like the in-game delve:

- DPS and speed, or armor factor and absorb
- quality, condition and weight
- named bonuses, charges and procs
- the effect, the classes that can use it, the level requirement, and trade/drop flags

Below it, **Sold by / Drops from / One-time drop / Crafted / Quest reward / Artifact / Starter gear / Currency for** list where players get the item. Each entry opens the merchant list or the data row.

**Client appearances** lists every `objects.csv` row in the selected client. *Not used by any server item yet* shows the art the server never uses. **Create server item from this** copies a similar existing server item and points it at the appearance:

- a weapon copies a weapon, and a shield copies a shield
- armor copies an item in the same slot (body, arms, gloves, legs, boots, helm, cloak)
- a housing decoration copies a garden (`ext_…`), wall or floor object, chosen from the name

Then set its name, level, stats and price, and **Review & save**. Icons from later expansions' icon series show as a striped square; in game they may show a question mark.

The preview is a conversion from the client's files. Armor is drawn on the character body in game and isn't assembled onto a body here.

**Effects.** A server item's `Effect` is drawn in the preview, the way the client resolves it: `spweapons.csv` → `spnifs.csv` → `effects/<nif>`. It appears as animated particles (flames, glows, vapour, sparks) plus any glow cards, in the item's own space. A client appearance shows its own Object Effect column (objects.csv 55–58). The **Effect** field is a dropdown of every named effect in the client, and the preview updates as soon as you pick one. An effect-only item (such as the fire-eyes helms, which use an invisible placeholder mesh) is framed on its effect. Effect numbers missing from `spweapons.csv` (the potions' 1479) draw nothing in game, and the preview says so.

The particles are a browser port of the new client's `nif_particles.gd`: rate, speed, cone, lifetime, colour over life, grow/fade, gravity, spin and blend mode. Treat them as a close preview, not a screenshot of the classic client.

**Worn preview.** Cloaks and body armor are also shown on a player character, dressed the way the client dresses Catacombs figures (new-client `build_races.py`):

- the race's skeleton, head and default starter clothes
- the item's textures as the client picks them. With Cata Status (objects.csv col 65) on, the client uses the Catacombs columns 66–71 (pskins BaseTex → the exact mskins copy) and ignores the classic ones (guide 13.3, confirmed in game). Otherwise it uses the classic skin's "Cata <name>" set. The figures' own texture archives win over same-named copies laid out for the classic figures, and boots use the 2:1 sheet of the two spellings.
- for a server item, its **Extension** picks the body, gloves and boots mesh, which is what adds pauldrons and other details (0 = the plain mesh). Arms and legs always use mesh 1.
- a robe (objects.csv col 15 = 3) wears the long robe body, hides the arms and legs, and puts gloves and boots on mesh 3
- the item's dye **Color** (tints.csv Catacombs colour) tints its pieces, as in game. Editing Extension or Color updates the preview.
- a cloak texture on the race's hood-down cloak mesh, using texture coordinate set 1
- the idle animation

**Worn by** picks Norse, Briton or Celt, male or female; cloaks start facing away so the design is visible.

**Helms** are drawn on the figure as the client does (new-client `build_helms.py` / `fig3_figure.gd`), and the view zooms to the head:

- Most helms have one 3D model per race and gender (objects.csv `Nif1`–`Nif12`, in the helm realm's race order). The one for the chosen figure hangs on the `Bip01 Helmet` (else `Bip01 Head`) bone, scaled by its items.csv helm scale.
- A helm is textured with its Catacombs helm texture (the column after `Nif12`) when set, otherwise with the item's Helm skin (col 12) when the model uses it.
- A helm only exists for its own realm's races. A Midgard helm on a Briton is shown on the Midgard figure of the same gender, with a note.
- Head-swap helms (col 95 "Nif" with col 96 "Head Swap" = 1: Dragonsworn, Dragonslayer) replace the head with the race's full-helm part, in the Helm skin.
- An item's effect (fire eyes, glows) rides on the helm.

The hood-up cloak is not drawn yet. Previews and the texture index are keyed to the client's files, so an import or live patch is picked up without clearing caches.

**Cloaks and armor textures** come first from the Catacombs columns (objects.csv 66–72, through pskins.csv BaseTex → mskins.csv), which is what player characters wear. The classic columns follow, labelled *classic / NPC*. The epic class cloaks keep the plain stock cloak in classic column 11 and their real art only in column 72. That's why they once looked blank. None of the 47 epic cloaks has a server item in the stock database; use *Create server item from this* to add them.

### Importing items from another client (live patches)

When the live client gets new item art, `asset_worker.py import-items` copies the item appearances into a game's client. It brings the `objects.csv` rows, their `pskins.csv` rows and textures, keeping object IDs so one server item `Model` works in every install. It works for skin-based items (cloaks, armor); weapons with their own mesh aren't handled yet. A skin ID already used by different art gets the next free ID, and only new lines and archive entries are added. A backup goes under `look-backups/`, and the import appears in **Custom looks** with **Uninstall**. Close the game and server first:

```powershell
python asset_worker.py import-items --client "GAME/runtime/client-opendaoc/app" --source "D:/Electronic Arts/Dark Age of Camelot" --objects 4924,4925,4926 --backups "Source/artifacts/world-editor/<profile>/look-backups"
```

(Use the Pillow Python, as for custom looks.) The 25th-anniversary cloaks (objects 4924–4926, live patch 26 Oct 2026) were imported into Classic and Stormforged this way; their skins became private IDs 5788–5790 there. The modern test client received the live `gamedata.mpk` and `pskin060.mpk` directly.

## Merchants

The left list shows every merchant item list, with item counts, how many NPCs sell it and its currency. **New merchant list** starts an empty one.

- The centre shows the 5 pages × 30 slots the merchant window offers. Search items below the grid and click one to put it in the selected (or next free) slot.
- Click a slot to set its price or remove it. Price belongs to the item itself (`ItemTemplate.Price`), so it changes everywhere that item is sold. Copy the item first to price it differently on one list.
- **Payment: Coins** is a normal merchant (`DOL.GS.GameMerchant`).
- **Payment: An item** works like the Darkness Falls seal merchants, but with any item. It adds a row to `offline_currency_lists` (ItemListID → currency item `Id_nb`); the editor creates the table on first save. Prices on that list are then counts of the currency item.
- **Make selected 3D NPC sell this list** sets the NPC's `ItemsListTemplateID` and its `ClassType`: `DOL.GS.GameCustomCurrencyMerchant` for an item currency, `DOL.GS.GameMerchant` otherwise. Sellers with the wrong class are flagged.

`GameCustomCurrencyMerchant` is server code added with this editor (`GameServer/gameobjects/GameMerchant.cs`, table class `GameServer/database/DbOfflineCurrencyList.cs`). A game folder needs the rebuilt `GameServer.dll` before such merchants work; an older server can't load that ClassType.

## Custom looks

The classic client can only draw its own NetImmerse `.nif` meshes rigged to DAoC skeletons. A custom look is therefore a **private copy of a stock model**: same mesh, skeleton and animations, with your textures (and, if you have one, your own DAoC-compatible NIF).

1. Open **Custom looks** and pick a base model with the body and animations you want. *Player-race bodies only* lists the multi-part human/elf/troll bodies.
2. **Download template** saves each stock texture as PNG. Paint over it and keep the layout, because the UVs don't change.
3. Upload your PNG/JPEG for each part you change, enter a name and optional size %, then **Install look** (with the game and server closed).
4. Select an NPC in 3D world (Place copy or Duplicate makes a new one), then in Custom looks click **Use on selected NPC**. This sets `Model` and clears `NPCTemplateID`, because a template would replace the model. **Reload textured view** previews it; **Review & save** stores the NPC.

The install follows the client modding rules in `docs/CLIENT-MODDING-GUIDE.txt`:

- new `monsters.csv` and `skins.csv` rows go in an unused model-ID gap below 2494 (not used by any Mob or NpcTemplate)
- textures are DXT1 with mips, resized to the stock size, in `figures/skins/skin099.mpk`
- catalog lines are inserted in ID order with no blank lines, and every existing line is checked unchanged
- dark/detail overlay columns for replaced parts are cleared, so stock patterns don't paint over the new skin (not yet verified in game for player-race bodies)
- transparency is not kept

**Advanced NIF:** a `.nif` you upload is copied to `figures/cust_<name>.nif` with a new `monnifs.csv` row. The private NIF IDs 989–999 have only a few free slots left. The mesh must use the base model's skeleton and bone names, because it borrows that model's animation set. Meshes taken from other games must be re-rigged to the DAoC skeleton in a 3D tool first; this editor doesn't convert or rig them.

Installs back up `gamedata.mpk` and `skin099.mpk` under `artifacts/world-editor/<profile>/look-backups/`. **Uninstall** restores them, but only if neither file changed since. Uninstall newer looks first, and change the `Model` of any NPC still using the removed ID. Custom looks are for this install only. Release packages are built from clean clients, and art you didn't make or license must never go into a public package.

## Game data

Choose a table on the left. Search finds text in any text column; pick a column and type a value in **= exact value** to match one column exactly. Click a row to edit it on the right. **Duplicate**, **New blank row** and **Delete** create pending edits. New rows get a fresh GUID or the next free number as their key automatically. Tables whose key is a name (such as `ItemTemplate.Id_nb` or `ServerProperty.Key`) ask you for one. When a row is copied, its `<Table>_ID` GUID column also gets a new value.

Related-data buttons follow common links: merchant item → item, item → merchant lists / loot / spells / recipes, loot template → items and mobs, spell line → spells, path → waypoints. **Show in 3D** opens the zone that contains a positioned row and selects it.

Only content tables are listed. Accounts, characters, inventories, houses, guilds and bot rosters are never shown or editable. A row's key can't be changed after it's saved; duplicate the row instead. The database's own constraints (for example unique `SpellID`) are checked when you save; if one fails, nothing is applied.

## Server files

The list shows the text files under the game's `runtime/server` folder (`.json`, `.xml`, `.txt`, `.ini`, `.cfg`, `.config`, `.csv`) and the `.txt` files directly in `runtime`. Logs, binaries, `*.deps.json`/`*.runtimeconfig.json` and `account.txt` are excluded. Saving:

- refuses invalid JSON or XML
- refuses if the file changed on disk since you opened it
- refuses while the server is running
- keeps the original line endings, encoding and BOM
- copies the previous version to `artifacts/world-editor/<profile>/file-backups/`

**Earlier versions…** loads a backup into the editor; save the file to restore it.

## Zone editing

The **Zone** tab edits server zone name, water level, lava/diving flags, realm, and XP/RP/BP/coin bonuses. It displays the server's region, origin and extent and checks these against the client catalog. Dragging is disabled if those layout values differ. Name differences and collision/placement differences are separate from this bounds check.

This version does not sculpt terrain, move client building fixtures, edit C# scripts, or regenerate navigation meshes. NPC template settings and encounter scripts may override individual NPC fields or positions at server start. Verify those NPCs in game after editing.

## Patches and client/server matching

**Export patch** saves only the edited rows plus a SHA-256 identity of the reference client's world files. It exports no accounts, characters, inventories, or full database. Patches are format `offline-daoc-world-editor-2`; each change is an `update`, `insert` (complete new row) or `delete` (complete original row). Version-1 patches still import. **Import patch** checks that the client world matches, that every original value is unchanged, and that no new row already exists, then stages the edits for review. **Restore edits** reverses a save: rows it added are deleted, rows it deleted are added back, and edited fields get their old values. Patches are intended for copies of the same server world.

NPC, object, and door positions are sent by the server: these changes do not require modifying `game.dll`. The patch records which client geometry the edits were designed against.

The **Client sync** tab compares the reference client's `zones`, `newtowns`, and `frontiers` files with another configured client. Review the target and summary, then apply. Sync uses the repository's `modern_world_overlay.py` guarded copier with input/output hashes, backups, failure restore and verification. Extra target New Towns models are removed because they override classic building layouts. Other extra files are retained, following the existing overlay policy; this is reference-file alignment, not an exact directory mirror. The executable, figures, items and effects are outside this operation.

Client file backups are under `Source/artifacts/world-editor/<profile>/client-backups/`. To restore them:

```powershell
python Source/source/tools/modern_world_overlay.py rollback "TARGET CLIENT/app" "BACKUP FOLDER" --apply
```

**Client sync does not prove that server navmeshes, door IDs, scripted coordinates or bot routes match a different world version.** It is useful for bringing a newer client onto the existing classic world. Migrating the server onto newer world geometry also requires reviewed world migration, rebuilt navigation and route checks; the existing `live_world_migration.py` / `live_world_navmesh.py` tools remain separate. No navigation files are silently replaced.

## Command line

`cli.py` runs the same checks without the browser, for scripted fixes (and for an AI assistant fixing things):

```
python source/tools/world_editor/cli.py --profile classic find Mob --where "Name=Master Elementalist" --columns Mob_ID,Region,Level
python source/tools/world_editor/cli.py --profile classic item <Id_nb>
python source/tools/world_editor/cli.py --profile classic items --issue nowhere
python source/tools/world_editor/cli.py --profile classic sql "SELECT count(*) FROM Mob WHERE Region=1"
python source/tools/world_editor/cli.py --profile classic plan edits.json --out fix.patch.json
python source/tools/world_editor/cli.py --profile classic apply fix.patch.json
python source/tools/world_editor/cli.py --profile classic history
python source/tools/world_editor/cli.py --profile classic undo <backup id>
```

Pick the world with `--profile classic|stormforged|modern`, `--game <folder>`, or `--db` with `--client`. `plan` turns an edits file (change a row by key or every row matching `where`, copy a row, insert, delete; the format is in `cli.py`) into a normal editor patch and prints what would change, without applying it. `apply` and `undo` use the editor's own save path: the same validation, a refusal while the game or server runs, a database snapshot, and backups shared with the browser editor's **Restore edits**. `sql` opens the database read-only, so it can't change anything. Unlike the Game data view it can read every table, including accounts and characters, which is useful for diagnosing a save, but it never writes to them.

## Geometry exporter

Build once with the .NET 10 SDK (already built in this workspace):

```powershell
dotnet build Source/source/development-tools/OpenDAoC-BuildNav/OpenDAoC-BuildNav.csproj -c Release
```

The editor defaults to that build's executable; `--exporter PATH` overrides it. Exports are isolated by client-world hash using `DAOC_BUILDNAV_BASE`, then cached under the editor state folder. Existing exporter binaries predating this output-directory option need rebuilding. The geometry cache does not include a generated navmesh. The importer also accepts `--geometry FOLDER`, but requires `world-editor-source.json` with a `fingerprint` matching the selected client's world hash.

World-file hashes are cached against size and nanosecond modification/creation timestamps. Changed/new/deleted files are detected on patch validation. First loading a client scans several GB and may take a minute. Do not patch client assets while an editor session is open; reopen it after any client asset changes.

## Validation

```powershell
cd Source/source/tools
python -m unittest world_editor.test_editor -v
```

Tests exercise field allowlists, the content-table allowlist (player tables excluded), insert/delete round trips and restore, typed column rules, row search, the server-file allowlist with JSON/XML checks, backups and stale-file refusal, custom-look install/uninstall round trips on a synthetic client (needs the Pillow Python) and refusal to uninstall over later client changes, stale-row conflicts, atomic writes, database locking, backup/restore, preservation of unrelated player progress, client-world mismatch, client-sync preview conflicts, PCX decoding, and loopback API authentication/origin checks. Real in-game verification is a separate step.

Third-party renderer: Three.js r170 (MIT), included under `static/vendor/` with its license.
