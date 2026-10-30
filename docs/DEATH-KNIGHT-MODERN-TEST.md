# Death Knight (live Necromancer) modern test installation

Target: `artifacts/modern-client-test` only.

The Death Knight is player class 66, an Albion class. It is the live Necromancer from the 1.122B
redesign: forms, direct casting and melee, and death servants. It is offered beside the classic
shade Necromancer (class 12), which is unchanged. Creation needs two things:
- **Server switch:** `classes / enable_death_knight_test=True`.
- **Patched client:** the client with native class slot 66, together with
  `classes / native_custom_class_slots=True`. Unpatched clients never show the class.

This is a first playable implementation, not a certified copy of live.

## Install and roll back

```
python source/tools/install_expansion_test.py artifacts/modern-client-test --classes 39,58,33,66 --apply
python source/tools/install_expansion_test.py artifacts/modern-client-test --rollback <backup folder>
```

The installer checks that the server is stopped. It backs up the database and `GameServer.dll`, and
it verifies the 37 saved-progress tables.

The client build comes from `source/tools/classslots/patch_class_slots.py`, which works only on the
pristine 1.130 `game.dll`. It is staged in `artifacts/classslots-staging-deathknight`. The installed
client it replaced is backed up under `backups/client-deathknight-*`. The launcher only starts a
client whose hash matches `runtime/modern-client.json` (`GameSha256`), so that profile was updated
to the new build, and its previous copy is in the same backup folder. To undo, copy both files back. The emulation checks (`verify_creation_emulation.py`, `verify_stub_emulation.py`,
`verify_screen_emulation.py`) all pass:
- class 66 registers after the Pendragon Sovereign, with the Mauler entry's fields;
- its name is "Death Knight";
- its creation stats are Intelligence, Dexterity and Quickness;
- the creation screen handles 18 Albion buttons.

## Identity

- **Shared with the Necromancer:**
  - Races: Briton, Inconnu and Saracen.
  - Stats: Intelligence, Dexterity and Quickness.
  - Base hit points and weapon skill.
  - Cloth armor and staves (`AlbClothCasterCareer`).
  - The Disciple champion trainer type.
- **Not shared:** the class does not derive from the classic shade class, so none of the shade,
  pet-health or combat-lock behavior applies.
- **Items:** the Death Knight shares every Necromancer item (`ClassItemRules`). This covers equipping,
  use and bot gear, and random loot is rolled as Necromancer loot.
- **Trainers:** a Death Knight Trainer stands 64 units from each of the 7 Necromancer trainers.
- **Spell lines:** six lines of its own (`Death Knight Deathsight` and so on, class hint 66) with the
  live display names. The class-specific lines win over the classic Necromancer's lines, which are
  untouched.
- **Kit ranges:** spell IDs 71000–71799, tooltips 23200–23999 and styles 6600–6699. The servant NPC
  templates are 66001–66005. The conjured weapon templates are `deathknight_icebrand_*` and
  `deathknight_nethersbane`.

## Mechanics (new handlers in `spells/DeathKnight/DeathKnight.cs`)

- **Forms:** maintained until changed, with a 2-second reuse shared by Revert Form. Changing out of
  Darkness requires Revert Form first (1.124B).
  - **Decrepit (1):**
    - 10% more magic damage.
    - Health regeneration that works in combat (1.122C and 1.123 reductions).
    - 50% chance to disease melee attackers, with a 15% snare (1.127).
  - **Chthonic (8):**
    - Up to 30% more health, scaling with Painworking.
    - 20 absorption (1.123B) and +30% parry (1.124D).
    - Up to 20% more weaponskill (1.126).
    - Spec AF of 125/75/50/25 by level, overwriting other spec AF (1.123B and 1.125).
    - 10% secondary magic resistance (1.125 and 1.129B).
    - Dismisses the servant and blocks summons, PBAoEs and bolts.
  - **Spirit (30):**
    - 10% of damage taken becomes power.
    - Increased power regeneration.
    - The servant gets +55% resistances while in range and the master is not crowd controlled.
  - **Darkness (RR5 Call of Darkness):**
    - You become a Demon Lord for 30 seconds, with a 10-minute reuse. It has the benefits of Chthonic and
      Decrepit Form (not Spirit), using live's own Demon values (see below).
    - It does not return you to a form when it ends.
- **Ground spells:** placed at the ground target. Only one is active per Death Knight (a new one
  replaces it), all share one reuse timer, and items do not extend their duration.
  - Decrepit/Unholy Ground: a disease, 15 seconds (1.122C, 1.123 and 1.126).
  - Icy Ground: Cold damage to up to 16 enemies (1.124D and 1.126).
  - Enchanted Ground: power for allies.
