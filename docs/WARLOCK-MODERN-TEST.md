# Warlock first modern test installation

Target: `artifacts/modern-client-test` only. Player class 59, gated by
`classes / enable_warlock_test=True`. The installer enables only this additional
class and leaves existing realm abilities, Valkyrie and other class data intact.

This is a first playable implementation, not certification of complete live parity.
Research and remaining source reconciliation are in
`../../Class-Research/codex/warlock/MODERN-LIVE-SPEC.md`.

## Included

128 learnable spells, plus seven internal effects: baseline matter damage/bolts/roots;
Cursing spirit damage, secondary PBAE and nearsight; Hexing energy lifetaps,
constitution debuffs, secondary snares and AoE roots; Witchcraft healing, group
healing, absorb, AF debuffs, cures, resurrection, mobile regeneration and the
Dread–Anguish–Agony–Doom chain. No weapon styles are added for this caster class.

All 17 primers are maintained mutually exclusive stances, with instant activation,
no activation power charge, and no switching during casts. Secondary spells need
an active primer. Range stances increase range/radius and cost 5% base power;
uninterruptible stances use rank-specific base-power costs and damage penalties;
powerless stances trade longer casting for no power cost. Ordinary and secondary
casts use Dexterity; chamber loads always take six seconds.

Six fixed chambers load while stationary. Use the same chamber again to release
its effect instantly, including while moving. Releases share a ten-second reuse.
Loaded chambers appear as buff icons. Floating chamber orbs are not implemented.
Primers and chambers clear on logout rather than persisting incomplete state.

