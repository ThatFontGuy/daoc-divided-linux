# Pendragon Sovereign

Albion's royal solo/co-op class uses Storm Sovereign's current combat balance table.
It is class 65 on the server and occupies Albion's Mauler selection slot (60) in the
modern test client. Storm Sovereign remains class 64 in Midgard's slot 61.

All seven Albion races are eligible. No specialization spending is required: Slash,
Crush, Thrust, Two Handed, Polearm, Shields, Parry and Stealth train with character level.
Each weapon line has seven private styles (42 total), including chains, defensive
reactions, positional attacks and a stealth opener. Chain finishers provide three-second
stuns, four seconds for Shields, with normal immunity rules. Plate armor and large
shields are available from creation. Starter equipment and a trainer are supplied.
Crownwarden stands beside Lord Prydwen in Camelot.

## Shared power baseline

| Feature | Both Sovereigns |
|---|---|
| Base HP / weapon skill curves | 720 / 360 |
| Innate bonuses at 50 | +115 all eight stats, +575 flat HP, +115 flat power |
| Melee sustain | 30% damage returned as health, 10% each as power/endurance |
| Spell sustain | 50% damage returned as health, 20% each as power/endurance |
| Royal companion | Owner level, 4x normal pet health, 2x damage, 30% damage-to-health return |
| Transformation | 60 seconds, 180-second reuse |
| Transformation bonuses | +50% melee damage, 2x royal spell damage, at most 0.25-second royal casts, +20% absorption/haste |
| Transformation recovery | 10% maximum health/power/endurance every four seconds; 1.5x hit sustain |
| Transformed companion | 3x normal pet damage |
| Support chant at 40 | 50 health/power/endurance per four seconds, combat/stealth speed, 80 AF, 24% magic resist, 17% haste, 9-DPS damage add |
| Extra resistance ward | Up to 10% secondary magic resistance |

Sustain uses damage that landed, bounded by the target's pre-hit health. Resisted hits
do not restore resources. Restoration is capped by the caster's resource pools.
Albion's plate armor and six weapon choices are realm-specific advantages; these
are comparable powerful classes, not a claim of measured PvP balance. Damage types
differ: Pendragon uses holy fire/heat instead of Midgard's energy/cold/body procs.

## Royal abilities

The installer copies the installed Midgard abilities' damage, power costs, acquisition
levels, cast times, ranges, radii, durations and timers into separate Albion content.
It never reseeds the Midgard class. Future intentional power changes can be shared
through the common combat table; content changes can be mirrored by rerunning the
Albion migration against the updated Midgard content.

| Ability | Level | Behavior at final rank |
|---|---:|---|
| Crownfire Lance | 1 | 250 base heat damage, 1500 range, 2.5-second cast |
| Binding Radiance | 11 | 160 heat damage, eight-second 30% snare, two-second cast |
| Royal Smite | 21 | Instant 180 heat damage, 15-second reuse |
| Chains of the Crown | 31 | Instant 200 heat PBAoE, 350 radius, 15-second reuse |
| Crownfire Burst | 41 | 250 heat PBAoE, 350 radius, 2.3-second cast, no reuse timer |
| Field of Judgement | 45 | Stationary field at caster's feet; 100 heat damage per three seconds, lasts/reuses in 30 seconds |
| Royal Procession | 1 | Maintained support chant, final strength at level 40 |
| Decree: Advance | 15 | Party movement burst, independent 30-second reuse |
| Decree: Stand Fast | 20 | Party absorption burst, independent 30-second reuse |
| Decree: Strike True | 25 | Party accuracy/melee burst, independent 30-second reuse |
| Sovereign's Renewal | 11 | Instant 25% self-heal, 30-second reuse |
| Rally to the Crown | 31 | Party 15% health/20% endurance recovery, 90-second reuse |
| Will of the Pendragon | 45 | Control break and three-second protection, 180-second reuse |
| Armor of the Crown | 1 | Full base/specification buffs to all eight stats |
| Sacred Ward | 25 | Maintained secondary magic resistance |
| Consecrated Armament | 11 | Weapon procs and shield protection |
| Sovereign's Challenge | 10 | Ranged taunt, 10-second reuse |
| Royal Ambush | 25 | Mark from stealth; next melee hit against marked target adds 30% damage |
| Radiant Reversal | 35 | Parries retaliate for eight seconds; 45-second reuse |
| Royal Lion | 5 | Permanent companion, shared stealth and normal pet commands |
| Lion of Albion | 40 | Royal transformation with the shared power bonuses above |
| King's Advance | 15 | Instant radiant impact/teleport, 2100 range, 350 main damage plus half splash, 15-second reuse; extra primary crit chance from stealth |
| Veil of Avalon | 30 | Maintained stealth movement/concealment benefit |

King's Advance retains line-of-sight and reachable-ground checks and brings a following
lion. A lion ordered to stay remains behind. The lion does not attack while owner-hidden;
an explicit attack command reveals both. The regular lion uses installed model 100;
the player's Lion of Albion transformation uses installed Stygian Lion model 1193.
The companion grows during the transformation while retaining its lion model.

## Realm abilities

Royal Fortitude grants 3/6/9% toughness, Storm Mastery grants 2/4/6% melee/spell damage,
and Crown's Resolve grants 2/4/6% secondary resistance to all nine damage types. These
use separate Albion keys and cost 2/4/6 realm skill points per successive rank. The
same stock RA selection is available as on the installed Storm Sovereign.

Wrath of the Pendragon is free and automatically granted at RR5 (R5L0). It empowers
you and your nearby living Royal Lion for 20 seconds (+20% melee/spell damage and
+10 percentage points of melee/spell critical chance, subject to ordinary caps), then
immediately strikes attackable enemies within 500 for 300 base heat damage. Five-minute
reuse; activation breaks stealth. You must be alive, standing and free of stun/mez.

## Instant decrees

Decrees activate instantly from their original buttons, each on its own 30-second
reuse timer. The chamber experiment and preparation buttons have been removed.
Old preparation hotbar buttons can be discarded; original decree buttons still work.

## Installation and verification

`source/tools/sovereign/install_pendragon.py` previews by default. Applying requires
the selected installation to be stopped. It checks client hashes, prepares a private
database, verifies all 37 saved-progress tables, backs up every replaced file, and
verifies installed hashes. `--rollback <backup>` refuses to overwrite newer gameplay.
No server or client is started or stopped by the installer.

The client patch is generated from the verified pristine backup and preserves the
Midgard class and the secondary-resistance display fix. Albion uses separate spell,
style, template, tooltip, RA and trainer identities. Stock client catalogs are unchanged.

Automated checks cover power parity, identity collisions, Midgard/save isolation,
effect/model references, native selection stubs, rollback and shared combat behavior.
Real gameplay still needs creation/relog, all weapon styles, lion concealment/controls,
transformation appearance, terrain-sensitive King's Advance and RR5 acceptance checks.
