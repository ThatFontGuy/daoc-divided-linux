# Co-op world with guild warfare: implementation study

Status: disabled in the local test installation at the owner’s request; normal RvR restored.
The opt-in hybrid implementation is retained for later work. Cross-realm capital teleporter changes were removed.
Use the installer with `--disable-coop-pvp --apply` to restore normal RvR, default BG claims and eight-player keep claims.
The guild blessing proposals remain design work; no new blessing/reward system is included.

## Proposed rules

- Classic/SI home lands, capitals, ordinary dungeons and housing: cross-realm co-op.
  Allow mixed-realm groups, guilds, trade and communication.
- Darkness Falls, selected frontier regions/zones and battlegrounds: guild-based PvP.
  Configure an explicit allowlist, validated against the installed world. Do not enable
  PvP merely because a broad RvR flag happens to be set on another expansion's zone.
- Group members and guildmates are friendly. Proposed alliance support: allied guilds
  friendly too. Guildless players may fight unrelated players in these areas but cannot
  claim objectives; grouping remains a way for friends to play together.
- Apply the same ownership/team decision to pets, commander subpets, bombs, AoE damage,
  heals, buffs, guards and kill rewards. Outside warfare areas player-owned attacks
  cannot damage another player or their pets (apart from any explicitly retained duels).
- Keep portal areas, transitions and resurrection points protected. Spell legality must
  check both actors' locations, including delayed hits/pulses crossing a boundary.
- Keep familiar battleground level brackets. Decide separately whether realm-rank caps
  and normal entry restrictions should remain in the private server.

These rules are implemented below; the reward designs later in this document remain proposals.

## Existing foundations verified in this source

- `serverrules/PvEServerRules.cs` permits cross-realm groups, guilds, trading and
  communication, and supplies cooperative player friendliness/attack restrictions.
- `serverrules/PvPServerRules.cs` blocks attacks on groupmates, guildmates and battle-group
  members, resolves pet ownership, and has configurable safe/unsafe regions. Its
  `IsSameRealm` is not a complete guild hostility policy: player-to-player friendliness
  remains broadly permissive. Simply copying its attack check is insufficient.
- `keeps/KeepManager.cs:IsEnemy` already has a PvP branch using guild/alliance ownership,
  selected by the global server type. Its friendly-group loop also appears to recurse
  on the original target instead of the iterated member; verify/fix this before reuse.
- `keeps/AbstractGameKeep.cs` persists claimed guild names and has claim permissions,
  claim limits and optional BG claims. Claim validation still requires the player's realm
  to match the keep's realm. Capture/claim/guard/door behavior needs a consistent guild
  ownership path rather than assuming the global PvE or PvP flag supplies everything.
- `serverrules/DFEnterJumpPoint.cs` gates entrance by realm keep ownership only on Normal
  servers; non-Normal server types permit entrance. Keep DF open to everyone in the
  proposed co-op mode, independently of objective buffs.
- `world/Region.cs` and `world/Zone.cs` expose RvR/frontier information. Installed region
  IDs and zone boundaries still need validation before writing the PvP allowlist.

## Guild rewards already present

`gameutils/Guild.cs` persists merit points, one active bonus type and its start time.
`commands/playercommands/guild.cs` charges 1,000 merit for a 24-hour selected guild bonus.
Code defaults in ServerProperties are +5% PvE XP, +2% RP and +5% crafting speed;
these are source defaults, not a claim about this played world's configured values.
There are XP payout, RP/BP event and crafting hooks. The existing single-bonus slot
would need extension for simultaneous combat and progression blessings.

Merit-for-boss-kills hooks exist, including Legion and the Tuscar/Kula script. Having a
reward hook does not establish that the encounter itself is complete or raid-ready.

## Reward design proposal

1. Persistent guild progression: earn merit from PvE boss kills, first objective captures
   and successful defenses. A small guild can progress during solo/co-op play too.
2. Spendable blessings: activate a 24-hour XP/crafting/RP bonus using the existing system.
   Suggested initial tuning: +10% XP, +10% crafting speed or +5% RP, pending owner choice.
3. Ownership blessings: one claimed keep grants a modest health/power/endurance recovery
   buff; holding a second distinct objective can add a modest damage or defense blessing.
   These combat effects are new work. Define their interaction with ordinary caps,
   Stormsong/Ward and pets explicitly; normal capped stats may hide a flat stat reward.
4. DF objective: add a capturable standard/shrine for a guild blessing. DF has no verified
   existing guild-owned control point in this review, so this requires new content.
5. Persistent status: show active rewards and objective ownership through a guild command
   or NPC. Resolve ownership on capture, loss, disband, guild join/leave and restart.
   Avoid unlimited stacking from repeated captures; award distinct captures/defenses and
   scale repeated PvP kill merit so alts/bots cannot generate unlimited rewards.

Guild PvE merit should work without another human being online. Autonomous bots and
player companions need separate participation rules; an account should not receive
several independent guild awards merely because its summoned pets helped kill a target.

## Suggested implementation order and checks

1. Opt-in hybrid ruleset and a single hostility helper, with tests for cross-realm co-op,
   same-realm enemy guilds, groups, guildless players, alliances and location boundaries.
