"""Enable the opt-in hybrid rules only after validating the selected world's boundaries."""
import datetime
import uuid

FRONTIERS = {
    11: (1, "Forest Sauvage"), 12: (1, "Snowdonia"),
    14: (1, "Pennine Mountains"), 15: (1, "Hadrian's Wall"),
    111: (100, "Uppland"), 112: (100, "Yggdra Forest"),
    113: (100, "Jamtland Mountains"), 115: (100, "Odin's Gate"),
    210: (200, "Mount Collory"), 211: (200, "Cruachan Gorge"),
    212: (200, "Breifine"), 214: (200, "Emain Macha"),
}


def enable(db):
    for zone, expected in FRONTIERS.items():
        row = db.execute("SELECT RegionID,Name FROM Zones WHERE ZoneID=?", (zone,)).fetchone()
        if row is None or tuple(row) != expected:
            raise ValueError(f"Unexpected frontier boundary for zone {zone}")
    row = db.execute("SELECT Description FROM Regions WHERE RegionID=249").fetchone()
    if row is None or row[0] != "Darkness Falls":
        raise ValueError("Darkness Falls region does not match the hybrid rules")
    known_bgs = {165, *range(234, 243), 250, 251, 252, 253}
    if any(row[0] not in known_bgs for row in db.execute("SELECT RegionID FROM Battleground")):
        raise ValueError("Unknown battleground region; review its PvP boundary first")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for key, value, category, description in (
        ("hybrid_coop_pvp", "True", "server", "Co-op world with realm vs realm in DF, battlegrounds and frontier zones; requires restart."),
        ("allow_bg_claim", "True", "atlas", "Allow guild claims in battlegrounds."),
        ("claim_num", "1", "keeps", "One nearby player may claim for a solo/co-op guild."),
    ):
        if db.execute("SELECT 1 FROM ServerProperty WHERE Key=?", (key,)).fetchone():
            db.execute("UPDATE ServerProperty SET Value=?,LastTimeRowUpdated=? WHERE Key=?", (value, now, key))
        else:
            db.execute("INSERT INTO ServerProperty (Category,Key,Description,DefaultValue,Value,LastTimeRowUpdated,ServerProperty_ID) VALUES (?,?,?,?,?,?,?)",
                       (category, key, description, "False" if key == "hybrid_coop_pvp" else value, value, now, str(uuid.uuid4())))
    return {"rules": "Hybrid co-op / realm war in the frontiers", "hybrid_coop_pvp": True,
            "single_player_guild_claims": True, "battleground_guild_claims": True}


def disable(db):
    """Restore stock RvR without restoring an older save or changing world ownership."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for key, value in (("hybrid_coop_pvp", "False"), ("allow_bg_claim", "False"), ("claim_num", "8")):
        db.execute("UPDATE ServerProperty SET Value=?,LastTimeRowUpdated=? WHERE Key=?", (value, now, key))
    return {"rules": "Normal realm-versus-realm", "hybrid_coop_pvp": False}
