"""Add offline Master Level content to an explicitly selected world. Preview unless --apply.

Every class may follow any of the eight paths: the paths are class-0 careers acquired at level 50,
inserted in a fixed order because a character's chosen path is stored as an index into that order.
Only package-owned spell rows are replaced; player saves are not touched.
Stop the selected installation before applying.
"""
import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import uuid

PACKAGE = "OfflineDAoC.MasterLevels.v1"
# Never reorder: GamePlayer.MLLine is an index into this list.
PATHS = ("Banelord", "Battlemaster", "Convoker", "Perfecter", "Sojourner", "Spymaster", "Stormlord", "Warlord")
FIRST_ID = 63000
TOOLTIP_BASE = 21000

# Storms: ground target within 1500, 350 radius, 3 s cast, ten minutes, pulse every 4 s, 30 s reuse, no power.
STORM = {"Target": "Self", "Range": 1500, "Radius": 350, "CastTime": 3, "Duration": 600, "Frequency": 40, "RecastDelay": 30}
SPELLS = {
    "Stormlord": [
        dict(STORM, Name="Dazzling Array", Type="DazzlingArray", ClientEffect=7209, Value=15),
        dict(Name="Vacuum Vortex", Type="VacuumVortex", ClientEffect=7227, Target="Self", Range=1500, CastTime=1, RecastDelay=10),
        dict(STORM, Name="Enervating Gas", Type="EnervatingGas", ClientEffect=7272, Value=15),
        dict(STORM, Name="Inebriating Fumes", Type="InebriatingFumes", ClientEffect=7257, Value=60),
        dict(STORM, Name="Mental Siphon", Type="MentalSiphon", ClientEffect=7302, Value=10),
        dict(Name="Focusing Winds", Type="FocusingWinds", ClientEffect=7205, Target="Self", Duration=60, RecastDelay=120),
        dict(STORM, Name="Choking Vapors", Type="ChokingVapors", ClientEffect=7222, Value=60),
        dict(STORM, Name="Sense Dulling Cloud", Type="SenseDullingCloud", ClientEffect=7304, Value=60),
        dict(STORM, Name="Energy Tempest", Type="EnergyTempest", ClientEffect=7215, Damage=250, DamageType=12),
        dict(Name="Arcing Power", Type="ArcingPower", ClientEffect=7248, Target="Self", Radius=350, Duration=30, RecastDelay=60, Value=50),
    ],
}

# The other seven paths share one spell type; MasterLevelAbilities.cs holds their behaviour and bonus sizes.
# Shouts work around you; "Enemy"/"Realm" need a target; ground abilities are placed within Range.
def ml(name, effect, target="Self", **fields):
    return dict(fields, Name=name, Type="MasterLevelAbility", ClientEffect=effect, Target=target)


def ground(name, effect, **fields):
    return ml(name, effect, Range=fields.pop("Range", 1500), CastTime=fields.pop("CastTime", 3), **fields)


