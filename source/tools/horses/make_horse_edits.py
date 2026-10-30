"""Build World Workshop edits that add every client mount, saddle, horse armor, barding and saddlebag.

The client's gamedata.mpk lists what it can draw:
  horsemap.csv           mount ID (sent as the Horse item's SPD_ABS) -> monster model
  horsearmorthememap.csv saddle / horse armor theme (HorseArmor item's DPS_AF), per realm
  horsematerialmap.csv   barding style (HorseBarding item's DPS_AF), 1-36

Every stable master sells them after its route tickets: every mount, then its realm's saddles and armor,
every barding and the four saddlebags. A stable master with no ticket list gets its realm's stable_tack_<realm>
list. Neutral stable masters count as the realm of their region; boat stable masters are left alone. The
world's database is read (read-only) to find the ticket lists, the items and settings it already has (those are
not added again) and the old Horse Trader / Tack Merchant NPCs and lists, which are removed.
Items are level 1 and cheap; pair them with the server setting rates / mount_any_level_full_speed = True so
every mount rides at full speed and works in RvR.

    python source/tools/horses/make_horse_edits.py --client <client app folder> --db <world db> --out horse-edits.json
    python source/tools/world_editor/cli.py --game <game folder> plan horse-edits.json --out horses.patch.json
"""
import argparse
import csv
import io
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'new-client' / 'pipeline'))
from daoc_mpk import read_mpk  # noqa: E402

GOLD = 10000

# Display names for horsemap.csv rows whose Text is a dev label or misspelt.
MOUNT_NAMES = {
    1: 'Brown Horse', 2: 'Black Horse', 3: 'White Horse', 4: 'Grey Horse', 5: 'Palomino Horse',
    6: 'Spotted Horse', 7: 'Chocolate Horse', 8: 'Clydesdale Horse', 9: 'Appaloosa Horse',
    10: 'Dappled Grey Horse', 11: 'Leopard Horse', 12: 'Primitive Dun Horse', 13: 'Red Dun Horse',
    14: 'Shire Dappled Horse', 15: 'Strawberry Roan Horse',
    17: 'Brown Warhorse', 18: 'Black Warhorse', 19: 'White Warhorse', 20: 'Grey Warhorse',
    21: 'Palomino Warhorse', 22: 'Spotted Warhorse', 23: 'Chocolate Warhorse', 24: 'Clydesdale Warhorse',
    25: 'Appaloosa Warhorse', 26: 'Leopard Warhorse', 27: 'Primitive Dun Warhorse', 28: 'Red Dun Warhorse',
    33: 'Brown Unicorn', 34: 'Black Unicorn', 35: 'White Unicorn', 36: 'Grey Unicorn',
    37: 'Palomino Unicorn', 38: 'Spotted Unicorn', 39: 'Chocolate Unicorn', 40: 'Clydesdale Unicorn',
    41: 'Rainbow Unicorn', 49: 'Nightmare', 50: 'Undead Horse',
    51: 'Storm War Steed', 52: 'Frost War Steed', 53: 'Flame War Steed', 54: 'Earth War Steed',
    55: 'Pink Unicorn', 56: 'Sea Horse', 57: 'Arboreal Horse', 58: 'Arboreal Warhorse',
    59: 'Clockwork Horse', 60: 'Gemstone Horse', 61: 'Dragonfly Mount', 62: 'Wyvern Mount',
    63: 'Gryphon Mount', 64: 'Stone Dragon', 65: 'Wingless Stone Dragon', 66: 'Minotaur Mount',
    67: 'Chimera Mount', 68: 'Evil Pixie Mount', 69: 'Troll Mount', 70: 'War Boar',
    71: 'Baby Wolf Dragon', 72: 'Baby Glimmer Dragon', 73: 'Stone Dragon Mount', 74: 'Great Elk',
    75: 'Great Wolf', 76: 'Keggar', 77: 'Great Lion', 78: 'Questing Beast', 79: 'Killer Rabbit',
    80: 'Giant Rabbit', 81: 'Horned Rabbit', 82: 'Fey Rabbit', 83: 'Unibunny', 84: 'Broom',
    85: 'Ghost Mount', 86: 'Green Broom', 87: 'Darkfire Broom', 88: 'Fire Broom', 89: 'Chimera Mount',
}

# Mounts that don't look right with a rider in game (owner, 2026-10-28): dragonfly, wingless
# stone dragon, minotaur, troll, stone dragon (64), evil pixie. Left out until they are fixed.
# 70 "test boar" points at a monster the client doesn't have (invisible).
HIDDEN_MOUNTS = {61, 64, 65, 66, 68, 69, 70}
# 67, the stock Chimera, has no saddle node; install_chimera_mount.py adds the saddled copy as mount 89, and the
# mount_67 item rides that.
RIDES = {67: 89}

