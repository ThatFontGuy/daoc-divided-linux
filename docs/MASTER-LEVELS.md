# Master Levels (offline)

October 21, 2026. Progression plus all eight paths. Installed only in the modern client
test world (`artifacts/modern-client-test`). Classic/Stormforged installs are unchanged.

## How it works

- **Earning:** training activates automatically on reaching level 50, and on login for existing
  level-50 characters. No quest, command or path selection is needed to start earning. There are no
  Trials of Atlantis encounters. Experience earned at level 50 fills the
  ML bar; each full bar raises your Master Level, up to ML10. At `ml_xp_rate` 1.0 (server property,
  category `rates`) one ML costs the experience of one level 49 to 50; 2.0 is twice as fast, 0 turns
  it off. Normal `xp_rate` and XP bonuses apply first. Code: `MasterLevelRules`.
- **Paths:** every class (including Stormforged and Valkyrie) may take any of the eight paths. They
  are class-0 careers acquired at level 50, seeded in a fixed order by
  `source/tools/masterlevels/seed_masterlevels.py`; never reorder them, because a character's path
  is saved as an index into that order.
- **Choosing:** `/ml` (or `/masterlevel`) shows your ML, path and progress. `/ml path <name>`
  picks or changes the path, out of combat; your ML level carries over. GMs can still use
  `/player startml`, `/player setml <0-10>` and `/player setmlline <0-7>`.
- ML abilities appear in a spell line named after the path, one ability per Master Level.
  They cost no power, so every class can use them.

## Stormlord (built)

Rebuilt on the ECS effect system; the old handlers used hooks this server no longer calls and only
targeted players. Storms are placed at your ground target (1,500 range, 3 s cast), cover a 350 radius,
pulse every 4 s for ten minutes and reuse in 30 s. You keep one storm of each kind; recasting moves it.
Storms hit monsters and enemy players, end when you die, change region or log out, and draw monsters'
aggro to you.

| ML | Ability | Effect |
|---|---|---|
| 1 | Dazzling Array | Storm: you, your group and pets inside are 15% harder to hit |
| 2 | Vacuum Vortex | Gather all your storms at your ground target (10 s reuse) |
| 3 | Enervating Gas | Storm: drains 15% endurance per pulse; you gain half |
| 4 | Inebriating Fumes | Storm: −60 dexterity and quickness while inside |
| 5 | Mental Siphon | Storm: drains 10% power per pulse; you gain half (monster power is bottomless, so vs monsters it only feeds you) |
| 6 | Focusing Winds | For 60 s your storms pulse twice as often (2 min reuse) |
| 7 | Choking Vapors | Storm: −60 strength and constitution while inside |
| 8 | Sense Dulling Cloud | Storm: −60 intelligence, piety, empathy and charisma while inside |
| 9 | Energy Tempest | Storm: 250 energy damage per pulse to each enemy inside |
| 10 | Arcing Power | Your next single-target damage spell within 30 s also hits enemies within 350 of the target for 50% (1 min reuse) |

Classic ML2/ML6 pushed and held drifting storms; these storms stay put, so those two were changed
as above. Debuffs are held while an enemy stays inside and removed the moment it leaves or the storm
ends. Visuals and icons are the client's own Stormlord effects (7205-7305 range). Numbers live in the
seed script. "Harder to hit" (`eProperty.MissHit`) now counts in the melee miss roll.

## The other seven paths (built)

One spell type, `MasterLevelAbility`, dispatches on spell ID to the table in
`spells/Masterlevel/MasterLevelAbilities.cs`; ranges, radii, durations, damage and reuse timers are in
the seed script, bonus sizes in that table. Timed buffs/debuffs use one stackable ECS effect
(`MasterLevelEffect`, icon shown); ground objects (fonts, wards, runes, constructs) are
`MasterLevelField`s, one per caster per ability, ending with their duration or when you die, change
region or log out. Shouts and fields hit monsters and enemy players alike; the abilities themselves
can't be resisted, while the stock snares, mez, stun, fear and DoTs they apply roll normal resists.
The old legacy handlers stay in the folder for other content but are no longer used by MLs.
Siege/RvR-only skills were replaced with ones that also work in PvE (marked *).

**Banelord** (shouts around you): 1 Zone of Unmana (enemies cast 50% slower, interrupted) ·
2 Primal Agony (-10% current health up to 1500, power, endurance) · 3 Oppression* (40% snare, 20%
slower attacks) · 4 Inexorable Defeat (+50% endurance costs, -15% melee damage) · 5 Tactical Insight
(allies 15% harder to hit) · 6 Snaring Tendrils (50% snare, no self-stun any more) · 7 Chaotic Power
(allies +10% to hit, +10% resist pierce) · 8 Agony Transmission (-25% current health up to 3000, costs
half your health) · 9 Demoralization* (enemies -20% melee/spell damage) · 10 Banestrike (allies +15%
melee/spell damage).

**Battlemaster** (targeted, any class): 1 Sapping Strike (200 dmg, nearby enemies -25% endurance) ·
2 Faultfinder* (150 dmg, -20% absorption) · 3 Power Leak (interrupt + power drain around target) ·
4 Grapple (target rooted and half melee damage; you stay free) · 5 Essence Flames (group damage add) ·
6 Throw Weapon (1000 range, 300 dmg) · 7 Essence Sear (-15% magic resists around target) ·
8 Bodyguard* (ally +20% absorption, 10% harder to hit) · 9 Essence Dampen (-50 dex/qui around target) ·
10 Essence Shatter (dispel one buff + 250 dmg around target).

