# Tuatha Sovereign

Hibernia's royal solo/co-op class, a king or queen of the Tuatha Dé Danann. It uses the same combat
balance table as the Storm Sovereign (Midgard) and the Pendragon Sovereign (Albion).

- **Class and slot:** server class 67. In the modern test client it takes the creation entry the
  Sluaghbinder had in Hibernia: the native slot patch (`source/tools/classslots`) registers class 67
  there instead of 63.
- **The Sluaghbinder is kept:** it stays class 63 for the 0.37b edition and keeps its client name.
  It is already off in the modern test world (`enable_sluaghbinder=False`).
- **Requirements:** the Tuatha needs the patched client, `classes / native_custom_class_slots=True`
  and `classes / enable_tuatha=True`. Unpatched and classic clients cannot create it.

All seven Hibernian races are eligible: Celt, Firbolg, Elf, Lurikeen, Sylvan, Shar and Graoch.

## Skills and gear

- **No specialization spending:** Blades, Blunt, Piercing, Large Weapons, Celtic Spear, Shields,
  Parry and Stealth train with character level.
- **Styles:** each weapon line has seven private styles (42 in all), with the same chains, reactions,
  positional attacks, stuns and stealth opener as the other Sovereigns.
- **Armor and starter kit:** scale armor and large shields are available from creation. New
  characters start with a cruanach scale set, a short sword and an elm tower shield.
- **Trainer:** the Brehon of Tara stands beside Riofach, the Hero Trainer in Tir na Nog.

## Shared power baseline

Identical to [PENDRAGON-SOVEREIGN.md](PENDRAGON-SOVEREIGN.md#shared-power-baseline):

| Feature | Value |
|---|---|
| Innate bonuses at 50 | +115 to all eight stats, +575 flat HP, +115 flat power |
| Melee sustain | 30% of damage dealt returned as health, 10% each as power and endurance |
| Spell sustain | 50% returned as health, 20% each as power and endurance |
| Companion | owner level, 4x pet health, 2x damage, 30% life steal |
| Transformation | 60 seconds, 180-second reuse |

The realm differences are spirit damage (instead of Midgard's energy/cold/body or Albion's heat)
and the Hibernian weapons.

## Royal abilities

The seed copies the installed Midgard abilities' damage, power costs, unlock levels, cast times,
ranges, radii, durations and timers into separate Hibernian content. Every spell deals spirit damage.

| Ability | Midgard counterpart |
|---|---|
| Spirit Lance | Lightning Spear |
| Grasp of the Bramble | Winter's Grasp |
| Tara's Judgement | Royal Thunder |
| Ring of the Sidhe | Chain of the Crown |
| Otherworld Burst | Stormbreak |
| Fairy Ring | Eye of the Storm |
| Court of the Sidhe | Royal Presence |
| Decree: Advance / Stand Fast / Strike True | same |
| Sovereign's Renewal, Rally to the Crown | same |
| Will of the Tuatha | Will of the Sovereign |
| Armor of the Crown | same |
| Glamour Ward | Runic Ward |
| Wildwood Armament | Runic Armament |
| Sovereign's Challenge | same |
| Glamoured Ambush | Hunter's Mark |
| Thorn Reversal | Runic Reversal |
| Faerie Drake | Storm Wolf |
| Otherworld Ascendant | Storm Crown |
| Step Between Worlds | Sovereign's Hammerfall |
| Veil of the Sidhe | Veil of Winter |

- **Companion:** the Faerie Drake uses stock model 576. It grows during Otherworld Ascendant and
  keeps its model.
- **Transformation:** the player becomes a Sidhe lord (stock sidhe tiarna, model 339).
- **Realm abilities:** Royal Fortitude, Storm Mastery and Crown's Resolve use separate `Tuatha_*`
  keys. Wrath of the Tuatha is granted free at RR5.

## Vampiir hover (off for now)

The hover is switched off (`TUATHA_HOVER = False` in `patch_class_slots.py`), so the Tuatha stands
like any other class. A hover-only patch is written and checked in emulation, and can be switched
back on later. How it works in the 1.130 client:
- **One flag carries all of it:** the character record's "is Vampiir" byte (+0x15D) is set from
  class == 58 at character select (0x402A66) and on world entry (0x417F9B). It becomes the world
  object's flag +0x19C4 (0x433814).
- **Hover readers test for nonzero:** the animation set (0x42E44D), animation picks (0x42581E,
  0x425970, 0x42CE1B, 0x42FDA1) and the ground-contact effects (0x430131 and the code after it).
- **Skin and model readers:** the body texture and tint (0x417608, 0x4176CF, 0x417702), the
  `Head%d` model (0x47361F), the model load (0x45013E) and the getter 0x5ADFEB.

With the switch on, the native slot patch writes 2 instead of 1 for class 67, and makes those skin and model readers
require exactly 1. `verify_stub_emulation.py` checks the writers (58 gives 1, 67 gives 2, any other
class gives 0) and that each skin reader gives 0, 1, 0 for flag values 0, 1, 2.

Limits:
- **Other players' view:** the server does not send the player-create "Vamp fly" bit (0x40) for the
  Tuatha, because that sets the full Vampiir flag (value 1) on other clients. Other players see it
  standing normally.
- **Readers identified statically:** if any Vampiir look or behaviour remains in-game, it comes from
  a reader not yet split.
- **Earlier build:** a build that set the full flag for class 67 showed the pale skin, a missing power
  display and the hover.

## Identity ranges

| What | Range |
|---|---|
| Spells | 73000–73572 (Midgard ID + 10600); style procs 73300–73341; RR5 73560 |
| Tooltips | 25000–25572 (the client reads tooltip IDs as signed 16-bit, so they must stay at or below 32767) |
| Styles | 2200–2241 |
| Companion template | 60173001 |
| Realm abilities | InternalID 1940–1943 |
| Spell lines | `Tuatha.Sovereign00`–`22` (class hint 67), merged into one client line by `PendragonSpellbook.Hibernia` |

## Install and roll back

```
python source/tools/sovereign/install_tuatha.py artifacts/modern-client-test --apply
python source/tools/sovereign/install_tuatha.py artifacts/modern-client-test --rollback <backup folder>
```

The installer:
- previews by default;
- requires the selected game to be stopped;
- seeds a private copy of the world and verifies all 37 saved-progress tables;
- builds the client from the pristine 1.130 `game.dll`, replacing only a known native-slot client;
- updates `runtime/modern-client.json` `GameSha256`;
- backs up every replaced file and verifies the installed hashes.

Rollback refuses to overwrite files changed since installation.

## Still needs in-game checks

- creation and relog
- all six weapon lines' styles
- Faerie Drake stealth and controls
- the Sidhe transformation's appearance
- Step Between Worlds on uneven terrain
- RR5
- a full power bar (the class now draws power from Piety)