SPELLS.update({
    "Banelord": [
        ml("Zone of Unmana", 7261, Radius=700, Duration=30, RecastDelay=60),
        ml("Primal Agony", 7262, Radius=750, Damage=1500, RecastDelay=60),
        ml("Oppression", 7264, Radius=750, Duration=20, RecastDelay=60),
        ml("Inexorable Defeat", 7263, Radius=750, Duration=20, RecastDelay=60),
        ml("Tactical Insight", 7274, Radius=1000, Duration=30, RecastDelay=90),
        ml("Snaring Tendrils of Power", 7276, Radius=700, Value=50, Duration=15, RecastDelay=30),
        ml("Chaotic Power", 7287, Radius=1000, Duration=30, RecastDelay=90),
        ml("Agony Transmission", 7260, Radius=1000, Damage=3000, RecastDelay=300),
        ml("Demoralization", 7296, Radius=1000, Duration=30, RecastDelay=120),
        ml("Banestrike", 7306, Radius=1000, Duration=30, RecastDelay=120),
    ],
    "Battlemaster": [
        ml("Sapping Strike", 7232, "Enemy", Range=350, Damage=200, RecastDelay=15),
        ml("Faultfinder", 7267, "Enemy", Range=350, Damage=150, Duration=30, RecastDelay=30),
        ml("Power Leak", 7231, "Enemy", Range=350, Damage=150, RecastDelay=30),
        ml("Grapple", 7275, "Enemy", Range=350, Duration=10, RecastDelay=60),
        ml("Essence Flames", 7285, Radius=1500, Damage=12, Duration=300, RecastDelay=60),
        ml("Throw Weapon", 408, "Enemy", Range=1000, Damage=300, RecastDelay=15),
        ml("Essence Sear", 7290, "Enemy", Range=350, Duration=20, RecastDelay=60),
        ml("Bodyguard", 7352, "Realm", Range=1000, Duration=60, RecastDelay=60),
        ml("Essence Dampen", 7291, "Enemy", Range=350, Duration=20, RecastDelay=60),
        ml("Essence Shatter", 7292, "Enemy", Range=350, Damage=250, RecastDelay=60),
    ],
    "Convoker": [
        ground("Warding Crystal", 7268, Radius=350, Duration=600, Frequency=40, RecastDelay=60),
        ground("Prescience Node", 7271, Radius=1000, Duration=600, Frequency=40, RecastDelay=60),
        ground("Power Trap", 7252, Radius=350, Duration=600, Frequency=10, Damage=250, CastTime=2, RecastDelay=30),
        ground("Speedwarp", 7236, Radius=500, Duration=600, Frequency=20, RecastDelay=60),
        ground("Summon Warcrystal", 7238, Radius=1500, Duration=120, Damage=200, RecastDelay=120),
        ground("Battlewarder", 7250, Radius=350, Duration=60, Damage=350, CastTime=1, RecastDelay=120),
        ground("Dissonance Trap", 7254, Radius=350, Duration=600, Frequency=10, Damage=600, CastTime=2, RecastDelay=30),
        ml("Brittle Guard", 7249, Value=2000, Duration=600, RecastDelay=120),
        ml("Summoning Mastery", 7297, Radius=2000, Duration=600, RecastDelay=300),
        ground("Crystal Titan", 7234, Radius=400, Duration=120, Damage=400, RecastDelay=600),
    ],
    "Perfecter": [
        ml("Purify Vision", 7206, Radius=2000, RecastDelay=30),
        ml("Purging Wave", 7239, Radius=2000, RecastDelay=30),
        ground("Sphere of Rejuvenation", 7244, Radius=500, Duration=600, Frequency=40, Value=5, RecastDelay=60),
        ml("Greatness", 7242),
        ground("Font of Power", 7211, Radius=500, Duration=600, Frequency=40, Value=5, RecastDelay=60),
        ground("Determination Field", 7213, Radius=500, Duration=600, Frequency=40, RecastDelay=60),
        ml("Leaping Health", 7288, Radius=500, Value=50, Duration=30, RecastDelay=60),
        ml("Restore the Soul", 7246, "Realm", Range=1500, Value=50, CastTime=3, RecastDelay=60),
        ground("Dissonating Ward", 7309, Radius=500, Duration=600, Frequency=40, Damage=100, RecastDelay=60),
        ml("Rampant Healing", 7299, Radius=1500, Duration=30, RecastDelay=120),
    ],
    "Sojourner": [
        ml("Unburdened Warrior", 7243),
        ml("Unending Breath", 7226, Radius=2000, Duration=1800, RecastDelay=30),
        ml("Swift Passage", 7204, Radius=2000, Value=140, Duration=600, RecastDelay=30),
        ml("Unmake", 7284, RecastDelay=120),
        ml("Ancient Transmuter", 7235, Duration=120, CastTime=3, RecastDelay=300),
        ml("Gateway", 7201, CastTime=8, RecastDelay=60),
        ml("Resistance of the Ancients", 7278, Radius=2000, Duration=1200, RecastDelay=60),
        ml("Forceful Zephyr", 7229, "Enemy", Range=1500, RecastDelay=60),
        ml("Phase Shift", 7298, Value=5000, Duration=10, RecastDelay=300),
        ml("Mass Gateway", 7202, CastTime=15, RecastDelay=120),
    ],
    "Spymaster": [
        ml("Pickpocket", 7218),
        ground("Decoy", 7221, Range=2000, Radius=750, Duration=60, CastTime=2, RecastDelay=120),
        ml("Enduring Poison", 7281),
        ml("Sabotage", 7350, "Enemy", Range=1500, Duration=30, RecastDelay=60),
        ground("Tanglesnare", 7219, Radius=350, Duration=600, Frequency=10, Value=60, CastTime=2, RecastDelay=30),
        ground("Poisonspike", 7280, Radius=350, Duration=600, Frequency=10, Damage=120, CastTime=2, RecastDelay=30),
        ml("Lookout", 7351, Radius=1000, Duration=120, Frequency=20, RecastDelay=120),
        ground("Wrecking Rune", 7300, Radius=350, Duration=600, Frequency=10, Damage=800, RecastDelay=60),
        ml("Essence Flare", 7208, Radius=500, Duration=15, RecastDelay=120),
        ml("Blanket of Camouflage", 7207, Radius=1500, CastTime=3, RecastDelay=300),
    ],
    "Warlord": [
        ml("Iron Will", 7256),
        ml("Bolstering Battlecry", 7269, Radius=1500, RecastDelay=60),
        ml("Cowering Bellow", 7203, Radius=1000, Duration=15, RecastDelay=120),
        ml("Resilient Will", 7308, Radius=1500, Duration=30, RecastDelay=90),
        ml("Guided Strike", 7265, Radius=1500, Duration=30, RecastDelay=90),
        ml("Energizing Aura", 7277, Radius=1500, Duration=30, RecastDelay=90),
        ml("Cleansing Aura", 7259, Radius=1000, RecastDelay=60),
        ml("Defending Martyr", 7289, Radius=1500, Value=500, RecastDelay=300),
        ml("Leadership", 7295, Radius=1500, Duration=30, RecastDelay=120),
        ml("Warguard", 7307, Radius=1000, Duration=40, RecastDelay=300),
    ],
})

