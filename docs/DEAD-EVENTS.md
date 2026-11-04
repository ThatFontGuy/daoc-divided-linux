# Dead events and unreachable spell handlers

Audit of `source/server/GameServer` at `feature/bot-ai-trips` 269c2a7a, checked against the modern test world.
A handler counts as dead only if a real cast or ability can reach it and its work never runs.

The idea of listing every subscribed event against its raises comes from Pactor/gaheris `docs/dead-events.md` (GPL-3).
Its findings were rechecked here and no code was copied. Unlike Gaheris, this tree does raise `AttackedByEnemy`
(`GameLiving.OnAttackedByEnemy`), so listeners on that event are live.

## Events with subscribers and no working raise

| Event | Subscribers | Status |
|---|---|---|
| `GameLivingEvent.AttackFinished` | 22 | **Fixed.** The only raise forwarded an event the pet never received. Now raised once per resolved swing. |
| `DatabaseEvent.CharacterSelected` | 1 | **Fixed.** Now raised from `GameClient.LoadPlayer`, so `StartupLocations` repairs a character at 0,0,0 or with no bind. |
| `GameLivingEvent.CastStarting` | 3 | Left. Raised only by `NecromancerPetBrain`. Its listeners are Focus Shell and Master Level spells with no rows in the modern world, and Heretic code that nothing calls. |
| `GameLivingEvent.Moving` | 7 | Left, see Bainshee below. |

`GamePlayerEvent.AcceptQuest` and `DeclineQuest` look unraised to a text search, but `DialogResponseHandler` raises them through a ternary.

### Where `AttackFinished` is raised

It is raised at the end of `WeaponAction.MakeAttack`, not in `OnAttackEnemy`. `OnAttackEnemy` runs before the target's
`OnAttackedByEnemy`, so a listener there would read damage before ablatives and Modern RR5 reductions.

Misses, blocks, evades, parries and fumbles raise it too, because Testudo and Blade Barrier break on any swing.
Listeners filter on the result. Swings that never resolved (out of range, dead target, not visible) do not raise it.
Each hand and each Savage swing is its own raise. Reflex attacks and siege shots are not weapon swings and do not raise it.

### What the fix brings back

| Listener | Who has it | Before the fix |
|---|---|---|
| `StormSovereignEffect` keys 15 and 17 | Stormforged | Never fired |
| `BloodDrinkingEffect` | Shadowblade RR5 | Never healed |
| `TestudoEffect` | Warrior RR5 | Never broke when attacking |
| `BladeBarrierEffect` | Blademaster RR5 | Never broke when attacking |
| `SelectiveBlindnessEffect` | Mentalist RR5 | Never broke when the user attacked with a weapon (casting already broke it) |
| `AbstractQuest.InterruptAction` | Quest searches | Attacking did not interrupt a search |

Blade Barrier also never removed its handlers when it stopped. That is fixed, since they would now keep firing.

## Handlers whose work sits only in `OnEffectStart`

Only `GameSpellEffect` calls `OnEffectStart` and `OnEffectExpires`. A normal cast creates an ECS effect, so these spells
gave an icon and no effect. `LegacySpellECSEffect` calls the handler's own methods from `OnStartEffect` and `OnStopEffect`.

| Handler | Spells | Status |
|---|---|---|
| `WaterBreathingSpellHandler` | 17 | **Fixed** |
| `DisarmSpellHandler` | 6 | **Fixed** |
| `VampiirMeleeResistance` | 5 | **Fixed** |
| `VampiirMagicResistance` | 5 | **Fixed**, and no longer needs the owner to be a `GamePlayer` |
| `VampiirStealthDetection` | 3 | **Fixed**. It adds to `Skill_Stealth`, as the handler always did. |
| `CCResistSpellHandler` | 3 | **Fixed** |
| `HereticPiercingMagic` | 5 | **Fixed** differently. The effect was present but nothing read it, so it now adds to hit chance like `PiercingMagic`. |
| `VampiirArmorDebuff` | 5 | Left dead. It edits the target's real item fields, so a save or crash during the debuff could damage saved gear. Needs a rewrite. |
| `VampiirSkillBonusDeBuff` | 4 | Left dead. It wipes every spec level to zero, then sets each skill buff to 0 on expiry, which erases other buffs. Needs a rewrite. |
| `VampiirEffectivenessDeBuff` | 6 | Left dead. Pulsing, and two casters would corrupt the saved value it restores. Needs a rewrite. |
| `ConversionSpellHandler` | 1 | Left dead. The item spell has `Damage = 0`, so it would convert nothing and spam messages. Needs a data decision. |
| `SummonMonster` | 1 | Left. No spell line grants it. |

## Bainshee auras (open)

`BainsheePulseDmgSpellHandler` subscribes to `Moving` so the 8 Aura spells end when the caster moves. Nothing raises `Moving`,
and the handler's `CancelPulsingSpell` is itself stubbed out, so an aura keeps pulsing on the move. The spells are not
focus spells, and no source in this repo says an aura should break on movement, so this was left alone.

## Ruled out

- **Replaced by a `Modern*` ability:** Badge of Valor, Fury of Nature, Mark of Prey, Speed of Sound, Sputin's Legacy, Nature's Womb, Negative Maelstrom, Ichor, Whirling Staff.
- **Replaced by a direct call in `OnAttackEnemy`:** Dirty Tricks, Triple Wield, offensive and defensive procs.
- **No grant or no rows in the modern world:** Shield Trip, Entwining Snakes, Desperate Bowman, Focus Shell, `ValkyrieProc`, the Convoker and Spymaster spells, Illusion Blade, and `SummonElemental`.
- **Cure spells:** `RemoveSpellEffectHandler` is flagged by a search for `OnEffectPulse`, but no cure pulses and they run from `OnDirectEffect`.
- **Warlock primers:** `PrimerSpellHandler` is unused here. The live type is `WarlockPrimerHandler`.

## Notes on the method

- Spell counts are rows in the modern test world, read-only. They would differ in another world.
- Automated tests cover the raise, the bridge and Blade Barrier. None of this has been checked in game.