# Mounts whose riders fly (server setting world / flying_mount_ids; needs the modern client's flight patch):
# wyvern, gryphon, stone dragon, the baby wolf/glimmer dragons, stone dragon mount, the brooms, ghost mount,
# and the saddled Chimera (89, from install_chimera_mount.py).
FLYING_MOUNTS = (62, 63, 64, 71, 72, 73, 84, 85, 86, 87, 88, 89)

REALMS = {1: ('alb', 'Albion', 'Alb'), 2: ('mid', 'Midgard', 'Mid'), 3: ('hib', 'Hibernia', 'Hib')}
THEMES = {'Basic': 'Basic', 'Pre-Order': 'Founder', 'Heroic': 'Heroic', 'Heoric': 'Heroic',
          'Sinister': 'Sinister', 'Magic': 'Magical', 'Magical': 'Magical'}
PIECES = {0: ('Saddle', 0.5), 1: ('Light Horse Armor', 1), 2: ('Medium Horse Armor', 1.5), 3: ('Heavy Horse Armor', 2)}
BAGS = [(96, 'Left Front Saddlebag'), (97, 'Right Front Saddlebag'), (98, 'Left Rear Saddlebag'), (99, 'Right Rear Saddlebag')]

# Existing rows copied for their item flags, durability and package; everything visible is reset.
COPY_HORSE, COPY_SADDLE, COPY_BARDING = 'clockworkmount', 'saddle0', 'barding28'

STABLE_MASTER = 'DOL.GS.GameStableMaster'
PAGE, PAGES = 30, 5
STOCK_FROM = 10  # the stock starts at page 0 slot 10, after the route tickets (no list has more than 7)
# Home realm of the regions neutral stable masters stand in (Albion and the Shrouded Isles).
REGION_REALM = {1: 1, 51: 1, 100: 2, 151: 2, 200: 3, 181: 3}
OLD_TRADER_LISTS = [f'{kind}_{code}' for kind in ('horse_trader', 'tack_merchant') for code in ('alb', 'mid', 'hib')]


def table(mpk, name):
    rows = list(csv.reader(io.StringIO(mpk[name].decode('latin1'))))
    return [r for r in rows[2:] if r and r[0].strip().lstrip('-').isdigit()]


def mount_price(mount_id, text):
    if mount_id <= 15:
        return GOLD
    if mount_id <= 28:
        return 2 * GOLD
    if 'Unicorn' in text:
        return 3 * GOLD
    return 5 * GOLD


def item(copy, key, name, item_type, model, dps_af, spd_abs, realm, price):
    return {'table': 'ItemTemplate', 'copy': copy, 'key': key, 'set': {
        'Name': name, 'Level': 1, 'Item_Type': item_type, 'Model': model, 'DPS_AF': dps_af,
        'SPD_ABS': spd_abs, 'Realm': realm, 'Price': price, 'Color': 0,
        'IsTradable': 1, 'IsDropable': 1, 'CanDropAsLoot': 0, 'Description': ''}}


def query(con, sql, *args):
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(sql, args)]


