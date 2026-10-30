"""Custom NPC looks for the classic client: private copies of stock models with new skins (and optionally a NIF).

Runs in a Python with Pillow (the editor starts it). Stock catalog rows, NIFs and skins are never edited:
a look adds new monsters.csv / skins.csv (and monnifs.csv) rows under unused IDs, new DDS entries in the
private skin archive figures/skins/skin099.mpk and, optionally, a new figures/<name>.nif. Every install
backs up gamedata.mpk and skin099.mpk with hashes; uninstall restores them only if nothing else changed them.

  catalog   --client APP                          -> JSON list of models and their skin parts
  template  --client APP --model N                -> JSON {part column: PNG data URL} of the stock skins
  install   --client APP --request FILE --backups DIR
  uninstall --client APP --backup DIR
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import math
import re
import shutil
import struct
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'tools/asset-tool'))
import archive  # noqa: E402  validated MPAK codec

PARTS = {3: 'Body', 4: 'Head', 5: 'Arms', 6: 'Gloves', 7: 'Lower body', 8: 'Legs', 9: 'Boots', 10: 'Cloak', 11: 'Helm'}
# Extra texture layers (dark/detail) that player-race models blend over a part's base skin.
LAYERS = {3: (27, 53), 4: (37, 54), 5: (36, 55), 6: (50, 56), 7: (52, 57), 8: (41, 59), 9: (51, 58)}
PRIVATE_ARCHIVE = 99
MAX_MODEL = 2494          # stock table ends at 2493; IDs from 2500 are unproven in this client
NIF_IDS = range(989, 1000)  # monnifs.csv stops reading at its 1000 terminator


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def table(data):
    return list(csv.reader(io.StringIO(data.decode('latin1'))))


def by_id(data):
    return {r[0].strip(): r for r in table(data) if r and r[0].strip().isdigit()}


def stem(name):
    return Path(name.replace('\\', '/')).name.rsplit('.', 1)[0].lower()


def row_line(row):
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\r\n').writerow(row)
    return buf.getvalue()[:-2]


def insert_rows(data, rows, terminator=None):
    """Insert whole lines in ID order; every original line stays byte-identical, no blank lines appear."""
    lines = data.decode('latin1').split('\r\n')
    for row in sorted(rows, key=lambda r: int(r[0])):
        new_id, index, last = int(row[0]), None, len(lines) - 1
        for i, line in enumerate(lines):
            head = line.split(',', 1)[0].strip()
            if head.isdigit():
                if int(head) > new_id or (terminator and int(head) >= terminator):
                    index = i
                    break
                last = i
        if index is None:
            index = last + 1
        require(not terminator or new_id < terminator, f'ID {new_id} must be below {terminator}')
        lines.insert(index, row_line(row))
    result = '\r\n'.join(lines).encode('latin1')
    added = {row_line(r) for r in rows}
    require([l for l in result.decode('latin1').split('\r\n') if l not in added] == data.decode('latin1').split('\r\n'),
            'catalog insert changed an existing line')
    ids = [int(r[0]) for r in table(result) if r and r[0].strip().isdigit()]
    require(all(a <= b for a, b in zip(ids, ids[1:])), 'catalog IDs are not ascending')
    data_lines = [i for i, l in enumerate(result.decode('latin1').split('\r\n')) if l.split(',', 1)[0].strip().isdigit()]
    require(all(result.decode('latin1').split('\r\n')[i].strip() for i in range(data_lines[0], data_lines[-1])),
            'blank line inside catalog')
    return result


def encode_dds(image, reference=None):
    """DXT1 with a full mip chain: the skin format confirmed to work for private models in this client."""
    working = image.convert('RGB')
    header, blocks = None, []
    while True:
        out = io.BytesIO()
        working.save(out, format='DDS', pixel_format='DXT1')
        data = out.getvalue()
        require(data[84:88] == b'DXT1', 'Pillow did not produce DXT1')
        header = bytearray(data[:128]) if header is None else header
        blocks.append(data[128:])
        if working.size == (1, 1):
            break
        working = working.resize((max(1, working.width // 2), max(1, working.height // 2)), Image.Resampling.LANCZOS)
    struct.pack_into('<I', header, 8, (struct.unpack_from('<I', header, 8)[0] | 0xA0000) & ~0x8)
    struct.pack_into('<I', header, 20, len(blocks[0]))
    struct.pack_into('<I', header, 88, 0)
    struct.pack_into('<I', header, 28, len(blocks))
    struct.pack_into('<I', header, 108, 0x1000 | 0x8 | 0x400000)
    encoded = bytes(header) + b''.join(blocks)
    if reference and reference[84:88] == b'DXT1':
        # Keep the legacy header properties of a texture already working in this client.
        final = bytearray(reference[:128])
        for offset in (12, 16, 20, 28):
            final[offset:offset + 4] = encoded[offset:offset + 4]
        encoded = bytes(final) + encoded[128:]
    h, w = struct.unpack_from('<II', encoded, 12)
    levels = struct.unpack_from('<I', encoded, 28)[0]
    require(levels == int(math.log2(max(w, h))) + 1, 'Incomplete mip chain')
    Image.open(io.BytesIO(encoded)).load()
    return encoded


class Client:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.gamedata_path = self.root / 'gamedata.mpk'
        self.gname, self.gentries = archive.read(self.gamedata_path.read_bytes())
        self.files = {e.name.lower(): e for e in self.gentries}
        self.monsters = by_id(self.files['monsters.csv'].data)
        self.monnifs = by_id(self.files['monnifs.csv'].data)
        self.skins = by_id(self.files['skins.csv'].data)
        self._archives = {}

    def files_rows(self, name):
        return [(r[0].strip(), r) for r in table(self.files[name].data) if r and r[0].strip().isdigit()]

    def skin_archive(self, number):
        path = self.root / f'figures/skins/skin{int(number):03d}.mpk'
        if path not in self._archives:
            self._archives[path] = archive.read(path.read_bytes())[1] if path.is_file() else []
        return self._archives[path]

    def skin_bytes(self, skin_id):
        row = self.skins.get(str(skin_id))
        require(row is not None, f'Skin {skin_id} is not in skins.csv')
        base = stem(row[2])
        numbers = [row[4].strip()] if row[4].strip().isdigit() else []
        numbers += [p.stem[4:] for p in sorted((self.root / 'figures/skins').glob('skin*.mpk')) if p.stem[4:].isdigit()]
        for number in numbers:
            for entry in self.skin_archive(number):
                if stem(entry.name) == base:
                    return entry.data
        for path in (self.root / 'figures/skins').glob(base + '.*'):
            return path.read_bytes()
        raise ValueError(f'Texture {row[2]} for skin {skin_id} was not found')

    def parts(self, model):
        row = self.monsters[str(model)]
        found = []
        for col, label in PARTS.items():
            skin = row[col].strip() if col < len(row) else '0'
            if skin and skin != '0' and skin in self.skins:
                found.append({'col': col, 'part': label, 'skin': int(skin), 'file': self.skins[skin][2]})
        return found


def catalog(args):
    c = Client(args.client)
    result = []
    for mid, row in c.monsters.items():
        nif = c.monnifs.get(row[2].strip())
        result.append({'id': int(mid), 'name': row[1], 'nif': nif[2] if nif else None, 'parts': c.parts(mid),
                       'scale': row[12], 'private': int(mid) >= 2494 or (nif is not None and int(nif[0]) >= 989)})
    print(json.dumps(sorted(result, key=lambda m: m['id'])))


def template(args):
    c = Client(args.client)
    result = {}
    for part in c.parts(args.model):
        try:
            image = Image.open(io.BytesIO(c.skin_bytes(part['skin']))).convert('RGB')
        except Exception as exc:  # unreadable stock texture: report per part
            result[part['col']] = {'error': f'{type(exc).__name__}: {exc}'}
            continue
        out = io.BytesIO()
        image.save(out, format='PNG')
        result[part['col']] = {'png': 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode(),
                               'size': list(image.size), 'file': part['file']}
    print(json.dumps(result))


def free_model_ids(c, used):
    return [i for i in range(1, MAX_MODEL) if str(i) not in c.monsters and i not in used]


def install(args):
    request = json.loads(Path(args.request).read_text(encoding='utf-8'))
    c = Client(args.client)
    stock = c.monsters.get(str(request['model']))
    require(stock is not None, 'Choose a base model from the client catalog')
    name = re.sub(r'[^A-Za-z0-9 _-]', '', request['name']).strip()[:40]
    require(name, 'Give the look a name (letters and numbers)')
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')[:20]
    images = {int(k): Path(v) for k, v in request.get('images', {}).items()}
    nif_file = Path(request['nif']) if request.get('nif') else None
    require(images or nif_file, 'Add at least one painted texture or a NIF file')
    parts = {p['col']: p for p in c.parts(request['model'])}
    require(set(images) <= set(parts), 'A texture was given for a part this model does not have')

    skin_path = c.root / 'figures/skins' / f'skin{PRIVATE_ARCHIVE:03d}.mpk'
    if skin_path.is_file():
        sname, sentries = archive.read(skin_path.read_bytes())
    else:
        sname, sentries = b'skin099.mpk', []
    existing = {e.name.lower() for e in sentries}
    reference = next((e.data for e in sentries if e.data[84:88] == b'DXT1'), None)

    model_id = request.get('modelId') or free_model_ids(c, set(request.get('usedModels', [])))[-1]
    require(str(model_id) not in c.monsters and 0 < int(model_id) < MAX_MODEL, f'Model ID {model_id} is not free')
    next_skin = max(int(k) for k in c.skins) + 1
    new_mon = list(stock)
    new_mon[0], new_mon[1] = str(model_id), name
    if request.get('scale') and len(new_mon) > 12:
        new_mon[12] = str(int(request['scale']))
    new_skins, new_entries, new_nif, created = [], [], [], []
    for col, path in sorted(images.items()):
        image = Image.open(path).convert('RGB')
        try:
            size = Image.open(io.BytesIO(c.skin_bytes(parts[col]['skin']))).size
        except ValueError:
            size = image.size
        if image.size != size:
            image = image.resize(size, Image.Resampling.LANCZOS)  # same size as the stock skin is safest
        dds = f'cust_{slug}_{PARTS[col].replace(" ", "").lower()}.dds'
        require(dds not in existing, f'{dds} already exists in skin099.mpk; pick another name')
        row = list(c.skins[str(parts[col]['skin'])])
        row[0], row[1], row[2], row[4], row[5] = str(next_skin), f'{name} {PARTS[col]}', dds, str(PRIVATE_ARCHIVE), '0'
        new_skins.append(row)
        new_entries.append(archive.Entry(dds, encode_dds(image, reference),
                                         sentries[0].timestamp if sentries else int(time.time()), sentries[0].flags if sentries else 4))
        new_mon[col] = str(next_skin)
        for layer in LAYERS.get(col, ()):
            if layer < len(new_mon) and new_mon[layer].strip() not in ('', '0'):
                new_mon[layer] = '0'   # stock dark/detail overlays would paint over the new skin
        next_skin += 1
    if nif_file:
        raw = nif_file.read_bytes()
        require(raw.startswith((b'NetImmerse File Format', b'Gamebryo File Format')), 'The model file is not a NIF')
        nif_id = next((i for i in NIF_IDS if str(i) not in c.monnifs), None)
        require(nif_id is not None, 'No free private NIF IDs (989-999) are left')
        target = c.root / 'figures' / f'cust_{slug}.nif'
        require(not target.exists(), f'{target.name} already exists')
        nrow = list(c.monnifs[stock[2].strip()])
        nrow[0], nrow[1], nrow[2], nrow[9] = str(nif_id), name, target.stem, '0'
        new_nif.append(nrow)
        new_mon[2] = str(nif_id)

    replaced = {'monsters.csv': insert_rows(c.files['monsters.csv'].data, [new_mon])}
    if new_skins:
        replaced['skins.csv'] = insert_rows(c.files['skins.csv'].data, new_skins)
    if new_nif:
        replaced['monnifs.csv'] = insert_rows(c.files['monnifs.csv'].data, new_nif, 1000)
    gblob = archive.write(c.gname, [archive.Entry(e.name, replaced.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in c.gentries])
    archive.verify_memory_image(gblob)
    sblob = None
    if new_entries:
        sblob = archive.write(sname, sorted(sentries + new_entries, key=lambda e: e.name.lower()))
        archive.verify_memory_image(sblob)
        old = {e.name.lower(): e for e in sentries}
        for e in archive.read(sblob)[1]:
            require(e.name.lower() not in old or old[e.name.lower()] == e, f'existing skin entry changed: {e.name}')

    backup = Path(args.backups) / (time.strftime('%Y%m%d-%H%M%S-') + slug)
    backup.mkdir(parents=True)
    manifest = {'name': name, 'model': int(model_id), 'base': int(request['model']), 'created': time.strftime('%Y-%m-%d %H:%M'),
                'client': str(c.root), 'files': {}, 'after': {}, 'new_files': [], 'parts': [PARTS[c] for c in images]}
    for path in [c.gamedata_path] + ([skin_path] if sblob else []):
        rel = path.relative_to(c.root).as_posix()
        if path.is_file():
            shutil.copy2(path, backup / path.name)
            manifest['files'][rel] = sha(path.read_bytes())
        else:
            manifest['new_files'].append(rel)
    c.gamedata_path.write_bytes(gblob)
    manifest['after']['gamedata.mpk'] = sha(gblob)
    if sblob:
        skin_path.write_bytes(sblob)
        manifest['after'][skin_path.relative_to(c.root).as_posix()] = sha(sblob)
    if nif_file:
        target.write_bytes(raw)
        manifest['new_files'].append(target.relative_to(c.root).as_posix())
        manifest['after'][target.relative_to(c.root).as_posix()] = sha(raw)
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'model': int(model_id), 'backup': str(backup), 'name': name}))


def uninstall(args):
    folder = Path(args.backup)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    root = Path(args.client).resolve()
    for rel, digest in manifest['after'].items():
        path = root / rel
        require(path.is_file() and sha(path.read_bytes()) == digest,
                f'{rel} changed after this look was installed (another look or tool). Uninstall newer looks first.')
    for rel in manifest['files']:
        saved = folder / rel if (folder / rel).is_file() else folder / Path(rel).name
        shutil.copy2(saved, root / rel)
    for rel in manifest['new_files']:
        (root / rel).unlink(missing_ok=True)
    for rel, digest in manifest['files'].items():
        require(sha((root / rel).read_bytes()) == digest, f'restore verification failed: {rel}')
    (folder / 'uninstalled.txt').write_text(time.strftime('%Y-%m-%d %H:%M'), encoding='utf-8')
    print(json.dumps({'message': f'Removed custom look {manifest["name"]} (model {manifest["model"]}).'}))


# objects.csv (the item appearance table): 2 NIF (items.csv ID, 1 = worn body armour), 3 icon,
# 4-12 classic skins (pskins.csv IDs), 36 housing NIF (items.csv ID). See docs/CLIENT-MODDING-GUIDE.txt 13.2.
ARMOR_COLS = {4: 'Body', 6: 'Arms', 7: 'Gloves', 8: 'Lower body', 9: 'Legs', 10: 'Boots', 11: 'Cloak', 12: 'Helm'}
# Catacombs columns: what player characters (and newer items such as the epic class cloaks) actually wear.
# Epic cloaks keep the plain stock cloak in classic col 11 and their own art only in col 72 (guide 13.3).
CATA_COLS = {66: 'Body', 67: 'Body (female)', 68: 'Arms', 69: 'Gloves', 70: 'Legs', 71: 'Boots', 72: 'Cloak'}
EFFECT_COLS = {55: 'Effect', 56: 'Albion effect', 57: 'Midgard effect', 58: 'Hibernia effect'}
ICON_SERIES = {100: 'ITM_1200', 200: 'WPN_900', 500: 'ITM_1300', 2200: 'ITM_1400'}


def icon_cell(number):
    """Item icon number -> (sheet, cell 0-99); later expansions' series are not mapped."""
    for base, sheet in ICON_SERIES.items():
        if base <= number < base + 100:
            return sheet, number - base
    return None, None


