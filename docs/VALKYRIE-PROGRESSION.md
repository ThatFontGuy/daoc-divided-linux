# Valkyrie research implementation — first progression pass

October 21, 2026. Modern test world only. User reports successful level-one Valkyrie play from the starter slice. This pass extends that slice; it is not a complete class release.

## Implemented

Nine instant Spirit-damage ranks now belong to the actual **Odin's Will specialization**, with unlocks 1/4/7/9/13/19/25/35/45. Each uses 1500 range and a shared 20-second reuse. The previous level-one spell ID is preserved; eight new owned IDs are collision-checked. Values follow the [official class reference](https://www.darkageofcamelot.com/class-library-valkyrie/) (undated historical table, not guaranteed current retail). This is a documented reference baseline with selected modernization still pending.

The temporary test career/links are removed. Existing Mending baseline healing remains unchanged, and no saved character/spec/inventory rows are edited. Higher damage ranks require Odin's Will training rather than automatically advancing from the prototype baseline. Local SpellGroup and SharedTimerGroup 64990 intentionally keep ranks in one display/reuse family; these IDs are implementation choices. Borrowed icons/effects remain placeholders.

A Valkyrie trainer is added in **Mularn beside Saeunn, the existing Viking trainer**. It uses the existing ValkyrieTrainer script at the same known world coordinates. The two NPCs may overlap visually; target the Valkyrie Trainer by name. Its appearance is copied from that existing NPC. Normal progression/spec-point rules remain in force; the test does not award free levels or points.

## Test now

Restart the test server with the normal modern launcher. Existing Valkyries should retain their characters and see the attack under Odin's Will instead of Valkyrie Test Spells. Minor Mending remains in Mending. Visit the Valkyrie trainer in Mularn; as you level, train Odin's Will and verify the next rank at 4, 7 and later breakpoints. Test rank upgrades, shared cooldown, healing, combat and relog. Old quickbar entries may need dragging from the refreshed spell list if they referenced the removed test line.

## Remaining implementation checklist

| Area | Current state / next work |
|---|---|
| Creation/start | User-tested level-one class; explicit races, female restriction; chain starter armor since pass 4 |
| Single-target instant damage | Nine reference ranks implemented; gameplay progression needs user verification |
| Baseline Mending | Done in pass 2 (below): Valkyrie-only baseline line with Class Library values |
| Mending specialization | Done in pass 2 (below): all 32 Class Library spells |
| Sword/Spear/Shields | Completed in pass 5: 19 sword, 18 spear and 14 shield styles with class-specific chains and effects |
| Equipment progression | Chain from level 1; small shield at 1, medium at 5, large at 10 |
| Cone damage, pulsing cone, snares | Pass 3 (below) |
| Weapon procs and power rend | Odin's Aura plus 42 style effects, including 3%/6% area power rend |
| Ablatives, shears, resurrection | Odin's Will parts, repaired magic absorption, and Brace's 300-point physical buffer |
| RAs/RR5 | 31 compatible Atlas abilities, Valkyrie Charge, and automatic Valhalla's Blessing at RR5 |
| Bots, ML, CL | Player ML/CL already use shared level-50 progression; bot class selection/AI remains a separate feature. RR5 includes living group members, including bots |

The table prevents research leads from becoming silent defaults. Later retail deltas such as Ragnarok/Raze/Odin's Bite, Shieldmaiden heals and Charge require complete underlying definitions first. Do not copy shared Warrior/Hunter styles wholesale and call them Valkyrie styles.

## Verification and preservation

`source/tools/valkyrie_progression.py` backs up the private test DB, refuses a listening test server, and applies one transaction. Four definition-only integration tests cover idempotency, rank/spec/shared-timer wiring, preservation of the shared heal and rollback on ID collision. Fixtures copy definition tables only, not account/character data. No source server rebuild is needed for these data changes. No original install or player record was changed; no server was started during preparation.

Prototype seed refuses to reapply over progression revision 2. Private report: artifacts/modern-client-test/valkyrie-progression-report.json. Whole-DB backups include local test progress and must remain private; restoring them after more play can discard newer saves.

