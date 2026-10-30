# Work so far (October 2026, 0.38 development)

A guide to what this round of work adds on top of the 0.37 release. Almost all of it lives in the **modern client
test installation** (`artifacts/modern-client-test`, the original retail 1.130 client), not in the Classic or
Stormforged releases. Each area links its own document for the details.

**Status:** server built and started by the owner, with the full automated test suite passing (3,503 C# tests, plus
the class tools' Python tests). In-game testing of the newest class work is still to do; see the end of this page.

## Modern client test installation

- **The 1.130 client:** the original retail client now connects ([MODERN-CLIENT-TEST.md](MODERN-CLIENT-TEST.md)). It
  is bundled and patched for the custom classes ([MODERN-CUSTOM-CLIENT.md](MODERN-CUSTOM-CLIENT.md)).
- **Races:** all 21 realm races are available, Minotaurs and Half-Ogre included ([MODERN-RACES.md](MODERN-RACES.md)).
- **Native class slots:** client class slots for the expansion and royal classes (`source/tools/classslots`).
- **Trainers:**
  - Expansion class trainers are imported from Eve of Darkness ([EXPANSION-TRAINERS.md](EXPANSION-TRAINERS.md)).
  - Every class trainer wears its class's armor ([TRAINER-ARMOR.md](TRAINER-ARMOR.md)).

## Classes

### Every class toward live 1.130a

The goal is each class's spells, values and abilities as on live 1.130a. By name, 99% of live's class spells are in
the modern test world. The classic shade Necromancer is kept on purpose.

**How it's built.** Python migrations in `source/tools`, installed together by
`install_hybrid_lines.py`. It previews by default; `--apply` writes. It backs up, verifies the world, refuses to run
while a server is up, and supports `--rollback`. The steps run in this order:

| Step | What it adds |
|---|---|
| `remove_sluaghbinder.py` | drops the retired class's world rows |
| `hybrid_lines.py` | the hybrid classes' live lines and class abilities |
| `class_lines.py` | the other classes' live spells |
| `archery.py` | live archery |
| `proc_lines.py` | class proc buffs |
| `linked_lines.py` | totems, commands and other parent/child spells |
| `envenom_lines.py` | the assassins' live poisons |
| `round3_lines.py` | the remaining classes, the level 50 nukes, the seventh pass and the live pets |
| `spell_drift.py` | live values for stock spells |
| `audit_corrections.py` | corrections from a full audit |
| `dot_timing.py` | live duration and tick for damage-over-time spells |
| `live_spell_art.py` | the client's own spell art |

**Units** (live value → this server's table):
- Direct damage: × 0.0992.
- Lifedrains, damage shields and damage adds: ÷ 10.
- Cast time: live timer ÷ 1000 + 2 s (a timer of 1 is instant).
- A snare's Value: 100 − the speed left.
- Duration and recast: seconds. Frequency: tenths of a second.

**New mechanics** (server code, `spells/LiveClassEffectHandlers.cs`, `LiveGapHandlers.cs`, `LiveRound7Handlers.cs`):
- Wizard Ice Grip, Flame Cocoon and Warrior Battle Control (grapples).
- Assassin Overshadow (hide an ally).
- Thane Chain Lightning.
- Mentalist Speedwarp (a ward that negates speed boosts).
- Druid Heart of Nature.
- Enchanter Enchantments of Stone, Fire, Truth and Zeal.
- Siegebreaker, Reaver Malefic Horror and Shaman Blight Surge.
- Earlier passes: totems, damage reduction, Helping Hand, Track, damage-type auras and others.

**The live pets:**
- **Animist:** bombers, spore and heal turrets, Shroom of Life and the three level 40 main pets.
- **Spiritmaster:** the five class spirits and Gates of Valhalla.
- **Druid:** Grove Guardian, Grove Protector and Nature Sage.
- **Enchanter:** Underhill Stalker.

Each pet uses a copy of the closest stock template under the live name. Their per-pet spell kits are not yet live's.

**Not yet built:**
- Cabalist Simulacrum Soul, Fortitude and Resilience (no source for what they do).
- The Valkyrie's Valkyrie's Supremacy and Odin's Hope.
- The Mauler Farseer realm gift damage for ranks 1-4, and Siegebreaker's bonus for controlled siege weapons (no
  figures).

**Simplified:**
- Chain Lightning's jump radius and falloff, and Zeal's shared group heal: live gives no figures.
- Heart of Nature's root grants no immunity afterwards.
- Enchantment of Ice doesn't change the melee damage type.

**One spellbook line per specialization:** the migrations put spells whose level clashed with a stock spell into
extra lines "<line> (Live)" and "<line> (1.130)" (the client casts a list spell by line index + level, first match
winning). The server now shows each stock line and its extras to the client as one line (`SpellLineMerge`, through
`StormforgedRules.ClientSpellLines`): stock spells keep their level, each extra spell gets a free client level (its own,
else the nearest free one below, else above), and casting and delves map back to the real line. The world database is
unchanged and bots still use the real lines. 44 groups merge; Spirit Enhancement, Witchcraft, Valewalker Arb Path Spec,
Creeping Path Spec and Calefaction hold more spells than levels 1-50, so 35 spells show client levels 51-68.
Hotbar buttons for spells in the old extra lines, and for lines after them, need placing again.

**Local-only data:** six data files the class migrations read (`archery_data.py`, `class_lines_data.py`,
`class_lines_data_v2.py`, `dot_timing_data.py`, `spell_drift_data.py`, `audit_corrections_data.py`) are derived from
daoc.gg's data. They are kept out of the repository for now, and so is the class research behind them. A clone can't
rerun the class migrations; the playable build carries their results in its world database.

### New and expansion classes (modern test, first playable versions)

- **Expansion classes:**
  - Death Knight, the live Necromancer, beside the classic one ([DEATH-KNIGHT-MODERN-TEST.md](DEATH-KNIGHT-MODERN-TEST.md)).
  - Bainshee, Vampiir and Heretic ([EXPANSION-CLASSES-MODERN-TEST.md](EXPANSION-CLASSES-MODERN-TEST.md)).
  - Valkyrie ([VALKYRIE-MODERN-TEST.md](VALKYRIE-MODERN-TEST.md), [VALKYRIE-PROGRESSION.md](VALKYRIE-PROGRESSION.md)).
  - Warlock ([WARLOCK-MODERN-TEST.md](WARLOCK-MODERN-TEST.md)).
  - Mauler in all three realms ([MAULER-MODERN-TEST.md](MAULER-MODERN-TEST.md)).
- **Royal classes:** Storm Sovereign (Midgard, replacing Stormforged in the modern test), Pendragon Sovereign (Albion)
  and Tuatha Sovereign (Hibernia) ([STORM-SOVEREIGN.md](STORM-SOVEREIGN.md), [PENDRAGON-SOVEREIGN.md](PENDRAGON-SOVEREIGN.md),
  [TUATHA-SOVEREIGN.md](TUATHA-SOVEREIGN.md)). The older Stormforged design stays documented in
  [STORMFORGED.md](STORMFORGED.md).
- **The Sluaghbinder is retired:** its server code is removed and `remove_sluaghbinder.py` drops its world rows.

## Progression

- **Master Levels:** all eight paths, earned from level 50 experience ([MASTER-LEVELS.md](MASTER-LEVELS.md)).
- **Champion Levels:** 1-15, earned from realm points at level 50 ([CHAMPION-LEVELS.md](CHAMPION-LEVELS.md)).
- **Live realm abilities:** the RR5 abilities, and Tireless free at level one ([LIVE-RA-MODERNIZATION.md](LIVE-RA-MODERNIZATION.md)).

## Combat and rules

- **Chants:** they stack as on live ([MULTIPLE-CHANTS.md](MULTIPLE-CHANTS.md)).
- **Spell pushback:** capped damage pushback for spell casting ([SPELL-CAST-PUSHBACK.md](SPELL-CAST-PUSHBACK.md)).
- **Recovery:** out-of-combat recovery floors for players ([RECOVERY-AND-BUFF-UPKEEP.md](RECOVERY-AND-BUFF-UPKEEP.md)).

## Bots and companions

- **Buffs:** the order bots and companions hand out buffs in ([BUFF_RULES.md](BUFF_RULES.md)).
- **Newer classes:** bots and companions can be every expansion, live and royal class while its switch is on ([BOT-MODERN-CLASSES.md](BOT-MODERN-CLASSES.md)).
- **Bot tester log:** every bot records refused and failed spells and styles, resists, exceptions and deaths, with a report in `logs/bot-tester` and the `/bottester` command ([BOT-TESTER-LOG.md](BOT-TESTER-LOG.md)).
- **Account companions:** specialization lines trained by hand and a free respec from the training page.
- **Gamebots:** AI fixes from the soak runs, such as healer bots finishing a spell they're already casting, and
  pet-combat and loot-flow fixes.

## Launcher

The launcher has a modern client profile: client and helper paths come from the profile and are hash-checked before
launch.

## What still needs in-game testing

Automated tests and the server start pass. In-game checks are still to do for:
- **The newest class work:** the grapples, Overshadow, Speedwarp, the enchantments, Chain Lightning, Blight Surge, the
  charms and the live pets.
- **Earlier value changes:** Cavern Unity 24 → 12, the Bonedancer skeleton snares 5/10/15%, Shroud of Doubt 50 → 20,
  Arthritic Curse 3 → 6, and the live DoT timing.
