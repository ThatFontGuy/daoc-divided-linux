# Sovereign identity and style redesign proposal

Status: design proposal, October 25, 2026. Source and installed modern-test world inspected read-only. No gameplay or player data changed.

## Findings from the current implementation

The modern-test database has Storm Sovereign (64), Pendragon Sovereign (65), and Tuatha Sovereign (67). Storm has four weapon lines plus Shields (35 styles); the others have five plus Shields (42 each). Each line has the same seven-action structure at levels 1/10/20/30/40/50, plus a stealth opener at 15.

The actual sequence is anytime -> follow-up -> chained stun; a separate parry response (block on Shields); a rear positional; an unrestricted level-50 attack; and the stealth opener. The level-50 attack is not a chain finisher. There are no separate block AND parry chains on the weapon lines, no side branch, and no defensive follow-ups. All rear positionals use the same opening.

Pendragon and Tuatha seed from Midgard's spell table. Their styles dispatch through the shared StormSovereignAbilities.Style handler, including a repeated first-weapon profile for their extra heavy line. Names, damage types, gear and appearances differ, but combat decisions are largely identical. There are some real weapon effects already: sword healing, axe DoTs, hammer/spear splash and shield wards. These are a useful starting point, not enough to make three distinct classes.

Evidence:
- source/tools/sovereign/seed_sovereign.py: SPELLS, STYLE_NAMES and style seeding.
- source/tools/sovereign/seed_pendragon.py and seed_tuatha.py: cloning and weapon mapping.
- source/server/GameServer/spells/Stormforged/StormSovereignAbilities.cs: Style handler.
- source/server/GameServer/ECS-Effects/StormSovereignEffect.cs: armament and parry retaliation.
- source/server/GameServer/styles/StyleProcessor.cs: actual opening and chain checks.
- artifacts/modern-client-test/runtime/data/opendaoc.sqlite3.db: installed style rows, read-only.

## Shared power floor to preserve

Keep automatic training, the comprehensive maintained chant, full self buffs, resistance ward, stealth access, a strong companion, emergency healing and control break. Keep the existing innate stats and basic damage-to-resource sustain as the starting baseline. The owner wants substantially overpowered classes, so normal-class parity is not the target.

Keep the existing regeneration, travel speed, AF, resists, haste and damage-add chant benefits. Add realm identity through active interactions and a modest themed rider, rather than forcing the player to choose between necessary buffs. Do not require repetitive buff upkeep.

Differentiate where each class exceeds the others: Pendragon survival and retaliation; Storm immediate burst and packs; Tuatha sustained pressure, marks and magical sustain. Every class remains capable solo, with each offering a different strongest play pattern. Numerical suggestions below are initial design values, not measured balance results.

## Recommended weapon reduction

| Class | Retain | Retire from new training |
|---|---|---|
| Pendragon | Slash, Crush, Polearm, Shields | Thrust, Two Handed |
| Storm | Sword, Hammer, Axe, Shields | Spear |
| Tuatha | Blades, Piercing, Celtic Spear, Shields | Blunt, Large Weapons |

This leaves a sustain line, pressure/burst alternatives and a dedicated shield kit for each realm. Heavy-weapon identities remain with Albion's Polearm and Hibernia's Celtic Spear. Storm's supported weapons can still use permitted two-handed variants; verify existing weapon permissions before implementation.

Fewer lines are a design recommendation, not a technical requirement. Three deep lines are preferable to retaining five shallow copies.

## Pendragon: the unbreakable royal champion

Core mechanic: Royal Authority, up to three charges from successful blocks/parries or completed chains. Charges last long enough to move between nearby fights. Finishers spend charges for stronger effects; ordinary styles remain strong without them. Put a short shared charge-generation limit on defensive events so a crowd cannot generate unlimited retaliation.

- Slash: duelist sustain. Accurate cuts, small direct heals, radiant wounds, parry counters and a single-target execution.
- Crush: judgement and guard breaking. Armor weakening, attack-speed suppression, powerful block counters and a crushing burst finisher.
- Polearm: commanding reach. Broad sweeps, frontal pressure and a high-damage parry chain; spends Authority on cleave rather than duplicating Crush.
- Shields: protection and retaliation. Strong block chain, temporary ablatives, group shielding and a proper shield finisher.

