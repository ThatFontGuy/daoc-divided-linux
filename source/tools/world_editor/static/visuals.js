import * as THREE from 'three';
import {GLTFLoader} from './vendor/loaders/GLTFLoader.js';
import {clone as cloneSkeleton} from './vendor/utils/SkeletonUtils.js';

// Invisible boxes stand in for NPC models when picking: raycasting a skinned mesh skins every vertex on the CPU.
const HIT_BOX=new THREE.BoxGeometry(1,1,1),HIT_MATERIAL=new THREE.MeshBasicMaterial({visible:false});
const ANIMATED=30;

// Draw real client assets. Placement/raycast authority stays in the collision layer.
export class WorldVisuals {
  constructor(scene, camera, labels, getState, local, values) {
    this.camera=camera;this.labels=labels;this.state=getState;this.local=local;this.values=values;
    this.scenery=new THREE.Group();this.people=new THREE.Group();scene.add(this.scenery,this.people);
    this.loader=new GLTFLoader();this.resources=new Map();this.instances=new Map();this.tags=new Map();
    this.serial=0;this.lastUpdate=0;this.clip=new THREE.Plane(new THREE.Vector3(0,-1,0),1e8);
    this.show=true;this.trees=true;this.names=true;this.cutaway=false;this.pickables=[];
  }
  clear() {
    this.serial++;for(const o of this.scenery.children)o.dispose?.();this.scenery.clear();for(const r of this.instances.values())this.disposeProxy(r.group);this.people.clear();this.labels.replaceChildren();
    // Cached model resources own shared geometry/materials; dispose them once, after clones are removed.
    for(const p of this.resources.values())p.then(g=>g.scene.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const m of (Array.isArray(o.material)?o.material:[o.material])){for(const v of Object.values(m))if(v?.isTexture)v.dispose();m.dispose();}}})).catch(()=>{});
    this.resources.clear();this.instances.clear();this.tags.clear();this.pickables=[];this.pickablesDirty=false;this.manifest=null;this.labelEntities=[];this.lastUpdate=0;
  }
  resource(file) {
    const url=this.base+file;
    if(!this.resources.has(url)){
      const serial=this.serial;
      const promise=this.loader.loadAsync(url).then(g=>{
        if(serial!==this.serial)return g;
        g.scene.traverse(o=>{if(o.isMesh){
          const colors=o.geometry.attributes.color;
          if(file.startsWith('scenery/')&&colors){for(let i=0;i<colors.count;i++)colors.setXYZ(i,Math.max(.4,colors.getX(i)),Math.max(.4,colors.getY(i)),Math.max(.4,colors.getZ(i)));colors.needsUpdate=true;}
          for(const m of (Array.isArray(o.material)?o.material:[o.material])){m.clippingPlanes=[this.clip];m.clipShadows=true;if(m.map)m.map.anisotropy=4;}
        }});
        return g;
      });this.resources.set(url,promise);
    }
    return this.resources.get(url);
  }
  async load(manifest,base,onProgress) {
    this.clear();this.manifest=manifest;this.base=base;const serial=this.serial;
    const grouped=new Map();for(const fixture of manifest.fixtures){if(!grouped.has(fixture.model))grouped.set(fixture.model,[]);grouped.get(fixture.model).push(fixture);}
    let done=0;const entries=[...grouped];let next=0;
    const worker=async()=>{while(next<entries.length){const [key,placements]=entries[next++];const model=manifest.models[key];if(!model?.file)continue;
      try{
        const gltf=await this.resource(model.file);if(serial!==this.serial)return;
        gltf.scene.updateMatrixWorld(true);
        gltf.scene.traverse(node=>{
          if(!node.isMesh)return;
          const inst=new THREE.InstancedMesh(node.geometry,node.material,placements.length);const matrix=new THREE.Matrix4();
          for(let i=0;i<placements.length;i++){
            const p=placements[i];matrix.identity();
            if(p.basis){const a=p.basis;matrix.set(a[0],a[3],a[6],0,a[1],a[4],a[7],0,a[2],a[5],a[8],0,0,0,0,1);}
            else matrix.makeRotationY((p.yaw||0)*Math.PI/180);
            matrix.scale(new THREE.Vector3(p.scale||1,p.scale||1,p.scale||1));matrix.setPosition(...p.pos);matrix.multiply(node.matrixWorld);inst.setMatrixAt(i,matrix);
            if(node.morphTargetInfluences?.length)inst.setMorphAt(i,node);
          }
          if(inst.morphTexture)inst.morphTexture.needsUpdate=true;
          inst.computeBoundingSphere();inst.userData={scenery:true,name:model.name,source:model.source,placements,
            tree:/tree|elm|oak|pine|birch|willow|fir_|beech|bush|grass|shroom|spruce|briar|trunk|hedge|palm|fern|reed/i.test(model.name)};
          this.scenery.add(inst);
        });
      }catch(e){console.warn('Scenery preview unavailable',model.name,e.message);}
      onProgress?.(`Drawing buildings and scenery ${++done}/${entries.length}…`);
    }};
    await Promise.all(Array.from({length:4},worker));this.updateVisibility();return serial===this.serial;
  }
  updateVisibility(){this.scenery.visible=this.show;for(const o of this.scenery.children)o.visible=this.trees||!o.userData.tree;this.people.visible=this.show;}
  disposeProxy(group){group.traverse(o=>{if(o.userData.proxy)o.traverse(n=>{if(n.isMesh){n.geometry.dispose();n.material.dispose();}});});}
  options({show=this.show,trees=this.trees,names=this.names,cutaway=this.cutaway}){this.show=show;this.trees=trees;this.names=names;this.cutaway=cutaway;this.updateVisibility();}
  proxy(entity) {
    const group=new THREE.Group(),v=this.values(entity),color=v.Realm?0x60abc9:0xbc966b;
    if(entity.table==='Mob'){
      const body=new THREE.Mesh(new THREE.CapsuleGeometry(.26,.75,4,6),new THREE.MeshStandardMaterial({color}));body.position.y=.9;
      const head=new THREE.Mesh(new THREE.SphereGeometry(.20,8,6),body.material);head.position.y=1.6;group.add(body,head);
    }else{
      const box=new THREE.Mesh(new THREE.BoxGeometry(entity.table==='Door'?1.2:.8,entity.table==='Door'?2:.8,.4),new THREE.MeshStandardMaterial({color:entity.table==='Door'?0xcb9b62:0x76a8e4}));box.position.y=entity.table==='Door'?1:.4;group.add(box);
    }
    group.userData.proxy=true;return group;
  }
  async attach(entity,serial) {
    const id=`${entity.table}:${entity.key}`;if(this.instances.has(id))return;
    const v=this.values(entity),info=this.manifest?.figures[String((v.Model||0)&0x7fff)];
    const group=new THREE.Group();this.people.add(group);const record={group,entity,mixer:null,signature:`${v.Model}:${v.Size}:${v.Realm}`};this.instances.set(id,record);
    let model;
    try{
      if(entity.table==='Mob'&&info?.file){
        const gltf=await this.resource(info.file);if(serial!==this.serial||this.instances.get(id)!==record)return;
        model=cloneSkeleton(gltf.scene);model.scale.setScalar((v.Size||50)/50*(info.scale||1));
        const idle=gltf.animations.find(a=>a.name==='idle')||gltf.animations[0];
        if(idle){record.mixer=new THREE.AnimationMixer(model);record.mixer.clipAction(idle).play();record.mixer.update(.01);}
        record.preview='Client model';
      }else{model=this.proxy(entity);record.preview='Appearance unavailable: editor placeholder';}
    }catch(e){model=this.proxy(entity);record.preview='Appearance unavailable: editor placeholder';}
    if(serial!==this.serial)return;
    group.add(model);group.traverse(o=>{if(o.isMesh)o.userData.entity=entity;});
    // Skinned mesh bind-pose bounds can be far above the animated head; use a stable editor label height.
    record.height=Math.max(.9,Math.min(8,1.9*(v.Size||50)/50));
    const hit=new THREE.Mesh(HIT_BOX,HIT_MATERIAL),w=Math.max(.6,record.height*.45);hit.scale.set(w,record.height,w);hit.position.y=record.height/2;hit.userData.entity=entity;
    group.add(hit);record.hit=hit;this.pickablesDirty=true;
  }
  tick(time,dt,entities,selected,cutHeight) {
    this.clip.constant=this.cutaway?cutHeight:1e8;
    if(time-this.lastUpdate>.3){
      this.lastUpdate=time;
      const nearby=entities.map(e=>({e,id:`${e.table}:${e.key}`,p:this.local(this.values(e))})).map(o=>({...o,d:this.camera.position.distanceTo(o.p)}))
        .filter(o=>selected.has(o.id)||o.d<200).sort((a,b)=>(selected.has(b.id)?1:0)-(selected.has(a.id)?1:0)||a.d-b.d).slice(0,100);
      const keep=new Set(nearby.map(o=>o.id));
      for(const [id,r] of this.instances){const v=this.values(r.entity);if(!keep.has(id)||r.signature!==`${v.Model}:${v.Size}:${v.Realm}`){this.people.remove(r.group);r.mixer?.stopAllAction();this.disposeProxy(r.group);this.instances.delete(id);this.pickablesDirty=true;}}
      // Only the nearest models animate; the rest hold their idle pose.
      nearby.forEach((o,i)=>{const r=this.instances.get(o.id);if(r)r.animate=i<ANIMATED;});
      // Other world layers (bind points, zone points, waypoints…) are drawn as markers only.
      if(this.show)for(const {e} of nearby)if(e.table==='Mob'||e.table==='WorldObject'||e.table==='Door')this.attach(e,this.serial);
      this.labelEntities=nearby;
    }
    if(this.pickablesDirty){this.pickablesDirty=false;this.pickables=[...this.instances.values()].map(r=>r.hit).filter(Boolean);}
    for(const r of this.instances.values()){const v=this.values(r.entity);r.group.position.copy(this.local(v));r.group.rotation.y=-(v.Heading||0)/4096*Math.PI*2;if(r.animate)r.mixer?.update(dt);}
    const keep=new Set();let count=0;const occupied=[];
    for(const item of this.labelEntities||[]){
      const chosen=selected.has(item.id);if(!this.names&&!chosen)continue;if(!chosen&&(item.d>110||count>35))continue;
      const p=this.local(this.values(item.e));p.y+=(this.instances.get(item.id)?.height||2)+.6;p.project(this.camera);
      if(p.z<-1||p.z>1||Math.abs(p.x)>1.1||Math.abs(p.y)>1.1)continue;
      const x=(p.x*.5+.5)*this.labels.clientWidth,y=(-p.y*.5+.5)*this.labels.clientHeight;
      if(!chosen&&occupied.some(q=>Math.abs(q.x-x)<95&&Math.abs(q.y-y)<28))continue;
      occupied.push({x,y});count++;keep.add(item.id);
      let tag=this.tags.get(item.id);if(!tag){tag=document.createElement('button');tag.className='worldLabel';tag.onclick=e=>{e.stopPropagation();this.onSelect?.(item.e,e.ctrlKey);};this.labels.append(tag);this.tags.set(item.id,tag);}
      const v=this.values(item.e),text=`${v.Name||item.e.table}
${v.Guild||''}`;
      if(tag.dataset.text!==text){tag.dataset.text=text;tag.replaceChildren(document.createTextNode(v.Name||item.e.table));
        if(v.Guild){const small=document.createElement('small');small.textContent=v.Guild;tag.append(small);}}
      if(tag.classList.contains('selected')!==chosen)tag.classList.toggle('selected',chosen);tag.style.transform=`translate(${x}px,${y}px) translate(-50%,-100%)`;
      tag.title=this.instances.get(item.id)?.preview||'NPC position';
    }
    for(const [id,t] of this.tags)if(!keep.has(id)){t.remove();this.tags.delete(id);}
  }
}
