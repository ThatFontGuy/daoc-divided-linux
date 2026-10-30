import hashlib
from pathlib import Path
import sqlite3
import struct
import unittest
from unittest import mock
from contextlib import redirect_stdout
import io
import json
import shutil
import tempfile

import install as installer

from patch_client import patch
from seed_stormforged import seed, PACKAGE

ROOT = Path(__file__).resolve().parents[3]
WORLD = ROOT/"playable/editions/0.36-no-custom-class/runtime/data/opendaoc.sqlite3.db"
CLIENT = ROOT/"playable/runtime/client-opendaoc/app/game.dll"


@unittest.skipUnless(WORLD.is_file(), "Requires the clean 0.36 edition world")
class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        with sqlite3.connect(WORLD.as_uri()+"?mode=ro", uri=True) as source:
            source.backup(self.db)

    def tearDown(self):
        self.db.close()

    def test_every_button_resolves_to_its_own_spell_using_classic_packet_address(self):
        seed(self.db)
        rows=self.db.execute("SELECT l.LineName,l.Level,s.SpellID,s.Type,s.CastTime,s.Range,s.Radius FROM LineXSpell l JOIN Spell s ON s.SpellID=l.SpellID WHERE s.PackageID=?",(PACKAGE,)).fetchall()
        addresses={}
        for row in rows:
            address=(row['LineName'],row['Level'])
            self.assertNotIn(address,addresses, f"Classic client would cast {addresses.get(address)} instead of {row['SpellID']}")
            addresses[address]=row['SpellID']
        for tier,level in enumerate((1,5,10,15,20,30,40,50)):
            n=62000+tier*20
            for suffix,offset in (('Stormbolt',0),('Thunderclap',1),('ChainLightning',2),('Stormheart',3),('Stormsong',5),('ThunderforgedWard',7),('Stormrest',9),('Stormhammer',16)):
                self.assertEqual(addresses[('Stormforged.'+suffix,level)],n+offset)
            heal=next(r for r in rows if r['SpellID']==n+9)
            self.assertEqual((heal['Type'],heal['CastTime'],heal['Radius']),('StormforgedRest',3,0))
            ward=next(r for r in rows if r['SpellID']==n+7)
            self.assertEqual(ward['Type'],'StormforgedWard')
            if level>=10:
                self.assertEqual(addresses[('Stormforged.LightningBomb',level)],n+12)
                bomb=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(n+12,)).fetchone()
                burst=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(bomb['SubSpellID'],)).fetchone()
                self.assertEqual(bomb['Type'],'SummonAnimistFnF')
                self.assertEqual(bomb['CastTime'],3)
                self.assertEqual(burst['Radius'],250)
                self.assertIsNotNone(self.db.execute("SELECT 1 FROM NpcTemplate WHERE TemplateId=?",(bomb['LifeDrainReturn'],)).fetchone())

    def test_commander_support_roster_has_full_level_summons_and_real_spells(self):
        seed(self.db)
        for id, template, expected in ((62206,60171003,{'Heal','DirectDamage','CombatSpeedDebuff'}),
                                       (62207,60171004,{'DirectDamage','EnergyResistDebuff'})):
            summon=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(id,)).fetchone()
            self.assertEqual((summon['Damage'],summon['Value'],summon['LifeDrainReturn']),(-100,255,template))
            pet=self.db.execute("SELECT * FROM NpcTemplate WHERE TemplateId=?",(template,)).fetchone()
            ids=[int(x) for x in pet['Spells'].split(';')]
            types={self.db.execute("SELECT Type FROM Spell WHERE SpellID=?",(x,)).fetchone()[0] for x in ids}
            self.assertTrue(expected.issubset(types))
            self.assertFalse(self.db.execute("SELECT 1 FROM LineXSpell WHERE SpellID=?",(id,)).fetchone())
        taunt=self.db.execute("SELECT Type,CastTime,RecastDelay,Radius FROM Spell WHERE SpellID=62219").fetchone()
        self.assertEqual(tuple(taunt),('Taunt',0,5,350))

    def test_mender_uses_top_native_buffs_without_concentration_or_player_buttons(self):
        from seed_stormforged import MENDER_BUFF_SOURCES
        seed(self.db)
        mender=self.db.execute("SELECT Spells FROM NpcTemplate WHERE TemplateId=60171003").fetchone()[0]
        for offset,source_id in enumerate(MENDER_BUFF_SOURCES):
            id=62220+offset
            original=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(source_id,)).fetchone()
            private=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(id,)).fetchone()
            self.assertIn(str(id),mender.split(';'))
            self.assertEqual(private['Value'],original['Value'])
            self.assertEqual(private['Type'],original['Type'])
            self.assertEqual((private['Target'],private['Concentration'],private['Power'],private['Radius']),('Realm',0,0,0))
            self.assertFalse(self.db.execute("SELECT 1 FROM LineXSpell WHERE SpellID=?",(id,)).fetchone())
            self.assertNotEqual(private['TooltipId'],private['Icon'])

    def test_hybrid_enable_preserves_world_ownership_and_saves_and_is_idempotent(self):
        from seed_hybrid_coop import enable
        before={t:list(self.db.execute(f'SELECT * FROM "{t}"')) for t in ('Keep','Account','DOLCharacters','Inventory','PlayerXEffect')}
        enable(self.db)
        enable(self.db)
        self.assertEqual(self.db.execute("SELECT Value FROM ServerProperty WHERE Key='hybrid_coop_pvp'").fetchone()[0],'True')
        self.assertEqual(self.db.execute("SELECT Value FROM ServerProperty WHERE Key='claim_num'").fetchone()[0],'1')
        self.assertEqual(self.db.execute("SELECT Value FROM ServerProperty WHERE Key='allow_bg_claim'").fetchone()[0],'True')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM ServerProperty WHERE Key='hybrid_coop_pvp'").fetchone()[0],1)
        for table,rows in before.items(): self.assertEqual(list(self.db.execute(f'SELECT * FROM "{table}"')),rows)

    def test_hybrid_refuses_unknown_zone_boundaries_before_setting_any_flags(self):
        from seed_hybrid_coop import enable
        self.db.execute("UPDATE Zones SET RegionID=100 WHERE ZoneID=11")
        with self.assertRaisesRegex(ValueError,'frontier boundary'): enable(self.db)
        self.assertFalse(self.db.execute("SELECT 1 FROM ServerProperty WHERE Key='hybrid_coop_pvp'").fetchone())

    def test_storm_bombs_duration_cooldown_pulse_and_release_clump(self):
        seed(self.db)
        for tier in range(2,8):
            n=62000+tier*20
            summon=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(n+12,)).fetchone()
            self.assertEqual((summon['Duration'],summon['RecastDelay']),(120,0))
            ranged=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(summon['SubSpellID'],)).fetchone()
            pulse=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(ranged['SpellID']+4,)).fetchone()
            self.assertEqual((pulse['Target'],pulse['Range'],pulse['Radius'],pulse['CastTime'],pulse['RecastDelay']),('Enemy',0,350,0,4))
        release=self.db.execute("SELECT s.* FROM Spell s JOIN LineXSpell l ON l.SpellID=s.SpellID WHERE l.LineName='Stormforged.ReleaseStormClump'").fetchall()
        self.assertEqual(len(release),1)
        self.assertEqual((release[0]['Type'],release[0]['Target'],release[0]['Radius'],release[0]['Power']),('TurretsRelease','Pet',500,0))

    def test_heroic_unlocks_effects_and_private_tooltips(self):
        seed(self.db)
        for id,level,type,line in ((62200,40,'StormforgedAvatar','AvatarOfThor'),(62201,10,'StormforgedStormguard','Stormguard'),(62202,20,'StormforgedSecondThunder','SecondThunder')):
            spell=self.db.execute("SELECT s.*,l.Level,l.LineName FROM Spell s JOIN LineXSpell l ON s.SpellID=l.SpellID WHERE s.SpellID=?",(id,)).fetchone()
            self.assertEqual((spell['Type'],spell['Level'],spell['LineName']),(type,level,'Stormforged.'+line))
            self.assertEqual(spell['Target'],'Self')
            self.assertNotEqual(spell['TooltipId'],spell['Icon'])
            self.assertIsNotNone(self.db.execute("SELECT 1 FROM Spell WHERE SpellID=?",(spell['SubSpellID'],)).fetchone())
        avatar=self.db.execute("SELECT Value,Duration,RecastDelay,Frequency FROM Spell WHERE SpellID=62200").fetchone()
        self.assertEqual(tuple(avatar),(918,60,180,20))

    def test_travel_and_network_spell_unlocks_and_stormstep_range(self):
        seed(self.db)
        for id,level,type,line in ((62210,15,'StormforgedStep','Stormstep'),(62211,30,'StormforgedRide','RideTheStorm'),(62212,20,'StormforgedRecall','ThunderRecall'),(62213,25,'StormforgedEye','EyeOfTheStorm')):
            spell=self.db.execute("SELECT s.*,l.Level,l.LineName FROM Spell s JOIN LineXSpell l ON s.SpellID=l.SpellID WHERE s.SpellID=?",(id,)).fetchone()
            self.assertEqual((spell['Type'],spell['Level'],spell['LineName']),(type,level,'Stormforged.'+line))
            self.assertEqual(spell['CastTime'],0)
        step=self.db.execute("SELECT Range,RecastDelay,SubSpellID FROM Spell WHERE SpellID=62210").fetchone()
        self.assertEqual(tuple(step),(2000,8,62216))
        recall=self.db.execute("SELECT Range,RecastDelay FROM Spell WHERE SpellID=62212").fetchone()
        self.assertEqual(tuple(recall),(1000,5))
        eye=self.db.execute("SELECT Radius,Frequency FROM Spell WHERE SpellID=62213").fetchone()
        self.assertEqual(tuple(eye),(600,40))

    def test_shield_permission_has_one_unambiguous_large_shield_grant(self):
        seed(self.db)
        ranks=self.db.execute("SELECT SpecLevel,AbilityLevel FROM SpecXAbility WHERE Spec='StormforgedCareer' AND AbilityKey='Shield'").fetchall()
        self.assertEqual([tuple(row) for row in ranks],[(1,3)])

    def test_attack_shapes_and_thane_icons(self):
        seed(self.db)
        for tier in range(8):
            n=62000+tier*20
            single=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(n+1,)).fetchone()
            pulse=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(n+2,)).fetchone()
            hammer=self.db.execute("SELECT * FROM Spell WHERE SpellID=?",(n+16,)).fetchone()
            self.assertEqual((single['CastTime'],single['Radius']),(0,0))
            self.assertGreater(single['Range'],0)
            self.assertEqual((pulse['CastTime'],pulse['Range'],pulse['Radius']),(0,0,350))
            self.assertEqual((hammer['CastTime'],hammer['Range'],hammer['Radius'],hammer['ClientEffect']),(2.5,1500,350,3538))
            self.assertEqual(self.db.execute("SELECT Icon FROM Spell WHERE SpellID=?",(n+7,)).fetchone()[0],3531)
            self.assertNotEqual(single['TooltipId'],single['Icon'])

    def test_idempotent_and_stock_content_preserved(self):
        original = self.db.execute("SELECT * FROM Spell WHERE SpellID=3508").fetchone()
        counts = {t: self.db.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
                  for t in ("Account", "DOLCharacters", "Inventory")}
        first = seed(self.db)
        second = seed(self.db)
        self.assertEqual(first, second)
        self.assertEqual(tuple(self.db.execute("SELECT * FROM Spell WHERE SpellID=3508").fetchone()), original)
        for table, count in counts.items():
            self.assertEqual(self.db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0], count)
        self.assertEqual(self.db.execute("PRAGMA quick_check").fetchone()[0], "ok")

    def test_equipment_intrinsic_at_one_and_stats_capped_at_forty(self):
        seed(self.db)
        for key, rank in (("MidArmor", 4), ("Shield", 3)):
            row = self.db.execute("SELECT SpecLevel FROM SpecXAbility WHERE Spec='StormforgedCareer' AND AbilityKey=? AND AbilityLevel=?", (key,rank)).fetchone()
            self.assertEqual(row[0],1)
        ward = self.db.execute("SELECT s.Value FROM Spell s JOIN LineXSpell l ON l.SpellID=s.SpellID WHERE s.Type='StormforgedWard' AND l.Level=40").fetchone()
        self.assertEqual(ward[0],100)
        self.assertEqual(self.db.execute("SELECT Frequency FROM Spell WHERE Type='StormforgedAura' AND PackageID=? LIMIT 1",(PACKAGE,)).fetchone()[0],40)
        self.assertGreater(self.db.execute("SELECT count(*) FROM StartupLocation WHERE ClassID=64").fetchone()[0],0)

    def test_new_characters_receive_midgard_chain_hammer_large_shield_and_shared_recall(self):
        seed(self.db)
        rows=self.db.execute("SELECT i.Name,i.Object_Type,i.Item_Type,i.Realm,i.Type_Damage FROM StarterEquipment s JOIN ItemTemplate i ON i.Id_nb=s.TemplateID WHERE s.Class IN ('64','0')").fetchall()
        armor=[r for r in rows if r['Object_Type']==35]
        self.assertEqual({r['Item_Type'] for r in armor},{21,22,23,25,27,28})
        self.assertTrue(all(r['Realm']==2 for r in armor))
        self.assertTrue(any(r['Object_Type']==12 for r in rows),'hammer')
        self.assertTrue(any(r['Object_Type']==42 and r['Type_Damage']==3 for r in rows),'large shield')
        self.assertEqual(sum(r['Name']=='Personal Bind Recall Stone' for r in rows),1)

    def test_maintained_support_has_no_repeated_attack_visuals_and_ward_has_damage_add(self):
        seed(self.db)
        for row in self.db.execute("SELECT s.ClientEffect,w.ClientEffect FROM Spell s JOIN Spell w ON w.SpellID=s.SubSpellID WHERE s.Type='StormforgedChant'"):
            self.assertEqual(tuple(row),(3531,0))
        for row in self.db.execute("SELECT s.Type,s.ClientEffect FROM Spell w JOIN Spell s ON s.SpellID=w.SpellID+8 WHERE w.Type='StormforgedWard'"):
            self.assertEqual(tuple(row),('DamageAdd',0))

    def test_collision_is_rejected_before_changes(self):
        self.db.execute("UPDATE Spell SET SpellID=62000 WHERE SpellID=3508")
        count = self.db.execute("SELECT count(*) FROM Spell").fetchone()[0]
        with self.assertRaises(ValueError):
            seed(self.db)
        self.assertEqual(self.db.execute("SELECT count(*) FROM Spell").fetchone()[0],count)