Example Slash anytime chain: Crowned Slash -> Oathcut -> King's Sentence. The first applies a radiant wound, the second heals, and the third delivers heavy damage plus an Authority bonus. Block branch: Royal Rebuke -> Crownfire Reprisal, granting an ablative then retaliating. Parry branch: Royal Riposte -> Duelist's Decree, granting accuracy then a strong self-healing strike.

Chant rider: finishing a defensive chain grants a small temporary group ward with a refresh limit. Lion identity: intercept/protect and a targeted pounce, rather than the same elemental caster pet. Transformation identity: a moving royal fortress, emphasizing retaliation, protection and decisive melee finishers. Retain a strong damage bonus so it still feels like an offensive power mode. Convert the stationary damage field into a consecrated protection-and-retaliation zone. Differentiate decrees into rally, protection and execution orders.

## Storm: the destructive storm king

Core mechanic: Tempest, up to three charges built through landed weapon chains and selected lightning spells. Spend charges on storm finishers. Do not let splash hits or procs recursively generate charges.

- Sword: storm duelist. Fast reliable single-target pressure, healing cuts and parry-triggered spell empowerment.
- Hammer: thunder detonations. Main pack-clearing line, explosive chain finishers, block-triggered thunder retaliation and armor breaking.
- Axe: winter executioner. Bleeds, frost pressure, strong parry counters and finishers that exploit its own wounds.
- Shields: stormguard. Blocks bank a controlled lightning retaliation and grant a short protective ward.

Example Hammer anytime chain: Thunderstroke -> Shatterguard -> Thor's Judgement. Builds charge, cracks armor, then detonates a capped lightning arc. Block branch: Thunder Aegis -> Hammer of Reprisal, ward then explosive counter. Parry branch: Storm Counter -> Skybreaker, charges Tempest then delivers concentrated lightning. Axe must exploit its own frost wound, rather than any unrelated DoT on the victim.

Chant rider: completed chains empower the next royal lightning cast. Wolf identity: aggressive pursuit, frostbite setup and coordinated lightning strikes. Transformation identity: fastest and most explosive of the three; lightning chains and empowered hammer impacts. Preserve the existing storm field as this class's signature area spell. Decrees become movement, stormguard and overload bursts.

## Tuatha: the otherworld sovereign

Core mechanic: Otherworld Marks, up to three per target from specific weapon actions and spells. Finishers consume the owner's marks for spirit damage, healing or a limited echo. Marks are personal, expire, and cannot be recursively created by echoes.

- Blades: thorn duelist. Bleeds, parry counters and restorative finishers; sustained melee pressure.
- Piercing: glamour hunter. Precision, rear/side attacks, magical defense weakening and concentrated mark detonations.
- Celtic Spear: spirit reaper. Sweeps, spirit wounds, snares and mark-powered drain bursts.
- Shields: thornward. Protective glamour, reactive thorns and shield counters that build marks.

Example Piercing anytime chain: Veilneedle -> Oathpiercer -> Sidhe's Claim. Marks, weakens spirit resistance briefly, then detonates marks. Block branch: Mirror Guard -> Shattered Reflection, protective glamour then spirit counter. Parry branch: Sidestep of the Sidhe -> Stolen Breath, marks then restores health/power. Distinguish this healing from Pendragon by requiring offensive mark consumption.

Chant rider: a completed mark detonation shares a limited recovery pulse. Drake identity: applies a companion-specific setup effect and supports spirit detonations, with no self-sustaining mark/proc loop. Transformation identity: marks accelerate, selected finishers echo once, and drains strengthen. Replace the copied stationary storm with a faerie ring that supports marks and positional pressure. Decrees become glamour movement, thorn protection and an echo window. Keep Step Between Worlds but tie its impact to a mark or positional setup.

## Style progression: a new unlock every two or three levels

Target 20 styles per retained line, including Shields: 80 styles per class. Shared unlock spacing is useful for learning; effects, tactical roles and finishers must differ by weapon and realm.

