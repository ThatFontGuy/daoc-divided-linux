"""Raise the 1.130 client's monster model ceiling from 2500 to 32768.

The client keeps monsters.csv in a static array (464 bytes an entry, 2500 entries at 0xB4E378) and refuses
higher IDs at two compares, the loader's and the getter's. The array can't grow where it sits, so this moves it:
a new zero-filled section holds a wider array, and every code reference is repointed. The technique comes from
Camelot Studio (MIT, measured on 1.127); the addresses below were found again by disassembling the pristine 1.130
game.dll: 2 compares and 63 references, none past the first entry. The other 2500 constants in the DLL were read
and aren't this table. A section with no file bytes adds nothing to game.dll beyond its header.

This is not part of the normal client build. Nothing here has been run in game yet.

  python model_table.py <pristine game.dll> <output game.dll>       the class slot build plus the wider table
"""
import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patch_class_slots as slots  # noqa: E402

OLD_BASE = 0xB4E378
STRIDE = 0x1D0
OLD_CAP = 2500
NEW_CAP = 32768          # the server sends model IDs as a word; higher ones are unmeasured
CAP_SITES = 0x433F28, 0x457795   # cmp eax,0x9c4
# (VA of the 32-bit address in the instruction, field offset inside an entry)
REFERENCES = (
    (0x405ef1, 0x78), (0x41188d, 0xc4), (0x41192b, 0xc4), (0x41193b, 0x70), (0x411cc4, 0x70),
    (0x411cea, 0xc8), (0x412320, 0x70), (0x412346, 0xc8), (0x413f48, 0x70), (0x413f6e, 0xc8),
    (0x413f97, 0xc0), (0x413fa1, 0xbc), (0x413fc6, 0xbc), (0x416a4d, 0x74), (0x416a69, 0x90),
    (0x416fc1, 0xd8), (0x417003, 0xdc), (0x41960e, 0x78), (0x4196e7, 0x78), (0x419dd2, 0x70),
    (0x419df8, 0xc8), (0x419e21, 0xc0), (0x419e2b, 0xbc), (0x419e54, 0xbc), (0x419ea1, 0x74),
    (0x41a00c, 0xdc), (0x4217d8, 0x0), (0x422051, 0x144), (0x422064, 0x134), (0x422076, 0x138),
    (0x42208d, 0x140), (0x4221b3, 0xf4), (0x4221ce, 0x98), (0x4233a0, 0x70), (0x4233c6, 0xc8),
    (0x4233e7, 0x140), (0x4234d3, 0xc0), (0x4234dd, 0xbc), (0x423502, 0xbc), (0x42bea2, 0x78),
    (0x42d5fa, 0x78), (0x42e395, 0x78), (0x42e3bf, 0x78), (0x432a0a, 0xb4), (0x432a65, 0x40),
    (0x43339c, 0xb4), (0x43387e, 0x70), (0x4338b3, 0xc0), (0x4338bd, 0xbc), (0x4338e2, 0xbc),
    (0x433ea3, 0xd8), (0x433f36, 0x0), (0x434e77, 0x70), (0x43a161, 0x78), (0x450192, 0x98),
    (0x4577ac, 0x0), (0x472e43, 0x170), (0x472f0b, 0x148), (0x473024, 0x19c), (0x47329f, 0x170),
    (0x473361, 0x148), (0x47347a, 0x19c), (0x473612, 0x0),
)


def align(n, boundary):
    return (n + boundary - 1) & -boundary


def widen(original, cap=NEW_CAP):
    """Return original with the monster table moved to a new section; every site is checked before any is written."""
    if not OLD_CAP < cap <= NEW_CAP:
        raise ValueError(f'Model ceiling must be {OLD_CAP + 1}-{NEW_CAP}')
    data = bytearray(original)
    pe = struct.unpack_from('<I', data, 60)[0]
    opt = pe + 24
    if data[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<I', data, opt+28)[0] != slots.BASE:
        raise ValueError('Expected the 1.130 game.dll')
    count = struct.unpack_from('<H', data, pe+6)[0]
    table = opt + struct.unpack_from('<H', data, pe+20)[0]
    sections = [struct.unpack_from('<8sIIIIIIHHI', data, table+40*i) for i in range(count)]
    if any(s[0].rstrip(b'\0') == b'.models' for s in sections):
        raise ValueError('The model table is already moved')
    if table+(count+1)*40 > min(s[4] for s in sections if s[4]):
        raise ValueError('No section header space')

    def offset(va):
        rva = va - slots.BASE
        for s in sections:
            if s[2] <= rva < s[2] + s[3]:
                return s[4] + rva - s[2]
        raise ValueError(f'Address {va:x} is outside the image')

    sa = struct.unpack_from('<I', data, opt+32)[0]
    rva = align(max(s[2] + max(s[1], s[3]) for s in sections), sa)
    size = cap * STRIDE
    base = slots.BASE + rva
    for at in CAP_SITES:
        if data[offset(at):offset(at)+5] != b'\x3d' + struct.pack('<I', OLD_CAP):
            raise ValueError(f'Unexpected instruction at {at:x}')
    for at, field in REFERENCES:
        if struct.unpack_from('<I', data, offset(at))[0] != OLD_BASE + field:
            raise ValueError(f'Unexpected table reference at {at:x}')
    for at in CAP_SITES:
        struct.pack_into('<I', data, offset(at)+1, cap)
    for at, field in REFERENCES:
        struct.pack_into('<I', data, offset(at), base + field)
    struct.pack_into('<8sIIIIIIHHI', data, table+count*40, b'.models\0', size, rva, 0, 0, 0, 0, 0, 0, 0xC0000080)
    struct.pack_into('<H', data, pe+6, count+1)
    struct.pack_into('<I', data, opt+12, struct.unpack_from('<I', data, opt+12)[0] + size)
    struct.pack_into('<I', data, opt+56, align(rva+size, sa))
    struct.pack_into('<I', data, opt+64, 0)
    checksum = 0
    for pos in range(0, len(data), 2):
        checksum += int.from_bytes(data[pos:pos+2], 'little')
        checksum = (checksum & 0xffff)+(checksum >> 16)
    checksum = (checksum & 0xffff)+(checksum >> 16)
    struct.pack_into('<I', data, opt+64, checksum+len(data))
    return bytes(data)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    original = Path(sys.argv[1]).read_bytes()
    built = widen(slots.patch(original)[0])
    Path(sys.argv[2]).write_bytes(built)
    print(f'{sys.argv[2]}: model ceiling {NEW_CAP}, sha256 {hashlib.sha256(built).hexdigest()}')


if __name__ == '__main__':
    main()
