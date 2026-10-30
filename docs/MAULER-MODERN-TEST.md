# Modern Mauler test build — all three realms

Installed October 24, 2026 into `artifacts/modern-client-test` only. Native class
IDs are Albion 60, Midgard 61 and Hibernia 62. Custom classes remain 63–65.
`enable_mauler_test=True` enables creation; the installer requires
`native_custom_class_slots=True` before changing anything.

Each realm has **133 learnable spells and 32 styles**: 128 shared spells and five
realm-specific damage gifts, with 16 Fist Wraps and 16 Mauler Staff styles.
There are 245 server spell definitions including internal aura/style effects.
Existing Mauler trainers are already present in all realms. New characters get
valid realm starting positions, bind points, leather armor, two training fist
wraps and a Mauler Staff. This build covers human players; bot support is separate.

## Implementation

- Strength-based power pool and the existing Mauler out-of-combat drain are
  retained. Hostile incoming damage now generates power from actual health loss,
  with fractional accumulation for small hits. Self/environmental damage and
  fully absorbed hits do not generate power. Power and endurance taps are bounded
  by available resources; the damage-based taps use the existing PowerDrain handler.
- Both maintained aura modes are present. Gift effects depend on the selected
  aura, with matching internal spell variants. Switching during a cast is blocked.
  Staff-conditioned gifts check the equipped weapon and **trained** Staff skill
  at cast start and completion. Nethuni and Tegashrig are exempt from Staff checks;
  Tegashrig still chooses weaponskill or evasion according to aura.
- Gift of Perizor roots under Wildbull and drains power under Farseer. Realm
  gifts use Matter/Body in Albion, Cold/Spirit in Midgard and Heat/Energy in
  Hibernia. Arasthai supplies melee or magic potency. Gift of Renewal is an 85-point
  offensive heal proc, with a 25% trigger chance.
- Magnetism includes maintained and pulsing snares, PBAE and cone roots,
  casting-speed debuff pulses, Matter debuffs, damage-to-power protection and Gift
  of Precision. Climbing Spikes is granted at specialization 50; the top pulsing
  snare is at 49.
- Power Strikes includes endurance taps, health-to-power damage taps, kicks,
  damage adds, fumble, melee dehaste, silence, disarm and Gift of Form.
- Silence/disarm and the formerly unmapped stat effects use dedicated ECS
  handlers. Evasion and weaponskill apply separate properties. Effects remove
  their own contributions on expiry/cancellation.
- Staff styles implement the redesign: Wild Swing's bladeturn penetration,
  Jolting energy proc, Turbid combat speed, ablative stripping, Scorching casting
  debuff, Forging bleed and Farseer's free spell/style costs. Fist Wraps uses the
  later Gut Shot and Phoenix Strike chains.
- Aura Convergence sacrifices nearby group power, returns offered power to the
  Mauler, drains hostile power within 500 up to the remaining pool capacity, and
  protects nearby group members from 33% magical damage for 30 seconds.

The selected current balance changes include 13/16/20/28% specialization absorb,
30-second dehaste with 60-second reuse, 10/20/30% fumble with three-minute reuse,
halved Nethuni healing, and Phoenix Strike following Owl Strike with a 130-damage
proc. Baseline Constitution follows the live 1.114b values rather than the older
Class Library. Specialization multiplier is 1.8, the latest verified primary-source
value found in this pass.

## Evidence and limits

Primary sources:

