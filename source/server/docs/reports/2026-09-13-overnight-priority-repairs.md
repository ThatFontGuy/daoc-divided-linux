# September 13 overnight-priority repairs

Scope: the September 12 19:00 to September 13 02:40 local-time audit. Server and client were stopped during deployment. No monster rows, levels, difficulty, drops, character records, or navigation mesh files were edited.

## 1. Group watchdog handling

- Nearby members of a full autonomous PvE party now share evidence of progress. A support character can stand still while the leader travels or the party earns experience without needing personal coin/XP changes to satisfy its individual watchdog.
- Sampling is limited to once per party per five seconds and uses memory only. Protection requires the member to remain within the existing 500-unit cohesion radius in the same region. It expires after fifteen minutes without shared movement/experience progress. Existing combat, staging, resurrection and task deadlines remain in place.
- When an individual really requires relocation, the coordinator ends the locked PvE party explicitly before relocation. The outcome records the actual recovery reason instead of leaving the others to discover a missing member later.
- This does not extend protection to distant stranded members, player-led companions, or RvR sessions.

## 2. Dungeon target access and searching

- Empty dungeon searches no longer send bots to random nearby mesh points, which can be in another room or on another floor.
- Searches prefer a living monster with the same assigned name and a proven reachable approach. The same goal remains assigned. Groups retain their coordinated anchor update, existing wait period, formation, corridor-clearing and rest rules.
- Solo searches update the same goal's search anchor so the travel controller does not immediately send them back to the old location.
- Expensive search-anchor work is limited to once per fifteen seconds per searching controller, with at most sixteen live candidates considered before the existing catalog fallback.
- Dungeon pull eligibility can try another melee-range approach when the nearest polygon fails. Range, line of sight and a connected return path are still required. No through-wall attacks were enabled.
- Read-only native tests checked the installed configured cave-spider, spraggonix and pelagian-crab goal points from the sampled Cursed Tomb, Spraggon and Koalinth locations. Legacy NPC rows already absent from the verified bot-goal catalog were not added or changed. This is not a claim that every old NPC row is reachable.
- Deaths caused by genuinely difficult corridor encounters remain possible; difficulty was not reduced.

## 3. Meetup travel

- An autonomous PvE member within 2,000 units of its meetup waypoint finishes on foot instead of taking another cached horse detour away from the meetup.
- A pending meetup horse approach has an absolute two-minute budget. Walking back and forth no longer resets that budget. On expiry the same rendezvous remains the destination and the existing failed-stable cooldown applies.
- Player horse travel, non-meetup travel, paid tickets, refunds, active rides, and RvR group rules were not changed.
- Formation attendance radii were not loosened, and the full eight-member rule remains.

## 4. Adalyn / Realm Exchange

- Arrival now clears an obsolete attack stance only when the bot is not in combat, has no aggro, and is not casting. Previously the service controller could show Ready while the transaction layer refused an attacking actor.
- The reached broker is still passed directly to the existing real transaction code. Inventory ownership, purchases, listing limits, prices and ledger logic are unchanged.
- Added rate-limited diagnostics after a service remains unhandled. They identify grouping, combat, attack stance, casting, movement, capital eligibility, service phase, expiry and cooldown. They do not dump inventory or perform database scans.
- Important limitation: the old Ready-to-use logs did not record which transaction guard rejected each historical Adalyn visit. The stale-stance path is repaired, but only the next live run can establish whether another blocker also contributed to those 77 recoveries. This should not be described as a proven reconstruction of every historical Adalyn failure.

## 5. Shared approach / frontier hotspots

- Recovery first tries a short destination from the actual complete navmesh path. It no longer depends solely on straight geometric side steps, which failed at the audited Lough Derg, Domnann and Campacorentin bends despite connected routes.
- The short destination is issued through PathTo, not direct walking or teleportation. Close route bends use a correspondingly smaller completion radius so recovery does not declare success before moving.
- Installed native checks reproduced connected paths and validated the new recovery destinations for dergan, sporite, blodfelag, bloated-spider and Hadrian samples.
- The Emain sample at 474010,318918,5786 genuinely lies on a small disconnected surface. Added one tightly bounded recovery signature: within 64 horizontal and 64 vertical units of that sample, after normal recovery fails. Its adjacent destination is under 100 units away and must prove its onward path and local exit at runtime. It does not add a general frontier wall/gate shortcut.

## Verification and limits

- Release build: successful, zero compile errors. Existing repository warnings remain.
- Full ordinary test suite: 1,491 passed, zero failed. Explicit installed-environment tests are separate from that count.
- New explicit installed native-route test: passed, including the Emain signature's height exclusion, nearby escape, onward connectivity, configured dungeon goals, and short recovery destinations.
- Server/client were not launched for gameplay testing. Runtime AI interactions, throughput under population load, and recurrence rates must be checked in the next live run. Zero regressions cannot honestly be guaranteed by offline tests alone.
- Deployment uses the existing stopped-process checks, DLL/PDB rollback copies, and before/after file hashes. Only GameServer.dll and GameServer.pdb in the runtime root and lib directory are replaced.
