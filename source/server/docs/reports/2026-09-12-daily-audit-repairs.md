# September 12 daily-audit repairs

## What changed

1. **Frontier travel and return-home loops**

   A delayed path failure from an old destination no longer counts as a failure of a newly chosen destination. The logs contained an Emain recovery whose failed destination was approximately 48,000 units from its current destination. Failures of intermediate steps on an unchanged route still count normally.

   Bots now approach frontier medallion merchants using a connected point within real interaction range, rather than requiring the merchant's exact standing coordinates. Returning PvE/service bots can board with their real home medallion. Previously boarding required an RvR assignment even though PvE return-home travel was implemented. The home-passage intent also permits the existing friendly keep-door interaction while approaching the ticket merchant. Enemy doors, ticket payment, combat restrictions, relic restrictions, and bounded departure batches remain in place.

2. **Camelot Realm Exchange handoff**

   After reaching the broker, the controller stops any leftover follow order and hands that exact broker to the existing transaction code. It no longer depends solely on an earlier AI turn independently finding the same NPC while the bot may still be moving. Realm, distance, combat, inventory, listing, payment, and transaction checks remain unchanged. Accounts, money, inventory rows, and listings were not edited.

   The old logs prove bots stayed at Adalyn, but do not expose every rejected transaction condition. This handoff correction needs confirmation at Adalyn in the next live run; it is not proof that every possible exchange stall has been eliminated.

3. **Timed group meetups and horse detours**

   During initial PvE assembly only, the first horse must be within roughly two minutes' straight-line walking distance. The audit included a bot trying to reach Vuloch from around 150,000 units away. That kind of first-horse detour can consume the meetup window. Nearby horses and later horse-network connections remain available; otherwise the bot continues toward its actual meetup and can reconsider horses along the way.

   Actual horse routes, speed, mounting, dismounting, player horse synchronization, ordinary solo travel, and assembled-party walking were not changed. This is a bounded route-choice improvement, not a claim that every West Downs approach is now proven failure-free.

4. **Spindelhalla's unsafe husk goals**

   The entrance-to-husk mesh route exists, but passes aggressive level-36–43 monsters before reaching level-10–11 husks. These husks are no longer offered as autonomous grind objectives. This avoids sending low-level bots into a high-level dungeon based only on the final monster's level. All husks and other monsters remain present with unchanged levels, difficulty, loot, and player access. Other Spindelhalla goals remain available.

5. **Dungeon casualty recovery and Vendo's exit**

   Dungeon resurrectors check whether they can see a corpse before reserving it. If a corpse is nearby but behind a wall, out-of-combat recovery can approach it using the existing movement system instead of repeatedly attempting a cast from the same blocked position. Combat resurrection still does not send a healer chasing a distant corpse.

   A resurrection that started before the one-minute release deadline gets a bounded opportunity to finish. New casts after the deadline cannot extend the wait forever. Failed group resurrection logs now include corpse location and each resurrector's life state, region, distance, power, casting state, and interruption state. This is one diagnostic entry when a group fails, not an added polling service.

   Vendo exit 50 had a connected approach but failed the visibility test against the raw doorway coordinates. It now uses the same tightly bounded, bidirectionally connected, same-floor exit check already used for Koalinth exit 57. Other doors and portals do not inherit that exception. Cursed Tomb and Koalinth receive the shared casualty-access improvements; their working entry routes were not rewritten.

## Verification and limits

- Full Release test suite: **1,487 passed, zero failed**.
- Separate read-only installed-mesh probe passed, including Vendo/Koalinth exit checks and wrong-exit/wrong-height rejection checks, the sampled Hadrian merchant approach, and Spindelhalla access evidence.
- No production database, monster, navmesh, class-stat, loot, or client files were modified by this update.
- Tests do not establish zero regressions under every live condition. Adalyn transactions, frontier return trips, timed meetups, and sustained Cursed/Koalinth group progress need confirmation in the next live run. Difficulty-related defeats are intentionally still possible.