def items_catalog(args):
    c = Client(args.client)
    nifs = by_id(c.files['items.csv'].data)
    out = []
    for oid, row in c.files_rows('objects.csv'):
        col = lambda i: row[i].strip() if len(row) > i else ''
        nif, house = col(2), col(36)
        skins = {ARMOR_COLS[i]: int(col(i)) for i in ARMOR_COLS if col(i).isdigit() and col(i) != '0'}
        skins.update({CATA_COLS[i]: int(col(i)) for i in CATA_COLS if col(i).isdigit() and col(i) != '0'})
        skins.pop('Body (female)', None)
        if house not in ('', '0') and house in nifs:
            kind = 'housing'
        elif nif not in ('', '0', '1') and nif in nifs:
            kind = 'model'
        elif skins:
            kind = 'cloak' if set(skins) == {'Cloak'} else 'helm' if set(skins) == {'Helm'} else 'armor'
        else:
            kind = 'other'
        icon = int(col(3)) if col(3).isdigit() else 0
        sheet, cell = icon_cell(icon)
        effects = {label: int(col(i)) for i, label in EFFECT_COLS.items() if col(i).isdigit() and col(i) != '0'}
        out.append({'id': int(oid), 'name': row[1].strip(), 'kind': kind, 'icon': icon, 'sheet': sheet, 'cell': cell, 'effects': effects,
                    'nif': nifs[nif][2].strip() if kind == 'model' else nifs[house][2].strip() if kind == 'housing' else None,
                    'skins': skins})
    print(json.dumps(out))


