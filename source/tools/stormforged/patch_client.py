"""Build-identified Midgard Mauler -> Stormforged patch. Never writes over the input.

No stock model/effect catalog is changed. A private PE section holds the class name,
description and one initializer trampoline. The Hib/Alb Mauler resources remain intact.
"""
import argparse
import hashlib
from pathlib import Path
import struct

SUPPORTED = {"f55ed6b068e22ce8e1106871c2fad6ee10c18390bbb8b5dc772219ad8c8b83bb"}
BASE = 0x400000


def align(value, boundary):
    return (value + boundary - 1) // boundary * boundary


def patch(original, sovereign=False):
    digest = hashlib.sha256(original).hexdigest()
    if digest not in SUPPORTED:
        raise ValueError(f"Unsupported client SHA-256 {digest}; no patch applied")
    data = bytearray(original)
    pe = struct.unpack_from("<I", data, 60)[0]
    if data[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", data, pe+4)[0] != 0x14c:
        raise ValueError("Expected x86 PE")
    optional = pe + 24
    count = struct.unpack_from("<H", data, pe+6)[0]
    table = optional + struct.unpack_from("<H", data, pe+20)[0]
    sections = [struct.unpack_from("<8sIIIIIIHHI", data, table+40*i) for i in range(count)]

    def offset(va):
        for section in sections:
            if section[2] <= va-BASE < section[2]+max(section[1],section[3]):
                return section[4]+va-BASE-section[2]
        raise ValueError(f"Address outside image: {va:x}")

    def replace(va, before, after):
        pos = offset(va)
        if bytes(data[pos:pos+len(before)]) != before or len(before) != len(after):
            raise ValueError(f"Unexpected instruction at {va:x}")
        data[pos:pos+len(before)] = after

    file_align = struct.unpack_from("<I", data, optional+36)[0]
    section_align = struct.unpack_from("<I", data, optional+32)[0]
    first_raw = min(s[4] for s in sections if s[4])
    if table+(count+1)*40 > first_raw:
        raise ValueError("No space for a private PE section header")
    raw = align(len(data), file_align)
    rva = align(max(s[2]+max(s[1],s[3]) for s in sections), section_align)
    va = BASE+rva
    label = b"Storm Sovereign\0" if sovereign else b"Stormforged\0"
    description = b"A royal master of thunder, weapons and stealth, accompanied by a loyal Storm Wolf.\0" if sovereign else b"A master of thunder: lightning, storm wards, restoration, stealth and stormbound allies.\0"
    label_va = va+64
    desc_va = label_va+len(label)
    # Replace only Midgard's label initializer, preserving ECX and the original call convention.
    stub = b"\x8b\x0d"+struct.pack("<I",0x104c0ec)+b"\x6a\x00\x68"+struct.pack("<I",label_va)
    stub += b"\xe8"+struct.pack("<i",0x7303fb-(va+len(stub)+5))
    stub += b"\xe9"+struct.pack("<i",0x44f3f8-(va+len(stub)+5))
    payload = stub.ljust(64,b"\x90")+label+description
    before = bytes(data[offset(0x44f3eb):offset(0x44f3f8)])
    expected = b"\x8b\x0d\xec\xc0\x04\x01\x57\x56\xe8"+struct.pack("<i",0x7303fb-0x44f3f8)
    if before != expected:
        raise ValueError("Unexpected Midgard initializer")
    replace(0x44f3eb, before, b"\xe9"+struct.pack("<i",va-0x44f3f0)+b"\x90"*(len(before)-5))
    # Character-creation registration: use private fallback strings rather than Mauler lore.
    replace(0x5b2769, b"\xc7\x45\xb0"+struct.pack("<I",0x90d), b"\xc7\x45\xb0"+struct.pack("<I",0))
    replace(0x5b2770, b"\xc7\x45\xb4"+struct.pack("<I",0x940abc), b"\xc7\x45\xb4"+struct.pack("<I",label_va))
    replace(0x5b2785, b"\xc7\x45\xc8"+struct.pack("<I",0x905), b"\xc7\x45\xc8"+struct.pack("<I",0))
    replace(0x5b278c, b"\xc7\x45\xcc"+struct.pack("<I",0x95ebe0), b"\xc7\x45\xcc"+struct.pack("<I",desc_va))
    # Native races are Norseman, Kobold, Minotaur and Troll. Keep Norseman and
    # replace the next two with Dwarf and Troll; remove the duplicate final insertion.
    replace(0x5b27bb, b"\xc7\x45\xec\x08\x00\x00\x00", b"\xc7\x45\xec\x07\x00\x00\x00")
    replace(0x5b27ce, b"\xc7\x45\xec\x14\x00\x00\x00", b"\xc7\x45\xec\x06\x00\x00\x00")
    replace(0x5b27e8, b"\xe8"+struct.pack("<i",0x5b4a65-0x5b27ed), b"\x83\xc4\x04\x90\x90")
    data.extend(b"\0"*(raw-len(data)))
    raw_size = align(len(payload),file_align)
    data.extend(payload.ljust(raw_size,b"\0"))
    struct.pack_into("<8sIIIIIIHHI",data,table+count*40,b".storm\0\0",len(payload),rva,raw_size,raw,0,0,0,0,0x60000020)
    struct.pack_into("<H",data,pe+6,count+1)
    struct.pack_into("<I",data,optional+56,align(rva+len(payload),section_align))
    struct.pack_into("<I",data,optional+4,struct.unpack_from("<I",data,optional+4)[0]+raw_size)
    struct.pack_into("<I",data,optional+64,0)
    checksum = 0
    for pos in range(0,len(data),2):
        checksum += int.from_bytes(data[pos:pos+2],"little")
        checksum = (checksum & 0xffff)+(checksum >> 16)
    checksum = (checksum & 0xffff)+(checksum >> 16)
    struct.pack_into("<I",data,optional+64,checksum+len(data))
    return bytes(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client",type=Path)
    parser.add_argument("--output",type=Path,help="Write a new file; omission is preview-only")
    args=parser.parse_args()
    original=args.client.read_bytes()
    result=patch(original)
    if args.output:
        if args.output.resolve() == args.client.resolve():
            raise ValueError("Output must be separate")
        with args.output.open("xb") as stream:
            stream.write(result)
    print("Original SHA256:",hashlib.sha256(original).hexdigest())
    print("Patched SHA256:",hashlib.sha256(result).hexdigest())
    print("Written to "+str(args.output) if args.output else "Preview only; no client was changed")


if __name__ == "__main__":
    main()
