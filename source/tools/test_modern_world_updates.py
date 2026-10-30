"""The release-by-release world updates (modern_world_updates.py), as build_modern_test_package.py uses them for each new release."""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

import make_patch
import modern_world_updates as m


def world(path: Path, mobs: dict[str, tuple]):
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE Mob (Mob_ID TEXT PRIMARY KEY, Name TEXT, X INTEGER, Size INTEGER)')
    con.execute('CREATE TABLE DOLCharacters (DOLCharacters_ID TEXT PRIMARY KEY, Name TEXT)')
    con.executemany('INSERT INTO Mob VALUES (?, ?, ?, ?)', [(k, *v) for k, v in mobs.items()])
    con.commit()
    con.close()


def mobs(path: Path) -> dict:
    con = sqlite3.connect(path)
    out = {r[0]: r[1:] for r in con.execute('SELECT Mob_ID, Name, X FROM Mob')}
    con.close()
    return out


def bring_up_to_date(path: Path, chain: Path):
    """What the launcher does (WorldUpdates.cs): every step the world's offline_patch_log doesn't list, in order."""
    con = sqlite3.connect(path)
    done = set()
    if con.execute("SELECT count(*) FROM sqlite_master WHERE name='offline_patch_log'").fetchone()[0]:
        done = {r[0] for r in con.execute('SELECT Version FROM offline_patch_log')}
    con.execute('CREATE TABLE IF NOT EXISTS offline_patch_log (Version TEXT PRIMARY KEY, AppliedUtc TEXT, Notes TEXT)')
    ran = []
    for step in m.load(chain)['Steps']:
        if step['Version'] not in done:
            make_patch.apply_world_update(con, m.json.loads((chain / step['File']).read_text(encoding='utf-8')))
            con.execute("INSERT INTO offline_patch_log VALUES (?, '', '')", (step['Version'],))
            ran.append(step['Version'])
    con.commit()
    con.close()
    return ran


class NextReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.chain, self.baselines = self.tmp / 'chain', self.tmp / 'baselines'
        self.baselines.mkdir()
        # three published releases: dev1, dev2 moves the guard, dev3 adds a battleground keeper
        world(self.baselines / 'world-r1.sqlite3.db', {'guard': ('Guard', 100, 50), 'rat': ('Rat', 5, 20)})
        world(self.baselines / 'world-r2.sqlite3.db', {'guard': ('Guard', 150, 51), 'rat': ('Rat', 5, 20)})
        world(self.baselines / 'world-r3.sqlite3.db', {'guard': ('Guard', 150, 49), 'rat': ('Rat', 5, 20), 'keeper': ('Keep Lord', 900, 60)})
        m.seed(self.chain, [(v, self.baselines / f'world-{v}.sqlite3.db') for v in ('r1', 'r2', 'r3')])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build_release(self, version: str, mobs_: dict) -> Path:
        """The build's world steps for a new release (build_modern_test_package.build)."""
        clean = self.tmp / f'clean-{version}.db'
        clean.unlink(missing_ok=True)
        world(clean, mobs_)
        previous = m.previous_release(self.chain, version)
        m.add_step(self.chain, version, previous, m.baseline(previous, self.baselines), clean)
        m.stamp(clean, self.chain)
        m.keep_baseline(version, clean, self.baselines)
        return clean

    def test_a_new_release_reaches_every_older_world_and_keeps_saves(self):
        clean = self.build_release('r4', {'guard': ('Guard', 175, 50), 'rat': ('Giant Rat', 5, 20), 'keeper': ('Keep Lord', 900, 60)})
        self.assertEqual([s['Version'] for s in m.load(self.chain)['Steps']], ['r2', 'r3', 'r4'])
        self.assertEqual(m.load(self.chain)['Steps'][-1]['From'], 'r3')
        self.assertTrue((self.baselines / 'world-r4.sqlite3.db').is_file(), 'kept for the next release')

        played = self.tmp / 'played.db'          # a tester still on the first release, with a character
        shutil.copy2(self.baselines / 'world-r1.sqlite3.db', played)
        con = sqlite3.connect(played)
        con.execute("INSERT INTO DOLCharacters VALUES ('c1', 'Tester')")
        con.commit()
        con.close()
        self.assertEqual(bring_up_to_date(played, self.chain), ['r2', 'r3', 'r4'])
        self.assertEqual(mobs(played), mobs(clean))
        con = sqlite3.connect(played)
        self.assertEqual(con.execute('SELECT Name FROM DOLCharacters').fetchall(), [('Tester',)])
        con.close()
        self.assertEqual(bring_up_to_date(played, self.chain), [], 'each step runs once')

        fresh = self.tmp / 'fresh.db'            # a fresh install of the new release
        shutil.copy2(clean, fresh)
        self.assertEqual(bring_up_to_date(fresh, self.chain), [])
        self.assertEqual(m.check(self.chain, [(v, self.baselines / f'world-{v}.sqlite3.db') for v in ('r1', 'r2', 'r3')], clean),
                         {v: {'rerolled_monsters_differ': 0} for v in ('r1', 'r2', 'r3')})

    def test_building_the_same_release_again_replaces_its_step(self):
        self.build_release('r4', {'guard': ('Guard', 175, 50), 'rat': ('Rat', 5, 20), 'keeper': ('Keep Lord', 900, 60)})
        clean = self.build_release('r4', {'guard': ('Guard', 180, 50), 'rat': ('Rat', 5, 20), 'keeper': ('Keep Lord', 900, 60)})
        steps = m.load(self.chain)['Steps']
        self.assertEqual([(s['Version'], s['From']) for s in steps], [('r2', 'r1'), ('r3', 'r2'), ('r4', 'r3')])
        played = self.tmp / 'played.db'
        shutil.copy2(self.baselines / 'world-r3.sqlite3.db', played)
        bring_up_to_date(played, self.chain)
        self.assertEqual(mobs(played), mobs(clean))

    def test_an_older_label_or_a_missing_world_stops_the_build(self):
        with self.assertRaises(SystemExit):
            m.previous_release(self.chain, 'r2')            # already published and not the last step
        self.build_release('r4', {'guard': ('Guard', 150, 49)})
        (self.baselines / 'world-r4.sqlite3.db').unlink()
        with self.assertRaises(SystemExit):
            m.baseline(m.previous_release(self.chain, 'r5'), self.baselines)


if __name__ == '__main__':
    unittest.main()
