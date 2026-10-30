# Bot tester log

Every bot plays as a tester:
- companion bots
- `/spawn` helpers
- account companions
- autonomous gamebots

While they play, the server records what each class's spells and styles actually do. It also records
what goes wrong. The log never changes a bot's decisions, and a logging failure never reaches the game.
The code is in `bots/BotTesterLog.cs`.

## Where to look

The files are in the server folder under `logs/bot-tester/`. In the modern test install that is
`artifacts/modern-client-test/runtime/server/logs/bot-tester/`.

| File | What it is |
|---|---|
| `REPORT.txt` | Start here: findings sorted by severity, then one line per class |
| `summary-latest.json` | Every statistic, for each class, spell, pet spell and style |
| `events-YYYYMMDD.jsonl` | Individual events, one JSON object per line |

**When the report is written:**
- every 10 minutes (`bot_tester_report_minutes`)
- when the server stops
- when you type `/bottester`

**`/bottester` commands:**
- `/bottester` writes the report now and shows the top findings in chat.
- `/bottester verbose on` also logs every cast, spell hit and style until the server restarts.
- `/bottester reset` clears the statistics for a fresh test run. It writes the report first.

## What is recorded

- **Spells:**
  - Tries, casts, refusals and interrupts.
  - Resists, immunities and other negations.
  - Landings: every target the spell got past its resist checks on. This counts stuns, disarms,
    debuffs and procs, which never deal damage, so they don't look always resisted.
  - Hits, damage and zero-damage hits.
  - A refused cast keeps the message the game sent, for example "You must wait 5 seconds to cast again"
    or "Your target is not in view".
- **Pet spells:** recorded under their owner's class.
- **Styles:**
  - Executions and their damage.
  - Failed executions, with the requirement that failed (position, opener style, previous attack result).
- **Exceptions:**
  - Any game service error involving a bot or its pet. That error also removes the bot from the world.
  - Logged with the spell it was casting and its last 8 actions.
- **Deaths:**
  - Who killed the bot.
  - Its power and endurance, its group size, its activity and pet.
  - Its last 8 actions.
- **Coverage:** the spells and styles each class knows, to find the ones its bots never use.

## Why a spell was skipped

When the bot AI passes over a known attack spell, the check that stopped it is counted, for example:
- "instant: on cooldown", "instant: target out of range" or "instant: spell type not used by the bot attack AI"
- "cast: melee hybrid prefers melee in reach" or "cast: chosen, but the bot is being hit"

These counts are kept only in memory, with no event per skip. The report adds the top three reasons to each "never
tried" finding. "Never considered" means the AI never looked at the spell at all. `summary-latest.json` has
`skipped` and `skipReasons` for every spell.

## Findings

| Severity | Meaning |
|---|---|
| critical | An exception (a code bug) |
| high | A spell that was never cast successfully, a style whose requirements always fail, or a damage spell that always deals 0 damage |
| medium | A spell that fails more than half the time, or a spell resisted or negated on 90% of casts |
| low | A spell interrupted more often than it is cast |
| info | A spell or style known but never tried; the bot AI may not use it |

A finding is a lead, not a verdict. A spell refused for "not in view" points at bot positioning. A
damage spell that always deals 0 points at the spell itself.

## Volume

- **Events:** problem events only, with each repeat (same bot, skill and reason) logged at most once
  every 5 minutes. The counts in the report still include every occurrence.
- **Daily cap:** events stop at 256 MB a day. Reports continue.
- **Turning it off:** set `bot_tester / bot_tester_log` to False.
