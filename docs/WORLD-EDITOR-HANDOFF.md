# World editor hand-off (October 26, 2026)

For whoever builds the 3D world editor. Its first job is placing NPCs and other world rows by hand where the
automatic migration to live's 1.130 geometry ("fix B") can't. Background:
[MODERN-CLIENT-WORLD-MISMATCH.md](MODERN-CLIENT-WORLD-MISMATCH.md).

## Where things stand

The modern test install (`artifacts/modern-client-test`) runs fix B: the 1.130 client shows live's world, and
the server's navmeshes and world rows were moved to match it. What still needs hand work:

1. **Town NPCs.** New Towns is a redesign. In Cotswold (zone 0), Mularn (100) and Mag Mell (200) most
   merchants and trainers belong to buildings live moved 300-6,100 units. They are still near their classic
   spots, often in the street. There is no live-era spawn data to restore from.
2. **Unresolved rows** of the migration plan: about 20 NPCs in the zone-277 quest instance, 7 named NPCs in
   Dartmoor (zone 4), and 24 doors live doesn't have. Listed in the plan's `unresolved` array.
3. **Tower guards** at Castle Sauvage, Snowdonia Fortress and Svasud Faste whose live tower has no top. The
   plan reason says "height kept relative to the keep" or "off the navmesh".

## Geometry to draw

`artifacts/world-geometry/` (Git-ignored, 1.3 GB), exported by `OpenDAoC-BuildNav --obj=true`:

