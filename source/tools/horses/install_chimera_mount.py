"""A private saddled Chimera mount for the modern 1.130 client (horsemap mount 89).

The stock Chimera (horsemap 67 -> monsters 1180 -> monnifs 472 figures/chimera.nif) was never a real mount:
its NIF has no "saddle" node, so the client seats the rider at a fallback spot high above its back. Every
working mount (horse, wyvern, gryphon, dragonfly, broom) has one. This adds, without touching stock files:
  figures/ChimeraSaddle.nif  byte copy of chimera.nif + one NiNode "saddle" (child of Bip01 Spine1, no
                             controller, so it follows the back's animation)
  monnifs.csv  1039  copy of 472: NIF ChimeraSaddle, Expansion Only 0, ride anim set 71 (the horse rider pose)
  monsters.csv 2441  copy of 1180 pointing at 1039
  horsemap.csv 89    "Chimera Mount" -> 2441
Point the server's Chimera item at mount 89 (ItemTemplate mount_67 SPD_ABS) after installing.

    python install_chimera_mount.py --client <client-modern/app>            preview (writes nothing)
    python install_chimera_mount.py --client <client-modern/app> install    backs up, then installs
    python install_chimera_mount.py rollback <backup folder>
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import shutil
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('daoc_archive', ROOT / 'tools' / 'asset-tool' / 'archive.py')
archive = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(archive)

STOCK_NIF, PRIVATE_NIF = 'chimera.nif', 'ChimeraSaddle.nif'
MONNIF_ID, MONSTER_ID, MOUNT_ID = '1039', '2441', '89'
STOCK_MONNIF, STOCK_MONSTER = '472', '1180'
RIDE_ANIMS = '71'
SADDLE_PARENT = 'Bip01 Spine1'
# Where the rider sits, in model space (forward is -Y, up is +Z): on the back behind the wing roots.
# The back's top surface there is Z 131-147 (measured from the body mesh); adjust after seeing it in game.
SADDLE_AT = (0.0, 8.0, 138.0)
# The rider also takes the saddle's orientation: the broom's working saddle, model-space rotation rows
# (0,0,1),(1,0,0),(0,1,0), seats the Chimera's rider upright and facing its heads (-Y). Seen in game:
# an identity rotation under Bip01 Spine1 inherited the bone frame (rider upside down), and the broom
# rotation turned 180 degrees about Z seated the rider facing backwards.
SADDLE_FACING = (0, 0, 1, 1, 0, 0, 0, 1, 0)


def require(ok, message):
    if not ok:
        raise SystemExit('Refusing: ' + message)


# ------------------------------------------------------------------ NIF 4.2.2.0 ---
def nif_blocks(raw):
    head = raw.index(b'\n') + 1
    version, count = struct.unpack_from('<II', raw, head)
    found = []
    for m in re.finditer(rb'Ni[A-Za-z]{2,40}', raw):
        s = m.start() - 4
        if s < head + 8:
            continue
        n = struct.unpack_from('<I', raw, s)[0]
        if 4 <= n <= len(m.group()):
            found.append((s, m.group()[:n].decode()))
    footer = len(raw) - 8
    require(struct.unpack_from('<I', raw, footer)[0] == 1, 'expected exactly one root')
    blocks = []
    for i, (s, kind) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else footer
        blocks.append(dict(index=i, kind=kind, body=s + 4 + len(kind), end=end))
    return head, count, blocks, footer


def nif_node(raw, b):
    p = b['body']
    (nlen,) = struct.unpack_from('<I', raw, p); p += 4
    name = raw[p:p + nlen].decode('latin1'); p += nlen
    p += 8                                        # extra data, controller
    (flags,) = struct.unpack_from('<H', raw, p); p += 2
    t = struct.unpack_from('<3f', raw, p); p += 12
    r = struct.unpack_from('<9f', raw, p); p += 36
    (s,) = struct.unpack_from('<f', raw, p); p += 4 + 12
    (nprop,) = struct.unpack_from('<I', raw, p); p += 4 + 4 * nprop
    (hbb,) = struct.unpack_from('<B', raw, p); p += 1
    if hbb:
        p += 4 + 12 + 36 + 12
    count_at = p
    (n,) = struct.unpack_from('<I', raw, p); p += 4
    kids = list(struct.unpack_from(f'<{n}i', raw, p)); p += 4 * n
    (ne,) = struct.unpack_from('<I', raw, p); p += 4 + 4 * ne
    require(p == b['end'], f'NiNode {b["index"]} parse ended at {p}, block ends at {b["end"]}')
    return dict(name=name, flags=flags, t=t, r=r, s=s, kids=kids, count_at=count_at)


def _mul(a, b):
    return [sum(a[i * 3 + k] * b[k * 3 + j] for k in range(3)) for i in range(3) for j in range(3)]


def _apply(r, v):
    return [r[i * 3] * v[0] + r[i * 3 + 1] * v[1] + r[i * 3 + 2] * v[2] for i in range(3)]


def world_nodes(raw):
    head, count, blocks, footer = nif_blocks(raw)
    require(len(blocks) == count, f'found {len(blocks)} blocks, header says {count}')
    nodes = {b['index']: nif_node(raw, b) for b in blocks if b['kind'] == 'NiNode'}
    root = struct.unpack_from('<i', raw, footer + 4)[0]
    out = {}

    def walk(i, R, T, S):
        n = nodes[i]
        wt = [a + c for a, c in zip(_apply(R, [S * x for x in n['t']]), T)]
        wr, ws = _mul(R, n['r']), S * n['s']
        out[i] = dict(n, wt=wt, wr=wr, ws=ws)
        for k in n['kids']:
            if k in nodes:
                walk(k, wr, wt, ws)

    walk(root, [1, 0, 0, 0, 1, 0, 0, 0, 1], [0, 0, 0], 1.0)
    return head, blocks, footer, out


def add_saddle(raw):
    head, blocks, footer, nodes = world_nodes(raw)
    require(not any(n['name'] == 'saddle' for n in nodes.values()), 'the model already has a saddle node')
    parents = [i for i, n in nodes.items() if n['name'] == SADDLE_PARENT]
    require(len(parents) == 1, f'expected one {SADDLE_PARENT} node')
    pi = parents[0]
    p = nodes[pi]
    # local = R^T (world - T) / S  (the inverse of world = R (S local) + T for an orthonormal R)
    d = [a - c for a, c in zip(SADDLE_AT, p['wt'])]
    rt = [p['wr'][j * 3 + i] for i in range(3) for j in range(3)]
    local = [x / p['ws'] for x in _apply(rt, d)]
    local_r = _mul(rt, list(SADDLE_FACING))         # world rotation = parent R * local R
    name = b'saddle'
    body = struct.pack('<I', len(name)) + name + struct.pack('<ii', -1, -1) + struct.pack('<H', p['flags'])
    body += struct.pack('<3f', *local) + struct.pack('<9f', *local_r) + struct.pack('<f', 1.0)
    body += struct.pack('<3f', 0, 0, 0) + struct.pack('<I', 0) + struct.pack('<B', 0)   # velocity, no props, no bound
    body += struct.pack('<II', 0, 0)                                                    # no children, no effects
    new_index = len(blocks)
    out = bytearray(raw[:footer]) + struct.pack('<I', 6) + b'NiNode' + body + raw[footer:]
    insert_at = p['count_at'] + 4 + 4 * len(p['kids'])
    out[p['count_at']:p['count_at'] + 4] = struct.pack('<I', len(p['kids']) + 1)
    out[insert_at:insert_at] = struct.pack('<i', new_index)
    struct.pack_into('<I', out, head + 4, len(blocks) + 1)
    out = bytes(out)
    # Re-read: same blocks plus the saddle, at the intended spot, under the intended parent.
    _, check_blocks, _, check = world_nodes(out)
    saddle = [n for n in check.values() if n['name'] == 'saddle']
    require(len(saddle) == 1 and len(check_blocks) == len(blocks) + 1, 'rebuilt NIF does not parse as expected')
    require(all(abs(a - b) < 0.01 for a, b in zip(saddle[0]['wt'], SADDLE_AT)), 'saddle landed in the wrong place')
    require(all(abs(a - b) < 0.001 for a, b in zip(saddle[0]['wr'], SADDLE_FACING)), 'saddle faces the wrong way')
    require(new_index in check[pi]['kids'], 'saddle is not under its parent')
    return out, local


# --------------------------------------------------------------------- catalogs ---
def rows_of(text):
    return [r for r in csv.reader(io.StringIO(text))]


def append_line(data, row):
    text = data.decode('latin1')
    require(text.endswith('\r\n'), 'catalog does not end with CRLF')
    ids = [r[0] for r in rows_of(text) if r]
    require(row[0] not in ids, f'id {row[0]} already exists')
    numeric = [int(i) for i in ids if i.strip().isdigit()]
    require(int(row[0]) > max(numeric), f'id {row[0]} must come after the last id {max(numeric)}')
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\r\n').writerow(row)
    new = (text + buf.getvalue()).encode('latin1')
    lines = new.decode('latin1').split('\r\n')
    require(all(lines[i] for i in range(len(lines) - 1)), 'blank line inside the catalog')
    require(new.startswith(data), 'an existing line changed')
    return new


def stock_row(data, row_id):
    found = [r for r in rows_of(data.decode('latin1')) if r and r[0] == row_id]
    require(len(found) == 1, f'expected one stock row {row_id}')
    return list(found[0])


def build(client):
    gamedata = client / 'gamedata.mpk'
    figures = {p.name.lower(): p for p in (client / 'figures').iterdir()}
    require(STOCK_NIF in figures, 'figures/chimera.nif is missing')
    require(PRIVATE_NIF.lower() not in figures, f'figures/{PRIVATE_NIF} already exists (installed?)')
    stock = figures[STOCK_NIF].read_bytes()
    nif, local = add_saddle(stock)

    name, entries = archive.read(gamedata.read_bytes())
    by = {e.name.lower(): e for e in entries}
    for n in ('monnifs.csv', 'monsters.csv', 'horsemap.csv'):
        require(n in by, f'gamedata.mpk has no {n}')

    monnif = stock_row(by['monnifs.csv'].data, STOCK_MONNIF)
    monnif[0], monnif[1], monnif[2] = MONNIF_ID, 'Chimera Mount (saddled)', Path(PRIVATE_NIF).stem
    monnif[9], monnif[11] = '0', RIDE_ANIMS
    monster = stock_row(by['monsters.csv'].data, STOCK_MONSTER)
    monster[0], monster[1], monster[2] = MONSTER_ID, 'Chimera Mount', MONNIF_ID
    mount = [MOUNT_ID, 'Chimera Mount', MONSTER_ID, '0']

    changed = {
        'monnifs.csv': append_line(by['monnifs.csv'].data, monnif),
        'monsters.csv': append_line(by['monsters.csv'].data, monster),
        'horsemap.csv': append_line(by['horsemap.csv'].data, mount),
    }
    new_entries = [archive.Entry(e.name, changed.get(e.name.lower(), e.data), e.timestamp, e.flags) for e in entries]
    blob = archive.write(name, new_entries)
    _, check = archive.read(blob)
    require([e.name for e in check] == [e.name for e in entries], 'entry order changed')
    for old, new in zip(entries, check):
        if old.name.lower() not in changed:
            require(old.data == new.data and old.timestamp == new.timestamp and old.flags == new.flags,
                    f'{old.name} changed')
    archive.verify_memory_image(blob)
    return dict(nif=nif, local=local, gamedata=blob, rows=dict(monnifs=monnif, monsters=monster, horsemap=mount))


def install(client, backups):
    plan = build(client)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    folder = backups / f'client-chimera-saddle-{stamp}'
    folder.mkdir(parents=True)
    gamedata = client / 'gamedata.mpk'
    shutil.copy2(gamedata, folder / 'gamedata.mpk')
    target = client / 'figures' / PRIVATE_NIF
    manifest = dict(client=str(client), gamedata_before=hashlib.sha256(gamedata.read_bytes()).hexdigest(),
                    gamedata_after=hashlib.sha256(plan['gamedata']).hexdigest(), added=[str(target)],
                    rows=plan['rows'])
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    (folder / 'README.txt').write_text(
        'Before the private saddled Chimera mount (install_chimera_mount.py).\n'
        f'Restore: python source/tools/horses/install_chimera_mount.py rollback "{folder}"\n', encoding='utf-8')
    target.write_bytes(plan['nif'])
    gamedata.write_bytes(plan['gamedata'])
    print('Installed. Backup and rollback:', folder)


def rollback(folder):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    client = Path(manifest['client'])
    gamedata = client / 'gamedata.mpk'
    require(hashlib.sha256(gamedata.read_bytes()).hexdigest() == manifest['gamedata_after'],
            'gamedata.mpk changed since this install; roll back newer installs first')
    shutil.copy2(folder / 'gamedata.mpk', gamedata)
    for added in manifest['added']:
        Path(added).unlink(missing_ok=True)
    print('Rolled back', folder)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('action', nargs='?', default='plan', choices=['plan', 'install', 'rollback'])
    p.add_argument('folder', nargs='?', type=Path, help='backup folder (rollback)')
    p.add_argument('--client', type=Path, help='client-modern/app folder')
    p.add_argument('--backups', type=Path, help='backup root (default: <client>/../../backups)')
    a = p.parse_args()
    if a.action == 'rollback':
        rollback(a.folder)
        return
    require(a.client is not None, '--client is required')
    plan = build(a.client)
    print('saddle under', SADDLE_PARENT, 'local', [round(x, 2) for x in plan['local']], 'model space', SADDLE_AT)
    for k, v in plan['rows'].items():
        print(k, ','.join(v)[:120])
    print('gamedata.mpk', len(plan['gamedata']), 'bytes; NIF', len(plan['nif']), 'bytes')
    if a.action == 'install':
        install(a.client, a.backups or a.client.parents[1] / 'backups')
    else:
        print('Preview only.')


if __name__ == '__main__':
    main()