## Pass 2: Mending baseline and specialization (October 23, 2026)

Applied to the modern test world by `source/tools/valkyrie_mending.py` (data revision 3; backup and report in `artifacts/modern-client-test/`). Values are parsed from the raw HTML tables of the [official class reference](https://www.darkageofcamelot.com/class-library-valkyrie/).

**Baseline.** A new line `Valkyrie Mending` (baseline, class hint 34) replaces the shared `Mending` baseline for the Valkyrie only, because `Specialization.GetSpellLinesForLiving` prefers a class-hinted baseline. Healer, Shaman and Seer keep the shared line unchanged. It holds 24 Valkyrie-owned heal copies (minor heal, heal, group heal) with the reference costs and cast times, which are lower than the shared Classic rows (Emendation costs 29 here and 42 in the shared line; group heals cast in 2.6–2.0 s instead of 3.0 s). Three shared rows that already match exactly are linked without changes: Cure Poison 1371, Cure Disease 1372, Arrival from Valhalla 3031. The shared line's Minor Refinement (level 3) is not in the Valkyrie table and is left out.

**Specialization.** The existing empty `Valkyrie Mending Spec` line now holds 32 spells: 8 major heals, Redeem from Valhalla (instant, 300 s reuse, 25%/25%), 4 single-target health-regeneration buffs and 4 group ones (`HealthRegenBuff`, value added per regeneration tick), 4 single-target heals over time and 4 group ones (`HealOverTime`), and 7 instant area heals centered on the caster (radius 350, 15 s reuse).

Choices where the reference is silent, and differences from it:
- The HoTs pulse every 2 s, following OpenDAoC's own orphaned Valkyrie row 121009. The page gives "health/pulse" but no pulse rate.
- The area heal heals every target in radius the same amount. The reference says closer targets get more, but `HealSpellHandler` has no distance falloff and changing it would affect other classes' heals.
- One caster's HoTs (single and group) overwrite each other, and so do one caster's regeneration buffs, because the server stacks by effect type. HoTs from different casters coexist.
- "Variable" rez cost uses the same −25 setting as the existing Midgard rezzes.
- Icons and effects are borrowed from the Healer/Shaman/OpenDAoC rows they were copied from. Pass 4 replaced this pass's `TooltipId` 0 with each spell's own tooltip ID.

Seven definition-only tests (`source/tools/tests/test_valkyrie_mending.py`) cover values, reapplying, rollback on ID collision, the revision check, tooltip safety and the shared lines staying unchanged. The four earlier progression tests still pass. Not yet checked in game.

**Test now:** restart the test server. Old quickbar heals point at shared Mending rows and need to be dragged again from the refreshed spell list. Check heals and costs at your level, then train Mending and check Major Reconstitution and Odin's Antidote (5), Shieldmaiden's Aid (7) and Odin's Amelioration (9).

## Pass 3: rest of Odin's Will (October 23, 2026)

Data: `source/tools/valkyrie_odins_will.py` (revision 4). Server code: new spell types `ValkyrieDexQuiShearCone` and `ValkyrieAcuityShearCone` (`spells/Valkyrie/ValkyrieConeShear.cs`), and percentage pulse upkeep (negative `PulsePower`, `BotSpellPower.PulseCost` and `EffectService`). **The data needs that server build;** applying it to a server without the new spell types would break spell loading.

31 spells are added to Odin's Will next to the nine damage ranks, plus 5 unlinked proc spells:

| Table | Implementation |
|---|---|
| Call from Valhalla (43) | Resurrect, 4.0 s, 65% health / 35% power |
| Valhalla's Scorn–Rage (8–48) | `DirectDamage`, Target `Cone` (700 length, 90° arc), Spirit, 30 s reuse |
| Odin's Retribution chant (5–42) | Existing `FrontalPulseConeDD`, same cone, pulse every 5 s, 10% power to start and 9% per pulse, 8 s reuse |
| Odin's Faith/Virtue/Temperance (30/40/50) | `MagicAblativeArmor` group chant: pulse every 6 s, absorbs 30% of each magic hit up to 60/90/120, no power cost, 8 s reuse |
| Odin's Aura (8–44) | `OffensiveProc`, group, 10 minutes, 10% chance; each rank fires its own Spirit damage spell |
| Vindictive (17–47), Valkyrie's Authority–Dominance (19–49) | New cone shear types: Spirit damage to enemy players, bots and controlled pets only, then remove that target's strongest concentration Dex/Qui (or Acuity) buff, up to 75 for the first two ranks of each |
| Odin's Restraint–Lock (12–46) | `SpeedDecrease` cone, 50–80% for 10–40 s, 30 s reuse |

Choices and known differences:
- **One chant at a time.** The server keeps the 1.65 rule that a new pulse spell ends the caster's other pulse spells, so Odin's Faith and Odin's Retribution replace each other.
- **Shear reuse groups.** The page alternates 300 s and 60 s reuse within each shear table, so each table is split into two spell groups by reuse. That keeps both versions on the spell list (Graze/Nip and Laceration/Bite; Authority/Command and Supremecy/Dominance). Costs are as printed, even where they look odd (Nip 16 after Graze 16).
- **Why a new shear handler.** The stock `*Shear` handlers search the legacy effect list, which this server's ECS buffs never enter, so they can never remove anything. No existing spell uses them, and they are left unchanged.
- **Cone damage falloff.** Cone damage and snares use the server's standard cone distance falloff. The page doesn't mention falloff.
- **Proc range.** The proc spells use a 300 range, copied from the existing Blightstrike proc template.

Tests: 8 definition tests (`source/tools/tests/test_valkyrie_odins_will.py`) and 6 unit tests (`Tests/UnitTests/UT_ValkyrieOdinsWill.cs`) for percentage pulse cost and the shear rules. Full server suite: 3,137 passed. Not yet checked in game.

Deployed October 23, 2026: the new `GameServer.dll`/`.pdb` went to all three modern test server folders (previous copies in `artifacts/modern-client-test/backups/gameserver-pre-odins-will-20261023-164731/`), then the data was applied (database backup `pre-valkyrie-odins-will-*`). That build also includes an unrelated `StormforgedEffects.cs` edit from earlier the same day, with the owner's approval.

**Test now:** restart the test server. By level: Odin's Minor Retribution (5), Valhalla's Scorn and Odin's Minor Aura (8), Odin's Restraint (12), Vindictive Graze (17) and Valkyrie's Authority (19) on a buffed enemy player or pet, Odin's Faith (30). Check the chant's power drain, that Faith and Retribution replace each other, and that the shear removes a buff.

## Pass 4: own tooltips and chain armor (October 23, 2026)

**Tooltips.** The owner reported that the new spells showed the wrong tooltip. The client looks a spell's description up by its tooltip ID (`TooltipId`, sent as the spell's internal ID), and the copied spells had 0. Every Valkyrie spell now has its own ID, `27000 + SpellID − 64990` (block 27000–27160, which nothing else uses: Sluaghbinder is 29000, Pendragon 26000, Stormforged 20600). The three spell scripts write it, and each checks that no other spell uses its IDs. `PacketLib1110.UsesOwnTooltipIdentity` now includes 64990–65150, so buff icons use the spell's own tooltip as well. The range stops at 65150 because 65151 and 65152 are stock spells, and a unit test pins that boundary. The linked shared rows (Cure Poison, Cure Disease, Arrival from Valhalla) keep their stock tooltips. Reapplying an earlier script no longer rolls the data revision back.