# Champion Levels: one path per realm, CL1-15, trained automatically (ChampionAbilities.cs).
# IDs 63100 + realm * 15 + CL - 1. Passives (CL1, 3, 5, 7, 9, 11, 13) hold their bonuses as permanent effects.
CHAMPION_FIRST_ID = 63100
CHAMPION_PATHS = ("ChampionAlbion", "ChampionMidgard", "ChampionHibernia")
CHAMPION_TOOLTIP_BASE = 21100
CHAMPION_SPELLS = {
    "ChampionAlbion": [
        ml("Knightly Vigor", 1457),
        ml("Lay on Hands", 3062, "Realm", Range=1500, Value=30, RecastDelay=120),
        ml("Avalonian Wards", 1475),
        ml("Smite", 1605, "Enemy", Range=1500, Damage=400, RecastDelay=30),
        ml("Squire's Endurance", 3131),
        ml("Purify", 3025, Duration=5, RecastDelay=300),
        ml("Chivalry", 1567),
        ml("Banner of Camelot", 5447, Radius=1500, Duration=120, RecastDelay=300),
        ml("Valor", 1456),
        ml("Judgement", 3379, Radius=500, Damage=200, RecastDelay=120),
        ml("Lionheart", 1455),
        ml("Holy Aegis", 1198, Value=3000, Duration=15, RecastDelay=180),
        ml("Grail Blessing", 3133),
        ml("Grace of Avalon", 3042, Radius=1500, Value=40, RecastDelay=180),
        ml("Excalibur", 1604, "Enemy", Range=1000, Damage=1000, Duration=30, RecastDelay=600),
    ],
    "ChampionMidgard": [
        ml("Jotun Blood", 2864),
        ml("Valhalla's Call", 3053, Value=30, RecastDelay=120),
        ml("Rune-Warded", 3167),
        ml("Frostbite Hurl", 156, "Enemy", Range=1500, Damage=400, RecastDelay=30),
        ml("Mead of Poetry", 4411),
        ml("Berserker's Break", 3025, Duration=5, RecastDelay=300),
        ml("Fury of the North", 3168),
        ml("Warhorn of Heimdall", 3537, Radius=1500, Duration=60, RecastDelay=300),
        ml("Odin's Eye", 3536),
        ml("Fimbulwinter", 271, Radius=500, Damage=200, RecastDelay=120),
        ml("Troll Hide", 3265),
        ml("Unyielding", 1198, Value=20000, Duration=15, RecastDelay=180),
        ml("Ravens' Insight", 4412),
        ml("Mead Hall", 3042, Radius=1500, Value=40, RecastDelay=180),
        ml("Ragnarok", 3528, Radius=700, Damage=300, Duration=20, RecastDelay=600),
    ],
    "ChampionHibernia": [
        ml("Blessing of Danu", 5007),
        ml("Healing Spring", 4884, "Realm", Range=1500, Value=30, RecastDelay=120),
        ml("Faerie Ward", 5078),
        ml("Spear of Lugh", 2575, "Enemy", Range=1500, Damage=400, Duration=15, RecastDelay=30),
        ml("Silver Branch", 4413),
        ml("Glamour Shift", 5077, Duration=5, RecastDelay=300),
        ml("Fianna's Craft", 4881),
        ml("Song of the Sidhe", 415, Radius=1500, Duration=60, RecastDelay=300),
        ml("Morrigan's Sight", 2573),
        ml("Glamour Mist", 466, Radius=500, RecastDelay=120),
        ml("Oakheart", 4883),
        ml("Shadowform", 7298, Duration=15, RecastDelay=180),
        ml("Cauldron of Dagda", 4882),
        ml("Rebirth Grove", 4884, Radius=1500, Value=40, RecastDelay=180),
        ml("Wings of the Morrigan", 2576, Radius=700, Damage=300, Duration=20, RecastDelay=600),
    ],
}

