# Bainshee, Vampiir and Heretic modern test installation

Target: `artifacts/modern-client-test` only. The installer enables player classes 39 Bainshee,
58 Vampiir and 33 Heretic, which this world otherwise keeps in `disabled_classes`. Character creation
for each class is gated by `classes / enable_bainshee_test`, `enable_vampiir_test` and
`enable_heretic_test` (all default `False`; the installer sets them to `True`).

Treat this as a first playable implementation. It is not certified as matching live completely.

## Install and roll back

```
python source/tools/install_expansion_test.py artifacts/modern-client-test --classes 39,58,33           # preview
python source/tools/install_expansion_test.py artifacts/modern-client-test --classes 39,58,33 --apply
python source/tools/install_expansion_test.py artifacts/modern-client-test --rollback <backup folder>
```

The installer needs the server to be stopped. It works on a copy of the world, checks that the 37
saved-progress tables are unchanged, checks the client art, and then backs up and replaces the
database and `GameServer.dll`. It is definition-only and can be run again safely.

## Where the data comes from

- **Base data:** the full pre-1.121 spell ranks and styles come from the pinned Eve of Darkness
  donor database (`artifacts/sovereign-validation/database-donors/Eve-of-Darkness-db-public`).
- **Live changes:** the changes from 1.110 to 1.129b are applied on top. They come from the local
  copies of the live patch notes.
- **Values and procs:** the official class library supplies values that EoD lacks or has wrong. It
  also supplies the style procs.

The manifest is `source/tools/expansion_test_data.py`. Each live change sits next to the row it
changes, with the patch it comes from.

| Class | Spell IDs | Tooltip IDs | Style IDs | Spells (learnable) | Styles |
|---|---|---|---|---|---|
| Bainshee | 68000–68799 | 17600–18399 | none | 128 (126) | caster |
| Vampiir | 69000–69799 | 18400–19199 | 5800–5899 | 145 (123) | 22 Piercing |
| Heretic | 70000–70799 | 19200–19999 | 3300–3399 | 185 (139) | 43 Crush, Flexible, Shields |

Tooltip IDs stay below 32768 because the client reads them as signed 16-bit values. All 357 art IDs
resolve through this client's `spells.csv` and `icons.csv`. Three EoD icons are not in the client and
have stand-ins:

- the two Bainshee absorbs;
- Arawn's Singe;
- Monster Disease.

## Things this world lacked

The server's list of creatable classes (`GlobalConstants.STARTING_CLASSES_DICT`) had Heretic and
Vampiir commented out, so creation failed with "Wrong class" even after the install. Both are now
listed. While a class's test switch is off its race list is empty, so creation is still refused.

The installer also adds data these classes need that this world did not have:

- **Starting location:** a class start, without which new characters cannot log in.
- **Career abilities** (from EoD SpecXAbility):
  - Vampiir: leather armor, Piercing, Safe Fall, Climb Walls, the four Vampiir stat abilities and
    the eight Vampiir Bolt ranks.
  - Heretic: cloth armor, small shield, Flexible, Crushing and Staves.
- **Vampiir stat abilities:** the `Ability` rows for the four stat abilities, which use the
  server's existing `VampiirStrength`, `VampiirDexterity`, `VampiirConstitution` and
  `VampiirQuickness` classes.
- **Styles and procs:** all weapon styles for both melee classes. This world had none, and its
  Hibernian piercing styles have no procs at all, so each proc is a new kit spell built from the
  class library effect.

## Bainshee

- **Spectral Force (baseline):**
  - The AF, absorb, bladeturn and Pain nuke are unchanged.
  - 1.128 added the Spectral Cords root line.
  - 1.129 moved Alarming Screech, the mez cure, here at 26.
- **Spectral Guard:**
  - 1.121 moved the ablative chant to 20/30/40 and the single-target root into this line.
  - 1.122b moved the cone root to 46.
  - The Bawler nukes and bolts use class library damage.
  - 1.126 added Bawler's Obliteration, a cone nuke with a snare.
- **Ethereal Shriek:**
  - 1.121 made the nukes and bolts Cold. 1.122b consolidated the line.
  - 1.121b made the pulsing nearsight.
  - Deafening Cascade does 315.
  - The Torment Cold DDs are included.
  - Reverberating Yell, Shriek and Scream are Body debuffs from 1.127, raised to 10/30/50% in 1.128c.
    Scream also applies 40% Energy and Spirit debuffs for 12 seconds.
  - Ethereal Shriek is the level 50 area pet scare, with radius 2000 and 5-minute reuse. Its fear
    does not grant pet-fear immunity (1.124b).
