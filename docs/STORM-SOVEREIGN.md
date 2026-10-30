# Storm Sovereign — modern test class replacement

Storm Sovereign replaces Stormforged in the modern client test installation. Class ID 64,
Mauler Midgard client slot 61, StormforgedCareer and internal Stormforged.* keys are retained.
Existing characters retain level, inventory, realm rank, ML/CL and all saved progress.
The original Thane and the separate Classic/Stormforged installations are unchanged.

## Skills and growth

Sword, Hammer, Axe, Spear, Shields, Parry and Stealth track character level automatically.
Chain armor, large shields and weapon permissions are intrinsic. There are seven private
styles per weapon line: anytime, chain, parry/block reaction, positional, chained stun,
level-50 finisher and stealth opener. Styles unlock at 1/10/20/30/40/50, with the stealth
opener at 15. Stuns last 3 seconds (shield 4) and respect standard immunity.

Innate bonuses, outside item/buff caps, are floor(level * 2.3) to every stat and maximum
power and floor(level * 11.5) maximum HP. At 50: +115 all stats, +575 HP, +115 power, in
addition to normal Constitution/Piety contributions. No saved base-stat edits are made.

## Sustain

Every damaging hit returns part of the damage actually dealt: melee 30% as health and 10% each as
power and endurance; spells, procs, style effects and DoTs 50% as health and 20% each as power and
endurance. Storm Crown multiplies these by 1.5 (45%/15% melee, 75%/30% spells). Resists, misses,
absorbed hits and overkill return nothing; returns are limited by missing resources.

## Spells

Ranks replace older ranks automatically. Abilities unlock at their listed level.

| Ability | Unlock | Final behavior |
|---|---:|---|
| Lightning Spear | 1 | 250 energy, 1500 range, 2.5 s base cast |
| Winter's Grasp | 11 | 160 cold, 30% snare 8 s, 2 s base cast |
| Royal Thunder | 21 | Instant 180 energy; 15 s reuse |
| Chain of the Crown | 31 | Instant 200 energy PBAoE, 350 radius; 15 s reuse |
| Stormbreak | 41 | 250 energy PBAoE, 350 radius; 2.3 s base cast, no reuse |
| Eye of the Storm | 45 | Stationary storm at caster's feet, 350 radius, 100 energy / 3 s, 30 s lifetime/reuse |
| Royal Presence | 1 | Maintained comprehensive chant, reaches full strength at 40 |
| Decree: Advance | 15 | Party +15% movement multiplier for 10 s |
| Decree: Stand Fast | 20 | Party +10% absorption for 10 s |
| Decree: Strike True | 25 | Party +10 accuracy and +10% melee damage for 10 s |
| Sovereign's Renewal | 11 | Instant 25% self-heal; 30 s reuse |
| Rally to the Crown | 31 | Party 15% heal and 20% endurance; 90 s reuse |
| Will of the Sovereign | 45 | Break stun/mez/snare, 3 s protection; 180 s reuse, works while controlled |
| Armor of the Crown | 1 | Full base/spec buffs to all eight stats |
| Runic Ward | 25 | Up to +10% magic resistance in ability category |
| Runic Armament | 11 | Weapon-dependent procs, shield wards |
| Sovereign's Challenge | 10 | Taunt, 1500 range, 10 s reuse |
| Hunter's Mark | 25 | Mark from stealth: next melee hit against that target adds 30% damage |
| Runic Reversal | 35 | Parries return lightning for 8 s; 45 s reuse |
| Storm Wolf | 5 | One permanent owner-level wolf, 4x pet health, 2x damage (3x in Storm Crown), 30% life steal, shared stealth and normal pet commands |
| Storm Crown | 40 | 60 s transformation, 180 s reuse; +50% melee damage, 2x royal spell damage, royal casts at most 0.25 s, +20% absorption, +20% melee haste, 10% health/power/endurance every 4 s, 1.5x steal, lightning pulses |
| Sovereign's Hammerfall | 15 | Instant teleport/hammer impact, 2100 range, 350 primary energy and half splash, 15 s reuse; +10 primary crit chance from stealth |
| Veil of Winter | 30 | Maintained stealth benefit: +10% hidden movement and 25% shorter enemy-player detection radius, minimum 75 |

