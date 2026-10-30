"""Checks of the live-world migration (live_world_migration.py): the affected rule, door matching, relocation,
and apply/rollback on a temporary world."""
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import live_world_migration as m


class FakeGeometry:
    def __init__(self, heights):
        self._heights = heights

    def heights(self, x, y):
        return self._heights(x, y)


class FakeWalkable:
    """Walkable floor at height 100 only where x >= 1000."""

    def at(self, x, y, z, tolerance):
        return 100.0 if x >= 1000 and abs(100 - z) <= tolerance else None


class AffectedTests(unittest.TestCase):
    def test_same_floor_is_not_affected(self):
        floor = FakeGeometry(lambda x, y: [100.0])
        self.assertIsNone(m.affected(floor, floor, 0, 0, 100))

    def test_a_new_wall_through_the_body(self):
        classic = FakeGeometry(lambda x, y: [100.0])
        live = FakeGeometry(lambda x, y: [100.0, 180.0])
        self.assertEqual(m.affected(classic, live, 0, 0, 100), 'inside live geometry')

    def test_a_floor_that_moved_or_went(self):
        classic = FakeGeometry(lambda x, y: [500.0])
        self.assertEqual(m.affected(classic, FakeGeometry(lambda x, y: [100.0]), 0, 0, 500), 'lost its floor')
        self.assertEqual(m.affected(classic, FakeGeometry(lambda x, y: []), 0, 0, 500), 'lost its floor')
        self.assertEqual(m.affected(FakeGeometry(lambda x, y: [500.0]), FakeGeometry(lambda x, y: [440.0]), 0, 0, 500), 'floor moved')


class RelocateTests(unittest.TestCase):
    def test_moves_to_the_nearest_walkable_spot(self):
        x, y, z, how = m.relocate(FakeWalkable(), 900, 0, 100)
        self.assertGreaterEqual(x, 1000)
        self.assertLessEqual(x, 1000 + m.SEARCH_STEP)
        self.assertEqual(z, 100.0)
        self.assertIn('moved', how)

    def test_fixes_only_the_height_when_the_spot_is_walkable(self):
        self.assertEqual(m.relocate(FakeWalkable(), 1500, 0, 50), (1500, 0, 100.0, 'height fixed'))

    def test_gives_up_beyond_the_search_radius(self):
        self.assertIsNone(m.relocate(FakeWalkable(), -5000, 0, 100))


class StructureTests(unittest.TestCase):
    keep = dict(name='k', region=1, src=(1000, 1000), dst=(5000, 9000), turn=90)

    def test_carry_turns_about_the_old_centre_then_shifts(self):
        x, y = m.carry(self.keep, 1100, 1000)  # 100 east of the old centre, turned 90 degrees: 100 north of the new one
        self.assertAlmostEqual(x, 5000)
        self.assertAlmostEqual(y, 9100)
        self.assertEqual(m.carry(dict(self.keep, turn=0), 1000, 1000), (5000, 9000))

    def test_headings_turn_with_the_world(self):
        # Heading 0 faces +y (atan2(-dx, dy)); a quarter turn counter-clockwise faces -x, heading 1024.
        self.assertEqual(m.turn_heading(0, 90), 1024)
        self.assertEqual(m.turn_heading(4000, 45), (4000 + 512) % 4096)
        self.assertEqual(m.turn_heading(100, -9), 4096 + 100 - 102)

    def test_the_gate_measured_turns_match_the_keeps(self):
        # Snowdonia's big gate: classic at 90 degrees from the centre, live at 135.
        snow = next(s for s in m.STRUCTURES if s['name'] == 'Snowdonia Fortress')
        gx, gy = snow['src'][0], snow['src'][1] + 1125
        x, y = m.carry(snow, gx, gy)
        import math
        self.assertAlmostEqual(math.degrees(math.atan2(y - snow['dst'][1], x - snow['dst'][0])), 135, places=3)


class GeometryPlacementTests(unittest.TestCase):
    def test_a_tower_guard_goes_to_the_live_tower_top(self):
        live = FakeGeometry(lambda x, y: [5738.0, 6420.0])  # ground and live's lower tower top
        self.assertEqual(m.place_on_geometry(live, 0, 0, 6568)[2], 6420.0)

    def test_a_surface_without_standing_room_is_skipped(self):
        # Below x=100 every surface within 200 units has something 16-160 units over it.
        live = FakeGeometry(lambda x, y: [6500.0, 6560.0, 6700.0, 6720.0] if x < 100 else [6500.0])
        x, y, z, how = m.place_on_geometry(live, 0, 0, 6500)
        self.assertGreaterEqual(x, 100 - m.SEARCH_STEP)
        self.assertEqual(z, 6500.0)


class DoorTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('create table Door (Door_ID text, InternalID int, X int, Y int, Z int, Heading int)')

    def test_a_moved_door_takes_lives_position_and_turn(self):
        self.db.execute("insert into Door values ('a', 207156901, 334912, 421471, 5335, 0)")
        changes, unresolved = m.plan_doors(self.db, 207, {207156901: ('hborderkeep1.nif', 334912, 421471, 5335, 568)},
                                           {207156901: ('hborderkeep1.nif', 333504, 419777, 5186, 2616)})
        self.assertEqual(unresolved, [])
        self.assertEqual(changes[0]['new'], dict(InternalID=207156901, X=333504, Y=419777, Z=5186, Heading=2048))

    def test_a_renumbered_variant_keeps_its_row_under_the_new_id(self):
        self.db.execute("insert into Door values ('b', 2011301, 530837, 478264, 2231, 100)")
        changes, _ = m.plan_doors(self.db, 2, {2011301: ('btavern.nif', 530837, 478264, 2231, 2390)},
                                  {2184201: ('btavern_normal.nif', 530837, 478264, 2231, 2389)})
        self.assertEqual(changes[0]['new']['InternalID'], 2184201)
        self.assertEqual(changes[0]['reason'], 'door renumbered')

    def test_a_door_live_does_not_have_is_left_alone(self):
        self.db.execute("insert into Door values ('c', 2011101, 531748, 480112, 2217, 0)")
        changes, unresolved = m.plan_doors(self.db, 2, {2011101: ('bhouse2.nif', 531748, 480112, 2217, 0)}, {})
        self.assertEqual(changes, [])
        self.assertEqual(unresolved[0]['id'], 2011101)


class ApplyRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.db_path, self.plan_path, self.backups = root / 'world.db', root / 'plan.json', root / 'backups'
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute('create table Mob (Mob_ID text, X int, Y int, Z int, Name text)')
            con.execute("insert into Mob values ('m1', 10, 20, 30, 'guard'), ('m2', 1, 2, 3, 'untouched')")
            con.commit()
        self.plan_path.write_text(json.dumps(dict(format=1, changes=[
            dict(table='Mob', key_column='Mob_ID', key='m1', old=dict(X=10, Y=20, Z=30), new=dict(X=11, Y=21, Z=31), reason='t')],
            unresolved=[])), encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def rows(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            return con.execute('select Mob_ID, X, Y, Z from Mob order by Mob_ID').fetchall()

    def test_apply_then_rollback(self):
        folder = m.apply(self.db_path, self.plan_path, self.backups, write=True)
        self.assertEqual(self.rows(), [('m1', 11, 21, 31), ('m2', 1, 2, 3)])
        self.assertTrue((folder / 'world.db').exists())
        m.rollback(self.db_path, folder, write=True)
        self.assertEqual(self.rows(), [('m1', 10, 20, 30), ('m2', 1, 2, 3)])

    def test_refuses_rows_changed_since_the_plan(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute("update Mob set X=99 where Mob_ID='m1'")
            con.commit()
        with self.assertRaises(SystemExit):
            m.apply(self.db_path, self.plan_path, self.backups, write=True)
        self.assertEqual(self.rows()[0], ('m1', 99, 20, 30))

    def test_skip_changed_leaves_rewritten_rows_and_rolls_back_only_what_it_wrote(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute("update Mob set Z=99 where Mob_ID='m1'")
            con.commit()
        folder = m.apply(self.db_path, self.plan_path, self.backups, write=True, skip_changed=True)
        self.assertEqual(self.rows()[0], ('m1', 10, 20, 99))
        m.rollback(self.db_path, folder, write=True)
        self.assertEqual(self.rows()[0], ('m1', 10, 20, 99))

    def test_preview_changes_nothing(self):
        self.assertIsNone(m.apply(self.db_path, self.plan_path, self.backups, write=False))
        self.assertEqual(self.rows()[0], ('m1', 10, 20, 30))


if __name__ == '__main__':
    unittest.main()