2. Pet trees/AoE/heals/buffs/rewards and companion/autonomous bot targeting. Keep neutral
   NPC/faction combat intact. PvP permissions and helpful-spell permissions must agree.
3. Guild-based keep capture/claim and guard/door/siege allegiance; DF access and safe ports.
4. Persistent merit rewards and the existing timed guild bonus UI, then new combat blessings
   and the DF shrine. Test restart, objective loss, membership changes and duplicate awards.
5. Back up and deploy only while the selected game is stopped; test two accounts in-game.

Relative scope: basic mixed-realm co-op is the smallest part; reliable region-based guild
warfare and objective allegiance are substantial changes; new guild blessing mechanics add
another feature layer. Keep this work separate from the currently installed class build
until the rule choices are settled and a tested build is ready.

## Implemented hybrid mode

The `hybrid_coop_pvp` server property selects `HybridCoopRules` at rules creation. Its
code default is false, so ordinary installations retain their original rules. It requires
a restart; the selected install keeps its Normal server type so existing native death
handling treats PvP deaths as RvR without adding PvE XP/con penalties.

Active warfare boundaries, verified against the packaged world:

- Albion old frontiers: zones 11, 12, 14, 15 in region 1 only.
- Midgard old frontiers: zones 111, 112, 113, 115 in region 100 only.
- Hibernia old frontiers: zones 210, 211, 212, 214 in region 200 only.
- New Frontiers 163; Cathal Valley 165; Summoner's Hall 233; Passage of Conflict 244;
  Darkness Falls 249; battleground regions 234–242 and classic BG regions 250–253.
- All other locations retain cooperative player relationships. The broad IsFrontier
  flag on regions 1/100/200 is deliberately ignored.

Groups, guilds, alliances and battle groups are friendly. Two guildless, unrelated
players are enemies inside warfare areas. Helpful spells cannot assist an opposing team
from the cooperative side of a boundary. Pet/subpet/bomb/siege controllers use the same
relationship rules. Core immunity/peace/GM protections remain; portal keep areas and
explicit safe areas block attacks on both sides. Native duels remain available.
Spell impacts recheck hostile allegiance/location, and hostile DoTs stop when no longer
legal; neutral-monster PvE keeps the original path. Color handling uses per-viewer
friend/enemy realm values so enemy guilds of the same racial realm can appear hostile.
Use `/coop` to check whether your current location is cooperative or a warfare area.

Keep guards, doors and components use guild/alliance allegiance. Unclaimed capturable
keeps are hostile to all teams; portal keeps are protected. Defeating a capturable lord
resets the keep through its native path and claims it for the human winner's guild when
the existing guild claim limit permits. Guildless winners cannot retain guild ownership.
The existing claim limit is preserved. Manual claims support mixed-realm guilds; claims
are permitted in BGs and the selected installation requires only one nearby player.
Existing guilds, ownership, ranks, characters, inventories and rewards are not reset.
Autonomous bots retain their existing realm-based campaign goals; this mode does not add
an autonomous guild-war planning system or manufacture new guilds for bots.

Enable in the selected stopped test installation, using its standard backup installer:

    python source/tools/stormforged/install.py artifacts/stormforged-playable --enable-coop-pvp --apply

Without `--apply` this previews changes. The installer validates frontier IDs/names and
known BG regions, prepares a private database, checks stopped processes, backs up changed
files and verifies installed hashes. Later Stormforged updates preserve the mode property.
The enable step changes only mode, BG-claim and solo-claim properties, not keep ownership.
A fresh/old played world with different zone IDs is rejected until reviewed.

Acceptance with two normal player accounts (GM immunity intentionally prevents PvP):

1. At a home town, confirm different-realm grouping, trade, buffs/heals and no hostile damage.
2. In DF and each frontier/BG type, confirm unrelated players can fight even in the same realm.
3. Group or join the same guild/alliance: attacks and bomb/AoE damage must stop; healing works.
4. Try a pet, a commander subpet and a placed bomb, then move either owner/body across a safe
   boundary. Confirm late damage/DoTs stop and outside heals cannot assist an opposing team.
5. Check portal keeps and release/teleport immunity; verify `/coop` describes each location.
6. Capture an eligible keep with a guild, check guard/door allegiance for owner, grouped guest
   and enemy guild, then restart and verify ownership persists.

Automated tests cover rules, teams, controller trees, boundaries, core attack gating,
late damage/heal checks, keep allegiances, factory/DF opt-in and idempotent boundary-validated
installation. They do not replace a two-client check of combat, colors and keep capture.

## Cross-realm capital travel

Existing LiveTeleporter and InlandTeleporter NPCs offer the other two capitals while
hybrid mode is enabled. This includes Master Visur in Camelot, Stor Gothi Annark in
Jordheim, and Channeler Glasny in Tir na Nog. Foreign-realm characters can interact
with these teleporters, so the return journey is available too.

Click [Camelot], [Jordheim] or [Tir na Nog]. Whispering the capital name or Albion,
Midgard, or Hibernia also selects its capital. The destination comes from that realm's
existing canonical Teleport row, with the normal region/zone validation and portal
spell pipeline. Combat and relic restrictions remain. No NPC or destination rows are
created or moved; original non-hybrid menus and realm restrictions remain intact.
`/tc` continues to return you to your character's own realm exchange.
