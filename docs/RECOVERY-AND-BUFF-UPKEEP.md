# Out-of-combat recovery and buff upkeep

Players have configurable regeneration floors outside combat. Default approximate standing refill times are 60 seconds for health, 30 for power and 20 for endurance, starting once the character is out of combat. Sitting doubles the floor's rate. Tick timing, rounding and native regeneration bonuses affect actual times; this is not an instant refill or a guaranteed stopwatch duration.

Combat, attacks, casting, crowd control and fighting controlled pets block the new recovery bonus. Endurance gains no new bonus while moving. Disease and bleeding still suppress health regeneration, and stronger native regeneration remains stronger. Ordinary monsters are unchanged. Bots retain their existing faster recovery system and its combat/movement safeguards; the new player floor is not applied to their different timer cadence. Native Vampiir/Mauler power decay is unchanged.

Server properties:

| Property | Default |
|---|---:|
| `faster_out_of_combat_recovery` | True |
| `rest_health_seconds` | 60 |
| `rest_power_seconds` | 30 |
| `rest_endurance_seconds` | 20 |
| `rest_sitting_multiplier` | 2 |
| `buff_upkeep_refresh_seconds` | 15 |

Set a resource's seconds to zero to disable its extra floor, or turn off the recovery switch to restore native regeneration. Recovery settings are in category `recovery`; buff refresh is in `bots`.

Gamebot maintenance can refresh its own exact-rank, non-pulsing timed class buffs shortly before expiration. Eligible spells last at least a minute, cost no concentration, and must still pass normal spell-cost/cooldown/concentration/follow checks. The early-refresh window is at most a quarter of the buff's original duration. Another caster's buff, a different rank, short buffs, concentration buffs and pulses are left to existing behavior. No early refresh is requested during combat, for a target in combat, or while a matching cast is active/queued. Existing missing-buff and pet maintenance remains in place.

Automated coverage: `UT_RecoveryAndBuffUpkeep`, plus the full server regression suite. Actual party rebuff timing and recovery while playing still require an in-game check. This source change does not update either playable installation automatically.
