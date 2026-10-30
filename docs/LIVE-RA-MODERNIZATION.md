# Live realm-ability modernization audit

Research checked October 23, 2026. This is an implementation audit and migration plan, not a claim that the full live RA system is already installed. The separate Tireless update implements the owner's explicit free-at-level-one rule. Trainer, NPC-equipment, starter armor and item records are outside this change.

## Which live version is the target?

The official patch index identifies 1.129b as its latest published live release and lists 1.130a separately as Pendragon testing. Use confirmed live changes through 1.129b, rather than assuming announced test changes shipped. Sources can lag, so record the exact baseline for each implemented ability.

The standalone official RA reference table is useful for the overall 9/5-rank framework but is not authoritative for every current effect or cooldown. For example, its old RR5 names/effects and 15-minute timers conflict with later live patch notes. Enchanter changes already appear in 1.108; later Hunter, Warlock and Vampiir notes also supersede that table.

## Installed system

- `ClassXRealmAbility_Atlas` exposes primarily Atlas old-frontiers implementations. The modern passive and active rank flags are both false.
- Atlas stat enhancements use five steps of 6/12/18/24/30, with upgrade costs 1/3/6/10/14. Their helper remains five-rank even if a parent class starts reporting nine ranks. Merely changing the flags can produce capped values and 1000-point unavailable upgrades.
- Most standard classes have no mapped executable `RR5RealmAbility` subclass. Valkyrie has Valhalla's Blessing from our completion pass. Existing RR5 source files and ability definitions are not enough: each class needs the correct mapping, implementation and free grant.
- Heretic, Bainshee, Vampiir, Warlock, and all three Mauler class slots have no mapped RA lists in the installed world.
- Some newer generic handlers already exist beside the Atlas variants, but their implementation, costs, effects, class restrictions, cooldowns, client delves and NPC/bot targeting require auditing before use.

## Verified changes to carry forward

### Rank framework (1.108 and official reference)

- Common nine-rank passives use incremental costs 1/1/2/3/3/5/5/7/7; total 34 points. Augmented stats use 4/8/12/17/22/28/34/41/48. These are not the installed Atlas five-rank amounts.
- Common five-rank actives use incremental costs 5/5/5/7/8; total 30. Abilities with special rank counts or costs need their own tables.
- Class-specific RR5 abilities are free at realm level 40 (RR5L0). They must not become purchasable substitutes or require spending points.

### Later live changes

- **1.127:** Ichor root durations become 5/7/9/12/15 seconds and are not scaled by magic resists, duration gear, or crowd-control reduction. Immunity handling and RA stun-feedback bypass also need coverage.
- **1.128:** First Aid changes to five ranks with heals 25/30/35/42.5/50% and cooldowns 600/450/300/240/180 seconds. Early Pendragon proposals differ; use the final live values. Damage RAs including Anger of the Gods, Negative Maelstrom, Thornweed Field, Volcanic Pillar and Wrath receive increases. Charge is no longer free to light tanks.
- **1.128 class access:** remove Ichor from Minstrel and Valkyrie; add it to Runemaster and Wizard. Move Static Tempest from Runemaster to Valkyrie.
- **1.128 RR5:** Warlock Boiling Cauldron gains an unresistable 30-second 50% fumble/miscast component, an eight-target limit and a ten-minute cooldown. Vampiir Mark of Prey also grants the user/group +20% melee and spell critical chance for 30 seconds.
- **1.129:** light-tank Determination costs become 1/1/2/2/3/3/3/5/5, distinct from normal passive costs. Anger of the Gods and Wrath cooldowns become 600/525/450/375/300 seconds; Negative Maelstrom and Volcanic Pillar become 900/780/675/560/450.
- **1.129 RR5:** reduce reuse to ten minutes for Armsman, Necromancer, Paladin, Sorcerer, Wizard, Warrior and Hero.
- **1.129b:** training an RA must not clear its active cooldown; Charge also gains an animation. Avoid copying the unrelated smith/trainer/armor changes into this RA migration.

### Examples of older class-specific changes that also matter

These show why a complete per-class review must go beyond the latest patch:

- Champion: Badge of Valor cooldown reduced in 1.121.
- Shaman: Restorative Mend regeneration values/timing changed in 1.121.
- Hunter: Bestial Heart in 1.125 no longer sacrifices the active pet, while retaining pet/bow restrictions. The static reference still names an older RR5.
- Thane: Chain Lightning gains a 2-second uninterruptible cast and a stronger initial hit in 1.125.
- Valewalker: Vale Defense gains a separate stronger self buffer while retaining the group buffer in 1.125.
- Wizard: Wall of Flame's pulsing all-damage buffer changes in 1.125.
- Warlock gains trainable Concentration in 1.125.

## Every standard class slot: installed coverage

Counts below were captured before the separate free-Tireless migration removes the redundant purchasable Tireless binding. An existing list does not mean its contents match live. All classes need class-access validation and a live behavior/cost pass.

| Class | Server ID | Existing RA mappings | Executable free RR5 mapping |
|---|---:|---:|---|
| Animist | 55 | 30 | Missing |
| Armsman | 2 | 32 | Missing |
| Bainshee | 39 | 0 | Missing |
| Bard | 48 | 32 | Missing |
| Berserker | 31 | 33 | Missing |
| Blademaster | 43 | 33 | Missing |
| Bonedancer | 30 | 30 | Missing |
| Cabalist | 13 | 30 | Missing |
| Champion | 45 | 34 | Missing |
| Cleric | 6 | 31 | Missing |
| Druid | 47 | 30 | Missing |
| Eldritch | 40 | 30 | Missing |
| Enchanter | 41 | 30 | Missing |
| Friar | 10 | 32 | Missing |
| Healer | 26 | 30 | Missing |
| Heretic | 33 | 0 | Missing |
| Hero | 44 | 33 | Missing |
| Hunter | 25 | 31 | Missing |
| Infiltrator | 9 | 28 | Missing |
| MaulerAlb | 60 | 0 | Missing |
| MaulerHib | 62 | 0 | Missing |
| MaulerMid | 61 | 0 | Missing |
| Mentalist | 42 | 31 | Missing |
| Mercenary | 11 | 32 | Missing |
| Minstrel | 4 | 33 | Missing |
| Necromancer | 12 | 30 | Missing |
| Nightshade | 49 | 31 | Missing |
| Paladin | 1 | 34 | Missing |
| Ranger | 50 | 31 | Missing |
| Reaver | 19 | 31 | Missing |
| Runemaster | 29 | 30 | Missing |
| Savage | 32 | 32 | Missing |
| Scout | 3 | 30 | Missing |
| Shadowblade | 23 | 29 | Missing |
| Shaman | 28 | 31 | Missing |
| Skald | 24 | 32 | Missing |
| Sorcerer | 8 | 30 | Missing |
| Spiritmaster | 27 | 31 | Missing |
| Thane | 21 | 32 | Missing |
| Theurgist | 5 | 30 | Missing |
| Valewalker | 56 | 33 | Missing |
| Valkyrie | 34 | 33 | Valhalla's Blessing |
| Vampiir | 58 | 0 | Missing |
| Warden | 46 | 35 | Missing |
| Warlock | 59 | 0 | Missing |
| Warrior | 22 | 32 | Missing |
| Wizard | 7 | 30 | Missing |

Custom Sluaghbinder and Sovereign classes have no direct live counterpart. Preserve their private keys and custom abilities; decide their shared general RA access separately instead of silently substituting a stock class or overwriting their unique RR5.

## Free Tireless update

The prior native Tireless row was class-99-only, level 5, rank 0; its Ability definition has no property-changing handler, so simply changing its class restriction would not produce regeneration.

