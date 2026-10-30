"""Optional verification (needs pefile and unicorn): emulate the creation screen's class-button getters, select()
and constructor loop of a patched game.dll against the 20-slot array at +0x13C.
Usage: python verify_screen_emulation.py <patched game.dll>"""
import sys,struct,pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
pe=pefile.PE(sys.argv[1]);img=pe.get_memory_mapped_image();B=pe.OPTIONAL_HEADER.ImageBase
def mu_new():
    mu=Uc(UC_ARCH_X86,UC_MODE_32);mu.mem_map(B,(len(img)+0xfff)&~0xfff);mu.mem_write(B,img);mu.mem_map(0x100000,0x40000);return mu
obj=0x110000;btns=0x120000
ok=True
for fn,idxv,field,expect in [(0x5a010f,17,0x48,1),(0x5a0124,19,0x48,0),(0x5a010f,20,0x48,None),(0x5a010f,15,0x48,1)]:
    mu=mu_new()
    for k in range(20):mu.mem_write(obj+0x13c+4*k,struct.pack('<I',btns+0x100*k));mu.mem_write(btns+0x100*k+0x48,b'\x77')
    sp=0x10f000;mu.mem_write(sp,struct.pack('<I',0x100100));mu.mem_write(0x100100,b'\xf4')
    mu.reg_write(UC_X86_REG_ESP,sp);mu.reg_write(UC_X86_REG_ECX,obj);mu.reg_write(UC_X86_REG_EAX,idxv)
    mu.emu_start(fn,0x100100,count=50)
    vals=[mu.mem_read(btns+0x100*k+0x48,1)[0] for k in range(20)]
    changed=[k for k,v in enumerate(vals) if v!=0x77]
    good=(changed==[] if expect is None else changed==[idxv] and vals[idxv]==expect)
    print(hex(fn),'index',idxv,'changed',changed,'ok',good);ok&=good
# select(index) at 0x5a016d: edi=obj, arg on stack; walks all 20 and stores selection at +0x134
mu=mu_new()
for k in range(20):
    b=btns+0x100*k;mu.mem_write(obj+0x13c+4*k,struct.pack('<I',b));mu.mem_write(b,struct.pack('<I',0x130000))  # vtable
mu.mem_write(0x130000+0x64,struct.pack('<I',0x100200));mu.mem_write(0x100200,b'\xc3')  # vtable+0x64 -> ret
sp=0x10f000;mu.mem_write(sp,struct.pack('<II',0x100100,18));mu.mem_write(0x100100,b'\xf4')
mu.reg_write(UC_X86_REG_ESP,sp);mu.reg_write(UC_X86_REG_EDI,obj)
mu.emu_start(0x5a016d,0x100100,count=2000)
flags=[struct.unpack('<I',bytes(mu.mem_read(btns+0x100*k+0x70,4)))[0]&1 for k in range(20)]
sel=struct.unpack('<I',bytes(mu.mem_read(obj+0x134,4)))[0]
good=sel==18 and flags==[1 if k==18 else 0 for k in range(20)];print('select(18): selected',sel,'flags',flags,'ok',good);ok&=good
print('ALL OK' if ok else 'FAILED')
# constructor loop 0x59FCF6..0x59FD29 with the UI lookups stubbed: 0x53E115(push id) -> fake control; 0x4E9B51 -> button
from unicorn import UC_HOOK_CODE
mu=mu_new();ebp=0x118000;mu.reg_write(UC_X86_REG_EBP,ebp);mu.reg_write(UC_X86_REG_ESP,ebp-0x100);mu.reg_write(UC_X86_REG_EBX,obj)
mu.mem_write(obj,b'\xaa'*0x200);ids=[]
def rd(a):return struct.unpack('<I',bytes(mu.mem_read(a,4)))[0]
def hook(m,addr,size,_):
    sp=m.reg_read(UC_X86_REG_ESP)
    if addr==0x53e115:
        cid=rd(sp+4);ids.append(cid);m.reg_write(UC_X86_REG_EAX,0x130000+cid*0x10);m.reg_write(UC_X86_REG_ESP,sp+8);m.reg_write(UC_X86_REG_EIP,rd(sp))
    elif addr==0x4e9b51:
        m.reg_write(UC_X86_REG_EAX,m.reg_read(UC_X86_REG_ESI));m.reg_write(UC_X86_REG_ESP,sp+4);m.reg_write(UC_X86_REG_EIP,rd(sp))
mu.hook_add(UC_HOOK_CODE,hook)
mu.emu_start(0x59fcf6,0x59fd29,count=5000)
new=[rd(obj+0x13c+4*k) for k in range(20)];old=bytes(mu.mem_read(obj+0xd8,0x40))
good=ids==list(range(1021,1041)) and new==[0x130000+cid*0x10 for cid in ids] and old==b'\xaa'*0x40
print('ctor loop: controls',ids[0],'..',ids[-1],len(ids),'stored at +0x13C',good,'old array untouched',old==b'\xaa'*0x40)
print('CTOR OK' if good else 'CTOR FAILED')

# adapter registration hook: run from 0x5ADCB3 with ESI = adapter manager; 0x4B701A recorded (ret 0xC)
mu=mu_new();owner=0x112000;esp0=0x10f000
mu.reg_write(UC_X86_REG_ESP,esp0);mu.reg_write(UC_X86_REG_ESI,owner);mu.reg_write(UC_X86_REG_EBX,0x1234);mu.reg_write(UC_X86_REG_EDI,0x5678)
calls=[]
def cstr(m,a):
    out=b''
    while True:
        c=bytes(m.mem_read(a,1))
        if c==b'\0':return out.decode()
        out+=c;a+=1
def hook2(m,addr,size,_):
    if addr==0x4b701a:
        sp=m.reg_read(UC_X86_REG_ESP);ret,o,slot,name=struct.unpack('<4I',bytes(m.mem_read(sp,16)))
        calls.append((o,slot,cstr(m,name)));m.mem_write(slot,struct.pack('<I',0xADA00000+len(calls)))
        m.reg_write(UC_X86_REG_ESP,sp+16);m.reg_write(UC_X86_REG_EIP,ret)
mu.hook_add(UC_HOOK_CODE,hook2)
mu.emu_start(0x5adcb3,0x5adcb8,count=500)
names=[c[2] for c in calls];owners={c[0] for c in calls};slots=[c[1] for c in calls]
pushed=struct.unpack('<I',bytes(mu.mem_read(mu.reg_read(UC_X86_REG_ESP),4)))[0]
good=(names==['class_16_text','class_17_text','class_18_text','class_19_text'] and owners=={owner} and len(set(slots))==4
      and all(struct.unpack('<I',bytes(mu.mem_read(s,4)))[0]==0xADA00001+k for k,s in enumerate(slots))
      and mu.reg_read(UC_X86_REG_ESP)==esp0-4 and pushed==0x95a780 and mu.reg_read(UC_X86_REG_EBX)==0x1234 and mu.reg_read(UC_X86_REG_EDI)==0x5678)
print('adapters:',names,'slots writable/distinct',len(set(slots))==4,'resumes with original push',pushed==0x95a780)
print('ADAPTERS OK' if good else 'ADAPTERS FAILED')