# The Ancient Transmuter sells arrows and poisons; like any merchant it also buys loot.
TRANSMUTER_LIST = "ML_transmuteritems"
TRANSMUTER_SOURCE = "MidThrowingArrowsPoisons"


def row_copy(db, table, source, changes):
    row = dict(source)
    for field in db.execute(f'PRAGMA table_info("{table}")'):
        name, kind, pk = field[1], field[2], field[5]
        if pk and "INT" in kind.upper():
            row.pop(name, None)
        elif pk:
            row[name] = str(uuid.uuid4())
    row.update(changes)
    if "LastTimeRowUpdated" in row:
        row["LastTimeRowUpdated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cols = ",".join('"' + k + '"' for k in row)
    db.execute(f'INSERT INTO "{table}" ({cols}) VALUES ({",".join("?" for _ in row)})', tuple(row.values()))


def source_row(db, table, where, args=()):
    row = db.execute(f'SELECT * FROM "{table}" WHERE {where} LIMIT 1', args).fetchone()
    if row is None:
        raise ValueError(f"Missing prerequisite {table}: {where}")
    return dict(row)


def seed(db):
    db.row_factory = sqlite3.Row
    for path in PATHS:
        spec = source_row(db, "Specialization", "KeyName=?", (path,))
        if spec["Implementation"] != "DOL.GS.LiveMasterLevelsSpecialization":
            raise ValueError(f"{path} is not a Master Level specialization")
        source_row(db, "SpellLine", "KeyName=?", (path,))
    for row in db.execute("SELECT SpellID,PackageID FROM Spell WHERE SpellID BETWEEN ? AND ?", (FIRST_ID, FIRST_ID + 99)):
        if row["PackageID"] != PACKAGE:
            raise ValueError(f"Spell ID collision: {row['SpellID']}")
    for row in db.execute("SELECT SpellID,PackageID FROM Spell WHERE TooltipId BETWEEN ? AND ?", (TOOLTIP_BASE, TOOLTIP_BASE + 99)):
        if row["PackageID"] != PACKAGE:
            raise ValueError(f"Tooltip collision: {row['SpellID']}")

    db.execute("DELETE FROM LineXSpell WHERE SpellID IN (SELECT SpellID FROM Spell WHERE PackageID=?)", (PACKAGE,))
    db.execute("DELETE FROM Spell WHERE PackageID=?", (PACKAGE,))
    db.execute(f"DELETE FROM ClassXSpecialization WHERE ClassID=0 AND SpecKeyName IN ({','.join('?' for _ in PATHS)})", PATHS)

    # The stock ML ability grants are empty stubs (no implementation); the rebuilt passives are spells.
    db.execute(f"DELETE FROM SpecXAbility WHERE Spec IN ({','.join('?' for _ in PATHS)})", PATHS)

    career = source_row(db, "ClassXSpecialization", "ClassID=0")
    for path in PATHS:
        row_copy(db, "ClassXSpecialization", career, {"ClassID": 0, "SpecKeyName": path, "LevelAcquired": 50})

    spell_base = source_row(db, "Spell", "SpellID=3508")
    link_base = source_row(db, "LineXSpell", "1=1")
    defaults = {"Target": "Self", "Range": 0, "Radius": 0, "Power": 0, "CastTime": 0, "Damage": 0, "DamageType": 0,
                "Duration": 0, "Frequency": 0, "Pulse": 0, "PulsePower": 0, "RecastDelay": 0, "Value": 0,
                "LifeDrainReturn": 0, "SpellGroup": 0, "EffectGroup": 0, "SubSpellID": 0, "SharedTimerGroup": 0,
                "MoveCast": 0, "Uninterruptible": 0, "IsFocus": 0, "Concentration": 0, "Message1": "", "Message2": "",
                "Message3": "", "Message4": ""}
    count = 0
    for index, path in enumerate(PATHS):
        for level, fields in enumerate(SPELLS.get(path, []), start=1):
            spell_id = FIRST_ID + index * 10 + level - 1
            data = dict(defaults, **fields)
            data.update({"SpellID": spell_id, "Spell_ID": f"masterlevel-{spell_id}", "Description": data["Name"],
                         "Icon": data["ClientEffect"], "PackageID": PACKAGE, "TooltipId": TOOLTIP_BASE + spell_id - FIRST_ID,
                         "SpellGroup": spell_id})
            row_copy(db, "Spell", spell_base, data)
            row_copy(db, "LineXSpell", link_base, {"LineName": path, "SpellID": spell_id, "Level": level})
            count += 1

    champions = seed_champions(db, spell_base, link_base, defaults, career)

    db.execute("DELETE FROM MerchantItem WHERE ItemListID=?", (TRANSMUTER_LIST,))
    for row in db.execute("SELECT * FROM MerchantItem WHERE ItemListID=?", (TRANSMUTER_SOURCE,)).fetchall():
        row_copy(db, "MerchantItem", row, {"ItemListID": TRANSMUTER_LIST})
    transmuter = db.execute("SELECT count(*) FROM MerchantItem WHERE ItemListID=?", (TRANSMUTER_LIST,)).fetchone()[0]
    return {"paths": list(PATHS), "spells": count, "built_paths": sorted(SPELLS), "transmuter_items": transmuter,
            "champion_spells": champions}


def seed_champions(db, spell_base, link_base, defaults, career):
    for row in db.execute("SELECT SpellID,PackageID FROM Spell WHERE SpellID BETWEEN ? AND ?", (CHAMPION_FIRST_ID, CHAMPION_FIRST_ID + 99)):
        if row["PackageID"] != PACKAGE:
            raise ValueError(f"Spell ID collision: {row['SpellID']}")
    spec_base = source_row(db, "Specialization", "KeyName='Stormlord'")
    line_base = source_row(db, "SpellLine", "KeyName='Stormlord'")
    names = {"ChampionAlbion": "Champion of Albion", "ChampionMidgard": "Champion of Midgard", "ChampionHibernia": "Champion of Hibernia"}
    db.execute(f"DELETE FROM ClassXSpecialization WHERE ClassID=0 AND SpecKeyName IN ({','.join('?' for _ in CHAMPION_PATHS)})", CHAMPION_PATHS)
    count = 0
    for realm_index, path in enumerate(CHAMPION_PATHS):
        db.execute("DELETE FROM Specialization WHERE KeyName=?", (path,))
        db.execute("DELETE FROM SpellLine WHERE KeyName=?", (path,))
        row_copy(db, "Specialization", spec_base, {"KeyName": path, "Name": names[path],
                 "Description": "Realm Champion abilities, trained automatically with each Champion Level.",
                 "Implementation": "DOL.GS.RealmChampionSpecialization"})
        row_copy(db, "SpellLine", line_base, {"KeyName": path, "Name": names[path], "Spec": path, "IsBaseLine": 0, "ClassIDHint": 0})
        row_copy(db, "ClassXSpecialization", career, {"ClassID": 0, "SpecKeyName": path, "LevelAcquired": 50})
        for level, fields in enumerate(CHAMPION_SPELLS[path], start=1):
            spell_id = CHAMPION_FIRST_ID + realm_index * 15 + level - 1
            data = dict(defaults, **fields)
            data.update({"SpellID": spell_id, "Spell_ID": f"champion-{spell_id}", "Description": data["Name"],
                         "Icon": data["ClientEffect"], "PackageID": PACKAGE,
                         "TooltipId": CHAMPION_TOOLTIP_BASE + spell_id - CHAMPION_FIRST_ID, "SpellGroup": spell_id})
            row_copy(db, "Spell", spell_base, data)
            row_copy(db, "LineXSpell", link_base, {"LineName": path, "SpellID": spell_id, "Level": level})
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = args.database.resolve(strict=True)
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
        if not args.apply:
            with sqlite3.connect(":memory:") as preview:
                source.backup(preview)
                print(json.dumps({"preview": True, **seed(preview)}, indent=2))
            return
        backup = path.with_name(path.name + ".before-masterlevels-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".bak")
        if backup.exists():
            raise FileExistsError(backup)
        with sqlite3.connect(backup) as out:
            source.backup(out)
    with sqlite3.connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        result = seed(db)
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    print(json.dumps({"backup": str(backup), **result}, indent=2))


if __name__ == "__main__":
    main()
