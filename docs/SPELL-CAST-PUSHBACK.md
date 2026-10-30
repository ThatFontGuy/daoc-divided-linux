# Damage pushback for spell casting

Players, temporary companions, persistent companions and autonomous GameBots now use capped pushback for ordinary damaging hits. Each successful hit adds 500 ms to an active spell, capped at 1,000 ms per cast. Ordinary damage no longer creates the recent-hit casting lockout, including while idle, so bot healing/offensive casting gates remain open. The AI's recent-attacker melee fallback also respects this policy.

Misses, blocks, fully absorbed hits, resisted damaging spells and DoT ticks do not add pushback. Instant spells, Quickcast, uninterruptible spells, Mastery of Concentration and Facilitate Painworking retain protection. Movement, crowd control, taunts and other explicit interrupt paths retain their existing rules. The caster's own melee swing lockout remains. Active focus channels and archery casts keep their legacy damage-interruption path; ordinary monster/pet casters are unchanged.

Server properties (category `spells`):

| Property | Default | Meaning |
|---|---:|---|
| `spell_damage_pushback` | True | Enable the player/GameBot policy; False restores legacy damage interruption |
| `spell_damage_pushback_per_hit` | 500 | Milliseconds added per hit |
| `spell_damage_pushback_cap` | 1000 | Maximum accumulated milliseconds per cast |

The server sends the existing spell-cast animation packet with the updated remaining time, without resetting its cast deadline. The original client's visual response needs an in-game check; no binary client patch is included.

Regression coverage is in `UT_SpellCastPushback`: actual cast deadlines, per-cast cap/reset, concurrent hits, player and GameBot timer flags, AI melee fallback, Quickcast, instant/uninterruptible protection, and setting boundaries. No playable installation has been updated as part of this source change.