**Chain armor (owner decision).** `source/tools/valkyrie_chain_armor.py` (revision 5) raises the Valkyrie's level-1 `MidArmor` grant from 3 (studded) to 4 (chain), which other classes reach at 10–12. New Valkyries start in the level-2 bronze pansarkedja chain set (helm, gloves, boots, sleeves, leggings, hauberk) instead of the bronze stelskodd studded set. The training sword and small shield are unchanged, and other Viking classes keep their studded starter rows. Existing characters can wear chain right away, but their inventories are not changed, so they keep their studded starter pieces.

Deployed with backups (`backups/gameserver-pre-valk-tooltips-20261023-165523/`, plus a database backup for each script). Tests: 24 data tests and 13 Valkyrie unit tests; full server suite 3,137 passed. Not yet checked in game.

## Pass 5: player-class completion (revision 6)

The migration `source/tools/valkyrie_completion.py` adds the missing player-class definitions without changing other classes or saved characters. It retains Whirling Blade's original style ID so existing quickbars stay valid; new styles have class-34 IDs 2001–2050 and effects in 65200–65250 with tooltip identities 27210–27260. All new effects use existing client assets. No client binary or catalog patch is required.

- **51 styles:** 19 Sword, 18 Spear, 14 Shields. Prerequisites are rebuilt explicitly for Valkyrie: block/parry, front/side/back and actual preceding styles. The common native style rows supply melee growth rates, endurance, icons and animations; newly missing variants use comparable melee values. These are functional local balance choices, not a claim of exact modern-retail growth rates.
- **42 private style effects:** bleeding, taunt/detaunt, attack-speed debuffs, snares, reference-duration stuns, Spirit damage, Aurora/Odin's Bite area power rend, Roundhouse's Crush PBAE, Gungnir's Fury's Spirit PBAE, and Brace's 300-point 50% physical ablative. Slam is the Valkyrie reference's five seconds. No shared Warrior/Hunter style/proc definition is edited.
- **Career:** medium shields at 5, large at 10, Protect I/II at 10/20 and Intercept at 15, using this server's hybrid career conventions. Chain-from-level-one remains. Existing characters retain levels, training, inventories and progress; career abilities refresh on relog.
- **RAs:** 31 installed Atlas passives/actives plus a Valkyrie-specific Charge binding and the existing Valhalla's Blessing RR5. Charge is target-free, so it can be used in PvE; it lasts 15 seconds and follows the server's selected three/five-rank active-RA scaling. It does not remove existing roots/snares. RR5 lasts 30 seconds, reuses in ten minutes, and uses the existing 75% free power/style endurance implementation. Its group targeting now includes living companion bots. The style affordability check no longer rolls the free-endurance proc; only actual use does.
- **Magic absorption repaired:** all three ablative types register with ECS and filter incoming physical/magical damage correctly. Spell and damage-over-time hits reach absorption. Critical damage cannot make base damage negative; exhausted buffers stop absorbing immediately. Physical and magic buffers coexist, and weaker same-family buffers cannot replace stronger ones.
- **PBAE heals:** the seven Valkyrie instant area heals now heal more near the caster. The local curve is linear to a 25% minimum at the outer edge; the reference specifies falloff but does not publish its curve. Other classes' heals keep their existing behavior.
- **Multiple chants:** concurrency follows the server's `ALLOW_MULTIPLE_CHANTS` rule being implemented separately by Claude. This pass does not impose a one-chant restriction or change that setting.

