import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {WorldVisuals} from './visuals.js';
import {GLTFLoader} from './vendor/loaders/GLTFLoader.js';
import {loadParticles,applyNifMaterials,faceCamera} from './particles.js';

const $ = id => document.getElementById(id);
const token = new URLSearchParams(location.hash.slice(1)).get('token') || sessionStorage.getItem('worldEditorToken') || '';
sessionStorage.setItem('worldEditorToken', token);
history.replaceState(null, '', location.pathname);
const S = {config:null, data:null, pending:new Map(), selected:new Set(), undo:[], redo:[], comparison:null, loading:0,tool:'select',
  added:new Map(), mode:'worldView', table:null, rows:[], rowTotal:0, offset:0, query:{}, row:null, file:null};
const identity = e => `${e.table}:${e.key}`;
const clone = x => structuredClone(x);
let toastTimer;
function toast(message, error=false) {
  $('toast').textContent = message; $('toast').classList.remove('hidden'); $('toast').classList.toggle('error',error);
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),error?18000:8000);
}
async function api(path, data) {
  const r = await fetch('/api/'+path, {method:data?'POST':'GET', headers:{'X-Editor-Token':token,...(data?{'Content-Type':'application/json'}:{})},...(data?{body:JSON.stringify(data)}:{})});
  const result=await r.json(); if (!r.ok) throw Error(result.error || 'Request failed'); return result;
}
function guarded(fn) { return async (...args)=>{try {await fn(...args);} catch(e) {toast(e.message,true); console.error(e);}}; }
function busy(message) { $('busy').textContent=message; $('busy').classList.toggle('hidden',!message); }
function snapshot() {return [...S.pending].map(([k,v])=>[k,clone(v)]);}
function checkpoint() {S.undo.push(snapshot()); if(S.undo.length>100)S.undo.shift(); S.redo=[];}

// Each world table stores position/label in its own columns; the editor works with X/Y/Z/Heading/Name aliases.
const layer = table => S.config?.layers[table] || {};
const schema = table => S.config?.schema[table];
function aliases(table, v) {
  const l=layer(table);if(!l.x)return v;
  const sub=l.sub&&v[l.sub]!=null&&v[l.sub]!==''?(typeof v[l.sub]==='number'?`${l.sub} ${v[l.sub]}`:String(v[l.sub])):undefined;
  return {...v,X:v[l.x],Y:v[l.y],Z:v[l.z],Heading:l.heading?v[l.heading]:0,
    Name:l.name?v[l.name]:(l.title||table)+(sub?' · '+sub:''),Guild:l.name?sub:undefined};
}
function toColumns(table, values) {
  const l=layer(table),map={X:l.x,Y:l.y,Z:l.z,Heading:l.heading,Name:l.name},columns=schema(table)?.columns||{},result={};
  for(const [k,v] of Object.entries(values)){const column=k in map&&l.x?map[k]:k;if(column&&column in columns)result[column]=v;}
  return result;
}
function rawValues(e) {const c=S.pending.get(identity(e));return c?.op==='insert'?c.after:{...e.values,...(c?.after||{})};}
function pendingValues(e) {return aliases(e.table, rawValues(e));}
const isDeleted = e => S.pending.get(identity(e))?.op==='delete';
function stage(e, values) {
  const key=identity(e), old=S.pending.get(key), columns=toColumns(e.table, values);
  if(old?.op==='delete')return;
  if(old?.op==='insert'){const change=clone(old);Object.assign(change.after,columns);S.pending.set(key,change);return;}
  const change=old?clone(old):{op:'update',table:e.table,key:e.key,before:{},after:{}};
  for(const [field,value] of Object.entries(columns)) {
    if(field===schema(e.table).key||!(field in e.values))continue;
    if(!(field in change.before))change.before[field]=e.values[field];
    if(value===change.before[field]) {delete change.before[field];delete change.after[field];}
    else change.after[field]=value;
  }
  if(Object.keys(change.after).length)S.pending.set(key,change);else S.pending.delete(key);
}
function insideZone(table, v) {
  const z=S.data?.zone,l=layer(table);if(!z||!l.x)return false;
  if(table==='Door')return Math.floor((v.InternalID||0)/1000000)===z.ZoneID;
  if(l.region&&v[l.region]!==z.RegionID)return false;
  const ox=z.OffsetX*8192,oy=z.OffsetY*8192;return v[l.x]>=ox&&v[l.x]<ox+z.Width*8192&&v[l.y]>=oy&&v[l.y]<oy+z.Height*8192;
}
// New rows staged in this zone are drawn like loaded ones.
function syncAdded() {
  const before=[...S.added.keys()].join('|'),next=new Map();
  for(const [key,c] of S.pending){if(c.op!=='insert'||!insideZone(c.table,c.after))continue;const e=S.added.get(key)||{table:c.table,key:c.key,values:c.after,isNew:true};e.values=c.after;next.set(key,e);}
  S.added=next;return before!==[...next.keys()].join('|');
}
const allEntities = () => S.data?[...S.data.entities,...S.added.values()]:[];
const selectedEntities = () => allEntities().filter(e=>S.selected.has(identity(e)));
function changed() {
  $('dirty').textContent=`${S.pending.size} pending edit${S.pending.size===1?'':'s'}`;
  $('undo').disabled=!S.undo.length; $('redo').disabled=!S.redo.length;
  if(S.data&&syncAdded())makeMarkers();
  for(const key of [...S.selected])if(S.pending.get(key)?.op==='delete')S.selected.delete(key);
  updateMarkers(); updateWater(); renderEntities(); renderInspector(); renderZoneFields(); renderRows(); renderRow();
  if(S.mode==='itemsView'&&S.catalog){renderItemList();renderItemSide();
    const look=selectedLook();if(look&&look.key!==S.previewKey)previewItem(look).catch(e=>toast(e.message,true));}
  if(S.mode==='merchantsView'&&S.lists){renderLists();renderListView();}
}
function undo(redo=false) {
  const from=redo?S.redo:S.undo,to=redo?S.undo:S.redo;
  if(!from.length)return;to.push(snapshot());S.pending=new Map(from.pop());changed();
}
$('undo').onclick=()=>undo(); $('redo').onclick=()=>undo(true);
document.addEventListener('keydown',e=>{
  if(e.ctrlKey&&e.key.toLowerCase()==='s'&&S.mode==='filesView'){e.preventDefault();$('fileSave').click();return;}
  if(/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||$('dialog').open)return;
  if(e.ctrlKey&&e.key.toLowerCase()==='z'){e.preventDefault();undo(e.shiftKey);}
  if(e.ctrlKey&&e.key.toLowerCase()==='y'){e.preventDefault();undo(true);}
  if(S.mode==='itemsView'&&(e.key==='ArrowDown'||e.key==='ArrowUp')){
    const rows=[...document.querySelectorAll('#itemList .itemRow')],at=rows.findIndex(r=>r.classList.contains('selected'));
    const next=rows[Math.max(0,Math.min(rows.length-1,at+(e.key==='ArrowDown'?1:-1)))];if(next){e.preventDefault();next.click();next.scrollIntoView({block:'nearest'});}return;}
  if(S.mode!=='worldView')return;
  if(e.ctrlKey&&e.key.toLowerCase()==='d'){e.preventDefault();$('duplicate').click();return;}
  if(e.key==='Delete'){e.preventDefault();$('remove').click();}
  if(e.ctrlKey)return;
  if(e.key.toLowerCase()==='f')focus();
  if(e.key.toLowerCase()==='w'){e.preventDefault();setTool('move');}
  if(e.key.toLowerCase()==='e'){e.preventDefault();setTool('place');}
  if(e.key.toLowerCase()==='p'){e.preventDefault();$('toolPath').click();}
  if(e.key.toLowerCase()==='q'||e.key==='Escape')setTool('select');
});

// ---------- Modes ----------
function setMode(mode) {
  S.mode=mode;document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('hidden',v.id!==mode));
  if(mode==='filesView'&&!$('fileList').children.length)loadFiles().catch(e=>toast(e.message,true));
  if(mode==='looksView'&&!S.models)loadModels().catch(e=>toast(e.message,true));
  if(mode==='itemsView'&&!S.itemEnums)initItems().catch(e=>toast(e.message,true));
  if(mode==='merchantsView'&&!S.lists)loadLists().catch(e=>toast(e.message,true));
}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));

// ---------- 3D scene ----------
const viewport=$('viewport');
const renderer=new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0x91b2bd);
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;renderer.localClippingEnabled=true;
viewport.append(renderer.domElement);
const scene=new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xe5f4ff,0x66634b,2));
const sun=new THREE.DirectionalLight(0xffeed3,2.8);sun.position.set(-500,1000,400);scene.add(sun);
const camera=new THREE.PerspectiveCamera(50,1,0.5,80000);camera.position.set(800,1100,800);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.15;controls.maxPolarAngle=Math.PI*.495;
// The wheel is handled below (zoomAt) so it dives toward what is under the cursor, not a plane through the orbit target.
controls.enableZoom=false;
const world=new THREE.Group(), markerGroup=new THREE.Group(), extras=new THREE.Group();scene.add(world,markerGroup,extras);
let terrain=null, collision=null, markers=[], markerLookup=new Map(), pointer=new THREE.Vector2(), ray=new THREE.Raycaster();
const units=.025;
const visuals=new WorldVisuals(scene,camera,$('labels'),()=>S,local,pendingValues);
visuals.onSelect=(entity,multi)=>{const key=identity(entity);if(!multi)S.selected.clear();if(multi&&S.selected.has(key))S.selected.delete(key);else S.selected.add(key);changed();};
const rings=new THREE.Group();scene.add(rings);
function origin() {const z=S.data?.zone;return z?[z.OffsetX*8192,z.OffsetY*8192]:[0,0];}
function local(v) {const [x,y]=origin();return new THREE.Vector3((v.X-x)*units,v.Z*units,(v.Y-y)*units);}
function coordinates(p) {const [x,y]=origin();return {X:Math.round(p.x/units+x),Y:Math.round(p.z/units+y),Z:Math.round(p.y/units)};}
function dispose(group) {while(group.children.length){const o=group.children[0];group.remove(o);o.traverse(n=>{n.geometry?.dispose();if(n.material){(Array.isArray(n.material)?n.material:[n.material]).forEach(m=>m.dispose());}});}}
function buildTerrain(g) {
  if(!g.heights)return;
  const rows=g.heights,n=129,step=g.step*2,position=[],indices=[],colors=[],uv=[];
  const [ox,oy]=origin();const dx=(g.origin[0]-ox)*units,dz=(g.origin[1]-oy)*units;
  let low=Infinity,high=-Infinity;for(const row of rows)for(const h of row){low=Math.min(low,h);high=Math.max(high,h);}
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){
    const h=rows[y*2][x*2];position.push(dx+x*step*units,h*units,dz+y*step*units);uv.push(x/(n-1),1-y/(n-1));
    const f=(h-low)/Math.max(high-low,1);const c=new THREE.Color().setHSL(.40-f*.12,.19,.24+f*.13);colors.push(c.r,c.g,c.b);
    if(x<n-1&&y<n-1){const a=y*n+x;indices.push(a,a+n,a+1,a+1,a+n,a+n+1);}
  }
  const geom=new THREE.BufferGeometry();geom.setAttribute('position',new THREE.Float32BufferAttribute(position,3));geom.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));geom.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));geom.setIndex(indices);geom.computeVertexNormals();
  terrain=new THREE.Mesh(geom,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,side:THREE.DoubleSide}));world.add(terrain);
}
function buildCollision(data) {
  if(collision){world.remove(collision);collision.geometry.dispose();collision.material.dispose();}
  const [ox,oy]=origin();const p=new Float32Array(data.positions.length*3);
  data.positions.forEach((v,i)=>{p[i*3]=(v[0]-ox)*units;p[i*3+1]=v[1]*units;p[i*3+2]=(v[2]-oy)*units;});
  const geom=new THREE.BufferGeometry();geom.setAttribute('position',new THREE.BufferAttribute(p,3));geom.setIndex(data.indices);geom.computeVertexNormals();
  collision=new THREE.Mesh(geom,new THREE.MeshStandardMaterial({color:0x748e86,roughness:1,side:THREE.DoubleSide,flatShading:true}));
  world.add(collision);if(terrain)terrain.visible=false;applyViewOptions();
  $('geometryStatus').textContent='client collision geometry · buildings & floors';
  $('auditResult').textContent='Floor geometry is ready. Check visible placements to review NPC heights.';
}
const baseColors={Mob:0x67d2ac,WorldObject:0x85baff,Door:0xf0bc71,ZonePoint:0xc58cff,BindPoint:0x7be36f,Teleport:0x4fd9ff,
  JumpPoint:0xff9fdc,Keep:0xff7b5c,Relic:0xffe066,Area:0xb3b3b3,StartupLocation:0xffffff,PathPoints:0xffcf5a};
const defaultLayers=new Set(['Mob','WorldObject','Door','ZonePoint','BindPoint','Teleport','JumpPoint','Keep','Relic']);
function markerGeometry(table) {
  if(table==='Door')return new THREE.BoxGeometry(.65,.65,.25);
  if(table==='PathPoints')return new THREE.SphereGeometry(.22,6,4);
  if(table==='Mob'||table==='WorldObject')return new THREE.SphereGeometry(.35,8,6);
  return new THREE.OctahedronGeometry(.45);
}
function makeMarkers() {
  dispose(markerGroup);markers=[];markerLookup.clear();
  for(const e of allEntities()){
    const mesh=new THREE.Mesh(markerGeometry(e.table),new THREE.MeshBasicMaterial({color:baseColors[e.table]||0xffffff,depthTest:false,transparent:true,opacity:.9}));
    mesh.renderOrder=5;mesh.userData.entity=e;markerGroup.add(mesh);markers.push(mesh);markerLookup.set(identity(e),mesh);
  }
  updateMarkers();
}
let visibleCache=[];
function visibleEntities() {
  const search=$('search').value.toLowerCase();
  const enabled=new Set([...document.querySelectorAll('[data-kind]:checked')].map(e=>e.dataset.kind));
  return allEntities().filter(e=>enabled.has(e.table)&&!isDeleted(e)&&`${pendingValues(e).Name} ${e.values.Guild||''} ${e.key}`.toLowerCase().includes(search)&&(!$('townOnly').checked||(e.table==='Mob'&&Boolean(e.values.Guild))));
}
function updateMarkers() {
  const visibleList=visibleCache=visibleEntities(),visible=new Set(visibleList.map(identity));
  for(const mesh of markers){const e=mesh.userData.entity,v=pendingValues(e);mesh.rotation.z=Math.PI;mesh.rotation.y=-(v.Heading||0)/4096*Math.PI*2;
    const selected=S.selected.has(identity(e));mesh.material.color.setHex(selected?0xfff4b3:S.pending.has(identity(e))?0xeb8797:baseColors[e.table]||0xffffff);mesh.visible=visible.has(identity(e));}
  scaleMarkers();
  updateRings();updateExtras(visibleList);
}
function scaleMarkers(){for(const mesh of markers){const e=mesh.userData.entity,p=local(pendingValues(e)),distance=camera.position.distanceTo(p),size=Math.max(.6,distance*.0025)*(S.selected.has(identity(e))?1.4:1);mesh.scale.setScalar(size);mesh.position.copy(p);mesh.position.y+=(distance<180?2.4:.4)+size*.4;const hasModel=e.table==='Mob'&&Boolean(visuals.manifest?.figures[String((pendingValues(e).Model||0)&0x7fff)]?.file);mesh.material.opacity=distance<130&&visuals.show&&hasModel ? .25 : .9;}}
function updateRings(){dispose(rings);for(const e of selectedEntities()){const p=local(pendingValues(e)),group=new THREE.Group();group.position.copy(p);group.position.y+=.06;
  const ring=new THREE.Mesh(new THREE.RingGeometry(.85,1,36),new THREE.MeshBasicMaterial({color:0xffdb68,side:THREE.DoubleSide,depthTest:false}));ring.rotation.x=-Math.PI/2;ring.renderOrder=8;group.add(ring);
  if(layer(e.table).heading){const arrow=new THREE.ArrowHelper(new THREE.Vector3(0,0,1),new THREE.Vector3(0,.1,0),2,0xffdb68,.5,.4);group.add(arrow);}group.rotation.y=-(pendingValues(e).Heading||0)/4096*Math.PI*2;rings.add(group);}}