- **Painworking melee:**
  - Weaponskill and melee damage use Intelligence and the Painworking spec (hooked in the player and
    bot weapon stat and spec functions).
  - Conjure Icebrand gives a blade per five levels. Nethersbane is removed at login.
  - Both are staff-type weapons, usable with the staff ability, and they deal Cold damage in combat.
- **Magic conversion** (Soul of Magic through Way of Magic):
  - Self only (1.129B), with a 5-second cast (1.123) and renewals from 1.125.
  - The next magical attack is absorbed and converted to health at 5/10/25/50/75% (1.127).
- **Ignore line:** the ally has a 25–100% chance to resist debuffs, for 20 seconds with a 180-second
  reuse (1.123 and 1.129B).
- **Smaller mechanics:**
  - Power Shield.
  - Empowerment group crit aura.
  - Regenerate (self and servant).
  - Snares that ignore and grant no immunity: the Exhaustion and Ice lines and Freezing Howl
    (1.122C, 1.123B and 1.128C).
- **Servants:** Aegis, Soultorn, Fiend, Priest and Succubus.
  - They level with the caster.
  - Models are matched to live screenshots (see below), and each changes model and name in Spirit
    Form.
  - Their casters have their core spells.

## Kit (from the 1.122B notes, then 1.122C–1.129B)

All five lines are built from the 1.122B lists with every later change applied, including:
- the 1.123 moves (snares to Death Servant; the PBAoE and bolt allowed in Decrepit and Spirit);
- 1.127 Speed of the Dead in place of Bringer of Death;
- the 1.124D and 1.126 damage and reuse changes;
- the 1.128C Plague damage and the Spirit Bladeturn at 26;
- the 1.129B Ignore and magic conversion changes.

Removed spells are not added: Death Shredder, Swords of Arawn and Bringer of Death.

The realm abilities are the 1.122B Necromancer list without Mastery of Parry (1.124D), plus the
Death Knight Call of Darkness.

## Fixes after the first in-game test

- **Servants dying on summon:** stock permanent pets use a duration of 65535. The servant spells had
  0, which ended the pet effect at once.
- **Servant models:** now the DR Greater Necroservant (Aegis), Ghost (Soultorn), DR Necroservant
  (Fiend), Inquisitor (Priest of Arawn) and Succubus.
- **Form appearance:** forms now change the character's model.
  - Decrepit uses the Lich (441).
  - Chthonic uses the player-model Flesh Wight (23).
  - Spirit uses the ghost model of the player's own race and gender, the same table the shade uses.
  - Darkness uses the Wraith (655).
  - Live's exact form models are not documented anywhere I could find, so these are the closest
    client models. The client tables have no Decrepit, Chthonic or Spirit model by name.
- **Spell art:** the client contains the 1.122B Necromancer effects under internal names, and these
  are now used by rank (grey to red):
  - Empowerment: crit buff 15227–15231
  - Exhaustion snares: necro st slow 15233–15237
  - Magic conversion: necro dconvert 15238–15242
  - Enchanted Ground: necro power storm 15232
  - Power Vortex: 15243
  - Pet fear: 15197–15201
  - Freezing Howl: 15192–15196
  - Icebrand and Nethersbane: 15185 and 15184
  - The Heretic Hellflower chant also uses its live health/AF aura effects, 15351–15355.
  - Other spells keep the classic Necromancer art.
- **Icebrand and Nethersbane:** now two-handed swords, using Albion's Great Sword (7) and the dark
  two-handed epic sword (3314). The career grants Weaponry: Two Handed. Painworking styles take any
  weapon.
- **Starting equipment:** new Death Knights get the Necromancer's starting cloth outfit and staff.
- **Sources checked:** the official class library still shows the classic shade Necromancer; it was
  never updated for 1.122B. The 1.122B–1.129B patch notes stay the source for values.

## Second in-game test fixes

- **One spell per level per line:** the client casts a list spell by line index and level, and the
  server takes the first spell at that level (`UseSpellHandler.GetSkill`). A second spell at the same
  level is unreachable.
  - Decrepit Form and Revert Form were both level 1, and the kits had other such pairs.
  - The installer now moves a colliding spell to the nearest level no spell in that line uses.
    Every other spell keeps its live level. Revert Form is now at 4, and the Power Blast line sits
    one level off the Exhaustion snares.
  - This also moves seven Bainshee spells, listed in `spread_levels` output.
  - The Heretic is exempt: its specs use the hybrid list, which is cast by skill slot.
- **Forms casting a disease on you:** forms no longer carry the Decrepit disease as a sub-spell. The
  base handler casts sub-spells on the target after every cast, so each form tried to disease the
  Death Knight itself.
- **Weapon look:** Icebrand is the Great Sword with the client's cold-vapor two-hander glow (effect
  26). Nethersbane is the Darkness Falls Shadowblade two-handed sword (4410) with its glow (473). The
  client has no dedicated Icebrand model or file.

