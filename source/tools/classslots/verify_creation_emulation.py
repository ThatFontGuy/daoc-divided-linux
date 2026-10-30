"""Optional verification (needs pefile and unicorn): emulate each new creation entry against the original Mauler
entry of its realm, with the four game calls replaced by recorders.
Usage: python verify_creation_emulation.py <pristine game.dll> <patched game.dll>"""
import sys,struct,pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
def load(path):
    pe=pefile.PE(path);return pe.get_memory_mapped_image(),pe.OPTIONAL_HEADER.ImageBase
FUNCS={0x5b440d:4,0x59f8d4:4,0x5afc27:0x28,0x515a30:0}
FIELDS=[-0x50,-0x4c,-0x48,-0x40,-0x3c,-0x38,-0x34,-0x20,-0x1c,-0x18]
def run_block(path,start,stop,regs):
    img,B=load(path);mu=Uc(UC_ARCH_X86,UC_MODE_32)
    mu.mem_map(B,(len(img)+0xfff)&~0xfff);mu.mem_write(B,img)
    mu.mem_map(0x100000,0x20000)
    ebp=0x118000;esp=ebp-0x200
    mu.reg_write(UC_X86_REG_EBP,ebp);mu.reg_write(UC_X86_REG_ESP,esp)
    mu.mem_write(ebp+8,struct.pack('<I',0xC0FFEE))
    for r,v in regs.items():mu.reg_write(r,v)
    log=[]
    def rd(a):return struct.unpack('<I',bytes(mu.mem_read(a,4)))[0]
    def hook(mu,addr,size,_):
        if addr in FUNCS:
            sp=mu.reg_read(UC_X86_REG_ESP);ret=rd(sp)
            args=[rd(sp+4+4*k) for k in range(FUNCS[addr]//4)]
            if addr==0x5b440d:log.append(('race',rd(args[0])))
            elif addr==0x5afc27:
                fields={d:rd(ebp+d) for d in FIELDS};fields['b44']=mu.mem_read(ebp-0x44,1)[0]
                fields['ratings']=bytes(mu.mem_read(ebp-0x10,3)).hex()
                log.append(('register',dict(container=hex(args[0]),classid=args[1],realm=args[2],count=args[9],fields=fields)))
            mu.reg_write(UC_X86_REG_ESP,sp+4+FUNCS[addr]);mu.reg_write(UC_X86_REG_EIP,ret)
    mu.hook_add(UC_HOOK_CODE,hook)
    mu.emu_start(start,stop,count=5000)
    return log,esp-mu.reg_read(UC_X86_REG_ESP),mu.reg_read(UC_X86_REG_EIP)==stop
pristine,patched=sys.argv[1],sys.argv[2]
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import patch_class_slots
_,layout=patch_class_slots.patch(open(pristine,'rb').read())
stub=layout['stubs']
cases={
 'Albion':  (0x5b0ad0,0x5b0b85,stub['Albion'],0x5b0b8b,{UC_X86_REG_EBX:1,UC_X86_REG_EDI:0x77,UC_X86_REG_ESI:0x117fd0}),
 'Midgard': (0x5b21e2,0x5b22a5,stub['Midgard'],0x5b22ad,{UC_X86_REG_EBX:0x55,UC_X86_REG_EDI:0x77,UC_X86_REG_ESI:0x99}),
 'Hibernia':(0x5b3470,0x5b352c,stub['Hibernia'],0x5b3534,{UC_X86_REG_EBX:0x66,UC_X86_REG_EDI:3,UC_X86_REG_ESI:0x117fd0}),
}
allok=True
for realm,(ms,me,ss,se,regs) in cases.items():
    mlog,mbal,_=run_block(pristine,ms,me,regs)
    slog,sbal,sret=run_block(patched,ss,se,regs)
    m=[x for x in mlog if x[0]=='register'][0][1]
    entries=[x[1] for x in slog if x[0]=='register']
    expected=[slot.class_id for slot in patch_class_slots.REALMS[realm]['slots']]
    print(f"   registered classes {[e['classid'] for e in entries]} (expected {expected})")
    allok&=[e['classid'] for e in entries]==expected and all(e['realm']==m['realm'] and e['count']==m['count'] for e in entries)
    s=entries[-1]
    same={k:(m['fields'][k]==s['fields'][k]) for k in m['fields'] if k not in (-0x4c,-0x34,-0x50,-0x38)}
    print(f"== {realm}: mauler class {m['classid']} realm {m['realm']} races {[v for k,v in mlog if k=='race']}")
    print(f"   new    class {s['classid']} realm {s['realm']} races {[v for k,v in slog if k=='race']} stack depth on return {sbal} returned {sret}")
    print('   fields equal to Mauler (except text):',all(same.values()),{k:v for k,v in same.items() if not v},'count',m['count'],s['count'],'resids',s['fields'][-0x50],s['fields'][-0x38])
    allok&=(sbal==(4 if realm=='Albion' else 0)) and sret and all(same.values()) and m['realm']==s['realm'] and m['count']==s['count']
print('ALL OK' if allok else 'FAILED')