def stable_edits(con, horses, tack):
    """Stock every stable master after its tickets; drop the old Horse Trader / Tack Merchant NPCs and lists."""
    edits, stock_by_list = [], {}
    for m in query(con, 'SELECT Mob_ID, Realm, Region, ItemsListTemplateID FROM Mob WHERE ClassType = ?', STABLE_MASTER):
        realm = m['Realm'] or REGION_REALM.get(m['Region'], 0)
        list_id = m['ItemsListTemplateID'] or ''
        if not list_id:
            list_id = f'stable_tack_{REALMS[realm][0]}' if realm in REALMS else 'stable_tack_neutral'
            edits.append({'table': 'Mob', 'key': m['Mob_ID'], 'set': {'ItemsListTemplateID': list_id}})
        stock = horses + tack[realm]
        assert stock_by_list.setdefault(list_id, stock) == stock, f'{list_id} is shared by stable masters of two realms'

    for list_id, stock in stock_by_list.items():
        rows = query(con, 'SELECT ItemTemplateID, PageNumber, SlotPosition FROM MerchantItem WHERE ItemListID = ?', list_id)
        have = {r['ItemTemplateID'] for r in rows}
        used = [r['PageNumber'] * PAGE + r['SlotPosition'] for r in rows if r['ItemTemplateID'] not in stock]
        if used and max(used) >= STOCK_FROM:
            raise ValueError(f'{list_id} has tickets past page 0 slot {STOCK_FROM - 1}')
        assert STOCK_FROM + len(stock) <= PAGE * PAGES, list_id
        for n, key in enumerate(stock, STOCK_FROM):
            if key not in have:
                edits.append({'table': 'MerchantItem', 'insert': {
                    'ItemListID': list_id, 'ItemTemplateID': key, 'PageNumber': n // PAGE, 'SlotPosition': n % PAGE}})

    for list_id in OLD_TRADER_LISTS:
        for r in query(con, 'SELECT Mob_ID FROM Mob WHERE ItemsListTemplateID = ?', list_id):
            edits.append({'table': 'Mob', 'delete': r['Mob_ID']})
        for r in query(con, 'SELECT MerchantItem_ID FROM MerchantItem WHERE ItemListID = ?', list_id):
            edits.append({'table': 'MerchantItem', 'delete': r['MerchantItem_ID']})
    return edits


def build(client, db):
    mpk = read_mpk(Path(client) / 'gamedata.mpk')
    edits, horses, tack = [], [], {r: [] for r in REALMS}

    for r in table(mpk, 'horsemap.csv'):
        mid = int(r[0])
        if mid in HIDDEN_MOUNTS or mid in RIDES.values():
            continue
        name = MOUNT_NAMES.get(mid, r[1].strip())
        key = f'mount_{mid:02}'
        # DPS_AF on a horse is unused by the server; keep the copied value clear.
        edits.append(item(COPY_HORSE, key, name, 9, 2912, 0, RIDES.get(mid, mid), 0, mount_price(mid, name)))
        horses.append(key)

    for r in table(mpk, 'horsearmorthememap.csv'):
        theme, desc, piece = int(r[0]), r[1].strip(), int(r[2])
        if piece not in PIECES:  # 51 "No Saddle": an unsaddled horse already shows its realm's basic saddle
            continue
        realm = next(n for n, (_, _, short) in REALMS.items() if desc.startswith(short))
        style = THEMES[next(w for w in desc.split() if w in THEMES)]
        label, gold = PIECES[piece]
        key = f'horse_armor_{theme:02}'
        model = 3431 if piece == 0 else 2913
        edits.append(item(COPY_SADDLE, key, f'{REALMS[realm][1]} {style} {label}', 7, model, theme, 0, realm,
                          int(gold * GOLD)))
        tack[realm].append(key)

    bardings = {}
    for r in table(mpk, 'horsematerialmap.csv'):
        if r[0] == '48' and r[2] == '1' and int(r[3]) > 0:
            bardings[int(r[3])] = r[1].split(':', 1)[1].strip().replace('  ', ' ').replace('reigns', 'reins')
    barding_keys = []
    for style, desc in sorted(bardings.items()):
        kind = desc.split(' Barding')[0]
        gold = {'Tasset': 0.5, 'Blanket': 0.75, 'Half': 1, 'Full': 1.5}[kind]
        key = f'horse_barding_{style:02}'
        edits.append(item(COPY_BARDING, key, desc, 8, 2914, style, 0, 0, int(gold * GOLD)))
        barding_keys.append(key)

    bag_keys = []
    for slot, name in BAGS:
        key = f'horse_saddlebag_{slot - 95}'
        edits.append(item(COPY_BARDING, key, name, slot, 2911, 0, 0, 0, GOLD))
        bag_keys.append(key)

    # Realm 0 (a neutral stable master outside the home regions) gets no realm saddles or armor.
    tack = {realm: tack.get(realm, []) + barding_keys + bag_keys for realm in (0, *REALMS)}

    # The server adds this row with its default (False) on first start; add it switched on.
    edits.append({'table': 'ServerProperty', 'insert': {
        'Category': 'rates', 'Key': 'mount_any_level_full_speed', 'DefaultValue': 'False', 'Value': 'True',
        'Description': 'Do personal mounts of any level ride at the over level 35 speed and work in RvR zones?'}})
    edits.append({'table': 'ServerProperty', 'insert': {
        'Category': 'world', 'Key': 'flying_mount_ids', 'DefaultValue': '',
        'Value': ';'.join(str(m) for m in FLYING_MOUNTS if m not in HIDDEN_MOUNTS),
        'Description': 'Mount IDs (client horsemap.csv, separated by ;) whose riders can fly. Needs the patched modern client.'}})

    with closing(sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)) as con:
        # Items and settings the world already has stay as they are.
        items = {r['Id_nb'] for r in query(con, 'SELECT Id_nb FROM ItemTemplate')}
        props = {r['Key'] for r in query(con, 'SELECT "Key" FROM ServerProperty')}
        edits = [e for e in edits if not (e['table'] == 'ItemTemplate' and e['key'] in items or
                                          e['table'] == 'ServerProperty' and e['insert']['Key'] in props)]
        edits += stable_edits(con, horses, tack)
    return edits


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--client', required=True, help='client app folder holding gamedata.mpk')
    p.add_argument('--db', required=True, help='the world database (runtime/data/opendaoc.sqlite3.db), read only')
    p.add_argument('--out', required=True)
    args = p.parse_args()
    edits = build(args.client, args.db)
    Path(args.out).write_text(json.dumps(edits, indent=1), encoding='utf-8')
    counts = {}
    for e in edits:
        counts[e['table']] = counts.get(e['table'], 0) + 1
    print(f'{len(edits)} edits -> {args.out}: {counts}')


if __name__ == '__main__':
    main()