**Convoker** (ground objects): 1 Warding Crystal* (allies inside +10% absorption and resists) ·
2 Prescience Node (reveals hidden enemies, -10% resists) · 3 Power Trap (rune: 4 s stun, 250 dmg,
power drain) · 4 Speedwarp (enemies inside snared 50%) · 5 Summon Warcrystal* (turret, 200 dmg every
2 s) · 6 Battlewarder (350 dmg every 2 s; you can move) · 7 Dissonance Trap (rune: 600 dmg) ·
8 Brittle Guard (absorbs 50% of damage up to 2000) · 9 **Summoning Mastery, buffed**: all your pets
within 2000 grow 30% and gain +25% melee/spell damage, +15% absorption, +15 resists for 10 min; reuse
5 min (was 10) · 10 Crystal Titan (titan stomps for 400 every 3 s for 2 min).

**Perfecter**: 1 Purify Vision (group: cure nearsight and mez, heal 10%) · 2 Purging Wave (group: cure
poison, disease, DoTs) · 3 **Sphere of Rejuvenation, buffed**: heals 5% health every 4 s in combat too,
10% out of combat, 500 radius · 4 **Greatness, buffed** (passive): +30% concentration (was 20%) and
+10% healing · 5 **Font of Power, buffed**: 5% power and endurance every 4 s in combat, 10% out ·
6 Determination Field (mez/stun/snare 50% shorter inside) · 7 Leaping Health (next heal splashes 50%
to allies near the target) · 8 Restore the Soul (removes resurrection illness, heals 50%) ·
9 Dissonating Ward (100 spirit dmg + power drain every 4 s) · 10 Rampant Healing (next heal also heals
every ally within 1500).

**Sojourner**: 1 Unburdened Warrior (passive: carry 50% more) · 2 Unending Breath (group water
breathing) · 3 Swift Passage* (group +40% speed out of combat) · 4 Unmake* (cleanse all your snares,
DoTs, disease, nearsight, debuffs) · 5 Ancient Transmuter (2 min merchant: buys loot, sells arrows and
poisons) · 6 Gateway (to bind) · 7 Resistance of the Ancients (group +15% magic resists) · 8 Forceful
Zephyr (hurls an enemy 700 units, 5 s root) · 9 Phase Shift (all damage absorbed up to 5000 for 10 s)
· 10 Mass Gateway (whole group incl. companions to your bind).

**Spymaster**: 1 Pickpocket (passive: +50% coin from kills, including your pets' kills) · 2 Decoy (copy
of you with twice your health draws monsters fighting your group) · 3 Enduring Poison (passive: 50% of
poison hits keep the charge; the old code had a 0.15% slip) · 4 Sabotage* (-20% absorption, 20% slower
attacks) · 5 Tanglesnare (rune: 60% snare) · 6 Poisonspike (rune: poison DoT) · 7 Lookout (2 min aura:
reveals hidden enemies, allies +10% to hit) · 8 Wrecking Rune* (rune: 800 dmg, siege included) ·
9 Essence Flare (mez enemies within 500) · 10 Blanket of Camouflage (group players stealth).

**Warlord**: 1 Iron Will* (passive: +10% max health; replaces Siege Master) · 2 Bolstering Battlecry
(heal 20%, +10% power/endurance) · 3 Cowering Bellow (enemies flee) · 4 Resilient Will (allies 10%
harder to hit) · 5 Guided Strike (+10% melee and spell crit) · 6 Energizing Aura (half endurance
costs, +20% endurance) · 7 Cleansing Aura (cleanse DoT/poison/disease, heal 10%) · 8 Defending Martyr
(half your health heals others 25% + 500) · 9 Leadership (+10% damage, +10% to hit) · 10 Warguard
(+25% absorption, +15% magic resists).

The eight empty stock ML ability grants (SpecXAbility) are removed by the seed; the passives are now
spells in the ML line that can't be cast. Companions and autonomous bots still don't earn or use MLs.

## What you see in game

- Shouts and targeted abilities put an effect icon on everyone they buff or debuff, and tell you how
  many enemies, allies or pets they reached ("Banestrike affects 4 allies").
- Fonts, wards, crystals, the Lookout aura and Stormlord's Dazzling Array give everyone inside a
  chant-like effect icon while they stay inside; it fades about two seconds after the next pulse
  once they leave. Hostile fields with bonuses (Prescience Node, Stormlord's stat storms) show their
  debuff on enemies inside. Effects refresh rather than restart each pulse (`MasterLevelHold`).
- Passives you have unlocked on your current path show as permanent icons, restored on login and
  whenever your path or Master Level changes (`MasterLevelRules.SyncPassives`).
- Heals, power/endurance restores and cures report the amount or count in chat.
- Passive bonuses follow your current path only: leaving a path also removes its spell line, which
  previously kept the old path's passives (for example Greatness) working.

## Verification

Unit tests: `UT_MasterLevels` (XP conversion, storm and field bonuses held and released, Dazzling Array
allies, drains, Arcing Power filter, all 70 table entries, bonus bookkeeping, passives); full server suite
passes (3,099). Stormlord and the spell list were checked in game; the other seven paths were not yet.
