"""Add Stormforged content to an explicitly selected world. Preview unless --apply.

Only package-owned rows are replaced. Stock Thane content and player saves are not modified.
Backups use SQLite's backup API, not a file copy of a possibly live database.
Stop the selected installation before applying; the installer enforces that separately.
"""
import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import uuid

PACKAGE = "OfflineDAoC.Stormforged.v1"
CLASS = 64
CAREER = "StormforgedCareer"
TEMPLATE = 60171001
BOMB_TEMPLATE = 60171002
MENDER_TEMPLATE = 60171003
CASTER_TEMPLATE = 60171004
LEVELS = (1, 5, 10, 15, 20, 30, 40, 50)
# Highest stock Midgard healer/shaman buffs; private copies remove concentration.
MENDER_BUFF_SOURCES = (3168, 3187, 3176, 3157, 3244, 3278, 3284, 3238,
                       3365, 3298, 3100, 3228, 3231, 3234, 3287, 3290, 3293)
# The classic UseSpell packet identifies a spell by LINE + LEVEL, not SpellID.
# Different abilities must never share a level in the same line.
HEROIC_LINES = {62200: "AvatarOfThor", 62201: "Stormguard", 62202: "SecondThunder",
                62210: "Stormstep", 62211: "RideTheStorm", 62212: "ThunderRecall", 62213: "EyeOfTheStorm"}
