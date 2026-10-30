# Offline DAoC 0.33 "Claude Takeover"

0.33 continues from 0.32b. It includes everything from the "new class test" builds that followed
0.32b, and a round of work by Claude on bots, pets, spell effects, art and packaging.

It comes in two editions, from one download. They are the same game, and only the custom class
differs:
- **0.33b** includes the Hibernian **Sluaghbinder** class, for players and bots.
- **0.33** has the original Classic + SI class list only. The Hibernian Mauler slot is disabled,
  as in 0.32.

## Downloading and starting

- **One full download.** 0.33 no longer rebuilds on top of v0.3 and v0.31 downloads. The helper
  fetches about 5 GB in parts, checks every part and unpacks one ready-to-play folder.
- **Your own account.** No account is included. The launcher makes a private login for each
  install, and the server creates the account the first time you click ENTER REALM.
- **Your own world.** No characters, bots, houses or auction history are included. Bots are
  created from the launcher buttons.
- **Default settings:**
  - bot goals at their defaults
  - GM off
  - 1× XP
  - each install keeps its own client settings profile, so it never uses another copy's settings
- **Bundled .NET runtime.** Nothing needs installing except the Windows .NET Framework 3.5
  feature.
- **Progress transfer tool.** It moves an account, characters, items, money, houses and bots from
  any earlier version. See [TRANSFER-PROGRESS.md](TRANSFER-PROGRESS.md).

## Bots

- **Faster world with thousands of bots.** Database reads no longer wait behind bot saves. Bot
  AI stops repeating failed route searches, and heavy scans moved off the main game loop. This
  cut the stutter, NPC flicker and input lag seen with 6,000 bots.
- **Stuck pulls are handled for every class.** If a pull doesn't connect, the bot moves in
  closer and tries again, then picks another target. A stuck cast is cleared automatically.
- **Ranged bots close in properly.** A resting caster or archer now walks up to a target that's
  too far away, or wandering, instead of standing still.
- **Archers that stall** at close range switch to melee for a moment instead of freezing.
- **No self-mez.** Bots no longer mesmerize the monster they're trying to kill.
- **Savages:**
  - They can use claws in their main hand, which was why many level 1 Savages never attacked.
  - They save their health-costing buffs until they reach the target.
- **Level 0 creatures count as targets.** New level 1 bots use real starter camps near home,
  each checked for a walkable route.
- **The stuck-bot watchdog** counts earned XP as progress, so a caster killing from one spot
  isn't sent home by mistake.
- **Groups:**
  - They still prefer 8 bots, but can now start with 5–7 when a full party can't be found.
  - Smaller groups pick somewhat easier targets.
  - Bots waiting for a group grind outdoors instead of standing idle.
- **Darkness Falls:** solo bots enter at level 25+ and only take targets that con blue or easier.
  A group already inside picks its next camp inside.
- **Selling:** bots with a nearly full bag sell at their next natural break, never mid-grind.
- **Routing:** a camp that several bots can't route to is benched for a while, instead of drawing
  more bots into the same wall.

## Sluaghbinder (0.33b)

- **New looks for the pets:**
  - The sturdy zombie, zombie magician and zombie priest have their own private models and skins.
  - The walking dead has a subtle purple-grey recolour.
  - The zombie guardian has repainted rusted plate with a detailed belt.
  - The Dullahan's armor is symmetric and its seam is fixed.
- **Zombie magician:**
  - Attacks with a black-purple void blast.
  - Has its own casting gestures.
  - Its melee animations are fixed.
  - Its robe is lower-res to match the game, with muted markings.
  - Its shoulder spikes are folded into the robe.
- **Zombie priest:**
  - Heals party members and pets properly: a heal over time below 75% health, and a direct heal
    below 50%.
  - It breaks off to heal, and player-owned priests get the same healing AI.
- **Pet health rebalance.** The Dullahan and guardian are less tanky, and the magician and priest
  are squishier. Damage is unchanged.
- **Blood Shield.** All Cairn armor buffs (self, pet, and the guardian's and Dullahan's own)
  show a black and blood-red shield instead of the holy halo.
- **Summons:**
  - They cast in 10 seconds, down from 20.
  - They show green hand glows.
- **Tooltips.** Every Sluaghbinder buff shows its own tooltip on the effect bar.
- **The zombie guardian's mace and tower shield** are unique rusted models.

## Everyone

- **Necromancer:** the level 20 Necroservant carries its own blackened bone hammer and
  rotten-wood grave shield.
- **Helmets:** faces now show under every variant of the Hibernian "Helm 3" family (15 helmet
  models, such as the amber cailiocht helm). Item stats are unchanged.

## Limits and honest notes

- **Darkness Falls is still beta.**
  - Raid AI isn't implemented.
  - Legion, the hardest level 70+ encounters, unreachable flying targets and unverified routes are
    left out of bot goals.
- **Bot changes need long live runs.** They were tested with the full automated test suite and
  measured in multi-hour bot runs. Some, like the smaller groups and the archer fallback, still
  need longer live observation.
- **Startup data warnings.** The server logs a few warnings at startup that come from the stock
  world data (for example missing poison spells). They were there before 0.33 and don't affect
  play.
- **One server at a time.** Only one local server can run at once, because every copy uses port
  10300.

## For developers

- **The edition switch** is the server setting `classes / enable_sluaghbinder`: on for 0.33b and
  by default, off in the 0.33 database.
- **Source:** see [DEVELOPMENT.md](DEVELOPMENT.md) and [LLM-QUICKSTART.md](LLM-QUICKSTART.md).
- **Art tools:** the private art pipeline (pets, weapons, spell effects) is in `tools/pet-art`,
  with an install and rollback script for every step.