// Path waypoint lines and bind/area radii.
function updateExtras(list){
  dispose(extras);const paths=new Map();
  for(const e of list){
    const v=pendingValues(e),l=layer(e.table);
    if(e.table==='PathPoints'){if(!paths.has(v.PathID))paths.set(v.PathID,[]);paths.get(v.PathID).push(v);}
    if(l.radius&&v[l.radius]>0){const r=v[l.radius]*units,disc=new THREE.Mesh(new THREE.RingGeometry(Math.max(r-.25,0),r,48),new THREE.MeshBasicMaterial({color:baseColors[e.table],side:THREE.DoubleSide,transparent:true,opacity:.55,depthTest:false}));disc.rotation.x=-Math.PI/2;disc.position.copy(local(v));disc.position.y+=.3;disc.renderOrder=4;extras.add(disc);}
  }
  for(const [pathId,points] of paths){if(points.length<2)continue;points.sort((a,b)=>a.Step-b.Step);
    const path=pathEntity(pathId);if(path&&rawValues(path).PathType===3&&points.length>2)points.push(points[0]);
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p=>local(p).add(new THREE.Vector3(0,.5,0)))),new THREE.LineBasicMaterial({color:baseColors.PathPoints,depthTest:false,transparent:true}));line.renderOrder=4;extras.add(line);}
}
controls.addEventListener('change',scaleMarkers);
// Server water level (Zones.WaterLevel): below this height the server makes players swim. 0 means no water.
const water=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({color:0x3a8fc4,transparent:true,opacity:.42,depthWrite:false,side:THREE.DoubleSide}));
water.rotation.x=-Math.PI/2;water.renderOrder=2;water.visible=false;scene.add(water);
let pickWater=false;
function zoneEntity() {const z=S.data.zone;return {table:'Zones',key:z.ZoneID,values:Object.fromEntries(Object.keys(schema('Zones').columns).map(k=>[k,z[k]]))};}
function waterLevel() {return Number(rawValues(zoneEntity()).WaterLevel)||0;}
// What the server uses: the zone's own level, else its region's.
function effectiveWater() {const own=waterLevel();return own?{level:own,source:'zone'}:{level:Number(S.data.regionWater)||0,source:S.data.regionWater?'region':'none'};}
function updateWater() {
  const on=$('showWater').checked&&Boolean(S.data);$('waterTools').classList.toggle('hidden',!on);
  if(!on){water.visible=false;pickWater=false;$('waterPick').classList.remove('active');return;}
  const z=S.data.zone,{level,source}=effectiveWater(),w=z.Width*8192*units,h=z.Height*8192*units;
  water.scale.set(w,h,1);water.position.set(w/2,level*units,h/2);water.visible=level>0;
  if(document.activeElement!==$('waterLevel'))$('waterLevel').value=level;
  $('waterSource').textContent={zone:'zone',region:'from region',none:'no water'}[source];
  $('waterSource').title={zone:'This zone sets its own water level.',region:'This zone has no level of its own (0), so the server uses the region level. Changing it here gives the zone its own level.',none:'Neither the zone nor its region has a water level. The client still draws its own water, but the server never treats anyone as underwater here.'}[source];
}
function setWater(level) {
  if(!S.data)return;level=Math.round(THREE.MathUtils.clamp(level,0,65535));if(level===waterLevel())return;
  checkpoint();stage(zoneEntity(),{WaterLevel:level});changed();
}
$('showWater').onchange=updateWater;
$('waterLevel').onchange=()=>{const n=Number($('waterLevel').value);if(Number.isFinite(n))setWater(n);else updateWater();};
$('waterDown').onclick=e=>setWater(effectiveWater().level-(e.shiftKey?128:16));
$('waterUp').onclick=e=>setWater(effectiveWater().level+(e.shiftKey?128:16));
$('waterPick').onclick=()=>{pickWater=!pickWater;$('waterPick').classList.toggle('active',pickWater);if(pickWater)toast('Click the ground or a floor to set the water level to its height.');};
function home() {
  if(!S.data)return;const z=S.data.zone;const w=z.Width*8192*units,h=z.Height*8192*units;
  const ys=S.data.entities.map(e=>pendingValues(e).Z*units).filter(Number.isFinite).sort((a,b)=>a-b);const elevation=ys[Math.floor(ys.length/2)]||0;
  controls.target.set(w/2,elevation,h/2);camera.position.copy(controls.target).add(new THREE.Vector3(w*.2,Math.max(w,h)*.9,Math.max(w,h)*.8));controls.update();
}
function focus() {
  const chosen=selectedEntities();if(!chosen.length)return;
  const center=new THREE.Vector3();chosen.forEach(e=>center.add(local(pendingValues(e))));center.divideScalar(chosen.length);
  controls.target.copy(center).add(new THREE.Vector3(0,1,0));camera.position.copy(center).add(new THREE.Vector3(3,4,4.5));controls.update();
}
$('home').onclick=home;$('focus').onclick=focus;
new ResizeObserver(()=>{const w=viewport.clientWidth,h=viewport.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(viewport);
const frameClock=new THREE.Clock();let frameTime=0;
// Near/far follow the orbit distance so close-ups aren't clipped and depth precision stays usable.
function fitClipPlanes(){const d=camera.position.distanceTo(controls.target),near=THREE.MathUtils.clamp(d*.01,.02,.5),far=THREE.MathUtils.clamp(d*60,1500,80000);
  if(Math.abs(near-camera.near)>camera.near*.05||Math.abs(far-camera.far)>camera.far*.05){camera.near=near;camera.far=far;camera.updateProjectionMatrix();}}
// Drop to 1× resolution while frames are slow (high-DPI screens, close-ups filling the view with scenery).
const fullRatio=Math.min(devicePixelRatio,2);let frameAvg=1/60,ratioChanged=0;
function adaptResolution(dt,now){frameAvg+=(dt-frameAvg)*.05;if(fullRatio<=1||now-ratioChanged<4)return;const r=renderer.getPixelRatio();
  if(r>1&&frameAvg>1/38){renderer.setPixelRatio(1);ratioChanged=now;}else if(r===1&&frameAvg<1/57){renderer.setPixelRatio(fullRatio);ratioChanged=now;}
  if(renderer.getPixelRatio()!==r)renderer.setSize(viewport.clientWidth,viewport.clientHeight);}
renderer.setAnimationLoop(()=>{const dt=Math.min(frameClock.getDelta(),.05);if(S.mode!=='worldView')return;frameTime=performance.now()/1000;controls.update();fitClipPlanes();adaptResolution(dt,frameTime);visuals.tick(frameTime,dt,visibleCache,S.selected,controls.target.y+3);renderer.render(scene,camera);});
function pointerRay(e) {const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);}
function surfaceHit(e) {pointerRay(e);const hits=ray.intersectObject(collision||terrain||new THREE.Group());return $('cutaway').checked?hits.find(h=>h.point.y<=controls.target.y+3):hits[0];}
function entityHit(){return ray.intersectObjects([...markers.filter(m=>m.visible),...visuals.pickables])[0];}
function floorAt(x,y,reference) {
  if(!collision&&S.data?.geometry.heights){
    const g=S.data.geometry,gx=(x-g.origin[0])/g.step,gy=(y-g.origin[1])/g.step;
    if(gx<0||gy<0||gx>256||gy>256)return null;
    const ix=Math.min(255,Math.floor(gx)),iy=Math.min(255,Math.floor(gy)),fx=gx-ix,fy=gy-iy;
    const a=g.heights[iy],b=g.heights[iy+1];return (a[ix]*(1-fx)+a[ix+1]*fx)*(1-fy)+(b[ix]*(1-fx)+b[ix+1]*fx)*fy;
  }
  const mesh=collision||terrain;if(!mesh)return null;
  const p=local({X:x,Y:y,Z:reference});const r=new THREE.Raycaster(new THREE.Vector3(p.x,p.y+64*units,p.z),new THREE.Vector3(0,-1,0),0,50000);
  return r.intersectObject(mesh)[0]?.point.y/units??null;
}
// Wheel zoom about the point under the cursor (an NPC, else the floor), so it stays under the cursor while the
// camera closes in. Each notch covers 20% of the distance; stops 1.5 units from an NPC (whole body in view) or
// 0.4 units (~16 world units) from the floor.
function zoomAt(e) {
  e.preventDefault();if(!S.data)return;
  const delta=e.deltaY*(e.deltaMode===1?33:e.deltaMode===2?400:1);if(!delta)return;
  // An NPC under the cursor anchors at its chest, not at its floating marker.
  pointerRay(e);const entity=entityHit()?.object.userData.entity;
  let anchor=entity?local(pendingValues(entity)).add(new THREE.Vector3(0,1,0)):surfaceHit(e)?.point;
  if(!anchor){const plane=new THREE.Plane(new THREE.Vector3(0,1,0),-controls.target.y);anchor=ray.ray.intersectPlane(plane,new THREE.Vector3());}
  if(!anchor||anchor.distanceTo(camera.position)>30000)anchor=controls.target.clone();
  const reach=camera.position.distanceTo(anchor);let f=Math.pow(.8,-THREE.MathUtils.clamp(delta,-300,300)/100);
  if(f<1)f=Math.max(f,Math.min(1,(entity?1.5:.4)/reach));else if(camera.position.distanceTo(controls.target)*f>20000)return;
  if(Math.abs(f-1)<1e-4)return;
  camera.position.sub(anchor).multiplyScalar(f).add(anchor);controls.target.sub(anchor).multiplyScalar(f).add(anchor);scaleMarkers();
}
renderer.domElement.addEventListener('wheel',zoomAt,{passive:false});
let down=null,drag=null;
renderer.domElement.addEventListener('pointerdown',e=>{
  if(e.button!==0||!S.data)return;down={x:e.clientX,y:e.clientY};
  pointerRay(e);const hit=entityHit();
  if((e.shiftKey||S.tool==='move')&&hit&&S.data.zone.layoutMatches&&(collision||terrain)){
    const entity=hit.object.userData.entity;if(!S.selected.has(identity(entity)))S.selected=new Set([identity(entity)]);
    const surface=surfaceHit(e);if(!surface)return;
    checkpoint();drag={start:surface.point.clone(),values:new Map(selectedEntities().map(o=>[identity(o),pendingValues(o)]))};
    controls.enabled=false;renderer.domElement.setPointerCapture(e.pointerId);e.stopImmediatePropagation();e.preventDefault();changed();
  }
},true);
// Raycasting the collision mesh is costly; handle at most one pointer move per frame.
let moveEvent=null;
renderer.domElement.addEventListener('pointermove',e=>{if(!moveEvent)requestAnimationFrame(()=>{const m=moveEvent;moveEvent=null;pointerMove(m);});moveEvent=e;});
function pointerMove(e){
  const hit=surfaceHit(e);if(hit){const p=coordinates(hit.point);$('coords').textContent=`X ${p.X} · Y ${p.Y} · Z ${p.Z}`;}
  if(!drag){const hovered=entityHit()?.object.userData.entity;$('hoverCard').classList.toggle('hidden',!hovered);if(hovered){const v=pendingValues(hovered),r=viewport.getBoundingClientRect();$('hoverCard').textContent=(v.Name||'(unnamed)')+(v.Guild?' · '+v.Guild:'')+` · ${layer(hovered.table).label||hovered.table}`;$('hoverCard').style.left=Math.min(e.clientX-r.left+14,r.width-230)+'px';$('hoverCard').style.top=(e.clientY-r.top+18)+'px';}}
  if(!drag||!hit)return;
  const dx=(hit.point.x-drag.start.x)/units,dy=(hit.point.z-drag.start.z)/units;
  for(const entity of allEntities()){const start=drag.values.get(identity(entity));if(!start)continue;
    const X=Math.round(start.X+dx),Y=Math.round(start.Y+dy);
    const z=$('snap').checked?floorAt(X,Y,hit.point.y/units):start.Z;
    if(z===null)continue;stage(entity,{X,Y,Z:Math.round(z)});
  }
  updateMarkers();
}
renderer.domElement.addEventListener('pointerup',guarded(async e=>{
  if(drag){drag=null;controls.enabled=true;down=null;changed();return;}
  if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>5){down=null;return;}down=null;
  if(pickWater){pickWater=false;$('waterPick').classList.remove('active');const surface=surfaceHit(e);if(surface)setWater(surface.point.y/units);return;}
  pointerRay(e);const hit=entityHit();
  if(S.tool==='path'){
    const surface=surfaceHit(e);if(!surface)return;const p=coordinates(surface.point);
    await addWaypoint({X:p.X,Y:p.Y,Z:$('snap').checked?Math.round(floorAt(p.X,p.Y,p.Z)??p.Z):p.Z});return;
  }
  if(S.tool==='place'&&!hit){
    const source=selectedEntities()[0];if(!source)return toast('Select the NPC or object to copy first, then click the ground.',true);
    const surface=surfaceHit(e);if(!surface)return;const p=coordinates(surface.point);
    const Z=$('snap').checked?Math.round(floorAt(p.X,p.Y,p.Z)??p.Z):p.Z;
    const key=await duplicateRow(source.table,rawValues(source),toColumns(source.table,{X:p.X,Y:p.Y,Z}));if(key!==null){S.selected=new Set([`${source.table}:${key}`]);changed();}
    return;
  }
  if(hit){const key=identity(hit.object.userData.entity);if(e.ctrlKey){if(S.selected.has(key))S.selected.delete(key);else S.selected.add(key);}else S.selected=new Set([key]);}
  else if(!e.ctrlKey)S.selected.clear();changed();
}));
renderer.domElement.addEventListener('pointercancel',()=>{drag=null;down=null;controls.enabled=true;changed();});
renderer.domElement.addEventListener('pointerleave',()=>$('hoverCard').classList.add('hidden'));
renderer.domElement.addEventListener('dblclick',()=>{if(S.selected.size)focus();});

