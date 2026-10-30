# September 11 audit fixes — deployed

The server was stopped for deployment and has been left stopped. Changes address the five audit priorities and remove dragon combat teleports/drops. No account, character, inventory database, monster spawn, difficulty, class balance, client, launcher or navigation-mesh files were edited.

## 1. Group/watchdog exceptions

The audit recorded 67 null-key exceptions in the group/watchdog path. A bot could leave its group between two reads of its membership. The exception handler could then remove the bot from the world.

The watchdog now captures membership once. Group-session lookups reject missing membership safely, and the main group pulse retains one captured group reference. This fixes the exception path; it does not turn off recovery for genuinely stuck travelers or extend meetup/task deadlines.

## 2. Inventory save failures

A duplicate inventory insert could leave SQLite's reused statement unusable. Later rows then failed with API misuse, and successful earlier rows could lose their in-memory saved acknowledgement. That encouraged the same duplicate insert on the next flush.

Failed statements are now discarded before the remaining rows are processed. Successful rows keep their acknowledgement. Bot inventory saves use the shared writer lock, and recovery of a previously inserted item requires matching item identity, owner, template and count, with neither copy listed on a housing lot. Items are not given new IDs to hide conflicts, deleted, or transferred between owners.

A real temporary SQLite test confirms that a duplicate between two valid rows does not prevent either valid row from being saved.

## 3. Returning from enemy frontiers

The audit found 777 recoveries across three foreign-frontier return destinations. Bots switching back to PvE could try an inappropriate walking return route.

They now use their realm's real frontier porter and return medallion. PvE members returning from different frontiers can board individually before their normal group meetup; RvR warband boarding remains together. A returning bot with a full backpack can sell one ordinary disposable item at the real medallion merchant to make room. Protected equipment/upgrades are not discarded. Relic-carrier restrictions remain.

## 4. Cursed Tomb and Spraggon Den groups

The tested trouble spots have complete installed navigation corridors. Two behavior problems were found:

- Followers could stop at a corridor monster more than 500 units from the leader. The tank was then forbidden to clear that monster because the followers were outside the same 500-unit pull gate. Only mandatory dungeon corridor clearing now permits a bounded 1,100-unit gathering radius. Ordinary pulls remain at 500. Full membership, casualty, resource and designated-puller checks remain.
- During group combat, the travel controller could hold members before their combat AI ran. Members can now assist against a nearby enemy that another party member is already fighting, then use their normal combat AI for attacks, healing, pets and movement into range. This does not choose a new grind objective or initiate an unrelated pull.

No monster difficulty was reduced. Deaths caused by genuinely hard packs can still happen.

## 5. Service/meetup travel blockers

Glibryn was being selected as a normal merchant even though he is in housing and the audited location has no usable navigation. Housing merchants are now excluded from normal bot service selection; the NPC remains available to players.

At a broker, an item another buyer had already purchased could leave a bot waiting on its old cached shopping decision. A completed service check with nothing to do now invalidates that bot's cached decision immediately. The same applies after a merchant check with no transaction. This is a local cache invalidation, not a server-wide inventory rescan. The persistence fix also addresses failed transaction/save chains.

The Isle of Glass approach was checked, not remeshed: it has a complete path to the real portal. Its 87 corrections involved 86 bots, so that count alone did not establish a repeated per-bot deadlock. Its existing bounded recovery remains; successful travel through it still needs watching live.

## Dragons

Removed player teleport/throw callbacks and their combat schedules from Golestandt, Gjalpinulva and Cuuldurach. None will use those callbacks to scatter players or lift/drop them. Normal dragon patrol flight, landing, melee, breath and other attacks remain unchanged. Their existing lair geometry/range fixes were retained.

## Verification and limits

- Release build succeeded.
- 1,453 regular automated tests passed, including new null-membership, inventory ownership and partial-insert regression checks.
- Four separate installed-mesh corridor checks passed: Isle of Glass, two Cursed Tomb paths, and Spraggon Den.
- The native probe initially exposed a test-fixture unload/reload lifetime problem; it was corrected to retain each loaded mesh for the fixture. No live-server navigation code was changed for that.
- GameServer and CoreDatabase DLL/PDB files were installed in runtime root and lib, with matching hashes.
- Rollback copies: `C:/Users/thedo/Desktop/Offline DAoC/runtime/server/rollback-september11-audit-20260911-203931`.

The server was not launched for a live population test. These checks cannot promise zero regressions or prove that every historical recovery disappears. The next live run should confirm reduced save errors, foreign-frontier recoveries, stationary dungeon parties and service waits.
