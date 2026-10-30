# Character passport: take a toon to a friend's world and back

Status: design, 2026-10-27. Build step 1 (Join Friend and Host for Friends) is in the launcher, see
[PLAY-WITH-FRIENDS.md](PLAY-WITH-FRIENDS.md); the passport itself is not built yet. The earlier feasibility study,
[PORTABLE-CHARACTER-COOP-RESEARCH.md](PORTABLE-CHARACTER-COOP-RESEARCH.md), reaches the same model.

## Goal

A character lives in your own save. You can take it to a friend's hosted world with
everything it carries, play there, and bring it home with everything it earned. At any moment
the character is playable in exactly one world, so nothing can be duplicated by going back and forth.

## Building blocks we reuse

| Piece | Where | What we take |
|---|---|---|
| Join Friend | `stefanrows/OfflineDAoC`, commits `62450ea9` (Tailscale guest join) and `4e035020` (remembered details, DPAPI password) | The client-only `--join` launcher path, host address / account form, reachability check on TCP 10300, `docs/TAILSCALE_COOP.md` host setup |
| Progress import | `source/tools/OfflineDaoc.ProgressImport` | Table list (`progress-policy.json`), column-intersection copying, backups, integrity checks, account password hash (`ImportEngine.HashPassword`) |
| Game API host | `source/server/GameServer/API/ApiHost.cs` | Kestrel already in the server process; the Passport Desk is a second, small listener built the same way |

Join Friend on its own does not move characters:
stefanrows' doc says characters made on a host stay in the host's save. The passport adds that part.

## Terms

- **Home**: the player's own install. The character's real record lives here.
- **Host**: the friend's install, running its server for others over Tailscale.
- **Passport**: one file holding one character and what it carries.
- **Trip**: one round trip, named by a `trip_id` (GUID). Home and host both remember the current trip id.
  A passport is accepted only with the trip id the receiver expects, so an old passport can never be replayed.

## What a character is in the save

All ids below are the character's `DOLCharacters_ID` (a GUID) unless noted.

| Table | Key column | Travels? |
|---|---|---|
| `DOLCharacters` | `DOLCharacters_ID` | Yes. `GuildID`, `GuildRank`, `GuildNote` cleared on the way out (see Guilds) |
| `DOLCharactersXCustomParam` | `DOLCharactersObjectId` | Yes, except our own `passport.*` keys |
| `CharacterXDataQuest`, `Quest`, `Task`, `CharacterXMasterLevel` | `Character_ID` | Yes |
| `CharacterXOneTimeDrop`, `FactionAggroLevel` | `CharacterID` | Yes |
| `PlayerXEffect` | `ChardID` | Yes |
| `TimeXLevel` | `Character_ID` | Yes |
| `Inventory` | `OwnerID` = character id | Yes: worn, backpack and the character's own bank vault |
| `ItemUnique` | `Id_nb` = `Inventory.UTemplate_Id` | Yes, every row the inventory references |
| `ItemTemplate` | `Id_nb` = `Inventory.ITemplate_Id` | The row is copied into the passport. The receiver uses its own row when it has one with that id; otherwise it adds the carried row as an `ItemUnique` and points the item at it |
| `AccountXMoney` | `AccountId` + `Realm` | Not copied. Money moves as a **purse** (below) |
| `AccountXCrafting` | `AccountId` + `Realm` | Not copied. Crafting skill is merged as the higher value per skill (below) |
| `Inventory` with `OwnerID` = `<account>_<realm>` | account vault | **Stays home** |
| `DBHouse` and house tables | `OwnerID` | **Stays home** |
| `Guild*` | | **Stays home** |
| `account_companions`, `bot_profiles` (`OwnerCharacterID`), `offline_world_bots` | | **Stays home** in version 1 (see Later) |
| `PlayerBoats` | `BoatOwner` | Stays home |

Money and crafting are account-wide per realm in this server (`GamePlayer` reads `AccountXMoney`
by account and realm; `/player/.../tradeskills` reads `AccountXCrafting`). That's why they need rules
of their own instead of a plain copy.

## Passport file

`<Name>-<trip_id>.odpassport`, a zip:

```
manifest.json
  format: 1
  trip_id, character_id, name, realm, class, level
  direction: "outbound" (home → host) or "return" (host → home)
  from_world: { build: "0.37-stormforged", fingerprint, server_name }
  purse: { realm, copper }         # total in copper
  crafting: { realm, skills }      # SerializedCraftingSkills, CraftingPrimarySkill
  created_utc
  payload_sha256
rows/<Table>.json                  # [{column: value}, ...] per table above
templates/ItemTemplate.json        # template rows the inventory uses
```

JSON rows plus column intersection let a passport move between slightly different builds, as
`ImportEngine` does. A column the receiver lacks is dropped and listed in the report. A table the
receiver lacks blocks the import only if it has rows.

The SHA-256 catches damage in transit. It is not a security seal. Friends' worlds are trusted: a
host who edits a passport can give a toon anything, the same as a GM.

## The round trip

### 1. Leave home (export + lock)

The home server must be stopped. This runs in the guest's launcher on the home save.