class RvrRestoreTests(unittest.TestCase):
    def test_disable_restores_rvr_settings_and_preserves_other_settings(self):
        from seed_hybrid_coop import disable
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE ServerProperty (Key TEXT, Value TEXT, LastTimeRowUpdated TEXT)")
            db.executemany("INSERT INTO ServerProperty VALUES (?, ?, '')", [
                ("hybrid_coop_pvp", "True"), ("allow_bg_claim", "True"),
                ("claim_num", "1"), ("enable_stormforged", "True")])
            disable(db)
            disable(db)
            self.assertEqual(dict(db.execute("SELECT Key, Value FROM ServerProperty")), {
                "hybrid_coop_pvp": "False", "allow_bg_claim": "False",
                "claim_num": "8", "enable_stormforged": "True"})


@unittest.skipUnless(CLIENT.is_file(), "Requires the supported 0.36 client")
class ClientPatchTests(unittest.TestCase):
    def test_patch_is_deterministic_and_preserves_other_realms(self):
        original = CLIENT.read_bytes()
        patched = patch(original)
        self.assertEqual(patched, patch(original))
        self.assertIn(b"Stormforged\0",patched)
        pe=struct.unpack_from("<I",original,60)[0]
        self.assertEqual(struct.unpack_from("<H",patched,pe+6)[0],struct.unpack_from("<H",original,pe+6)[0]+1)
        # The first and third Mauler label initializers (Hib and Alb) are untouched.
        from importlib.util import spec_from_file_location, module_from_spec
        spec=spec_from_file_location("label_helper",ROOT/"source/server/tools/patch_sluaghbinder_client_label.py")
        helper=module_from_spec(spec);spec.loader.exec_module(helper)
        for va,size in [(0x44f3c5,38),(0x44f407,29)]:
            offset=helper._pe_offset(original,va)
            self.assertEqual(original[offset:offset+size],patched[offset:offset+size])
        self.assertEqual(hashlib.sha256(CLIENT.read_bytes()).digest(),hashlib.sha256(original).digest())

    def test_unknown_or_already_patched_build_is_rejected(self):
        original=CLIENT.read_bytes()
        with self.assertRaises(ValueError):patch(original+b"changed")
        with self.assertRaises(ValueError):patch(patch(original))


