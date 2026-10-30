# Bots for the expansion, live and royal classes

Companion bots (`/spawn`, account companions) and autonomous gamebots can be any of the newer classes:
- **Albion:** Heretic, Mauler, Death Knight and Pendragon Sovereign.
- **Midgard:** Valkyrie, Warlock, Mauler and Storm Sovereign.
- **Hibernia:** Bainshee, Vampiir, Mauler and Tuatha Sovereign.

## When bots get them

A class is offered to bots only while its own server switch is on. These are the same switches its
players use:
- `enable_heretic_test`, `enable_death_knight_test` and `enable_valkyrie_test`
- `enable_warlock_test`, `enable_bainshee_test` and `enable_vampiir_test`
- `enable_mauler_test`, which covers all three Maulers
- `enable_stormforged`, `enable_pendragon` and `enable_tuatha`

All of them are on in the modern client test world (`artifacts/modern-client-test`). With every switch
off, as in Classic and AI-Test, the bot class pools and rolls are the same as before.
- **Server:** `AutonomousBotIdentityGenerator.ModernChoices` and `IsClassAvailable`.
- **Launcher roster:** `BotCharacterGenerator.ModernChoices`. The launcher reads each switch from the
  world's `ServerProperty` table.

Bots use only the classic races each class allows, not the modern races.

## Builds (`bots/specs`)

| Class | Builds (`/companion style`) |
|---|---|
| Heretic | Enhancement or Rejuvenation, with Flexible or Crush |
| Death Knight | Deathsight, Painworking or Death Servant (staff) |
| Valkyrie | Sword and shield, or spear |
| Warlock | Cursing, Hexing or Witchcraft (staff) |
| Bainshee | Ethereal Shriek, Phantasmal Wail or Spectral Guard (staff) |
| Vampiir | One build: Piercing, Vampiiric Embrace, Shadow Mastery, Dementia |
| Mauler | Mauler Staff, or two Fist Wraps |
| Sovereigns | One-hander and shield, or two-hander |

The Sovereigns learn their spells from their careers, so their plans train only weapons, Shields and
Parry. Stealth is left untrained so they fight in the open as tanks.

**Roles:**
- The Sovereigns count as tanks.
- The Valkyrie counts as a healing hybrid.
- Melee classes with siege skills can crew siege weapons.

**Weapons:**
- The Vampiir is a list caster that fights with a one-handed weapon, so it is never moved to a staff slot.
- Mauler weapons also match the realm-neutral (Realm 0) item rows, because Midgard and Hibernia have
  almost none of their own below level 37.

## Class spells (`bots/BotClassKitPolicy.cs`)

**Removed from a bot's spell list:**
- Warlock chambers and primers. The chamber handler casts its caster to `GamePlayer`. Without primers,
  bot Warlocks cast secondaries freely.
- Death Knight conjured weapons, ground spells, Revert Form, and every form except Decrepit.
- The Sovereign toggles, and the stealth-only opener.

**Kept up by bots:**
- The Mauler aura: the first one learned.
- Decrepit Form.
- The Sovereign chant and ward.
- The Storm Wolf and the Death Knight servant.
- The Sovereign group buffs: speed, absorption, and to-hit/damage.

**Used in a fight:**
- The Sovereign self heal, below half health.
- The harmful Sovereign abilities (strikes, storms, Hammerfall), on their reuse timers.

**Maulers:** `ModernMauler.IsPlayer` now accepts Mauler bots, so their stances, gifts and free-cost
utility work for bots the way they do for players.

## Fixes from the first bot tester run (October 25)

**Bugs in the new classes:**
- **Class abilities:** bots get their class's own abilities, as players do (`Specialization.GetAbilitiesForLiving`). Before
  this, they got only the abilities shared by every class. The expansion and royal careers grant weapon and armor
  abilities only to their own class. As a result, every Valkyrie, Mauler and Sovereign gamebot had no weapon and no
  armor, and stood still at its target.
- **Sovereign spells:** Sovereign bots take their career abilities. These are a list line, so hybrid bots had never
  read them.
- **Vampiir power:** Vampiir bots get a power pool from Strength, as Vampiir players do. Before this, their pool was 0.
  They also cast between swings, like Shamans.

**Bot AI:**
- **Healing:** a melee healer (Friar, Bard) waits for its own last swing to clear before a heal with a cast time, instead
  of having the cast refused.
- **Newly used spells:**
  - The Bonedancer commands its commander.
  - The Death Knight uses Regenerate Flesh below 70% health, and Gift of Power on group members below 40% power.
  - The Enchanter casts Enchanted Barrier on a group member under attack.
  - Bainshee point-blank spells (Shrill Aura) reach their radius.