## Confirmed from live screenshots (owner's live Necromancer)

- **Spirit Form:**
  - Level 30, 20% power, instant, 2-second recast.
  - The delve also gives +40 resistance to Body, Spirit and Energy, now applied.
  - The Necromancer becomes the green hooded Wraith (monster 655) and still holds its weapon.
- **Summon Aegis:** level 5, 40% power, 6-second cast.
  - The "umbral aegis" is a red-orange giant scorpion: the Fiery Scorpion (640).
  - In Spirit Form it becomes the "spirit aegis", a purple starry scorpion: the Starry Scorpion
    (1257). The servant changes model and name while the master is in Spirit Form
    (`DeathKnight.SpiritServants`).
- **Icebrand:** a translucent blue blade. It is now the Great Sword with the client's "icy blue glow"
  (effect 27).
- **Call of Darkness:** the live delve says Demon Lord, Chthonic and Decrepit benefits +10%, 30
  seconds. Darkness now matches that (it no longer counts as Spirit Form) and uses the DR demon (2).
- **Forms:**
  - Chthonic Form is the world's "Chthonic Knight" mob model (653), which the client draws as the
    bronze-plated DR Abomination.
  - Decrepit Form has no matching model in this client; the Avalonian undead (452) stands in.
- **Servants (normal / Spirit Form):**
  - Soultorn: Wraith 655 / phantom, grey Shackled Soul 1745.
  - Plated fiend: green Hulker 657 / umbral hulk, red Hulker 662.
  - Succubus 644 / arch demon, Winged Demon 605.
  - Priest of Arawn: Inquisitor 2119 / image of Arawn 645. Both are best guesses.

## Rebuilt from live's spell data

The daoc.gg character planner carries live's spell data: the 1.123b spell records with every sub-spell and delve
text, the Painworking styles, the item bonuses, and a patch log through 1.130a. The extract is in
`artifacts/research/necro-live/` (not in Git). Where the patch notes changed a value after that baseline, the
patched value wins. For example, the raw Chthonic spec AF of 50/75/125/205 is the table that 1.123B reduced to
25/50/75/125.

- **Form models (live shapechange spells):** Decrepit 23 (drawn as the DR greater necroservant), Chthonic 653,
  Spirit 1670 (Necromancer Shade) and the Demon Lord 635 (Ash Demon, drawn as the DR demon).
- **Form bonuses (live sub-spells):**
  - Chthonic gives +20 Painworking instead of a weaponskill percentage.
  - Spirit adds +20 stealth detection.
  - The Demon Lord has its own values: +20% magic damage, 22 absorption, +40 Painworking and +25% parry.
- **Spell fixes:**
  - Locust damage and power.
  - Infinite Death damage.
  - Death Bladeturn at 24.
  - Exhaustion snares at 3/13/23/33/43 lasting 10-30 s.
  - Power Blast costs 16/30/44/70/99.
  - Plague durations of 5/10/20/20/20.
  - Spirit Bladeturn at 15% power with a 5 s cast.
  - Power drains of 6-56.
  - The magic conversion and Empowerment reuse timers.
  - Nethersbane cast in 15 s.
  - No power cost on the ice snares and Anti-Magic line.
  - The ground spells pulse each second on up to 8 enemies, and Unholy Ground has a 375 radius (1.130A).
  - The power storms have a 200 radius, and Mystic Ground costs 70 power (1.130A).
  - Channeled Frenzy costs 65 power (1.130A).
- **Live names:** Regenerate Body, Dead Flesh Living and Imbue the Abyss; Majestic, Spellbound and Mystic Ground;
  Communion with Death and Intimacy with Death.
- **Removed:** the 1.122B Arawn parry buffs, which are not in the live list.
- **New spells:**
  - **Wake Servant (Death Servant 26):** cures mesmerize on the servant.
  - **Power Lock (Death Servant spec 45):** a 10 s lock. The target is stunned and loses 15% of its power each
    second to the Death Knight, and neither side can be hit in melee. 90 s reuse.
  - **Arawn's Legion (Death Servant spec 50):** a 10 s cast. Up to 8 legionnaires rise beside enemies within
    2000 units and attack them for 30 s. 10 minute reuse.
- **Styles:**
  - Live chains: Chilling Touch follows Villainous Strike, and Vanquisher follows Arctic Death.
  - Live endurance, to-hit and defense values.
  - Vanquisher strips ablatives.
  - Icy Cleave has a 125 radius, and Frozen Edge lasts 12 s.
  - The Deathseeker proc halves healing for 25 s.
