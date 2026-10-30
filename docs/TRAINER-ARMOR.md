# Class trainer armor (Eve of Darkness reference)

October 23, 2026. Owner request: every class trainer wears its class's newer armor set, like the expansion trainers imported from Eve of Darkness ([EXPANSION-TRAINERS.md](EXPANSION-TRAINERS.md)). Modern test world only.

## What changed

`source/tools/trainer_armor.py` (preview by default, `--apply` to write):

- **Advanced-class trainers (all 47 classes, including the three Mauler realms):** each wears its class's epic armor template, for example `thane`, `armsman`, `mauler_alb`. These templates already existed locally, and every one matches Eve of Darkness [db-public e0e6ed28](https://github.com/Eve-of-Darkness/db-public/tree/e0e6ed280f6239d2c40d4d0a57b244dafdc2056e) slot for slot (model, color, extension, effect, emblem).
  - For most classes the template's armor models are exactly the class's epic items (for example Armsman "Stalwart Arm", Healer "Valhalla Touched", Valkyrie "Battle Maiden's"). Cloth casters match on the epic robe.
  - **Exception:** Thane, Berserker, Blademaster, Hunter and Minstrel, and the Sorcerer and Friar vests, use newer models (around 3300–3390) that no local item uses. Eve of Darkness's own epic items for those classes keep the older models, the same as ours. Owner decision (October 23, 2026): keep the newer Eve of Darkness trainer look for these classes.
- **Base-class trainers (Fighter, Acolyte, Viking, Seer and so on):** unchanged. They have no epic armor (owner decision). A first pass gave 8 of them Eve of Darkness's one-off templates; those 8 were reverted (backup `pre-trainer-armor-base-revert-20261023-195556.sqlite3.db`).
- **Custom trainers (Stormforged, Pendragon):** unchanged.
- **NPC templates:** when a trainer has an NPC template that carries equipment, the template's gear replaces the Mob's at load. Those templates are updated too, but only when no other kind of NPC uses them. 25 changed, each belonging only to its trainer.

Result: 390 advanced-class trainers managed, 319 Mob rows and 25 NPC templates changed. Reapplying changes nothing. Only Mob and NpcTemplate equipment fields are written, and no saves, inventories or other NPCs are touched. The script refuses to run while the test server is listening, and it backs up the database first (`pre-trainer-armor-20261023-195413-705156.sqlite3.db`). The report `artifacts/modern-client-test/trainer-armor-report.json` comes from that first run and still lists the 8 reverted base-class rows.

**Eve of Darkness epic items compared (not changed):** of our 277 epic armor items, 271 exist there (the 6 missing are the custom Sluaghbinder set). Their models are identical. Differences are 18 item names, 12 bonus types (for example the Minstrel and Sorcerer vests' second bonus is type 151 there and 9 here), a few bonus values, and 6 extensions. These are player items, left for a separate decision.

Tests: `source/tools/tests/test_trainer_armor.py` (4 definition-only tests). No server build or client patch is needed. The armor models (about 2900–3600) are in the bundled 1.130 client; the old 1.65-era client in Classic/Stormforged may lack them, which is one reason those installs are untouched. Not yet checked in game.

Note: Codex's expansion-trainer installer refuses `--rollback` once the database has changed after its install, so restoring that import now needs this pass's backup or a manual revert.
