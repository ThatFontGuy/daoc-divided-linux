# Champion Levels (offline)

October 21, 2026. Installed only in the modern client test world (`artifacts/modern-client-test`).
Classic/Stormforged installs are unchanged.

## How it works

- **Earning:** realm points earned at level 50 become champion experience (`cl_rp_rate`, category
  `rates`, default 1.0 = one point per realm point after the normal RP rate and bonuses). Champion
  training activates immediately on reaching level 50 (and on login for existing level-50 characters); there is no king quest or
  champion trainer. Code: `ChampionRules`.
- **Levels:** CL1-15 (was capped at 10). Per level: 25,000 for CL1-5, 50,000 for CL6-10, 100,000 for
  CL11-15; 875,000 in total, about 350 level-50 enemy gamebot kills at ~2,500 realm points each.
- **One path per realm**, trained automatically: each Champion Level adds its ability to your
  "Champion of Albion/Midgard/Hibernia" spell line (`RealmChampionSpecialization`, class-0 careers at
  level 50 that only load for your realm). Stormforged and Valkyrie use the Midgard path.
- Abilities cost no power. Passives show as permanent effect icons and hold their bonuses in the
  ability category, so normal buff caps don't absorb them.
- Kept from the original system: +40 hit points per Champion Level (`hps_per_championlevel`),
  saddlebags at CL2-5, and a power pool for pure tanks at CL1.
- The CL6 break-free abilities can be used while stunned or mesmerized
  (`MasterLevelAbilities.TryBreakFree`, called first in the casting component).
- GM testing: `/player startchampion`, then `/player clxp <amount>` (875000 reaches CL15);
  `/player clearchampion` removes them.

## Paths

Passives are the same in every realm: CL1 +15 all stats, CL3 +5% all resists, CL5 faster health,
power and endurance regeneration (+10/+4/+4 per tick), CL7 +5% melee and spell damage, CL9 +5% melee,
spell and archery critical chance, CL11 +10% maximum health, CL13 +10% healing.

| CL | Albion: Round Table | Midgard: Einherjar | Hibernia: Tuatha Dé |
|---|---|---|---|
| 2 | Lay on Hands: heal self or ally 30% [2 min] | Valhalla's Call: heal self 30%, +20% endurance [2 min] | Healing Spring: heal 30% + 100 every 3 s for 15 s [2 min] |
| 4 | Smite: 400 spirit, 1500 range [30 s] | Frostbite Hurl: 400 cold + 40% snare 8 s [30 s] | Spear of Lugh: 400 energy, -10% resists 15 s [30 s] |
| 6 | Purify: break CC, immune 5 s [5 min] | Berserker's Break: same | Glamour Shift: same + stealth out of combat |
| 8 | Banner of Camelot: group +10% absorb and resists, 2 min [5 min] | Warhorn of Heimdall: group +15% damage, 1 min [5 min] | Song of the Sidhe: group +25% speed (combat too), 10% harder to hit, 1 min [5 min] |
| 10 | Judgement: stun within 500 for 4 s + 200 spirit [2 min] | Fimbulwinter: root within 500 for 6 s + 200 cold [2 min] | Glamour Mist: mesmerize within 500 for 8 s [2 min] |
| 12 | Holy Aegis: absorb all damage up to 3000, 15 s [3 min] | Unyielding: half damage taken, 15 s [3 min] | Shadowform: 50% harder to hit, 15 s [3 min] |
| 14 | Grace of Avalon: group heal 40% + cure [3 min] | Mead Hall: group heal 40% + 20% power/endurance [3 min] | Rebirth Grove: group heal 40% + 150 every 3 s [3 min] |
| 15 | Excalibur: 1000 spirit strike, group +25% damage 30 s [10 min] | Ragnarok: 20 s storm, 300 cold every 2 s within 700 [10 min] | Wings of the Morrigan: 20 s crows, 300 spirit every 2 s within 700, group +20% speed [10 min] |

Numbers are in `source/tools/masterlevels/seed_masterlevels.py` (`CHAMPION_SPELLS`); behaviour in
`spells/Masterlevel/ChampionAbilities.cs`. Spell IDs 63100-63144.

## Not covered

Companions and autonomous bots don't earn or use Champion Levels. The client's own champion trainer
window and the old off-class mini-lines (`LiveChampionsSpecialization`) are unused.

## Verification

Unit tests in `UT_MasterLevels` cover the CL table and rate, all 45 abilities, passive bonuses held
outside buff caps, and the break-free bypass; full server suite passes (3,111). Not yet checked in game.

## Correctness updates

- CL6 blocks stun (including weapon styles), mez, roots/snares, confusion and nearsight for its full
  duration, rather than merely shortening new effects. Expired or removed effects grant no protection.
- CL13's +10% healing uses the ability category, so it adds to capped healing gear.
- Repeated copies of the same ML/CL ability from different casters refresh one effect instead of
  adding duplicate bonuses. Different abilities remain compatible.
- Perfecter's Leaping Health and Rampant Healing copy the resolved heal, including variance,
  effectiveness and criticals, before missing-health limits. For group heals, the strongest resolved
  heal supplies the copy amount. Percentage heals qualify too.