| Level | Unlock role |
|---:|---|
| 1 | Strong anytime opener |
| 3 | Anytime follow-up |
| 5 | Parry response |
| 8 | Block response |
| 10 | Third attack in anytime chain |
| 13 | Parry follow-up |
| 15 | Stealth opener |
| 18 | Side opener |
| 20 | Rear opener |
| 23 | Side follow-up |
| 25 | Rear follow-up |
| 28 | Block follow-up |
| 30 | Stealth follow-up |
| 33 | Alternate anytime branch: sustain or setup |
| 35 | Finisher for alternate branch |
| 38 | Third attack in parry chain |
| 40 | Third attack in block chain |
| 43 | Positional capstone following the line's preferred positional branch |
| 45 | Realm-mechanic setup style |
| 48 | Signature finisher following that setup |

The stealth opener remains at level 15 to preserve existing early stealth play.

One-handed lines get separate block and parry responses. Polearm/Celtic Spear block branches require a meaningful equipment-switch design: the current engine checks the target's previous attack, so a shield block followed by a heavy-weapon switch may be viable, but needs verification. If switching cannot preserve a usable response window, use a shared class-level block-earned token with a brief duration and consume it on the heavy counter. Do not add fake blocks while no shield is equipped. Shields' parry branch likewise needs verification with actual shield-style weapon selection.

Avoid filler ranks of identical styles. Each unlock adds a real choice, follow-up or payoff. Keep earlier openers useful at 50 by scaling proc effects with level. Give shield chains their own protection/retaliation identity; do not simply attach shield names to the normal weapon template.

## Initial power and usability targets

- Keep existing general sustain and power baseline; add identity through earned burst, defense or mark payoffs.
- Suggested starting growth ranges: anytime 0.75-0.9, second steps 1.0-1.15, earned finishers 1.25-1.5. Verify the server's growth formula and actual damage before treating these as final numbers.
- A harder positional or defensive condition should earn a visibly stronger payoff than spamming the anytime opener.
- Keep stuns short and subject to standard immunity. Every line does not need the same stun in the same chain slot. Give alternative finishers damage, drains, armor breaking, ablatives or cleave.
- Strong AoE remains, but secondary targets and echo counts need explicit caps. Extra targets already multiply the powerful spell sustain.
- Do not stack a new universal damage multiplier on top of transformation, RR5, style procs and lifesteal without measuring combined results.
- Retain simple playable defaults: chant, buffs, companion, anytime chain. Extra branches reward attention without making basic survival dependent on a long rotation.

## Implementation and existing-character handling

1. Separate realm-and-weapon behavior from the current index/7 handler. Define each style's identity, prerequisites and effects explicitly. Share low-level helpers rather than sharing the entire combat kit.
2. Preserve class IDs, career keys, spell identities for retained abilities and trained RA identities. Preserve retained style IDs where practical so old hotbars remain useful. Check private ID ranges and signed tooltip limits before assigning new content.
3. Keep seeders idempotent and migrate each class independently. Reseeding Albion/Hibernia from Midgard must not restore the old mirrored kits.
4. Before retiring permissions, inspect equipped, inventory and stored weapons. Keep legacy equipment usable during transition; offer replacement choices through the trainer without silently deleting or replacing player items. New characters receive a retained-line starter weapon. Document obsolete hotbar buttons.
5. Update bot style selection, weapon choices and class-kit policies so companion and autonomous bots can use the redesign. Player, companion and autonomous behavior need separate checks.
6. Validate every prerequisite, level unlock, block/parry branch, weapon restriction, target/owner effect, immunity and resource return. Test rank replacement and ensure repeated procs cannot recurse. Compare all three with the same gear and targets: single enemy, pack, elite, long fight and transformation burst.
7. Prepare a preview migration on a private copy and verify all saved-progress tables. Deploy tested output with backups only when installation is authorized and stopped. No server was started for this audit.

Recommended direction: keep the shared overpowered foundations, reduce to three meaningful weapons plus Shields, replace mirrored active kits with Authority / Tempest / Otherworld Marks, and make each line's frequent style unlocks build toward distinct offensive and defensive chains.