function renderZoneOptions() {
  const query=$('zoneSearch').value.toLowerCase(),current=$('zones').value;
  $('zones').replaceChildren();for(const z of S.config.zones){if(!`${z.ZoneID} ${z.Name}`.toLowerCase().includes(query))continue;const o=new Option(`${z.ZoneID} · ${z.Name}${z.layoutMatches?'':' ⚠'}`,z.ZoneID);$('zones').add(o);}
  if([...$('zones').options].some(o=>o.value===current))$('zones').value=current;
}
$('zoneSearch').oninput=renderZoneOptions;
async function loadZone(id) {
  const seq=++S.loading;busy('Loading zone terrain and world records…');
  try {
    const data=await api('zone?id='+Number(id));if(seq!==S.loading)return;
    S.data=data;S.added=new Map();S.paths=new Map();syncAdded();S.selected.clear();visuals.clear();dispose(world);terrain=collision=null;buildTerrain(data.geometry);makeMarkers();home();
    $('zones').value=String(data.zone.ZoneID);
    $('empty').classList.add('hidden');$('geometryStatus').textContent=data.geometry.heights?'client terrain · load buildings for exact placement':'no geometry loaded';
    $('layout').textContent=data.zone.layoutMatches?data.geometry.warning:'Client/server zone boundaries differ or the client lacks this zone. Dragging is disabled. Choose matching client data.';
    $('layout').classList.toggle('warning',!data.zone.layoutMatches);
    $('auditResult').textContent='Load buildings / floors to check placements against client geometry.';$('issues').replaceChildren();
    changed();
    loadVisuals(seq).catch(e=>toast(e.message,true));
    loadCollision(false).catch(e=>{ $('sceneDetails').textContent=e.message; });
  } finally {if(seq===S.loading)busy(null);}
}
$('zones').onchange=guarded(()=>loadZone($('zones').value));
$('loadMesh').onclick=guarded(()=>loadCollision(true));
async function loadCollision(showBusy=false){
  if(!S.data)return;const zid=S.data.zone.ZoneID;if(showBusy)busy('Reading collision geometry…');
    try{const mesh=await api('mesh?id='+zid);if(S.data.zone.ZoneID===zid){buildCollision(mesh);$('sceneDetails').textContent=mesh.warnings?.join('\n')||'Collision geometry loaded.';}}
  finally{if(showBusy)busy(null);}
}
async function loadVisuals(seq=S.loading){
  if(!S.data)return;const zid=S.data.zone.ZoneID;$('visualProgress').classList.remove('hidden');$('visualProgress').textContent='Preparing textured world…';
  try{
    const models=[...new Set([...S.pending.values()].filter(c=>c.table==='Mob'&&c.after.Model!==undefined).map(c=>c.after.Model))].slice(0,128);
    let job=await api('visual-start',{zone:zid,models});
    while(job.status==='running'){
      if(seq!==S.loading)return;$('visualProgress').textContent=job.message;
      await new Promise(resolve=>setTimeout(resolve,1000));job=await api('visual-status?id='+encodeURIComponent(job.id));
    }
    if(seq!==S.loading)return;if(job.status==='failed')throw Error(job.message);
    if(terrain&&job.scene.ground){
      const map=await new THREE.TextureLoader().loadAsync(job.base+job.scene.ground);map.colorSpace=THREE.SRGBColorSpace;map.anisotropy=renderer.capabilities.getMaxAnisotropy();
      if(seq!==S.loading){map.dispose();return;}terrain.material.map=map;terrain.material.vertexColors=false;terrain.material.color.setHex(0xffffff);terrain.material.needsUpdate=true;
    }
    const loaded=await visuals.load(job.scene,job.base,msg=>{if(seq===S.loading)$('visualProgress').textContent=msg;});
    if(!loaded||seq!==S.loading)return;applyViewOptions();
    $('geometryStatus').textContent=job.scene.summary;$('layout').textContent=S.data.zone.layoutMatches?'Client scenery loaded. Select a name or model to begin.':'Client/server zone bounds differ. Dragging is disabled.';
    $('sceneDetails').textContent=job.scene.summary+'\n'+job.scene.warnings.join('\n');
  }finally{if(seq===S.loading)$('visualProgress').classList.add('hidden');}
}
$('loadVisuals').onclick=guarded(()=>loadVisuals());
function applyViewOptions(){
  const textured=$('viewMode').value==='textured',hasScenery=visuals.scenery.children.length>0;
  visuals.options({show:textured,trees:$('showTrees').checked,names:$('showNames').checked,cutaway:$('cutaway').checked});
  if(collision)collision.visible=!textured||!hasScenery;
  if(terrain)terrain.visible=textured?(hasScenery||!collision):!collision;
  scaleMarkers();
}
for(const id of ['viewMode','showNames','showTrees','cutaway'])$(id).onchange=applyViewOptions;
function setTool(tool){S.tool=tool;for(const [id,t] of [['toolSelect','select'],['toolMove','move'],['toolPlace','place'],['toolPath','path']])$(id).classList.toggle('active',tool===t);renderer.domElement.style.cursor=tool==='move'?'move':tool==='place'?'copy':tool==='path'?'crosshair':'grab';if(tool!=='path')S.pathTarget=null;renderPathPanel();}
$('toolSelect').onclick=()=>setTool('select');$('toolMove').onclick=()=>setTool('move');$('toolPlace').onclick=()=>setTool('place');
$('toolPath').onclick=guarded(async()=>{
  const e=selectedEntities()[0],v=e&&rawValues(e);
  if(e?.table==='PathPoints')return startWaypoints(v.PathID,v.Step);
  if(e?.table==='Mob'&&v.PathID)return startWaypoints(v.PathID,null);
  if(e?.table==='Mob')return createPath(e);
  toast('Select an NPC (or one of its waypoints) first, then add waypoints.',true);
});

// ---------- Walk paths: Path row + ordered PathPoints rows, referenced by Mob.PathID ----------
const PATH_TYPES={1:'Walk once',2:'Back and forth',3:'Loop'};
S.paths=new Map();
async function pathInfo(pathId, refresh=false) {
  if(!refresh&&S.paths.has(pathId))return S.paths.get(pathId);
  const [path,points]=await Promise.all([api('rows?'+new URLSearchParams({table:'Path',column:'PathID',equals:pathId,limit:5})),
    api('rows?'+new URLSearchParams({table:'PathPoints',column:'PathID',equals:pathId,limit:500}))]);
  const info={row:path.rows[0]||null,points:points.rows};S.paths.set(pathId,info);return info;
}
function pathEntity(pathId) {
  const pending=[...S.pending.values()].find(c=>c.table==='Path'&&c.op==='insert'&&c.after.PathID===pathId);
  if(pending)return {table:'Path',key:pending.key,values:pending.after,isNew:true};
  const row=S.paths.get(pathId)?.row;return row?{table:'Path',key:row[schema('Path').key],values:row}:null;
}
// Every waypoint of a path, loaded or pending, with its current (pending) values.
function waypoints(pathId) {
  const found=new Map();
  for(const row of S.paths.get(pathId)?.points||[]){const e=rowEntity('PathPoints',row);found.set(identity(e),e);}
  for(const e of allEntities())if(e.table==='PathPoints')found.set(identity(e),e);
  for(const c of S.pending.values())if(c.table==='PathPoints'&&c.op==='insert'&&!found.has(`${c.table}:${c.key}`))found.set(`${c.table}:${c.key}`,{table:c.table,key:c.key,values:c.after,isNew:true});
  return [...found.values()].filter(e=>!isDeleted(e)&&rawValues(e).PathID===pathId).sort((a,b)=>rawValues(a).Step-rawValues(b).Step);
}
async function startWaypoints(pathId, after) {
  await pathInfo(pathId);const box=document.querySelector('[data-kind="PathPoints"]');if(box&&!box.checked){box.checked=true;updateMarkers();}
  setTool('path');S.pathTarget={pathId,after};renderPathPanel();
  toast(after===null?'Click the ground to add waypoints to the end of the path. Esc stops.':`Click the ground to insert waypoints after step ${after}. Esc stops.`);
}
async function createPath(mob) {
  if(!schema('Path')||!schema('PathPoints'))throw Error('This database has no Path tables.');
  const v=pendingValues(mob);let base=`${(v.Name||'NPC').slice(0,40)} walk`,pathId=base;
  for(let n=2;;n++){const taken=(await api('rows?'+new URLSearchParams({table:'Path',column:'PathID',equals:pathId,limit:1}))).total||[...S.pending.values()].some(c=>c.table==='Path'&&c.after.PathID===pathId);if(!taken)break;pathId=`${base} ${n}`;}
  checkpoint();
  await duplicateRow('Path',{...blankRow('Path'),PathID:pathId,PathType:3,RegionID:S.data.zone.RegionID},{},true);
  stage(mob,{PathID:pathId,...(rawValues(mob).Speed>0?{}:{Speed:200})});
  S.paths.set(pathId,{row:null,points:[]});
  await startWaypoints(pathId,null);
  await addWaypoint({X:v.X,Y:v.Y,Z:v.Z},true);
  toast(`Created path "${pathId}" starting at ${v.Name}. Click the ground to add more waypoints; Esc stops.`);
}
async function addWaypoint(position, keepCheckpoint=false) {
  const target=S.pathTarget;if(!target)return;const points=waypoints(target.pathId);
  const speed=Math.max(1,Math.round(Number($('pathSpeed')?.value)||200)),wait=Math.max(0,Math.round(Number($('pathWait')?.value)||0));
  if(!keepCheckpoint)checkpoint();
  let step;
  if(target.after===null)step=(points.length?Math.max(...points.map(p=>rawValues(p).Step)):0)+1;
  else{step=target.after+1;for(const p of points)if(rawValues(p).Step>=step)stage(p,{Step:rawValues(p).Step+1});target.after=step;}
  await duplicateRow('PathPoints',{...blankRow('PathPoints'),PathID:target.pathId,Step:step,...toColumns('PathPoints',position),MaxSpeed:speed,WaitTime:wait},{},true);
  changed();
}
function renderPathPanel() {
  const panel=$('pathPanel');if(!panel||!S.config)return;
  const selected=selectedEntities(),e=selected.length===1?selected[0]:null,v=e&&rawValues(e);
  const pathId=e?.table==='Mob'?v.PathID:e?.table==='PathPoints'?v.PathID:null;
  panel.classList.toggle('hidden',!(e&&(e.table==='Mob'||e.table==='PathPoints')&&schema('PathPoints')));panel.replaceChildren();
  if(panel.classList.contains('hidden'))return;
  const title=document.createElement('label');title.textContent='WALK PATH';panel.append(title);
  const add=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;panel.append(n);return n;};
  if(!pathId){add('p','This NPC stands at its spawn point. Give it a path to make it walk around.','muted');
    const b=add('button','⋯ Create walk path');b.onclick=guarded(()=>createPath(e));return;}
  if(!S.paths.has(pathId)){add('p','Loading path…','muted');pathInfo(pathId).then(renderPathPanel).catch(err=>toast(err.message,true));return;}
  const points=waypoints(pathId),path=pathEntity(pathId);
  add('div',`${pathId} · ${points.length} waypoint${points.length===1?'':'s'}`,'pathName');
  if(path){const select=add('select');select.setAttribute('aria-label','Path type');for(const [k,t] of Object.entries(PATH_TYPES))select.add(new Option(t,k));select.value=String(rawValues(path).PathType||1);
    select.onchange=()=>{checkpoint();stage(path,{PathType:Number(select.value)});changed();};}
  else add('p','No Path row exists for this ID; the server walks the waypoints once.','notice warning');
  // Applied to new waypoints: their MaxSpeed caps the NPC's walk speed; WaitTime pauses there (tenths of a second).
  const row=add('div',null,'row pathSettings');row.innerHTML='<label>New waypoint speed <input id="pathSpeed" type="number" min="1" max="2000"></label><label>Wait (0.1 s) <input id="pathWait" type="number" min="0" max="36000"></label>';
  $('pathSpeed').value=S.pathSpeed??200;$('pathWait').value=S.pathWait??0;
  $('pathSpeed').onchange=()=>{S.pathSpeed=$('pathSpeed').value;};$('pathWait').onchange=()=>{S.pathWait=$('pathWait').value;};
  const actions=add('div',null,'row');
  const go=document.createElement('button');go.className=S.tool==='path'?'active':'';
  go.textContent=S.tool==='path'?(S.pathTarget?.after==null?'Adding to end… (Esc)':`Inserting after ${S.pathTarget.after}… (Esc)`):(e.table==='PathPoints'?'Insert waypoints after this':'Add waypoints');
  go.onclick=guarded(()=>S.tool==='path'?setTool('select'):startWaypoints(pathId,e.table==='PathPoints'?v.Step:null));actions.append(go);
  if(e.table==='Mob'){const detach=document.createElement('button');detach.textContent='Stop walking';detach.title='Clear this NPC\'s PathID (the path rows stay)';detach.onclick=()=>{checkpoint();stage(e,{PathID:''});changed();};actions.append(detach);}
  if(e.table==='Mob'&&!(v.Speed>0))add('p','Speed is 0: the NPC will not move. Set Speed under All columns.','notice warning');
  if(e.table==='Mob'&&v.NPCTemplateID)add('p','Its NPC template may replace some values at spawn; the path is kept.','muted');
}
$('topView').onclick=()=>{camera.position.copy(controls.target).add(new THREE.Vector3(.01,Math.max(40,camera.position.distanceTo(controls.target)),.01));controls.update();};
$('isoView').onclick=()=>{const d=Math.max(40,camera.position.distanceTo(controls.target));camera.position.copy(controls.target).add(new THREE.Vector3(.4,.6,.7).normalize().multiplyScalar(d));controls.update();};
function quickEdit(makeValues){
  const selected=selectedEntities();if(!selected.length)return;
  checkpoint();for(const entity of selected){const edit=makeValues(pendingValues(entity));if(edit)stage(entity,edit);}changed();
}
function step(){return Math.max(1,Math.min(10000,Math.round(Number($('moveStep').value)||32)));}
function nudge(dx,dy,dz=0){quickEdit(v=>{const X=v.X+dx*step(),Y=v.Y+dy*step();let Z=v.Z+dz*step();if(!dz&&$('snap').checked){const h=floorAt(X,Y,Z);if(h!==null)Z=Math.round(h);}return {X,Y,Z};});}
$('nudgeNorth').onclick=()=>nudge(0,-1);$('nudgeSouth').onclick=()=>nudge(0,1);$('nudgeWest').onclick=()=>nudge(-1,0);$('nudgeEast').onclick=()=>nudge(1,0);
$('lower').onclick=()=>nudge(0,0,-1);$('raise').onclick=()=>nudge(0,0,1);
$('turnLeft').onclick=()=>quickEdit(v=>({Heading:((v.Heading||0)+512)%4096}));$('turnRight').onclick=()=>quickEdit(v=>({Heading:((v.Heading||0)+3584)%4096}));
$('snapSelected').onclick=()=>{if(!collision&&!terrain)return toast('Wait for zone geometry to load.',true);quickEdit(v=>{const h=floorAt(v.X,v.Y,v.Z);return h===null?null:{Z:Math.round(h)};});};
$('duplicate').onclick=guarded(async()=>{
  const chosen=selectedEntities();if(!chosen.length)return;const keys=[];
  for(const e of chosen){const v=pendingValues(e);const key=await duplicateRow(e.table,rawValues(e),toColumns(e.table,{X:v.X+64,Y:v.Y}),keys.length>0);if(key===null)return;keys.push(`${e.table}:${key}`);}
  S.selected=new Set(keys);changed();toast(`${keys.length} cop${keys.length===1?'y':'ies'} added 64 units east. Drag or nudge into place, then Review & save.`);
});
$('remove').onclick=()=>{const chosen=selectedEntities();if(!chosen.length)return;checkpoint();chosen.forEach(stageDelete);S.selected.clear();changed();toast(`${chosen.length} marked for deletion. Undo restores them; nothing is removed until Review & save.`);};
$('openData').onclick=guarded(async()=>{const e=selectedEntities()[0];if(!e)return;await openTable(e.table,{column:schema(e.table).key,equals:e.key});selectRow(e.table,e.key);setMode('dataView');});

// ---------- Row creation / deletion (shared by 3D and data views) ----------
const uuidPattern=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
async function newKey(table, suggested) {
  const info=schema(table);
  if(info.keyKind==='uuid')return crypto.randomUUID();
  if(info.keyKind==='int'){let {key}=await api('new-key?table='+encodeURIComponent(table));
    for(const c of S.pending.values())if(c.table===table&&c.op==='insert'&&c.key>=key)key=c.key+1;return key;}
  const typed=await askText(`New ${table} row`,`${table} rows are identified by ${info.key}. Enter a unique ${info.key} for the new row:`,suggested||'');
  if(!typed)return null;if(S.pending.has(`${table}:${typed}`))throw Error('A pending row already uses that key.');return typed;
}
// Browser prompt()/confirm() are unavailable in some embedded views; use the editor dialog instead.
function askText(title, message, value='') {
  return new Promise(resolve=>{
    const div=document.createElement('div'),p=document.createElement('p'),input=document.createElement('input');p.textContent=message;input.value=value;div.append(p,input);
    let done=false;$('dialog').addEventListener('close',()=>{if(!done)resolve(null);},{once:true});
    showDialog(title,div,async()=>{if(!input.value.trim())throw Error('Enter a value.');done=true;resolve(input.value.trim());},'OK');
    input.onkeydown=e=>{if(e.key==='Enter')$('confirm').click();};input.focus();input.select();
  });
}
function askConfirm(title, message, label) {
  return new Promise(resolve=>{let done=false;$('dialog').addEventListener('close',()=>{if(!done)resolve(false);},{once:true});showDialog(title,message,async()=>{done=true;resolve(true);},label);});
}
async function duplicateRow(table, values, overrides={}, keepCheckpoint=false, suggested=null) {
  const info=schema(table),key=await newKey(table,suggested??(values[info.key]?`${values[info.key]}_copy`:''));if(key===null)return null;
  const after={...clone(values),...overrides,[info.key]:key};
  // Unique row GUID columns (such as ItemTemplate_ID) need fresh values in the copy.
  for(const [column,value] of Object.entries(after))if(column!==info.key&&typeof value==='string'&&value&&(column===`${table}_ID`||/_ID$/i.test(column)&&uuidPattern.test(value)))after[column]=crypto.randomUUID();
  for(const column of Object.keys(after))if(!(column in info.columns))delete after[column];
  if(!keepCheckpoint)checkpoint();S.pending.set(`${table}:${key}`,{op:'insert',table,key,before:{},after});return key;
}
function blankRow(table) {
  const values={};for(const [column,rule] of Object.entries(schema(table).columns))values[column]=rule[0]==='text'?(rule[2]?null:''):(rule[rule.length-1]?null:0);
  if('LastTimeRowUpdated' in values)values.LastTimeRowUpdated=new Date().toISOString().slice(0,19).replace('T',' ');
  return values;
}
function stageDelete(e) {
  const key=identity(e),old=S.pending.get(key);
  if(old?.op==='insert'){S.pending.delete(key);return;}
  S.pending.set(key,{op:'delete',table:e.table,key:e.key,before:clone(e.values),after:{}});
}

