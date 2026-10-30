"""Hash-guarded Stormforged patch for the private 1.130 x86 client.

Only Midgard Mauler registration is changed. Wire class 61 stays intact:
the existing server creation handler converts it to Stormforged (64).
Never writes over the input. No game execution is performed.
"""
import argparse
import hashlib
from pathlib import Path
import struct

SUPPORTED = '3915a495253040a4cdfc79d265a8d268797304eb46b9a34d51a88d49a8445022'
BASE = 0x400000
RACES = (5, 6, 7, 8, 14, 17, 20)


def align(n, boundary):
    return (n + boundary - 1) // boundary * boundary


def patch(original, sovereign=False):
    if hashlib.sha256(original).hexdigest() != SUPPORTED:
        raise ValueError('Unsupported modern game.dll SHA256; no patch applied')
    data = bytearray(original)
    pe = struct.unpack_from('<I', data, 60)[0]
    if data[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', data, pe+4)[0] != 0x14c:
        raise ValueError('Expected x86 PE')
    opt = pe + 24
    if struct.unpack_from('<I', data, opt+28)[0] != BASE:
        raise ValueError('Unexpected image base')
    count = struct.unpack_from('<H', data, pe+6)[0]
    table = opt + struct.unpack_from('<H', data, pe+20)[0]
    sections = [struct.unpack_from('<8sIIIIIIHHI', data, table+40*i) for i in range(count)]

    def offset(va):
        for s in sections:
            if s[2] <= va-BASE < s[2]+s[3]:
                return s[4]+va-BASE-s[2]
        raise ValueError(f'Address not backed by file: {va:x}')

    def replace(va, before, after):
        pos = offset(va)
        if len(before) != len(after) or data[pos:pos+len(before)] != before:
            raise ValueError(f'Unexpected instruction at {va:x}')
        data[pos:pos+len(before)] = after

    fa = struct.unpack_from('<I', data, opt+36)[0]
    sa = struct.unpack_from('<I', data, opt+32)[0]
    if table+(count+1)*40 > min(s[4] for s in sections if s[4]):
        raise ValueError('No section header space')
    raw = align(len(data), fa)
    rva = align(max(s[2]+max(s[1], s[3]) for s in sections), sa)
    va = BASE+rva
    label = b'Storm Sovereign\0' if sovereign else b'Stormforged\0'
    description = b'A royal master of thunder, weapons and stealth, accompanied by a loyal Storm Wolf.\0' if sovereign else b'A master of thunder: lightning, storm wards, restoration, stealth and stormbound allies.\0'
    label_va = va+256
    desc_va = label_va+len(label)

    def branch(op, at, target):
        return bytes([op])+struct.pack('<i', target-(at+5))

    # Midgard class-name initializer, between the Alb and Hib initializers.
    stub = b'\x8b\x0d'+struct.pack('<I', 0xd93264)+b'\x6a\x00\x68'+struct.pack('<I', label_va)
    stub += branch(0xe8, va+len(stub), 0x7303db)
    stub += branch(0xe9, va+len(stub), 0x44efa8)
    before = bytes.fromhex('8b0d6432d9005756e833142e00')
    replace(0x44ef9b, before, branch(0xe9, 0x44ef9b, va)+b'\x90'*8)
    # Creation name and lore: zero resource ID forces private fallback text.
    for at, prefix, old, new in [
        (0x5b21f0, 'c745b0', 0x90d, 0),
        (0x5b21f7, 'c745b4', 0x940cec, label_va),
        (0x5b220c, 'c745c8', 0x905, 0),
        (0x5b2213, 'c745cc', 0x95ef00, desc_va),
    ]:
        p = bytes.fromhex(prefix)
        replace(at, p+struct.pack('<I', old), p+struct.pack('<I', new))
    # Midgard realm class-group caption; other realms retain their Mauler text.
    replace(0x52d616, b'\x68'+struct.pack('<I', 0x903), b'\x68'+struct.pack('<I', 0))
    replace(0x52d61b, b'\x68'+struct.pack('<I', 0x953598), b'\x68'+struct.pack('<I', label_va))
    # Replay the original list-insertion calling convention for all seven races.
    race_va = va+64
    races = bytearray()
    for race in RACES:
        races += b'\xc7\x45\xec'+struct.pack('<I', race)
        races += b'\x8d\x45\xec\x50\x8d\x45\xd0'
        races += branch(0xe8, race_va+len(races), 0x5b440d)
    races += branch(0xe9, race_va+len(races), 0x5b2274)
    # Exact supported input hash guards the complete replaced original race block.
    start, end = offset(0x5b222c), offset(0x5b2274)
    replace(0x5b222c, bytes(original[start:end]), branch(0xe9, 0x5b222c, race_va)+b'\x90'*(end-start-5))
    payload = stub.ljust(64, b'\x90')+races
    if len(payload) > 256:
        raise ValueError('Trampoline exceeds reserved space')
    payload = payload.ljust(256, b'\x90')+label+description
    if sovereign:
        # 1.130's resist handler (41a605) stores primary+racial for the label,
        # while its color also sees secondary RAs (41a66a -> 4c0a64).
        # Include secondary resistance using ResistCalculator's exact ordering:
        # primary + trunc((100-primary)*secondary/100) + racial, capped at 70.
        # Preserve item/buff/cap/secondary fields used by the UI's details.
        stub_offset = align(len(payload), 16)
        resist_va = va + stub_offset
        resist = bytes.fromhex(
            '50 52'                 # save index and primary+racial
            '0f bf 4f ee'           # ecx = racial, from buff pointer - 18
            '29 ca'                # edx = primary
            'b9 64 00 00 00 29 d1' # ecx = 100-primary
            '0f b6 56 3f'          # edx = secondary byte
            '0f af ca 89 c8 99'    # eax = product, cdq
            'b9 64 00 00 00 f7 f9' # signed divide by 100 (truncate)
            '5a 01 c2'             # original total + secondary contribution
            '83 fa 46 7e 05 ba 46 00 00 00' # clamp to 70
            '58 89 90 4c 93 d4 00') # restore index; original total store
        resist += branch(0xe9, resist_va+len(resist), 0x41a63f)
        replace(0x41a639, bytes.fromhex('89 90 4c 93 d4 00'),
                branch(0xe9, 0x41a639, resist_va)+b'\x90')
        payload = payload.ljust(stub_offset, b'\x90') + resist
    raw_size = align(len(payload), fa)
    data.extend(b'\0'*(raw-len(data)))
    data.extend(payload.ljust(raw_size, b'\0'))
    struct.pack_into('<8sIIIIIIHHI', data, table+count*40, b'.custom\0', len(payload), rva, raw_size, raw, 0, 0, 0, 0, 0x60000020)
    struct.pack_into('<H', data, pe+6, count+1)
    struct.pack_into('<I', data, opt+56, align(rva+len(payload), sa))
    struct.pack_into('<I', data, opt+4, struct.unpack_from('<I', data, opt+4)[0]+raw_size)
    struct.pack_into('<I', data, opt+64, 0)
    checksum = 0
    for pos in range(0, len(data), 2):
        checksum += int.from_bytes(data[pos:pos+2], 'little')
        checksum = (checksum & 0xffff)+(checksum >> 16)
    checksum = (checksum & 0xffff)+(checksum >> 16)
    struct.pack_into('<I', data, opt+64, checksum+len(data))
    return bytes(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('client', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = patch(args.client.read_bytes())
    if args.output:
        with args.output.open('xb') as stream:
            stream.write(result)
    print('Patched SHA256:', hashlib.sha256(result).hexdigest())
    print('Written to '+str(args.output) if args.output else 'Preview only')
