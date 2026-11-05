#!/usr/bin/env python3
"""Tests for renumber_class_id.py, against a tiny scratch database (not a real server copy) that
exercises every one of the script's own column categories: a bare ClassId column, a delimited
list-of-IDs column, a column that must be ignored (ClassType), and a keyname-suffix column that
should be reported but never changed.

    python3 tools/test_renumber_class_id.py
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import renumber_class_id as r


def make_db(path):
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE ClassXSpecialization (ClassXSpecializationID INTEGER PRIMARY KEY, ClassID INT, SpecKeyName TEXT);
        CREATE TABLE StarterEquipment (StarterEquipmentID INTEGER PRIMARY KEY, Class TEXT, TemplateID TEXT);
        CREATE TABLE ItemTemplate (Id_nb TEXT PRIMARY KEY, AllowedClasses TEXT, ClassType TEXT);
        CREATE TABLE SpecXAbility (SpecXabilityID INTEGER PRIMARY KEY, Spec TEXT, ClassId INT, AbilityKey TEXT);
        CREATE TABLE Mob (Mob_ID INTEGER PRIMARY KEY, ClassType TEXT);

        INSERT INTO ClassXSpecialization (ClassID, SpecKeyName) VALUES (64, 'drengrspath_64');
        INSERT INTO ClassXSpecialization (ClassID, SpecKeyName) VALUES (64, 'Parry');
        INSERT INTO ClassXSpecialization (ClassID, SpecKeyName) VALUES (22, 'Axe');

        INSERT INTO StarterEquipment (Class, TemplateID) VALUES ('64', 'bronze_spear');
        INSERT INTO StarterEquipment (Class, TemplateID) VALUES ('22', 'training_sword');

        INSERT INTO ItemTemplate (Id_nb, AllowedClasses, ClassType) VALUES ('item1', '22;64;65', 'DOL.GS.GameNPC');
        INSERT INTO ItemTemplate (Id_nb, AllowedClasses, ClassType) VALUES ('item2', '164;264', 'DOL.GS.GameNPC');
        INSERT INTO ItemTemplate (Id_nb, AllowedClasses, ClassType) VALUES ('item3', '22', 'DOL.GS.GameNPC');

        INSERT INTO SpecXAbility (Spec, ClassId, AbilityKey) VALUES ('vikingcareer_64', 0, 'MidArmor');
        INSERT INTO SpecXAbility (Spec, ClassId, AbilityKey) VALUES ('Axe', 0, 'Weaponry: Axes');

        INSERT INTO Mob (ClassType) VALUES ('DOL.GS.GameNPC');
        """
    )
    con.commit()
    con.close()


class RenumberClassIdTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = str(self.tmp / "test.db")
        make_db(self.db)

    def test_discovers_and_classifies_every_known_column_without_complaint(self):
        con = sqlite3.connect(self.db)
        try:
            columns = r.discover_class_columns(con)
            id_cols, list_cols, unclassified = r.classify(columns)
        finally:
            con.close()
        self.assertEqual(unclassified, [])
        self.assertIn(("ClassXSpecialization", "ClassID"), id_cols)
        self.assertIn(("StarterEquipment", "Class"), id_cols)
        self.assertIn(("ItemTemplate", "AllowedClasses"), list_cols)

    def test_an_unclassified_class_shaped_column_stops_the_script(self):
        con = sqlite3.connect(self.db)
        con.execute("ALTER TABLE Mob ADD COLUMN SubclassHint TEXT")
        con.commit()
        con.close()
        with self.assertRaises(r.RenumberError):
            r.run(self.db, 64, 199, apply=False)

    def test_dry_run_reports_every_match_without_changing_anything(self):
        before = Path(self.db).read_bytes()
        r.run(self.db, 64, 199, apply=False)
        self.assertEqual(Path(self.db).read_bytes(), before, "dry run must not write anything")

    def test_apply_moves_bare_id_columns_including_text_typed_ones(self):
        r.run(self.db, 64, 199, apply=True)
        con = sqlite3.connect(self.db)
        try:
            self.assertEqual(
                con.execute("SELECT count(*) FROM ClassXSpecialization WHERE ClassID = 199").fetchone()[0], 2
            )
            self.assertEqual(
                con.execute("SELECT count(*) FROM ClassXSpecialization WHERE ClassID = 64").fetchone()[0], 0
            )
            # Still a TEXT value, not silently turned into an int-affinity surprise:
            self.assertEqual(
                con.execute("SELECT Class FROM StarterEquipment WHERE TemplateID = 'bronze_spear'").fetchone()[0],
                "199",
            )
            # The untouched class (22) must survive exactly as it was:
            self.assertEqual(
                con.execute("SELECT count(*) FROM ClassXSpecialization WHERE ClassID = 22").fetchone()[0], 1
            )
        finally:
            con.close()

    def test_apply_rewrites_delimited_list_columns_token_by_token(self):
        r.run(self.db, 64, 199, apply=True)
        con = sqlite3.connect(self.db)
        try:
            self.assertEqual(
                con.execute("SELECT AllowedClasses FROM ItemTemplate WHERE Id_nb = 'item1'").fetchone()[0],
                "22;199;65",
            )
            # "164" and "264" must never be touched by a "64" token replace:
            self.assertEqual(
                con.execute("SELECT AllowedClasses FROM ItemTemplate WHERE Id_nb = 'item2'").fetchone()[0],
                "164;264",
            )
        finally:
            con.close()

    def test_ignored_columns_are_never_touched_even_when_they_contain_the_id_as_a_substring(self):
        r.run(self.db, 64, 199, apply=True)
        con = sqlite3.connect(self.db)
        try:
            self.assertEqual(
                con.execute("SELECT ClassType FROM ItemTemplate WHERE Id_nb = 'item1'").fetchone()[0],
                "DOL.GS.GameNPC",
            )
        finally:
            con.close()

    def test_keyname_suffix_columns_are_reported_but_never_rewritten(self):
        con = sqlite3.connect(self.db)
        findings = r.report_keyname_suffixes(con, 64)
        con.close()
        found = {(t, c): vals for t, c, vals in findings}
        self.assertIn(("ClassXSpecialization", "SpecKeyName"), found)
        self.assertIn("drengrspath_64", found[("ClassXSpecialization", "SpecKeyName")])
        # A shared/plain keyname with no suffix at all must not be reported:
        self.assertNotIn("Parry", found.get(("ClassXSpecialization", "SpecKeyName"), []))

        r.run(self.db, 64, 199, apply=True)
        con = sqlite3.connect(self.db)
        try:
            self.assertEqual(
                con.execute(
                    "SELECT count(*) FROM ClassXSpecialization WHERE SpecKeyName = 'drengrspath_64'"
                ).fetchone()[0],
                1,
                "a keyname suffix must survive --apply unchanged - it is advisory-only",
            )
        finally:
            con.close()

    def test_a_nonexistent_class_id_is_a_clean_no_op(self):
        before = Path(self.db).read_bytes()
        r.run(self.db, 12345, 199, apply=True)
        # No backup should even be worth creating for a true no-op, but more importantly nothing
        # in the live file should have changed:
        self.assertEqual(Path(self.db).read_bytes(), before)

    def test_apply_creates_a_timestamped_backup_before_changing_anything(self):
        r.run(self.db, 64, 199, apply=True)
        backups = list(self.tmp.glob("test.db.bak-*"))
        self.assertEqual(len(backups), 1)
        con = sqlite3.connect(str(backups[0]))
        try:
            self.assertEqual(
                con.execute("SELECT count(*) FROM ClassXSpecialization WHERE ClassID = 64").fetchone()[0],
                2,
                "the backup must reflect the pre-change state",
            )
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