| Path | What |
|---|---|
| `classic/zoneNNN.obj`, `.doors` | The classic world (OpenDAoC's 1.127 client), 103 zones |
| `live/zoneNNN.obj`, `.doors` | Live 1.130's world as the test client draws it, 103 zones (11 are identical to classic) |
| `zones.dat` | The zone table both use: region and offsets per zone |
| `artifacts/modern-client-test/runtime/server/navmesh/zoneNNN.nav` | The installed (live) bot navmeshes: walkable floor |

**obj coordinates:** vertices are world units ÷ 32 with Y and Z swapped. `v a b c` is world
`(a*32, c*32, b*32)`, in global region coordinates: the same space as the database's X, Y, Z. Faces are
triangles (`f i j k`, 1-based). The obj holds collision geometry only (terrain, buildings, props with
collision), without textures. A file can be 5-15 MB, so load it per zone.

**doors files:** one `INSERT INTO door (DoorID, ClientNif, X, Y, Z, Heading, DoorSize, ...) VALUES(...)`
line per door, in world coordinates.

**Zones:** a zone covers `region_offset_x * 8192` to `+65536` in X, and the same in Y from
`region_offset_y`, within its `region`. Parse `zones.dat` sections `[zoneNNN]`.
`source/tools/live_world_migration.py` has `load_zones()`.

**Reading .nav files in Python:** `source/server/tools/navmesh_splice/navcomp.py` (`NavAreas(path)`,
`locate(x, y, z)`, `height(poly, x, y)`).

## World rows

The world database is `artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db` (SQLite). Only these
tables carry positions the editor needs:

| Table | Key | Region | Position | Heading |
|---|---|---|---|---|
| `Mob` | `Mob_ID` | `Region` | `X`, `Y`, `Z` | `Heading` |
| `Door` | `Door_ID` | (from `InternalID`) | `X`, `Y`, `Z` | `Heading` |
| `BindPoint` | `BindPoint_ID` | `Region` | `X`, `Y`, `Z` | none |
| `Teleport` | `Teleport_ID` | `RegionID` | `X`, `Y`, `Z` | `Heading` |
| `WorldObject` | `WorldObject_ID` | `Region` | `X`, `Y`, `Z` | `Heading` |
| `ZonePoint` | `ZonePoint_ID` | `TargetRegion` | `TargetX`, `TargetY`, `TargetZ` (arrival spot) | `TargetHeading` |
| `Area` | `Area_ID` | `Region` | `X`, `Y`, `Z` (safe-area centres, with `Radius`) | none |
| `PathPoints` | `PathPoints_ID` | (`Path.RegionID` by `PathID`) | `X`, `Y`, `Z` | none |

- **Heading:** 0-4095, `atan2(-dx, dy) * 4096 / 2π`. 0 faces +Y; 1024 faces -X.
- **Door IDs:** `zone * 1,000,000 + fixture unique ID * 100 + door piece`. The client sends this ID when a
  door is clicked. The server checks the player is within reach of the row's X, Y.
- **Mob:** useful columns for display are `Name`, `Guild` (the title under the name), `Model`, `Size`,
  `Level`, `Realm`, `RoamingRange`, `PathID`.
- Keys are text (GUIDs or numbers stored as text).

## Saving edits

Write edits as a plan for `source/tools/live_world_migration.py` rather than writing the database directly.
The apply step:
- refuses while the server is running
- backs up the whole database
- checks each row still holds its old values
- verifies every write
- keeps a rollback that touches only the rows it changed

Plan format (JSON):

```json
{
  "format": 1,
  "changes": [
    {
      "table": "Mob", "key_column": "Mob_ID", "key": "1234",
      "old": {"X": 347800, "Y": 491259, "Z": 5249, "Heading": 2048},
      "new": {"X": 349300, "Y": 491200, "Z": 5425, "Heading": 1024},
      "reason": "editor: Lachlan into the New Towns elf hall",
      "label": "Lachlan Weapon Merchant"
    }
  ],
  "unresolved": []
}
```

`old` must be the row's current values: read them from the database when the edit is made. Columns not in
`old`/`new` are left alone. A door renumbered to a live door ID includes `InternalID` in both.

```
python source/tools/live_world_migration.py apply <db> <plan.json> --backups artifacts/modern-client-test/backups          # preview
python source/tools/live_world_migration.py apply <db> <plan.json> --backups artifacts/modern-client-test/backups --apply
python source/tools/live_world_migration.py rollback <db> <backup folder> --apply
```

Example of a full plan: `artifacts/modern-client-test/fixb-staging/world-plan-v2.json` (787 changes, 54
unresolved, each with a `reason` saying what the automatic pass did).

## Things that will trip the editor up

- **Server running:** the server holds the database and rewrites some rows. Stop it before applying a
  plan; apply refuses otherwise.
- **Dragons:** `scripts/namedmobs/Dragons/DragonLairPlacement.cs` and the dragon scripts put Golestandt,
  Gjalpinulva and Cuuldurach back at the classic lair positions on every start. Editing their rows won't
  stick.
- **Bot muster points:** `bots/autonomous/AutonomousRvrStaging.cs` and `RealmRaidMuster.cs` hard-code the
  border keeps' classic positions. Moving keep NPCs doesn't move where bots gather.
- **Two worlds, one source:** the Classic and Stormforged editions use the classic world. Edits belong
  only in the modern test install's database; never edit `Classic/` or `Stormforged/`.
- **Navmeshes:** the editor can show walkable floor from the .nav files. An NPC off the navmesh is fine if
  it doesn't move (guards on towers). Roaming NPCs and patrol paths need floor the bots and NPCs can path on.
- **After moving many town NPCs**, regenerate the bot seams so bots' "town" networks stay right:
  `source/server/tools/navmesh_splice/seamgraph.py` (its README has the commands).

## Useful code

| File | What |
|---|---|
| `source/tools/live_world_migration.py` | Plan, apply, rollback; `Geometry` (vertical hits on an obj), `Walkable` (navmesh), `carry()` (move and turn about a centre), `turn_heading()` |
| `source/tools/modern_world_overlay.py` | Switch the 1.130 client between live and classic world files |
| `source/tools/live_world_navmesh.py` | Install or roll back a server navmesh folder |
| `source/development-tools/OpenDAoC-BuildNav` | Re-export geometry: `OpenDAoC-BuildNav.exe --daoc=<client app> --zones=<ids> --obj=true` (run from its `base` folder) |