**Spells and loot:**
- **Heretic spells:** Arawn's Singe and the Heretic damage-and-snare spell passed a percentage to `Util.Chance(double)`,
  which expects a fraction, so they were always resisted. This affected players too.
- **Loot:** Hibernian loot for the Tuatha Sovereign uses its own weapons and scale armor. The out-of-class loot pool
  (level 50 solo players) adds each newer class while its switch is on.

**Left as they are:**
- The Animist's bomber and Briar Burst need the main pet, which comes at a higher level.
- Cabalist, Enchanter and Spiritmaster damage shields stay off for bots on purpose.
- Warlock Fear Slave only affects enemy pets.

## Fixes from the third bot tester run (October 25)

- **Hybrid attack spells:** Reavers, Valkyries, Champions, Valewalkers and Maulers now open with their attack
  spells and cast them between swings, like Shamans and Vampiirs (`ShamanBotCombatPolicy.CastsBetweenSwings`).
  Before, "melee hybrids prefer melee within 550 units" meant they only swung once in reach. That included the
  Mauler endurance tap and power drain, which have a 3-second cast.
- **Two-handed starter weapons:** a spear build (Valkyrie, Storm Sovereign) or a Mauler Staff build now starts with
  its two-hander (`BotWeaponStats.PrimaryType`). Before, it got its one-handed fallback and never used its
  two-handed styles (Wild Swing, Thrusting Spear).

## Regression fixed October 25: instant attack spells

The 8:32 PM build (also in the 0.38-dev2 release) added the Bonedancer command case inside the shared list of instant
attack types in `BotBrain.CheckInstantOffensiveSpells`. Every type above it then fell through to the commander check,
so no other bot cast an instant attack:
- direct damage, damage over time and lifedrain
- stat debuffs, diseases and stuns

Reaver Soul Wench, Valkyrie Odin's Heel and Valewalker Nature's Nausea were all at 0 tries. The commander case is now
separate. The type list is `BotBrain.IsInstantAttackType`, covered by a test.

## Fixes from the fourth bot tester run (October 26)

- **Heretic focus damage (players too):** every `RampingDamageFocus` spell (Arawn's Singe, Blazing and Lava
  lines) dealt damage only once per cast. ECS pulses run `StartSpell`, which only rolled a resist and put a blank
  effect on the target. The ramping damage lived in the legacy `OnSpellPulse`, which never runs. Now each pulse
  deals its ramped damage behind one resist roll.
  - Overnight that showed up as 2,183 casts, 1,953 hits and 10,871 resisted pulses.
  - The resist chance itself was normal: 12.5% at matched levels.
- **Heretics in melee reach:** they now cast and channel their focus between swings
  (`ShamanBotCombatPolicy.CastsBetweenSwings`), with the focus first in the rotation. Before, "prefers melee in
  reach" held it 114,051 times.
- **"Always resisted" crowd control was a logging gap:** the tester counted success only from damage. Death Knight
  Wasting Disease, Cabalist pet stun, Bonedancer pet disarms and the style stun showed only their negations. The
  log now counts landings too (`landed`).
  - The resist chance for these is normal: 12.5% for the disease, 0% for the pet stun.
  - The style stun's "Immune" results come from the NPC stun immunity check. The next run's landing count will show
    whether that is normal.

## Fix from the fifth bot tester run (October 26, daytime)

- **Bots kept their level 1 spells (all classes, an old bug):** a bot's usable-skill lists are cached when first
  built, and the level-up and trainer paths reused the cache. Only the Bonedancer path rebuilt it. So a bot that
  leveled during a session never learned another spell until the server restarted and reloaded it.
  - In this run every class except the Bonedancer knew only level 1 spells, at levels 8 to 20.
  - Death Knights cast only Billowing Death and leveled slowest.
  - `SetBotSpells` now rebuilds both lists every time (`UT_BotSpellRefresh`).
- **Results from the same run:**
  - Arawn's Singe: 21,041 casts landed 210,428 pulses, about 10 per cast, with a 6% resist rate.
  - Heretic kills per bot went from 77 to 654 (median for all classes: 453).
  - Death Knight Wasting Disease lands 90% of the time.

## Not yet built for bots

- The Death Knight's servant commands. Its `PetSpell` wrappers are not issued the way the classic
  Necromancer's are.
- Warlock chamber combinations.
- The other Death Knight forms.
- The Bainshee wraith form. Bots skip the class's player `Init`.

**Testing:** automated tests cover the plans, gating, races, roles and spell filters
(`UT_BotModernClasses`). In-game bot testing of these classes is still to do.