// ---------- Entity list, inspector ----------
function renderLayerFilters() {
  const box=$('layerFilters');box.replaceChildren();
  for(const [table,l] of Object.entries(S.config.layers)){
    const label=document.createElement('label'),input=document.createElement('input'),swatch=document.createElement('i');
    input.type='checkbox';input.dataset.kind=table;input.checked=defaultLayers.has(table);input.onchange=()=>{updateMarkers();renderEntities();};
    swatch.style.background='#'+(baseColors[table]||0xffffff).toString(16).padStart(6,'0');label.append(input,swatch,' '+l.label);box.append(label);
  }
}
function renderEntities() {
  if(!S.config)return;
  const visible=visibleEntities();$('entityCount').textContent=`${visible.length} shown · ${S.selected.size} selected`;
  const list=$('entityList');list.replaceChildren();
  for(const e of visible.slice(0,1500)){
    const v=pendingValues(e),button=document.createElement('button');button.className='entity'+(S.selected.has(identity(e))?' selected':'');
    button.textContent=(e.isNew?'＋ ':S.pending.has(identity(e))?'● ':'')+(v.Name||'(unnamed)');
    const sub=document.createElement('span');sub.textContent=`${v.Guild||layer(e.table).label||e.table} ${v.Level!==undefined&&e.table==='Mob'?'· Level '+v.Level:''}`;button.append(sub);
    button.onclick=ev=>{if(!ev.ctrlKey)S.selected.clear();const key=identity(e);if(ev.ctrlKey&&S.selected.has(key))S.selected.delete(key);else S.selected.add(key);changed();if(ev.detail>=2)focus();};list.append(button);
  }
}
$('entityList').addEventListener('dblclick',focus);
$('search').oninput=()=>{updateMarkers();renderEntities();};
$('townOnly').onchange=()=>{updateMarkers();renderEntities();};
const labels={RespawnInterval:'Respawn (seconds)',AggroLevel:'Aggression',AggroRange:'Aggro range',RoamingRange:'Roaming range',FactionID:'Faction',Heading:'Facing (0–4095)',X:'X · east / west',Y:'Y · north / south',Z:'Z · height'};
function parseInput(input, rule, current) {
  const text=input.value;
  if(text===''&&rule[rule.length-1]&&(current===null||rule[0]!=='text'))return null;
  if(rule[0]==='text')return text;
  const n=Number(text);if(text.trim()===''||!Number.isFinite(n)||(rule[0]==='int'&&!Number.isInteger(n)))throw Error(`${input.getAttribute('aria-label')}: enter a ${rule[0]==='int'?'whole number':'number'}`);
  return n;
}
// Edit form for any row: the main columns first, the rest under "All columns".
function form(container, entity, basic, title='All columns', choices={}) {
  const advancedOpen=container.querySelector('details')?.open;container.replaceChildren();
  const info=schema(entity.table);if(!info)return;
  const values=rawValues(entity),advanced=document.createElement('details');advanced.className='advancedFields';advanced.open=Boolean(advancedOpen);
  const summary=document.createElement('summary');summary.textContent=`${title} (${Object.keys(info.columns).length})`;advanced.append(summary);
  const order=Object.keys(info.columns).sort((a,b)=>{const ai=basic.indexOf(a),bi=basic.indexOf(b);return (ai<0?100:ai)-(bi<0?100:bi);});
  for(const name of order) {
    const rule=info.columns[name],div=document.createElement('div');div.className='field';const label=document.createElement('label');label.textContent=labels[name]||name;
    const current=values[name],long=rule[0]==='text'&&typeof current==='string'&&(current.length>40||current.includes('\n'));
    const options=choices[name];
    const input=document.createElement(options?'select':long?'textarea':'input');
    if(options){for(const [value,text] of Object.entries(options))input.add(new Option(`${text} (${value})`,value));
      if(current!==null&&current!==undefined&&!(String(current) in options))input.add(new Option(String(current),String(current)));}
    input.value=current??'';if(!long&&!options)input.type=rule[0]==='text'?'text':'number';
    if(current===null)input.placeholder='(empty)';
    input.setAttribute('aria-label',name);input.title=`${name} · ${rule[0]}${rule[0]==='int'?` ${rule[1]}…${rule[2]}`:''}${rule[rule.length-1]?' · may be empty':''}`;
    if(options){}else if(rule[0]==='text')input.maxLength=Math.min(rule[1],1000000);else{input.step=rule[0]==='int'?'1':'any';if(rule[0]==='int'){input.min=rule[1];input.max=rule[2];}}
    const isKey=name===info.key&&!entity.isNew&&S.pending.get(identity(entity))?.op!=='insert';
    if(isKey||name==='LastTimeRowUpdated'&&!entity.isNew)input.disabled=true;
    if(long){div.classList.add('long');}
    input.onchange=guarded(async()=>{if(!input.reportValidity())return;const value=parseInput(input,rule,current);checkpoint();
      const c=S.pending.get(identity(entity));
      if(c?.op==='insert'){
        const next=clone(c);next.after[name]=value;
        if(name===info.key){if(value===null||value===''||S.pending.has(`${entity.table}:${value}`))throw Error('Choose a key no other pending row uses.');
          S.pending.delete(identity(entity));next.key=value;if(S.row&&identity(S.row)===identity(entity))S.row={...S.row,key:value};
          if(S.selected.delete(identity(entity)))S.selected.add(`${entity.table}:${value}`);}
        S.pending.set(`${entity.table}:${next.key}`,next);
      }else stage(entity,{[name]:value});changed();});
    div.append(label,input);(basic.includes(name)?container:advanced).append(div);
  }
  container.append(advanced);
}
function basicColumns(table) {
  const l=layer(table);return [schema(table)?.key,l.name,l.x,l.y,l.z,l.heading,l.radius,...(table==='Mob'?['Guild','Level','Model','Size','Realm','NPCTemplateID','ItemsListTemplateID','EquipmentTemplateID','RespawnInterval','RoamingRange','PathID']:[]),...(table==='WorldObject'||table==='Door'?['Model','Realm','Locked']:[])].filter(Boolean);
}
// Links from a row to rows in other tables that it refers to (or that refer to it).
const RELATED={
  Mob:[['NPC template','NpcTemplate','TemplateId','NPCTemplateID'],['Merchant items','MerchantItem','ItemListID','ItemsListTemplateID'],['Equipment','NPCEquipment','TemplateID','EquipmentTemplateID'],['Loot tables','MobXLootTemplate','MobName','Name'],['Path waypoints','PathPoints','PathID','PathID'],['Ambient lines','MobXAmbientBehaviour','Source','Name'],['Faction','Faction','ID','FactionID'],['Spawns with this name','Mob','Name','Name']],
  NpcTemplate:[['Spawns using it','Mob','NPCTemplateID','TemplateId'],['Equipment','NPCEquipment','TemplateID','EquipmentTemplateID'],['Merchant items','MerchantItem','ItemListID','ItemsListTemplateID']],
  MerchantItem:[['Item','ItemTemplate','Id_nb','ItemTemplateID'],['Same merchant list','MerchantItem','ItemListID','ItemListID'],['Merchants selling it','Mob','ItemsListTemplateID','ItemListID']],
  ItemTemplate:[['Sold on merchant lists','MerchantItem','ItemTemplateID','Id_nb'],['In loot tables','LootTemplate','ItemTemplateID','Id_nb'],['Charge spell','Spell','SpellID','SpellID'],['Proc spell','Spell','SpellID','ProcSpellID'],['Crafting recipe','CraftedItem','Id_nb','Id_nb'],['Used as ingredient','CraftedXItem','IngredientId_nb','Id_nb'],['Starter equipment','StarterEquipment','TemplateID','Id_nb']],
  LootTemplate:[['Item','ItemTemplate','Id_nb','ItemTemplateID'],['Same loot table','LootTemplate','TemplateName','TemplateName'],['Mobs using it','MobXLootTemplate','LootTemplateName','TemplateName']],
  MobXLootTemplate:[['Loot table items','LootTemplate','TemplateName','LootTemplateName'],['Spawns with this name','Mob','Name','MobName']],
  NPCEquipment:[['Same equipment set','NPCEquipment','TemplateID','TemplateID'],['Spawns wearing it','Mob','EquipmentTemplateID','TemplateID']],
  Spell:[['In spell lines','LineXSpell','SpellID','SpellID'],['Sub spell','Spell','SpellID','SubSpellID'],['Items casting it','ItemTemplate','SpellID','SpellID']],
  LineXSpell:[['Spell','Spell','SpellID','SpellID'],['Spell line','SpellLine','KeyName','LineName'],['Same line','LineXSpell','LineName','LineName']],
  SpellLine:[['Spells in line','LineXSpell','LineName','KeyName']],
  Path:[['Waypoints','PathPoints','PathID','PathID'],['Spawns walking it','Mob','PathID','PathID']],
  PathPoints:[['Path','Path','PathID','PathID'],['All waypoints','PathPoints','PathID','PathID'],['Spawns walking it','Mob','PathID','PathID']],
  CraftedItem:[['Ingredients','CraftedXItem','CraftedItemId_nb','Id_nb'],['Item','ItemTemplate','Id_nb','Id_nb']],
  CraftedXItem:[['Ingredient item','ItemTemplate','Id_nb','IngredientId_nb'],['Recipe','CraftedItem','Id_nb','CraftedItemId_nb']],
  Faction:[['Linked factions','LinkedFaction','FactionID','ID'],['Spawns in faction','Mob','FactionID','ID']],
  StarterEquipment:[['Item','ItemTemplate','Id_nb','TemplateID']],
  LootOTD:[['Item','ItemTemplate','Id_nb','ItemTemplateID']],
};
function renderRelated(container, entity) {
  container.replaceChildren();const values=rawValues(entity),links=(RELATED[entity.table]||[]).filter(([,table,,from])=>schema(table)&&values[from]!==null&&values[from]!==undefined&&values[from]!==''&&values[from]!==0);
  if(!links.length)return;const label=document.createElement('label');label.textContent='RELATED DATA';container.append(label);
  const row=document.createElement('div');row.className='chips';
  for(const [text,table,column,from] of links){const b=document.createElement('button');b.textContent=text;b.title=`${table} where ${column} = ${values[from]}`;
    b.onclick=guarded(async()=>{await openTable(table,{column,equals:String(values[from])});setMode('dataView');if(S.rows.length===1)selectRow(table,S.rows[0][schema(table).key]);});row.append(b);}
  container.append(row);
}
function renderInspector() {
  if(!S.config)return;
  const selected=selectedEntities();
  $('selectionActions').classList.toggle('hidden',!selected.length);
  renderPathPanel();
  if(selected.length!==1){$('selectedName').textContent=selected.length?`${selected.length} selected`:'Nothing selected';$('selectedType').textContent=selected.length?'Shift+drag moves this group.':'Choose an NPC or world object.';$('inspector').replaceChildren();$('related').replaceChildren();return;}
  const e=selected[0];$('selectedName').textContent=pendingValues(e).Name||'(unnamed)';$('selectedType').textContent=(e.isNew?'NEW · ':'')+(e.values.Guild||layer(e.table).label||e.table);$('selectedType').title=`${e.table} · ${e.key}`;form($('inspector'),e,basicColumns(e.table));renderRelated($('related'),e);
  const notes=[],v=rawValues(e);
  if(v.NPCTemplateID&&e.table==='Mob')notes.push(`NPC template ${v.NPCTemplateID} may override level or appearance.`);
  if(v.PathID&&e.table==='Mob')notes.push(`Route ${v.PathID}: moving this spawn does not move its waypoints (turn on the Path waypoints layer to edit them).`);
  if(v.ClassType&&e.table==='Mob'&&!['DOL.GS.GameNPC','DOL.GS.GameObject'].includes(v.ClassType))notes.push(`Script: ${v.ClassType}. Scripted behavior may override edits.`);
  if(notes.length){const warning=document.createElement('p');warning.className='notice warning';warning.textContent=notes.join(' ');$('inspector').prepend(warning);}
}
function renderZoneFields() {
  if(!S.data||!S.config)return;const z=S.data.zone;form($('zoneFields'),zoneEntity(),Object.keys(S.config.fields.Zones),'Layout and other columns');
  $('zoneBounds').textContent=`Region ${z.RegionID}\nOrigin ${z.OffsetX*8192}, ${z.OffsetY*8192}\nExtent ${z.Width*8192} × ${z.Height*8192}\n${z.layoutMatches?'Client bounds match server':'CLIENT / SERVER BOUNDS DIFFER'}`;
}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('#worldView .tab').forEach(x=>x.classList.toggle('hidden',x.id!==b.dataset.tab));});
$('audit').onclick=()=>{
  if(!collision)return toast('Load buildings / floors first.',true);
  const issues=[];
  for(const e of visibleEntities()){
    const v=pendingValues(e);const h=floorAt(v.X,v.Y,v.Z);if(h===null||Math.abs(h-v.Z)>64)issues.push({e,text:h===null?'No floor found':`${Math.round(v.Z-h)} units from floor`});
  }
  $('auditResult').textContent=`${issues.length} positions need review. Floor check only; navigation, roaming, and scripted encounters are not validated.`;
  $('issues').replaceChildren();for(const {e,text} of issues.slice(0,100)){const b=document.createElement('button');b.textContent=`${pendingValues(e).Name}: ${text}`;b.onclick=()=>{S.selected=new Set([identity(e)]);changed();focus();};$('issues').append(b);}
};

