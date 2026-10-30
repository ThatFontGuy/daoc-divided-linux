"""Seed the experimental, player-only Sluaghbinder into the isolated test DB.

This script is intentionally scoped to ``new class test``.  It is idempotent,
backs up the target database before changing it, and only adds rows identified
by the Sluaghbinder class/spec/line IDs plus the two Tir na nOg flavor NPCs.
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "runtime" / "data" / "opendaoc.sqlite3.db"
BACKUP_PATH = ROOT / "runtime" / "data" / "opendaoc-before-sluaghbinder.sqlite3.db"

CLASS_ID = 63

# Sluaghbinder has three automatic core lines and three optional lines that
# become trainable when the Acolyte promotes at level 5.  The names of the
# original core lines are intentionally preserved; changing them breaks the
# spell-book identity the player already sees.
CORE_HOST = "Sluagh Host"
CORE_ROT = "Abhartach's Rot"
CORE_CAIRN = "Cairn Oath"
TREE_A = "Dullahan's Bulwark"
TREE_B = "Abhartach's Bane"
# Life drains play the naburite drinker's drain animation (stock effect 10079).
DRAIN_EFFECT = 10079
# Abhartach's Bane DoTs play the hrimthursa seer's Plague Spores cloud (stock effect 3425),
# so they look different from the baseline Abhartach's Rot DoT (511).
BANE_DOT_EFFECT = 3425
TREE_C = "Sluagh Covenant"
# TREE_B remains the stable internal key and display name for the trainable
# scythe/disease path.  CORE_ROT is the separate automatic baseline line and
# is hidden from the trainer.
TREE_B_DISPLAY = TREE_B
EPIC_LINE = "Sluaghbinder's Legacy"
EPIC_LINE_LEGACY_DISPLAY = "Epic Spells"
CORE_LINE_KEYS = (CORE_HOST, CORE_ROT, CORE_CAIRN)
ADVANCED_TREE_KEYS = (TREE_A, TREE_B, TREE_C)
SPEC_KEYS = CORE_LINE_KEYS + ADVANCED_TREE_KEYS
LINE_KEYS = SPEC_KEYS + (EPIC_LINE,)
LEGACY_TREE_KEYS = ("Dullahan's Bulwark", "Abhartach's Bane", "Sluagh Covenant", "Cairn Oath")
OLD_LINE_KEYS = tuple(dict.fromkeys(CORE_LINE_KEYS + LINE_KEYS + LEGACY_TREE_KEYS + (EPIC_LINE_LEGACY_DISPLAY,)))
CAREER_KEY = "SluaghbinderCareer"
MOB_IDS = ("sluaghbinder_trainer_tir_na_nog", "sluaghbinder_bound_wisp_tir_na_nog")

# Existing class-63 style rows are retained, but their trainable line is
# moved to the correct Sluaghbinder tree.  Do this by the stable base style
# IDs rather than by the old text, so reseeding also repairs an earlier seed.
BLUNT_STYLE_IDS = tuple(range(260, 275))
SHIELD_STYLE_IDS = tuple(range(221, 230))
SCYTHE_STYLE_IDS = tuple(range(385, 400))

# The class-63 scythe rows were copied from the Valewalker style table when
# the experimental class was first seeded.  Keep their IDs, openings,
# damage and effects intact, but give them Sluaghbinder-specific names so the
# trainer and style tooltips no longer expose Valewalker terminology.
SCYTHE_STYLE_NAMES = {
    385: "Cairn Reaping",
    386: "Barrow Sweep",
    387: "Sluagh Hook",
    388: "Rothollow Arc",
    389: "Bone-Chill Edge",
    390: "Gravefire",
    391: "Cairnward Slash",
    392: "Abhartach's Harvest",
    393: "Mirebound Snare",
    394: "Barrow Aegis",
    395: "Frostwound",
    396: "Cairn Bastion",
    397: "Plaguebrand",
    398: "Sluagh's Severance",
    399: "Dullahan's Reaping",
}

# The classic client reads the spell tooltip identity as a signed 16-bit
# value.  The previous seed used the 590xx server SpellID as TooltipId; those
# values are valid database keys but arrive negative to the client, so every
# hover request came back blank.  Keep the custom tooltip identities in a
# client-safe, unused range and keep them unique per custom spell.  The icon
# remains independent, so the original rot icon can be retained.
CLIENT_TOOLTIP_START = 29000
UNHOLY_AURA = {
    "Message1": "You are surrounded by an unholy aura.",
    "Message2": "{0} is surrounded by an unholy aura.",
    "Message3": "Your unholy aura wears off.",
    "Message4": "{0}'s unholy aura wears off.",
}
CLIENT_TOOLTIP_LIMIT = 32767

# The pet templates live in the isolated database because they are world data,
# not source-created NPCs.  These percentages are consumed by
# GameSummonedPet.SetStats (they are not flat stat values).  Keeping the table
# here makes a clean reseed restore the same role profiles instead of bringing
# back the old Constitution=20 zero-health bug.
PET_TEMPLATE_PROFILES = {
    60170001: (105, 110, 85, 90, 65, ""),
    60170002: (110, 115, 90, 95, 65, ""),
    60170003: (115, 120, 95, 100, 65, ""),
    60170004: (80, 90, 120, 110, 140, "59031"),
    60170005: (125, 145, 100, 95, 80, "1073;59032;59033"),
    # The priest is deliberately a melee healer/buffer.  Its direct-damage
    # bolt is not part of the role; the Zombie Magician alone carries 59031.
    60170006: (90, 115, 110, 105, 125, "59036;59037;59038;59039"),
    60170007: (130, 130, 115, 110, 135, "59032;59033;59070;59071;59072;59073;59076"),
}

# These are private client model registrations copied 1:1 from the stock
# corpse meshes.  They keep later texture/mesh edits isolated from ordinary
# Corpse and Headless Corpse mobs.
PET_MODEL_PROFILES = {
    60170005: "2494",  # private 1:1 Corpse / Decaying Marshman copy
    60170007: "2495",  # private 1:1 Headless Corpse copy
    60170006: "2072",  # private haunting badh copy (ghastly healer, install_ghastly_healer_art.py); stock badh is 1885
}

# The ghastly healer wears the world badh's robe pieces (slot, object, colour).
# Its right hand keeps the Celtic Dirk; it never gets the badh's staff.
GHASTLY_HEALER_ROBES = ((22, 2950, 66), (23, 2952, 66), (25, 2922, 0), (27, 2949, 66), (28, 2948, 66))

# Sizes are client-visible bytes. Both pets were 50: the requested Defender
# increase rounds 66.5 to 67, while Dullahan's 50% increase is exactly 75.
PET_SIZE_PROFILES = {
    60170005: "67",
    60170007: "75",
}

# NPC equipment models are objects.csv IDs, not items.csv/NIF IDs. Object 862
# points to the native chain morningstar item 268. Dullahan deliberately has
# no offhand; its old Celtic Tower shield object 1153 is removed below.
# Zombie Defender uses its original Tower
# Shield object 79; the later Great Grave shield object 1138 was reverted.
# Zombie Priest uses Hibernia's Celtic Dirk object 454; its old offhand
# buckler row is removed below. The internal template key stays stable.
# The old values 268/84 were gloves/boots, and 2898 was a tent object.
PET_EQUIPMENT_PROFILES = {
    "sluagh_zombie_guardian_mace_shield": {10: 14, 11: 79},
    "sluagh_zombie_priest_mace_buckler": {10: 454},
    "sluagh_cairn_dullahan_flail_shield": {10: 862},
}

# Existing client effect 54 is the one-handed crush dark-purple glow. It is
# an equipment appearance only, not a proc or a combat-stat modification.
PET_EQUIPMENT_EFFECT_PROFILES = {
    ("sluagh_cairn_dullahan_flail_shield", 10): 54,
}


def copy_backup() -> None:
    if BACKUP_PATH.exists():
        return
    source = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    target = sqlite3.connect(BACKUP_PATH)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def clone_spell(conn: sqlite3.Connection, template_id: int, spell_id: int, spell_key: str,
                name: str, description: str, line: str | None, line_level: int = 1,
                **changes: object) -> None:
    template = conn.execute("SELECT * FROM Spell WHERE SpellID = ?", (template_id,)).fetchone()
    if template is None:
        raise RuntimeError(f"Missing spell template {template_id}")
    columns = [row[1] for row in conn.execute("PRAGMA table_info(Spell)")]
    values = dict(zip(columns, template))
    # Keep the template's ClientEffect.  SpellID is a server/database key,
    # not a client effect animation ID; sending a new 590xx ID makes the
    # classic client reject the effect (and can crash on cast).
    # TooltipId is the client's per-spell identity.  A custom spell must use a
    # unique value in the classic client's signed-short range.  Reusing the
    # template icon makes ranks with the same icon resolve to one another,
    # while using the 590xx server ID makes the client treat the identity as a
    # negative number and produces a blank hover.  Pick the first free safe
    # identity for this Sluaghbinder spell.  Callers can still override it for
    # a deliberate legacy identity.
    tooltip_id = changes.pop("TooltipId", None)
    if tooltip_id is None and 59000 <= spell_id < 59100:
        tooltip_id = CLIENT_TOOLTIP_START + (spell_id - 59000)
        while tooltip_id <= CLIENT_TOOLTIP_LIMIT and conn.execute(
            "SELECT 1 FROM Spell WHERE TooltipId = ? LIMIT 1", (tooltip_id,)
        ).fetchone() is not None:
            tooltip_id += 1
        if tooltip_id > CLIENT_TOOLTIP_LIMIT:
            raise RuntimeError("No client-safe Sluaghbinder tooltip identities are available")
    if tooltip_id is None:
        tooltip_id = values.get("TooltipId", values.get("Icon", 0))
    values.update({
        "SpellID": spell_id,
        "Name": name,
        "Description": description,
        "TooltipId": int(tooltip_id),
        "Spell_ID": spell_key,
        "LastTimeRowUpdated": "2000-01-01 00:00:00",
    })
    values.update(changes)
    conn.execute(
        f"INSERT INTO Spell ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        [values[column] for column in columns],
    )
    if line is not None:
        conn.execute(
            "INSERT INTO LineXSpell (LineName, SpellID, Level, LastTimeRowUpdated, LineXSpell_ID) VALUES (?, ?, ?, ?, ?)",
            (line, spell_id, line_level, "2000-01-01 00:00:00", f"{line}_{spell_id}"),
        )


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Target database not found: {DB_PATH}")
    copy_backup()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        # Only remove rows owned by this isolated feature, making reruns safe.
        conn.execute("DELETE FROM ClassXSpecialization WHERE ClassID = ?", (CLASS_ID,))
        old_placeholders = ",".join("?" for _ in OLD_LINE_KEYS)
        spec_delete_keys = (CAREER_KEY, *OLD_LINE_KEYS)
        spec_delete_placeholders = ",".join("?" for _ in spec_delete_keys)
        conn.execute(
            f"DELETE FROM SpecXAbility WHERE Spec IN ({spec_delete_placeholders})",
            spec_delete_keys,
        )
        conn.execute(
            f"DELETE FROM LineXSpell WHERE LineName IN ({old_placeholders})",
            OLD_LINE_KEYS,
        )
        conn.execute(
            f"DELETE FROM SpellLine WHERE KeyName IN ({old_placeholders})",
            OLD_LINE_KEYS,
        )
        conn.execute(
            f"DELETE FROM Specialization WHERE KeyName IN ({spec_delete_placeholders})",
            spec_delete_keys,
        )
        conn.execute("DELETE FROM Spell WHERE Spell_ID LIKE 'Sluaghbinder_%'")
        for mob_id in MOB_IDS:
            conn.execute("DELETE FROM Mob WHERE Mob_ID = ?", (mob_id,))

        now = "2000-01-01 00:00:00"
        specs = [
            (CAREER_KEY, "Sluaghbinder Career", 0, "Sluaghbinder class career.", "DOL.GS.LiveCareerSpecialization", now),
            # Baseline lines are real class abilities, not spendable trainer
            # paths.  UntrainableSpecialization keeps them in GetSpecList so
            # their spells still arrive automatically as the player levels,
            # while PacketLib's trainer filter omits them.
            (CORE_HOST, CORE_HOST, 5255, "Core bound-dead summoning and basic pet bond magic.", "DOL.GS.UntrainableSpecialization", now),
            (CORE_ROT, CORE_ROT, 731, "Core rot and wasting magic that every Sluaghbinder learns.", "DOL.GS.UntrainableSpecialization", now),
            (CORE_CAIRN, CORE_CAIRN, 1701, "Core cairn-bound protection magic that every Sluaghbinder learns.", "DOL.GS.UntrainableSpecialization", now),
            (TREE_A, TREE_A, 1701, "RPG-themed tank path: scale armor, one-hand-and-shield styles, taunts, and protection tools.", None, now),
            (TREE_B, TREE_B_DISPLAY, 731, "Disease, damage-over-time, life-drain, and scythe combat path.", None, now),
            (TREE_C, TREE_C, 5255, "Advanced undead pet bonds and pet-enhancement path; no weapon styles.", None, now),
            (EPIC_LINE, EPIC_LINE, 9407, "Reserved for the first Sluaghbinder epic quest reward.", None, now),
        ]
        conn.executemany(
            "INSERT INTO Specialization (KeyName,Name,Icon,Description,Implementation,LastTimeRowUpdated) VALUES (?,?,?,?,?,?)",
            specs,
        )
        conn.executemany(
            "INSERT INTO SpellLine (KeyName,Name,Spec,IsBaseLine,ClassIDHint,LastTimeRowUpdated) VALUES (?,?,?,?,?,?)",
            [
                (CORE_HOST, CORE_HOST, CORE_HOST, 1, CLASS_ID, now),
                (CORE_ROT, CORE_ROT, CORE_ROT, 1, CLASS_ID, now),
                (CORE_CAIRN, CORE_CAIRN, CORE_CAIRN, 1, CLASS_ID, now),
                (TREE_A, TREE_A, TREE_A, 0, CLASS_ID, now),
                (TREE_B, TREE_B_DISPLAY, TREE_B, 0, CLASS_ID, now),
                (TREE_C, TREE_C, TREE_C, 0, CLASS_ID, now),
                # Deliberately not attached to ClassXSpecialization.  The
                # level-10 epic quest will attach this line when implemented.
                (EPIC_LINE, EPIC_LINE, EPIC_LINE, 0, CLASS_ID, now),
            ],
        )

        # The first three entries are baseline identity lines.  They are not
        # trained: their spells are granted as the character levels.  The next
        # three are real spendable lines unlocked by promotion at level 5.
        # The epic line is intentionally absent until its quest is completed.
        class_specs = [
            (CAREER_KEY, -1000),
            ("CharacterStyleUserCareer", -100),
            ("CharacterQuickcastUserCareer", -100),
            (CORE_HOST, -3),
            (CORE_ROT, -2),
            (CORE_CAIRN, -2),
            (TREE_A, -3),
            (TREE_B, -2),
            (TREE_C, -1),
        ]
        conn.executemany(
            "INSERT INTO ClassXSpecialization (ClassID,SpecKeyName,LevelAcquired,LastTimeRowUpdated) VALUES (?,?,?,?)",
            [(CLASS_ID, key, level, now) for key, level in class_specs],
        )

        # Restore the class career's missing armor permission and keep shield
        # proficiency as an intrinsic class capability.  Shield levels 1/2/3
        # correspond to small/medium/large shields in the stock item check;
        # putting all three ranks on the career prevents the tank tree from
        # showing redundant "learn to use a shield" abilities.  HibArmor
        # level 4 is Hibernian scale; without this row the promoted character
        # loses armor access because the custom career has no data abilities.
        # Bulwark then contains only trainable tank tools (blunt weapon access,
        # guard/protect ranks and intercept), rather than equipment gates.
        spec_abilities = [
            (CAREER_KEY, 1, "HibArmor", 4),
            (CAREER_KEY, 1, "Evade", 1),
            (CAREER_KEY, 1, "Shield", 1),
            (CAREER_KEY, 5, "Shield", 2),
            (CAREER_KEY, 10, "Shield", 3),
            (TREE_A, 1, "Weaponry: Blunt", 0),
            (TREE_A, 10, "Guard", 1),
            (TREE_A, 30, "Guard", 2),
            (TREE_A, 20, "Protect", 1),
            (TREE_A, 40, "Protect", 2),
            (TREE_A, 25, "Intercept", 0),
            (TREE_B, 1, "Weaponry: Scythe", 0),
        ]
        conn.executemany(
            "INSERT INTO SpecXAbility (Spec,SpecLevel,AbilityKey,AbilityLevel,ClassId,LastTimeRowUpdated) VALUES (?,?,?,?,?,?)",
            [(spec, level, ability, ability_level, 0, now) for spec, level, ability, ability_level in spec_abilities],
        )

        # Move only the isolated class-63 style rows.  No other class's
        # Blunt, Shield, or Scythe styles are changed.
        placeholders = ",".join("?" for _ in BLUNT_STYLE_IDS)
        conn.execute(
            f"UPDATE Style SET SpecKeyName=? WHERE ClassId=? AND ID IN ({placeholders})",
            (TREE_A, CLASS_ID, *BLUNT_STYLE_IDS),
        )
        placeholders = ",".join("?" for _ in SHIELD_STYLE_IDS)
        conn.execute(
            f"UPDATE Style SET SpecKeyName=? WHERE ClassId=? AND ID IN ({placeholders})",
            (TREE_A, CLASS_ID, *SHIELD_STYLE_IDS),
        )
        placeholders = ",".join("?" for _ in SCYTHE_STYLE_IDS)
        conn.execute(
            f"UPDATE Style SET SpecKeyName=? WHERE ClassId=? AND ID IN ({placeholders})",
            (TREE_B, CLASS_ID, *SCYTHE_STYLE_IDS),
        )
        for style_id, style_name in SCYTHE_STYLE_NAMES.items():
            conn.execute(
                "UPDATE Style SET Name=? WHERE ClassId=? AND ID=?",
                (style_name, CLASS_ID, style_id),
            )

        # Core pet ranks.  These names, icons and rank levels are the original
        # Sluaghbinder set; do not replace them with generic "Bound Spirit"
        # labels.  The custom templates provide the role-specific meshes and
        # the normal -88% pet level scaling.
        pet_ranks = [
            (59000, 1, 2, 9401, 60170001, "Raise Shambling Dead"),
            (59001, 4, 45, 9402, 60170002, "Raise Walking Dead"),
            (59002, 7, 45, 9403, 60170003, "Raise Sturdy Zombie"),
            (59003, 12, 45, 9404, 60170004, "Raise Zombie Magician"),
            (59004, 20, 45, 9405, 60170005, "Raise Zombie Guardian"),
            (59005, 32, 45, 9406, 60170006, "Raise Ghastly Healer"),
            (59030, 45, 45, 9407, 60170007, "Raise Dullahan"),
        ]
        for spell_id, level, cap, template, npc_template, name in pet_ranks:
            clone_spell(
                conn, template, spell_id, f"Sluaghbinder_{spell_id}", name,
                f"Raises a {name[6:].lower()} to serve the Sluaghbinder.",
                CORE_HOST, level, Damage=-88.0, Value=float(cap),
                LifeDrainReturn=npc_template, Type="SummonDruidPet",
                PackageID="Sluaghbinder_Pet",
            )
        # The first two pet buffs are core identity spells.  The remaining
        # enhancements require the optional pet specialization.
        for spell_id, level, value, template, name in [
            (59006, 5, 12, 10041, "Sluaghbound Might"),
            (59007, 15, 19, 10043, "Cairnward Resolve"),
        ]:
            clone_spell(
                conn, template, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Binds the Sluaghbinder's raised dead with Celtic spirit-might.", CORE_HOST, level,
                Value=float(value), PackageID="Sluaghbinder_Pet",
            )

        for spell_id, level, value, template, name in [
            (59008, 25, 26, 10044, "Sluagh's Graveward"),
            (59009, 35, 34, 10046, "Cairnheart Renewal"),
            (59010, 45, 45, 10047, "Dullahan's Covenant"),
        ]:
            clone_spell(
                conn, template, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Calls a deeper Celtic covenant to strengthen the Sluaghbinder's raised dead.", TREE_C, level,
                Value=float(value), PackageID="Sluaghbinder_Pet",
            )

        # The Covenant is a real pet-enhancement specialization, not just a
        # second copy of the core strength/constitution buff.  Each family
        # uses a stock Pet-target spell handler and normal level progression;
        # the values are deliberately moderate so a player can combine one
        # rank from each family without bypassing the ordinary pet scaling.
        covenant_pet_families = [
            # Dexterity/quickness improves attack cadence and casting without
            # changing the pet's role or adding a new combat script.
            (891, [
                (59045, 8, 14, "Sluaghbound Swiftness"),
                (59046, 16, 24, "Sluaghbound Quickening"),
                (59047, 24, 35, "Sluaghbound Haste"),
                (59048, 32, 47, "Sluaghbound Fleetness"),
                (59049, 40, 60, "Sluaghbound Windstep"),
            ], "Binds the raised dead with quicksilver Sluagh motion."),
            # Spec AF is the same native armor-factor handler used by the
            # existing Underhill pet buff.  Target=Pet is intentional: the
            # player casts it on the controlled pet, not on themself.
            (60018, [
                (59050, 10, 20, "Cairnhide"),
                (59051, 18, 31, "Cairnplate"),
                (59052, 26, 44, "Cairnwarding"),
                (59053, 34, 58, "Cairnwall"),
                (59054, 42, 72, "Cairnfortress"),
            ], "Shelters the raised dead beneath a layered cairn ward."),
            # Flat damage-add values are handled by the stock DamageAdd
            # handler and scale with the pet's weapon interval/variance.
            (10200, [
                (59055, 12, 1.8, "Sluagh Thorn"),
                (59056, 20, 3.5, "Sluagh Spines"),
                (59057, 28, 5.5, "Sluagh Fangs"),
                (59058, 36, 7.8, "Sluagh Blades"),
                (59059, 44, 10.5, "Sluagh Wrath"),
            ], "Sets the raised dead's blows with a measured grave sting."),
            # Combat speed is kept separate from Dexterity/Quickness so the
            # player may choose the enhancement that fits the pet's role.
            (861, [
                (59060, 15, 5, "Dullahan's Pace"),
                (59061, 23, 7, "Dullahan's Stride"),
                (59062, 31, 9, "Dullahan's Charge"),
                (59063, 39, 12, "Dullahan's Gallop"),
                (59064, 47, 15, "Dullahan's Onrush"),
            ], "Drives the raised dead forward with a gravebound battle pace."),
            # Health regeneration is a native Pet-target effect and gives the
            # line a sustain option without adding a new heal AI or a flat
            # full-health reset.
            (11539, [
                (59065, 18, 5, "Cairnheart Pulse"),
                (59066, 26, 8, "Cairnheart Mending"),
                (59067, 34, 12, "Cairnheart Rekindling"),
                (59068, 42, 17, "Cairnheart Resurgence"),
                (59069, 50, 23, "Cairnheart Rebirth"),
            ], "Restores the raised dead through a slow, cairn-bound renewal."),
        ]
        for template, ranks, description in covenant_pet_families:
            for spell_id, level, value, name in ranks:
                changes = {
                    "Value": float(value),
                    "Target": "Pet",
                    "Range": 1500,
                    "Radius": 350,
                    "PackageID": "Sluaghbinder_Covenant",
                }
                if template == 60018:
                    changes.update({
                        "CastTime": 3.0,
                        "Duration": 1200,
                        "EffectGroup": 1,
                        "SpellGroup": 0,
                    })
                elif template == 10200:
                    changes.update({
                        "Damage": float(value),
                        "Radius": 350,
                        "Range": 1500,
                        "EffectGroup": 40,
                        "SpellGroup": 40,
                        "DamageType": 14,
                    })
                elif template == 11539:
                    changes.update({
                        "Duration": 60,
                        "Frequency": 0,
                        "EffectGroup": 71,
                        "SpellGroup": 11539,
                    })
                clone_spell(
                    conn, template, spell_id, f"Sluaghbinder_{spell_id}", name,
                    description, TREE_C, level, **changes,
                )

        # These are pet-internal abilities, not player toolbar spells.  Keep
        # their stable IDs because the isolated pet templates reference them.
        # The previous trainable-tree seed deleted these rows, which is why
        # the magician/guardian/priest pets lost their abilities.
        for spell_id, template, name, description, changes in [
            (59031, 2506, "Rotting Gloom Blast", "A rotting blast that damages the target.", {
                "Target": "Enemy", "Range": 1500, "Power": 8, "CastTime": 2.6,
                "Damage": 45.0, "DamageType": 11, "Type": "DirectDamage", "SpellGroup": 59031,
            }),
            (59032, 3154, "Cairn Boneplate", "Hardens the zombie guardian with a lasting bone ward.", {
                "Target": "Self", "CastTime": 3.0, "Type": "SpecArmorFactorBuff", "Duration": 1200,
                "Pulse": 1, "RecastDelay": 8, "Value": 75.0, "EffectGroup": 2,
            }),
            (59033, 651, "Guardian Hunger", "The zombie guardian has a chance to drain life on hit.", {
                "ClientEffect": 11232, "Icon": 651, "Target": "Self", "Type": "OffensiveProc",
                "Duration": 65535, "Frequency": 25, "Value": 59034.0, "SpellGroup": 59033,
            }),
            (59034, 651, "Guardian Lifesteal", "Drains life from the guardian's target.", {
                "Target": "Enemy", "Range": 1500, "Damage": 42.0, "DamageType": 10,
                "Type": "Lifedrain", "RecastDelay": 4, "Value": -30.0, "LifeDrainReturn": 30,
                "SpellGroup": 59034, "SharedTimerGroup": 30, "ClientEffect": DRAIN_EFFECT,
            }),
            (59036, 10308, "Grave Renewal", "Renews the Sluaghbinder group's health beneath a unique cairn ward.", {
                # Group targeting lets the controlled priest apply the same
                # unique regeneration effect to itself, its owner, and the
                # owner's companion party.  Effect/SpellGroup are unique so
                # ordinary class regeneration buffs do not overwrite it.
                "Target": "Group", "Range": 2000, "Radius": 350, "CastTime": 2.0,
                "Type": "HealthRegenBuff", "Duration": 1200, "Frequency": 50,
                "Value": 10.0, "EffectGroup": 59036, "SpellGroup": 59036,
            }),
            (59037, 4412, "Miasma of Renewal", "A restorative miasma heals the Sluaghbinder group over time.", {
                "Target": "Group", "Range": 2000, "Power": 8, "CastTime": 3.0,
                "Type": "HealOverTime", "Duration": 15, "Frequency": 30, "Value": 35.0,
                "SpellGroup": 59037,
            }),
            (59038, 715, "Ghastly Mending", "A mournful keen that mends one ally.", {
                "Target": "Group", "Range": 1500, "Power": 20, "CastTime": 3.0,
                "Type": "Heal", "Value": 95.0, "SpellGroup": 59038,
            }),
            (59039, 4761, "Cairn Benediction", "Blesses the Sluaghbinder group with strength and constitution.", {
                "Target": "Group", "Range": 1000, "CastTime": 3.0, "Type": "StrengthConstitutionBuff",
                "Duration": 1200, "Radius": 350, "Value": 25.0, "EffectGroup": 204,
                "SpellGroup": 59039,
            }),
            # Dullahan's melee-hybrid kit.  These are pet-internal abilities:
            # no DD is granted here, and every harmful instant has a real
            # reuse timer so the pet cannot spam a single effect every tick.
            (59070, 60008, "Dullahan's Grave Rot", "An instant rot that lingers on the target.", {
                "Target": "Enemy", "Range": 1500, "Power": 8, "CastTime": 0.0,
                "Damage": 45.0, "DamageType": 14, "Type": "DamageOverTime", "Duration": 24,
                "Frequency": 40, "RecastDelay": 10, "SpellGroup": 59070, "EffectGroup": 59070,
            }),
            (59071, 961, "Dullahan's Withering Mark", "Weakens an enemy's strength and constitution.", {
                "Target": "Enemy", "Range": 1500, "Power": 8, "CastTime": 0.0,
                "Type": "StrengthConstitutionDebuff", "Duration": 24, "Value": 35.0,
                "RecastDelay": 10, "EffectGroup": 59071, "SpellGroup": 59071,
            }),
            (59072, 651, "Dullahan's Blood Tithe", "Instantly drains life from the target.", {
                "Target": "Enemy", "Range": 1500, "Power": 10, "CastTime": 0.0,
                "Damage": 50.0, "DamageType": 10, "Type": "Lifedrain", "Value": -35.0,
                "LifeDrainReturn": 35, "RecastDelay": 10, "SpellGroup": 59072, "ClientEffect": DRAIN_EFFECT,
                "SharedTimerGroup": 30,
            }),
            (59073, 621, "Dullahan's Fading Step", "Slows an enemy's dexterity and quickness.", {
                "Target": "Enemy", "Range": 1500, "Power": 8, "CastTime": 0.0,
                "Type": "DexterityQuicknessDebuff", "Duration": 24, "Value": 30.0,
                "RecastDelay": 10, "EffectGroup": 59073, "SpellGroup": 59073,
            }),
            (59076, 4765, "Dullahan's Graveplate", "Binds the Dullahan in a high-tier cairn armor ward.", {
                "Target": "Self", "Range": 0, "Power": 0, "CastTime": 3.0,
                "Type": "StrengthConstitutionBuff", "Duration": 1200, "Value": 75.0,
                "RecastDelay": 8, "EffectGroup": 59076, "SpellGroup": 59076,
            }),
        ]:
            clone_spell(
                conn, template, spell_id, f"Sluaghbinder_{spell_id}", name,
                description, None, PackageID="Sluaghbinder_Pet_Spells", **changes,
            )

        # Eight instant-cast rot ranks.  The server's existing DOT handler
        # applies the normal duration/frequency ticks; only the initial cast is
        # instant.  Keep the short four-second reuse timer so these spells
        # cannot be recast continuously (matching the intended suppression-
        # style instant-drain cadence).
        for spell_id, level, damage, power, name in [
            (59011, 1, 5, 2, "Abhartach's Rot"),
            (59012, 5, 9, 3, "Abhartach's Lesser Rot"),
            (59013, 10, 14, 4, "Abhartach's Blight"),
        ]:
            clone_spell(
                conn, 511, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Inflicts a wasting rot that damages the target over time.",
                CORE_ROT, level, CastTime=0.0, Damage=float(damage),
                Power=power, Icon=511, RecastDelay=4,
                PackageID="Sluaghbinder_Rot",
            )

        for spell_id, level, damage, power, name in [
            (59014, 16, 21, 6, "Abhartach's Withering"),
            (59015, 22, 30, 8, "Abhartach's Plague"),
            (59016, 29, 41, 10, "Abhartach's Deep Plague"),
            (59017, 36, 55, 12, "Abhartach's Grave Rot"),
            (59018, 44, 72, 14, "Abhartach's Final Rot"),
        ]:
            clone_spell(
                conn, 511, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Inflicts a wasting rot that damages the target over time.",
                TREE_B, level, CastTime=0.0, Damage=float(damage),
                Power=power, Icon=511, RecastDelay=4, ClientEffect=BANE_DOT_EFFECT,
                PackageID="Sluaghbinder_Rot",
            )

        # Five instant life-drain ranks share the normal life-drain handler.
        for spell_id, level, damage, power, drain, name, icon in [
            (59019, 8, 12, 4, 30, "Steal Vitality", 651),
            (59020, 18, 24, 6, 35, "Drink Vitality", 652),
            (59021, 28, 42, 8, 40, "Siphon Vitality", 653),
            (59022, 38, 68, 10, 50, "Plunder Vitality", 654),
            (59023, 48, 100, 12, 60, "Devour Vitality", 655),
        ]:
            clone_spell(
                conn, 651, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Instantly damages the target and returns part of the damage as health.",
                TREE_B, level, CastTime=0.0, Damage=float(damage),
                Power=power, LifeDrainReturn=drain, Icon=icon, RecastDelay=4,
                ClientEffect=DRAIN_EFFECT, SharedTimerGroup=59019,
                PackageID="Sluaghbinder_Rot",
            )

        # Core Cairn Oath protection.  Higher wards remain trainable in the
        # tank path, while the original Cairn names and stock icons stay intact.
        for spell_id, level, value, template, name in [
            (59024, 1, 14, 1701, "Cairn Skin"),
            (59025, 10, 24, 1704, "Cairn Guard"),
        ]:
            clone_spell(
                conn, template, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Hardens the Sluaghbinder with a cairn-bound ward.",
                CORE_CAIRN, level, CastTime=3.0, Value=float(value),
                PackageID="Sluaghbinder_Cairn", **UNHOLY_AURA,
            )

        for spell_id, level, value, template, name in [
            (59027, 30, 51, 3535, "Cairn Vigor"),
            (59028, 40, 63, 3536, "Cairn Fortitude"),
            (59029, 48, 75, 3537, "Cairn Oath"),
        ]:
            clone_spell(
                conn, template, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Hardens the Sluaghbinder with a lasting cairn-bound ward.",
                TREE_A, level, CastTime=3.0, Value=float(value),
                PackageID="Sluaghbinder_Bulwark",
                Message1="You are filled with the power of the cairn!",
                Message2="{0} is filled with the power of the cairn!",
            )

        # Barrow Deflection replaced Cairn Ward (an armor buff the core Cairn
        # line already outclassed): a modest self parry buff that lets the
        # Sluaghbinder parry without the Parry specialization.  A fresh seed
        # uses the stock Shield of Zeal icon; tools/pet-art/
        # install_bulwark_update.py installs the custom icon on a world.
        for spell_id, level, value, name in [
            (59026, 20, 4.0, "Barrow Deflection"),
            (59110, 32, 6.0, "Barrow Riposte"),
            (59111, 44, 8.0, "Barrow Wardblade"),
        ]:
            clone_spell(
                conn, 1706, spell_id, f"Sluaghbinder_{spell_id}", name,
                f"Barrow-cold reflexes guide the Sluaghbinder's weapon, increasing its chance to parry by {value:g}% for 20 minutes.",
                TREE_A, level, CastTime=3.0, Value=value, Type="ParryBuff",
                SpellGroup=59026, EffectGroup=59026, PackageID="Sluaghbinder_Bulwark",
                TooltipId=29000 + (spell_id - 59000),
                Message1="Barrow-cold reflexes guide your weapon.",
                Message2="{0} moves with barrow-cold reflexes.",
                Message3="Your barrow-cold reflexes fade.",
                Message4="{0}'s barrow-cold reflexes fade.",
            )

        # Tank-tree taunts use the server's native Taunt handler.  Their hate
        # values follow the Paladin taunt progression; they cost only power and
        # share one 15 s recast across every rank (Paladin: 30 s, free).
        for spell_id, level, value, power, name in [
            (59040, 5, 5.2, 2, "Dullahan's Challenge"),
            (59041, 15, 17.1, 6, "Dullahan's Rebuke"),
            (59042, 25, 38.7, 10, "Dullahan's Provocation"),
            (59043, 35, 55.6, 14, "Dullahan's Fury"),
            (59044, 45, 72.0, 18, "Dullahan's Command"),
        ]:
            clone_spell(
                conn, 1070, spell_id, f"Sluaghbinder_{spell_id}", name,
                "Taunts an enemy to focus its attention on the Sluaghbinder.",
                TREE_A, level, CastTime=0.0, Value=float(value), Power=power,
                RecastDelay=15, SharedTimerGroup=59040, PackageID="Sluaghbinder_Bulwark",
            )
        

        # A quiet trainer and non-aggressive flavor spirit in Tir na nOg
        # (region 201).  Keep Muirenn on the exterior roadside grass, rather
        # than inside the nearby house; this is also the stable location used
        # by the earlier Sluaghbinder world seed so later spell reseeds cannot
        # put her back indoors.
        trainer = conn.execute(
            "SELECT * FROM Mob WHERE Mob_ID = 'c4e71392-ed9a-4d21-84da-77051908bffb'"
        ).fetchone()
        if trainer is None:
            raise RuntimeError("Reference Tir na nOg trainer row is missing")
        mob_columns = [row[1] for row in conn.execute("PRAGMA table_info(Mob)")]
        trainer_values = dict(zip(mob_columns, trainer))
        trainer_values.update({
            "ClassType": "DOL.GS.Trainer.SluaghbinderTrainer",
            "TranslationId": "",
            "Name": "Muirenn",
            "Suffix": "",
            "Guild": "Sluaghbinder Trainer",
            "X": 28700,
            "Y": 36080,
            "Z": 7366,
            "Heading": 2048,
            "Region": 201,
            "Model": 294,
            "Size": 50,
            "Level": 50,
            "Realm": 3,
            "EquipmentTemplateID": "SluaghbinderMuirennBlack",
            "ItemsListTemplateID": None,
            "NPCTemplateID": -1,
            "Race": 10,
            "Gender": 2,
            "IsCloakHoodUp": 1,
            "VisibleWeaponSlots": 34,
            "Flags": 0,
            "AggroLevel": 0,
            "AggroRange": 0,
            "RespawnInterval": 0,
            "Brain": "",
            "PathID": "",
            "RoamingRange": 0,
            "Mob_ID": MOB_IDS[0],
        })
        conn.execute(
            f"INSERT INTO Mob ({','.join(mob_columns)}) VALUES ({','.join('?' for _ in mob_columns)})",
            [trainer_values[column] for column in mob_columns],
        )

        flavor_values = dict(trainer_values)
        flavor_values.update({
            "ClassType": "DOL.GS.GameNPC",
            "Name": "bound sluagh wisp",
            "Guild": "",
            "X": 28790,
            "Y": 36080,
            "Z": 7366,
            "Heading": 2048,
            "Model": 966,
            "Race": 2000,
            "Size": 25,
            "NPCTemplateID": -1,
            "Gender": 0,
            "IsCloakHoodUp": 0,
            "VisibleWeaponSlots": 0,
            "Level": 1,
            "EquipmentTemplateID": None,
            "Flags": 0,
            "AggroLevel": 0,
            "AggroRange": 0,
            "RespawnInterval": 0,
            "Mob_ID": MOB_IDS[1],
        })
        conn.execute(
            f"INSERT INTO Mob ({','.join(mob_columns)}) VALUES ({','.join('?' for _ in mob_columns)})",
            [flavor_values[column] for column in mob_columns],
        )

        # Apply the role profiles to the existing isolated pet templates.  The
        # templates are installed by the client/data setup, so do not create
        # unrelated world rows here; a missing custom row is reported clearly.
        for template_id, (strength, constitution, dexterity, quickness, intelligence, spells) in PET_TEMPLATE_PROFILES.items():
            updated = conn.execute(
                "UPDATE NpcTemplate SET Strength=?, Constitution=?, Dexterity=?, Quickness=?, Intelligence=?, Spells=? WHERE TemplateId=?",
                (strength, constitution, dexterity, quickness, intelligence, spells, template_id),
            ).rowcount
            if updated != 1:
                raise RuntimeError(f"Sluaghbinder pet template {template_id} is missing")

        for template_id, model in PET_MODEL_PROFILES.items():
            updated = conn.execute(
                "UPDATE NpcTemplate SET Model=? WHERE TemplateId=?",
                (model, template_id),
            ).rowcount
            if updated != 1:
                raise RuntimeError(f"Sluaghbinder pet template {template_id} is missing")

        for template_id, size in PET_SIZE_PROFILES.items():
            updated = conn.execute(
                "UPDATE NpcTemplate SET Size=? WHERE TemplateId=?",
                (size, template_id),
            ).rowcount
            if updated != 1:
                raise RuntimeError(f"Sluaghbinder pet template {template_id} is missing")

        for equipment_template, slots in PET_EQUIPMENT_PROFILES.items():
            for slot, model in slots.items():
                updated = conn.execute(
                    "UPDATE NPCEquipment SET Model=? WHERE TemplateID=? AND Slot=?",
                    (model, equipment_template, slot),
                ).rowcount
                if updated != 1:
                    raise RuntimeError(
                        f"Sluaghbinder pet equipment {equipment_template} slot {slot} is missing"
                    )

        # No offhand on Zombie Priest. Deleting only this pet's slot is
        # idempotent, so reseeding cannot bring its old buckler back.
        conn.execute(
            "DELETE FROM NPCEquipment WHERE TemplateID=? AND Slot=11",
            ("sluagh_zombie_priest_mace_buckler",),
        )
        for slot, model, color in GHASTLY_HEALER_ROBES:
            conn.execute("DELETE FROM NPCEquipment WHERE TemplateID=? AND Slot=?",
                         ("sluagh_zombie_priest_mace_buckler", slot))
            conn.execute(
                "INSERT INTO NPCEquipment (TemplateID, Slot, Model, Color, Effect, Extension, Emblem, "
                "LastTimeRowUpdated, NPCEquipment_ID) VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?)",
                ("sluagh_zombie_priest_mace_buckler", slot, model, color, "2000-01-01 00:00:00",
                 f"sluagh_zombie_priest_mace_buckler:{slot}"),
            )

        # Dullahan carries only its glowing main-hand flail. Remove the actual
        # offhand item, not merely its appearance. This engine cannot block
        # without an equipped shield, so use the endgame Necromancer pet's
        # shieldless defense profile instead: 0 block / 10 parry / 10 evade.
        # The template key remains unchanged so existing summons still bind.
        conn.execute(
            "DELETE FROM NPCEquipment WHERE TemplateID=? AND Slot=11",
            ("sluagh_cairn_dullahan_flail_shield",),
        )
        updated = conn.execute(
            "UPDATE NpcTemplate SET BlockChance=0, ParryChance=10, EvadeChance=10 "
            "WHERE TemplateId=60170007",
        ).rowcount
        if updated != 1:
            raise RuntimeError("Dullahan pet template 60170007 is missing")

        for (equipment_template, slot), effect in PET_EQUIPMENT_EFFECT_PROFILES.items():
            updated = conn.execute(
                "UPDATE NPCEquipment SET Effect=? WHERE TemplateID=? AND Slot=?",
                (effect, equipment_template, slot),
            ).rowcount
            if updated != 1:
                raise RuntimeError(
                    f"Sluaghbinder pet equipment {equipment_template} slot {slot} is missing"
                )

        # Keep the visible pet names aligned with the player spell names.  The
        # final template used to carry the internal placeholder "cairn" label;
        # it is simply Dullahan to the player.
        for template_id, pet_name in {
            60170001: "shambling dead",
            60170002: "walking dead",
            60170003: "sturdy zombie",
            60170004: "zombie magician",
            60170005: "zombie guardian",
            60170006: "ghastly healer",
            60170007: "dullahan",
        }.items():
            conn.execute("UPDATE NpcTemplate SET Name=? WHERE TemplateId=?", (pet_name, template_id))

        conn.commit()
        check = conn.execute("PRAGMA quick_check").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"SQLite quick_check failed: {check}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # The epic-service installer owns the five quest-gated service spells.
    # Reseeding must not leave their LineXSpell rows pointing at missing Spell
    # rows (or duplicate the old display line), so cleanly re-apply that small
    # idempotent installer after the Sluaghbinder core seed is committed.
    import runpy
    epic_installer = runpy.run_path(str(ROOT / "tools" / "Add-SluaghbinderEpicSpells.py"))
    epic_installer["install"](DB_PATH)

    print(f"Seeded isolated Sluaghbinder test DB: {DB_PATH}")
    print(f"Backup: {BACKUP_PATH}")


if __name__ == "__main__":
    main()