- **Phantasmal Wail:**
  - Restricting Yelp through Scream are AoE Body nukes with a 10% Body debuff (1.121).
  - The pulsing PBAoE chant has 2.5-second pulses.
  - The PBAoE roots are included.
  - Fear Minion through Terrify Minion are at 9/19/29/39/49 with a 3.5-second cast (1.122b–1.129).
  - Resounding Aura does 375 Body damage to realm targets only (1.126 and the 2020-02-12 hotfix).

### 1.130a pass (daoc.gg live spell data)

Every Bainshee spell was compared against live's 1.130a spell data. The kit already had seven of the eight live
names a cross-check reported missing, under older names:
- **Ethereal Shriek area nukes:** the kit ran one rank behind live. They are now Roaring Concussion (1), Resonant
  Concussion (11), Clangorous Burst (21), Resonant Explosion (31) and Deafening Explosion (41), with live damage of
  38/73/114/157/174 and costs of 4/8/14/23/27.
- **Dex/Qui debuffs:** Diminishing Screech, Wail, Bellow, Shriek and Scream (3/13/23/33/43). They are live's
  targeted area debuffs: 24/32/49/60/70, 45 s, range 1500, radius 350, 7 s reuse.
- **Body debuffs:** Reverberating Wail, Shriek and Scream last 8 s and cost 10/16/23 power.
- **Bolts:** Thunderous Burst is now Thunderous Blast; the damage already matched.
- **New, Sound Vortex:** a ground vortex that hits up to 8 enemies within 1500 units for 300 every 4 s, for 30 s.
  10 s cast, 25% power, 10 minute reuse (`DeathKnightGround`, damage kind). Live has it at Spectral Guard 50
  beside Bawler's Obliteration. The client casts one spell per level in a list line, so it sits at 38, the nearest
  free level.

The Spectral Force bolts keep this world's range 650 and radius 100. Live's data lists 650 as the radius for the
whole family, which looks like the same value in a different field.

## Vampiir

- **Devouring Bolt (class ability):**
  - Can be cast in combat (1.123). This changed `VampiirBoltSpellHandler`.
  - Range 1875, reuse 45 seconds.
  - The ability handler looks for its stock spell IDs first, then falls back to the kit range.
- **Dementia:**
  - The claws are included.
  - The self melee and magic resist buffs have a 45-second reuse (1.129).
  - The armor debuffs and mezzes are included.
  - The +skill and effectiveness debuffs are at 1.121c levels, with Impress Confusion at 36.
  - Self Destruction is included.
  - The Night's Servant pet and its sacrifice were added in 1.121 and removed in 1.125, so they are
    not here.
- **Shadow Mastery:**
  - Enervating Embrace is removed. Renewal is at 20 and Flaring Claw at 18.
  - 1.121 moved the fumble here at 11/21/32. It has a 60-second reuse and 10/20/30% chance (1.128).
  - The Flight spells (Bat, Marrach, Gargoyle, Shadow, Darkness) last 45 seconds and cost 15% power.
    You must stand still to cast them (1.123/1.124b). They stay up in combat: the new `VampiirFlight`
    type skips the combat check and the speed-buff cancel on attack.
- **Vampiiric Embrace:**
  - The Heat DDs have range 750 (1.129b). Blaze is at 35 and Inferno at 49.
  - 1.121 moved the haste here at 11/16/29/36/45. Haste shares one reuse timer with the weaponskill
    and evade buffs.
  - The NPC dismissal is removed.
  - The new `VampiirDetermination` type adds the four self Determination buffs:
    - Shadow's Will, 21, 8%
    - Shadow's Endurance, 32, 17%
    - Shadow's Perserverence, 39, 30%
    - Shadow's Spite, 47, 46%

    Each reduces mesmerize, stun and snare/root duration and lasts 180 seconds. The patch notes give
    no power cost, so the costs here are estimates.
- **Claw power:**
  - 1.121c raised the level 48 claws to 36. 1.122b lowered them to 28.
  - 1.127 raised every claw cost by 33%.
- **Piercing styles:**
  - The styles use the Vampiir client style IDs (418–439).
  - Vampiiric Feint raises spell crit to 25% for 10 seconds, through the new `VampiirFeint` proc type.
  - Eye Shot, Lung Shot and Knee Cap are front, side and back positionals on client styles 577–579
    (1.123).

## Heretic

- **Rejuvenation:**
  - The Arawn's ramping focus nukes are included.
  - The Blazing focus snares are 50%.
  - The Lava AoE focus snares have range 1650 (1.126) and a 40% snare (1.128).
  - Glistening, Whirling and Torrential Blaze are included. Torrential casts in 2.5 seconds
    (2020 hotfix).
  - The spec heals are included.
  - The Embers line is now an instant direct-damage shout with a 15-second reuse, and Bursting is
    at 38 (1.123).
  - Fiery Grasp through Fiery Stranglehold have range 1000 (1.123) and a 30-second reuse (1.126).
  - The 1.125 Cocoon line (Afflicting through Destructive Cocoon, 7–49) replaces the old focused
    snare. Each Cocoon is a 3-second cast that puts a 10–200 point ablative on the enemy. The ablative
    absorbs all damage. It also applies combat effectiveness and melee swing speed debuffs that rise
    every 2 seconds and end when the ablative breaks. It always lands, lasts 60 seconds and cannot be
    reapplied while it is active. This is the new `HereticCocoon` type. The patch notes give no power
    costs, so these keep the old spells' opening costs.
  - Arawn's focus nukes have range 1650. The uninterruptible Blazes have range 1600 (1.125).
  - The Dark Ashes–Dark Magma Matter nukes come from 1.121.
  - Reanimate Corpse is included.