The owner explicitly requested level one. The migration makes the universal CharacterCareer grant native Tireless rank 1 at level 1 for every class, including base/custom classes. The regeneration calculator supplies a one-point floor for players and bots while moving/in combat and avoids stacking it with stronger regen or a previously purchased Tireless point. Old purchase bindings are removed; existing learned RA records and spent points are preserved. Existing purchases can be recovered with an ordinary RA respec; a later full RA migration must account for them when calculating refunds. The universal level-one rule is the owner's rule, not asserted here as a verified live grant for all casters.

The installer applies only the three intended definition updates in one live SQLite transaction under a write lock, with an online-consistent backup and saved-progress verification. It does not replace a staged old world, so concurrent trainer/armor updates cannot be overwritten by a stale database copy. It deploys the exact tested server DLL with backups and never starts game processes.

## Proposed full conversion

1. Establish a versioned modern RA catalog: neutral stable keys, explicit costs/values/cooldowns, supported class IDs and source/version per ability. Keep Atlas definitions available for interpreting previous purchases.
2. Replace shared passive handlers and then active handlers with verified live tables and tests, including special-cost Determination, Ichor immunity behavior, damage RA targeting, and cooldown persistence. Do not enable the global rank flags against old Atlas handlers.
3. Build complete per-class access matrices, adding missing expansion lists and excluding obsolete old-frontiers actives. Apply confirmed live class swaps; mark unverified access as pending rather than guessing.
4. Audit and wire each live RR5, including changed versions and required source-effect support. Test player/group/pet/bot targeting and automatic rank-five grants.
5. Calculate old spending using old tables BEFORE replacing keys or scaling. Prepare a refundable RA-only respec/mapping for affected saved characters and bot allocations, preserving total RP, RR, ML/CL, equipment, money, levels and trainer changes. Keep custom-class private abilities intact.
6. Preview the exact definition/player migration on a copy, test and install with backups while the world is stopped. Verify training, upgrades, respec refunds, delves and cooldowns in-game.

A reliable modern catalog needs code plus data and a saved-purchase conversion. This audit intentionally does not label old handlers as live-complete or perform an unreviewed blanket respec.

## Primary sources