1. Back up `runtime\data\opendaoc.sqlite3.db` to `runtime\passport-backups\<time>-<name>-out\`.
2. Check the character isn't already away and doesn't have an unfinished return.
3. Ask for the purse: how much of the realm wallet to take (default: all of it).
4. In one transaction:
   - write the passport (direction `outbound`);
   - take the purse out of the home `AccountXMoney` row;
   - add custom params `passport.away = <trip_id>`, `passport.host = <host name/address>`,
     `passport.guild = <GuildID>|<GuildRank>`, `passport.left_utc`.
5. Keep the departure snapshot (the backup and the passport) for a recall.

The home rows stay in place, frozen. Nothing is deleted at home until the character comes back.

### 2. The lock at home

The server refuses a character with `passport.away` set:

- `WorldInitRequestHandler` (the `loadPlayer` path): don't load the player. Tell them
  "<Name> is visiting <host>. Use Come Home in the launcher." and send them back to the character screen.
- `CharacterCreateRequestHandler.HandleDeleteCharacterRequest`: refuse to delete, like the existing
  "has a house" check.
- Rename, character transfer and any GM or bot tooling that writes the character: refuse.
- Progress import and World Workshop copy the flag along and say the character is away.

### 3. Arrive at the host (Passport Desk)

The host server runs a **Passport Desk**: a small HTTP listener inside the server process, so the
import goes through the live server and never fights it over the SQLite file.

- Off by default. Server property `PASSPORT_DESK_ENABLED`, port `PASSPORT_DESK_PORT` (default 10310).
- It binds to the same address as the game listener (`IP` in `serverconfig.xml`). On a normal
  single-player install that is `127.0.0.1`, so nothing is exposed. Hosting changes it to the
  Tailscale address (see Hosting).
- Every call uses the guest's **host** account and password (HTTP Basic over the Tailscale tunnel),
  checked against `Account.Password` with the same hash as `ImportEngine.HashPassword`. If
  `AutoAccountCreation` is on and the account doesn't exist, `arrive` creates it, as a first game login would.

`POST /passport/arrive` (body: passport)
1. The guest account must not be logged in.
2. Checks:
   - the class exists and is allowed on this host (custom classes such as Stormforged need a
     Stormforged host);
   - the character id is not already on this host, unless it is this account's earlier visitor with no trip open;
   - the name is free (if not, refuse with `name_taken`; the launcher asks for a visiting name and sends it again);
   - there is a free character slot in that realm (pick the first free `AccountSlot`).
3. In one transaction:
   - insert the rows with `AccountName` = the guest's host account;
   - map item templates as described in the table above;
   - add the purse to the host `AccountXMoney` for that realm;
   - merge crafting, taking the higher value for each skill;
   - restore any host guild remembered from an earlier visit (`passport_visits.host_guild`), if that guild still exists;
   - record the trip in a new `passport_visits` table
     (`character_id`, `account`, `trip_id`, `state` = `visiting`, `arrived_utc`, `host_guild`, `home_name`).
4. Position: keep the saved spot if its region exists on the host; otherwise put the character at its bind point.
   If that is also missing, use the realm's default start.
5. Reply `{ ok, slot, name, report }`.

The guest then logs in through Join Friend and plays normally. The visitor is an ordinary
character on the host; the host can group, trade and guild with it.

Visitors can't own houses on the host: buying one is refused while a `passport_visits` row is `visiting`.
That keeps the return clean.

### 4. Leave the host (check out)

`POST /passport/depart` (body: `character_id`, `trip_id`, `purse_copper`)
1. The guest account must not be logged in, and the trip must be `visiting`.
2. In one transaction:
   - export the character (direction `return`, same `trip_id`);
   - take the purse out of the host realm wallet (capped at what is there);
   - remember the host guild in `passport_visits.host_guild`, then clear `GuildID`;
   - set `state` = `departing`.
   A `departing` character is locked on the host the same way it was locked at home.
3. Reply with the passport.

`POST /passport/depart/confirm` (`character_id`, `trip_id`)
- Sent by the launcher once the passport is safely written to disk at home.
- The host deletes the character's rows (the same tables as export, plus `ItemUnique` rows nothing
  else references) and sets `state` = `returned`.
- Until it is confirmed, `depart` can be called again and returns the same passport.

`GET /passport/visitors`
- Lists this account's visitors and their states, so the launcher can show "Eriabeth is visiting Bob's world".

### 5. Come home (import + unlock)

The home server must be stopped. This runs in the guest's launcher.

1. Write the returned passport to `%LOCALAPPDATA%\OfflineDAoC\passports\pending\` first, then send
   `depart/confirm`. If the import below fails, the pending file is retried on the next launch.
2. Check that `trip_id` equals the home `passport.away`. A mismatch (an old or cancelled trip) is refused.
3. Back up the save to `runtime\passport-backups\<time>-<name>-in\`.
4. In one transaction:
   - delete the frozen home rows for this character (the export tables);
   - insert the returned rows;
   - map item templates as on the host;
   - add the returned purse to the home `AccountXMoney`;
   - merge crafting, taking the higher value for each skill;
   - restore the home guild from `passport.guild` if that guild still exists;
   - remove the `passport.*` params;
   - set `AccountName` and `AccountSlot` back to the home values.
5. Check row counts against the passport, as ImportEngine does, then move the pending file to
   `passports\done\`. Write `PASSPORT RESULT.txt` in the backup folder.

### 6. If the friend is gone: recall

When the host can't be reached, or the guest gives up, **Recall** in the launcher:
- restores the character from the departure snapshot: its rows as they were when it left, plus the purse;
- clears the lock and sets `passport.cancelled = <trip_id>`, so a late return of that trip is refused;
- warns clearly that everything earned on that trip is lost.

## Money: the purse

The realm wallet is shared by all the account's characters in that realm, so it can't simply be copied.

- **Leaving home**: the player picks how much to carry. That amount leaves the home wallet.
- **Arriving**: the purse joins the guest's host wallet for that realm.
- **Leaving the host**: the player picks how much to bring back. The default is the whole host
  wallet if this visitor is the guest's only character in that realm there.
- **Coming home**: the purse joins the home wallet.

Coin is only ever moved, never copied. Alts at home keep the rest of the wallet while the traveller is away.

## Crafting

Crafting skill is account-wide per realm. It is merged by taking the higher value for each skill, in
both directions, and never lowered. Skill can't be traded, so this can't be abused for duplication.

## Hosting (one-time host setup)

Built in step 1, see [PLAY-WITH-FRIENDS.md](PLAY-WITH-FRIENDS.md). Host for Friends sets `IP`/`UdpIP` to
`0.0.0.0`, so the host's own client keeps using 127.0.0.1, and leaves `RegionIP` at 127.0.0.1 (the server answers each
client with the address it connected to). Firewall rules tied to `CoreServer.exe` admit only Tailscale and the
local subnet. Step 4 adds the Passport Desk's TCP 10310 to the same rules and turns the desk on with hosting.

## Launcher (guest side)

The Join Friend window gets:

- **Bring a character**: a list of local characters (read from the home save; the home server must
  be stopped), with a purse field. JOIN FRIEND exports, locks and uploads (`arrive`), then starts the
  client against the host. If the upload fails, the trip is cancelled and the character unlocked right away.
- Characters already visiting this host (from `GET /visitors`) skip the export and just connect.
- **Come home**: `depart` → save pending → `confirm` → import → unlock.
- **Recall**: the escape hatch described in step 6.
- On start, any file in `passports\pending\` is imported before anything else.

The main launcher's character list shows "away at <host>" for locked characters.

## Code layout

| New | Purpose |
|---|---|
| `source/tools/OfflineDaoc.Passport/` | Shared library: passport format, `Export`, `Import`, `Remove`, item-template mapping, purse and crafting merge. Plain ADO.NET over SQLite with a table policy file, like ImportEngine |
| `source/tools/OfflineDaoc.Passport.Cli/` | `inspect`, `export`, `import`, `recall` for testing and manual use |
| `GameServer/passport/PassportDesk.cs` | Kestrel listener and the four endpoints; calls the shared library on the server's database inside a server-side lock |
| `GameServer/passport/PassportLock.cs` | `IsAway(character)`, used by the world-init, delete and rename hooks |
| `passport_visits` table | Host-side trip records |
| Launcher: `JoinFriendForm.cs`, `JoinFriendProfile.cs` (ported), `PassportPanel.cs`, `HostForFriends.cs` | Guest and host UI |

The server writes through the shared library while it is running. That is safe because the desk
only touches characters whose account isn't logged in and holds a desk-wide lock. The server loads
an account's characters at login, so it reads them fresh.

## Build order

1. **Join Friend port.** Bring over `--join`, the form and its profile; adapt them to our launcher; add
   Host for Friends. Built, with automated tests; done when two PCs play together in one world over Tailscale (not yet checked).
2. **Passport library and CLI.** Export and import with both servers stopped, moving the file by hand.
   Done when a round trip of a Stormforged character with gear, quests, money and crafting comes
   back row-for-row identical except for what was earned. This alone already meets the goal, manually.
3. **Home lock.** World-init, delete and rename hooks, plus recall.
4. **Passport Desk.** Server endpoints and `passport_visits`; arrive and depart while the host keeps playing.
5. **Launcher flow.** Bring a character, Come home, pending retry, "away" display.

## Tests

- Library: round trip on copies of real saves (Classic, Stormforged, AI-Test). A second trip with
  the same `trip_id` is refused. A missing item template is converted to an `ItemUnique`. The purse
  is conserved: home + host totals stay the same across a trip. Crafting only goes up.
- Lock: a locked character can't enter the world, be deleted or be renamed.
- Desk: wrong password, guest logged in, name taken, class not allowed, double depart, confirm without depart.
- Two-PC test: Stormforged home → Stormforged host, kill things, loot, level, come home, check it all came back.

## Later

- Bring companions along: `account_companions` and their bot characters as extra passport entries.
- Hosts that only accept visitors at or under a level, or with certain classes.
- An optional per-home HMAC on returned passports, if friends ever want tamper evidence.