// ---------- Game data view ----------
function renderTables() {
  const query=$('tableSearch').value.toLowerCase(),list=$('tableList');list.replaceChildren();
  for(const [group,tables] of Object.entries(S.config.groups)){
    const shown=tables.filter(t=>t.toLowerCase().includes(query)||group.toLowerCase().includes(query));if(!shown.length)continue;
    const h=document.createElement('div');h.className='groupName';h.textContent=group;list.append(h);
    for(const t of shown){const b=document.createElement('button');b.className='entity'+(t===S.table?' selected':'');b.textContent=t;
      const pending=[...S.pending.values()].filter(c=>c.table===t).length;if(pending){const span=document.createElement('span');span.textContent=`${pending} pending`;b.append(span);}
      b.onclick=guarded(()=>openTable(t));list.append(b);}
  }
}
$('tableSearch').oninput=renderTables;
// Columns that best identify a row come first in the results grid.
const preferred=['Name','KeyName','Id_nb','TemplateName','ItemListID','TemplateID','MobName','LootTemplateName','LineName','TeleportID','PathID','Key','Value','Description','Guild','Level','Model','Region','RegionID','X','Y','Z','SpellID','ItemTemplateID','Type','Chance','Count','Step'];
function gridColumns(table) {const info=schema(table),cols=Object.keys(info.columns),ordered=[info.key,...preferred.filter(c=>c!==info.key&&cols.includes(c))];for(const c of cols)if(ordered.length<9&&!ordered.includes(c)&&c!=='LastTimeRowUpdated')ordered.push(c);return ordered.slice(0,9);}
async function openTable(table, query={}) {
  if(!schema(table))throw Error(`${table} is not available in this database`);
  if(S.table!==table)S.row=null;S.table=table;S.query={q:query.q||'',column:query.column||'',equals:query.equals??''};S.offset=0;
  $('dataSearch').value=S.query.q;$('dataEquals').value=S.query.equals;
  $('dataColumn').replaceChildren(new Option('any column',''),...Object.keys(schema(table).columns).map(c=>new Option(c,c)));$('dataColumn').value=S.query.column;
  await searchRows();renderTables();
}
async function searchRows() {
  if(!S.table)return;const {q,column,equals}=S.query;
  const params=new URLSearchParams({table:S.table,q,offset:S.offset,limit:100});if(column){params.set('column',column);params.set('equals',equals);}
  const result=await api('rows?'+params);S.rows=result.rows;S.rowTotal=result.total;renderRows();renderRow();
}
function rowEntity(table,row){return {table,key:row[schema(table).key],values:row};}
function dataEntities() {
  if(!S.table)return [];const key=schema(S.table).key;
  const added=[...S.pending.values()].filter(c=>c.table===S.table&&c.op==='insert').map(c=>({table:c.table,key:c.key,values:c.after,isNew:true}));
  return [...added,...S.rows.map(r=>rowEntity(S.table,r))].filter((e,i,all)=>all.findIndex(o=>String(o.key)===String(e.key))===i&&e.key!==undefined&&(e.isNew||e.values[key]!==undefined));
}
function renderRows() {
  if(!S.table||!S.config)return;const cols=gridColumns(S.table);
  $('dataTitle').textContent=S.table;
  $('dataCount').textContent=S.rowTotal?`Rows ${S.offset+1}–${S.offset+S.rows.length} of ${S.rowTotal.toLocaleString()}`:'No matching rows';
  $('dataPrev').disabled=S.offset===0;$('dataNext').disabled=S.offset+S.rows.length>=S.rowTotal;
  const head=document.createElement('tr');for(const c of cols){const th=document.createElement('th');th.textContent=c;head.append(th);}$('dataHead').replaceChildren(head);
  const body=$('dataBody');body.replaceChildren();
  for(const e of dataEntities()){
    const tr=document.createElement('tr'),c=S.pending.get(identity(e)),v=rawValues(e);
    tr.className=(S.row&&String(S.row.key)===String(e.key)?'selected ':'')+(c?.op==='insert'?'new':c?.op==='delete'?'deleted':c?'edited':'');
    for(const col of cols){const td=document.createElement('td');const value=v[col];td.textContent=value===null||value===undefined?'':String(value).slice(0,80);td.title=value===null?'(empty)':String(value);tr.append(td);}
    tr.onclick=()=>selectRow(e.table,e.key);body.append(tr);
  }
}
function selectRow(table,key){const e=dataEntities().find(o=>o.table===table&&String(o.key)===String(key));S.row=e||null;renderRows();renderRow();}
function renderRow() {
  if(!S.config)return;
  if(S.row){const fresh=dataEntities().find(o=>String(o.key)===String(S.row.key)&&o.table===S.row.table);S.row=fresh||(S.pending.has(identity(S.row))?S.row:null);}
  const e=S.row;$('rowActions').classList.toggle('hidden',!e);
  if(!e){$('rowName').textContent='Nothing selected';$('rowType').textContent=S.table?'Choose a row, or add a new one.':'';$('rowForm').replaceChildren();$('rowRelated').replaceChildren();return;}
  const c=S.pending.get(identity(e)),v=aliases(e.table,rawValues(e));
  const label=gridColumns(e.table).slice(1).map(c=>v[c]).find(x=>typeof x==='string'&&x);
  $('rowName').textContent=v.Name||label||String(e.key);
  $('rowType').textContent=`${e.table} · ${schema(e.table).key} ${e.key}${c?.op==='insert'?' · NEW (pending)':c?.op==='delete'?' · WILL BE DELETED':c?' · edited':''}`;
  $('rowDelete').textContent=c?.op==='delete'?'↺ Keep row':'✕ Delete';$('rowWorld').classList.toggle('hidden',!layer(e.table).x);
  if(c?.op==='delete'){$('rowForm').replaceChildren();$('rowRelated').replaceChildren();return;}
  form($('rowForm'),e,[schema(e.table).key,...gridColumns(e.table)]);renderRelated($('rowRelated'),e);
  $('rowForm').querySelector('details').open=true;
}
$('dataGo').onclick=guarded(async()=>{S.query={q:$('dataSearch').value.trim(),column:$('dataColumn').value,equals:$('dataEquals').value};S.offset=0;await searchRows();});
$('dataSearch').onkeydown=$('dataEquals').onkeydown=e=>{if(e.key==='Enter')$('dataGo').click();};
$('dataClear').onclick=guarded(async()=>{$('dataSearch').value='';$('dataEquals').value='';$('dataColumn').value='';$('dataGo').click();});
$('dataPrev').onclick=guarded(async()=>{S.offset=Math.max(0,S.offset-100);await searchRows();});
$('dataNext').onclick=guarded(async()=>{S.offset+=100;await searchRows();});
$('dataNew').onclick=guarded(async()=>{if(!S.table)return;const key=await duplicateRow(S.table,blankRow(S.table));if(key!==null){changed();selectRow(S.table,key);}});
$('rowDuplicate').onclick=guarded(async()=>{const e=S.row;if(!e)return;const key=await duplicateRow(e.table,rawValues(e));if(key!==null){changed();selectRow(e.table,key);toast('Copy added as a pending new row. Change what you need, then Review & save.');}});
$('rowDelete').onclick=()=>{const e=S.row;if(!e)return;checkpoint();const c=S.pending.get(identity(e));if(c?.op==='delete')S.pending.delete(identity(e));else stageDelete(e);changed();};
$('rowWorld').onclick=guarded(async()=>{const e=S.row;if(!e)return;await showInWorld(e.table,rawValues(e),e.key);});
async function showInWorld(table, v, key) {
  const l=layer(table);let zone;
  if(table==='Door')zone=S.config.zones.find(z=>z.ZoneID===Math.floor(v.InternalID/1000000));
  else zone=S.config.zones.find(z=>(!l.region||z.RegionID===v[l.region])&&v[l.x]>=z.OffsetX*8192&&v[l.x]<(z.OffsetX+z.Width)*8192&&v[l.y]>=z.OffsetY*8192&&v[l.y]<(z.OffsetY+z.Height)*8192);
  if(!zone)throw Error('No server zone contains this position.');
  setMode('worldView');if(S.data?.zone.ZoneID!==zone.ZoneID)await loadZone(zone.ZoneID);
  const box=document.querySelector(`[data-kind="${table}"]`);if(box&&!box.checked){box.checked=true;}
  S.selected=new Set([`${table}:${key}`]);changed();focus();
}

// ---------- Server files view ----------
async function loadFiles() {
  const files=await api('files');S.files=files;renderFiles();
}
function renderFiles() {
  const query=$('fileSearch').value.toLowerCase(),list=$('fileList');list.replaceChildren();let folder=null;
  for(const f of S.files||[]){if(!f.path.toLowerCase().includes(query))continue;const dir=f.path.includes('/')?f.path.slice(0,f.path.lastIndexOf('/')):'(runtime)';
    if(dir!==folder){folder=dir;const h=document.createElement('div');h.className='groupName';h.textContent=dir;list.append(h);}
    const b=document.createElement('button');b.className='entity'+(S.file?.path===f.path?' selected':'');b.textContent=f.path.split('/').pop();
    const s=document.createElement('span');s.textContent=`${(f.size/1024).toFixed(1)} KB`;b.append(s);b.onclick=guarded(()=>openFile(f.path));list.append(b);}
}
$('fileSearch').oninput=renderFiles;
const fileDirty=()=>S.file&&$('fileText').value!==S.file.text;
async function openFile(path) {
  if(fileDirty()&&!await askConfirm('Unsaved file changes',`Discard unsaved changes to ${S.file.path}?`,'Discard changes'))return;
  const file=await api('file?path='+encodeURIComponent(path));S.file=file;
  $('filePath').textContent=path;$('fileText').value=file.text;$('fileText').disabled=false;
  $('fileBackups').replaceChildren(new Option(file.backups.length?`Earlier versions (${file.backups.length})…`:'No earlier versions',''),...file.backups.map(b=>new Option(b,b)));
  fileState();renderFiles();
}
function fileState(){const dirty=fileDirty();$('fileSave').disabled=!dirty;$('fileState').textContent=S.file?(dirty?'● unsaved changes':`${S.file.encoding}`):'';}
$('fileText').oninput=fileState;
$('fileText').onkeydown=e=>{if(e.key==='Tab'){e.preventDefault();const t=e.target,s=t.selectionStart;t.setRangeText('  ',s,t.selectionEnd,'end');fileState();}};
$('fileReload').onclick=guarded(async()=>{if(S.file)await openFile(S.file.path);});
$('fileSave').onclick=guarded(async()=>{
  if(!fileDirty())return;const path=S.file.path;busy('Saving file and backup…');
  try{const r=await api('file-save',{path,text:$('fileText').value,sha:S.file.sha});S.file=null;await openFile(path);toast(r.message+'\nBackup: '+r.backup);}
  finally{busy(null);}
});
$('fileBackups').onchange=guarded(async()=>{
  const id=$('fileBackups').value;if(!id||!S.file)return;const {text}=await api(`file-backup?id=${encodeURIComponent(id)}&path=${encodeURIComponent(S.file.path)}`);
  $('fileText').value=text;fileState();$('fileBackups').value='';toast(`Loaded the version saved before ${id} into the editor. Save file to restore it.`);
});

// ---------- Custom looks: private client models with the user's own skins ----------
async function loadModels() {
  $('modelList').textContent='Reading the client model catalog…';
  const [models,looks]=await Promise.all([api('models'),api('looks')]);S.models=models;S.looks=looks;renderModels();renderLooks();
}
function renderModels() {
  const query=$('modelSearch').value.toLowerCase(),people=$('modelPeople').checked,list=$('modelList');list.replaceChildren();
  const shown=(S.models||[]).filter(m=>m.parts.length&&`${m.id} ${m.name} ${m.nif||''}`.toLowerCase().includes(query)&&(!people||m.parts.length>=5));
  for(const m of shown.slice(0,400)){const b=document.createElement('button');b.className='entity'+(S.look?.id===m.id?' selected':'');b.textContent=`${m.private?'★ ':''}${m.name}`;
    const s=document.createElement('span');s.textContent=`Model ${m.id} · ${m.nif||'?'} · ${m.parts.length} texture${m.parts.length===1?'':'s'}`;b.append(s);b.onclick=guarded(()=>chooseModel(m));list.append(b);}
  if(shown.length>400){const p=document.createElement('p');p.className='muted';p.textContent=`${shown.length-400} more; narrow the search.`;list.append(p);}
}
$('modelSearch').oninput=renderModels;$('modelPeople').onchange=renderModels;
async function chooseModel(model) {
  S.look={id:model.id,model,images:{},templates:null};renderModels();
  $('lookTitle').textContent=`${model.name} · model ${model.id}`;$('lookParts').textContent='Reading textures…';
  $('nifBox').classList.remove('hidden');$('lookInstall').classList.remove('hidden');$('lookNif').value='';
  if(!$('lookName').value)$('lookName').placeholder=`Name of the look (based on ${model.name})`;
  S.look.templates=await api('model-template?model='+model.id);if(S.look?.id===model.id)renderLookParts();
}
function readFile(file) {return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.readAsDataURL(file);});}
function renderLookParts() {
  const box=$('lookParts');box.replaceChildren();const look=S.look;
  for(const part of look.model.parts){
    const t=look.templates?.[part.col]||{},card=document.createElement('div');card.className='lookPart';
    const h=document.createElement('strong');h.textContent=part.part;const info=document.createElement('span');info.className='muted';info.textContent=` ${part.file}${t.size?` · ${t.size[0]}×${t.size[1]}`:''}`;
    const images=document.createElement('div');images.className='row';
    const stock=document.createElement('img');stock.alt=`Stock ${part.part} texture`;if(t.png)stock.src=t.png;images.append(stock);
    const arrow=document.createElement('span');arrow.textContent='→';images.append(arrow);
    const mine=document.createElement('img');mine.alt=`Your ${part.part} texture`;if(look.images[part.col])mine.src=look.images[part.col];else mine.className='empty';images.append(mine);
    const actions=document.createElement('div');actions.className='row';
    const download=document.createElement('a');download.textContent='Download template';download.className='button';
    if(t.png){download.href=t.png;download.download=`${look.model.name.replace(/\W+/g,'_')}_${part.part.replace(/\W+/g,'')}_template.png`;}else download.classList.add('disabled');
    const upload=document.createElement('input');upload.type='file';upload.accept='image/png,image/jpeg';upload.setAttribute('aria-label',`Upload ${part.part} texture`);
    upload.onchange=guarded(async()=>{const f=upload.files[0];if(!f)return;if(f.size>20*1024*1024)throw Error('Image is larger than 20 MB');look.images[part.col]=await readFile(f);renderLookParts();});
    const clear=document.createElement('button');clear.textContent='Keep stock';clear.disabled=!look.images[part.col];clear.onclick=()=>{delete look.images[part.col];renderLookParts();};
    actions.append(download,upload,clear);
    if(t.error){const e=document.createElement('p');e.className='notice warning';e.textContent=t.error;card.append(h,info,e,actions);}else card.append(h,info,images,actions);
    box.append(card);
  }
}
$('lookGo').onclick=guarded(async()=>{
  const look=S.look;if(!look)return;
  const name=$('lookName').value.trim();if(!name)throw Error('Give the look a name.');
  const nif=$('lookNif').files[0]?await readFile($('lookNif').files[0]):null;
  if(!Object.keys(look.images).length&&!nif)throw Error('Upload at least one painted texture (or a NIF).');
  if(!await askConfirm('Install custom look',`Add "${name}" to the client as a new private model based on ${look.model.name}?\n\n${Object.keys(look.images).length} texture(s)${nif?' and your NIF mesh':''}. The game and server must be closed. gamedata.mpk and skin099.mpk are backed up first.`,'Install'))return;
  busy('Installing custom look into the client…');
  try{const r=await api('look-install',{model:look.id,name,scale:Number($('lookScale').value)||null,images:look.images,nif});
    toast(r.message+'\nBackup: '+r.backup);S.models=null;S.lastLook=r.model;await loadModels();}
  finally{busy(null);}
});
function renderLooks() {
  const list=$('lookList');list.replaceChildren();
  if(!S.looks?.length){const p=document.createElement('p');p.className='muted';p.textContent='No custom looks installed in this client yet.';list.append(p);return;}
  for(const look of S.looks){
    const card=document.createElement('div');card.className='lookCard'+(look.model===S.lastLook?' fresh':'');
    const h=document.createElement('strong');h.textContent=look.name;const s=document.createElement('div');s.className='muted';
    s.textContent=`Model ${look.model} · based on ${look.base} · ${look.parts.join(', ')||'mesh only'} · ${look.created}`;
    const row=document.createElement('div');row.className='row';
    const use=document.createElement('button');use.textContent='Use on selected NPC';use.onclick=()=>useLook(look.model);
    const copy=document.createElement('button');copy.textContent='Copy ID';copy.onclick=()=>{navigator.clipboard?.writeText(String(look.model));toast(`Model ${look.model} copied.`);};
    const remove=document.createElement('button');remove.textContent='Uninstall';remove.className='danger';
    remove.onclick=guarded(async()=>{if(!await askConfirm('Uninstall custom look',`Remove "${look.name}" (model ${look.model}) from the client? NPCs still using model ${look.model} will be invisible until you change their Model.`,'Uninstall'))return;
      busy('Restoring client files…');try{const r=await api('look-uninstall',{id:look.id});toast(r.message);await loadModels();}finally{busy(null);}});
    row.append(use,copy,remove);card.append(h,s,row);list.append(card);
  }
}
function useLook(model) {
  const npcs=selectedEntities().filter(e=>e.table==='Mob');
  if(!npcs.length)return toast('Select one or more NPCs in 3D world first (Place copy or Duplicate makes a new one).',true);
  checkpoint();for(const e of npcs)stage(e,{Model:model,...(rawValues(e).NPCTemplateID?{NPCTemplateID:0}:{})});changed();
  setMode('worldView');toast(`${npcs.length} NPC${npcs.length===1?'':'s'} set to model ${model} (pending). Reload textured view to preview, then Review & save.`);
}

