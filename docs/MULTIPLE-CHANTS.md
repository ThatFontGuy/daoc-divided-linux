# Multiple chants (live chant rules)

October 23, 2026. Owner request: chants and songs work as on live, so Bards, Paladins, Skalds and others can keep all of their chants running at once.

## Behavior

Server setting `spells / allow_multiple_chants`, default **True**.

- **True (live rules):**
  - A caster can keep any number of different chants and songs running. Chants with no concentration cost don't count toward the concentration-effect limit.
  - Starting a chant ends only that caster's running chant of the same spell type or effect group, for example a higher-rank chant of the same type.
  - Recasting a running chant still switches it off, as before.
  - Only one focus spell runs at a time, and casting another spell still ends a focus spell (`CancelFocusSpells`, unchanged).
- **Pulse caps (live 1.121 and 1.123):** under live rules, a player or bot keeps at most `spells / max_pulses` (default 8) pulsing spells running, and a Skald at most `spells / skald_max_pulses` (default 12). Focus spells and a chant that would replace a running one don't count. At the cap, a new chant fails at cast start with "You can't maintain any more chants." and costs nothing. NPCs aren't capped.
- **False:** the previous 1.65 rule. Every new pulse spell ends the caster's other pulse spells.

Songs still need an instrument in hand, and switching weapons still stops songs that need one. Since patch 1.97 any instrument plays any song, so a Bard can start every song without switching instruments.

## Code

- `EffectListComponent.PulsesConflict` decides which running pulses a new one ends. `CancelIncompatiblePulseEffects` uses it.
- `EffectListComponent.CanStartPulse` and `MaxPulses` apply the cap. `SpellHandler.CheckPulseCap` checks it at cast start.
- `CastingComponent`: a bot re-requesting a chant that is already running does nothing, instead of switching it off. Players keep the recast-to-cancel toggle.
- Bots, under live rules:
  - Performer and tank-chant selectors skip a chant already running at that rank or higher (`BotSongTwistPolicy.KeepsRunning`), so bots start each useful chant once instead of twisting between them. At the pulse cap they skip every new chant instead of retrying.
  - Bots no longer end the previous song when they switch instruments.
  - Entering combat still ends a performer bot's songs, as before (`StopTwistedSong`).
  - Under 1.65 rules the bot rotation is unchanged.

## Tests

`UT_MultipleChants` covers the conflict rule and the bot skip rule. `UT_BotMobileSongs` now checks the Warden case under both rules. Full server suite after Codex finished its Valkyrie work: 3,168 passed, 0 failed.

## Deployment

October 23, 2026: deployed to the modern test server only (`artifacts/modern-client-test/runtime/server`, all three folders). The previous DLLs, Codex's 17:54 build, are in `artifacts/modern-client-test/backups/gameserver-pre-multiple-chants-20261023-180917/`. The setting isn't stored in that database yet, so the default (True) applies. Classic and Stormforged installs are unchanged.

Not yet checked in game. Effects to watch for: buff-bar crowding with many chants, the group window, and how much bot performers spend on songs.

### Live power research (October 23, 2026)

- **Per-pulse cost:** the official Class Library lists cost 0 for nearly every song and chant. Per-pulse costs appear only on a few Paladin chants (endurance, advanced resist, celerity). Those pages are undated and partly older than 1.121, and no live patch removing chant power costs was found. Our data already matches this pattern.
- **New pulses:** patch 1.121 and 1.123 pulses list "10% power", and the notes don't say whether that is per cast or per pulse.
- **Caps:** 1.97 allowed two songs or chants at once, 1.121 raised that to 8 pulses for every class, and 1.123 raised the Skald to 12.

**Pulse caps deployed** to the modern test server the same day (previous DLLs in `artifacts/modern-client-test/backups/gameserver-pre-pulse-caps-20261023-183238/`). Full suite: 3,171 passed. Not yet checked in game.