def convert_effect(c, effect, out, index, ns, warnings):
    """An item's Effect number -> spweapons.csv -> spnifs.csv -> effects/<nif>, converted with its particle systems
    (glTF extras.nif_particles) and their textures. Drawn in the item's own space, like the client."""
    spw = by_id(c.files['spweapons.csv'].data) if 'spweapons.csv' in c.files else {}
    spn = by_id(c.files['spnifs.csv'].data) if 'spnifs.csv' in c.files else {}
    row = spw.get(str(effect))
    if row is None:
        warnings.append(f"Effect {effect} is not in this client's weapon effect table (nothing is drawn in game)")
        return {'id': effect, 'name': None, 'gltf': None}
    nif = spn.get(row[2].strip())
    name = stem(nif[2]) if nif else ''
    info = {'id': effect, 'name': row[1].strip(), 'nif': name, 'gltf': None}
    source = next((p for p in (c.root / 'effects').glob('*') if stem(p.name) == name and p.suffix.lower() == '.nif'), None)
    if not name or name == 'empty' or source is None:
        warnings.append(f'Effect {effect} ({row[1].strip()}): effect file {name or "?"} not found')
        return info
    folder = out / 'effect'
    (folder / 'textures').mkdir(parents=True, exist_ok=True)
    try:
        converted = ns.convert(source.read_bytes(), str(folder / 'model.gltf'), 'textures', node_anims=True)
    except Exception as exc:
        warnings.append(f'Effect {name}: {type(exc).__name__}: {exc}')
        return info
    for tex in converted['textures']:
        image = index.image(tex) if index.locate(tex) else ns.EMBEDDED.get(tex)
        if image is None:
            warnings.append('Missing effect texture ' + tex)
            continue
        image.save(folder / 'textures' / (tex + '.png'))
    info.update(gltf='effect/model.gltf', particles=converted.get('particles', 0), triangles=converted.get('triangles', 0))
    return info