// ---------- Items: server item templates and the client's item appearances ----------
const coins=c=>{c=Number(c)||0;const p=Math.floor(c/10000000),g=Math.floor(c/10000)%1000,s=Math.floor(c/100)%100,cu=c%100;return [p&&p+'p',g&&g+'g',s&&s+'s',(cu||!c)&&cu+'c'].filter(Boolean).join(' ');};
const slug=t=>String(t||'item').toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'').slice(0,60)||'item';
S.items={source:'server',rows:[],total:0,offset:0,sel:null};S.itemInfo=new Map();
async function initItems() {
  $('itemList').textContent='Reading the client item catalog…';
  const [enums,catalog]=await Promise.all([api('item-enums'),api('items-catalog')]);
  S.itemEnums=enums;S.catalog=new Map(catalog.map(c=>[c.id,c]));S.catalogList=catalog;
  S.itemChoices={Object_Type:enums.objectType,Item_Type:enums.itemType,Type_Damage:enums.damageType,Realm:enums.realm,Effect:{0:'None',...enums.effect},
    ...Object.fromEntries(['Bonus1Type','Bonus2Type','Bonus3Type','Bonus4Type','Bonus5Type','Bonus6Type','Bonus7Type','Bonus8Type','Bonus9Type','Bonus10Type','ExtraBonusType'].map(c=>[c,{0:'None',...enums.property}]))};
  for(const [k,v] of Object.entries(enums.itemType).sort((a,b)=>Number(a[0])-Number(b[0])))$('itemSlot').add(new Option(v,k));
  restoreItemFilters();setItemSource(S.items.source);
}
// Filters and sort survive a reload (per browser, like other view settings).
const ITEM_FILTERS=['itemSearch','itemKind','itemRealm','itemSlot','itemMinLevel','itemMaxLevel','itemSort','itemIssue','itemClientSort','itemUnused','itemFigure'];
function saveItemFilters(){try{localStorage.setItem('worldWorkshop.items',JSON.stringify({source:S.items.source,...Object.fromEntries(ITEM_FILTERS.map(id=>[id,$(id).type==='checkbox'?$(id).checked:$(id).value]))}));}catch{}}
function restoreItemFilters(){try{const saved=JSON.parse(localStorage.getItem('worldWorkshop.items')||'{}');for(const id of ITEM_FILTERS)if(id in saved){if($(id).type==='checkbox')$(id).checked=saved[id];else $(id).value=saved[id];}if(saved.source)S.items.source=saved.source;}catch{}}
$('itemReset').onclick=()=>{for(const id of ITEM_FILTERS)if(id!=='itemFigure'){if($(id).type==='checkbox')$(id).checked=false;else $(id).value=$(id).tagName==='SELECT'?$(id).options[0].value:'';}S.items.offset=0;saveItemFilters();searchItems().catch(e=>toast(e.message,true));};
// Bonus wording as the in-game delve: stats in points, resists in percent, skills as +levels.
function bonusText(type,value) {
  const name=S.itemEnums?.property[type]||`Bonus ${type}`,t=Number(type);
  if(t>=1&&t<=8)return `${name}: ${value}`;
  if(/^Resist/i.test(name))return `${name.replace(/^Resist /i,'')} resist: ${value}%`;
  if(/^Skill/i.test(name))return `${name.replace(/^Skill /i,'')}: +${value}`;
  if(/^Focus/i.test(name))return `${name.replace(/^Focus /i,'')} focus: +${value}`;
  if(t===10)return `Hits: ${value}`;if(t===9)return `Power: ${value}`;
  return `${name}: ${value}`;
}
function bonuses(v) {const out=[];for(let i=1;i<=10;i++)if(Number(v[`Bonus${i}Type`])&&Number(v[`Bonus${i}`]))out.push(bonusText(v[`Bonus${i}Type`],v[`Bonus${i}`]));if(Number(v.ExtraBonusType)&&Number(v.ExtraBonus))out.push(bonusText(v.ExtraBonusType,v.ExtraBonus));return out;}
const REALMS={0:'',1:'Alb',2:'Mid',3:'Hib'};
function iconNode(model) {
  const c=S.catalog?.get(Number(model)),i=document.createElement('i');i.className='icon';
  if(c?.sheet){i.style.backgroundImage=`url(/icons/${c.sheet.toLowerCase()}.bmp)`;i.style.backgroundPosition=`-${(c.cell%10)*32}px -${Math.floor(c.cell/10)*32}px`;}
  else i.classList.add('none');i.title=c?`Appearance ${c.id}: ${c.name}`:`Appearance ${model} is not in this client`;return i;
}
function setItemSource(source) {
  S.items.source=source;S.items.offset=0;document.querySelectorAll('[data-source]').forEach(b=>b.classList.toggle('active',b.dataset.source===source));
  document.querySelectorAll('#itemsView [data-server]').forEach(n=>n.classList.toggle('hidden',source!=='server'));
  document.querySelectorAll('#itemsView [data-client]').forEach(n=>n.classList.toggle('hidden',source!=='client'));
  if(![...$('itemKind').options].find(o=>o.value===$('itemKind').value&&!o.classList.contains('hidden')))$('itemKind').value='';
  searchItems().catch(e=>toast(e.message,true));
}
document.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>setItemSource(b.dataset.source));
let itemTimer;for(const id of ITEM_FILTERS.filter(i=>i!=='itemFigure'))$(id).addEventListener(['itemSearch','itemMinLevel','itemMaxLevel'].includes(id)?'input':'change',()=>{clearTimeout(itemTimer);itemTimer=setTimeout(()=>{S.items.offset=0;saveItemFilters();searchItems().catch(e=>toast(e.message,true));},300);});
$('itemPrev').onclick=()=>{S.items.offset=Math.max(0,S.items.offset-100);searchItems().catch(e=>toast(e.message,true));};
$('itemNext').onclick=()=>{S.items.offset+=100;searchItems().catch(e=>toast(e.message,true));};
async function searchItems() {
  const q=$('itemSearch').value.trim(),kind=$('itemKind').value;
  if(S.items.source==='server'){
    if($('itemIssue').value==='missing_model')$('itemCount').textContent='Checking appearances…';
    const r=await api('items?'+new URLSearchParams({q,kind,realm:$('itemRealm').value,slot:$('itemSlot').value,min_level:$('itemMinLevel').value,
      max_level:$('itemMaxLevel').value,sort:$('itemSort').value,issue:$('itemIssue').value,offset:S.items.offset}));
    S.items.rows=r.rows;S.items.total=r.total;r.rows.forEach(i=>S.itemInfo.set(i.Id_nb,i));
  }else{
    const words=q.toLowerCase(),unused=$('itemUnused').checked;
    const found=S.catalogList.filter(c=>(!kind||c.kind===kind||(kind==='weapon'&&c.kind==='model'))&&(!unused||!c.used)&&`${c.id} ${c.name} ${c.nif||''}`.toLowerCase().includes(words));
    const order=$('itemClientSort').value;
    found.sort(order==='name'?(a,b)=>a.name.localeCompare(b.name):order==='kind'?(a,b)=>a.kind.localeCompare(b.kind)||a.id-b.id:order==='id_desc'?(a,b)=>b.id-a.id:(a,b)=>a.id-b.id);
    S.items.total=found.length;S.items.rows=found.slice(S.items.offset,S.items.offset+100);
  }
  renderItemList();
}
function pendingItems() {return [...S.pending.values()].filter(c=>c.table==='ItemTemplate'&&c.op==='insert').map(c=>c.after);}
function renderItemList() {
  const list=$('itemList');if(!list||!S.catalog)return;list.replaceChildren();const server=S.items.source==='server';
  $('itemCount').textContent=S.items.total?`${S.items.offset+1}–${S.items.offset+S.items.rows.length} of ${S.items.total.toLocaleString()}`:'Nothing found';
  $('itemPrev').disabled=S.items.offset===0;$('itemNext').disabled=S.items.offset+S.items.rows.length>=S.items.total;
  const rows=server?[...(S.items.offset?[]:pendingItems().filter(i=>`${i.Name} ${i.Id_nb}`.toLowerCase().includes($('itemSearch').value.toLowerCase()))),...S.items.rows]:S.items.rows;
  for(const row of rows){
    const b=document.createElement('button'),text=document.createElement('div'),sub=document.createElement('span');
    const key=server?row.Id_nb:row.id,c=server&&S.pending.get(`ItemTemplate:${row.Id_nb}`);
    b.className='entity itemRow'+(S.items.sel&&S.items.sel.type===S.items.source&&String(S.items.sel.key)===String(key)?' selected':'');
    if(server){const v=c?.op==='insert'?c.after:{...row,...(c?.after||{})};text.textContent=(c?.op==='insert'?'＋ ':c?'● ':'')+(v.Name||v.Id_nb);
      const slot=S.itemEnums.itemType[v.Item_Type],extra=bonuses(v);
      sub.textContent=[`L${v.Level}`,S.itemEnums.objectType[v.Object_Type]||'Type '+v.Object_Type,slot&&Number(v.Item_Type)?slot:'',REALMS[v.Realm],coins(v.Price)].filter(Boolean).join(' · ');
      if(extra.length){const bon=document.createElement('em');bon.textContent=extra.slice(0,3).join(', ')+(extra.length>3?` +${extra.length-3} more`:'');sub.append(bon);}
      b.append(iconNode(v.Model));}
    else{text.textContent=row.name||`Appearance ${row.id}`;sub.textContent=`#${row.id} · ${row.kind}${row.nif?' · '+row.nif:''} · ${row.used?`used by ${row.used} server item${row.used===1?'':'s'}`:'not on server'}`;b.append(iconNode(row.id));}
    text.append(sub);b.append(text);b.onclick=guarded(()=>selectItem(S.items.source,key));list.append(b);
  }
}
async function itemEntity(id) {
  const c=S.pending.get(`ItemTemplate:${id}`);if(c?.op==='insert')return {table:'ItemTemplate',key:id,values:c.after,isNew:true};
  const r=await api('rows?'+new URLSearchParams({table:'ItemTemplate',column:'Id_nb',equals:id,limit:1}));
  if(!r.rows[0])throw Error(`Item ${id} was not found`);return rowEntity('ItemTemplate',r.rows[0]);
}
async function selectItem(type,key) {
  S.items.sel={type,key,entity:type==='server'?await itemEntity(key):null};renderItemList();renderItemSide();
  await previewItem(selectedLook());
}
$('itemFigure').onchange=()=>{const look=selectedLook();if(look)previewItem(look).catch(e=>toast(e.message,true));};
// What the viewer shows: the appearance plus the server item's Effect (0 = the appearance's own effect column).
function selectedLook() {
  const sel=S.items.sel;if(!sel)return null;
  const figure=$('itemFigure').value;
  if(sel.type==='client')return {model:Number(sel.key),effect:0,extension:0,color:0,figure,key:`${sel.key}:0:0:0:${figure}`};
  // The server item's Extension picks the body / gloves / boots mesh and its Color is the dye, as in game.
  const c=S.pending.get(`ItemTemplate:${sel.key}`),v=c?.op==='insert'?c.after:rawValues(sel.entity);
  const effect=Number(v.Effect)||0,extension=Number(v.Extension)||0,color=Number(v.Color)||0;
  return {model:Number(v.Model),effect,extension,color,figure,key:`${v.Model}:${effect}:${extension}:${color}:${figure}`};
}
// A readable summary like the in-game delve, built from the item's columns.
function renderDelve(v) {
  const box=$('itemDelve');box.replaceChildren();const lines=[],o=Number(v.Object_Type);
  if(o>=1&&o<=28)lines.push(`DPS ${(v.DPS_AF/10).toFixed(1)} · Speed ${(v.SPD_ABS/10).toFixed(1)}s · ${S.itemEnums.damageType[v.Type_Damage]||'damage '+v.Type_Damage}`);
  if(o>=32&&o<=38)lines.push(`Armor factor ${v.DPS_AF} · Absorb ${v.SPD_ABS}%`);
  if(o===42)lines.push(`Shield size ${v.Type_Damage} · DPS ${(v.DPS_AF/10).toFixed(1)}`);
  lines.push(`Quality ${v.Quality}% · Condition ${v.Condition??'?'}/${v.MaxCondition??'?'} · Weight ${(v.Weight/10).toFixed(1)}`);
  const b=bonuses(v);if(b.length)lines.push('Bonuses: '+b.join(' · '));
  if(Number(v.SpellID))lines.push(`Charge: spell ${v.SpellID} (${v.Charges}/${v.MaxCharges} charges)`);
  if(Number(v.ProcSpellID))lines.push(`Proc: spell ${v.ProcSpellID} at ${v.ProcChance||'default'}% chance`);
  if(Number(v.Effect))lines.push(`Effect: ${S.itemEnums.effect?.[v.Effect]||v.Effect}`);
  const classes=String(v.AllowedClasses||'').split(';').filter(x=>x&&x!=='0');
  if(classes.length)lines.push('Usable by: '+classes.map(c=>S.itemEnums.characterClass?.[c]||c).join(', '));
  if(Number(v.LevelRequirement))lines.push(`Requires level ${v.LevelRequirement}`);
  const flags=[!Number(v.IsTradable)&&'no trade',!Number(v.IsDropable)&&'no drop',!Number(v.CanDropAsLoot)&&'never loot',Number(v.MaxCount)>1&&`stacks to ${v.MaxCount}`].filter(Boolean);
  if(flags.length)lines.push(flags.join(' · '));
  for(const t of lines){const d=document.createElement('div');d.textContent=t;box.append(d);}
}
// Where players get it, each entry a link into the matching view.
function renderSources(r) {
  const uses=$('itemUses');uses.replaceChildren();
  const section=(title,items,make)=>{if(!items.length)return;const label=document.createElement('label');label.textContent=title;const chips=document.createElement('div');chips.className='chips';
    for(const it of items){const b=document.createElement('button');make(b,it);chips.append(b);}uses.append(label,chips);};
  section('SOLD BY',r.merchants,(b,m)=>{b.textContent=m.seller?`${m.seller}${m.sellers>1?` +${m.sellers-1}`:''} · ${m.ItemListID}`:m.ItemListID;b.title='Open this merchant list';b.onclick=guarded(()=>openList(m.ItemListID));});
  section('DROPS FROM',r.loot,(b,l)=>{b.textContent=`${l.mobs.length?l.mobs.slice(0,3).join(', ')+(l.mobs.length>3?'…':''):l.TemplateName} · ${l.Chance}%`;b.title=`Loot table ${l.TemplateName}`;
    b.onclick=guarded(async()=>{await openTable('LootTemplate',{column:'TemplateName',equals:l.TemplateName});setMode('dataView');});});
  section('ONE-TIME DROP',r.otd,(b,o)=>{b.textContent=`${o.MobName} (level ${o.MinLevel}+)`;b.onclick=guarded(async()=>{await openTable('LootOTD',{column:'MobName',equals:o.MobName});setMode('dataView');});});
  section('QUEST REWARD',r.quests,(b,q)=>{b.textContent=q.Name;b.onclick=guarded(async()=>{await openTable('DataQuest',{column:'ID',equals:String(q.ID)});setMode('dataView');});});
  section('STARTER GEAR FOR',r.starter,(b,x)=>{b.textContent=String(x.Class).split(';').map(c=>S.itemEnums.characterClass?.[c]||c).join(', ');b.disabled=true;});
  section('CRAFTED',r.crafted||[],(b,x)=>{b.textContent=`${S.itemEnums.craftingSkill?.[x.CraftingSkillType]||'Crafting skill '+x.CraftingSkillType}, skill ${x.CraftingLevel}`;b.onclick=guarded(async()=>{await openTable('CraftedItem',{column:'Id_nb',equals:S.items.sel.key});setMode('dataView');});});
  section('ARTIFACT',r.artifacts||[],(b,x)=>{b.textContent=x.ArtifactID;b.onclick=guarded(async()=>{await openTable('Artifact',{column:'ArtifactID',equals:x.ArtifactID});setMode('dataView');});});
  section('CURRENCY FOR',r.currency,(b,x)=>{b.textContent=x.ItemListID;b.onclick=guarded(()=>openList(x.ItemListID));});
  if(!uses.children.length){const p=document.createElement('p');p.className='notice warning';p.textContent='No merchant, loot table, crafting recipe, quest, artifact or starter kit gives this item. Unless a server script hands it out, players cannot get it yet.';uses.append(p);}
}
function renderItemSide() {
  if(!S.catalog||!S.items.sel)return;const sel=S.items.sel,actions=$('itemActions'),uses=$('itemUses');
  actions.replaceChildren();uses.replaceChildren();$('itemForm').replaceChildren();actions.classList.remove('hidden');
  const button=(text,fn,cls)=>{const b=document.createElement('button');b.textContent=text;if(cls)b.className=cls;b.onclick=guarded(fn);actions.append(b);return b;};
  $('itemDelve').replaceChildren();
  if(sel.type==='client'){
    const c=S.catalog.get(Number(sel.key));$('itemLabel').textContent='CLIENT APPEARANCE';$('itemName').textContent=c.name||`Appearance ${c.id}`;
    $('itemInfo').textContent=`objects.csv #${c.id} · ${c.kind}${c.nif?' · mesh '+c.nif:''}${Object.keys(c.skins).length?' · textures: '+Object.keys(c.skins).join(', '):''}${Object.keys(c.effects||{}).length?' · '+Object.entries(c.effects).map(([k,v])=>`${k} ${v}`).join(', '):''}\n${c.used?`Used by ${c.used} server item(s), e.g. ${c.example}.`:'No server item uses this appearance yet.'}`;
    button('＋ Create server item from this',()=>createFromAppearance(c),'primary');
    if(c.used)button('Show server items using it',async()=>{setItemSource('server');$('itemSearch').value='';const r=await api('items?'+new URLSearchParams({model:c.id}));S.items.rows=r.rows;S.items.total=r.total;renderItemList();});
    return;
  }
  const e=S.pending.has(`ItemTemplate:${sel.key}`)&&S.pending.get(`ItemTemplate:${sel.key}`).op==='insert'?{table:'ItemTemplate',key:sel.key,values:S.pending.get(`ItemTemplate:${sel.key}`).after,isNew:true}:sel.entity;
  if(!e)return;const v=rawValues(e),c=S.pending.get(identity(e));
  $('itemLabel').textContent='SERVER ITEM';$('itemName').textContent=v.Name||v.Id_nb;
  $('itemInfo').textContent=`${v.Id_nb}${c?.op==='insert'?' · NEW (pending)':c?.op==='delete'?' · WILL BE DELETED':c?' · edited':''}\n${S.itemEnums.objectType[v.Object_Type]||''} · ${S.itemEnums.itemType[v.Item_Type]||'slot '+v.Item_Type} · level ${v.Level} · ${coins(v.Price)}`;
  button('⧉ Copy',async()=>{const key=await duplicateRow('ItemTemplate',rawValues(e),{Name:`${v.Name} (copy)`});if(key!==null){changed();await selectItem('server',key);}});
  button('＋ Add to merchant list…',()=>addToListPrompt(v.Id_nb));
  button('Open in Game data',async()=>{await openTable('ItemTemplate',{column:'Id_nb',equals:v.Id_nb});selectRow('ItemTemplate',v.Id_nb);setMode('dataView');});
  button(c?.op==='delete'?'↺ Keep':'✕ Delete',()=>{checkpoint();if(c?.op==='delete')S.pending.delete(identity(e));else stageDelete(e);changed();},'danger');
  renderDelve(v);
  if(!e.isNew)api('item-sources?id='+encodeURIComponent(v.Id_nb)).then(r=>{if(S.items.sel?.key===sel.key)renderSources(r);}).catch(()=>{});
  else uses.textContent='New item: nothing sells or drops it yet.';
  if(c?.op==='delete')return;
  form($('itemForm'),e,['Id_nb','Name','Level','Realm','Object_Type','Item_Type','Model','DPS_AF','SPD_ABS','Type_Damage','Hand','Quality','Price','Weight','Color','Effect','Extension',
    'Bonus','Bonus1Type','Bonus1','Bonus2Type','Bonus2','Bonus3Type','Bonus3','Bonus4Type','Bonus4','Bonus5Type','Bonus5','Bonus6Type','Bonus6','Bonus7Type','Bonus7','Bonus8Type','Bonus8','Bonus9Type','Bonus9','Bonus10Type','Bonus10','ExtraBonusType','ExtraBonus',
    'SpellID','Charges','MaxCharges','ProcSpellID','ProcChance','IsDropable','IsTradable','IsPickable','CanDropAsLoot','MaxCount','PackSize','AllowedClasses','Description'],'More columns',S.itemChoices);
}
async function previewItem(look) {
  if(!look)return;S.previewKey=look.key;const {model,effect,figure,extension,color}=look;const textures=$('itemTextures'),note=$('itemPreviewNote');textures.replaceChildren();
  if(!S.catalog.get(model)){clearViewer();note.textContent=`Appearance ${model} is not in this client, so it shows as a default model or nothing in game.`;return;}
  note.textContent='Converting the client appearance…';
  const p=await api(`item-preview?model=${model}&effect=${effect}&figure=${figure}&extension=${extension}&color=${color}`);if(selectedLook()?.key!==look.key)return;
  const fx=p.effect;$('itemFigure').parentElement.classList.toggle('hidden',!p.figure);
  note.textContent=[p.source?`Mesh ${p.source}`:'',fx?.gltf?`Effect ${fx.id}: ${fx.name} (${fx.nif}${fx.particles?`, ${fx.particles} particle system${fx.particles===1?'':'s'}`:''})${p.gltf?'':' · shown on its own; in game it sits on the worn item'}`:'',
    p.figure?`Worn by a ${p.figure.race} (${p.figure.worn.join(', ')}${p.figure.robe?', robe body':''}${p.figure.extension?`, extension ${p.figure.extension}`:''}${p.figure.dye?`, dyed ${p.figure.dye.name}`:''}), dressed the way the client dresses player characters. Drag to turn.`:p.textures.length?'Worn armor is drawn on the character body; these are its textures.':'',...p.warnings].filter(Boolean).join('\n')||`Appearance ${model}`;
  if(p.figure)await showGltf(p.base+p.figure.gltf,fx?.gltf?p.base+fx.gltf:null,p.base+'effect/',{back:p.figure.worn.includes('cloak'),
    helm:p.figure.helm?{url:p.base+p.figure.helm.gltf,scale:p.figure.helm.scale}:null,focusHead:p.figure.worn.includes('helm'),dye:p.figure.dye?{rgb:p.figure.dye.rgb,parts:p.figure.worn}:null});
  else if(p.gltf||fx?.gltf)await showGltf(p.gltf?p.base+p.gltf:null,fx?.gltf?p.base+fx.gltf:null,p.base+'effect/');else clearViewer();
  for(const t of p.textures){const fig=document.createElement('figure'),img=document.createElement('img'),cap=document.createElement('figcaption');img.src=p.base+t.file;img.alt=t.name;cap.textContent=`${t.label} · ${t.name}`;fig.append(img,cap);textures.append(fig);}
}
// Small separate viewer for one item mesh.
const viewer={};
function ensureViewer() {
  if(viewer.renderer)return;const stage=$('itemStage');
  viewer.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});viewer.renderer.setPixelRatio(Math.min(devicePixelRatio,2));stage.append(viewer.renderer.domElement);
  viewer.scene=new THREE.Scene();viewer.scene.add(new THREE.HemisphereLight(0xffffff,0x555544,2.4));const key=new THREE.DirectionalLight(0xffffff,2.2);key.position.set(2,3,4);viewer.scene.add(key);
  viewer.camera=new THREE.PerspectiveCamera(35,1,.01,1000);viewer.controls=new OrbitControls(viewer.camera,viewer.renderer.domElement);viewer.controls.enableDamping=true;
  viewer.group=new THREE.Group();viewer.scene.add(viewer.group);viewer.loader=new GLTFLoader();
  new ResizeObserver(()=>{const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;viewer.renderer.setSize(w,h);viewer.camera.aspect=w/h;viewer.camera.updateProjectionMatrix();}).observe(stage);
  viewer.particles=[];viewer.clock=new THREE.Clock();
  const loop=()=>{requestAnimationFrame(loop);const dt=Math.min(viewer.clock.getDelta(),.05);if(S.mode!=='itemsView')return;viewer.controls.update();viewer.group.rotation.y+=viewer.spin?0.004:0;
    // Point sprites are sized in pixels: the viewport height over the view's vertical extent at distance 1.
    const scale=viewer.renderer.domElement.height/(2*Math.tan(THREE.MathUtils.degToRad(viewer.camera.fov)/2));
    viewer.mixer?.update(dt);for(const p of viewer.particles)p.update(dt,scale);faceCamera(viewer.billboards||[],viewer.camera);viewer.renderer.render(viewer.scene,viewer.camera);};loop();
  viewer.renderer.domElement.addEventListener('pointerdown',()=>{viewer.spin=false;});
}
function clearViewer(){if(viewer.group){viewer.mixer?.stopAllAction();viewer.mixer=null;dispose(viewer.group);viewer.particles=[];}$('itemStage').classList.add('empty');}
// The item mesh and its effect share the item's own space, as the client draws a weapon glow.
async function showGltf(url, effectUrl, effectBase, options={}) {
  ensureViewer();$('itemStage').classList.remove('empty');viewer.mixer?.stopAllAction();viewer.mixer=null;dispose(viewer.group);viewer.particles=[];
  const holder=new THREE.Group();viewer.group.add(holder);viewer.group.rotation.set(0,0,0);
  viewer.billboards=[];
  const itemGltf=url?await viewer.loader.loadAsync(url):null,item=itemGltf?.scene||null;if(item){viewer.billboards.push(...applyNifMaterials(itemGltf));holder.add(item);
    // A dressed character (worn armor / cloak preview): play its idle so cloth sits as in game.
    // The item's dye multiplies its own pieces (Fig3Figure armor_tints), not the head or starter clothes.
    if(options.dye)item.traverse(n=>{if(n.isMesh&&options.dye.parts.includes(n.name.replace(/_\d+$/,''))){n.material=n.material.clone();n.material.color.setRGB(...options.dye.rgb);}});
    const idle=itemGltf.animations.find(a=>a.name==='idle')||itemGltf.animations[0];
    if(idle){viewer.mixer=new THREE.AnimationMixer(item);viewer.mixer.clipAction(idle).play();viewer.mixer.update(.01);}}
  // A helm hangs on the figure's helm node (Bip01 Helmet, else Bip01 Head) in NIF space: glTF metres/Y-up back to
  // NIF units/Z-up (new client WeaponModels.TO_NIF), times the items.csv helm scale. Its effect (fire eyes...) rides along.
  let effectParent=holder,bone=null;
  if(item&&options.focusHead)item.traverse(n=>{const name=n.name.replace(/_/g,' ');if(name==='Bip01 Helmet'||(!bone&&name==='Bip01 Head'))bone=n;});
  if(options.helm&&item){
    if(bone){
      const helm=await viewer.loader.loadAsync(options.helm.url);viewer.billboards.push(...applyNifMaterials(helm));
      const mount=new THREE.Group(),k=40*(options.helm.scale||100)/100;
      mount.matrixAutoUpdate=false;mount.matrix.set(k,0,0,0, 0,0,-k,0, 0,k,0,0, 0,0,0,1);
      mount.add(helm.scene);bone.add(mount);effectParent=mount;
    }
  }
  if(effectUrl){const fx=await viewer.loader.loadAsync(effectUrl);viewer.billboards.push(...applyNifMaterials(fx));effectParent.add(fx.scene);viewer.particles=await loadParticles(fx,effectBase);if(viewer.particles.length)effectParent.add(...viewer.particles);}
  // Frame the item and its effect emitters (effect-only items such as VFX helms carry a tiny placeholder mesh).
  const box=item?new THREE.Box3().setFromObject(item):new THREE.Box3();
  for(const p of viewer.particles)box.expandByPoint(p.origin).expandByScalar(p.baseSize);
  if(box.isEmpty())box.setFromCenterAndSize(new THREE.Vector3(),new THREE.Vector3(1,1,1));
  const size=Math.max(box.getSize(new THREE.Vector3()).length(),item?0:1),center=box.getCenter(new THREE.Vector3());
  holder.position.sub(center);viewer.camera.near=size/100;viewer.camera.far=size*100;viewer.camera.updateProjectionMatrix();
  // Fit the whole thing in view; a dressed character is a tall, narrow box, so use its height.
  const height=box.getSize(new THREE.Vector3()).y,fit=viewer.mixer?height*.5/Math.tan(THREE.MathUtils.degToRad(viewer.camera.fov)/2)*1.2:size*1.1;
  viewer.camera.position.copy(new THREE.Vector3(.35,.15,1).normalize().multiplyScalar(fit));viewer.controls.target.set(0,0,0);viewer.controls.update();viewer.spin=true;
  if(options.back)viewer.group.rotation.y=Math.PI;
  // Helms: frame the head and shoulders instead of the whole figure.
  if(bone){
    viewer.scene.updateMatrixWorld(true);const head=bone.getWorldPosition(new THREE.Vector3());
    viewer.controls.target.copy(head).add(new THREE.Vector3(0,-height*.04,0));
    viewer.camera.position.copy(viewer.controls.target).add(new THREE.Vector3(.35,.15,1).normalize().multiplyScalar(height*.55));viewer.controls.update();
  }
}
// A new server item that looks like a client appearance: start from a similar existing item so every column is sensible.
const SLOT_TYPES={Body:25,Arms:28,Gloves:22,Legs:27,Boots:23,Helm:21,Cloak:26};
async function createFromAppearance(c) {
  let kind={model:/shield/i.test(c.name)?'shield':'weapon',armor:'armor',helm:'armor',cloak:'cloak',housing:'housing'}[c.kind]||'other';
  const slot=c.kind==='armor'||c.kind==='helm'?(SLOT_TYPES[Object.keys(c.skins).find(s=>SLOT_TYPES[s])]||25):null;
  // Housing: garden (exterior) 49, wall 50, floor 51 decide where a player may place it.
  const house=c.kind==='housing'?(/^ext/i.test(c.name)?49:/wall|tapestry|banner|painting|shield|plaque|mirror/i.test(c.name)?50:51):null;
  const r=await api('items?'+new URLSearchParams({kind,limit:500}));
  const like=r.rows.find(i=>(slot===null||i.Item_Type===slot)&&(house===null||i.Object_Type===house))||r.rows[0];
  const base=like?rawValues(await itemEntity(like.Id_nb)):blankRow('ItemTemplate');
  const name=(c.name||`Item ${c.id}`).replace(/^ext_\s*/i,'').replace(/_/g,' ');
  const key=await duplicateRow('ItemTemplate',base,{Name:name.charAt(0).toUpperCase()+name.slice(1),Model:c.id},false,slug(name));
  if(key===null)return;changed();setItemSource('server');await selectItem('server',key);
  toast(`New item based on ${like?like.Name:'a blank row'} with appearance ${c.id}. Check its type, level and stats, then Review & save.`);
}
async function addToListPrompt(idnb) {
  const list=await askText('Add to a merchant list','Merchant item list ID (an existing one, or a new name):',S.list?.id||'');
  if(!list)return;await openList(list);await addToList(idnb);
}

