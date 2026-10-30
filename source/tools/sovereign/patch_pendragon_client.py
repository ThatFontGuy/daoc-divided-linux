"""Verified 1.130 Albion selection patch, retaining Midgard and the resist fix."""
import hashlib
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stormforged'))
from patch_modern_client import patch as storm_patch, SUPPORTED, align

RACES=(1,2,3,4,13,16,19)

def patch(original,sovereign=True):
 if not sovereign: raise ValueError('Pendragon requires the Sovereign client baseline')
 data=bytearray(storm_patch(original,sovereign=True))
 pe=struct.unpack_from('<I',data,60)[0];opt=pe+24
 count=struct.unpack_from('<H',data,pe+6)[0]
 table=opt+struct.unpack_from('<H',data,pe+20)[0]
 sections=[struct.unpack_from('<8sIIIIIIHHI',data,table+i*40) for i in range(count)]
 if table+(count+1)*40>min(s[4] for s in sections if s[4]): raise ValueError('No PE section header space')
 def offset(va):
  for s in sections:
   if s[2]<=va-0x400000<s[2]+s[3]: return s[4]+va-0x400000-s[2]
  raise ValueError('Address is not file backed')
 def replace(va,before,after):
  pos=offset(va)
  if len(before)!=len(after) or data[pos:pos+len(before)]!=before: raise ValueError(f'Unexpected Albion instruction {va:x}')
  data[pos:pos+len(before)]=after
 def branch(at,target): return b'\xe9'+struct.pack('<i',target-at-5)
 fa=struct.unpack_from('<I',data,opt+36)[0];sa=struct.unpack_from('<I',data,opt+32)[0]
 raw=align(len(data),fa);rva=align(max(s[2]+max(s[1],s[3]) for s in sections),sa);va=0x400000+rva
 label=b'Pendragon Sovereign\0';description=b'Albion royal champion of holy fire, weapons and stealth, accompanied by a loyal Royal Lion.\0'
 label_va=va+256;description_va=label_va+len(label)
 # Keep EDI/ESI holding the original Mauler resource/name for the following realms.
 name=bytes.fromhex('8b0d6432d900 bf0d090000 beec0c9400 6a00 68')+struct.pack('<I',label_va)
 name+=b'\xe8'+struct.pack('<i',0x7303db-(va+len(name)+5))
 name+=branch(va+len(name),0x44ef8c)
 replace(0x44ef75,bytes.fromhex('8b0d6432d900 bf0d090000 57 beec0c9400 56 e84f142e00'),branch(0x44ef75,va)+b'\x90'*18)
 for at,prefix,old,new in [(0x5b0ade,'c745b0',0x90d,0),(0x5b0ae5,'c745b4',0x940cec,label_va),
  (0x5b0af9,'c745c8',0x905,0),(0x5b0b00,'c745cc',0x95ef00,description_va)]:
  p=bytes.fromhex(prefix);replace(at,p+struct.pack('<I',old),p+struct.pack('<I',new))
 replace(0x52d32d,b'\x68'+struct.pack('<I',0x902),b'\x68'+struct.pack('<I',0))
 replace(0x52d332,b'\x68'+struct.pack('<I',0x9535d4),b'\x68'+struct.pack('<I',label_va))
 # Albion has already pushed its first race pointer at5b0adb. Balance it once,
 # then replay the original list-insertion ABI (EAX=ESI, callee pops one pointer).
 races_va=va+64;races=bytearray(b'\x58')
 for race in RACES:
  races+=bytes.fromhex('c745ec')+struct.pack('<I',race)+bytes.fromhex('8d45ec 50 89f0')
  races+=b'\xe8'+struct.pack('<i',0x5b440d-(races_va+len(races)+5))
 races+=branch(races_va+len(races),0x5b0b57)
 start,end=offset(0x5b0b19),offset(0x5b0b57)
 replace(0x5b0b19,bytes(data[start:end]),branch(0x5b0b19,races_va)+b'\x90'*(end-start-5))
 payload=name.ljust(64,b'\x90')+races
 if len(payload)>256: raise ValueError('Albion stubs exceed reserved area')
 payload=payload.ljust(256,b'\x90')+label+description
 size=align(len(payload),fa)
 data.extend(b'\0'*(raw-len(data)));data.extend(payload.ljust(size,b'\0'))
 struct.pack_into('<8sIIIIIIHHI',data,table+count*40,b'.pendrag',len(payload),rva,size,raw,0,0,0,0,0x60000020)
 struct.pack_into('<H',data,pe+6,count+1)
 struct.pack_into('<I',data,opt+56,align(rva+len(payload),sa))
 struct.pack_into('<I',data,opt+4,struct.unpack_from('<I',data,opt+4)[0]+size)
 struct.pack_into('<I',data,opt+64,0)
 checksum=0
 for pos in range(0,len(data),2):
  checksum+=int.from_bytes(data[pos:pos+2],'little');checksum=(checksum&0xffff)+(checksum>>16)
 checksum=(checksum&0xffff)+(checksum>>16)
 struct.pack_into('<I',data,opt+64,checksum+len(data))
 return bytes(data)