def effects_list(args):
    """Named weapon/item effects (spweapons.csv) for the item editor's Effect choice."""
    c = Client(args.client)
    rows = by_id(c.files['spweapons.csv'].data) if 'spweapons.csv' in c.files else {}
    print(json.dumps({k: re.sub(r'\s+', ' ', r[1]).strip() for k, r in sorted(rows.items(), key=lambda kv: int(kv[0]))}))


# Player figures for the "worn" preview (fig3 indices, build_races.RACES): one per realm, male.
FIGURES = {'nor_m': 15, 'bri_m': 1, 'cel_m': 33, 'nor_f': 16, 'bri_f': 2, 'cel_f': 34}
CATA_SLOT = {66: 'body', 67: 'body', 68: 'arms', 69: 'gloves', 70: 'legs', 71: 'boots'}


# objects.csv Nif1 .. Nif12: one Catacombs helm per race and gender of the helm's realm, in this order
# (new-client build_helms.py COLUMN_RACES); the column after Nif12 is the Catacombs helm texture.
HELM_RACES = {
    'alb': ['bri_m', 'bri_f', 'sar_m', 'sar_f', 'hig_m', 'hig_f', 'ava_m', 'ava_f', 'inc_m', 'inc_f', 'hal_m', 'hal_f'],
    'mid': ['nor_m', 'nor_f', 'dwa_m', 'dwa_f', 'kob_m', 'kob_f', 'tro_m', 'tro_f', 'val_m', 'val_f', 'fro_m', 'fro_f'],
    'hib': ['cel_m', 'cel_f', 'elf_m', 'elf_f', 'lur_m', 'lur_f', 'fir_m', 'fir_f', 'syl_m', 'syl_f', 'sha_m', 'sha_f'],
}
HELM_REALM_OF = {r.split('_')[0]: realm for realm, races in HELM_RACES.items() for r in races}
HELM_REALM_OF.update({'brit': 'alb', 'alb': 'alb', 'mid': 'mid', 'hib': 'hib'})


def helm_meshes(c, row):
    """{figure prefix: items.csv row} for a helm's per-race Catacombs meshes, and the Catacombs texture column."""
    header = table(c.files['objects.csv'].data)[1]
    if 'Nif1' not in header:
        return {}, None
    cols = [header.index(f'Nif{i}') for i in range(1, 13)]
    items = by_id(c.files['items.csv'].data)
    entries = [items.get(row[ci].strip()) if len(row) > ci else None for ci in cols]
    votes = {}
    for e in entries:
        for tok in re.split(r'[_\d]+', e[2].strip().lower()) if e else []:
            realm = HELM_REALM_OF.get(tok) or HELM_REALM_OF.get(tok[:3]) if tok else None
            if realm:
                votes[realm] = votes.get(realm, 0) + 1
    races = HELM_RACES.get(max(votes, key=votes.get), []) if votes else []
    return {races[i]: e for i, e in enumerate(entries) if e and i < len(races)}, cols[-1] + 1


def pskin_image(c, prow):
    """A pskins row's texture from the exact items/pskins archive it names (others hold same-named classic copies)."""
    if prow is None or not prow[4].strip().isdigit():
        return None
    path = c.root / f'items/pskins/pskin{int(prow[4]):03d}.mpk'
    if not path.is_file():
        return None
    base = stem(prow[2])
    for entry in archive.read(path.read_bytes())[1]:
        if stem(entry.name) == base:
            return Image.open(io.BytesIO(entry.data)).convert('RGBA')
    return None


def boots_twin(index, tex):
    """Catacombs boots meshes want the 512 x 256 sheet; some sets name a square twin of the other spelling
    (cthboots01_05 vs cthboot01_05). Of the two, the 2:1 sheet wins (new-client build_armor.boots_twin)."""
    m = re.match(r'([a-z]+?)(boots?)(\d\d_.*)', tex)
    if not m:
        return tex
    twin = m.group(1) + ('boot' if m.group(2) == 'boots' else 'boots') + m.group(3)
    if twin not in index.entries:
        return tex
    a, b = index.image(tex), index.image(twin)
    wide = lambda im: im is not None and im.size[0] == 2 * im.size[1]
    return twin if wide(b) and not wide(a) else tex