@unittest.skipUnless(WORLD.is_file() and CLIENT.is_file(), "Requires clean release files")
class InstallerTests(unittest.TestCase):
    def test_install_and_guarded_rollback_on_disposable_files(self):
        with tempfile.TemporaryDirectory(prefix="stormforged-install-test-", dir=ROOT/"artifacts") as temp:
            game=Path(temp)
            targets=["runtime/server/GameServer.dll", "runtime/server/lib/GameServer.dll", "runtime/server/win-x64/GameServer.dll"]
            for relative in targets:
                path=game/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"original-server")
            client=game/"runtime/client-opendaoc/app/game.dll";client.parent.mkdir(parents=True);shutil.copy2(CLIENT,client)
            world=game/"runtime/data/opendaoc.sqlite3.db";world.parent.mkdir(parents=True);shutil.copy2(WORLD,world)
            original={p:installer.digest(game/p) for p in targets+[str(client.relative_to(game)),str(world.relative_to(game))]}
            with mock.patch.object(installer,"stopped") as stopped, mock.patch("sys.argv",["install.py",str(game),"--apply"]), redirect_stdout(io.StringIO()):
                installer.main()
                self.assertEqual(stopped.call_count,2)
            backup=next(game.glob("stormforged-backup-*"))
            record=json.loads((backup/"manifest.json").read_text())
            self.assertEqual(len(record["files"]),5)
            installed_client=installer.digest(client)
            # Any later save change must block the ENTIRE rollback before client/server files change.
            with world.open("ab") as stream:stream.write(b"later gameplay")
            with mock.patch.object(installer,"stopped"), mock.patch("sys.argv",["install.py",str(game),"--rollback",str(backup)]), self.assertRaises(ValueError):
                installer.main()
            self.assertEqual(installer.digest(client),installed_client)
            with world.open("r+b") as stream:stream.truncate(world.stat().st_size-len(b"later gameplay"))
            with mock.patch.object(installer,"stopped"), mock.patch("sys.argv",["install.py",str(game),"--rollback",str(backup)]), redirect_stdout(io.StringIO()):
                installer.main()
            for relative,sha in original.items():self.assertEqual(installer.digest(game/relative),sha)


if __name__ == "__main__":
    unittest.main()
