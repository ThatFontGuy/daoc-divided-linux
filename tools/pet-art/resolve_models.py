"""Resolve monsters.csv model IDs -> NIF + skin files + archives, and who else uses them."""
import sqlite3
import sys
from daoc_catalog import gamedata, csv_rows, CLIENT, mpk

SKIN_COLS = ["Body", "Head", "Arms", "Gloves", "Lbody", "Legs", "Boots", "Cloak", "Helm"]

files = gamedata()
monsters = {r[0]: r for r in csv_rows(files, "monsters.csv")[2:] if r and r[0].isdigit()}
monnifs = {r[0]: r for r in csv_rows(files, "monnifs.csv")[2:] if r and r[0].isdigit()}
skins = {r[0]: r for r in csv_rows(files, "skins.csv")[2:] if r and r[0].isdigit()}

db = sqlite3.connect(f"file:{CLIENT.parents[1] / 'data' / 'opendaoc.sqlite3.db'}?mode=ro", uri=True)
templates = db.execute("SELECT TemplateId, Name, Model FROM NpcTemplate").fetchall()
mobs = db.execute("SELECT Name, Model, COUNT(*) FROM Mob GROUP BY Name, Model").fetchall()


def users(model):
    t = [f"{tid}:{name}" for tid, name, m in templates if m and model in str(m).split(";")]
    m = [f"{name}x{n}" for name, mm, n in mobs if str(mm) == model]
    return t, m


skin_archive_cache = {}


def skin_entry_exists(archive_num, filename):
    path = CLIENT / "figures" / "skins" / f"skin{int(archive_num):03d}.mpk"
    if path not in skin_archive_cache:
        try:
            _, entries = mpk(path)
            skin_archive_cache[path] = {e.name.lower() for e in entries}
        except Exception as exc:
            skin_archive_cache[path] = exc
    names = skin_archive_cache[path]
    if isinstance(names, Exception):
        return f"{path.name}: {names}"
    return f"{path.name}:{'OK' if filename.lower() in names else 'MISSING'}"


for model in sys.argv[1:]:
    row = monsters.get(model)
    if not row:
        print(f"model {model}: not in monsters.csv")
        continue
    nif = monnifs.get(row[2])
    print(f"== model {model} '{row[1]}'  scale={row[12]}  NIF#{row[2]} -> {nif[2] if nif else '?'} (anim set {nif[3] if nif else '?'}, skeleton archive {nif[15] if nif else '?'})")
    for col, label in zip(row[3:12], SKIN_COLS):
        if col and col != "0":
            s = skins.get(col)
            if s:
                print(f"   {label:6} skin#{col} -> {s[2]}  archive {s[4]}  [{skin_entry_exists(s[4], s[2])}]")
            else:
                print(f"   {label:6} skin#{col} -> not in skins.csv")
    t, m = users(model)
    print(f"   templates using it: {t[:12]}{' ...' if len(t) > 12 else ''}")
    print(f"   world mobs using it: {m[:12]}{' ...' if len(m) > 12 else ''}")