The chain checks effects belonging to the caster at cast start and completion.
Agony requires Dread and Anguish; Doom also requires Agony. Doom lasts ten seconds
and detonates on expiry or explicit cure, excluding Purge, replacement and death.
Dread grants a magic ablative; Agony applies disease. Chain values follow the
[1.121 redesign](https://www.darkageofcamelot.com/1121-live-patch-notes/), updated by
[1.123](https://www.darkageofcamelot.com/1123-live-patch-notes/), and later revisions
listed in the research guide (notably normal-casting Agony and Matter Doom).

Server spell IDs 66000–66399 and independent tooltip IDs 28000–28399 are reserved.
All assigned art IDs resolve through this client's `spells.csv` and `icons.csv`.
Some ranks reuse the nearest Warlock family artwork where the catalog lacks an
exact named match (including new chain/chamber effects). These are explicit
provisional art choices; there are no new client assets or binary patches.

## Still to complete for live parity

- Baseline AF/bladeturn and low-level baseline absorb; currently Witchcraft
  specialization absorb is present.
- Hexing AoE damage/snare, combined resist debuffs and pet fear/immunity.
- Cursing Torrent's restricted RvR target rules.
- Witchcraft Misery, group healing-potency aura and spread heals.
- Full realm ability modernization and RR5 integration remain the existing
  realm-ability work; this installer preserves its mappings.
- Chain power is provisionally 7% base power, range 1500. Top Dread reuse uses a
  provisional 12 seconds. Published evidence does not settle those values yet.
- Chamber direct percentage healing uses maximum health and the existing direct
  health-change API; disease/critical/healing-potency interactions need validation.
- Orb presentation, exact family icon choices, animation playback and real
  combat behavior still require an in-game pass.

## Install and recovery

From the `Source` directory:

```powershell
python source/tools/install_warlock_test.py artifacts/modern-client-test
python source/tools/install_warlock_test.py artifacts/modern-client-test --apply
```

The installer refuses a running target, backs up all replaced files, verifies
37 tracked save tables, checks database integrity and copies the tested DLL to
all three runtime locations. It never starts or stops the server.

Rollback before further gameplay with the returned backup directory:

```powershell
python source/tools/install_warlock_test.py artifacts/modern-client-test --rollback <backup-directory>
```

Rollback refuses to overwrite files changed since installation, including newer
saved progress. Backups remain private and must not be committed or distributed.

## In-game checks

The October 24 login failure exposed a missing class-59 `StartupLocation` record:
new Warlocks were saved with region and coordinates zero. The migration now adds
a generic modern Midgard Warlock start using the existing Valkyrie start in region
100. `source/tools/repair_warlock_start.py --apply` backs up the selected world and
repairs only Midgard Warlocks with zero region, zero coordinates and zero bind
region. It checks every other character field and all other saved-progress tables.
The originally affected character was repaired in place; six migration/repair
tests pass. A successful in-game login remains to be confirmed.

Launch `START MODERN CLIENT TEST.exe`, create a Midgard Warlock and confirm the
three specializations. Existing trainers include Runda and Thidar in Jordheim.
Verify primer switching and costs; cast a secondary with and without a primer;
compare casting speed and UI interruptions. Load multiple different chambers,
release while moving, and verify shared reuse and their fixed effects. Check
tooltips/icons, chain prerequisites, cure versus Purge, target death, friendly
healing and resurrection. Automated checks do not replace this pass.

## Primer and chamber fix, October 25

**Tester report:**
- Primers switched off at once, so a secondary only went off when the primer and the spell were pressed together.
- Chambers announced they were loading and then did nothing.

**Cause:** the primer stance and the loaded-chamber state were spell effects with no duration. The effect service ends
such an effect on its next tick unless its expiry is pushed out, as the Death Knight forms and the Storm Sovereign chant
already do.
- Primers (`WarlockPrimerEffect`) are now held until changed or cancelled.
- Loaded chambers (`WarlockReadyEffect`) are now held until released.
- The Mauler aura (`MaulerStanceEffect`) had the same fault and is fixed with them.

**Chambers:** the kit follows live since the 1.114b redesign.
- Each of the six chambers loads a fixed effect: 6 seconds, standing still.
- Using the same chamber again releases it instantly, even while moving.
- Releases share a 10-second reuse.

Storing an arbitrary spell in a chamber is the pre-1.114b design and is not the target. A regression test covers the
three effects.

**Still to recheck in game:** bolt cooldowns, and whether primary (non-secondary) spells cast without a primer. The data
and server code allow both; the tester's reports may have come from the primer fault.

## Current-live pass, October 24 (Claude)

Built on Codex's first kit, using its research guide plus the Warlock sections of the official 1.114b, 1.116,
1.122b, 1.123 and 1.126 notes. 1.130a is deployed live but lists no Warlock spell changes. The kit now has 171
spell rows (spell IDs 66300–66360 are new).

**Spells added:**

| Line | Spells | Live source |
|---|---|---|
| Cursing spec | Secondary bolts: Lesser/Greater Bolt of Ruin (2, 4), Lesser/Greater Bolt of Havoc (9, 14), Bolt of Destruction (20), Greater Bolt of Destruction (24), Lesser Bolt of Death (28), Bolt of Death (36), Greater Bolt of Death (48). 14 to 324 damage, 1875 range, 20 s recast, no power. Spirit damage, since 1.127 makes specialization direct damage Spirit. | 1.114b, 1.127 |
| Cursing spec | Spellbinder's Torrent (50): secondary PBAoE, 365 damage, radius 300, no snare. A new `WarlockTorrent` handler hits only enemy realm players, gamebots, pets and keep guards; ordinary monsters are never hit. | 1.126, 2020-02-12 hotfix |
| Hexing | Secondary AoE damage and 35% snare: Hex of Creeping (5), Slowing (9), Lumbering (19), Crawling (30), Hindering (36), Snaring (46). 13 to 131 damage, 350 radius, 30 s, no power. | 1.114b, 1.116, 1.122B |
| Hexing | Matter debuffs: Malevolent Affliction (23, 15%), Pestilence (34, 30%), Scourge (45, 50%); 8 s, 2 s cast. Scourge also applies 40% Cold and Heat debuffs for 12 s through sub-spells. | 1.116, 1.128c |
| Hexing | Single-pet fear: Fear, Expel, Intimidate, Daunt and Terrify Slave (1/11/21/31/41), lasting 5/9/15/22/30 s with a 3.5 s cast, then a 60 s immunity. A new `WarlockPetFear` ECS handler accepts enemy pets only. While feared, the pet stops attacking and runs from the Warlock every second; its master's commands do not hold. | 1.122B, 1.123B, 1.129 |
| Witchcraft | Healing-potency aura: Relaxing, Restful, Soothing, Calming and Ameliorating Incantation (9/19/27/34/45), +2/4/6/8/10% healing for grouped allies. Pulses every 8 s for 10% power. New `WarlockHealingAura` handler; the healing-effectiveness calculator already counts base buffs, inside its 25% cap. | 1.123, 2018-03-28 hotfix |
| Witchcraft | Misery AoE DoT: Puny, Weak, Minor, Lesser Misery and Misery (3/13/23/33/43), 6 to 83 spirit damage every 2 s for 12 s, radius 350. | 1.123 |

**Icons:** the 1.130 client already contains the modern Warlock art, so these now use their real entries instead of borrowed Infernal icons:
- Dread 1–4, Anguish 1–4, Agony 1–3 and Doom (15069–15084).
- Agony Disease and Doom's final hit.
- Pet Fear 1–5 (15197–15201).
- Misery Grey to Red (15407–15411).
- Warlock Heal Aura Grey to Red (15412–15416).
- The secondary bolts use the client's own Bolt of Ruin to Bolt of Death entries (12065–12074).

Provisional art: the Hex AoE line uses the Beguiled family (12101–12106), the Matter debuffs use 12057–12059, and the constitution and AF debuffs keep Codex's choices. All 147 distinct icons resolve through `spells.csv` and `icons.csv`.

**Realm abilities** (installed by the RA migration, not this kit's installer):
- Class 59 now also has Mastery of Concentration (1.114b), Mastery of Healing and Wild Healing (1.116) and Ichor (1.121); 1.128 removed Ichor only from Minstrel and Valkyrie. Concentration (1.125) was already bound.
- RR5: Boiling Cauldron is rebuilt as `ModernBoilingCauldron`:
  - A cauldron appears at the enemy target (1500 range) and spills after 3.5 s (1.108).
  - It deals 650 heat damage to the 8 nearest enemies within 350 (1.128).
  - It bedazzles them for 20 s with a 30% chance to fumble melee (FumbleChance debuff) or miscast spells (a finished cast can fail, checked in `SpellHandler.CheckEndCast`) (1.128, 1.129b).
  - It is unresistable, with a 10-minute reuse.

**Still open:**
- Baseline AF and bladeturn, the low-level absorb and the normal-casting spread heals: no live values in the notes reviewed.
- The level-42 Dread reuse and the chain power cost (Codex's provisional values stand).
- The Matter-debuff middle rank: 30% is the library figure; 1.116 says 25%.
- Bot support for the new spells.
- In-game checks: Torrent targeting, the fear flee path, pulse cost and aura stacking, and the bedazzle miscast message.

Validation: 3,300 server tests passed, including 4 new Warlock tests (Torrent targets, aura property, fear immunity, cauldron bedazzle and reuse). The 7 Warlock data tests passed, including a new test of the live additions and icons, along with the 14 RA migration tests.

**Tooltip fix (October 24):** the owner asked whether secondary spells (Spell Burst and the others) really cost nothing under Skillful Cast.
- The mechanics were already right:
  - A secondary refuses to cast without a primer.
  - Powerless primers (Pure, Fluent, Skillful, Artistic and Masterful Cast) make secondaries free but slower.
  - Range primers charge 5% of base power, and Uninterruptible primers charge their listed percentage of base power.
  - All of this goes through `ModernWarlock.SecondaryCost` in `SpellHandler.PowerCost`.
- The tooltips said none of this. The client delve text comes only from a handler's `ShortDescription`: the primers showed one generic sentence, and secondaries had no note at all.
- Primers now show their own rank text (penalty and secondary cost).
- Every Warlock secondary's delve now ends with a note explaining the primer requirement and costs (`ModernWarlock.DelveNote`, appended in `SpellDelve`).
- A new test covers both. Tooltips the client cached before the update may need a relog to refresh.