- **Servant abilities (live level-50 values, scaled to the servant's level):**
  - Aegis: Aegis Shell.
  - Soultorn: Demonic Collapse and Soultorn's Death.
  - Fiend: Fiend Swings.
  - Priest of Arawn: Arawn's Heal, which also cures disease, poison and nearsight.
  - Succubus: Demonic Entrancement.
- **Spirit Form:**
  - Each servant has a second template (66011-66015) with its spirit model and name. Its spells are added to the
    servant's own while the master is in Spirit Form:
    - spirit aegis: a heat burst and Spirit Shell;
    - phantom: a 35% plague;
    - umbral hulk: Rabid Sickness;
    - arch demon: an area mesmerize.
  - The image of Arawn gets the resistances only. Live's data names no extra spell for it.
- **Conjured blades:** Icebrand carries the live stat bonuses for its level. Nethersbane has the live bonuses and
  two procs: a 150 cold strike and a cold resistance debuff.

## Third in-game test fixes

- **Umbral aegis:** now the DR Fiery Scorpion (2150). Its DR mesh and skin pair with the spirit aegis (1257); the
  classic Fiery Scorpion (640) drew the old small mesh.
- **Icebrand:** now the Midgard spirit great sword (4842), a translucent glowing blue blade. It is close to live's
  but not the same model; it resembles the starlight weapons. The
  Albion spirit weapons glow red. Blades conjured before this change keep the old look until recast.
- **Decrepit Form:** no absorption. Live's current delve lists only the 10% magic damage; the 5 ABS in the 1.123b
  data was removed in 1.125. The Demon Lord's absorption is Chthonic's 20 +10% (22).

## Icon pass

Live's spell data has no icon field, so icons come from the client's own effect table (`spells.csv`):
- **Kept names:** a live spell that keeps an older spell's name uses that spell's effect (Vitality Theft, the
  Regenerate line, Communion and Intimacy with Death, Eviscerating Protector, Spirit Shell).
- **Ranked lines:** each rank steps through its effect series: the AoE DoTs, Locusts, Horrors, power drains and
  Power Blasts.
- **Dedicated effects:**
  - Wake Servant uses Dead Awakening, the classic Necromancer's cure-mez effect.
  - Power Lock uses Grapple.
  - Gift of Arawn uses Arawn's Gift.
  - Arawn's Legion uses Call Death Servant.
  - The aegis shell, fiend haste and priest heal use the client's Demonic pet spells.
- **1.122B effects:** the effects 1.122B added for the Necromancer (crit buff, necro slow, necro dconvert,
  power storm, pet fear, Freezing Howl, Icebrand, Nethersbane) were already in use.

The client has no dedicated Form or summon icons, so those keep the classic Necromancer's servant and summon
effects.

## Snare immunity

The Exhaustion, Ice and Freezing snares (`DeathKnightSnare`) now also land on targets that already have root or
snare immunity, as live's delves say. They still grant none. This uses the shared `RespectsSnareImmunity` switch
in `SpeedDecreaseSpellHandler`. The Plague nukes keep respecting immunity (1.122B hotfix 5).

## Approximations and not done

- **Not modelled:**
  - The 25% interrupt resistance some servants have (from Gemini's notes, not in the live data).
  - The Succubus spirit rear stun style.
  - The legion's look, which live's data does not give (the Legion demon stands in).
  - The Regenerate power costs above rank 3, which continue live's 2/4/10 progression.
- **Servants:**
  - The spirit-form abilities (Spirit Slash, Rabid Swipe, the Phantom disease, the AoE Succubus mez)
    are not modelled; Spirit Form gives the resistance bonus only.
  - Servant melee styles (Umbral and Fanatic Slash) are not modelled.
- **Styles:**
  - The client has no Painworking styles, so the 10 styles use the Friar staff style art (IDs
    230–244) with live names and effects.
  - Vanquisher's ablative strip is not modelled.
- **Weapon art:** the client has no Icebrand or Nethersbane models, so both use two-handed sword
  models with glows. The Nethersbane procs are not modelled.
- **Chthonic scaling:** live says only that the bonuses "scale with Painworking". Here they run from
  50% when untrained to 100% when Painworking equals the character's level.
- **Estimated values:** the Locust and Power Blast costs and the Decrepit and Spirit regeneration
  rates.
- **Bots:** there is no companion or gamebot Death Knight build yet.

## Tests

- `UT_DeathKnight` (11 tests): identity, items, the race switch, form effects, Darkness, Power Shield,
  conjured weapon levels, Ignore and snare immunity.
- `test_expansion_test_data.py` (12 tests across all four classes): rerunning the installer, save
  preservation, start locations, a concrete handler for every spell type, the live-change
  assertions, trainers, lines, servants, weapons and realm abilities.
- `test_class_slots.py`: the static client patch checks, plus the three emulation scripts.

These are automated checks only. None of this has been checked in game yet.
