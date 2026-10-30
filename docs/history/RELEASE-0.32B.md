# Offline DAoC v0.32b — Darkness Falls Beta with Sluaghbinder

This is the optional Hibernian Sluaghbinder version of the
[normal v0.32 Darkness Falls Beta](RELEASE-0.32.md). It carries the same
Classic + Shrouded Isles, Darkness Falls, Bounty Master, Bard/companion,
and bot-route updates, then adds the class. Choose normal v0.32 if you do
not want Sluaghbinder. The v0.3, v0.31, and v0.31b releases remain legacy
downloads.

## Darkness Falls Beta limits

Albion, Midgard, and Hibernia can enter the dungeon. Autonomous bots are
intended to grind ordinary reachable monsters, use staged floor-aware paths,
take their own realm exits after one-way descents, and engage opposing-realm
bots near the shared center. Players can use existing seal vendors. The owner
has not completed a long live bot test there. **Darkness Falls raid AI is not
implemented.** Legion, the hardest level-70+ encounters, unreachable flying
targets, and unverified routes or monsters are excluded from ordinary bot
goals. The [normal release notes](RELEASE-0.32.md)
explain this implementation in detail; the optional class does not remove
these beta limits.

The September 26 beta maintenance update also fixes solo Bard bot
disconnect/re-entry churn caused by a null group in the PvE add-mez check.
Its Darkness Falls safety certificate accepts High Lord Oro's original
randomized level-65–70 template range without making that raid boss a
normal grind goal. Level-1–49 Bounty Masters can also assign certified,
floor-reachable ordinary Darkness Falls monsters. Unverified, flying, and
raid targets are excluded; home-realm dungeon targets and the level-50
epic bounty list are unchanged. No Darkness Falls raids were added.

The September 26 beta refresh sends Midgard bots through their reachable Darkness
Falls entrance, keeps low-level familiar goals within each realm's wing, and
lets surviving party members leave after a wipe. Solo bots look for a nearby
reachable familiar after a room clears or wait for the camp's respawn instead
of giving up early. Shared Bounty Masters avoid repeating the same completed
species across relogs; the Lough Derg empyrean orb and Domnann sneezer camps
were expanded, and insidious cniogcrags use a visible model. Bot-created
synthetic charm candidates no longer linger or respawn if the cast fails.
These changes also belong to normal v0.32; they are not Sluaghbinder-only.

## September 28 shared stability update

This optional release also carries the current normal v0.32 bot fixes:

- Savages can search ordinary outdoor camps for targets, while dungeon and
  known-risky camp checks stay strict. Cursed Tomb no longer assigns its
  low-level cave-spider goal behind a much stronger entrance pack. Koalinth
  goals distinguish mixed-level spawns and use the connected approach.
- Groups can begin a normal pull at 90/80/80 readiness rather than waiting for
  every member to reach 100%; draining fights still recover fully. Meetups
  can try a different validated point after a route failure, stop resetting
  every member's timer for a no-show, and continue with a viable party after
  bounded retries. Revived members only reform locally with a two-way path.
  The repeat Lough Derg short-detour failure has an alternate verified step.
- Hibernian solo bots can take a verified, paid stable route around a repeated
  outdoor zone-border loop on the way to Darkness Falls. Ordinary PvE goals
  do not send bots into another realm's frontier; RvR and realm-event travel
  are unchanged. These are routing fixes, not easier monster combat.
- Surplus backpack gear can be sold when bags are full, while equipped items,
  useful weapon swaps, and spare instruments remain protected. Cursed Tomb
  groups prefer an entrance-area goal first, and two falsely empty camps use
  the levels of their live monsters.
- `/gminfo` reports a bot's helmet model and extension. Scale coif model 840
  with stored extension 2 or 3 uses the visible extension-0 appearance without
  changing its stats or saved item. Moving Enchanter/Sorcerer-style companion
  speed casters can stop to cast and catch up. Classic-side Shrouded Isles
  portal visuals at Mag Mell, Cotswold, and Mularn remain collision-free;
  player portal travel and bot routes were not changed.

The Cardova level-32 dux report was a raw-database versus template-level
misread, so that monster was not changed. Midgard Darkness Falls combat defeats
were not treated as route failures, and monster difficulty was not changed.
The Release server build and 2,130 optional source tests passed. A fresh long
live run is still needed to measure these fixes in play.

## Optional class included

Sluaghbinder is a Hibernian player class. New characters start as Acolytes
and promote at level 5. Its three core lines and three advanced paths provide
distinct pets and abilities; Muirenn in Tir na Nog trains the class. The
five linked epic quests unlock player-only Epic Spells services. Companion
and autonomous Sluaghbinder bots use class-specific builds and pet behavior.
The private Dullahan and Zombie Defender visuals, Zombie Priest equipment,
and Covenant pet heal timing from v0.31b remain part of the optional version.
See the [legacy v0.31b notes](RELEASE-0.31B.md) for the original class detail.
This refresh additionally makes Covenant companion and gamebots wait for their
one-minute Cairnheart pet heal to expire, recasting only when the pet still
needs healing. The heal no longer acts as a routine buff or delays rest.
Distinct routine pet buffs can follow the prior confirmed effect at the
normal cast pace outside combat; interrupted/unconfirmed casts and combat
keep their previous safety delay. This has automated coverage but still
needs a live class-bot check.

## Download, source, and rollback

From the [v0.32b release](https://github.com/shadowofze/OfflineDAoC/releases/tag/v0.32b),
download `DOWNLOAD-AND-PLAY-v0.32b.cmd` and `Get-OfflineDAoC.ps1` into one new
folder. Double-click the helper. It verifies and assembles the normal v0.32
game, then applies the current
`Sluaghbinder-v0.32b-darkness-falls-beta-20260928-patch.zip` in a
new sibling copy. The normal v0.32 base stays intact. If you already have a
clean v0.32 folder, use the patch archive's included installer and its
instructions. Earlier v0.32b beta patch ZIPs remain available but predate
this update. The optional copy receives a
rollback command; keep the base
and earlier versions until you have checked the new installation. Stop both
servers before importing saves or applying the patch.

The editable optional source belongs to
[`release/v0.32b-sluaghbinder-darkness-falls`](https://github.com/shadowofze/OfflineDAoC/tree/release/v0.32b-sluaghbinder-darkness-falls).
The normal v0.32 source belongs to its separate
[`release/v0.32-darkness-falls`](https://github.com/shadowofze/OfflineDAoC/tree/release/v0.32-darkness-falls)
branch. The source ZIP and GitHub's **Code > Download ZIP** are not complete
playable downloads. Use the matching source and runtime version when making
LLM changes. [Player instructions](../PLAY.md) and [LLM instructions](../LLM-QUICKSTART.md)
give the full setup steps.

## Verification

[v0.32b verification notes](VERIFICATION-0.32B.md) separate isolated source
tests from release-package and real-client checks. Beta does not imply the
bots have passed a long live Darkness Falls test.