// ---------- Merchants: MerchantItem lists, their sellers and payment currency ----------
const PAGES=5,SLOTS=30,CURRENCY='offline_currency_lists';
async function loadLists() {S.lists=await api('merchant-lists?q='+encodeURIComponent($('listSearch').value.trim()));renderLists();}
function renderLists() {
  const box=$('listList');box.replaceChildren();
  const pendingLists=new Set([...S.pending.values()].filter(c=>c.table==='MerchantItem'&&c.op==='insert').map(c=>c.after.ItemListID));
  const lists=[...[...pendingLists].filter(id=>!S.lists.some(l=>l.id===id)).map(id=>({id,items:0,spawns:0,isNew:true})),...S.lists];
  for(const l of lists){const b=document.createElement('button');b.className='entity'+(S.list?.id===l.id?' selected':'');b.textContent=(l.isNew?'＋ ':pendingLists.has(l.id)?'● ':'')+l.id;
    const s=document.createElement('span');s.textContent=`${l.items} items · ${l.spawns} merchant${l.spawns===1?'':'s'}${l.currency?' · paid in '+l.currency:''}`;b.append(s);b.onclick=guarded(()=>openList(l.id));box.append(b);}
}
let listTimer;$('listSearch').oninput=()=>{clearTimeout(listTimer);listTimer=setTimeout(()=>loadLists().catch(e=>toast(e.message,true)),250);};
$('listNew').onclick=guarded(async()=>{const id=await askText('New merchant list','Name the new item list (for example grove_token_shop):','');if(id)await openList(id);});
async function openList(id) {
  setMode('merchantsView');if(!S.lists)await loadLists();
  S.list=await api('merchant-list?id='+encodeURIComponent(id));S.listPage=S.listPage??0;S.slotSel=null;
  for(const s of S.list.slots)if(s.ItemTemplateID)S.itemInfo.set(s.ItemTemplateID,{Id_nb:s.ItemTemplateID,Name:s.ItemName,Price:s.ItemPrice,Model:s.ItemModel,Level:s.ItemLevel});
  renderLists();renderListView();
}
function listSlots() {
  if(!S.list)return [];const found=new Map();
  for(const row of S.list.slots){const e=rowEntity('MerchantItem',row);found.set(identity(e),e);}
  for(const c of S.pending.values())if(c.table==='MerchantItem'&&c.op==='insert'&&c.after.ItemListID===S.list.id)found.set(`MerchantItem:${c.key}`,{table:'MerchantItem',key:c.key,values:c.after,isNew:true});
  return [...found.values()].filter(e=>!isDeleted(e)&&rawValues(e).ItemListID===S.list.id);
}
function currencyEntity() {
  const c=S.list&&S.pending.get(`${CURRENCY}:${S.list.id}`);if(c?.op==='insert')return {table:CURRENCY,key:S.list.id,values:c.after,isNew:true};
  return S.list?.currency?rowEntity(CURRENCY,S.list.currency):null;
}
function currencyItem(){const e=currencyEntity();return e&&!isDeleted(e)?rawValues(e).CurrencyItem:null;}
function price(item){const cur=currencyItem();if(!item)return '';return cur?`${item.Price} × ${S.itemInfo.get(cur)?.Name||cur}`:coins(item.Price);}
function renderListView() {
  if(!S.list||S.mode!=='merchantsView')return;const slots=listSlots(),page=S.listPage;
  $('listTitle').textContent=`${S.list.id} · ${slots.length} item${slots.length===1?'':'s'}`;$('listSide').classList.remove('hidden');$('listAdd').classList.remove('hidden');
  const pages=$('listPages');pages.replaceChildren();
  for(let p=0;p<PAGES;p++){const b=document.createElement('button');const n=slots.filter(e=>rawValues(e).PageNumber===p).length;b.textContent=`Page ${p+1}${n?` (${n})`:''}`;b.className=p===page?'active':'';b.onclick=()=>{S.listPage=p;S.slotSel=null;renderListView();};pages.append(b);}
  const grid=$('listGrid');grid.replaceChildren();
  for(let i=0;i<SLOTS;i++){
    const e=slots.find(s=>rawValues(s).PageNumber===page&&rawValues(s).SlotPosition===i),cell=document.createElement('button');cell.className='slot'+(S.slotSel===i?' selected':'');
    if(e){const v=rawValues(e),item=S.itemInfo.get(v.ItemTemplateID);cell.append(iconNode(item?.Model));const t=document.createElement('div');t.textContent=item?.Name||v.ItemTemplateID;const s=document.createElement('span');s.textContent=item?price(item):'(not loaded)';t.append(s);cell.append(t);
      if(e.isNew||S.pending.has(identity(e)))cell.classList.add('changed');}
    else cell.classList.add('free');
    cell.onclick=()=>{S.slotSel=i;renderListView();};grid.append(cell);
  }
  // Payment
  const cur=currencyItem();$('listCurrencyMode').value=cur?'item':'coin';$('currencyBox').classList.toggle('hidden',!cur&&$('listCurrencyMode').dataset.want!=='item');
  if(document.activeElement!==$('currencyItem'))$('currencyItem').value=cur||'';
  const sellers=$('listMerchants');sellers.replaceChildren();
  for(const m of S.list.merchants){const row=document.createElement('div');row.className='row seller';const t=document.createElement('span');t.textContent=`${m.Name}${m.Guild?' · '+m.Guild:''}`;
    const warn=cur&&m.ClassType!=='DOL.GS.GameCustomCurrencyMerchant'?' ⚠ not a currency merchant':(!cur&&m.ClassType==='DOL.GS.GameCustomCurrencyMerchant'?' ⚠ currency class but no currency':'');t.title=m.ClassType+warn;if(warn)t.textContent+=warn;
    const b=document.createElement('button');b.textContent='Show in 3D';b.onclick=guarded(()=>showInWorld('Mob',m,m.Mob_ID));row.append(t,b);sellers.append(row);}
  if(!S.list.merchants.length)sellers.textContent='No NPC sells this list yet.';
  // Selected slot
  const info=$('slotInfo');info.replaceChildren();const e=slots.find(s=>rawValues(s).PageNumber===page&&rawValues(s).SlotPosition===S.slotSel);
  if(S.slotSel===null||S.slotSel===undefined){info.textContent='Click a slot.';return;}
  if(!e){info.textContent=`Page ${page+1}, slot ${S.slotSel+1} is free. Search below and click an item to put it here.`;return;}
  const v=rawValues(e),item=S.itemInfo.get(v.ItemTemplateID);const h=document.createElement('strong');h.textContent=item?.Name||v.ItemTemplateID;
  const p=document.createElement('div');p.textContent=`${v.ItemTemplateID} · ${item?price(item):''}`;
  const row=document.createElement('div');row.className='row';
  const priceInput=document.createElement('input');priceInput.type='number';priceInput.min=0;priceInput.value=item?.Price??'';priceInput.title=cur?'Number of currency items':'Price in copper (100c = 1s, 100s = 1g, 1000g = 1p)';
  const setPrice=document.createElement('button');setPrice.textContent=cur?'Set cost':'Set price';
  setPrice.onclick=guarded(async()=>{const it=await itemEntity(v.ItemTemplateID);checkpoint();stage(it,{Price:Math.max(0,Math.round(Number(priceInput.value)||0))});S.itemInfo.set(v.ItemTemplateID,{...item,Price:Math.round(Number(priceInput.value)||0)});changed();
    toast('Price is part of the item itself: it changes on every merchant list that sells this item. Copy the item in Items to price it separately.');});
  const remove=document.createElement('button');remove.textContent='✕ Remove';remove.className='danger';remove.onclick=()=>{checkpoint();stageDelete(e);changed();};
  const open=document.createElement('button');open.textContent='Open item';open.onclick=guarded(async()=>{setMode('itemsView');if(!S.itemEnums)await initItems();setItemSource('server');await selectItem('server',v.ItemTemplateID);});
  row.append(priceInput,setPrice);const row2=document.createElement('div');row2.className='row';row2.append(open,remove);info.append(h,p,row,row2);
}
async function addToList(idnb, page=S.listPage??0) {
  const used=new Set(listSlots().map(e=>`${rawValues(e).PageNumber}:${rawValues(e).SlotPosition}`));
  let target=null;if(S.slotSel!==null&&S.slotSel!==undefined&&!used.has(`${page}:${S.slotSel}`))target=[page,S.slotSel];
  for(let p=page;!target&&p<PAGES;p++)for(let i=0;i<SLOTS&&!target;i++)if(!used.has(`${p}:${i}`))target=[p,i];
  if(!target)throw Error('This list is full (5 pages of 30 items).');
  await duplicateRow('MerchantItem',{...blankRow('MerchantItem'),ItemListID:S.list.id,ItemTemplateID:idnb,PageNumber:target[0],SlotPosition:target[1]});
  S.listPage=target[0];S.slotSel=null;changed();toast(`Added to page ${target[0]+1}, slot ${target[1]+1}.`);
}
let addTimer;const addSearch=()=>{clearTimeout(addTimer);addTimer=setTimeout(guarded(async()=>{
  const r=await api('items?'+new URLSearchParams({q:$('addSearch').value.trim(),kind:$('addKind').value,limit:40}));const box=$('addResults');box.replaceChildren();
  for(const i of r.rows){S.itemInfo.set(i.Id_nb,i);const b=document.createElement('button');b.className='entity itemRow';b.append(iconNode(i.Model));const t=document.createElement('div');t.textContent=i.Name;const s=document.createElement('span');s.textContent=`${i.Id_nb} · L${i.Level} · ${price(i)}`;t.append(s);b.append(t);
    b.onclick=guarded(()=>addToList(i.Id_nb));box.append(b);}
  for(const i of pendingItems())if(`${i.Name} ${i.Id_nb}`.toLowerCase().includes($('addSearch').value.toLowerCase())){S.itemInfo.set(i.Id_nb,i);const b=document.createElement('button');b.className='entity';b.textContent=`＋ ${i.Name} (new, pending)`;b.onclick=guarded(()=>addToList(i.Id_nb));box.prepend(b);}
}),250);};
$('addSearch').oninput=addSearch;$('addKind').onchange=addSearch;
$('listCurrencyMode').onchange=()=>{
  const want=$('listCurrencyMode').value;$('listCurrencyMode').dataset.want=want;
  if(want==='coin'){const e=currencyEntity();if(e&&!isDeleted(e)){checkpoint();stageDelete(e);changed();}else renderListView();}
  else{$('currencyBox').classList.remove('hidden');const e=currencyEntity();if(e&&isDeleted(e)){checkpoint();S.pending.delete(identity(e));changed();}$('currencyItem').focus();}
};
async function setCurrency(idnb) {
  idnb=idnb.trim();if(!idnb)return;await itemEntity(idnb).then(e=>S.itemInfo.set(idnb,rawValues(e)));
  checkpoint();const e=currencyEntity();
  if(e&&!e.isNew&&!isDeleted(e))stage(e,{CurrencyItem:idnb});
  else{if(e&&isDeleted(e))S.pending.delete(identity(e));
    const after={...blankRow(CURRENCY),ItemListID:S.list.id,CurrencyItem:idnb,Description:`Paid in ${S.itemInfo.get(idnb)?.Name||idnb}`,offline_currency_lists_ID:crypto.randomUUID()};
    if(S.list.currency)stage(rowEntity(CURRENCY,S.list.currency),{CurrencyItem:idnb});else S.pending.set(`${CURRENCY}:${S.list.id}`,{op:'insert',table:CURRENCY,key:S.list.id,before:{},after});}
  changed();toast(`${S.list.id} now takes ${S.itemInfo.get(idnb)?.Name||idnb} as payment (pending). Its merchants need ClassType DOL.GS.GameCustomCurrencyMerchant.`);
}
$('currencyItem').onchange=guarded(()=>setCurrency($('currencyItem').value));
let curTimer;$('currencyItem').oninput=()=>{clearTimeout(curTimer);curTimer=setTimeout(guarded(async()=>{
  const r=await api('items?'+new URLSearchParams({q:$('currencyItem').value.trim(),limit:12}));const box=$('currencyResults');box.replaceChildren();
  for(const i of r.rows){const b=document.createElement('button');b.className='entity itemRow';b.append(iconNode(i.Model));const t=document.createElement('div');t.textContent=i.Name;const s=document.createElement('span');s.textContent=i.Id_nb;t.append(s);b.append(t);
    b.onclick=guarded(async()=>{$('currencyItem').value=i.Id_nb;box.replaceChildren();await setCurrency(i.Id_nb);});box.append(b);}
}),250);};
$('listAssign').onclick=guarded(async()=>{
  const npcs=selectedEntities().filter(e=>e.table==='Mob');if(!npcs.length)throw Error('Select one or more NPCs in 3D world first (Place copy makes a new one).');
  const cur=currencyItem();checkpoint();
  for(const e of npcs){const cls=rawValues(e).ClassType||'';stage(e,{ItemsListTemplateID:S.list.id,ClassType:cur?'DOL.GS.GameCustomCurrencyMerchant':(/Merchant/.test(cls)&&!/CustomCurrency/.test(cls)?cls:'DOL.GS.GameMerchant')});}
  changed();toast(`${npcs.length} NPC${npcs.length===1?'':'s'} will sell ${S.list.id}${cur?` for ${S.itemInfo.get(cur)?.Name||cur}`:''} (pending).`);
});

