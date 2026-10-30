"""Sluaghbinder pet spell changes requested by the owner (2026-09-29).

  Zombie Magician  59031 Rotting Gloom Blast : visual only -> Eldritch "Void Bolt"
                   (client effect 4552: void-ball projectile, no blue caster
                   waves). Damage, type, target, range and cast time unchanged.
  Zombie Priest    59038 Priest's Mending    : heals 20% more (120 -> 144, pet
                   level scaling keeps it +20% at every level 32-50), single
                   target instead of the whole group.
                   59037 Miasma of Renewal   : single target instead of group.
                   Buffs (59036, 59039) untouched.
  Dullahan         59071 Withering Mark      : single target (radius 350 -> 0).

The pet AI already picks the owner / itself / an injured group member for
single-target ("Realm") heals. Run with the server STOPPED. Idempotent; prints
before/after and refuses to run if a row is not in the expected starting state.

usage: python pet_spell_changes.py <path-to-opendaoc.sqlite3.db>
"""
import shutil
import sqlite3
import sys
from pathlib import Path

CHANGES = [
    # spell id, column, expected old value, new value
    (59031, "ClientEffect", 2506, 4552),
    (59038, "Value", 120.0, 144.0),
    (59038, "Target", "Group", "Realm"),
    (59038, "Description", "A direct restorative prayer for the Sluaghbinder group.",
     "A direct restorative prayer that mends one ally."),
    (59037, "Target", "Group", "Realm"),
    (59037, "Description", "A restorative miasma heals the Sluaghbinder group over time.",
     "A restorative miasma heals one ally over time."),
    (59071, "Radius", 350, 0),

    # ---- Balance pass (2026-09-29) --------------------------------------
    # Pet spells scale linearly with pet level (pet = 88% of owner level, so
    # these are the values at owner 50 / pet 44). Pet max HP grows slightly
    # faster than linear, so a heal sized as a share of pet HP stays close to
    # flat across the priest's owner-level range 32-50.
    #   Priest's Mending : 240 at 50 (owner 32: 153, 40: 191, 45: 213)
    #                      ~9-11% of a same-level guardian/dullahan, ~11-13% of
    #                      priest/sturdy HP, ~15-20% of a player.
    #   Miasma of Renewal: 45 every 3 s for 15 s = 225 at 50 (owner 32: 143).
    (59038, "Value", 144.0, 240.0),
    (59037, "Value", 35.0, 45.0),

    # User-requested balance (2026-09-29): both priest heals obey normal
    # melee interruption. Only the zombie priest template uses these two.
    (59037, "Uninterruptible", 1, 0),
    (59038, "Uninterruptible", 1, 0),

    # Sluagh Covenant Cairnheart ranks (player / gamebot cast on their pet).
    # Stored as HealthRegenBuff they only added to natural regeneration, which
    # a pet in combat ticks every 30 s at half strength: about 0.6 HP/s at 50.
    # Now a real instant heal-over-time: every 3 s for 15 s, 20 s recast,
    # own effect group so it never collides with other classes' regen buffs.
    #   rank (level)     per tick  total   pet HP at that owner level
    #   Pulse (18)          30      150     ~480-640
    #   Mending (26)        45      225     ~640-990
    #   Rekindling (34)     65      325     ~930-1,400
    #   Resurgence (42)     90      450     ~1,270-1,900
    #   Rebirth (50)       125      625     ~1,730-2,550  (42 HP/s while active)
]

CAIRNHEART = {59065: (5.0, 30.0, 5), 59066: (8.0, 45.0, 7), 59067: (12.0, 65.0, 9),
              59068: (17.0, 90.0, 12), 59069: (23.0, 125.0, 15)}
for _sid, (_old, _new, _power) in CAIRNHEART.items():
    CHANGES += [
        (_sid, "Type", "HealthRegenBuff", "HealOverTime"),
        (_sid, "Duration", 60, 15),
        (_sid, "Frequency", 0, 30),
        (_sid, "RecastDelay", 0, 20),
        (_sid, "Value", _old, _new),
        (_sid, "Power", 0, _power),
        (_sid, "EffectGroup", 71, 59065),
        (_sid, "Description",
         "Instantly grants the raised pet cairn-bound health regeneration for 60 seconds.",
         f"Instantly wraps the raised pet in cairn warmth, healing {int(_new)} every 3 seconds for 15 seconds."),
        (_sid, "Message1", "You feel a calmness come over you.", "Cairn warmth knits your wounds."),
    ]


# Values a later installer owns; this script leaves them as they are.
#   59031 ClientEffect 4560: black-purple Sun Blast (tools/pet-art/install_void_sun.py)
SUPERSEDED = {(59031, "ClientEffect"): {4560}}


def main():
    db = Path(sys.argv[1])
    backup = db.with_name(db.name + ".before-pet-spell-changes")
    if not backup.exists():
        src = sqlite3.connect(db)
        dst = sqlite3.connect(backup)
        src.backup(dst)
        dst.close(); src.close()
        print(f"backup: {backup}")
    # A column may be changed in stages (e.g. 120 -> 144 -> 240); what matters
    # is its final value. Any earlier stage is an accepted starting point.
    final, accepted = {}, {}
    for sid, col, old, new in CHANGES:
        final[(sid, col)] = new
        accepted.setdefault((sid, col), set()).update((old, new))
    con = sqlite3.connect(db)
    todo = []
    for (sid, col), new in final.items():
        cur = con.execute(f"SELECT {col} FROM Spell WHERE SpellID = ?", (sid,)).fetchone()
        if cur is None:
            raise SystemExit(f"spell {sid} missing")
        if cur[0] == new:
            continue
        if cur[0] in SUPERSEDED.get((sid, col), ()):
            print(f"{sid} {col}: {cur[0]!r} is managed by a later installer; leaving it")
            continue
        if cur[0] not in accepted[(sid, col)]:
            raise SystemExit(f"{sid} {col}: unexpected value {cur[0]!r}; not changing anything")
        todo.append((sid, col, cur[0], new))
    with con:
        for sid, col, old, new in todo:
            print(f"{sid} {col}: {old!r} -> {new!r}")
            con.execute(f"UPDATE Spell SET {col} = ? WHERE SpellID = ?", (new, sid))
    for sid in sorted({c[0] for c in CHANGES}):
        print(con.execute("SELECT SpellID, Name, Type, Target, Radius, CastTime, Value, Damage, ClientEffect "
                          "FROM Spell WHERE SpellID = ?", (sid,)).fetchone())
    print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])


if __name__ == "__main__":
    main()
