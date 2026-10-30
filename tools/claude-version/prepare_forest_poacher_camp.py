"""Read-only spawn/clearance probe. Does not modify the running database."""
import ctypes as C
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / 'runtime/data/opendaoc.sqlite3.db'
SERVER = ROOT / 'runtime/server'
V = C.c_float * 3
FILTER = (C.c_ushort * 2)(1, 0x10)  # walkable only, exclude disabled
def vec(p):
    return V(p[0]/32, p[2]/32, p[1]/32)

def main():
    dll = C.CDLL(str(SERVER / 'lib/Detour.dll'))
    dll.LoadNavMesh.argtypes = [C.c_char_p, C.POINTER(C.c_void_p)]
    dll.LoadNavMesh.restype = C.c_bool
    dll.CreateNavMeshQuery.argtypes = [C.c_void_p, C.POINTER(C.c_void_p)]
    dll.CreateNavMeshQuery.restype = C.c_bool
    dll.FindClosestPoint.argtypes = [C.c_void_p, C.POINTER(C.c_float), C.POINTER(C.c_float), C.POINTER(C.c_ushort), C.POINTER(C.c_float)]
    dll.FindClosestPoint.restype = C.c_uint
    dll.PathStraight.argtypes = [C.c_void_p, C.POINTER(C.c_float), C.POINTER(C.c_float), C.POINTER(C.c_float), C.POINTER(C.c_ushort), C.c_int, C.POINTER(C.c_int), C.POINTER(C.c_float), C.POINTER(C.c_ushort)]
    dll.PathStraight.restype = C.c_uint
    dll.HasLineOfSight.argtypes = [C.c_void_p, C.POINTER(C.c_float), C.POINTER(C.c_float), C.POINTER(C.c_float), C.POINTER(C.c_ushort), C.POINTER(C.c_bool), C.POINTER(C.c_float)]
    dll.HasLineOfSight.restype = C.c_uint
    mesh, query = C.c_void_p(), C.c_void_p()
    assert dll.LoadNavMesh(str(SERVER/'navmesh/zone208.nav').encode(), C.byref(mesh))
    assert dll.CreateNavMeshQuery(mesh, C.byref(query))
    def snap(p, horizontal=16):
        out = V()
        status = dll.FindClosestPoint(query, vec(p), vec((horizontal,horizontal,256)), FILTER, out)
        return (round(out[0]*32),round(out[2]*32),round(out[1]*32)) if status & 0x40000000 else None
    def path(a,b):
        count=C.c_int(); points=(C.c_float*768)(); flags=(C.c_ushort*256)()
        status=dll.PathStraight(query,vec(a),vec(b),vec((32,32,64)),FILTER,0,C.byref(count),points,flags)
        return bool(status & 0x40000000 and not status & 0x70 and count.value and math.dist(b,(points[(count.value-1)*3]*32,points[(count.value-1)*3+2]*32,points[(count.value-1)*3+1]*32)) < 48)
    def clear_segment(a,b):
        clear=C.c_bool(); out=V()
        status=dll.HasLineOfSight(query,vec(a),vec(b),vec((16,16,64)),FILTER,C.byref(clear),out)
        return bool(status & 0x40000000 and clear.value)
    center=(468047,522337,5078)
    with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute("SELECT Mob_ID,X,Y,Z,Level,Model FROM Mob WHERE Region=200 AND Name='forest poacher'").fetchall()
        for row in rows:
            if math.dist(center[:2],row[1:3]) < 2500:
                print('CURRENT', row, 'NAV', snap(row[1:4]), 'BROAD_NAV',snap(row[1:4],500))
    accepted=[]
    for dx in range(-1000,1001,250):
        for dy in range(-500,1501,250):
            p=snap((center[0]+dx,center[1]+dy,center[2]))
            if not p or abs(p[2]-center[2])>180: continue
            clear=True
            for i in range(32):
                angle=i*math.tau/32
                edge=(p[0]+260*math.cos(angle),p[1]+260*math.sin(angle),p[2])
                q=snap(edge)
                if not q or math.dist(edge[:2],q[:2])>12 or not clear_segment(p,q):
                    clear=False; break
            if clear and (not accepted or all(path(a,p) and path(p,a) for a in accepted)):
                if all(math.dist(a[:2],p[:2])>=650 for a in accepted):
                    accepted.append(p)
                    print('CANDIDATE',p,'LOCAL',(p[0]-450560,p[1]-483328,p[2]))
    assert len(accepted)>=3, 'Not enough connected, clearance-checked positions'
    dll.FreeNavMeshQuery.argtypes=[C.c_void_p]; dll.FreeNavMeshQuery(query)
    dll.FreeNavMesh.argtypes=[C.c_void_p]; dll.FreeNavMesh(mesh)

if __name__=='__main__': main()
