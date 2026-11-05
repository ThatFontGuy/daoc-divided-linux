# Launcher realm boards: initial investigation

Investigated 2026-10-29. Planning only; no runtime files or player databases changed.

## Intended experience

A persistent, VN-inspired forum inside the launcher. The actual autonomous gamebots post under their own names, argue with other bots, tease players, share advice, ask questions, and reply when the player joins a thread. Threads survive restarts and become part of this world's history.

Suggested boards:

- Realm War: fight reports, rivalries, keep battles, congratulations, and trash talk across realms.
- Class and Hunting Help: leveling spots, terminology, trainers, equipment discussions, and questions.
- Tavern: introductions, guild chatter, bot questions, and general conversation.

Use a compact old-forum presentation: board index, topic/author/replies/last-post columns, numbered posts, quotes, signatures, and unread markers. Start with a native Windows Forms tab, matching the existing launcher dependencies. VN-inspired appearance and original writing; no dependency on an external forum service.

## Confirmed source foundations

Paths below are relative to the Source repository.

| Existing code | What it provides | Proposed use |
|---|---|---|
| `source/tools/OfflineDaoc.Launcher/MainForm.cs`, tab construction around line 562 | Windows Forms tabs, including Living Server and Realm Records | Add a Boards control alongside the existing tabs |
| `source/tools/OfflineDaoc.Launcher/HeraldPage.cs` | Read-only world queries and generated static Herald HTML | Reference for world summaries; static HTML alone cannot accept replies |
| `source/server/GameServer/bots/autonomous/AutonomousBotPersonality.cs` | Bot personality system | Stable writing style and participation preferences |
| `source/server/GameServer/bots/autonomous/AutonomousLivingServer.Memory.cs` | Memories of grouping, resurrection, abuse, and player familiarity | Friendly, neutral, or annoyed replies where a recorded relationship exists |
| `source/server/GameServer/bots/autonomous/AutonomousLivingServerStore.cs` | Persistent memories, named nemeses, firsts, and batched persistence | Source evidence for rivalries and a persistence pattern |
| `source/server/GameServer/bots/autonomous/AutonomousLivingServer.Events.cs` | Level and realm-rank events, firsts, reactions | Queue occasional milestone threads |
| `source/server/GameServer/bots/autonomous/AutonomousChatIntentModel.cs` | Rule-based and small statistical intent classification | Candidate routing for player replies; requires forum-specific evaluation |
| `source/server/GameServer/bots/autonomous/AutonomousChatKnowledge.cs` | Answers about terminology and world content | Ground helpful replies in implemented game information |
| `source/server/GameServer/bots/autonomous/AutonomousChatLiveAnswers.cs` | Current hunting and frontier answers | Candidate live-world advice, adapted to forum context |
| `docs/bot-voices/` | Existing original chat writing and voice design | Tone reference; write new forum-length content |

No interactive board implementation was found in the launcher or Living Server files inspected. This is a targeted investigation, not a full repository audit.

The local Source and Source-livingserver copies both contain Living Server systems. Their README/known-issues text still calls the release Beta 1.0. That does not establish which 1.1 binaries are installed in the player's active game folder. Confirm the active install and compare its build provenance before implementation or deployment.

## Recommended design

Keep board storage in a dedicated per-install SQLite file, with versioned migrations. This separates forum history and launcher posting from the busy world database. The server is the authority for bot posts and replies. The launcher can display saved threads and submit player posts while the game server is stopped; bots answer when the server next runs. Do not invent simulated gameplay during downtime.

Use explicit author kinds and stable IDs: real player character, autonomous gamebot, or system. Companion bots and temporary group helpers are excluded initially. Preserve display-name snapshots so historical posts remain readable if a bot disappears. Local single-player identity selection should be based on the install's characters; remote friend posting needs authenticated transport and is separate scope.

Suggested records:

- Threads: ID, board, title, creator, created time, last-post time, locked state.
- Posts: ID, thread ID, optional quoted/replied-to post ID, author kind and stable ID, display name, realm, body, created time, originating event key.
- Read state: local reader ID, thread ID, last-read post.
- Generation jobs: trigger/event key, target thread, eligible speakers, due time, attempts, completion status.
- Participation state: per-bot cooldown and recent topics, so restarts do not produce bursts.

Enforce unique event/job keys, transactional job completion and post insertion, bounded busy retries, parameterized queries, body limits, and schema compatibility. Capture immutable event data on the game thread; perform database work on a background worker. UI refresh and posting should also run off the UI thread. Existing LivingServerTable is a useful reference, not an assumed drop-in store for a second database.

## Posting and response behavior

Start threads from a small mix of real events and authored discussion prompts. A bot's kill boast must refer to a recorded fight; a rez thank-you must refer to a real interaction. Add replies from involved bots and occasional observers whose knowledge is plausible. Avoid giving every bot exact knowledge of every fight or current enemy position.

Choose speakers using personality, realm, class, guild, prior interactions, and current thread participation. Distinguish a confident boast from factual advice. Date live-world answers so an old post does not appear to describe the current frontier.

Player free text should be accepted, quoted, and retained. For the first version, classify supported topics and produce original authored responses with thread context and explicit entity references. Existing chat is not a generative language model; it will not support unrestricted conversation automatically. Unknown questions need an honest response or another bot asking for clarification, with no fabricated build advice. Optional local language-model support could follow behind the same response interface, but should not be necessary for the first release.

Let bots ask questions, let players answer, and schedule a relevant acknowledgement or follow-up. Track pending questions and the post being answered; replying only to the latest line would lose context. Permit disagreement and rival callbacks without allowing a thread to loop forever.

Proposed initial tuning, to be tested: 1–3 opening threads per simulated hour across all boards, 2–5 bot replies per ordinary discussion, individual posting cooldowns, a global budget, and finite follow-ups after player replies. Never force the player to wait through an artificial delay before their own post appears. Offer activity and banter intensity settings and a switch for personal callouts.

Example original thread shape:

> Realm War — "that bridge belongs to mid now"
>
> Winning bot: "nice charge, shame about the landing. same bridge tomorrow?"
>
> Defeated rival: "bring fewer healers and we can talk"
>
> Player: "you had twice our numbers"
>
> Observer bot: "both of you ran past the caster on the hill btw"

The combat details would be filled only from captured evidence. Advice threads should likewise use the actual server's rules and content, including its custom classes.

## Implementation sequence

1. Confirm the active 1.1 installation and intended source branch. Inspect event hooks, identity lifecycle, and save/export policy in that branch.
2. Build the standalone store and launcher Boards tab: browse, create thread, reply, quote, unread state, and persistence while stopped. Use an isolated fixture database for development.
3. Add server processing of new player posts with supported help topics and bot questions. Cover reply targeting, deduplication, bounded scheduling, and shutdown recovery.
4. Add event-backed rivalries, milestone posts, personality-specific voices, and bot-to-bot exchanges. Keep actual gameplay decisions independent of forum banter initially.
5. Verify launcher responsiveness, SQLite contention/recovery, restart behavior, deleted/renamed characters, disabled features, stale advice, and unknown player questions. Check UI at supported display scaling. Test on a copied install before any deployment.
6. Add forum history to the explicit private-save/backup policy and exclude it from clean public releases. Do not publish player-written posts, names, or private history in packages.

## Investigation boundaries

No server was started, no launcher was deployed, and no played database was queried or modified. No builds or tests were run because this change adds a planning document only. Existing unrelated local changes were left intact.
