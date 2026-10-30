"""Stage a private 1.130 compatibility sandbox; never starts it or edits installs."""
import importlib.util,json,shutil,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path

repo=Path(__file__).resolve().parents[2]
workspace=repo.parent
out=repo/'artifacts/modern-client-test'
if out.exists():raise SystemExit('Refusing to overwrite an existing test folder.')
source=workspace/'Classic/runtime'
spec=importlib.util.spec_from_file_location('release036',repo/'source/tools/build_release_036.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
server=out/'runtime/server';server.mkdir(parents=True)
for p in (source/'server').iterdir():
 if p.is_dir():
  if p.name.lower() in ['navmesh','logs','backups','dumps']:continue
  shutil.copytree(p,server/p.name,ignore=shutil.ignore_patterns('*.log','*.dmp','*.on','*.off','*before-*','*.bak'))
 elif p.suffix.lower() not in ['.log','.dmp','.on','.off','.bak']:
  shutil.copy2(p,server/p.name)
build=repo/'source/server/Release'
for p in build.iterdir():
 if p.is_file() and (p.suffix.lower() in ['.dll','.exe','.pdb','.json','.config']):shutil.copy2(p,server/p.name)
for p in (build/'lib').glob('*'):
 if p.is_file():
  for target in [server,server/'lib',server/'win-x64']:
   target.mkdir(exist_ok=True);shutil.copy2(p,target/p.name)
db=out/'runtime/data/opendaoc.sqlite3.db';db.parent.mkdir()
with sqlite3.connect((source/'data/opendaoc.sqlite3.db').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(db) as dst:src.backup(dst)
policy=json.loads((repo/'source/tools/OfflineDaoc.ProgressImport/progress-policy.json').read_text())
defaults=json.loads((repo/'source/tools/release-world-defaults.json').read_text(encoding='utf-8'))
release.clean_world(db,policy,defaults)
with sqlite3.connect(db) as c:
 c.execute("UPDATE ServerProperty SET Value='False' WHERE lower(`Key`)='enable_sluaghbinder'")
 c.execute("UPDATE ServerProperty SET Value='False' WHERE lower(`Key`)='start_as_base_class'")
 c.execute("UPDATE ServerProperty SET Value='0' WHERE lower(`Key`) IN ('time_between_account_creation','time_between_account_creation_sameip')")
 c.commit()
 c.execute('VACUUM')
config=server/'config/serverconfig.xml';tree=ET.parse(config);root=tree.getroot().find('Server')
values={'Port':'10330','IP':'127.0.0.1','RegionIP':'127.0.0.1','RegionPort':'10430','UdpIP':'127.0.0.1','UdpPort':'10430','EnableUPnP':'False','DetectRegionIP':'False','DBType':'SQLITE','DBConnectionString':f'Data Source={db};Version=3;Pooling=True;Journal Mode=WAL;Synchronous=Normal;Foreign Keys=False;Default Timeout=60','AutoAccountCreation':'True','ServerName':'Offline DAoC 1.130 TEST','ServerNameShort':'Offline1130Test'}
for k,v in values.items():
 node=root.find(k)
 if node is None:node=ET.SubElement(root,k)
 node.text=v
tree.write(config,encoding='utf-8',xml_declaration=True)
(out/'staging.json').write_text(json.dumps({'client':'existing OpenDAoC 1.130 client (not modified)','tcp':'127.0.0.1:10330','udp':'127.0.0.1:10430','progress':'cleared using release clean_world policy','server_started':False,'navmesh':'junction to Classic runtime/server/navmesh must be created before use'},indent=2))
print('Staged isolated server and sanitized test database:',out)