- **Enhancement:**
  - Chthonic, Kindled/Molten AF, Infernal damage add (Tear at 37) and Arawn's piercing are included.
  - The Buffers are included. Warmth and Heat moved from the baseline (1.121). Absorb is
    10/15/20/25/30/33% (1.125).
  - The spec AF buffs give 68/94/136/165/250/360/400 AF (1.125).
  - 1.121 added the Constitution, Strength and Dexterity debuffs and Endowment Seize.
  - The single and group damage shields and the Accursed buff-shear procs are removed (1.121).
  - The new `HereticHellflower` type adds the Hellflower chant. It is instant, pulses every
    6 seconds and costs 10% power. It raises the group's health and armor factor by
    1/2/3/4/6% (1.123, reduced in 1.125).
- **Enhancement baseline:** the concentration buffs, with Aura of Deflection at 150 AF (1.122b).
- **Styles:**
  - The class library procs are included.
  - Bone Crusher has Very High damage and strips one buff from each enemy within 350.
  - Shadowfire (Crush 50, back, 113 Heat) is included.
  - Leviathan is a back positional with 113 Heat.
  - Indigosnake returns 30% of its damage as health (1.126).

## Realm abilities

The class RR5s are bound: Sonic Barrier (Bainshee, which affects the Bainshee too since 1.128),
Mark of Prey (Vampiir, with the 1.128 +20% crit) and Fanaticism (Heretic, 15 seconds since 1.128).

The shared lists match EoD, with these live changes on top:
- **Heretic:** Static Tempest (1.125). 1.121 added Ichor of the Deep and 1.125 removed it again.
- **Vampiir:** Mastery of Focus (1.114b), Mastery of Magery and Dual Threat (1.123).
- **Charge:** costs 3/3/3/5/6 points (1.128c). This applies to every class that has Charge.

## Fixes after the first in-game test

- **AF buffs:** EoD's `ArmorFactorBuff` type is abstract on this server, so the AF buffs had no
  tooltip and could not be cast. This affected the 10 Bainshee buffs and the 14 Heretic buffs.
  Baseline AF now uses `BaseArmorFactorBuff` and spec AF uses `SpecArmorFactorBuff`. A test now
  checks that every kit spell type has a concrete handler.
- **Vampiir Bolt tooltip:** the ability tooltip now describes the bolt rank you cast. The client has
  no text of its own for it.

## Not done

- **Bainshee:**
  - Sound Vortex is not added; its live details are unknown.
  - The 1.125d pulse-list interface rule is not modelled.
  - The cancel-on-move code of the old pulse handler is half disabled.
- **Vampiir:**
  - Vampiir's Bite (1.121/1.124b) is not added. The current class library no longer lists it, and
    there is no client style for it.
  - The library's level 2 "Hornet" style has no client style.
- **Heretic:**
  - Hellfire Tendrils (Crush 30, 1.123) has no client style.
  - The 1.121 Reanimate Corpse rework (50% resurrection with disease) needs handler work.
  - The 1.121 Cure Poison/Disease 2.4-second cast is not applied. The Rejuvenation baseline line is
    shared with Clerics and Friars.
  - The 2018-11-14 ablative/debuff hotfix is not applied.
  - The Hellflower armor share is a percent of the member's worn torso armor AF. Live does not say
    how its armor factor percent is measured.

## Tests

- `source/tools/test_expansion_test_data.py`: 9 tests. They cover rerunning the installer, save
  preservation, start locations, tooltip limits, art and sub-spells, each class's live changes, the
  styles and career abilities, the realm-ability access and the Cocoon values. They also check that
  every spell type has a concrete server handler.
- `Tests/UnitTests/UT_ModernExpansionClasses.cs`: 12 tests. They cover Flight in combat, the
  Determination properties, the Feint spell crit, the Hellflower amounts, the pet scare without
  immunity, the race switches and creation for every eligible race. They also cover the Cocoon's
  ramp and removal, the Charge costs and the Vampiir Bolt description.

In-game checks so far (owner): all three classes can be created and their spells work. The AF buffs
and the Vampiir Bolt tooltip were missing in that test and have been fixed since. They have not been
checked in game again.