- [Official Mauler Class Library](https://www.darkageofcamelot.com/class-library-mauler/)
- [1.114b live deployment and Mauler changes](https://www.darkageofcamelot.com/2013/07/01/1114b-comes-live-servers/)
- [1.123 redesign](https://www.darkageofcamelot.com/1123-live-patch-notes/)
- [1.124C staff exemption and casting changes](https://www.darkageofcamelot.com/1124c-live-patch-notes/)
- [1.124D realm gift costs and cast time](https://www.darkageofcamelot.com/1124d-live-patch-notes/)
- [1.126 Convergence changes](https://www.darkageofcamelot.com/1126-live-server-patch-notes/)
- [1.128 control, healing and style changes](https://www.darkageofcamelot.com/1128-live-server-patch-notes/)
- [1.129b final selected balance overrides](https://www.darkageofcamelot.com/1-129b-live-patch-notes/)

The broader historical ledger is `../../Class-Research/codex/expansion-restoration/MAULER.md`
and `PATCH-RULES.md` beside it. The retrieved library rows are normalized in
`source/tools/mauler-library-rows.json`; obsolete rows are excluded explicitly.

This build needs an in-game comparison pass before full live parity can be claimed:

| Item | Current treatment / remaining verification |
|---|---|
| Incoming-damage power coefficient | Test rule: losing X% maximum health supplies X% maximum power. Retail coefficient is unresolved. |
| Damage-protection power conversion | Absorbed health fraction is scaled to the Mauler's pool. Exact retail conversion and stacking remain to compare. |
| Style growth/endurance/hit/defense coefficients | Explicit estimates from published qualitative bands, not measured retail factors. |
| Destructive Blow | Library has a zero-damage apparent error; test value 165 needs authoritative confirmation. |
| Burdening Grasp cost | Library omits its numeric cost; test default is 16% base power. |
| Lower Farseer realm gifts | Retain the published 1-damage values; later correction evidence is still needed. |
| Passive progression | Initial Evade and Protect plus armor/weapon grants are installed; later passive tiers need verification. |
| Damage-based power taps | Existing damage-return model; retail target-level limit remains to reconcile. |
| Convergence | Ally offer/current-power interpretation and damage-stack interactions need live comparison. |
| Item/set interactions | Dark Fury conversion bonus, item-specific procs and exact live loot are separate work. |
| Realm abilities / RR5 | Existing three-realm RA mappings are preserved. The obsolete RR5 identity is not rebound; current RR5 reconciliation remains open. |
| Client presentation | All assigned catalog art references resolve; family artwork is reused for missing modern names. Exact animation playback needs in-game validation. |

The two aura stances and temporary Mauler utility effects clear on logout.
Ordinary native spell effects retain the engine's existing save behavior.
No stock client catalog, texture, model or game binary was modified.

## Validation and installation

Release build passed. **72 focused and adjacent regression tests passed**, including
Mauler mechanics, native/custom slots, Warlock and Valkyrie effect behavior.
**Seven migration tests passed**, covering repeat installs, save preservation,
foreign-ID rejection, valid three-realm starts, matching style trees, starter
weapons, later live overrides, aura variants and art references. All 37 tracked
saved-progress tables were unchanged during installation.

Server spell IDs 67000–67999, tooltip IDs 31200–32199 (moved from 34000–34999; see below) and class-scoped style IDs
4000–4031 are reserved for this kit. The test installer backs up the current
database and binaries, verifies it is stopped, and deploys the tested DLL to all
three server locations. It does not start the server.

```powershell
python source/tools/install_mauler_test.py artifacts/modern-client-test --build-dir artifacts/mauler-tested-build
python source/tools/install_mauler_test.py artifacts/modern-client-test --build-dir artifacts/mauler-tested-build --apply
python source/tools/install_mauler_test.py artifacts/modern-client-test --rollback <backup-directory>
```

Rollback refuses to overwrite later gameplay. Preserve private backups; do not
commit or distribute played databases or saved credentials.

## In-game acceptance

Restart `START MODERN CLIENT TEST.exe`. Create a Mauler in each realm and verify
the native name, appearance, starting position, bind point, weapons and five
trainable specializations. Relog and check the class identity again. Existing
custom characters should continue showing their original custom class.

Test both weapon trees, offhand swings, aura-dependent gifts with insufficient
and sufficient trained Staff, casting with a Staff unequipped, low-power recovery
from hostile hits, drain caps, control timers, buff expiry, style chains and
Farseer's zero-cost window. Compare styles, buff icons and tooltips in the client.
Automated checks are separate from this in-game pass.

## Tooltip fix, October 24 (Claude)

The owner reported that most Mauler spells showed wrong tooltips. The client delve text comes only from a handler's
`ShortDescription`. Four Mauler handlers returned the database `Description`, which for most rows is the placeholder
"Modern Mauler test kit.".

- **Stat spells** (`MaulerStat`: Demand casting-speed debuffs, Nurizane fumbles, Gift of Precision, Gift of Form, Tegashrig weaponskill and evasion) now describe their effect, value, radius and duration.
- **Silences and disarms** (`MaulerControl`: Demand Respect, Reverence and Awe; Perizor's Disarming Strike, Bash and Blow) now say silence or disarm and for how long.
- **Utility spells** (`MaulerUtility`): Tegashrig protection, Perizor power drain, Arasthai magic potency and the style utility effects describe themselves. Aura Convergence keeps its written description.
- **All 35 gifts** (`MaulerGift`) keep their description and now also list what the gift does under the Aura of the Wildbull and under the Aura of the Farseer, using each child spell's own tooltip.
- Stock-type spells (snares, roots, buffs, kicks, taps, absorbs) already built their own tooltip text and are unchanged.

The spell lines themselves were checked: all three Mauler classes have their five specializations, and every line is linked to its spec with its spells (Aura Manipulation 34, baseline 10, Magnetism 37, Power Strikes 47, each realm's gift line 5).

Validation: 3,333 server tests passed, including 3 new tooltip tests. The Mauler data tests passed. The installer verified 37 progress tables. Backup: `backups/mauler-test-20261024-153742-267812`. Tooltips the client cached earlier may need a relog.

**Tooltip IDs moved below 32768 (October 24):**
- In game, hovering a Mauler spell showed no tooltip at all; only the debug line "Delve objectType=24, objectID=34xxx" appeared.
- Every custom kit whose tooltips work sits below 32768: ML/CL 21000, Sovereign 24000, Valkyrie 27000, Warlock 28000 and Sluaghbinder 29000. The Mauler kit alone used 34000–34831.
- The client evidently reads the delve index as a signed 16-bit value, so a reply indexed 34xxx never matches its request.
- Mauler tooltip IDs are now 31200 + (spell ID − 67000), including the Jolting Energy style proc that had a hard-coded 34701.
- The installed range is 31200–32031, with no collisions.
- A new migration test fails if any Mauler tooltip ID exceeds 32767.
- Backup: `backups/mauler-test-20261024-154356-675153`.

