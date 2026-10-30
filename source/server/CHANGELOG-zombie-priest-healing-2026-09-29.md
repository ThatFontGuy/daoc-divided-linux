# Zombie Priest healing repair - Claude version only

- Fixed `SummonDruidPet.GetPetBrain`: real `GamePlayer` owners do not implement the bot-only `IGamePlayer` interface. They now receive `SluaghbinderPetBrain`, allowing the priest to stop melee for its existing below-75% HoT and below-50% direct-heal priorities.
- Kept the existing gamebot/companion selection and autonomous casting behavior. No spell/database values, pet body/stat selection, damage, health balance, or other pet classes were changed.
- Updated priest tests to use the production brain factory instead of manually constructing the desired brain. Added player-owner, companion-target threshold, active-melee interruption, and unchanged-Druid coverage; retained bot/no-client and scaled-spell cases. Test spells now use the live power costs.

The player summon-selection defect predates Claude's changes. Both heals remain valid and assigned; Claude changed their targeting from group to single ally. The previous tests bypassed summon selection and therefore missed the player defect. This is a narrowly scoped wiring repair, not a claim that every historical healing observation has been reproduced.

Validation: eight player-owner cases reproduced the wrong-brain failure before the production fix. Afterwards, 24 priest-focused tests and the complete 2,170-test suite passed. Release build: zero errors (existing warnings remain). No live-client healing check has been performed after deployment.

Restart the Claude version and re-summon the priest to obtain the corrected brain. The original `new class test`, multiplayer installation, and GitHub were not changed.
