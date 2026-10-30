"""One-time cleanup of orphaned ItemUnique rows, then VACUUM.

Before the September 20 BotInventory rewrite, bot loot left its generated
ItemUnique definition behind when the inventory row was sold or destroyed.
About 525,000 such definitions (75% of the table) are referenced by nothing.

A row is deleted only if its Id_nb is not referenced by Inventory or by any
other table that can point at an item template. Run with the server STOPPED.
A full backup is written next to the database first.

usage: python cleanup_orphan_unique_items.py <path-to-opendaoc.sqlite3.db> [--dry-run]
"""
import os
import shutil
import sqlite3
import sys
import time

# Every column in the schema that can hold an item template / unique id.
REFERENCES = [
    ("Inventory", "UTemplate_Id"),
    ("Inventory", "ITemplate_Id"),
    ("CharacterXOneTimeDrop", "ItemTemplateID"),
    ("CraftedItem", "Id_nb"),
    ("DropTemplateXItemTemplate", "ItemTemplateID"),
    ("househookpointitem", "ItemTemplateID"),
    ("ItemTemplate", "Id_nb"),
    ("LootOTD", "ItemTemplateID"),
    ("LootTemplate", "ItemTemplateID"),
    ("MerchantItem", "ItemTemplateID"),
    ("NPCEquipment", "TemplateID"),
    ("Salvage", "Id_nb"),
    ("StarterEquipment", "TemplateID"),
    ("offline_level50_loadouts", "TemplateId"),
]

DANGLING = ("SELECT COUNT(*) FROM Inventory i WHERE i.UTemplate_Id IS NOT NULL AND i.UTemplate_Id <> '' "
            "AND NOT EXISTS (SELECT 1 FROM ItemUnique u WHERE u.Id_nb = i.UTemplate_Id)")


def collect_referenced(con):
    tables = {r[0].lower() for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.execute("DROP TABLE IF EXISTS temp.orphan_cleanup_refs")
    con.execute("CREATE TEMP TABLE orphan_cleanup_refs (id TEXT PRIMARY KEY)")
    for table, column in REFERENCES:
        if table.lower() not in tables:
            continue
        if column not in {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}:
            continue
        con.execute(f'INSERT OR IGNORE INTO temp.orphan_cleanup_refs SELECT "{column}" FROM "{table}" '
                    f'WHERE "{column}" IS NOT NULL AND "{column}" <> \'\'')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    if not os.path.isfile(path):
        print(f"not found: {path}")
        return 2

    if not dry_run:
        backup = path + ".before-orphan-cleanup"
        if not os.path.exists(backup):
            con = sqlite3.connect(path)
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            con.close()
            shutil.copy2(path, backup)
            print(f"backup written: {backup}")

    before = os.path.getsize(path)
    con = sqlite3.connect(path)
    con.execute("PRAGMA busy_timeout = 5000")
    collect_referenced(con)

    total = con.execute("SELECT COUNT(*) FROM ItemUnique").fetchone()[0]
    orphans = con.execute("SELECT COUNT(*) FROM ItemUnique WHERE Id_nb NOT IN (SELECT id FROM temp.orphan_cleanup_refs)").fetchone()[0]
    dangling_before = con.execute(DANGLING).fetchone()[0]
    print(f"ItemUnique rows: {total:,}  orphaned: {orphans:,}  kept: {total - orphans:,}")
    print(f"inventory rows already missing their unique definition: {dangling_before}")
    if dry_run or orphans == 0:
        con.close()
        return 0

    start = time.time()
    with con:
        deleted = con.execute("DELETE FROM ItemUnique WHERE Id_nb NOT IN (SELECT id FROM temp.orphan_cleanup_refs)").rowcount
    print(f"deleted {deleted:,} rows in {time.time() - start:.1f}s")
    dangling_after = con.execute(DANGLING).fetchone()[0]
    print(f"inventory rows missing their unique definition afterwards: {dangling_after}")
    if dangling_after != dangling_before:
        print("ERROR: cleanup changed inventory references; restore the backup.")
        return 1

    con.execute("DROP TABLE IF EXISTS temp.orphan_cleanup_refs")
    start = time.time()
    con.execute("VACUUM")
    con.execute("PRAGMA journal_mode=WAL")
    print(f"vacuum {time.time() - start:.1f}s; integrity: {con.execute('PRAGMA integrity_check').fetchone()[0]}")
    con.close()
    print(f"size {before / 1048576:.0f} MB -> {os.path.getsize(path) / 1048576:.0f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