- [Official patch index](https://www.darkageofcamelot.com/patch-notes/)
- [RA reference framework](https://www.darkageofcamelot.com/realm-abilities/)
- [1.108 live](https://www.darkageofcamelot.com/content/patch-notes-1108)
- [1.121 live](https://www.darkageofcamelot.com/1121-live-patch-notes/)
- [1.125 live](https://www.darkageofcamelot.com/1125-live-patch-notes/)
- [1.127 live](https://www.darkageofcamelot.com/1127-live-server-patch-notes/)
- [1.128 live](https://www.darkageofcamelot.com/1128-live-server-patch-notes/)
- [1.129 live](https://www.darkageofcamelot.com/1129-live-patch-notes/)
- [1.129b live](https://www.darkageofcamelot.com/1-129b-live-patch-notes/)

Private research snapshots and parsed tables are retained in artifacts/sovereign-validation/ra-live-research.


## Shared RA implementation, October 23

The first audited conversion covers 21 existing definitions: five augmented stats, Avoidance of Magic, Mastery of Pain/Blocking/Parrying/Healing/Magery, Wild Power/Healing/Minion, Falcon's Eye, Veil Recovery, both old Determination variants, Toughness, Ethereal Bond, and First Aid. Explicit handler tables supply modern rank limits, amounts and costs without enabling global flags that would alter unaudited abilities. Toughness and Ethereal Bond now apply flat HP/power rather than legacy percentages. The old stat prerequisites are removed for converted passives, including the autonomous bot planner. Stable existing keys preserve bot active lookup and cooldown serialization. Light-tank Determination has a separate private definition (internal ID 3040) for its 25-point cost table.

Shared access is supplemented from the pinned EOD snapshot for these abilities only, including the seven class slots whose RA lists were empty. This is a baseline for shared access, **not a completed live class matrix**. Old abilities outside this audited subset remain available pending their own conversion. Custom Sovereign/Pendragon abilities are preserved. The migration refuses to reprice a player's existing old purchases; the selected test world had none at preparation time. Bot allocations are rebuilt from saved trained points through their existing planner.

`source/tools/install_modern_realm_abilities.py` previews by default. Installation takes a SQLite write lock, backs up the database and server files, changes only RA definitions/bindings plus the universal Tireless grant, verifies all 37 saved-progress tables, then installs the tested DLL in all three server locations. It never starts or stops the server. Rollback refuses to overwrite later changes. Spells, styles, trainer equipment and client assets are untouched, preserving Claude's Valkyrie visual and trainer fixes.

Still outstanding: the remaining common passives (including stealth mechanics), active abilities and cooldowns, the full per-class access audit, all class-specific RR5 behavior, and in-game validation. Do not describe this increment as complete live RA parity.

Validation: 3,188 server tests passed, including 17 focused RA/Tireless cases; four shared-migration, four Tireless/installer, and eight Valkyrie-data regression tests passed. Post-install checks verified all 123 unrelated database tables unchanged, SQLite integrity, all three installed DLL hashes, and no duplicate AoM/Determination bindings. Initial rollback backup: `artifacts/modern-client-test/backups/modern-shared-ras-20261023-203011-074800`. A subsequent RA-only alias cleanup has its own backup at `modern-shared-ras-20261023-203129-253454`. No in-game validation was performed.


## Recovery and utility pass, October 23

The audited set now contains 36 definitions (including legacy aliases). Additional conversions: Serenity (five ranks, 1/2/3/5/7 regeneration), Lifter (nine ranks, 10ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“90%), Long Wind (five ranks with correct flat sprint-cost delve), Mastery of Focus (nine ranks, existing level-50 resist-level cap), Physical Defense (nine ranks), Ignore Pain and its tank alias, Mystic Crystal Lore, Raging Power, Second Wind, Purge and its reduced alias, Concentration, Charge and Valkyrie's Charge alias. Common actives have five ranks and 5/5/5/7/8 incremental costs. Recovery executes for GameLiving actors, including NPC-backed bots. Existing bot key lookup is preserved.

Purge follows the explicit 1.108 rank table (5-second/2-second/immediate/immediate/immediate activation, 900/900/900/600/300-second reuse); the official reference's prose still describes an older three-rank system. Its delayed completion does not shorten the cooldown if the effects expire before activation, and death does not clear the timer. Existing class-specific Purge/IP keys remain bound so serialized cooldowns keep their identity. Training a recovery rank does not reset its active cooldown. Old First Aid/MCL/Augmented Constitution prerequisites are removed for the converted recovery abilities.

Charge is target-free, lasts 15 seconds and uses 900/600/300/180/90-second reuse. Four old free Charge career grants are removed as required by live 1.128. Warlock's trainable Concentration access is added from live 1.125. Client animation parity for Charge remains to be verified; no client assets are changed. Shared access still uses the pinned EOD baseline with documented overrides and is not a complete current-live class matrix.

Validation: 3,207 server tests passed; 29 focused shared/recovery tests passed, including actual resource changes, combat/sitting restrictions, no cooldown when already full, and cooldown preservation when training. Six migration tests cover unchanged visuals/trainers/progress, duplicate active removal, free Charge removal, stable legacy class keys, saved cooldown preservation, and idempotence. Installed in the selected modern test world with an automatic rollback backup; all 123 unrelated tables and all three DLL hashes were verified. No in-game validation, client-slot edits or Mauler identity changes were performed in this pass.

Remaining work includes stealth, the special five-rank passives, group/damage actives, a full class-access review, and class-specific RR5 behavior.

Recovery/utility installation backup: `backups/modern-shared-ras-20261023-204433-190587`.


## Group and direct-damage pass, October 23

Nine more definitions are converted, bringing the audited set to 45 including retained aliases: Barrier of Fortitude (old Bunker of Faith key), Bedazzling Aura (old Brilliant Aura key), Soldier's Barricade, The Empty Mind, Vehement Renewal, Ameliorating Melodies, Anger of the Gods (old Fury key), Wrath of Champions, and Volcanic Pillar. Stable keys preserve cooldown serialization; the visible old RA names are updated. Shared class access is supplemented from the same pinned EOD baseline for this subset only.

- All converted group abilities enumerate GameLiving group members, including NPC-backed bots, with living/range/region filters. The caster is excluded from Vehement Renewal and Melodies healing.
- Fortitude supplies physical absorption rather than armor factor. Aura supplies secondary magic resists; Barricade supplies secondary physical/magic resistance instead of the old armor-factor effect. These three barriers share an exclusion flag and effect category, and a blocked activation does not consume reuse. Damage-only resistance bonuses use OtherBonus to avoid shortening CC duration. Empty Mind lasts 45 seconds and affects the caster only.
- Melodies heals exactly ten times, with a three-second pulse interval and the 100/175/250/325/400 rank values. The old handler healed its caster and ran twenty pulses.
- Anger uses 15/22.5/30/37.5/45 DPS, a fixed 30-second duration, and the 1.129 cooldowns 600/525/450/375/300 seconds. Its dedicated damage-add handler avoids the ordinary weapon-damage cap and buff-spec bonus; the existing 99999 effect group preserves stacking with ordinary adds.
- Wrath is an instant 150-radius spirit PBAoE using the 1.128 damage table and 1.129 cooldowns. Rank two follows the official final notes' explicit 522.5 value (rather than silently substituting a guessed correction).
- Volcanic Pillar has 400/700/1000/1250/1500 heat damage, 500 radius, 1500 range, a two-second cast and 900/780/675/560/450-second reuse. It captures the original target, region, location and rank. Movement/control/death/range loss cancels the cast; ordinary damage does not interrupt it. Retargeting cannot redirect the pending blast.
- Both direct-damage RAs use the spell damage/attack pipeline rather than raw TakeDamage, preserving resists, absorption, ablatives and combat notifications. Their base damage and variance are explicit, and ordinary spell criticals are suppressed.

Validation: 3,217 server tests passed; seven focused group/damage tests cover real group effect application and cleanup, bot targeting, dead/distant exclusions, mutual barrier exclusion, ten-pulse healing, Empty Mind duration and damage-only resistance category, live damage/cooldown tables, and a 1500-damage heat hit reduced to 750 by 50% heat resistance. Six migration and eight Valkyrie-data tests also passed. Post-install checks verified all 123 unrelated database tables unchanged, SQLite integrity, and all three installed DLL hashes. No client files or trainer/visual rows were edited, and no in-game check was performed.

Remaining: the ground storms (Negative Maelstrom, Thornweed Field, Static Tempest), Ichor, other group/control actives, special/stealth passives, a complete live class-access audit, and class-specific RR5 updates. This increment does not establish full live parity.

Group/damage rollback backup: `backups/modern-shared-ras-20261023-205840-300020`.


## Ground storm and Ichor pass, October 23

Negative Maelstrom, Thornweed Field, Static Tempest and Ichor are now converted: 49 audited definitions including aliases. Their normal five-rank active costs are explicit. Stable old keys preserve cooldown serialization; no character allocation is silently repriced.

- Negative Maelstrom: 350 radius, 30-second cold storm, five-second pulses that ramp to the 1.128 peak values 262.5/390/525/650/775. Reuse follows 1.129: 900/780/675/560/450 seconds. The old handler's fixed 240 damage and extra debuff are removed from the modern path.
- Thornweed Field: two-second cast, 500 radius, three-second damage/snare pulses, rank damage 30/60/120/210/300 and lifetime 10/15/20/25/30 seconds. Its short 50% snare refreshes without granting root immunity or generic half-duration snare decay. The old handler used caster-level damage, a fixed 30-second lifetime and an immediate placement timer.
- Static Tempest: instant targeted stationary storm with 360 radius; three-second unresistible stuns every five seconds for 15/20/25/30/35 seconds. Its dedicated stun handler respects active Charge/SoS and innate control immunities while bypassing ordinary stun-immunity timers and duration reductions.
- Ichor: two-second cast, 1875 range, 500 radius, spirit damage 185/343.8/500/612.5/725, and fixed root durations 5/7/9/12/15 seconds per final 1.127/1.128 notes. Neither resists, duration gear nor Determination shorten/extend that root. Its root remains at full strength until it breaks/expires, rather than decaying halfway through. It uses the normal root effect/immunity machinery with scoped immunity support for NPC-backed actors at every rank. Normal damage resists/ablatives still apply to the damage component, and active movement-control immunities prevent the root.
- The modern storm object owns and stops its timer, snapshots its placement, filters friendly/dead/out-of-radius targets, and expires when its caster leaves the region/world. The timed cast helper captures location/rank/target and cancels on movement, control, region departure or invalid targets; ordinary incoming damage does not interrupt these casts.
- Live 1.128 access overrides remove Ichor from Minstrel/Valkyrie, add it to Wizard/Runemaster, remove Static Tempest from Runemaster and add it to Valkyrie.

Validation: 3,227 server tests passed, including ten focused storm tests for fixed root ranks despite reduction stats, immunity on NPC-backed actors, non-decaying field snares, distinct-target/hostility/range filters, storm radii/lifetimes/pulses/cleanup, damage ramps/cooldowns, and cast-continuation cancellation. Seven migration tests and four installer/Tireless tests passed. The installer now checks source freshness both before backup and immediately before file installation, refusing a build older than concurrent server-source edits. Post-install checks verified all 123 unrelated tables unchanged, SQLite integrity and all three server DLL hashes. No client assets, class-creation code, trainer data or Valkyrie visuals were edited in this pass. In-game checks remain pending.

Remaining: other group/control actives, special and stealth passives, full class-access validation and class-specific RR5 updates. Native storm model IDs are reused without editing client files.

Storm/control rollback backup: `backups/modern-shared-ras-20261023-211140-397170`.


## Special passive, pet and casting pass, October 23

Six further conversions bring the audited definition count to 55 including aliases: Dual Threat, Viper, Reflex Attack, Mastery of Concentration, Juggernaut and Strike Prediction. Shared access uses the pinned baseline and stable existing keys. Descriptions now identify passive abilities correctly rather than showing the old 30-second activation rules.

- Dual Threat grants 5/7/10/15/20% melee/spell critical chance, without the old extra heal-critical bonus. Existing critical calculators retain their 50% cap.
- Viper is a five-rank passive giving 25/35/50/75/100% extra mundane-poison damage, with no activation timer. The poison DoT calculation scales damage and its critical component; ordinary spell DoTs receive no Viper bonus.
- Reflex Attack becomes a five-rank passive with 10/20/30/40/50% chance on damaging melee hits. Counterattacks are unstyled, use each weapon when dual-wielding, and do not recursively trigger another Reflex Attack. The actual post-Guard/Intercept victim supplies the ability. Counter damage uses normal hit notifications rather than bypassing them.
- Mastery of Concentration grants 30 seconds of uninterrupted casting at 25/35/50/60/75% effectiveness with 600-second reuse. Damage, healing, buff/debuff magnitude and control duration are scaled in their respective paths; a root remains a root rather than becoming a weak snare. Spell/DoT strength is captured for the cast so expiry does not restore full damage to an ongoing cast. Necromancer pets read their owner's active effect. Item, potion, poison, combat-style and realm-ability effects are excluded from this class-spell reduction. Fixed Ichor root durations remain fixed.
- Juggernaut raises pet level by 10/15/20/25/30 for 60 seconds, capped at 70, with 900-second reuse. It preserves and restores the exact original level and size, avoids size overflow, and never lowers a pet already above level 70. Summoning Mastery exclusion is enforced in both directions for the legacy and current ML9 implementations.
- Strike Prediction supplies a 5/7/10/15/20% minimum evade chance for 30 seconds, instead of adding to existing evade. Its group targeting supports NPC-backed members and the combat gate now permits classes without an innate Evade ability to benefit.

Compatibility correction: `GameLiving.GetAbility<T>` previously matched exact implementation types only. It now retains exact-type preference and falls back to assignable derived types. This makes modern handlers visible to existing Long Wind, Lifter, stat-prerequisite and pet-critical consumers. Regression coverage verifies the derived-handler fallback and exact-type preference.

Focused coverage includes real passive activation/removal, poison-only scaling, Reflex trigger eligibility, three pet-level/cap restoration cases, non-additive evade, MoC/control strength and cast snapshots, and inherited ability lookup. Other actives (including Speed of Sound), stealth and class-specific RR5 work remain pending. No class-creation/client files are edited by this pass.

Validation: the final build passed all 3,236 server tests, with nine focused utility cases, seven migration tests, four installer tests and eight Valkyrie-data regression tests. One earlier suite run hit an unrelated SQLite temporary-file cleanup lock; that test passed on retry and the final full suite passed. Post-install checks verified all 123 unrelated tables unchanged, SQLite integrity, and all three DLL hashes. In-game testing remains pending.

Utility/passive rollback backup: `backups/modern-shared-ras-20261023-215543-232730`.

## Shared timed actives and Charge fix pass, October 23 (Claude)

Four live 1.108 timed actives now use modern handlers on their existing live keys: Speed of Sound, Perfect Recovery, Decimation Trap and Adrenaline Rush. The total is 59 audited definitions including aliases. All four use the five-rank 5/5/5/7/8 active costs. Patch notes after 1.108 do not change any of these values.

- Speed of Sound: group members within 2000, including companions, gamebots and their pets, move at speed 4 for 10/20/30/45/60 seconds. Reuse is 600 seconds. Members are immune to stun, mez, snare and root, but damage still lands. Each member's effect ends when that member makes a melee swing or casts a harmful class spell. Healing, item procs, poisons, style effects and realm-ability spells do not break it. The Atlas effect sped up players only; the modern effect also handles NPC-backed members. Speedwarp negation is not implemented.
- Perfect Recovery: instant resurrection at 10/25/50/75/100% health and power, 1500 range, 300-second reuse. There is no resurrection illness because it uses the realm spell line. The handler subclasses the Atlas version, so the decline-and-re-enable path still works.
- Decimation Trap: a 2-second uninterruptible cast using the shared cast helper; moving or crowd control cancels it. It places a trap that detonates on the first enemy within 350 and deals 300/450/600/750/900 energy damage in a 350 radius. Damage runs through the normal resist and combat pipeline. The trap lasts 10 minutes, or until it detonates or its caster leaves the region. Reuse is 900 seconds.
- Adrenaline Rush: doubles base melee damage, and the base damage cap with it, for 20 seconds. Reuse is 1200/900/600/450/300 seconds.
- Access follows the pinned EoD baseline:
  - Speed of Sound: Minstrel, Skald, Bard.
  - Perfect Recovery: Cleric, Healer, Heretic, Druid.
  - Decimation Trap: Wizard, Runemaster, Eldritch, Warlock.
  - Adrenaline Rush: 17 caster and healer classes.
  - The single-rank `AtlasOF_SpeedOfSound` (Minstrel) and `AtlasOF_PerfectRecovery` (Healer) bindings are removed where the live key replaces them. Bound purchases of either would trip the refund guard.
- EoD gives Adrenaline Rush only to casters and healers. The owner confirmed that matches live, so it stays.

Fixes to earlier modern work:
- `ModernCharge` reused `ChargeECSGameEffect`, whose speed code is commented out, and no stun or mez handler checked the ECS Charge effect. Modern Charge therefore gave neither speed nor control immunity, except against the Static Tempest stun. `ModernChargeEffect` now applies speed 3. `AbstractCCSpellHandler` (mez and stun) now refuses targets with an active ECS Charge or Speed of Sound, and the snare/root handler now honours ECS Charge.

Still pending (Dashing Defense and Divine Intervention are done in the next pass): Vanish and Mastery of Stealth, the class-access audit, class-specific RR5s, and in-game checks.

Validation: 3,243 server tests passed, including 7 new shared-active tests (rank tables, Perfect Recovery spell, Speed of Sound on an NPC-backed member and its break, harmful-only break filter, Charge speed and immunity, Adrenaline Rush lifetime, Decimation Trap spell). The 8 migration tests passed, including a new test for live-key access and Atlas replacement. The installer verified 37 progress tables and all three DLL hashes. No client files were changed. In-game testing is pending.

Shared-actives rollback backup: `backups/modern-shared-ras-20261023-221108-984245`.


## Dashing Defense and Divine Intervention pass, October 23 (Claude)

The last two live 1.108 shared timed actives now use modern handlers on their live keys, for 61 audited definitions including aliases. Both use the five-rank 5/5/5/7/8 active costs and a 600-second reuse.

- Dashing Defense: groupmates within 1000 of the tank, not the tank, get the effect for 10/20/30/45/60 seconds. The attack-result code already had an unused `CheckDashingDefense` slot after Guard, and it is now wired in. For each incoming attack on a covered member:
  - Only the first valid tank tries, so an attack can be blocked or parried this way once, however many tanks run the ability (live rule).
  - The tank must be alive, not crowd controlled, not sitting or casting, in the same region and within 1000 of the member.
  - Stealth openers and spells are excluded.
  - The tank uses their own parry chance (melee only) and block chance, including the normal requirement that they face the attacker.
  - A success redirects the attack to the tank the way Guard does, so the existing "blocks the attack for you" messages apply. Parries send their own two messages.
  - Shield block rounds are not consumed for these blocks.
  - If the tank has no groupmates in range, the cooldown is not used.
- Divine Intervention: groupmates within 2000, not the user, get a 20-minute buff sharing one healing pool of 1000/1500/2000/2500/3000.
  - Whenever a protected member takes damage from another living, the pool heals them at once, right after health is subtracted in `GameLiving.TakeDamage`.
  - A heal never exceeds the hit or the member's missing health.
  - When the pool is empty, every member's buff ends.
  - The heal is credited to the caster. Fatal hits are not undone.
- Access follows the pinned EoD baseline: Dashing Defense for Armsman, Warrior and Hero; Divine Intervention for Cleric, Healer, Heretic and Druid.

All six live shared timed actives are now converted.

Still pending: Vanish and Mastery of Stealth, the class-access audit, class-specific RR5s, and in-game checks. In particular, Dashing Defense's block and parry odds and the Divine Intervention pool should be checked in a real group fight.

Validation: 3,246 server tests passed. They include 3 new cases: Dashing Defense targeting and range with tank exclusion and spell exclusion, no cooldown when alone, and a shared Divine Intervention pool capped by missing health and drained across members. The 8 migration tests passed, now also covering these two keys. The installer verified 37 progress tables and all three DLL hashes. No client files were changed.

Dashing Defense / Divine Intervention rollback backup: `backups/modern-shared-ras-20261023-222044-772762`.


## Stealth pass, October 23 (Claude)

Sources: the live 1.121, 1.126 and 1.128 snapshots, plus the official 1.121B (Pendragon test server) and 1.122B live notes.

- 1.121 removed Vanish and Mastery of Stealth as realm abilities. Vanish moved into the Stealth specialization (Vanish 1/2/3 at 29/39/49 Stealth). Mastery of Stealth became Shadow Seek for assassins and a free ability for archers.
- 1.122B reduced the level-49 Vanish 3 to Vanish 2 for Infiltrator, Nightshade and Shadowblade, with a 15-minute reuse.
- 1.126 removed Shadow Seek and made Mastery of Stealth trainable again for all six stealthers. It also returned stealth detection and movement to the pre-1.121 mechanics.
- No later note brings Vanish back as a realm ability.

Changes:
- Mastery of Stealth, on the existing `AtlasOF_MasteryOfStealth` key, now uses `ModernMasteryOfStealth`. It is a nine-rank passive at the 1/1/2/3/3/5/5/7/7 costs with no Augmented Quickness prerequisite. Its display name is now "Mastery of Stealth".
  - While stealthed: +10/15/20/25/30/35/40/45/50% movement speed and +75/125/175/235/300/375/450/535/625 detection range. These are the pre-1.121 values from the live realm-ability table.
  - Camouflage cancels the detection bonus, and the bonus does not apply when both sides have Detect Hidden (assassin against assassin).
  - It applies to player detection of stealthed players and of stealthed gamebots.
  - Access: Scout, Infiltrator, Shadowblade, Hunter, Nightshade and Ranger. Hunter and Ranger were missing. The custom classes 64 and 65 keep their existing binding.
  - Bug fixed: the key was previously bound to the old three-rank `MasteryOfStealthAbility`. The stealth speed code looks up `AtlasOF_MasteryOfStealth`, so training it gave no speed at all. The detection bonus was also commented out.
- Vanish is no longer trainable. The `AtlasOF_Vanish` binding (Infiltrator) and any `Vanish` realm-ability binding are removed; bound purchases of either would trip the refund guard. The Stealth spec grants the live `Vanish` key, now `ModernVanish`, to Infiltrator, Shadowblade and Nightshade: Vanish 1 at 29 and Vanish 2 at 39.
  - On use: unbreakable stealth that detection cannot see through. It purges damage over time, bleeds, mez, stun, snares and roots, and gives crowd-control immunity while it lasts.
  - Attackers lose their target. Afterwards the user is disarmed and silenced for 15 seconds (1.121 aligned the disarm with the silence). Poisons are cured when it ends.
  - Durations and speeds: Vanish 1 is 1 second at normal speed, Vanish 2 is 2 seconds at speed 1, and Vanish 3 (kept in code, no longer granted) is 5 seconds at speed 5. Reuse is 15/15/10 minutes.
  - **Unconfirmed:** the patch notes never list per-level values for the spec version. These are the three-level values the server already had, and they match the live description's "1 to 5 seconds".
- Player stealth detection previously checked only the legacy `VanishEffect`. It now also respects the ECS Vanish effect.

Not covered (left for the class-access audit or a later pass):
- The 1.121+ stealth-spec abilities Blur, Overshadow and Heightened Awareness.
- The Atlas-only `AtlasOF_ShadowRun` binding (Shadowblade).
- Gamebots still apply the old Augmented Quickness 2 prerequisite before buying Mastery of Stealth.

Validation: 3,252 server tests passed, including 6 new stealth tests (Mastery of Stealth tables, costs and prerequisite; visibility to the speed calculator; detection counters; Vanish rank tables; Vanish speed, lockouts and speed restore). The 9 migration tests passed, including a new stealth-access and spec-grant test. The installer verified 37 progress tables and all three DLL hashes. No client files were changed. In-game testing is pending.

Stealth rollback backup: `backups/modern-shared-ras-20261023-222945-530092`.


## Class-access audit, October 23 (Claude)

Base classes now train only modern live realm abilities. The installer removed 374 bindings, and a migration test checks that no base class has a non-modern realm ability left.

- Removed: 28 realm abilities that exist only in the Atlas old-frontiers ruleset; none of them is in the live realm-ability tables. They are Armor of Faith, Arrow Salvaging, Avoid Pain, Battery of Life, Battle Yell, Bladedance, Dodger, Dualist's Reflexes, Grapple, Hail of Blows, Longshot, Majestic Will, Mastery of Archery, Mastery of Arms, Mastery of the Arcane, Mastery of the Art, Mastery of Water, Prevent Flight, Rain of Annihilation, Rain of Fire, Rain of Ice, Regeneration, See Hidden, Trip, True Sight, Volley, Whirling Dervish and Wild Arcana. ("Trip" only matched the live RR5 "Shield Trip".)
- Removed: 20 Atlas single-class actives that stood in for the live class RR5s. They are Corporeal Disintegration, Defender of the Vale, Excited Frenzy, Faith Healing, Forestheart Ambusher, Group Purge, Resilience of Death, Rune of Decimation, Severing the Tether, Shadow Run, Siege Bolt, Striking the Soul, the six Style abilities, Unquenchable Thirst and Whip of Encouragement. These classes have no class-unique active until the RR5 pass adds the live ones.
- Custom classes (Valkyrie 34, Sluaghbinder 63, Stormforged 64, Pendragon 65) were left unchanged in this first step. The owner then had them lose the old-frontiers RAs too; see the next section.
- After the audit every base class has 16 to 32 realm abilities.
- Saves: removing a binding only stops future training; the Ability rows and handlers stay, so the change is reversible. The refund guard refuses the migration if any character has bought a removed key; the test world had no realm-ability purchases.

Gamebot fix: autonomous gamebots picked their realm-ability build from their class's ability keys. Mastery of Archery marked an archer, and Mastery of Pain or Mastery of Parrying marked a melee class.
- Codex's live access had already given Mastery of Pain to every class, so every caster and healer gamebot was using the melee build.
- This audit removes Mastery of Archery, which would also have moved archers onto the melee build.
- `AutonomousBotRealmAbilities.ArchetypeOf` now uses a fixed table for the base classes: archers, the healer classes, and the casters. Every other base class up to the Maulers is melee. Custom classes still use the key test.
- Builds are rebuilt from saved points on load, so existing gamebots pick up their correct build automatically. Build steps for removed abilities are skipped, and the points go to the remaining abilities.

Validation: 3,259 server tests passed, including 7 new gamebot archetype cases. The 10 migration tests passed, including the new audit test (base-class removal, custom classes untouched, no non-modern base-class key left). The installer verified 37 progress tables and all three DLL hashes. No client files were changed. In-game testing is pending.

Remaining: the 43 class-specific RR5s, the Stealth-spec Blur, Overshadow and Heightened Awareness, and in-game validation.

Class-access audit rollback backup: `backups/modern-shared-ras-20261023-223553-433010`.


## Custom-class follow-up, October 24 (Claude)

The owner asked to remove the old-frontiers RAs from the custom classes as well, keeping their own unique abilities. The audit now removes the 28 old-frontiers keys from every class: 26 more bindings. The Atlas single-class actives are still removed from base classes only.

Kept: the Sluaghbinder's Crippling Plague, Valhalla's Blessing, Valkyrie Charge, and the Sovereign and Pendragon abilities (Crown's Resolve, Royal Fortitude, Storm Mastery, Wrath of the Crown).

Valkyrie (34) check: its list already matches live, with nothing to add.
- It has the EoD Valkyrie list with Ichor of the Deep removed and Static Tempest added (both 1.128 moves).
- Its Charge is the `Valkyrie_Charge` key.
- Its live RR5 is Valhalla's Blessing.
- It lost only Mastery of Water.

The other custom classes have no live counterpart. They now get the live shared picks of their nearest live hybrids (19 bindings, `CUSTOM_ADDITIONS` in the migration).

| Class | Compared with | Added |
|---|---|---|
| Sluaghbinder (63), STR/INT melee and pet hybrid | Champion, Valewalker | Dual Threat, Mastery of Focus, Mastery of Magery, Wild Power, Ethereal Bond, Mystic Crystal Lore, Raging Power, Mastery of Concentration, Mastery of Parrying |
| Storm Sovereign (64) and Pendragon Sovereign (65), melee, spell and stealth hybrids | Thane, Paladin | Dual Threat, Mastery of Focus, Mastery of Concentration, Raging Power, Wrath of Champions |

Left out on purpose:
- Plain Determination: these classes already have Determination (Hybrid), and the two are the same passive.
- Other classes' signature actives (Ichor, Brilliant Aura, Anger of the Gods, Vehement Renewal).

Totals now: Valkyrie 33, Sluaghbinder 30, Storm Sovereign 36, Pendragon Sovereign 36. Every non-unique custom-class realm ability is now a modern live handler.

Validation: 3,259 server tests passed. The 11 migration tests passed, including updated audit coverage and a new custom-class and Valkyrie test. The installer verified 37 progress tables and all three DLL hashes. No server code or client files changed in this step.

Custom-class rollback backup: `backups/modern-shared-ras-20261024-060544-238015`.


## Class RR5 pass, batch 1 (self-buffs), October 24 (Claude)

### How RR5s work here

- RR5 abilities are `RR5RealmAbility` handlers. They cost 0 points and require realm level 40 (RR5). A class gets one through a `ClassXRealmAbility_Atlas` binding.
- Before this pass only the Valkyrie had one (Valhalla's Blessing); every other class had no RR5.
- The handlers are the legacy DOL ones, built on the old `TimedEffect` system. On this ECS server they still run: `TimedEffect` uses ECS timers, and the events they listen to (attack finished, cast finished, attacked by enemy, dying, quit, region changed, group disband) are still raised.
- The "attacked by enemy" event fires before damage is dealt, so damage reductions in it apply.
- Several combat hooks still read these effects (Blade Barrier parry, Rune of Utter Agility and Combat Awareness evade, Allure of Death crowd-control resist, Gift of Perizor). Each RR5 is audited against live and its patches before it is bound, rather than rewritten.
- These handlers are player-only (`living as GamePlayer`). Gamebots never buy actives they cannot use, so that is not a gap for them.

### Batch 1

| RR5 | Class | Result |
|---|---|---|
| Ferocious Will | Berserker | Added the missing 1.108 bonus: +25% to all resistances (OtherBonus, so crowd-control duration is unaffected) and a 25% chance to shrug off crowd control (in the mez/stun resist calculation). |
| Blade Barrier | Blademaster | Matches live, including the 1.108 25% damage reduction. |
| Rune of Utter Agility | Runemaster | Matches live: 90% evade from all directions for 15 s. |
| Combat Awareness | Hero | Matches live: 50% evade from all directions, 50% snare, no attack penalty (1.108). |
| Soldier's Citadel | Armsman | Reuse is 10 minutes. Batch 1 first set 15 minutes from the official table; 1.129 had already cut it back to 10, so this was corrected the same day. |
| Testudo | Warrior | No longer refuses to start without a target, and damage reduction no longer needs one. The reduced movement was never implemented; it is now 50% of normal speed, ignoring speed buffs and sprint. **The 50% figure is unconfirmed**, since live only says "reduced speed". |
| Shield of Immunity | Sorcerer | Matches live: absorbs 90% of melee and archery damage for 20 s. |
| Arms Length | Eldritch | Matches live: 10 s of speed that damage cannot break, with stun and mez immunity (legacy "Charging"). |

Also fixed: Allure of Death resisted Nearsight at 100%; live says 75%, the same as other crowd control. It is not bound yet.

### Remaining RR5 roadmap

These are the live values, with the patch changes the next batches must apply.

- **Replaced on live; the stock handler is the wrong ability:**
  - Searing Pet (Enchanter) became Frenzy of the Underhill in 1.108: pet melee and cast speed +100% for 30 s, 5-minute reuse.
  - Blissful Ignorance (Savage) moved into the Savagery spec at 35 in 1.108. The new RR5 is Frenzied Assault (multiple-hit chance).
  - Remedy stopped being an RR5 in 1.108 and became a free ability at level 50 for assassins, and for archers from 1.121. It has a 5-minute reuse, no health cost, and 60 s of poison immunity.
- **Missing database row:** Restorative Mind (Shaman). The handler exists, but the Ability row does not.
- **Later patch changes to apply:**
  - Fungal Union: 50% chance of no power cost (1.108).
  - Dreamweaver: shows Dragonslayer gear (1.108).
  - Nature's Womb: silences instead of stunning (1.108).
  - Sputin's Legacy: heals at least 30% (1.108).
  - Entwining Snakes, Desperate Bowman and Shield Trip: each grants 60% speed that cannot be broken, for 15 s. Shield Trip also deals 300 damage (1.108).
  - Selective Blindness: instant (1.108), reuse 10 minutes (1.128).
  - Blinding Dust: adds 50% nearsight for 15 s (1.108).
  - Calming Notes: all enemy realm targets, 20 s (1.108).
  - Call of Darkness: uninterruptible, with stun and mez immunity while casting (1.108). 1.125 fixes the form's buffs.
  - Epiphany: adds 50% group endurance (1.108).
  - Spirit Martyr: no stun or pet sacrifice (1.108).
  - Vale Defense: 1000-point group ablative (1.108), plus a 2000-point self ablative (1.125).
  - Valhalla's Blessing: 75% chance (1.108).
  - Boiling Cauldron: 3.5 s spill and 650 damage (1.108); reuse 10 minutes, an unresistable 30 s 50% bedazzle, and 8 targets (1.128).
  - Wall of Flame: a self ablative of 700 hit points at 100%, refreshed every 2.5 s (1.108, 1.125, 1.127).
  - Badge of Valor: reuse 10 minutes (1.121).
  - Fury of Nature: 15 s (1.121).
  - Chain Lightning: 400 damage and a 2 s uninterruptible cast (1.125).
  - Sonic Barrier: also affects the Bainshee (1.128).
  - Fanaticism: 15 s (1.128).
  - Mark of Prey: adds +20% melee and spell crit for 30 s (1.128).
- **Not yet reviewed:** Allure of Death, Badge of Valor, Blinding Dust, Boiling Cauldron, Call of Darkness, Calming Notes, Chain Lightning, Desperate Bowman, Dreamweaver, Entwining Snakes, Epiphany, Fanaticism, Fungal Union, Fury of Nature, Gift of Perizor (Maulers), Mark of Prey, Minion Rescue, Nature's Womb, Resolute Minion, Retribution of the Faithful, Selective Blindness, Selfless Devotion, Shield Trip, Sonic Barrier, Soul Quench, Spirit Martyr, Sputin's Legacy, Vale Defense, Valhalla's Blessing, Wall of Flame and Whirling Staff.
  - Many of these have no outside hook. They depend on their own event handlers, which must be checked individually.

Validation: 3,263 server tests passed, including 4 new RR5 tests (live reuse timers, Ferocious Will absorption and resists added and removed, Allure resist values, Testudo speed). The 12 migration tests passed, including a new test that each audited RR5 is bound to its live class only. The installer verified 37 progress tables and all three DLL hashes. In-game testing is pending; these handlers in particular need a live check, because their effects are player-only and cannot be fully exercised by unit tests.

RR5 batch 1 rollback backup: `backups/modern-shared-ras-20261024-071245-696525`.


## RR5 research update: current live differs from the official table, October 24 (Claude)

The official realm-ability page's RR5 table (`official-ra-tables.json`) is out of date. I searched the 1.110–1.129b live patch notes from the official archive; 1.109–1.113 and 1.117 were not retrievable. Live has replaced or reworked many class RR5s since 1.108.

**Reuse correction, applied:** 1.129 cut the RR5 reuse from 15 to 10 minutes for Armsman, Necromancer, Paladin, Sorcerer, Wizard, Warrior and Hero. Soldier's Citadel, Testudo, Combat Awareness and Shield of Immunity are now 600 s and installed. Selfless Devotion, Wall of Flame and the Necromancer RR5 take the same cut when they are done.

**RR5s that are new or replaced on live.** The stock handler is the old ability, or there is none.

| Class | Current live RR5 | Source | Server state |
|---|---|---|---|
| Infiltrator | Overwhelm: 10% chance to bypass block, parry and evade, 30 s, 5-minute reuse | 1.108 | `OverwhelmAbility` exists; not audited |
| Nightshade | Shadow Shroud: 10% damage reduction and 10% chance to be missed (1.114b) | 1.108, 1.114b | `ShadowShroudAbility` exists; not audited |
| Shadowblade | Blooddrinking: heals 45% of damage dealt for 15 s | 1.108, 1.114b, 1.121, 1.121b | `BlooddrinkingAbility` exists; not audited |
| Savage | Frenzied Assault: +10% multiple-hit chance | 1.108 | Missing |
| Enchanter | Frenzy of the Underhill: pet melee and cast speed +100%, 30 s, 5 minutes | 1.108 | Missing |
| Mercenary | Dissolute Swings, renamed from Blinding Dust: 30 s, +50% crush/slash/thrust weaponskill, clears stat debuffs and blocks new ones, +25% damage taken, 10-minute reuse | 1.121c, 1.124d, 1.126, 1.128 | Missing (Blinding Dust is the old ability) |
| Hunter | Bestial Heart, replaced Entwining Snakes: Dire Wolf form, +15% melee damage, +40% celerity, +115% in-combat speed, no bow; needs an active pet, which is no longer sacrificed | 1.124, 1.124d, 1.125 | Missing |
| Ranger | Nature's Madness, replaced Desperate Bowman: 500-radius storm, 30% attack and cast slow, 30 s pet scare, 10-minute reuse | 1.124, 1.127 | Missing |
| Scout | Far Sight, replaced Shield Trip: clears range-impairing effects, nearsight immunity 60 s, +20% archery and spell range, standard shots apply a 20 s 50% nearsight, 10-minute reuse | 1.124 | Missing |
| Skald | Voice of Skadi (Epiphany moved into Battlesongs at 49 in 1.121) | 1.121, 1.127 | Missing; details not found yet |
| Thane | Mjollnir's Protection, 60 s (1.114b); Chain Lightning changed in 1.125 | 1.114b, 1.125 | Unclear which is the current RR5 |
| Necromancer | Call of Darkness, reworked: instant, 45 s, 10-minute reuse, gains every form's benefits +10%. Depends on the 1.122b Necromancer form overhaul. | 1.122b, 1.124b, 1.125 | Server has no form system |
| Shaman | Restorative Mend: 15% health, power and endurance every 2 s for 20 s | 1.121 | Missing database row |
| Warlock, Vampiir | Reworked in 1.128. Warlock: Boiling Cauldron with a bedazzle element, later 20 s at 30% fumble. Vampiir: Mark of Prey +20% crit. | 1.128, 1.129b | Existing handlers predate the rework |
| Selfless Devotion (Paladin) | Changed in 1.122b | 1.122b | Not yet read in full |

**Implication:** a faithful current-live RR5 set means new handlers for about 12 abilities, and the Necromancer RR5 depends on a class rework the server does not have. The remaining NF-era RR5s (Allure of Death, Valhalla's Blessing, Vale Defense and the others in the roadmap above) can still be audited and bound as in batch 1. The direction is the owner's call.

Batch 2 review findings so far:
- Valhalla's Blessing (75%) and Fungal Union (50%) already use the live chances. Fungal Union's reuse is 420 s; live is 300.
- Vale Defense is broken: it casts spell 7063, which does not exist in the database.
- Epiphany is no longer an RR5 on live.

Reuse-fix rollback backup: `backups/modern-shared-ras-20261024-071953-229429`.


## Class RR5 pass, batch 2: current-live replacements, October 24 (Claude)

The owner chose current live. Nine RR5s that live added or swapped in after 1.108 are now built as modern ECS handlers (`realmabilities/handlers/ModernRr5Abilities.cs`). They are free at RR5 and bound to their live class. The Necromancer RR5 is deferred because it needs the 1.122b form rework.

Further research for this batch:
- 1.109 fetched from the official site: Fueled by Rage replaced Frenzied Assault (Savage), and Voice of Skadi replaced Epiphany (Skald).
- Found by search: 1.111 made Voice of Skadi 15 s with a 5-minute reuse; 1.113 made Mjollnir's Protection the Thane RR5 and moved Chain Lightning into Stormcalling.

| Class | RR5 | Built to | Sources |
|---|---|---|---|
| Mercenary | Dissolute Swings | 30 s: +25% damage dealt, +25% damage taken from all sources, clears stat debuffs and blocks new ones; 10-minute reuse | 1.121c, 1.124d, 1.126, 1.128 |
| Savage | Fueled by Rage | 30 s: 20% less damage taken, half of the prevented damage healed; 10-minute reuse | 1.109 |
| Enchanter | Frenzy of the Underhill | 30 s: pet melee and cast speed +100%; 5-minute reuse | 1.108 |
| Shaman | Restorative Mend | Group within 2000: 15% health, power and endurance every 2 s for 20 s; 10-minute reuse | 1.121, 1.120 |
| Scout | Far Sight | Clears nearsight, 60 s nearsight immunity; 30 s of +20% archery and spell range, and standard shots nearsight 50% for 20 s; removes stealth; 10-minute reuse | 1.124 |
| Hunter | Bestial Heart | 30 s Dire Wolf (model 649): +15% melee damage, +40% attack speed, +115% run speed, disease on melee hits, no bow; removes stealth; no pet needed; 10-minute reuse | 1.124, 1.124d, 1.125, 1.126 |
| Ranger | Nature's Madness | 30 s storm at the Ranger's feet, pulsing every 2 s in a 500 radius: enemies attack and cast 30% slower, and enemy pets inside flee; removes stealth; 10-minute reuse | 1.124, 1.127 |
| Skald | Voice of Skadi | 15 s crowd-control immunity, which also stops Static Tempest's stun (1.127); 5-minute reuse | 1.109, 1.111, 1.127 |
| Thane | Mjollnir's Protection | Group within 2000: 60 s, absorbs 50% of spell damage up to 1500 each; 10-minute reuse | 1.113, 1.114b |

Server hooks added, all through `ModernRr5`:
- Incoming damage adjustments at the start of `GameLiving.OnAttackedByEnemy`, before ablatives.
- Weapon base-damage factor.
- After a weapon hit: Far Sight's nearsight on standard shots, and Bestial Heart's disease.
- Cast time, for Frenzy of the Underhill and the Nature's Madness slow.
- Spell range, plus archery-range ability bonus support in the range calculator.
- Crowd-control, snare and Static Tempest immunity checks.
- Nearsight immunity.
- Stat-debuff immunity in `SingleStatDebuff`: strength, dexterity, constitution, quickness, acuity and the dual-stat debuffs.
- Bow block while in Dire Wolf form.

Database: eight new Ability rows (private internal IDs 3041–3048, using the icons of the RR5s they replaced), and the existing Restorative Mend row repointed at the new handler.

**Assumptions to check in game:**
- Mjollnir's Protection's reuse is not given in any note found, so it is assumed to be 10 minutes. It is built as a separate 1500-point pool per member; the note's "1500 total" could also mean one shared pool.
- Nature's Madness's pet "scare" makes enemy pets stop attacking and run away from the storm while they are inside it. There is no stock ECS fear.
- Bestial Heart's +115% speed is applied as a 2.15× run-speed multiplier for the duration.
- Dissolute Swings: the 1.128 rule that Dirty Tricks cannot be used during it is not implemented, and its damage bonus is not checked against Banespike.

Validation: 3,272 server tests passed, including 9 new tests: reuse timers; Dissolute Swings damage both ways; Fueled by Rage reduction and heal; Mjollnir pools per member, spell damage only, and ending when drained; the Restorative Mend tick; Voice of Skadi immunity; Bestial Heart bonuses applied, then removed, with the bow blocked; Far Sight range and immunity; Frenzy and Madness cast times. The 13 migration tests passed, including a new test for the RR5 rows. The installer verified 37 progress tables and all three DLL hashes. No client files were changed. In-game testing is pending.

RR5 status: 17 classes now have their RR5. Still to do:
- The NF-era RR5s with patch changes: Valhalla's Blessing (bound already), Vale Defense (broken spell reference), Fungal Union reuse, Allure of Death, Badge of Valor, Boiling Cauldron (1.128 and 1.129b rework), Calming Notes, Dreamweaver, Fanaticism, Fury of Nature, Gift of Perizor, Mark of Prey (1.128), Minion Rescue, Nature's Womb (Druid), Resolute Minion, Retribution of the Faithful, Selective Blindness, Selfless Devotion (1.122b), Sonic Barrier, Soul Quench, Spirit Martyr, Sputin's Legacy, Wall of Flame and Whirling Staff.
- The assassin RR5s: Overwhelm, Shadow Shroud and Blooddrinking.
- The Necromancer RR5.

RR5 batch 2 rollback backup: `backups/modern-shared-ras-20261024-072924-396604`.


## Class RR5 pass, batch 3, and Vanish correction, October 24 (Claude)

### Vanish correction (supersedes the stealth pass)

The 1.123 live notes for Infiltrator, Nightshade and Shadowblade say "Vanish has been removed from Stealth specialization. Vanish is once again a trainable Realm Ability." They also raise the disarm and silence from 15 to 30 seconds. The stealth pass had stopped at 1.122B.

- Vanish is now the trainable five-rank realm ability again: costs 5/5/5/7/8, 3/3/4/5/6 s of protection at normal speed and then speeds 1, 3, 4 and 5 (matching the current live table), a 900 s reuse and a 30 s lockout. The 1.121 poison cure when it ends is kept.
- It is bound to Infiltrator, Shadowblade and Nightshade, and the Stealth-spec grant is removed.
- Mastery of Stealth is unaffected.

### Batch 3

More research: 1.122b rewrote Selfless Devotion. 1.123 turned Gift of Perizor into a Mauler spec spell in the Mauler rework; no replacement Mauler RR5 was found.

**Legacy handlers kept, with live value fixes:**

| RR5 | Class | Fix |
|---|---|---|
| Fungal Union | Animist | Reuse 420 → 300 s (the 50% free-cast chance is already live) |
| Allure of Death | Bonedancer | Reuse 420 → 600 s (Nearsight resist already fixed to 75%) |
| Dreamweaver | Bard | Reuse 420 → 600 s |
| Selective Blindness | Mentalist | Reuse 600 s (1.128); already instant |
| Overwhelm | Infiltrator | Bypass 15% → 10% (1.108); new Ability row |
| Shadow Shroud | Nightshade | Reuse 300 → 600 s; 10% reduction and miss chance already live (1.114b); new Ability row |
| Blooddrinking | Shadowblade | 20% for 30 s → 45% for 15 s (1.121, 1.121b); new Ability row |
| Valhalla's Blessing | Valkyrie | Unchanged (75%, already bound) |

**Rebuilt as modern handlers** (`ModernRr5ClassicAbilities.cs`):

| RR5 | Class | Built to | Why rebuilt |
|---|---|---|---|
| Vale Defense | Valewalker | Group 1000-point 50% ablative for 10 minutes, the Valewalker's own holds 2000 (1.108, 1.125) | Cast spell 7063, which does not exist |
| Fanaticism | Heretic | Group within 2000: 25% magic absorption for 15 s (1.128) | Covered only hybrids and tanks |
| Selfless Devotion | Paladin | No stat penalty; every 3 s for 15 s: self 100, groupmates within 750 get 300 (groups of 2-5) or 500 (6+), boosted by healing bonuses; 10-minute reuse (1.122b, 1.129) | Still had the pre-1.122b stat penalty |
| Sputin's Legacy | Healer | 20 s: a killing blow leaves 1 health, heals 30-100%, then 5 s of damage and crowd-control immunity; the same immunity on expiry; 15-minute reuse | Legacy only topped up health |
| Spirit Martyr | Spiritmaster | 3200-point pool scaled by pet health, at most 600 per member (most injured first); the pet dies (1.127c) | Rewritten to the live rules |
| Fury of Nature | Warden | 15 s (1.121): style damage doubled; weapon damage spread-heals the group, excluding the Warden | Legacy used 30 s |
| Retribution of the Faithful | Cleric | 30 s: each melee attack on the Cleric has a 50% chance of a 3 s unresistable stun on the attacker | Rewritten on the incoming-attack hook |
| Mark of Prey | Vampiir | Group within 2000: 30 s stacking damage add whose damage returns to the Vampiir as power, plus +20% melee and spell crit (1.128) | Missing the 1.128 crit |
| Calming Notes | Minstrel | Mez of every enemy within 750 for 20 s (1.108) | Referenced spell 7045 and pets only |
| Sonic Barrier | Bainshee | Group including the Bainshee (1.128): armor absorption raised by the armor's own absorption (plate 34, chain or scale 24, studded or reinforced 19, leather 10) for 45 s | Referenced missing spells 36002-36005 |
| Soul Quench | Reaver | PBAE within 350: 200 damage (1.114b) scaled ×0.5 to ×1.5 by Soulrending/50; 75% returned as health | Rewritten on the damage pipeline |
| Wall of Flame | Wizard | Ward: 400 heat damage in a 150 radius every 3 s for 15 s; a 700-point 100% self ablative refreshed every 2.5 s; 10-minute reuse (1.125, 1.127, 1.129) | Legacy predates the ablative |
| Whirling Staff | Friar | 251 crush damage within 350 (the legacy value); targets cannot attack for 6 s | Rewritten on the damage pipeline |
| Nature's Womb | Druid | 5 s self silence (1.108, instead of a stun); all damage taken heals instead | Legacy stunned |
| Resolute Minion | Cabalist | Pet crowd-control immunity for 60 s; existing effects are not removed | Rewritten as an ECS effect |
| Badge of Valor | Champion | 20 s: target armor absorption increases melee damage, as (1+abs)/(1−abs) on the damage modifier; 10-minute reuse (1.121) | Legacy only worked inside a Battlemaster ability |

New hooks: an every-attack hook (Retribution), damage immunity and conversion and cheat death in the incoming-damage hook, a style-damage factor, an armor-absorption factor, Fury of Nature's spread heal on weapon hits, and pet and Sputin crowd-control immunity.

**Not bound, and why:**
- Necromancer: needs the 1.122b form system.
- Theurgist Minion Rescue: summons need their own pass.
- Warlock Boiling Cauldron: Warlock work is in progress elsewhere.
- Maulers: Gift of Perizor is a spec spell since 1.123, and no replacement RR5 was found.
- 40 classes now have their live RR5, including the Valkyrie's Valhalla's Blessing.

**Assumptions to check in game:**
- Sputin's heal is a random 30-100%, since live says only "at least 30%". The 5 s immunity blocks damage and crowd control, but not other harmful spells.
- Sonic Barrier's "multiple of existing ABS" is read as doubling the armor's absorption.
- Soul Quench's Soulrending scaling curve is not given on live.
- Whirling Staff keeps the legacy 251 damage, since live says "moderate".
- Mark of Prey keeps the legacy 5.1 damage-add value.

Validation: 3,279 server tests passed, including 8 new RR5 tests and the updated Vanish tests. The 13 migration tests passed, now covering every row and the Vanish binding with no spec grant. The installer verified 37 progress tables and all three DLL hashes. No client files were changed. In-game testing is pending.

RR5 batch 3 rollback backup: `backups/modern-shared-ras-20261024-073928-989305`.

