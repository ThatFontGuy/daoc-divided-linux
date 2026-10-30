# Stormforged development build

**Modern test update:** Storm Sovereign now replaces this kit in the modern test installation.
See [STORM-SOVEREIGN.md](STORM-SOVEREIGN.md). The design below documents the older class.

Stormforged is an intentionally powerful Midgard class alongside the original Thane.
The working name can be changed. Server class 64 is presented through Midgard's Mauler
slot (61) in the original client. The server, database and client patch must be installed together.
The original Thane and the Hibernian Sluaghbinder mapping remain separate.

## Current design

- Any Midgard race (Norseman, Troll, Dwarf, Kobold, Valkyn, Frostalf, Deifrang), even ones the
  server's disabled-race list blocks for other classes; normal leveling to 50. The patched classic
  client still offers only Norseman, Troll and Dwarf. Class identity is retained from creation.
- **Chain, large shields, hammers, axes and swords from level 1**, as intrinsic class
  abilities. New characters receive Midgard chain armor, a training hammer, a large
  shield and the normal shared recall stone. Existing inventories are not reset.
- Sword, axe, hammer, shield, parry and stealth automatically match character level.
  Spells unlock automatically. The client sees one **Stormforged** spell line holding only the
  newest learned rank of each ability; weapon styles retain their full lists. On the server each
  ability still has its own line (the client addresses spells by line and level, and every type
  shares the same tier levels). `StormforgedRules.ClientSpellLines` merges them for the client and
  gives each ability a fixed slot number, its unlock level pushed past slots already taken:
  Chain Lightning 1, Stormbolt 2, Stormhammer 3, Stormheart 4, Stormrest 5, Stormsong 6,
  Thunderclap 7, Thunderforged Ward 8, Stormbound Elemental 9, Lightning Bomb 10, Release Storm
  Clump 11, Stormguard 12, Stormstep 15, Second Thunder 20, Thunder Recall 21, Eye of the Storm 25,
  Ride the Storm 30, Avatar of Thor 40. The spellbook shows these slot numbers as levels. Slots
  never move, so hotbar buttons keep working as ranks upgrade; buttons made before this change
  must be dragged again from the new line. No tradeoff between keeping lines trained is required.
- Stormcalling: stronger energy attacks, a cast-time bolt, instant thunderclap on a
  12-second cooldown, instant 350-radius Chain Lightning centered on the caster (12-second
  cooldown), and Stormhammer, a 2.5-second targeted 350-radius AoE using the stock Thane hammer effect. Damaging hits return 50% as health
  and 15% each as power/endurance, limited by missing resources. No enemy resource pool is required. Stormforged spells and internal buff/pet spells
  cost power only; they do not charge the server default five endurance per cast.
  Melee styles retain their normal endurance costs.
- Stormheart: a maintained 350-radius lightning aura, once every four seconds. Each
  enemy damaged returns 75% of its damage as health and 25% each as power/endurance.
  Returns scale per target, including multiple enemies in the same pulse. Misses/resists
  do not pay; overkill is not counted. Ordinary server attack legality still applies.
- Stormsong: one maintained group effect supplies speed, health/power/endurance recovery
  and a lightning damage add. Recovery occurs every four seconds. Speed reaches 205%
  at level 40, persists in combat and stealth, and does not grant immunity to crowd control,
  encumbrance or relic-carrier speed rules. Group support reaches 1,500 units; children
  stop when the singer is gone or the member leaves the group/range. The singer's
  chant runs until canceled; its activation visual is not replayed on recovery ticks.
  Its damage add defers silently to an equal or stronger active damage add (including
  Ward), rather than retrying and producing an already-active message every pulse.
