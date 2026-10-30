"""Give every enabled modern class a level-50 starting kit for the launcher's "+ Lv.50" bots.

offline_level50_loadouts only held the 39 classic / Shrouded Isles classes, so a batch that rolled
a Heretic, Valkyrie, Mauler, Sovereign... threw "The level-50 class template is missing or
incomplete" and added no bots. Each missing class copies the armor and jewelry of a classic class
of its realm that wears the same armor, then gets weapons for its own weapon skills (read from
ClassXSpecialization / SpecXAbility on 2026-10-27).

Stopped server only. Dry run by default; --apply backs the database up first.
  python provision_level50_modern_classes.py <opendaoc.sqlite3.db> [--apply]
"""
import argparse, datetime, re, shutil, sqlite3, uuid
from pathlib import Path

PACKAGE = 'Offline50-Modern-20261027'
# class: (name, realm, armor/jewelry donor, [(slot, object type, donor class or None for a world template)])
# Slots: 10 right hand, 11 left hand, 12 two-handed, 13 ranged, 40-42 spare weapons in the backpack.
# Object types: 2 crush, 3 slash, 4 thrust, 6 two-handed, 8 staff, 11 sword, 12 hammer, 13 axe, 14 spear,
# 19 blades, 20 blunt, 21 piercing, 22 large weapons, 23 celtic spear, 24 flexible, 27 fist wraps,
# 28 mauler staff, 42 shield.
KITS = {
    33: ('Heretic', 1, 5, [(10, 2, 1), (11, 42, 6), (40, 24, 19)]),
    34: ('Valkyrie', 2, 21, [(10, 11, 21), (11, 42, 21), (12, 14, 25)]),
    39: ('Bainshee', 3, 40, [(12, 8, 40)]),
    58: ('Vampiir', 3, 49, [(10, 21, 49)]),
    59: ('Warlock', 2, 29, [(12, 8, 29)]),
    60: ('Mauler', 1, 9, [(10, 27, None), (11, 27, None), (12, 28, None)]),
    61: ('Mauler', 2, 23, [(10, 27, None), (11, 27, None), (12, 28, None)]),
    62: ('Mauler', 3, 49, [(10, 27, None), (11, 27, None), (12, 28, None)]),
    64: ('Storm Sovereign', 2, 21, [(10, 11, 21), (11, 42, 21), (40, 12, 21), (41, 13, 21), (42, 14, 25)]),
    65: ('Pendragon Sovereign', 1, 1, [(10, 3, 1), (11, 42, 1), (12, 6, 1), (40, 2, 1), (41, 4, 1)]),
    66: ('Death Knight', 1, 12, [(12, 8, 12)]),
    67: ('Tuatha Sovereign', 3, 44, [(10, 19, 44), (11, 42, 44), (12, 22, 44), (40, 20, 44), (41, 21, 44), (42, 23, 44)]),
}
SMALL_SHIELD = {33}          # Heretic trains Shield 1 only
WEAPON_SLOTS = {10, 11, 12, 13, 40, 41, 42}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('database')
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    db_path = Path(a.database)
    backup = None
    if a.apply:
        backup = db_path.with_name(db_path.name + '.before-level50-modern-' +
                                   datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(db_path, backup)
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute('begin immediate')   # fails if a running server holds the database
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    have = {r[0] for r in c.execute('select distinct ClassId from offline_level50_loadouts')}
    added = {}

    def template(tid):
        row = c.execute('select * from ItemTemplate where Id_nb=?', (tid,)).fetchone()
        assert row, tid
        return dict(row)

    def donor_item(donor, typ):
        for r in c.execute('select TemplateId from offline_level50_loadouts where ClassId=?', (donor,)):
            t = template(r[0])
            if t['Object_Type'] == typ:
                return t
        raise ValueError(f'class {donor} has no type {typ} item')

    def world_item(typ, realm):
        r = c.execute('select * from ItemTemplate where Object_Type=? and Model>0 and Realm in (0,?) and Level between 45 and 51 '
                      'order by Level desc, Quality desc limit 1', (typ, realm)).fetchone()
        assert r, (typ, realm)
        r = dict(r)
        # Same clean-up as provision_level50_roster.py: no procs, charges or random bonuses.
        for field in ['SpellID', 'SpellID1', 'ProcSpellID', 'ProcSpellID1', 'PoisonSpellID', 'Charges', 'Charges1',
                      'MaxCharges', 'MaxCharges1', 'ExtraBonus', 'ExtraBonusType']:
            r[field] = 0
        for n in range(1, 11):
            r[f'Bonus{n}'] = r[f'Bonus{n}Type'] = 0
        r.update(Level=50, LevelRequirement=50, BonusLevel=50, Quality=100, Bonus=35, DPS_AF=165,
                 SPD_ABS=max(25, r['SPD_ABS'] or 0))
        return r

    def add(cid, name, realm, slot, item):
        typ = item['Object_Type']
        real_slot = 10 if slot >= 40 else slot
        item = dict(item)
        ident = f'offline50_20261027_c{cid}_s{slot}_t{typ}'
        item.update(Id_nb=ident, ItemTemplate_ID=uuid.uuid4().hex, Name=f'Offline level 50 {name} {typ}/{real_slot}',
                    Item_Type=real_slot, Realm=realm, AllowedClasses=str(cid), MaxCount=1, PackSize=1,
                    Condition=100000, MaxCondition=100000, Durability=100000, MaxDurability=100000,
                    IsPickable=1, IsDropable=1, IsTradable=1, CanDropAsLoot=1, IsIndestructible=0, IsNotLosingDur=0,
                    PackageID=PACKAGE, Description='Modern class level 50 template', LastTimeRowUpdated=now)
        if slot in WEAPON_SLOTS and typ != 42:
            item['Hand'] = 1 if slot == 12 else 2 if slot == 11 else 0
        if typ == 42:
            item['Hand'] = 0
            if cid in SMALL_SHIELD:
                item['Type_Damage'] = 1
        c.execute('delete from ItemTemplate where Id_nb=?', (ident,))
        c.execute('insert into ItemTemplate (' + ','.join(f'"{k}"' for k in item) + ') values (' +
                  ','.join('?' * len(item)) + ')', list(item.values()))
        c.execute('insert into offline_level50_loadouts (ClassId, SlotPosition, TemplateId) values (?,?,?)', (cid, slot, ident))
        added.setdefault(cid, []).append((slot, typ))

    for cid, (name, realm, donor, weapons) in KITS.items():
        if cid in have:
            print(f'class {cid} {name}: already has a kit, left alone')
            continue
        for r in c.execute('select SlotPosition, TemplateId from offline_level50_loadouts where ClassId=? order by SlotPosition',
                           (donor,)).fetchall():
            if r[0] not in WEAPON_SLOTS:
                add(cid, name, realm, r[0], template(r[1]))
        for slot, typ, source in weapons:
            add(cid, name, realm, slot, donor_item(source, typ) if source else world_item(typ, realm))

    # The launcher needs at least 15 items for a class; check every class the bot generator can roll.
    short = [(r[0], r[1]) for r in c.execute(
        'select l.ClassId, count(t.Id_nb) from offline_level50_loadouts l left join ItemTemplate t on t.Id_nb=l.TemplateId '
        'group by l.ClassId having count(t.Id_nb) < 15')]
    missing = [cid for cid in KITS if not c.execute('select 1 from offline_level50_loadouts where ClassId=?', (cid,)).fetchone()]
    for cid, items in added.items():
        print(f'class {cid} {KITS[cid][0]}: {len(items)} items, weapons ' +
              ', '.join(f'slot {s} type {t}' for s, t in items if s in WEAPON_SLOTS))
    assert not short and not missing, (short, missing)

    if not a.apply:
        c.rollback()
        print('Dry run: nothing changed. Add --apply to write it.')
        return
    c.commit()
    c.close()
    print(f'Applied. Backup: {backup}')


if __name__ == '__main__':
    main()