Decrees have independent 30-second reuse timers. Royal Presence supplies 50 health/power/
endurance every four seconds, 205% movement in combat/stealth, 80 AF, 24% magic resists,
17% melee haste and a 9-DPS damage add at level 40. It includes party members and their
controlled pets. Roots and other movement restrictions still apply.

The wolf has 4x pet health scaling and 2x melee damage (3x during Storm Crown); its hits heal it for
30% of the damage dealt. It uses stock Snow Wolf model 459, with White Wolf model 650 at increased size during
Storm Crown. It has frost and lightning attacks and normal attack/follow/stay/passive/defensive
commands. While owner-stealthed it does not acquire or attack targets. An explicit attack
command reveals both. Hidden wolves are removed from enemy clients that cannot detect their
owner. Hammerfall brings a following wolf; stay orders remain intact.

Hammerfall uses installed Command Mjollnir visual 3541. Target range, LOS and reachable-ground
checks remain. No model, effect or texture catalogs are modified. Storm Crown retains the
installed Frost Giant model 918; appearance and animations need in-game acceptance.

## Realm abilities and display corrections

Sovereign-only realm abilities cost 2, 4 and 6 realm skill points for their three ranks:
Royal Fortitude grants 3/6/9% maximum health, Storm Mastery grants 2/4/6% melee and spell
damage, and Crown's Resolve grants 2/4/6% secondary resistance to all nine damage types.
The inherited Thane selection also gains Mastery of Magery, Wild Power, Wild Minion and
Mastery of Stealth. Existing trained abilities are preserved.

Wrath of the Crown is automatically granted, free, at RR5 (R5L0). It empowers you and
your living Storm Wolf within 2000 units for 20 seconds: +20% melee/spell damage and
+10 percentage points of melee/spell critical chance, subject to normal crit caps.
Activation immediately strikes attackable enemies within 500 units for 300 base energy
damage. Reuse is five minutes. It breaks stealth and requires you to be alive, standing
and free of stun/mez. Normal resistance and damage rules apply.

The modern client's resist percentage now includes the secondary resistance layer, with
multiplicative stacking and the 70% hard cap. For example, 24% primary plus 10% secondary
shows 31% before racial resistance. Individual buff/item/secondary values stay separate.
A secondary ward alone previously colored the label green while leaving its primary-only
percentage at 0%. Winter's Grasp and the wolf's Frostbite use installed cold/snare effect
and icon 14321; the previous reference 3519 was absent from this client.

## Instant decrees

Decrees activate instantly from their original buttons, each on its own 30-second
reuse timer. The chamber experiment and preparation buttons have been removed.
Old preparation hotbar buttons can be discarded; original decree buttons still work.

## Install and recovery

Source tools: source/tools/sovereign/seed_sovereign.py, test_sovereign.py and install_sovereign.py.
The installer previews by default; --apply requires the selected game to be stopped, prepares
and checks a private database, verifies every saved-progress table, backs up all replaced files
and verifies installed hashes. It never starts or stops a server/client. --rollback <backup>
refuses to overwrite files changed since installation, including newer gameplay.

The modern client is generated from its verified pristine backup, with a private class name
and description, then its profile hash is updated. Other realms' classes are preserved.

After installing, remove old Stormforged hotbar spells/styles and drag the new entries from
the skill list. Old buttons contain obsolete spell-line/level or style addresses.

Automated checks do not replace gameplay checks. Verify creation/existing-character labels,
all weapon types and style chains, stun immunity, chant speed while hidden/in combat, wolf
concealment and controls, Hammerfall/terrain/visuals, transformation expiry and relog persistence.
