"""Execute the emitted x86 arithmetic in a bounded instruction interpreter.

This checks the actual detour bytes, signed rounding, cap, register/stack
preservation and continuation without starting the game or executing native code.
"""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stormforged'))
from patch_modern_client import patch

REPO=Path(__file__).resolve().parents[3]

def offset(data,va):
 pe=struct.unpack_from('<I',data,60)[0];opt=pe+24
 table=opt+struct.unpack_from('<H',data,pe+20)[0]
 for i in range(struct.unpack_from('<H',data,pe+6)[0]):
  _,_,rva,size,raw,*_=struct.unpack_from('<8sIIIIIIHHI',data,table+i*40)
  if rva<=va-0x400000<rva+size: return raw+va-0x400000-rva
 raise AssertionError(hex(va))

def run(data,primary,racial,secondary,index):
 at=offset(data,0x41a639)
 assert data[at]==0xe9 and data[at+5]==0x90
 va=0x41a63e+struct.unpack_from('<i',data,at+1)[0]
 pc=offset(data,va);start=pc
 regs={'a':index*4,'c':1234,'d':primary+racial}
 stack=[];stored=None
 signed=lambda n: (n+2**31)%2**32-2**31
 for _ in range(50):
  b=data[pc:pc+8]
  if b[0] in (0x50,0x52): stack.append(regs['a' if b[0]==0x50 else 'd']);pc+=1
  elif b[:4]==bytes.fromhex('0f bf 4f ee'): regs['c']=racial;pc+=4
  elif b[:2]==b'\x29\xca': regs['d']-=regs['c'];pc+=2
  elif b[0]==0xb9: regs['c']=struct.unpack_from('<i',data,pc+1)[0];pc+=5
  elif b[:2]==b'\x29\xd1': regs['c']-=regs['d'];pc+=2
  elif b[:4]==bytes.fromhex('0f b6 56 3f'): regs['d']=secondary;pc+=4
  elif b[:3]==bytes.fromhex('0f af ca'): regs['c']=signed(regs['c']*regs['d']);pc+=3
  elif b[:2]==b'\x89\xc8': regs['a']=regs['c'];pc+=2
  elif b[0]==0x99: regs['d']=-1 if regs['a']<0 else 0;pc+=1
  elif b[:2]==b'\xf7\xf9':
   dividend=(regs['d']<<32)+(regs['a']&0xffffffff)
   regs['a']=int(dividend/regs['c']);regs['d']=dividend-regs['a']*regs['c'];pc+=2
  elif b[0] in (0x58,0x5a): regs['a' if b[0]==0x58 else 'd']=stack.pop();pc+=1
  elif b[:2]==b'\x01\xc2': regs['d']+=regs['a'];pc+=2
  elif b[:3]==b'\x83\xfa\x46': less_equal=regs['d']<=70;pc+=3
  elif b[:2]==b'\x7e\x05': pc+=2+(5 if less_equal else 0)
  elif b[0]==0xba: regs['d']=struct.unpack_from('<i',data,pc+1)[0];pc+=5
  elif b[:6]==bytes.fromhex('89 90 4c 93 d4 00'): stored=(0xd4934c+regs['a'],regs['d']);pc+=6
  elif b[0]==0xe9:
   assert va+(pc-start)+5+struct.unpack_from('<i',data,pc+1)[0]==0x41a63f
   assert not stack and regs['a']==index*4
   return stored
  else: raise AssertionError(f'Unexpected instruction {b.hex()}')
 raise AssertionError('Detour did not return')

class ResistDisplayTests(unittest.TestCase):
 def test_emitted_detour_matches_server_formula_and_preserves_every_resist_slot(self):
  original=(REPO/'artifacts/modern-client-test/backups/client-bundle-20261021-165832-708287/game.original.dll').read_bytes()
  data=patch(original,sovereign=True)
  for primary in (-40,-1,0,1,24,26,50,55,75,110):
   for racial in (0,3,5,10):
    for secondary in (0,2,6,10,16,25,50,100):
     for index in range(9):
      expected=min(70,primary+int((100-primary)*secondary/100)+racial)
      self.assertEqual(run(data,primary,racial,secondary,index),(0xd4934c+index*4,expected))

if __name__=='__main__': unittest.main()