def dress_figure(c, row, out, figure, warnings, extension=0, color=0):
    """The item worn by a player character, as the client dresses Catacombs figures (new-client build_armor.py and
    Fig3Figure.item_armor / _apply_armor, which follow game.dll):
      textures  with Cata Status (col 65) on, objects.csv's Catacombs columns 66-71 (BaseTex -> mskins), as the
                client draws them (guide 13.3, confirmed in game); otherwise the classic skin's "Cata <name>" set
                (nif_character.cata_outfit). The figure archives (figures/Mskins) win over same-named classic copies
                laid out for the old figures; boots use the 2:1 sheet of the two spellings
      meshes    body / gloves / boots use the item's Extension (0 = mesh 1), arms and legs mesh 1; a robe (objects
                col 15 "Lbody #" = 3) wears body mesh 7, hides arms and legs and puts gloves / boots on mesh 3
      cloak     col 72's own texture, else the Catacombs twin of the classic cloak skin (Cat_<name>), texture set 1
      dye       the item's Color (tints.csv Catacombs colour) multiplies its pieces (the viewer applies it)
    Idle animation included."""
    import io as _io
    sys.argv = sys.argv[:1]
    import build_races as br
    import nif_character as nc
    import texture_index as ti
    t = br.Tables()
    col = lambda i: row[i].strip() if len(row) > i else ''
    # Helms: a per-race mesh hung on the head (Nif1..Nif12), or a head-swap helm (col 95 "Nif" + col 96 "Head Swap")
    # that replaces the head with one of the race's full-helm parts (fig3map slot 9).
    helms, helm_tex_col = helm_meshes(c, row)
    full_helm = int(col(95)) if col(95).isdigit() and int(col(95)) > 0 and col(96) == '1' else 0
    if helms and figure not in helms:
        # The helm only exists for its own realm's races: show it on that realm's figure of the same gender.
        same = [k for k in helms if k in FIGURES and k.endswith(figure[-2:])] or [k for k in helms if k in FIGURES]
        if same:
            warnings.append(f'This helm has no model for the chosen race; shown on {same[0]}.')
            figure = same[0]
    fig = FIGURES.get(figure, 15)
    female = figure.endswith('_f')
    mn, players, pick = br.figure_rows(t, fig)
    pskins = by_id(c.files['pskins.csv'].data)
    mskins = by_id(c.files['mskins.csv'].data) if 'mskins.csv' in c.files else {}

    index = ti.TextureIndex()
    index.first = ['figures/mskins']
    clothes = {}
    for slot, catskin in br.CATSKIN.items():
        info = t.skin(pick(catskin))
        if info:
            m = re.search(r'(\d\d)', info['tex'])
            clothes[slot] = {'variant': int(m.group(1)) if m else 1, **info}
    names = {v: k for k, v in br.SLOTS.items()}
    names.update({v: {'boot': 'boots', 'glove': 'gloves'}.get(k, k) for k, v in nc.CATA_SLOTS.items()})
    armour = {}
    if col(65) == '1':
        # Cata Status on: the client draws the Catacombs columns 66-71 and ignores the classic ones (guide 13.3,
        # confirmed in game); BaseTex -> the exact mskins copy, else the pskins texture from the figure archives.
        for i, slot in CATA_SLOT.items():
            sid = col(i)
            if (i == 66 and female) or (i == 67 and not female) or sid not in pskins:
                continue
            ps = pskins[sid]
            base = ps[6].strip() if len(ps) > 6 else ''
            tex = stem(mskins[base][2] if base in mskins else ps[2]).strip()
            if index.locate(tex) is not None:
                armour[slot] = boots_twin(index, tex) if slot == 'boots' else tex
    if not armour:
        # No Catacombs columns: the classic skin's "Cata <name>" set, by name (nif_character.cata_outfit).
        for slot_no, (_variant, tex) in nc.cata_outfit(t.rows, [int(row[0])], 'f' if female else 'm').items():
            slot = names.get(slot_no)
            if slot:
                armour[slot] = boots_twin(index, tex.lower()) if slot == 'boots' else tex.lower()
    robe = col(15) == '3' and 'body' in armour
    worn = []
    for slot, tex in armour.items():
        if robe and slot in ('arms', 'legs'):
            continue
        variant = 7 if robe and slot == 'body' else 3 if robe and slot in ('gloves', 'boots') else \
            max(1, int(extension or 0)) if slot in ('body', 'gloves', 'boots') else 1
        clothes[slot] = {'variant': variant, 'tex': tex, 'chan': '', 'archive': None, 'item': True}
        worn.append(slot)
    if robe:
        for slot in ('arms', 'legs'):
            clothes.pop(slot, None)
    # The cloak: col 72's own texture (epic and live cloaks), else the classic cloak skin's Catacombs twin.
    cloak = None
    if col(72) in pskins and not pskins[col(72)][1].strip().lower().startswith('cata'):
        cloak = stem(pskins[col(72)][2])
    elif col(11) in pskins:
        base = stem(pskins[col(11)][2])
        cloak = next((x for x in ('cat_' + base, 'cat_' + re.sub(r'\d+$', '', base), 'cat_cloak') if x in index.entries), None)
    helm = helms.get(figure)
    if not worn and not cloak and not helm and not full_helm:
        return None
    faces = [t.skin(x) for x in t.faces[fig][2:] if x.strip()]
    folder = out / 'figure'
    (folder / 'textures').mkdir(parents=True, exist_ok=True)
    head = (*t.labelled_head(t.fmap[(fig, 0)][0]), faces[0]['tex'], (1.0, 1.0, 1.0), 'head')
    textures = {faces[0]['tex']: faces[0]}
    if full_helm and not helm:
        swaps = t.fmap.get((fig, 9), [])
        prow = pskins.get(col(12))
        image = pskin_image(c, prow)
        if 0 < full_helm <= len(swaps) and t.part(swaps[full_helm - 1]) and image is not None:
            name = stem(prow[2]) + '__helm'
            image.save(folder / 'textures' / f'{name}.png')
            head = (*t.part(swaps[full_helm - 1]), name, (1.0, 1.0, 1.0), 'head')
            textures.pop(faces[0]['tex'])
            worn.append('helm')
    parts = [head]
    for slot, n in br.SLOTS.items():
        if slot not in clothes:
            continue
        meshes = t.fmap.get((fig, n), [])
        v = clothes[slot]['variant']
        if not 0 < v <= len(meshes) or not t.part(meshes[v - 1]):
            v = 1                                        # this race lacks that mesh: the default shape
        pid = meshes[v - 1] if meshes else None
        if pid and t.part(pid):
            parts.append((*t.part(pid), clothes[slot]['tex'], (1.0, 1.0, 1.0), slot))
            textures[clothes[slot]['tex']] = clothes[slot]
    if cloak:
        cloaks = t.fmap.get((fig, 7), [])
        if cloaks and t.part(cloaks[0]):
            arc, nif = t.part(cloaks[0])
            parts.append((arc, nif + '@1', cloak, (1.0, 1.0, 1.0), 'cloak'))
            textures[cloak] = {'tex': cloak, 'chan': '', 'archive': None, 'item': True}
    helm_info = None
    if helm is not None:
        helm_info = convert_helm(c, row, helm, helm_tex_col, pskins, folder, warnings)
        if helm_info:
            worn.append('helm')
    for name, info in textures.items():
        raw = None if info.get('item') else t.texture_bytes(info)
        image = Image.open(_io.BytesIO(raw)) if raw else (index.image(name) if index.locate(name) else None)
        if image is None:
            warnings.append(f'Figure texture {name} not found')
            image = Image.new('RGBA', (16, 16), (173, 161, 140, 255))
        image.convert('RGBA').save(folder / 'textures' / f'{name.lower()}.png')
    clips = {'idle': v for k, v in nc.clip_files(int(mn[3]), ('Idle',)).items()}
    skeleton = (f'sfig{int(mn[15] or 1):03d}.mpk', f'{mn[2].strip().lower()}_skeleton.nif')
    nc.build_cata(skeleton, parts, clips, str(folder / 'figure.gltf'), 'textures')
    dye = None
    if int(color or 0) > 0 and 'tints.csv' in c.files:
        for r in table(c.files['tints.csv'].data):
            if r and r[0].strip() == str(int(color)):
                vals = [v.strip() for v in r[2:11]]
                rgb = vals[6:9] if len(vals) >= 9 and all(v.isdigit() for v in vals[6:9]) else vals[0:3]
                if all(v.isdigit() for v in rgb):
                    dye = {'name': r[1].strip(), 'rgb': [round(int(v) / 255.0, 4) for v in rgb]}
    return {'gltf': 'figure/figure.gltf', 'race': mn[1].strip().replace('Cata ', ''), 'worn': worn + (['cloak'] if cloak else []),
            'helm': helm_info, 'robe': robe, 'extension': int(extension or 0), 'dye': dye,
            'textures': {slot: clothes[slot]['tex'] for slot in worn if slot in clothes}}