- Thunderforged Ward: self-only armor factor, all eight primary stats, all nine normal
  physical/magical resistances, a damage add and a reactive energy damage shield. Primary
  stats and AF scale directly with character level, even using the first spell rank;
  low-level buffs no longer round down to zero. Resistances reach full strength at 40. This does not
  replace equipment bonuses or force every derived combat value to a universal cap.
  The ward uses the stock Thane self-buff icon with a private tooltip showing numerical
  stat/AF/resist bonuses. Stormsong shows regeneration and speed values.
  Ward potency/bonuses are captured at cast time; recast after leveling to update them.
- Stealth may coexist with the maintained effects. A storm attack/pulse that attacks
  an enemy reveals the caster. Ordinary melee and detection rules still apply.
- Stormrest: a targeted heal usable only while both caster and recipient are out of combat.
- Stormbound Elemental (level 5) now summons a Stormbound Commander plus a Mender
  and Tempest automatically. All three match the owner's level, including after leveling;
  the stock Bonedancer cumulative-level cap is not used. The commander keeps its instant
  single-target/area lightning, has 4x pet health scaling, 2x melee damage, at least 35%
  armor absorption and 2x level armor factor per armor slot. Its melee threat is 8x damage,
  with a 350-radius instant taunt every five seconds (subject to NPC spell scheduling).
  The Mender prioritizes injured party/pet targets under 90% health, casts lightning and
  debuffs attack speed; the Tempest casts lightning and debuffs energy resistance. Support
  spells scale with their level, and support health scaling is 2x. Both use the same stock
  elemental model (114). Attack/follow/passive commands propagate through the commander;
  releasing or losing it also releases its support spirits. A dead support spirit can be
  replaced by releasing and resummoning the squad.
- Lightning Bomb: from level 10, ground-targeted Animist-style stationary summons using
  the same stock appearance at a smaller size. They cast ranged area lightning plus an instant 350-radius PBAoE every four seconds, last 120 seconds,
  have no summon recast delay (the three-second cast remains),
  and allow **16 owned lightning storms**, even around one ground target. This private
  per-owner allowance replaces the ordinary Animist player/area caps for these storms;
  co-op players have separate allowances, and private storms do not consume the ordinary
  shared Animist area quota. Ground visibility/range/terrain/keep-height checks remain. Human-owned Lightning Bombs
  can acquire legal grey-con enemies too; stock Animist targeting remains unchanged. They are repeating turrets,
  rather than one-shot proximity mines. Release Storm Clump unlocks at level 10: target
  one owned turret to release your turrets within 500 units, without releasing the
  melee elemental or another player's pets.

## Loot and equipment permissions

Atlas ROG generation explicitly recognizes class 64: chain from level 1, swords/axes/
hammers/shields, maximum large shield size, and the Thane-style melee/Piety stat profile.
Skill bonuses target the class's actual Sword/Hammer/Axe/Shields/Parry/Stealth lines;
stock Stormcalling and staff skill bonuses are excluded. Generic mob drops and group
rolls for other classes retain their normal behavior. Existing loot is not rerolled.

The intrinsic Shield ability is one level-1 grant at rank 3. Granting ranks 1, 2 and 3
at the same acquisition level allowed the native ability selector to choose rank 1.
Rank 3 includes the lower shield sizes; the class does not need three separate grants.

## Heroic storm abilities

- **Stormguard (level 10):** until-cancelled self effect. Each blocked melee attack
  launches energy damage at the attacker and enemies within 350 units. The strike
  uses the normal per-hit 50% health / 15% power / 15% endurance restoration.
  Parries, misses, ranged attacks and spells do not trigger it.
- **Second Thunder (level 20):** until-cancelled self effect. A fatal damage hit is
  intercepted before death, restoring full health/power/endurance and launching a
  500-radius lightning burst. The trigger has a two-minute shared spell cooldown;
  cancelling/recasting the protection does not reset it. This is damage protection,
  not resurrection after a direct administrative death or release.
- **Avatar of Thor (level 40):** 60-second transformation using installed Frost Giant
  model 918, with a three-minute reuse timer. Custom lightning strikes deal double
  damage, private spells cast in at most 250 ms, and every two seconds it restores
  15% of each maximum resource and pulses 350-radius lightning. The previous model
  is restored on removal unless another transformation has replaced it.