`source/tools/install_valkyrie_completion.py` previews by default, backs up the database and all three server DLL/PDB copies before `--apply`, checks that the installation is stopped, verifies all 37 saved-progress tables, and supports hash-guarded `--rollback <backup-folder>`. Rollback refuses after later gameplay/file changes to avoid losing newer progress. The installer can use `--build-dir` to deploy the exact DLL tested in a separate output folder.

Validation includes definition-only migration/idempotency/collision tests, stock-class preservation, client asset references, a saved-progress/rollback fixture, and real ECS combat-path tests for magic/physical buffers and depletion. Gameplay acceptance remains: relog, train Sword/Spear/Shields, check chains and procs on enemies, test Odin's Faith against spell damage, spend RAs at the trainer, and check the free RR5 at rank five. No game server was started for this work.

Installed revision 6 in the selected modern test installation on October 23, 2026. Validation: 3,168 server tests passed (including 19 new completion cases), plus 32 Valkyrie data/installer tests. All 37 saved-progress table hashes matched before and after migration. The installed three server DLLs match the exact isolated tested build; database quick_check is ok. Installation report and backup manifest are private under artifacts/sovereign-validation/valkyrie-completion-install-result.json and the selected installation's backups/valkyrie-completion-* folder. Claude's multiple-chant implementation was preserved; only a required namespace qualification in its BotBrain reference was corrected during compilation. In-game behavior has not been exercised by this automated run.

