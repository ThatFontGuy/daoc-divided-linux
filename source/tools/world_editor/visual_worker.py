"""Read-only DAoC asset conversion for the editor's textured view.

Runs in a separate Python with Pillow/NumPy. All generated files stay in --out.
Uses the existing NIF converters; never invokes the game or changes client assets.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[2] / 'new-client/pipeline'
sys.path.insert(0, str(PIPELINE))


def rows(raw):
    return list(csv.reader(io.StringIO(raw.decode('latin1'))))


def safe_name(name):
    return Path(name.replace('\\', '/')).name.rsplit('.', 1)[0].lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--client', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--zone', type=int, required=True)
    ap.add_argument('--request', type=Path, required=True)
    args = ap.parse_args()
    os.environ['DAOC_CLIENT'] = str(args.client.resolve())
    import numpy as np
    from PIL import Image
    from daoc_mpk import read_mpk, MpakArchive
    import nif_static as ns
    import nif_character as nc
    from netimmerse import read_nif, spec
    import build_zone as bz
    import texture_index as ti

    out, client, zid = args.out.resolve(), args.client.resolve(), args.zone
    out.mkdir(parents=True, exist_ok=True)
    request = json.loads(args.request.read_text())
    ti.CACHE = out / 'texture-index.json'
    index = None
    warnings, inputs, models, fixtures, figures = [], {}, {}, [], {}
    archives = {}

    def skinned_parts(path):
        nif = read_nif(path.read_bytes())
        sp = spec()
        return [b.get('name') for b in nif.blocks if b.type=='NiNode' and any(
            c is not None and sp.is_a(c.type,'NiTriBasedGeom') and c.get('skin_instance') is not None
            and not (int(c.get('flags',0)) & 1) for c in (b.get('children') or []))]

    def part_looks(mr, skins, parts):
        columns={'body':(3,(27,53)),'head':(4,(37,54)),'arms':(5,(36,55)),
                 'gloves':(6,(50,56)),'lbody':(7,(52,57)),'legs':(8,(41,59)),'boots':(9,(51,58))}
        result={}
        for part in parts:
            col, multi=columns.get(str(part).lower(),columns['body'])
            row=skins.get(mr[col].strip())
            if row is None or mr[col].strip()=='0':
                col,multi=columns['body'];row=skins.get(mr[col].strip())
            if row is None:
                raise ValueError('No catalog skin for '+str(part))
            look={'base':safe_name(row[2]),'dark':None,'detail':None}
            for c in multi:
                m=skins.get(mr[c].strip()) if c<len(mr) else None
                kind={'2':'dark','7':'detail'}.get(m[3].strip()) if m else None
                if kind and look[kind] is None:
                    look[kind]=safe_name(m[2])
            look['tex']='__'.join([look['base']]+[look[k] for k in ('dark','detail') if look[k]])
            result[part]=look
        return result

    def bake_multi(image, other, gain):
        a=np.asarray(image.convert('RGBA'),dtype=np.float32)
        b=np.asarray(other.convert('RGBA').resize(image.size),dtype=np.float32)
        a[...,:3]=np.clip(a[...,:3]*b[...,:3]/255*gain,0,255)
        return Image.fromarray(a.astype('uint8'))

    def remember(path):
        s = path.stat()
        inputs[path.relative_to(client).as_posix()] = [s.st_size, s.st_mtime_ns]
        return path

    def archive(path):
        remember(path)
        if path not in archives:
            archives[path] = MpakArchive(path)
        return archives[path]

    def status(message):
        (out / 'progress.json').write_text(json.dumps({'message': message}), encoding='utf-8')
        print(message, flush=True)

    def texture(name, directory, source=None, figure=False):
        nonlocal index
        destination = directory / (name + '.png')
        directory.mkdir(parents=True, exist_ok=True)
        base = name[:-4] if name.endswith(('__d2', '__x2')) else name
        image = None
        if source and source.suffix.lower() == '.npk':
            arc = archive(source)
            hit = next((n for n in arc.names() if safe_name(n) == base and n.endswith(('.dds','.tga','.bmp'))), None)
            if hit:
                image = Image.open(io.BytesIO(arc.read(hit))).convert('RGBA')
        if image is None:
            if index is None:
                status('Indexing client textures (first use only)…')
                index = ti.TextureIndex()
            index.figures_first = figure
            index.first = ([source.parent.relative_to(client).as_posix().lower()] if source else []) + ['newtowns/']
            hit = index.locate(base)
            if hit:
                remember(client / hit[0])
                image = index.image(base)
            if image is None:
                image = ns.EMBEDDED.get(base)
        if image is None:
            # A neutral checker identifies unavailable texture data without broken URL requests.
            image = Image.new('RGBA', (16,16), (173,161,140,255))
            warnings.append('Missing texture: ' + base)
        if name.endswith('__d2'):
            image = Image.fromarray(np.clip(np.asarray(image.convert('RGB'), dtype=np.float32)*2,0,255).astype('uint8'))
        image.thumbnail((1024,1024))
        image.save(destination)

    def clean_gltf(path):
        doc = json.loads(path.read_text())
        # The converter includes collision-only nodes for Godot; they must not be drawn as scenery.
        hidden = {i for i,n in enumerate(doc.get('nodes',[])) if n.get('name','').startswith(('collision','climb','doorcol'))}
        for scene in doc.get('scenes',[]):
            scene['nodes'] = [i for i in scene.get('nodes',[]) if i not in hidden]
        for node in doc.get('nodes',[]):
            if 'children' in node:
                node['children'] = [i for i in node['children'] if i not in hidden]
        path.write_text(json.dumps(doc), encoding='utf-8')

    # Match BuildNav/client search order: New Towns overrides regional/base world art.
    prefixes = ['newtowns', 'frontiers', ''] if (client / f'frontiers/zones/zone{zid:03}').is_dir() else ['newtowns', '']
    zdir = next((client / prefix / f'zones/zone{zid:03}' for prefix in prefixes
                 if (client / prefix / f'zones/zone{zid:03}/dat{zid:03}.mpk').is_file()), None)
    if zdir is None:
        raise ValueError('Client zone archive is missing')
    dat = read_mpk(remember(zdir / f'dat{zid:03}.mpk'))
    for name in ('nifs.csv','fixtures.csv'):
        for prefix in prefixes:
            found = False
            for stem in ('csv','dat'):
                path = client / prefix / f'zones/zone{zid:03}/{stem}{zid:03}.mpk'
                if path.is_file() and name in archive(path).entries:
                    dat[name] = archive(path).read(name)
                    found = True
                    break
            if found:
                break
    sector = bz.sector_ini(dat['sector.dat'])

    def resolve_nif(name, dungeon=False):
        stem = safe_name(name)
        folders = ['dnifs','zones/dnifs','zones/nifs','nifs'] if dungeon else ['zones/nifs','nifs']
        for prefix in prefixes:
            for folder in folders:
                directory = client / prefix / folder
                if not directory.is_dir():
                    continue
                for extension in ('.nif','.npk'):
                    path = directory / (stem + extension)
                    if path.is_file():
                        return path
        return None

    def scenery(path):
        if path is None:
            return None
        key = hashlib.sha256(path.relative_to(client).as_posix().lower().encode()).hexdigest()[:18]
        if key in models:
            return key
        directory = out / 'scenery' / key
        directory.mkdir(parents=True, exist_ok=True)
        try:
            remember(path)
            raw = path.read_bytes() if path.suffix.lower()=='.nif' else next(archive(path).read(n) for n in archive(path).names() if n.endswith('.nif'))
            info = ns.convert(raw, str(directory / 'model.gltf'), 'textures')
            clean_gltf(directory / 'model.gltf')
            for tex in info['textures']:
                texture(tex, directory / 'textures', path)
            models[key] = {'file': f'scenery/{key}/model.gltf', 'name': path.stem,
                           'source': path.relative_to(client).as_posix(), 'triangles': info['triangles']}
            return key
        except Exception as exc:
            warnings.append(f'{path.name}: {type(exc).__name__}: {exc}')
            models[key] = {'missing': True, 'name': path.stem}
            return None

    ground = None
    status('Preparing textured ground…')
    for stem, prefix in (('lod','lod'),('tex','tex')):
        path = zdir / f'{stem}{zid:03}.mpk'
        if not path.is_file():
            continue
        tiles = read_mpk(remember(path))
        tile = next((n for n in tiles if n.startswith(prefix+'00-00.')), None)
        if not tile:
            continue
        ext = tile.rsplit('.',1)[1]
        mosaic = Image.new('RGB',(2048,2048),(99,111,72))
        for x in range(8):
            for y in range(8):
                raw = tiles.get(f'{prefix}{x:02}-{y:02}.{ext}')
                if raw:
                    mosaic.paste(Image.open(io.BytesIO(raw)).convert('RGB').resize((256,256)),(x*256,y*256))
        mosaic.save(out / 'ground.jpg',quality=90)
        ground = 'ground.jpg'
        break

    if 'fixtures.csv' in dat:
        table = {int(r[0]):r for r in rows(dat['nifs.csv']) if r and r[0].strip().isdigit()}
        placed = [r for r in rows(dat['fixtures.csv']) if len(r)>11 and r[0].strip().isdigit() and r[1].strip().isdigit()]
        h = bz.heights(dat,sector)
        used = sorted({int(r[1]) for r in placed})
        mapped = {}
        for i,nid in enumerate(used):
            status(f'Converting scenery {i+1}/{len(used)}…')
            row = table.get(nid)
            mapped[nid] = scenery(resolve_nif(row[2])) if row else None
        for r in placed:
            key=mapped.get(int(r[1]))
            if not key or models[key].get('missing'):
                continue
            x,y,z,a,s = (float(r[k] or 0) for k in (3,4,5,6,7))
            if r[11].strip()=='1':
                z=bz.height_at(h,x,y)
            fixtures.append({'model':key,'name':r[2].strip(),'pos':[x*.025,z*.025,y*.025],
                             'yaw':-a,'scale':s/100 if s else 1,'id':r[14] if len(r)>14 else r[0]})
    elif 'city.csv' in dat:
        origin=bz.CITY_ORIGIN.get(zid,(23808,23808,8000))
        yaw=sector.getint('rotate','rotate',fallback=2)*90
        chunks=[r[1].strip() for r in rows(dat['city.csv']) if len(r)>1 and r[0].strip().isdigit()]
        for i,name in enumerate(chunks):
            status(f'Converting city buildings {i+1}/{len(chunks)}…')
            path=zdir/'nifs'/(safe_name(name)+'.npk')
            key=scenery(path) if path.is_file() else None
            if key:
                fixtures.append({'model':key,'name':name,'pos':[origin[0]*.025,origin[2]*.025,origin[1]*.025],'yaw':yaw,'scale':1})
    elif 'dungeon.place' in dat:
        chunks=[v.strip() for v in dat['dungeon.chunk'].decode('latin1').splitlines() if v.strip()]
        conv=np.array([[1,0,0],[0,0,1],[0,-1,0]],float);turn=np.diag([-1,1,-1])
        for line in dat['dungeon.place'].decode('latin1').splitlines():
            if not line.strip():
                continue
            v=[float(x) for x in line.split(',')]
            key=scenery(resolve_nif(chunks[int(v[0])],True))
            if key:
                r=turn@conv@bz._axis_angle(-v[4],v[5:8])@conv.T
                p=turn@(conv@np.array(v[1:4])*.025)+np.array([23808,16000,23808])*.025
                fixtures.append({'model':key,'name':chunks[int(v[0])],'pos':p.tolist(),'basis':r.T.reshape(-1).tolist(),'scale':1})

    # Read model/skin catalogs from this selected client; no substitute classic assets.
    catalog = read_mpk(remember(client/'gamedata.mpk')) if (client/'gamedata.mpk').is_file() else {}
    tables={name:{r[0].strip():r for r in rows(catalog.get(name,b'')) if r and r[0].strip().isdigit()}
            for name in ('monsters.csv','monnifs.csv','skins.csv')}
    figures_by_name={p.name.lower():p for p in (client/'figures').glob('*') if p.is_file()}
    used=sorted({int(e['values'].get('Model',0))&0x7fff for e in request['entities'] if e['table']=='Mob'})
    for i,model in enumerate(used):
        status(f'Converting NPC / mob appearances {i+1}/{len(used)}…')
        mr=tables['monsters.csv'].get(str(model))
        nr=tables['monnifs.csv'].get(mr[2].strip()) if mr else None
        path=figures_by_name.get(nr[2].strip().lower()+'.nif') if nr else None
        if not path:
            figures[str(model)]={'missing':True}
            continue
        directory=out/'figures'/str(model);directory.mkdir(parents=True,exist_ok=True)
        try:
            remember(path)
            parts=skinned_parts(path)
            looks=part_looks(mr,tables['skins.csv'],parts)
            clips={}
            try:
                idle=nc.clip_files(int(nr[3]),('Idle',)).get('Idle')
                if idle:
                    clips['idle']=idle
                    remember(client/'anims'/idle[0])
            except Exception:
                pass
            if parts:
                nc.build(path.name,{p:lk['tex'] for p,lk in looks.items()},clips,str(directory/'model.gltf'),'textures',file_bind=True)
                for lk in looks.values():
                    texture(lk['base'],directory/'textures',figure=True)
                    # Keep part-specific skin names produced by the existing look resolver.
                    if lk['tex']!=lk['base']:
                        image=Image.open(directory/'textures'/(lk['base']+'.png')).convert('RGBA')
                        for slot,gain in (('dark',1),('detail',2)):
                            if lk[slot]:
                                texture(lk[slot],directory/'textures',figure=True)
                                image=bake_multi(image,Image.open(directory/'textures'/(lk[slot]+'.png')),gain)
                        image.save(directory/'textures'/(lk['tex']+'.png'))
            else:
                info=ns.convert(path.read_bytes(),str(directory/'model.gltf'),'textures')
                for tex in info['textures']:
                    texture(tex,directory/'textures',figure=True)
            clean_gltf(directory/'model.gltf')
            figures[str(model)]={'file':f'figures/{model}/model.gltf','name':mr[1],
                                 'scale':float(mr[12] or 100)/100,'animated':bool(clips)}
        except Exception as exc:
            figures[str(model)]={'missing':True,'name':mr[1] if mr else str(model)}
            warnings.append(f'Model {model}: {type(exc).__name__}: {exc}')
    scene={'version':2,'zone':zid,'ground':ground,'models':models,'fixtures':fixtures,'figures':figures,
           'warnings':warnings,'inputs':inputs,
           'summary':f'{len(fixtures)} scenery objects · {sum(not v.get("missing") for v in figures.values())}/{len(figures)} NPC/mob appearances'}
    (out/'scene.json').write_text(json.dumps(scene),encoding='utf-8')
    status('Textured scene ready')


if __name__=='__main__':
    main()