- These use private tooltip identities and normal buff cancellation. None of the
  client catalogs or stock models are modified. The installed model has mesh,
  texture, movement and combat animation entries; its in-game appearance still
  needs user acceptance.

## Storm travel and network

- **Stormstep (level 15):** instant teleport to an **enemy target** up to **2,000 units** away,
  landing about 90 units in front of it and facing it, followed by a 350-radius lightning arrival
  blast. Eight-second cooldown. Normal target range/LOS checks apply; where a navmesh exists the
  landing spot is snapped to it, falling back to the target's own spot. A caster already beside
  the target stays put and just bursts.
- **Thunder Recall (level 20):** instant, five-second cooldown. Moves this owner's live
  Lightning Bombs in the same region to a ground target within 1,000 units and refreshes
  the actual summon effects and registry lifetimes to two minutes. Uses in-region NPC
  movement to preserve brains, ownership, pet counts and effects. Can gather all 16 private storms in one area.
- **Eye of the Storm (level 25):** until-cancelled effect, pulling hostile NPCs within
  600 units to about 90 units from the caster every four seconds. Ignores friendlies,
  training dummies and CC/root-immune enemies; validates terrain before moving them.
- **Ride the Storm (level 30):** until-cancelled effect. This owner's elemental and bombs
  within 2,000 units echo directly cast Stormbolt, Thunderclap, Chain Lightning and
  Stormhammer. Echoes preserve the original area shape, are instant/free, and use normal
  pet casting/range/LOS. PBAoEs center on each pet. Aura/proc/echo casts and other casters
  are excluded, preventing recursive storm networks.

The first data pass has spell tiers at 1, 5, 10, 15, 20, 30, 40 and 50. Numerical tuning
lives in `source/tools/stormforged/seed_stormforged.py`. The normal Thane data is not rewritten.
No autonomous Stormforged population or player-companion AI is introduced in this first pass.

## Build and verification

Use the normal Release build and server test commands in DEVELOPMENT.md. Focused C# tests:

    dotnet test source/server/Tests/Tests.csproj -c Release --filter FullyQualifiedName~UT_Stormforged

Migration and binary-patch tests (require the original clean 0.36 files under playable/):

    python source/tools/stormforged/test_stormforged.py

The database migration is preview-only unless explicitly applied. It checks ID collisions,
does not modify player-progress tables, and adds package-owned content transactionally.
Spell IDs 62000-62155 and tooltip IDs in the 20600 range are reserved by this implementation.
The client patch accepts only the verified original classic 0.36 SHA-256; it refuses unknown
or already patched binaries. The installer also recognizes its exact known patched output for
subsequent server/content updates. The patch adds a private PE section and changes only Midgard's registration
and label initializer. The Godot client is not wired to this class yet.

## Installation and rollback

Prefer a separate test installation. Stop its client, launcher and server first. The source
checkout builds a newer upstream development server than the sealed 0.36 playable package;
deploying that build also includes its existing upstream changes, not just Stormforged.

Preview, which does not change the selected game:

    python source/tools/stormforged/install.py "<game-folder>"

After reviewing the preview, install into the stopped game:

    python source/tools/stormforged/install.py "<game-folder>" --apply

The installer backs up the database, client and three server DLL copies with a hash manifest,
then verifies installed hashes. It never starts a server. Rollback:

    python source/tools/stormforged/install.py "<game-folder>" --rollback "<backup-folder>"

Rollback refuses to overwrite files changed after installation, including a database with newer
gameplay. It preserves the backups for manual recovery rather than discarding later progress.

## Required first in-game acceptance

