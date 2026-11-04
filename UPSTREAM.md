# Upstream

- DividedRealms: https://github.com/rambodolphin13/DividedRealms, snapshot `e7155da` (2026-10-30, 0.38-dev7), merged up to `084a433` (2026-11-04, DR-dev-0.1a, the Fishing Update).
  History is squashed upstream; later commits will build on this one.
- Removed from the snapshot: `source/new-client/` only (World Workshop editor kept).
- Lineage: OpenDAoC -> OfflineDAoC (shadowofze) -> DividedRealms.
- Left out of the 0.1a merge on purpose: the Passport Desk (bringing a character to a friend's world; Windows launcher feature),
  `OfflineDaoc.TestClient`, the Windows launcher changes, and `source/new-client`. `PASSPORT_DESK_PORT_OFFSET` stays in
  BaseServer because a test uses it.
- Our own bot death-pose change was dropped: upstream's `ShowDeadToViewers` / `ShowStandingToViewers` cover it.
