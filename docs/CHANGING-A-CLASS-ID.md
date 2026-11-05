# Changing a class's ID, and giving a custom class a native client slot

A step-by-step procedure for two related jobs, written up after actually doing both for Drengr
(this project's own custom Midgard class) and hitting most of the mistakes it warns about:

- **Renumbering an existing class's ID** - needed whenever a custom class's current ID collides
  with something else (this happened for Drengr and Nosferatu: both were designed on a different
  server, `daoc-offline-linux-server-bots`, under IDs that collided with this fork's own native
  classes once migrated here).
- **Giving a custom class a native character-creation slot** - the client's creation screen only
  shows a fixed, small set of class IDs per realm (its own compiled-in list, not read from the
  server at all); a brand-new ID is *never* selectable there no matter what the server does. The
  only way in is to take over a slot some other class already occupies - in practice, retiring one
  of this fork's own native classes (Pendragon Sovereign/Death Knight/Tuatha Sovereign/Stormforged)
  and moving the custom class onto its old ID. Drengr took over Stormforged's Midgard slot (64)
  this way; the other three native slots (Albion 65/66, Hibernia 67) are still unclaimed if another
  Midgard, Albion, or Hibernia class needs one later - except Midgard already has none left (there
  is only one native Midgard slot: 64).

If "the subject comes up" - a request to add a custom class to character creation, or any request
to renumber one - follow this document rather than reconstructing the process from scratch; it is
exactly what it took for Drengr, including the parts that went wrong the first time.

## Part 1: giving a class a native client slot

This is a one-time binary patch to the client's `game.dll`, independent of whatever class ID ends
up being used server-side (Part 2). Skip this part entirely if you're only renumbering a class that
already has no native slot (or doesn't need one).

1. **Decide which native slot to retire.** Check `source/tools/classslots/patch_class_slots.py`'s
   `SLOTS` tuple for what's currently assigned to each of the four native slots (64 Midgard, 65/66
   Albion, 67 Hibernia) and pick one in the right realm. Retiring a class doesn't delete it: move
   its own class ID to a new, unused, *dormant* number (Stormforged moved 64 -> 70) so its code,
   database rows, and any characters that already played it keep working - the native slot number
   is just freed up for the new class to take over, nothing about the retired class's own identity
   has to change otherwise.
2. **Update the `Slot` definition** for that slot in `patch_class_slots.py` - name, description,
   eligible races, and starting stats (see the `DRENGR` slot there for the shape). This file's
   own `SLOTS`/realm-hook constants are the single source of truth the patcher reads from.
3. **Re-patch a pristine 1.130 `game.dll`** (verified hash `3915a495...` - the patcher refuses
   anything else) and confirm the output is byte-for-byte reproducible by running it twice and
   diffing.
4. **Regenerate `client-patch.json`** via `source/tools/make_client_patch.py <pristine-dir>
   <output.json>` - this is what the launcher's `ModernClientSetup.cs` actually applies to a
   player's own client copy at setup time.
5. **Update `runtime/modern-client.json`'s `GameSha256`** to the new patched hash, by hand - this
   is a **second, independent** hash check (`ModernClientProfile.Verify()`), run at *every launch*,
   not just at setup. **This is the mistake that happened twice already** (once for the project
   owner, once for a friend installing it): updating only `client-patch.json`'s hash and forgetting
   this one leaves every subsequent launch failing with "the verified modern client/helper has
   changed," even though setup itself succeeded.
6. **Repackage the distributable client zip** (`dist/Othlyn-DividedRealms-Client.zip` or whatever
   it's currently named) with both updated files, and re-verify its own SHA256 is what actually
   gets uploaded/downloaded - a stale zip on a distribution site causes the exact same symptom as
   step 5's mistake, and is easy to confuse with it.

No part of this patches any class *content* (spells, specs, stats beyond starting values, races
beyond the creation-screen list) - that's all server-side and needs no client patch, ever, for any
later change. Steps 1-6 only ever need redoing if the *slot itself* changes hands again.

## Part 2: renumbering a class's ID in the server/database

**Use `tools/renumber_class_id.py <db-path> <old-id> <new-id>` for this - do not hand-roll a fresh
SQL sweep.** It exists because the first time this project did this migration (Drengr: donor ID 65
-> intermediate 69 -> final 64), the same kind of bug was found three separate times, each only by
a live, reported, in-game symptom after the "migration" was believed complete:

| Found via | Table(s) missed |
|---|---|
| New Drengr characters couldn't equip a spear or wear studded/chain armor at the right level | `SpecXAbility`'s career-ability grants (a second, later-discovered gap in a table already partly handled) |
| New Drengr spawned with Stormforged's old hammer+shield | `StarterEquipment` |
| Spear styles only showed the level-1 and level-10 attacks | `Style`, `StyleXSpell` |

A full, column-name-based sweep of the entire schema (not just the tables a previous migration
happened to touch) is the only way to not repeat this a fourth time. That sweep is now
`renumber_class_id.py`'s `discover_class_columns()` - it re-examines every `%lass%`-named column
in the live schema *every time it runs*, classifies each one, and **refuses to run at all** if it
finds a column not already classified as one of:

- a bare class-ID column (`CLASS_ID_COLUMNS` - safe to update directly, e.g.
  `ClassXSpecialization.ClassID`, `StarterEquipment.Class`)
- a delimited list of class IDs sharing one column (`CLASS_ID_LIST_COLUMNS` - rewritten token by
  token, e.g. `ItemTemplate.AllowedClasses`, `"2;9;11"`)
- genuinely unrelated to a character's class ID at all (`IGNORED_COLUMNS` - the DOL "ClassType"
  concept, an unrelated C# behavior-class name used on `Mob`/`ItemTemplate`/`ZonePoint`/etc.; or a
  class-*name*-keyed column like `TimeXLevel.Character_Class`, unaffected by a pure ID renumber)

If it ever stops and reports an unclassified column, that means the schema grew a new one since
this was written - go look at what it actually stores, add it to the right set in the script
(with a one-line comment why), and run again. **Do not just add it to `IGNORED_COLUMNS` to make
the error go away** without checking; that is exactly how the original bug happened.

### What this tool does *not* do automatically, and why

Several of this project's own custom specs - the parts of a migration that are genuinely unique to
*this* class, not shared with any stock class - are named with the owning class ID baked into the
spec's own **keyname** as a suffix, by this project's own convention (not a database rule):
`vikingcareer_64`, `drengrspath_64`, `drengrsvalor_64_Valor`, and so on. These live in
`Specialization.KeyName`, `SpecXAbility.Spec`, `SpellLine.Spec`/`SpellLine.KeyName`,
`LineXSpell.LineName`, and (if the clone used this convention for a styled weapon spec too)
`Style.SpecKeyName`. A pure "update every `ClassId` column" sweep cannot rename these - the ID is
inside a free-text string, not a structured column - and blindly string-replacing "64" anywhere
it appears is genuinely unsafe (it would also corrupt an unrelated spec that happens to contain
"64" as a substring for some other reason).

`renumber_class_id.py` **reports every value using this convention** (its `--apply` output prints
them, prefixed "NOT changed above") but never touches them - this is a deliberate, reviewed, manual
step:

```sql
-- Repeat for every table/column the dry run's advisory section listed, substituting the
-- old and new ID. Do this BEFORE renumber_class_id.py --apply, or the advisory section's
-- "_<old-id>" search will already find nothing (it only reports the old ID).
UPDATE Specialization    SET KeyName  = REPLACE(KeyName,  '_64', '_199') WHERE KeyName  LIKE '%\_64'  ESCAPE '\';
UPDATE SpecXAbility      SET Spec     = REPLACE(Spec,     '_64', '_199') WHERE Spec     LIKE '%\_64'  ESCAPE '\';
UPDATE SpellLine         SET Spec     = REPLACE(Spec,     '_64', '_199') WHERE Spec     LIKE '%\_64'  ESCAPE '\';
UPDATE SpellLine         SET KeyName  = REPLACE(KeyName,  '_64', '_199') WHERE KeyName  LIKE '%\_64_%' ESCAPE '\';
UPDATE LineXSpell        SET LineName = REPLACE(LineName, '_64', '_199') WHERE LineName LIKE '%\_64_%' ESCAPE '\';
UPDATE Style             SET SpecKeyName = REPLACE(SpecKeyName, '_64', '_199') WHERE SpecKeyName LIKE '%\_64' ESCAPE '\';
```

A *shared/plain* spec a custom class merely reuses directly (not cloned) - Drengr's actual
`Spear`/`Staff`/`Parry` specs, which keep their generic keynames with no suffix at all, and have
their own `Style` rows keyed by `(SpecKeyName, ClassId)` for the class's ID specifically - needs no
keyname rename; only its `Style.ClassId`/`StyleXSpell.ClassID` rows (handled automatically above)
matter. The advisory list only ever reports keys that actually carry the old ID as a suffix.

### Order of operations

1. **Back up the database first** (the script does this itself before `--apply`, but take your own
   copy too if you're about to also hand-edit keynames per the SQL above, since those aren't part
   of what the script's own backup timing covers).
2. Run `renumber_class_id.py <db> <old> <new>` **without** `--apply` and read the full report.
3. Decide what each advisory-listed keyname should become, and apply those renames by hand (SQL
   above) **before** the next step - the script's `--apply` run doesn't know about them and won't
   wait for them.
4. Run `renumber_class_id.py <db> <old> <new> --apply`.
5. Run it a third time, dry run, for the **old** ID again - it should report nothing left anywhere
   (both the column sweep and the keyname advisory), confirming nothing was missed in either pass.

### Caching: what needs `/reload specs` vs. a full restart

- `SpellLine`, `SpecXAbility`, `Style`, `StyleXSpell`, `Specialization`, `ClassXSpecialization`:
  covered by the GM command `/reload specs` (`SkillBase.LoadSpecializations()`) - no restart.
- `StarterEquipment`: cached once at startup (`CreationStartupEquipment`), **needs a full
  restart** - no live-reload path exists for this one.
- `GlobalConstants.STARTING_CLASSES_DICT`, `eCharacterClass` itself, any other C#/enum change:
  needs a rebuild **and** restart, same as any other code change (see below).

## Part 3: server source changes (if the class itself, not just its ID, is changing)

- `eCharacterClass.cs`: the enum entry. If retiring a class off a slot rather than deleting it,
  give it a new dormant ID rather than removing the entry - `StormforgedRules`-style helper code
  that resolves by `(int)eCharacterClass.X` then keeps working unchanged; nothing needs to know the
  new numeric value except this one line.
- If the class is being **promoted from a loose `bin/scripts/` runtime script into compiled
  source** (needed for a native-slot class, since `GlobalConstants.STARTING_CLASSES_DICT` is a
  static field that can't read a loose script's ID): move its `.cs` file and trainer into
  `playerclasses/<realm>/` and `trainer/<realm>/` proper, add them to the `.csproj` build (or just
  drop them in the folder if the project uses implicit globbing - check first), and **remove the
  stale copy from `bin/scripts/`** on every deployed server, or the two will conflict.
- `GlobalConstants.STARTING_CLASSES_DICT`: must list the *current* class for its realm, not
  whatever it used to be - this exact mistake ("Wrong class: 64, realm:2" in the server log) blocked
  all new character creation for Drengr until fixed.
- **Search every test file for the old literal ID, not just the ones you remember editing.** This
  bit twice: the first renumbering pass fixed `UT_StormSovereign.cs` and `UT_CustomClassSlots.cs`
  (because those were the files being actively worked on) but missed `UT_Stormforged.cs` and
  `UT_Pendragon.cs`, which had hardcoded the same old ID in unrelated-looking assertions
  (`StormforgedRules.OverviewClass(...)`, `CreationMapsOnlyEnabledMidgardMauler(...)`) and weren't
  caught until a full, unfiltered `dotnet test` run much later. Run:
  `grep -rn '\b<old-id>\b' source/server/Tests/` before considering the change done, and run the
  **entire** test suite (not a `--filter`-narrowed subset) at least once before shipping.
- If the class has its own quirks beyond a stock clone (Drengr's `GetAutotrainableSkills()`
  override, custom pet/spell handlers, etc.), those live in the class's own `.cs`/handler files,
  same as any other C# change - nothing in this document is special there.

## Part 4: deploy and verify

1. Rebuild (`dotnet build -c Release`), run the full test suite, back up the currently-deployed
   `GameServer.dll`/`.pdb` with a timestamp, deploy the new build, verify the deployed file's hash
   matches what was just built.
2. Check whether anything from Part 2's caching table needs a restart (`StarterEquipment` or any
   C#/enum change always does; `/reload specs` alone is enough for the rest).
3. Coordinate server stop/start with whoever else might also restart it - overlapping restart
   attempts have caused a real `database is locked` crash here before.
4. In-game, check: the class is selectable at creation (if a native slot was involved) or promotable
   via its trainer (if not); starting gear and armor type match the class's actual level-1
   eligibility, not some other class's; every weapon type it trains actually shows styles past
   level 1; and (if an existing character was renumbered) that character still logs in and its
   `SerializedSpecs` string still parses (a stale spec keyname in a saved character can
   null-deref `SkillBase.GetSpecialization` on login).
