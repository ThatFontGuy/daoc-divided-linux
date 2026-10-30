"""Guardrail and round-trip tests using isolated, synthetic world databases."""
import copy
import json
import sqlite3
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zlib
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from .editor import Editor, FIELDS, KEYS, Handler, ThreadingHTTPServer, REPO, pcx, validate_changes


def mpk(path, files):
    directory, blocks, offset = bytearray(), [], 0
    for name, data in files.items():
        packed = zlib.compress(data)
        directory.extend(name.encode().ljust(256, b'\0') + struct.pack('<7I', 0, 0, 0, len(data), offset, len(packed), 0))
        blocks.append(packed)
        offset += len(packed)
    names = zlib.compress(b'world-editor-test\0')
    dirs = zlib.compress(directory)
    header = struct.pack('<4I', 0, len(dirs), len(names), len(files))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'MPAK\0' + bytes(b ^ i for i,b in enumerate(header)) + names + dirs + b''.join(blocks))


class EditorTests(unittest.TestCase):
    def setUp(self):
        scratch = REPO / 'artifacts/world-editor-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.db = self.root / 'runtime/data/world.db'
        self.db.parent.mkdir(parents=True)
        self.client = self.root / 'client'
        mpk(self.client / 'zones/zones.mpk', {'zones.dat': b'[zone200]\nname=Test\nregion=200\nregion_offset_x=1\nregion_offset_y=2\nwidth=8\nheight=8\ntype=1\n===============\nBanner\n'})
        with closing(sqlite3.connect(self.db)) as con, con:
            for table, fields in FIELDS.items():
                cols = {KEYS[table]: 'INTEGER PRIMARY KEY' if table=='Zones' else 'TEXT PRIMARY KEY', **{k: 'TEXT' if v=='text' else 'INTEGER' for k,v in fields.items()}}
                if table in ('Mob','WorldObject'):
                    cols['Region'] = 'INTEGER'
                if table == 'Door':
                    cols['InternalID'] = 'INTEGER'
                if table == 'Zones':
                    cols.update({k:'INTEGER' for k in ('RegionID','OffsetX','OffsetY','Width','Height')})
                con.execute(f'CREATE TABLE {table} (' + ','.join(f'{k} {v}' for k,v in cols.items()) + ')')
                values = {k: ('Test' if t.startswith('TEXT') else 0) for k,t in cols.items()}
                values[KEYS[table]] = 200 if table=='Zones' else table+'-1'
                if table in ('Mob','WorldObject','Door'):
                    values.update(X=9000,Y=17000,Z=100,Heading=10)
                if table in ('Mob','WorldObject'):
                    values['Region']=200
                if table=='Mob':
                    values['Size']=50
                if table=='Door':
                    values['InternalID']=200000001
                if table=='Zones':
                    values.update(RegionID=200,OffsetX=1,OffsetY=2,Width=8,Height=8)
                con.execute(f'INSERT INTO {table} ({",".join(values)}) VALUES ({",".join("?" for _ in values)})', tuple(values.values()))
            con.execute('CREATE TABLE PlayerProgress (Value INTEGER)')
            con.execute('INSERT INTO PlayerProgress VALUES (10)')
        self.ed = Editor(self.db,self.client,self.root/'state')
        self.closed = patch('world_editor.editor.ensure_closed')
        self.closed.start()

    def tearDown(self):
        self.closed.stop()
        self.temp.cleanup()

    def change(self, table='Mob', field='X', before=9000, after=9100):
        return dict(table=table,key=table+'-1',before={field:before},after={field:after})

    def make_patch(self, changes=None):
        return self.ed.patch(changes or [self.change()], self.ed.world_fingerprint())

    def value(self, table='Mob', field='X'):
        with closing(sqlite3.connect(self.db)) as con, con:
            return con.execute(f'SELECT {field} FROM {table}').fetchone()[0]

    def test_zone_filters_and_client_layout(self):
        z=self.ed.zone(200)
        self.assertEqual(z['zone']['Name'],'Test')
        self.assertTrue(z['zone']['layoutMatches'])
        self.assertEqual({e['table'] for e in z['entities']},{'Mob','WorldObject','Door'})
        self.assertEqual(len(self.ed.czones),1)

    def test_mid_transaction_error_rolls_back_every_row(self):
        p=self.make_patch([self.change(),self.change('WorldObject')])
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("CREATE TRIGGER deny_object BEFORE UPDATE ON WorldObject BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.ed.apply(p)
        self.assertEqual(self.value(),9000)
        self.assertEqual(self.value('WorldObject'),9000)

    def test_wal_snapshot_and_apply(self):
        with closing(sqlite3.connect(self.db)) as con:
            con.execute('PRAGMA journal_mode=WAL')
        result=self.ed.apply(self.make_patch())
        self.assertEqual(self.value(),9100)
        self.assertTrue((Path(result['backup'])/'world-before.db').is_file())

    def test_sync_apply_and_restore(self):
        target=self.root/'target';mpk(target/'zones/zones.mpk',{'zones.dat':b'old'})
        self.ed.targets={'0':target}
        original=(target/'zones/zones.mpk').read_bytes()
        report=self.ed.compare('0')
        with patch('modern_world_overlay.check_closed'):
            result=self.ed.sync('0',report['id'])
            self.assertEqual((target/'zones/zones.mpk').read_bytes(),(self.client/'zones/zones.mpk').read_bytes())
            from .editor import overlay
            overlay.rollback(target,Path(result['backup']),True)
        self.assertEqual((target/'zones/zones.mpk').read_bytes(),original)

    def test_apply_backup_and_row_restore_preserves_player_progress(self):
        patch=self.make_patch()
        result=self.ed.apply(patch)
        self.assertEqual(self.value(),9100)
        with closing(sqlite3.connect(Path(result['backup'])/'world-before.db')) as con:
            self.assertEqual(con.execute('SELECT X FROM Mob').fetchone()[0],9000)
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute('UPDATE PlayerProgress SET Value=99')
        self.ed.rollback(result['id'])
        self.assertEqual(self.value(),9000)
        self.assertEqual(self.value('PlayerProgress','Value'),99)

    def test_conflict_refuses_entire_patch(self):
        p=self.make_patch([self.change(),self.change('WorldObject',before=123)])
        with self.assertRaisesRegex(ValueError,'Conflict'):
            self.ed.apply(p)
        self.assertEqual(self.value(),9000)

    def test_stale_patch_refuses_overwrite(self):
        p=self.make_patch()
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute('UPDATE Mob SET X=9101')
        with self.assertRaisesRegex(ValueError,'Conflict'):
            self.ed.apply(p)
        self.assertEqual(self.value(),9101)

    def test_restore_refuses_later_world_change(self):
        result=self.ed.apply(self.make_patch())
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute('UPDATE Mob SET X=9111')
        with self.assertRaisesRegex(ValueError,'Conflict'):
            self.ed.rollback(result['id'])

    def test_unknown_tables_and_columns_and_invalid_numbers(self):
        for c in [self.change('PlayerProgress'), self.change(field='Region'), self.change(field='Heading',before=10,after=65536),
                  self.change(after=1.5), self.change(after=True), self.change(field='Name',before='Test',after='x'*256)]:
            with self.subTest(c=c),self.assertRaises(ValueError):
                validate_changes([c])

    def test_duplicate_row_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            validate_changes([self.change(),self.change()])

    def test_changed_client_blocks_patch(self):
        p=self.make_patch()
        (self.client/'zones/new-file.nif').write_bytes(b'changed geometry')
        with self.assertRaisesRegex(ValueError,'different client'):
            self.ed.apply(p)

    def test_locked_database_refuses_apply(self):
        p=self.make_patch()
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):
                self.ed.apply(p)
        self.assertEqual(self.value(),9000)

    def test_backups_path_traversal_refused(self):
        with self.assertRaises(ValueError):
            self.ed.rollback('../other')

    def test_preview_does_not_modify_database(self):
        original=self.db.read_bytes()
        self.make_patch()
        self.assertEqual(original,self.db.read_bytes())

    def test_http_authentication_and_origin_guards(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.editor=self.ed
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            for headers in [{},{'X-Editor-Token':self.ed.token,'Origin':'https://evil.example'},
                            {'X-Editor-Token':self.ed.token,'Host':'evil.example'}]:
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(urllib.request.Request(url+'/api/config',headers=headers))
            with urllib.request.urlopen(urllib.request.Request(url+'/api/config',headers={'X-Editor-Token':self.ed.token})) as r:
                self.assertEqual(r.status,200)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_client_sync_preview_and_hash_conflict(self):
        target=self.root/'target';mpk(target/'zones/zones.mpk',{'zones.dat':b'old'})
        self.ed.targets={'0':target}
        report=self.ed.compare('0')
        self.assertEqual(len(report['manifest']['entries']),1)
        before=(target/'zones/zones.mpk').read_bytes()
        (target/'zones/zones.mpk').write_bytes(b'concurrent edit')
        with self.assertRaisesRegex(ValueError,'changed after comparison'):
            self.ed.sync('0',report['id'])
        self.assertNotEqual(before,(target/'zones/zones.mpk').read_bytes())

    def test_pcx_rle_decoder(self):
        header=bytearray(128);header[0]=10;header[2]=1;header[3]=8;header[65]=1
        struct.pack_into('<4H',header,4,0,0,1,1);struct.pack_into('<H',header,66,2)
        self.assertEqual(pcx(bytes(header)+bytes([0xc2,5,6,7])),[[5,5],[6,7]])

    def make_content_table(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute('CREATE TABLE MerchantItem (ItemListID VARCHAR(255) NOT NULL, ItemTemplateID TEXT, PageNumber INT(11) NOT NULL DEFAULT 0,'
                        ' SlotPosition UNSIGNED TINYINT(3) NOT NULL DEFAULT 0, MerchantItem_ID VARCHAR(255) PRIMARY KEY)')
            con.execute("INSERT INTO MerchantItem VALUES ('List','sword',0,1,'m-1')")
            con.execute('CREATE TABLE DOLCharacters (DOLCharacters_ID TEXT PRIMARY KEY, Name TEXT)')
        self.ed = Editor(self.db,self.client,self.root/'state')

    def test_schema_lists_content_tables_only(self):
        self.make_content_table()
        self.assertIn('MerchantItem', self.ed.schema)
        self.assertNotIn('DOLCharacters', self.ed.schema)
        self.assertNotIn('PlayerProgress', self.ed.schema)
        self.assertEqual(self.ed.schema['MerchantItem']['columns']['SlotPosition'], ('int', 0, 255, False))
        with self.assertRaises(ValueError):
            self.ed.rows('DOLCharacters')

    def test_insert_delete_and_restore_round_trip(self):
        self.make_content_table()
        new = {'ItemListID':'List','ItemTemplateID':'axe','PageNumber':0,'SlotPosition':2,'MerchantItem_ID':'m-2'}
        old = {'ItemListID':'List','ItemTemplateID':'sword','PageNumber':0,'SlotPosition':1,'MerchantItem_ID':'m-1'}
        result = self.ed.apply(self.make_patch([
            dict(op='insert',table='MerchantItem',key='m-2',before={},after=new),
            dict(op='delete',table='MerchantItem',key='m-1',before=old,after={})]))
        self.assertEqual([r['MerchantItem_ID'] for r in self.ed.rows('MerchantItem')['rows']], ['m-2'])
        self.ed.rollback(result['id'])
        self.assertEqual([r['MerchantItem_ID'] for r in self.ed.rows('MerchantItem')['rows']], ['m-1'])

    def test_insert_conflicts_and_row_rules(self):
        self.make_content_table()
        existing = {'ItemListID':'List','ItemTemplateID':'x','PageNumber':0,'SlotPosition':1,'MerchantItem_ID':'m-1'}
        with self.assertRaisesRegex(ValueError,'already exists'):
            self.ed.apply(self.make_patch([dict(op='insert',table='MerchantItem',key='m-1',before={},after=existing)]))
        bad = [dict(op='insert',table='MerchantItem',key='m-3',before={},after={**existing,'MerchantItem_ID':'m-4'}),
               dict(op='insert',table='MerchantItem',key='m-3',before={},after={**existing,'MerchantItem_ID':'m-3','SlotPosition':256}),
               dict(op='insert',table='MerchantItem',key='m-3',before={},after={**existing,'MerchantItem_ID':'m-3','ItemListID':None}),
               dict(op='update',table='MerchantItem',key='m-1',before={'MerchantItem_ID':'m-1'},after={'MerchantItem_ID':'m-9'}),
               dict(op='drop',table='MerchantItem',key='m-1',before={},after={})]
        for c in bad:
            with self.subTest(c=c),self.assertRaises(ValueError):
                validate_changes([c], self.ed.schema)

    def test_row_search_by_text_and_column(self):
        self.make_content_table()
        self.assertEqual(self.ed.rows('MerchantItem','swo')['total'],1)
        self.assertEqual(self.ed.rows('MerchantItem','',column='SlotPosition',equals='1')['total'],1)
        self.assertEqual(self.ed.rows('MerchantItem','nothing')['total'],0)
        self.assertEqual(self.ed.new_key('MerchantItem')['key'].count('-'),4)
        self.assertEqual(self.ed.new_key('Zones'),{'key':201})

    def test_server_file_edit_backup_and_guards(self):
        server=self.root/'runtime/server';(server/'config').mkdir(parents=True);(server/'logs').mkdir()
        (server/'bot-world.json').write_bytes(b'{"a": 1}\r\n')
        (server/'config/serverconfig.xml').write_text('<a/>')
        (server/'logs/server.txt').write_text('log');(server/'GameServer.dll').write_bytes(b'MZ')
        (self.root/'runtime/account.txt').write_text('secret')
        self.assertEqual([f['path'] for f in self.ed.file_list()],['server/bot-world.json','server/config/serverconfig.xml'])
        for bad in ('account.txt','server/logs/server.txt','server/GameServer.dll','../outside.txt'):
            with self.subTest(path=bad),self.assertRaises(ValueError):
                self.ed.read_file(bad)
        f=self.ed.read_file('server/bot-world.json')
        self.assertEqual(f['text'],'{"a": 1}\n')
        with self.assertRaisesRegex(ValueError,'Invalid JSON'):
            self.ed.save_file('server/bot-world.json','{oops',f['sha'])
        with self.assertRaisesRegex(ValueError,'Invalid XML'):
            self.ed.save_file('server/config/serverconfig.xml','<a>',self.ed.read_file('server/config/serverconfig.xml')['sha'])
        self.ed.save_file('server/bot-world.json','{"a": 2}\n',f['sha'])
        self.assertEqual((server/'bot-world.json').read_bytes(),b'{"a": 2}\r\n')
        with self.assertRaisesRegex(ValueError,'changed on disk'):
            self.ed.save_file('server/bot-world.json','{}',f['sha'])
        backups=self.ed.read_file('server/bot-world.json')['backups']
        self.assertEqual(len(backups),1)
        self.assertEqual(self.ed.read_file_backup(backups[0],'server/bot-world.json')['text'],'{"a": 1}\n')
        with self.assertRaises(ValueError):
            self.ed.read_file_backup(backups[0],'../../outside.txt')

    def make_item_tables(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute('CREATE TABLE ItemTemplate (Id_nb VARCHAR(255) PRIMARY KEY, Name TEXT, Level INT(11) NOT NULL DEFAULT 0, Realm INT(11) NOT NULL DEFAULT 0,'
                        ' Object_Type INT(11) NOT NULL DEFAULT 0, Item_Type INT(11) NOT NULL DEFAULT 0, Model INT(11) NOT NULL DEFAULT 0, Price BIGINT(20) NOT NULL DEFAULT 0,'
                        ' DPS_AF INT(11) NOT NULL DEFAULT 0, SPD_ABS INT(11) NOT NULL DEFAULT 0, Quality INT(11) NOT NULL DEFAULT 0, PackSize INT(11) NOT NULL DEFAULT 1)')
            con.executemany('INSERT INTO ItemTemplate (Id_nb,Name,Object_Type,Item_Type,Model,Price) VALUES (?,?,?,?,?,?)',
                            [('sword','Sword',3,10,5,100),('cloak','Cloak',32,26,6,50),('tunic','Tunic',35,25,7,90),('rug','Rug',51,0,8,10),('token','Token',0,0,9,1)])
        self.make_content_table()

    def test_item_kinds_and_merchant_lists(self):
        self.make_item_tables()
        kinds = {k: [r['Id_nb'] for r in self.ed.items(kind=k)['rows']] for k in self.ed.ITEM_KINDS}
        self.assertEqual(kinds, {'weapon':['sword'],'armor':['tunic'],'cloak':['cloak'],'shield':[],'jewelry':[],'housing':['rug'],'other':['token']})
        self.assertEqual(self.ed.items(model='7')['rows'][0]['Id_nb'],'tunic')
        with self.assertRaises(ValueError):
            self.ed.items(kind='DROP TABLE')
        self.assertEqual(self.ed.merchant_lists()[0]['id'],'List')
        self.assertEqual(self.ed.merchant_list('List')['slots'][0]['ItemName'],'Sword')

    def test_item_sorting_level_range_checks_and_sources(self):
        self.make_item_tables()
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE ItemTemplate SET Level=CASE Id_nb WHEN 'sword' THEN 50 WHEN 'tunic' THEN 20 WHEN 'cloak' THEN 5 ELSE 1 END")
            con.execute("UPDATE ItemTemplate SET Item_Type=0 WHERE Id_nb='tunic'")
            con.execute('CREATE TABLE LootTemplate (TemplateName TEXT, ItemTemplateID TEXT, Chance INT, Count INT, LootTemplate_ID TEXT PRIMARY KEY)')
            con.execute("INSERT INTO LootTemplate VALUES ('wolf_loot','cloak',10,1,'l1')")
            con.execute('CREATE TABLE MobXLootTemplate (MobName TEXT, LootTemplateName TEXT, DropCount INT, MobXLootTemplate_ID TEXT PRIMARY KEY)')
            con.execute("INSERT INTO MobXLootTemplate VALUES ('grey wolf','wolf_loot',1,'x1')")
        ids = lambda **k: [r['Id_nb'] for r in self.ed.items(**k)['rows']]
        self.assertEqual(ids(sort='level_desc')[:2], ['sword', 'tunic'])
        self.assertEqual(ids(sort='level', min_level='5', max_level='20'), ['cloak', 'tunic'])
        self.assertEqual(ids(slot='26'), ['cloak'])
        self.assertEqual(ids(issue='unequippable'), ['tunic'])
        self.assertEqual(ids(issue='nowhere'), ['rug', 'token', 'tunic'])   # cloak drops, sword is sold on 'List'
        sources = self.ed.item_sources('cloak')
        self.assertEqual(sources['loot'][0]['mobs'], ['grey wolf'])
        for bad in ({'sort': 'Name; DROP TABLE x'}, {'issue': 'x'}):
            with self.assertRaises(ValueError):
                self.ed.items(**bad)

    def test_currency_table_is_created_on_first_save(self):
        self.make_item_tables()
        self.assertIn('offline_currency_lists', self.ed.schema)
        self.assertEqual(self.ed.rows('offline_currency_lists')['total'], 0)
        row = {'ItemListID':'List','CurrencyItem':'token','Description':None,'LastTimeRowUpdated':'2026-01-01 00:00:00','offline_currency_lists_ID':'c-1'}
        result = self.ed.apply(self.make_patch([dict(op='insert',table='offline_currency_lists',key='List',before={},after=row)]))
        self.assertEqual(self.ed.merchant_list('List')['currency']['CurrencyItem'],'token')
        self.assertEqual(self.ed.merchant_lists()[0]['currency'],'token')
        self.ed.rollback(result['id'])
        self.assertIsNone(self.ed.merchant_list('List')['currency'])

    def test_custom_look_install_and_uninstall(self):
        try:
            python = self.ed.render_python()
        except ValueError:
            self.skipTest('No Python with Pillow for the custom-look worker')
        import subprocess, sys as _sys
        # Synthetic client catalogs: a model 5 with one body skin in skin001.mpk.
        monsters = b'Information,,NIF,Skins\r\nID,name,#,Body,Head,Arms,Gloves,Lbody,Legs,Boots,Cloak,Helm,Scale\r\n5,Test Man,7,11,0,0,0,0,0,0,0,0,100\r\n9,Other,7,11,0,0,0,0,0,0,0,0,100\r\n'
        monnifs = b'Information\r\nID,Textual,Name,Set,R,W,B,S,A,Exp\r\n7,Test,testman,1,0,0,0,0,0,0\r\n1000, MAX MONNIFS\r\n'
        skins = b'Information\r\nID,Textual,Name,MULTI,Num,Only\r\n11,Test body,testbody.dds,0,1,0\r\n'
        script = ('import sys,io;sys.path.insert(0,sys.argv[2]);import archive;from PIL import Image;b=io.BytesIO();'
                  'Image.new("RGB",(8,8),(200,0,0)).save(b,format="DDS",pixel_format="DXT1");'
                  'open(sys.argv[1],"wb").write(archive.write(b"skin001.mpk",[archive.Entry("testbody.dds",b.getvalue())]))')
        (self.client/'figures/skins').mkdir(parents=True)
        subprocess.run([python,'-c',script,str(self.client/'figures/skins/skin001.mpk'),str(REPO/'tools/asset-tool')],check=True)
        _sys.path.insert(0,str(REPO/'tools/asset-tool'))
        import archive
        (self.client/'gamedata.mpk').write_bytes(archive.write(b'gamedata.mpk',[archive.Entry('monsters.csv',monsters),
            archive.Entry('monnifs.csv',monnifs),archive.Entry('skins.csv',skins)]))
        original = (self.client/'gamedata.mpk').read_bytes()
        png = 'data:image/png;base64,' + subprocess.run([python,'-c','import io,base64;from PIL import Image;b=io.BytesIO();'
            'Image.new("RGB",(4,4),(0,150,0)).save(b,format="PNG");print(base64.b64encode(b.getvalue()).decode())'],
            check=True,capture_output=True,text=True).stdout.strip()
        self.assertEqual([m['id'] for m in self.ed.models()],[5,9])
        self.assertIn('png',self.ed.assets('template','--model','5')['3'])
        with self.assertRaises(ValueError):
            self.ed.install_look({'model':5,'name':'Bad','images':{'3':'data:text/plain;base64,aGk='}})
        result = self.ed.install_look({'model':5,'name':'CJ Look','scale':110,'images':{'3':png}})
        mon = archive.read((self.client/'gamedata.mpk').read_bytes())[1]
        text = {e.name:e.data.decode('latin1') for e in mon}
        self.assertIn(f'\r\n5,Test Man,', text['monsters.csv'])
        self.assertIn(f'{result["model"]},CJ Look,7,12,', text['monsters.csv'])
        self.assertTrue(text['skins.csv'].endswith('12,CJ Look Body,cust_cj_look_body.dds,0,99,0\r\n'))
        self.assertIn('cust_cj_look_body.dds',[e.name for e in archive.read((self.client/'figures/skins/skin099.mpk').read_bytes())[1]])
        look = self.ed.looks()[0]
        self.assertEqual(look['model'],result['model'])
        self.ed.uninstall_look(look['id'])
        self.assertEqual((self.client/'gamedata.mpk').read_bytes(),original)
        self.assertFalse((self.client/'figures/skins/skin099.mpk').exists())
        self.assertEqual(self.ed.looks(),[])

    def test_custom_look_uninstall_refuses_changed_client(self):
        try:
            self.ed.render_python()
        except ValueError:
            self.skipTest('No Python with Pillow for the custom-look worker')
        folder = self.ed.state/'look-backups/x';folder.mkdir(parents=True)
        (self.client/'gamedata.mpk').write_bytes(b'changed later')
        (folder/'manifest.json').write_text(json.dumps({'name':'x','model':1,'base':1,'created':'','parts':[],'client':str(self.client),
            'files':{'gamedata.mpk':'0'*64},'after':{'gamedata.mpk':'1'*64},'new_files':[]}))
        with self.assertRaisesRegex(ValueError,'changed after'):
            self.ed.uninstall_look('x')
        with self.assertRaises(ValueError):
            self.ed.uninstall_look('../x')

    def test_preview_model_ids_are_bounded(self):
        for models in ('all',[True],[-1],[65536],[1]*129):
            with self.subTest(models=models),self.assertRaises(ValueError):
                self.ed.visual_start(200,models)

    def test_visual_status_returns_only_registered_scene(self):
        folder=self.root/'scene';folder.mkdir()
        scene={'version':2,'zone':200,'models':{},'fixtures':[],'figures':{},'ground':None,'warnings':[]}
        (folder/'scene.json').write_text(json.dumps(scene))
        self.ed.visual_jobs['capability']={'folder':folder,'process':None,'zone':200,'key':'test'}
        result=self.ed.visual_status('capability')
        self.assertEqual(result['status'],'ready')
        self.assertEqual(result['base'],'/assets/capability/')
        self.assertEqual(result['scene'],scene)
        with self.assertRaises(ValueError):
            self.ed.visual_status('../other')

    def test_visual_asset_route_restricts_files_and_paths(self):
        folder=self.root/'scene';folder.mkdir();(folder/'sample.gltf').write_text('{"asset":{"version":"2.0"}}')
        (folder/'request.json').write_text('{"private":"not a preview asset"}')
        self.ed.visual_jobs['capability']={'folder':folder,'process':None,'zone':200,'key':'test'}
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.editor=self.ed
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}/assets/'
        try:
            with urllib.request.urlopen(url+'capability/sample.gltf') as response:
                self.assertEqual(response.headers['Content-Type'],'model/gltf+json')
            for path in ('unknown/sample.gltf','capability/request.json','capability/../outside.gltf'):
                with self.subTest(path=path),self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(url+path)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_cli_plan_apply_undo(self):
        from . import cli
        edits=self.root/'edits.json'
        edits.write_text(json.dumps([{'table':'Mob','key':'Mob-1','set':{'X':'9300'}},
                                     {'table':'Mob','copy':'Mob-1','key':'Mob-2','set':{'Name':'Copy'}},
                                     {'table':'Door','delete':'Door-1'}]))
        base=['--db',str(self.db),'--client',str(self.client),'--state',str(self.root/'state')]
        out=self.root/'fix.patch.json'
        cli.main(base+['plan',str(edits),'--out',str(out)])
        self.assertEqual(self.value(),9000)            # plan writes nothing
        cli.main(base+['apply',str(out)])
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("SELECT X FROM Mob WHERE Mob_ID='Mob-1'").fetchone()[0],9300)
            self.assertEqual(con.execute("SELECT Name, X FROM Mob WHERE Mob_ID='Mob-2'").fetchone(),('Copy',9000))
            self.assertEqual(con.execute('SELECT count(*) FROM Door').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT Value FROM PlayerProgress').fetchone()[0],10)
        with self.assertRaises(SystemExit):           # the same patch again conflicts
            cli.main(base+['apply',str(out)])
        backup=next(b.name for b in (self.root/'state/backups').iterdir() if (b/'applied.txt').is_file())
        cli.main(base+['undo',backup])
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM Mob').fetchone()[0],1)
            self.assertEqual(con.execute('SELECT count(*) FROM Door').fetchone()[0],1)
        self.assertEqual(self.value(),9000)

    def test_cli_sql_is_read_only(self):
        from . import cli
        with self.assertRaises(SystemExit):
            cli.main(['--db',str(self.db),'--client',str(self.client),'sql','DELETE FROM Mob'])
        self.assertEqual(self.value(),9000)


if __name__=='__main__':
    unittest.main()