def convert_helm(c, row, helm, tex_col, pskins, folder, warnings):
    """One race's helm mesh (items/<nif>.nif, a static mesh in the head bone's space) as figure/helm/model.gltf,
    textured as game.dll dresses a Catacombs helm: the Catacombs helm texture column when set, else the item's Helm
    skin (col 12) when the mesh uses that texture, else the mesh's own textures (build_helms.py)."""
    import nif_static as ns
    import texture_index as ti
    name = helm[2].strip()
    path = next((p for p in (c.root / 'items').glob('*') if stem(p.name) == name.lower() and p.suffix.lower() == '.nif'), None)
    if path is None:
        warnings.append(f'Helm mesh {name}.nif is not in this client')
        return None
    d = folder / 'helm'
    (d / 'textures').mkdir(parents=True, exist_ok=True)
    info = ns.convert(path.read_bytes(), str(d / 'model.gltf'), 'textures')
    col = lambda i: row[i].strip() if len(row) > i else ''
    cata = pskins.get(col(tex_col)) if tex_col is not None and col(tex_col) not in ('', '0') else None
    helm_skin = pskins.get(col(12))
    doc = json.loads((d / 'model.gltf').read_text(encoding='utf-8'))
    index = ti.TextureIndex()
    if cata is not None:                                  # one texture on every surface
        image = pskin_image(c, cata) or index.image(stem(cata[2]))
        override = {stem(im['uri']): stem(cata[2]) for im in doc.get('images', [])}
    elif helm_skin is not None and stem(helm_skin[2]) in {t.lower() for t in info['textures']}:
        image = pskin_image(c, helm_skin)
        override = {stem(helm_skin[2]): stem(helm_skin[2])} if image is not None else {}
    else:
        image, override = None, {}
    for tex in info['textures']:
        target = override.get(tex.lower())
        picture = image if target else (index.image(tex) if index.locate(tex) else ns.EMBEDDED.get(tex))
        if picture is None:
            warnings.append(f'Helm texture {tex} not found')
            continue
        picture.save(d / 'textures' / f'{(target or tex).lower()}.png')
    for im in doc.get('images', []):
        base = stem(im['uri'])
        im['uri'] = f'textures/{override.get(base, base).lower()}.png'   # files above are saved lower case
    (d / 'model.gltf').write_text(json.dumps(doc), encoding='utf-8')
    scale = int(helm[25]) if len(helm) > 25 and helm[25].strip().isdigit() else 100
    return {'gltf': 'figure/helm/model.gltf', 'scale': scale, 'nif': name}


def texture_signature(client):
    """Identity of the client's texture files (names, sizes, times), so an import or patch gets a fresh index."""
    import os
    h = hashlib.sha256()
    for top in ('gamedata.mpk', 'items', 'figures', 'effects', 'phousing'):
        path = client / top
        entries = [path] if path.is_file() else [Path(d) / f for d, _, fs in os.walk(path) for f in fs] if path.is_dir() else []
        for f in sorted(entries):
            st = f.stat()
            h.update(f'{f.relative_to(client)}|{st.st_size}|{st.st_mtime_ns};'.encode())
    return h.hexdigest()[:16]