SPELL_LINES = {0: "Stormbolt", 1: "Thunderclap", 2: "ChainLightning",
               3: "Stormheart", 5: "Stormsong", 7: "ThunderforgedWard",
               9: "Stormrest", 10: "StormboundElemental", 12: "LightningBomb",
               16: "Stormhammer", 18: "ReleaseStormClump"}


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
    # Reject collisions before deleting anything; all our IDs are stable across reseeds.
    for row in db.execute("SELECT SpellID,PackageID FROM Spell WHERE SpellID BETWEEN 62000 AND 62999"):
        if row["PackageID"] != PACKAGE:
            raise ValueError(f"Spell ID collision: {row['SpellID']}")
    for row in db.execute("SELECT TemplateId,PackageID FROM NpcTemplate WHERE TemplateId IN (?,?,?,?)", (TEMPLATE, BOMB_TEMPLATE, MENDER_TEMPLATE, CASTER_TEMPLATE)):
        if row["PackageID"] != PACKAGE:
            raise ValueError(f"Pet template collision: {row['TemplateId']}")
    if db.execute("SELECT 1 FROM ClassXSpecialization WHERE ClassID=? AND SpecKeyName NOT IN ('Sword','Hammer','Axe','Shields','Parry','Stealth',?, 'CharacterStyleUserCareer')", (CLASS, CAREER)).fetchone():
        raise ValueError("Class 64 is already in use")

    existing_ids = [r[0] for r in db.execute("SELECT SpellID FROM Spell WHERE PackageID=?", (PACKAGE,))]
    for spell_id in existing_ids:
        db.execute("DELETE FROM LineXSpell WHERE SpellID=?", (spell_id,))
    db.execute("DELETE FROM Spell WHERE PackageID=?", (PACKAGE,))
    db.execute("DELETE FROM ClassXSpecialization WHERE ClassID=?", (CLASS,))
    db.execute("DELETE FROM SpecXAbility WHERE Spec=?", (CAREER,))
    db.execute("DELETE FROM SpellLine WHERE KeyName LIKE 'Stormforged.%'")
    db.execute("DELETE FROM Specialization WHERE KeyName=?", (CAREER,))
    row_copy(db, "Specialization", source_row(db, "Specialization", "KeyName='ThaneCareer'"),
             {"KeyName": CAREER, "Name": "Stormforged", "Description": "Automatic storm abilities; all skills rise with character level."})
    template = source_row(db, "ClassXSpecialization", "ClassID=21")
    for order, key in enumerate((CAREER, "CharacterStyleUserCareer", "Sword", "Hammer", "Axe", "Shields", "Parry", "Stealth")):
        row_copy(db, "ClassXSpecialization", template, {"ClassID": CLASS, "SpecKeyName": key, "LevelAcquired": -100 if order < 2 else -order})

    ability = source_row(db, "SpecXAbility", "Spec='ThaneCareer'")
    # Full equipment permissions are intrinsic from creation.
    grants = [(1, "Weaponry: Staves", 0), (1, "MidArmor", 4), (1, "Shield", 3)]
    grants += [(1, "Weaponry: " + weapon, 0) for weapon in ("Swords", "Hammers", "Axes")]
    grants += [(5, "Guard", 1), (10, "Protect", 1), (15, "Intercept", 0), (20, "Protect", 2)]
    for level, key, rank in grants:
        if not db.execute("SELECT 1 FROM Ability WHERE KeyName=?", (key,)).fetchone():
            raise ValueError(f"Missing ability {key}")
        row_copy(db, "SpecXAbility", ability, {"Spec": CAREER, "SpecLevel": level, "AbilityKey": key, "AbilityLevel": rank, "ClassId": CLASS})

    # Copy style and realm-ability bindings under the new class ID; never change stock rows.
    db.execute("DELETE FROM Style WHERE ClassId=?", (CLASS,))
    for row in db.execute("SELECT * FROM Style WHERE ClassId=21").fetchall():
        row_copy(db, "Style", row, {"ClassId": CLASS})
    db.execute("DELETE FROM ClassXRealmAbility_Atlas WHERE CharClass=?", (CLASS,))
    for row in db.execute("SELECT * FROM ClassXRealmAbility_Atlas WHERE CharClass=21").fetchall():
        row_copy(db, "ClassXRealmAbility_Atlas", row, {"CharClass": CLASS})

    spell_base = source_row(db, "Spell", "SpellID=3508")
    line_base = source_row(db, "SpellLine", "1=1")
    link_base = source_row(db, "LineXSpell", "1=1")
    for name in list(SPELL_LINES.values()) + list(HEROIC_LINES.values()):
        row_copy(db, "SpellLine", line_base, {"KeyName": "Stormforged." + name, "Name": name, "Spec": CAREER, "IsBaseLine": 1, "ClassIDHint": CLASS})

    def spell(id, name, type, level, line=None, **fields):
        tooltip = 20600 + id - 62000
        if db.execute("SELECT 1 FROM Spell WHERE TooltipId=? AND PackageID<>?", (tooltip, PACKAGE)).fetchone():
            raise ValueError(f"Tooltip collision {tooltip}")
        data = {"SpellID": id, "Spell_ID": f"stormforged-{id}", "Name": name, "Description": name,
                "Type": type, "PackageID": PACKAGE, "TooltipId": tooltip, "ClientEffect": 3508, "Icon": 3508,
                "Target": "Self", "Range": 0, "Radius": 0, "Power": 0, "CastTime": 0,
                "Damage": 0, "DamageType": 12, "Duration": 0, "Frequency": 0, "Pulse": 0,
                "PulsePower": 0, "RecastDelay": 0, "Value": 0, "LifeDrainReturn": 0,
                "SpellGroup": 0, "EffectGroup": 0, "SubSpellID": 0, "SharedTimerGroup": 0,
                "MoveCast": 0, "Uninterruptible": 0, "IsFocus": 0, "Concentration": 0}
        data.update(fields)
        row_copy(db, "Spell", spell_base, data)
        if line:
            row_copy(db, "LineXSpell", link_base, {"LineName": "Stormforged." + (HEROIC_LINES[id] if id in HEROIC_LINES else SPELL_LINES[id % 20]), "SpellID": id, "Level": level})

    for tier, level in enumerate(LEVELS):
        n = 62000 + tier * 20
        power = max(1, level // 2)
        damage = 10 + level * 6
        spell(n, f"Stormbolt {level}", "StormforgedStrike", level, "Stormcalling", Target="Enemy", Range=1800,
              Damage=damage, Power=power, CastTime=2, LifeDrainReturn=50, Value=15, SpellGroup=62000,
              Icon=3510, ClientEffect=3510)  # Thane's top bolt, Thor's Full Lightning
        spell(n+1, f"Thunderclap {level}", "StormforgedStrike", level, "Stormcalling", Target="Enemy", Range=1500,
              Damage=damage*.8, Power=power, CastTime=0, RecastDelay=12, LifeDrainReturn=50, Value=15, SpellGroup=62001, Icon=3549, ClientEffect=3549)
        spell(n+2, f"Chain Lightning {level}", "StormforgedStrike", level, "Stormcalling", Target="Enemy", Range=0,
              Radius=350, Damage=damage*.75, Power=power, CastTime=0, RecastDelay=12, LifeDrainReturn=50, Value=15, SpellGroup=62002, Icon=3528, ClientEffect=3528)
        spell(n+16, f"Stormhammer {level}", "StormforgedStrike", level, "Stormcalling", Target="Enemy", Range=1500,
              Radius=350, Damage=damage*.75, Power=power, CastTime=2.5, LifeDrainReturn=50, Value=15, SpellGroup=62016, Icon=3541, ClientEffect=3541)
        spell(n+3, f"Stormheart {level}", "StormforgedAura", level, "Stormheart", Duration=3600, Frequency=40,
              Power=power, Value=level, SubSpellID=n+4, SpellGroup=62003, Icon=3517, ClientEffect=3517)
        spell(n+4, f"Stormheart Pulse {level}", "StormforgedStrike", level, Target="Enemy", Radius=350,
              Damage=damage*.5, LifeDrainReturn=75, Value=25)
        spell(n+5, f"Stormsong {level}", "StormforgedChant", level, "Stormsongs", Duration=3600, Frequency=40,
              Radius=1500, Value=125+min(level,40)*2, Damage=3+level, SubSpellID=n+6, SpellGroup=62005, Icon=3534, ClientEffect=3534)
        spell(n+6, f"Stormsong Weapons {level}", "DamageAdd", level, Target="Realm", Range=1500,
              Duration=9, Damage=1+level*.3, SpellGroup=62006, ClientEffect=0)
        spell(n+7, f"Thunderforged Ward {level}", "StormforgedWard", level, "Stormheart", Duration=3600,
              Value=min(100, level*2.5), SubSpellID=n+8, SpellGroup=62007, Icon=3537, ClientEffect=3537)
        spell(n+8, f"Thunderforged Shield {level}", "DamageShield", level, Duration=3600,
              Damage=1+level*.35, SpellGroup=62008, ClientEffect=0)
        spell(n+15, f"Thunderforged Weapons {level}", "DamageAdd", level, Target="Realm", Range=1500,
              Duration=3600, Damage=1+level*.4, SpellGroup=62015, ClientEffect=0)
        spell(n+9, f"Stormrest {level}", "StormforgedRest", level, "Stormsongs", Target="Realm", Range=1500,
              Value=25+level*15, Power=power, CastTime=3, SpellGroup=62009)
        if level >= 5:
            spell(n+10, f"Stormbound Elemental {level}", "StormforgedPet", level, "Stormbound", CastTime=3,
                  Power=power, Duration=65535, Damage=-100, Value=50, LifeDrainReturn=TEMPLATE, SpellGroup=62010)
            spell(n+11, f"Stormbound Spark {level}", "DirectDamage", level, Target="Enemy", Range=1200,
                  Damage=damage*.6, RecastDelay=8, SpellGroup=62011)
            spell(n+14, f"Stormbound Thunder {level}", "DirectDamage", level, Target="Enemy", Range=350,
                  Radius=250, Damage=damage*.4, RecastDelay=20, SpellGroup=62014)
        if level >= 10:
            spell(n+12, f"Lightning Bomb {level}", "SummonAnimistFnF", level, "Stormbound", CastTime=3,
                  Range=1000, Power=power, Duration=120, Damage=-100, Value=50,
                  LifeDrainReturn=BOMB_TEMPLATE, SubSpellID=n+13, RecastDelay=0, SpellGroup=62012)
            spell(n+13, f"Lightning Bomb Burst {level}", "DirectDamage", level, Target="Enemy", Range=900,
                  Radius=250, Damage=damage*.6, CastTime=1, RecastDelay=5)
            spell(n+17, f"Lightning Storm Pulse {level}", "DirectDamage", level, Target="Enemy", Range=0,
                  Radius=350, Damage=damage*.4, CastTime=0, RecastDelay=4, Icon=3523, ClientEffect=3523)
        if level == 10:
            spell(n+18, "Release Storm Clump", "TurretsRelease", level, "Stormbound", Target="Pet",
                  Range=4000, Radius=500, CastTime=0, Icon=868, ClientEffect=868)

    spell(62200, "Avatar of Thor", "StormforgedAvatar", 40, "Stormheart", Duration=60, Frequency=20,
          RecastDelay=180, Power=10, Value=918, SubSpellID=62203, SpellGroup=62200, Icon=3537, ClientEffect=3537)
    spell(62201, "Stormguard", "StormforgedStormguard", 10, "Stormheart", Duration=3600,
          Power=5, SubSpellID=62205, SpellGroup=62201, Icon=3536, ClientEffect=3536)
    spell(62202, "Second Thunder", "StormforgedSecondThunder", 20, "Stormheart", Duration=3600,
          Power=5, SubSpellID=62204, SpellGroup=62202, Icon=3535, ClientEffect=3535)
    spell(62203, "Avatar Lightning", "StormforgedStrike", 40, Target="Enemy", Range=0, Radius=350,
          Damage=250, LifeDrainReturn=50, Value=15, Icon=3528, ClientEffect=3528)
    spell(62204, "Second Thunder Rebirth", "StormforgedStrike", 20, Target="Enemy", Range=0, Radius=500,
          Damage=500, LifeDrainReturn=50, Value=15, Icon=3528, ClientEffect=3528)
    spell(62205, "Stormguard Retaliation", "StormforgedStrike", 10, Target="Enemy", Range=1500, Radius=350,
          Damage=150, LifeDrainReturn=50, Value=15, Icon=3541, ClientEffect=3541)

    spell(62210, "Stormstep", "StormforgedStep", 15, "Stormheart", Target="Enemy", Range=2000, Power=5,
          RecastDelay=8, SubSpellID=62216, SpellGroup=62210, Icon=3548, ClientEffect=3548)
    spell(62211, "Ride the Storm", "StormforgedRide", 30, "Stormheart", Duration=3600, Power=5,
          SubSpellID=62214, SpellGroup=62211, Icon=3537, ClientEffect=3531)
    spell(62212, "Thunder Recall", "StormforgedRecall", 20, "Stormheart", Range=1000, Power=5,
          RecastDelay=5, SpellGroup=62212, Icon=3538, ClientEffect=3538)
    spell(62213, "Eye of the Storm", "StormforgedEye", 25, "Stormheart", Duration=3600, Frequency=40,
          Radius=600, Power=5, SpellGroup=62213, Icon=3525, ClientEffect=3531)
    spell(62214, "Ride the Storm Echo", "DirectDamage", 30, Target="Enemy", Range=1800,
          Damage=200, Icon=3508, ClientEffect=3508)
    spell(62216, "Stormstep Arrival", "StormforgedStrike", 15, Target="Enemy", Range=0, Radius=350,
          Damage=350, LifeDrainReturn=50, Value=15, Icon=3528, ClientEffect=3528)

    # Internal support spells are not player spell-list entries. Pets scale their
    # damage/healing from these level-50 values while staying at the owner's level.
    for id, template in ((62206, MENDER_TEMPLATE), (62207, CASTER_TEMPLATE)):
        spell(id, "Stormbound Support", "SummonMinion", 1, Damage=-100, Value=255,
              Duration=65535, LifeDrainReturn=template)
    spell(62208, "Stormbound Mending", "Heal", 1, Target="Realm", Range=1800,
          Value=650, CastTime=2, RecastDelay=2, ClientEffect=0)
    spell(62209, "Stormbound Lightning", "DirectDamage", 1, Target="Enemy", Range=1500,
          Damage=240, CastTime=2, ClientEffect=3509)
    spell(62217, "Stormbound Weakening", "CombatSpeedDebuff", 1, Target="Enemy", Range=1500,
          Value=25, Duration=30, RecastDelay=12, ClientEffect=3521, SpellGroup=62217)
    spell(62218, "Stormbound Conductivity", "EnergyResistDebuff", 1, Target="Enemy", Range=1500,
          Value=30, Duration=30, RecastDelay=12, ClientEffect=3521, SpellGroup=62218)
    spell(62219, "Stormbound Challenge", "Taunt", 1, Target="Enemy", Range=1200,
          Radius=350, Value=600, RecastDelay=5, ClientEffect=0)

    for offset, source_id in enumerate(MENDER_BUFF_SOURCES):
        original = source_row(db, "Spell", f"SpellID={source_id}")
        id = 62220 + offset
        row_copy(db, "Spell", original, {
            "SpellID": id, "Spell_ID": f"stormforged-{id}", "Name": "Stormbound " + original['Name'],
            "PackageID": PACKAGE, "TooltipId": 20600 + id - 62000,
            "Type": original['Type'],
            "Target": "Realm", "Range": 1800, "Radius": 0, "Power": 0, "Concentration": 0,
            "Duration": original['Duration'] if source_id in (3238,3100) else 3600,
            "CastTime": 1, "Pulse": 0, "PulsePower": 0, "RecastDelay": 0,
            "SpellGroup": id, "EffectGroup": 0})

    pet = source_row(db, "NpcTemplate", "TemplateId=1")
    for id, name in [(TEMPLATE, "Stormbound Commander"), (BOMB_TEMPLATE, "Lightning Bomb"),
                     (MENDER_TEMPLATE, "Stormbound Mender"), (CASTER_TEMPLATE, "Stormbound Tempest")]:
        db.execute("DELETE FROM NpcTemplate WHERE TemplateId=?", (id,))
        # Stock air-elemental appearance is selected by model; no stock catalog assets are edited.
        row_copy(db, "NpcTemplate", pet, {"TemplateId": id, "Name": name, "Model": "114", "Size": "55" if id == TEMPLATE else "30" if id == BOMB_TEMPLATE else "45",
                 "ClassType": "", "Level": "0", "Spells": ";".join(map(str, [62208,62209,62217]+list(range(62220,62220+len(MENDER_BUFF_SOURCES))))) if id == MENDER_TEMPLATE else "62209;62218" if id == CASTER_TEMPLATE else "",
                 "TetherRange": 2 if id == TEMPLATE else 0,
                 "EquipmentTemplateID": "", "Strength": 120, "Constitution": 160 if id == TEMPLATE else 120, "Dexterity": 100,
                 "Quickness": 100, "Piety": 100, "MeleeDamageType": 2, "PackageID": PACKAGE})

    db.execute("DELETE FROM StartupLocation WHERE ClassID=?", (CLASS,))
    for row in db.execute("SELECT * FROM StartupLocation WHERE ClassID=21").fetchall():
        row_copy(db, "StartupLocation", row, {"ClassID": CLASS})
    # Thane has rows only for Norseman/Troll/Dwarf; Stormforged accepts every Midgard race.
    # Race-specific rows sort first, so this any-race row only places the other races.
    row_copy(db, "StartupLocation", source_row(db, "StartupLocation", "ClassID=21 AND RaceID=5"), {"ClassID": CLASS, "RaceID": 0})
    db.execute("DELETE FROM StarterEquipment WHERE Class=?", (CLASS,))
    starter_row = source_row(db, "StarterEquipment", "1=1")
    starter_items = ["bronze_pansarkedja_"+piece for piece in ("boots", "gloves", "hauberk", "helm", "leggings", "sleeves")]
    starter_items += ["training_hammer", "rowan_tower_shield2"]
    for item in starter_items:
        source_row(db, "ItemTemplate", "Id_nb=?", (item,))
        row_copy(db, "StarterEquipment", starter_row, {"Class": str(CLASS), "TemplateID": item})
    # Class 0 rows are awarded by CreationStartupEquipment once a class loadout exists.
    # The normal shared recall stone therefore needs no duplicate class-specific row.
    if not db.execute("SELECT 1 FROM StarterEquipment WHERE Class='0' AND TemplateID='Personal_Bind_Recall_Stone'").fetchone():
        row_copy(db, "StarterEquipment", starter_row, {"Class": str(CLASS), "TemplateID": "Personal_Bind_Recall_Stone"})
    trainer = source_row(db, "Mob", "Guild='Thane Trainer' AND Region=101")
    db.execute("DELETE FROM Mob WHERE Mob_ID='stormforged-trainer'")
    row_copy(db, "Mob", trainer, {"Mob_ID": "stormforged-trainer", "Name": "Stormkeeper", "Guild": "Stormforged Trainer",
             "ClassType": "DOL.GS.Trainer.StormforgedTrainer", "X": trainer["X"]+120, "NPCTemplateID": 0, "PackageID": PACKAGE})
    setting = db.execute("SELECT 1 FROM ServerProperty WHERE Key='enable_stormforged'").fetchone()
    if setting:
        db.execute("UPDATE ServerProperty SET Value='True' WHERE Key='enable_stormforged'")
    else:
        row_copy(db, "ServerProperty", source_row(db, "ServerProperty", "Key='enable_sluaghbinder'"),
                 {"Key": "enable_stormforged", "Category": "classes", "Value": "True", "DefaultValue": "False",
                  "Description": "Enable the Midgard Stormforged custom class.", "ServerProperty_ID": "enable_stormforged"})
    return {"class": CLASS, "spells": db.execute("SELECT count(*) FROM Spell WHERE PackageID=?", (PACKAGE,)).fetchone()[0],
            "trainer": "Stormkeeper, beside Frode in Jordheim", "tiers": LEVELS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = args.database.resolve(strict=True)
    with sqlite3.connect(path.as_uri()+"?mode=ro", uri=True) as source:
        if not args.apply:
            with sqlite3.connect(":memory:") as preview:
                source.backup(preview)
                print(json.dumps({"preview": True, **seed(preview)}, indent=2))
            return
        backup = path.with_name(path.name+".before-stormforged-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")+".bak")
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