Development checks completed: 2,782 server tests passed (including 18 Stormforged checks),
and eight Python checks passed for migration, binary patching and guarded installation/rollback.
The installer preview succeeded against the local game. The owner confirmed first character
creation and login in the separate test installation. Starter equipment and buff/chant behavior
were revised after that first playtest; the checks below need to be repeated. The normal
playable installation has not been patched.
An isolated clean test installation is prepared at `artifacts/stormforged-playable`, with
the client patch, content migration and matching server build applied and backed up.
It has not been started. Stop the normal server before testing it: both use port 10300.

Automated tests do not establish gameplay correctness. Before using a personal save, check:

1. Stormforged appears only in Midgard with Norseman/Troll/Dwarf; ordinary Thane still works.
2. Create, verify starter armor/hammer/large shield/recall stone, log out/in, and verify automatic skills.
3. Compare restored resources against damage on one and several enemies, including resists.
4. Verify the aura does not attack friends and reveals stealth when it attacks an enemy.
5. Test chant speed in and out of combat/stealth, group join/leave and movement restrictions.
6. At 40, inspect all stats, AF/resists, reapply/cancel the ward and check for stacking/leaks.
7. Verify Stormrest fails if either participant is in combat.
8. Check elemental melee, instant cooldowns, follow/attack/release and cleanup on owner logout.
9. Place bombs at valid/invalid ground targets; verify area damage, lifetime and turret limits.
10. Stop/restart and confirm character identity, inventory and progression survive.

After the spell-line routing update, remove old Stormforged hotbar spell buttons and
drag fresh buttons from the spell list. Old buttons retain obsolete line indexes.
Lightning Bomb requires a valid visible ground target within 1,000 units.

## Commander squad verification

The squad uses private templates 60171003/60171004 and internal spell IDs 62206–62209
and 62217–62219. No ordinary Bonedancer level, support-slot or summon-pool rules are changed.
The player spell list still uses its existing summon button and unique line/level addresses.
Automated checks cover ownership-level matching, level increases, health/melee/threat factors,
support spell scaling without repeated multiplication, healer target/range selection, support
release propagation, the sixteen-storm boundary and seeded support spell/template wiring.
Combat behavior and client presentation still require an in-game acceptance pass.

## Innate storm vitality and Mender support

Stormforged has intrinsic bonuses from level 1, recalculated directly from level rather
than written into saved base stats or applied as a removable buff. Each level gives +2
in all eight stats, +10 maximum HP and +2 maximum power, capped at character level 50.
At 50 this is +100 stats, +500 HP and +100 power; Constitution/Piety also contribute
normally to health/power. These bonuses stack separately from Ward, item caps and normal
buff caps, survive cancellation/death/relog, and don't require recasting after leveling.
Other classes and ordinary NPCs receive none of these intrinsic bonuses.

The Mender explicitly considers its human summoner even if the group roster is empty,
and prioritizes an injured summoner before the rest of its nearby party/pet roster.
It attempts defensive support while following and assisting attacks, preserving the
normal pending-cast gate. Range, region, life state and helpful-target rules still apply.

Its private spell IDs 62220–62236 copy the strongest installed healer/shaman base stats,
STR/CON, DEX/QUI, acuity, armor, 37% combat speed, power/endurance regeneration, Frigg-style
health regeneration and six magical resists. Copies keep native effects/values and stock
icons, have no concentration or power cost, and don't appear as player spell buttons.
Long buffs last an hour; celerity/Frigg retain their native short duration and are renewed
as needed (Frigg only for injured targets). Normal buffs keep their normal caps; Ward can
already fill some of those caps. The passive class bonus remains separate and visible.
The Mender upgrades weaker native buffs and skips equal/stronger active effects rather
than repeatedly attempting a rejected cast. Allow time after summoning for it to cast its
buffs; healing takes priority. Release/resummon the squad after installing new pet spells.

Human-player tests also cover the private sixteen-turret allowance. GamePlayer does not
implement the bot-facing IGamePlayer interface; both types are explicitly recognized for
that allowance and for recalling all private storms without the stock area cap.