def item_preview(args):
    """Convert one item appearance for the browser: a glTF for meshes, PNG textures for worn armour."""
    import os
    os.environ['DAOC_CLIENT'] = str(Path(args.client).resolve())
    sys.path.insert(0, str(REPO / 'source/new-client/pipeline'))
    import nif_static as ns
    import texture_index as ti
    from daoc_mpk import MpakArchive
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ti.CACHE = Path(args.cache) / f'texture-index-{texture_signature(Path(args.client))}.json'
    c = Client(args.client)
    row = dict(c.files_rows('objects.csv')).get(str(args.model))
    require(row is not None, f'Item appearance {args.model} is not in objects.csv')
    col = lambda i: row[i].strip() if len(row) > i else ''
    nifs = by_id(c.files['items.csv'].data)
    index = ti.TextureIndex()
    result = {'model': args.model, 'name': row[1].strip(), 'gltf': None, 'textures': [], 'warnings': []}

    def save_texture(name, label):
        stem_name = stem(name)
        hit = index.locate(stem_name)
        image = index.image(stem_name) if hit else None
        if image is None:
            result['warnings'].append(f'Missing texture {name}')
            return None
        file = f'{len(result["textures"])}_{re.sub(r"[^a-z0-9_]+", "_", stem_name)}.png'
        image.convert('RGBA').save(out / file)
        result['textures'].append({'label': label, 'name': name, 'file': file})
        return file

    for nif_col, folders in ((2, ('items',)), (36, ('phousing/nifs', 'items'))):
        nid = col(nif_col)
        if nid in ('', '0', '1') or nid not in nifs:
            continue
        name = stem(nifs[nid][2])
        source = None
        for folder in folders:
            for path in (c.root / folder).glob('*'):
                if stem(path.name) == name and path.suffix.lower() in ('.nif', '.npk'):
                    source = path
                    break
            if source:
                break
        if not source:
            result['warnings'].append(f'Mesh {nifs[nid][2]} not found')
            continue
        if source.suffix.lower() == '.npk':
            arc = MpakArchive(source)
            raw = next(arc.read(n) for n in arc.names() if n.lower().endswith('.nif'))
        else:
            raw = source.read_bytes()
        try:
            info = ns.convert(raw, str(out / 'model.gltf'), 'textures')
        except Exception as exc:
            result['warnings'].append(f'{source.name}: {type(exc).__name__}: {exc}')
            continue
        (out / 'textures').mkdir(exist_ok=True)
        for tex in info['textures']:
            hit = index.locate(tex)
            image = index.image(tex) if hit else ns.EMBEDDED.get(tex)
            if image is None:
                image = Image.new('RGBA', (16, 16), (173, 161, 140, 255))
                result['warnings'].append('Missing texture ' + tex)
            image.save(out / 'textures' / (tex + '.png'))
        result['gltf'] = 'model.gltf'
        result['source'] = source.relative_to(c.root).as_posix()
        break
    pskins = by_id(c.files['pskins.csv'].data) if 'pskins.csv' in c.files else {}
    mskins = by_id(c.files['mskins.csv'].data) if 'mskins.csv' in c.files else {}
    seen = set()

    def skin_texture(sid):
        # pskins col 6 "Material BaseTex" names the real Catacombs texture in mskins (guide 13.4).
        row = pskins.get(sid)
        if row is None:
            return None
        base = row[6].strip() if len(row) > 6 else ''
        return mskins[base][2].strip() if base not in ('', '0') and base in mskins else row[2].strip()

    def add(name, label):
        if name and name.lower() not in seen:
            seen.add(name.lower())
            save_texture(name, label)

    cata = {label: col(i) for i, label in CATA_COLS.items() if col(i) not in ('', '0')}
    for label, sid in cata.items():
        add(skin_texture(sid), f'{label} · worn by players')
    words = {'Body': 'body', 'Arms': 'arms', 'Gloves': 'glove', 'Legs': 'legs', 'Boots': 'boot', 'Cloak': 'cloak'}
    for i, label in ARMOR_COLS.items():
        sid = col(i)
        if sid in ('', '0') or sid not in pskins:
            continue
        if not cata:
            # Rows without Catacombs columns: the set named "Cata <name>" is what players wear.
            for prow in pskins.values():
                name = prow[2].strip()
                if (prow[1].strip().lower() == 'cata ' + pskins[sid][1].strip().lower() and label in words
                        and words[label] in name.lower()):
                    add(name, f'{label} · worn by players')
        # Helms have no Catacombs column: the classic texture is what everyone sees.
        add(pskins[sid][2].strip(), label if label == 'Helm' else f'{label} · classic / NPC')
    if True:  # armour, cloaks and helms on a player figure (dress_figure returns None for anything else)
        try:
            result['figure'] = dress_figure(c, row, out, args.figure, result['warnings'], args.extension, args.color)
        except Exception as exc:  # the flat textures above still show the item
            result['warnings'].append(f'Worn preview unavailable: {type(exc).__name__}: {exc}')
    effect = args.effect if args.effect else next((int(col(i)) for i in EFFECT_COLS if col(i).isdigit() and col(i) != '0'), 0)
    if effect:
        result['effect'] = convert_effect(c, effect, out, index, ns, result['warnings'])
    print(json.dumps(result))


PSKIN_COLS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 66, 67, 68, 69, 70, 71, 72]