## Trainer replacement

The owner requested Eve of Darkness's actual expansion trainers. The temporary Mularn trainer is replaced by 13 imported Valkyrie trainers, including Brienda and Sunhilda in Jordheim. The old progression seed will not recreate the temporary NPC. See [Expansion Trainers](EXPANSION-TRAINERS.md) for the names, coordinates and guarded import.

## Spell icons and effects (October 23, 2026)

The owner reported that the spell icons didn't match live. Every Valkyrie spell had been using the icon and visual effect of the spell it was copied from. `source/tools/valkyrie_icons.py` (preview by default, `--apply` to write) now sets `Icon` and `ClientEffect` for all 96 owned Valkyrie spells and the 5 Odin's Aura proc spells, from `source/tools/valkyrie-icons-eod.json` (hash-checked):

- **Source:** Eve of Darkness [db-public e0e6ed28](https://github.com/Eve-of-Darkness/db-public/tree/e0e6ed280f6239d2c40d4d0a57b244dafdc2056e). Each spell takes the values of the same spell in that database's Odin's Will, Valkyrie Mending Spec or Mending line, matched by name within the line.
- **Client check:** every ID exists in the bundled 1.130 client's `spells.csv`. The client has its own Valkyrie block: 12501–12554 for Odin's Will and the aura procs, and 14810–14812 for Odin's Faith, Virtue and Temperance. Eve of Darkness matches that block except for the Faith family, where it borrows the Skald's Barrier of Sound; those three use the client's dedicated rows instead.
- **Baseline heals:** each rank now has its own stock icon (Minor Improvement 3003, and so on) instead of one icon for the whole family.
- **Mending spec heals over time, regen buffs and area heal:** the client has no Valkyrie-specific rows for these, so they use Eve of Darkness's choices (the Hibernian Trance and Albion Angelic and Redemption visuals). That part is a reference choice, not confirmed live art.
- **Unchanged:** the shared stock Cure Poison, Cure Disease and Arrival from Valhalla keep their own art. Tooltips, mechanics and saves are not touched, and nothing touches Codex's weapon-style effect spells.

95 spells changed (6 already matched). The database is backed up as `pre-valkyrie-icons-*`.

**Visual audit (same day).** All 143 owned Valkyrie spell rows were checked against the client's `spells.csv`:
- **Valkyrie spells and aura procs:** all 101 point at existing rows that carry real effect data (cast animation, hand and target effects), and each is the matching Valkyrie row in the client.
- **Spirit and Crush weapon-style procs:** Codex's 8 used the client's *cold* snare visual (14321). They now use the client's generic proc visual for their damage type and shape: Raze and Polar Rift take spirit dd1 (14325); Odin's Deathblow and Ragnarok take spirit dd 2 (14326); Gungnir's Fury, Odin's Bite and Aurora take spirit PBAE (14329); Roundhouse takes 14323, as Eve of Darkness's "Force of the Roundhouse" (the same Crush proc). Neither the client nor Eve of Darkness has Valkyrie-named rows for these, so this is the best available match, not confirmed live art. These visuals are listed in `STYLE_PROC_VISUALS` in `valkyrie_icons.py`, so rerun it after `valkyrie_completion.py`.
- **Other style procs:** bleed, stun and snare procs use the same stock visuals as other classes' styles. The attack-speed slows have no visual, the same as stock. The taunt and detaunt procs have no effect row; stock styles point at 7353/7354, which don't exist in the 1.130 client either. Tests: `source/tools/tests/test_valkyrie_icons.py` (4). Rerun this tool after rerunning the progression, Mending or Odin's Will scripts, because they copy their template's icon. Restart the test server to see it. Not yet checked in game.