// ---------- Review, patches, backups ----------
function showDialog(title, body, action=null, label='Apply') {
  $('dialogTitle').textContent=title;$('dialogBody').replaceChildren();
  if(typeof body==='string')$('dialogBody').textContent=body;else $('dialogBody').append(body);
  $('confirm').textContent=label;$('confirm').classList.toggle('hidden',!action);$('confirm').disabled=false;
  $('confirm').onclick=guarded(async()=>{ $('confirm').disabled=true;try{await action();$('dialog').close();}finally{$('confirm').disabled=false;} });$('dialog').showModal();
}
$('cancel').onclick=()=>$('dialog').close();
async function currentPatch() {
  if(!S.pending.size)throw Error('No edits have been staged.');
  if(!S.data)throw Error('Load a zone first.');
  return api('export',{changes:[...S.pending.values()],fingerprint:S.data.fingerprint});
}
function describe(c) {
  const op=c.op||'update';
  if(op==='insert')return `NEW ${c.table} · ${c.key}\n`+Object.entries(c.after).filter(([,v])=>v!==null&&v!=='').map(([k,v])=>`  ${k}: ${JSON.stringify(v)}`).join('\n');
  if(op==='delete')return `DELETE ${c.table} · ${c.key}${c.before.Name?' ('+c.before.Name+')':''}`;
  return `${c.table} · ${c.key}\n`+Object.keys(c.after).map(k=>`  ${k}: ${JSON.stringify(c.before[k])} → ${JSON.stringify(c.after[k])}`).join('\n');
}
function reviewBody(patch) {
  const div=document.createElement('div'),p=document.createElement('p'),count=op=>patch.changes.filter(c=>(c.op||'update')===op).length;
  p.textContent=`${count('update')} edited, ${count('insert')} new and ${count('delete')} deleted rows. A database backup and reversible row patch will be saved. Close the game and server before applying.`;div.append(p);
  const pre=document.createElement('pre');pre.textContent=patch.changes.map(describe).join('\n\n');div.append(pre);return div;
}
$('pendingList').onclick=()=>{if(!S.pending.size)return toast('No pending edits.');showDialog('Pending edits',reviewBody({changes:[...S.pending.values()]}));};
$('review').onclick=guarded(async()=>{
  const patch=await currentPatch();await api('validate',{patch});
  showDialog('Review server world edits',reviewBody(patch),async()=>{
    busy('Saving world edits and backup…');try{const r=await api('apply',{patch});S.pending.clear();S.undo=[];S.redo=[];await loadZone(S.data.zone.ZoneID);await searchRows();toast(r.message+'\nBackup: '+r.backup);}finally{busy(null);}
  },'Save to server data');
});
$('export').onclick=guarded(async()=>{
  const patch=await currentPatch();const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(patch,null,2)],{type:'application/json'}));a.href=url;a.download=`daoc-world-${new Date().toISOString().replace(/[:.]/g,'-')}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);toast('Patch exported. It includes edited world rows and a required client-world fingerprint; no player records.');
});
$('import').onclick=()=>$('importFile').click();
$('importFile').onchange=guarded(async()=>{
  const file=$('importFile').files[0];if(!file)return;const patch=JSON.parse(await file.text());$('importFile').value='';await api('validate',{patch});
  if(S.pending.size)throw Error('Export or undo the existing pending edits before importing another patch.');
  showDialog('Import matching world patch',reviewBody(patch),async()=>{checkpoint();for(const c of patch.changes)S.pending.set(`${c.table}:${c.key}`,{op:'update',...c});changed();toast('Imported into pending edits. Review & save applies it.');},'Stage imported edits');
});
$('compare').onclick=guarded(async()=>{
  busy('Comparing client world files…');try{S.comparison=await api('compare',{target:$('targets').value});$('syncResult').textContent=S.comparison.summary+'\n'+S.comparison.manifest.entries.slice(0,12).map(e=>`${e.action}: ${e.path}`).join('\n');$('syncApply').disabled=!S.comparison.manifest.entries.length;}finally{busy(null);}
});
$('targets').onchange=()=>{S.comparison=null;$('syncApply').disabled=true;$('syncResult').textContent='';};
$('syncApply').onclick=()=>{
  const comparison=S.comparison,target=$('targets').value;if(!comparison)return;
  showDialog('Apply client world sync',`${comparison.summary}\n\nReference: ${S.config.client}\nTarget: ${S.config.targets[target]}\n\nThis copies the reference world files and removes extra New Towns models that override the reference layout. Original target files are backed up. Close games and the server first.`,async()=>{
    busy('Synchronizing and verifying client world files…');try{const r=await api('sync',{target,id:comparison.id});toast(r.message+'\nBackup: '+r.backup);S.comparison=null;$('syncApply').disabled=true;$('syncResult').textContent='Synchronized and verified.';}finally{busy(null);}
  },'Synchronize client world');
};
$('backups').onclick=guarded(async()=>{
  if(S.pending.size)throw Error('Export or undo pending edits before restoring an earlier save.');
  const ids=await api('backups');if(!ids.length)return toast('No editor saves to restore yet.');
  const div=document.createElement('div');div.textContent='Restore the edited world fields only. Later character progress is preserved. Conflicting later edits stop the restore.';
  const select=document.createElement('select');ids.forEach(id=>select.add(new Option(id,id)));div.append(select);
  showDialog('Restore an earlier world edit',div,async()=>{const r=await api('rollback',{id:select.value});S.pending.clear();S.undo=[];S.redo=[];if(S.data)await loadZone(S.data.zone.ZoneID);await searchRows();toast(r.message+'\nBackup: '+r.backup);},'Restore edited fields');
});
window.addEventListener('beforeunload',e=>{if(S.pending.size||fileDirty()){e.preventDefault();e.returnValue='';}});
await guarded(async()=>{
  S.config=await api('config');$('profile').textContent=S.config.database;$('profile').title=S.config.database+'\n'+S.config.client;$('sourcePath').textContent=S.config.client;
  for(const [id,path] of Object.entries(S.config.targets||{}))$('targets').add(new Option(path,id));
  $('compare').disabled=!$('targets').options.length;
  if(!$('targets').options.length)$('syncResult').textContent='No target clients configured. Launch with --target-client to enable synchronization.';
  renderLayerFilters();renderTables();
  if(!S.config.features?.currencyMerchant){const o=$('listCurrencyMode').querySelector('option[value=item]');o.disabled=true;o.textContent='An item (needs a server with GameCustomCurrencyMerchant)';}
  renderZoneOptions();const first=S.config.zones.find(z=>z.ZoneID===200)||S.config.zones[0];if(first){$('zones').value=first.ZoneID;await loadZone(first.ZoneID);}changed();
})();