def import_items(args):
    """Copy item appearances (objects.csv rows) from another client, e.g. the live client after a patch.

    Brings each row's pskins.csv rows and their pskinNNN.mpk textures. A pskins ID already used by different art in
    this client gets the next free ID, and the object row is rewired to it; object IDs are kept so server items can
    use the same Model in every install (refused if taken by a different row). Only whole new lines are inserted
    (ID order, no blank lines) and every existing archive entry is kept. Backups and manifest as for custom looks.
    """
    src, dst = Client(args.source), Client(args.client)
    ids = [i.strip() for i in args.objects.split(',') if i.strip()]
    require(ids and all(i.isdigit() for i in ids), 'Give object IDs, e.g. --objects 4924,4925')
    src_obj, dst_obj = dict(src.files_rows('objects.csv')), dict(dst.files_rows('objects.csv'))
    src_ps, dst_ps = by_id(src.files['pskins.csv'].data), by_id(dst.files['pskins.csv'].data)
    new_obj, new_ps, remap, archives, skipped = [], [], {}, {}, []
    next_ps = max(int(k) for k in dst_ps) + 1
    for oid in ids:
        row = src_obj.get(oid)
        require(row is not None, f'Object {oid} is not in the source client')
        if oid in dst_obj:
            require(dst_obj[oid][1] != row[1], f'Object {oid} ({row[1].strip()}) is already imported in this client')
            require(dst_obj[oid] == row, f'Object {oid} already exists in this client with a different appearance')
            skipped.append(oid)
            continue
        row = list(row)
        require(len(row) <= 2 or row[2].strip() in ('', '0', '1'), f'Object {oid} uses a mesh (NIF); only skin-based items are imported so far')
        for col in PSKIN_COLS:
            sid = row[col].strip() if len(row) > col else ''
            if sid in ('', '0'):
                continue
            ps = src_ps.get(sid)
            require(ps is not None, f'Object {oid} column {col}: skin {sid} missing in the source client')
            require(len(ps) <= 6 or ps[6].strip() in ('', '0'), f'Skin {sid} uses an mskins material; not supported yet')
            if sid not in remap:
                if dst_ps.get(sid) == ps:
                    remap[sid] = sid                       # identical stock row already present
                else:
                    target = sid if sid not in dst_ps and all(r[0] != sid for r in new_ps) else str(next_ps)
                    if target == str(next_ps):
                        next_ps += 1
                    copy = list(ps)
                    copy[0] = target
                    if len(copy) > 5:
                        copy[5] = '0'                      # Expansion Only off on private rows (guide 3)
                    new_ps.append(copy)
                    remap[sid] = target
                    archives.setdefault(ps[4].strip(), set()).add(ps[2].strip().lower())
            row[col] = remap[sid]
        new_obj.append(row)
    require(new_obj, 'Nothing to import: every object is already in this client')
    replaced = {'objects.csv': insert_rows(dst.files['objects.csv'].data, new_obj)}
    if new_ps:
        replaced['pskins.csv'] = insert_rows(dst.files['pskins.csv'].data, new_ps)
    gblob = archive.write(dst.gname, [archive.Entry(e.name, replaced.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in dst.gentries])
    archive.verify_memory_image(gblob)
    # Texture archives: add the needed entries; an existing archive keeps all its entries byte for byte.
    blobs = {}
    for number, names in archives.items():
        rel = f'items/pskins/pskin{int(number):03d}.mpk'
        sname, sentries = archive.read((src.root / rel).read_bytes())
        wanted = [e for e in sentries if e.name.lower() in names]
        require(len(wanted) == len(names), f'{rel}: textures missing in the source client')
        path = dst.root / rel
        if path.is_file():
            dname, dentries = archive.read(path.read_bytes())
            have = {e.name.lower(): e for e in dentries}
            for e in wanted:
                require(e.name.lower() not in have or have[e.name.lower()].data == e.data, f'{rel}: {e.name} differs in this client')
            merged = dentries + [e for e in wanted if e.name.lower() not in have]
            if len(merged) == len(dentries):
                continue
            blobs[rel] = archive.write(dname, sorted(merged, key=lambda e: e.name.lower()))
        else:
            blobs[rel] = archive.write(sname, sorted(wanted, key=lambda e: e.name.lower()))
        archive.verify_memory_image(blobs[rel])
    names = ', '.join(r[1].strip() for r in new_obj)
    backup = Path(args.backups) / (time.strftime('%Y%m%d-%H%M%S-') + 'import')
    backup.mkdir(parents=True)
    manifest = {'name': f'Imported: {names}', 'model': int(new_obj[0][0]), 'base': 0, 'created': time.strftime('%Y-%m-%d %H:%M'),
                'client': str(dst.root), 'source': str(src.root), 'objects': [int(r[0]) for r in new_obj], 'pskins': remap,
                'files': {}, 'after': {}, 'new_files': [], 'parts': ['imported item']}
    for rel in ['gamedata.mpk', *blobs]:
        path = dst.root / rel
        if path.is_file():
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup / rel)
            manifest['files'][rel] = sha(path.read_bytes())
        else:
            manifest['new_files'].append(rel)
    dst.gamedata_path.write_bytes(gblob)
    manifest['after']['gamedata.mpk'] = sha(gblob)
    for rel, blob in blobs.items():
        (dst.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst.root / rel).write_bytes(blob)
        manifest['after'][rel] = sha(blob)
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'objects': manifest['objects'], 'pskins': remap, 'skipped': skipped, 'backup': str(backup),
                      'files': list(manifest['after'])}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['catalog', 'template', 'install', 'uninstall', 'items', 'item-preview', 'effects', 'import-items'])
    ap.add_argument('--client', required=True)
    ap.add_argument('--model', type=int)
    ap.add_argument('--request')
    ap.add_argument('--backups')
    ap.add_argument('--backup')
    ap.add_argument('--out')
    ap.add_argument('--cache')
    ap.add_argument('--effect', type=int, default=0)
    ap.add_argument('--source')
    ap.add_argument('--figure', default='nor_m', choices=sorted(FIGURES))
    ap.add_argument('--extension', type=int, default=0)
    ap.add_argument('--color', type=int, default=0)
    ap.add_argument('--objects')
    args = ap.parse_args()
    try:
        {'catalog': catalog, 'template': template, 'install': install, 'uninstall': uninstall,
         'items': items_catalog, 'item-preview': item_preview, 'effects': effects_list, 'import-items': import_items}[args.command](args)
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(2)


if __name__ == '__main__':
    main()
