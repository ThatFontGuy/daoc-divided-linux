import * as THREE from 'three';

// NetImmerse 4.x particle systems (weapon glows, flames, sparks) from nif_static.particle_systems specs
// (glTF extras.nif_particles), simulated on the CPU. Mirrors the new client's game/nif_particles.gd:
// direction = emitter up axis tilted by the declination and turned by the planar angle, cone = declination
// variation, colour keys over life, grow/fade, gravity, spin. Units are metres, Y up.

const VERTEX = `
attribute vec4 tint; attribute float size; attribute float angle;
uniform float scale; varying vec4 vTint; varying float vAngle;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = size * scale / max(-mv.z, 0.001);
  vTint = tint; vAngle = angle;
}`;
// Blend modes as the client's alpha properties (see nif_static.particle_blend).
const FRAGMENT = {
  mix: 'gl_FragColor = t * vTint;',
  add: 'gl_FragColor = t * vTint;',
  invdest: 'gl_FragColor = vec4(t.rgb * vTint.rgb, t.a * vTint.a);',
  invdest_add: 'gl_FragColor = vec4(t.rgb * vTint.rgb, 1.0);',
  screen: 'vec3 c = t.rgb * vTint.rgb; float m = max(max(c.r, c.g), max(c.b, 0.001)); gl_FragColor = vec4(c / m, m * t.a * vTint.a);',
  multiply: 'float a = t.a * vTint.a; gl_FragColor = vec4(clamp(t.rgb * vTint.rgb + vec3(1.0 - a), 0.0, 1.0), 1.0);',
};
function fragment(blend, textured) {
  return `uniform sampler2D map; varying vec4 vTint; varying float vAngle;
void main() {
  vec2 p = gl_PointCoord - 0.5; float c = cos(vAngle), s = sin(vAngle);
  vec2 uv = vec2(c * p.x - s * p.y, s * p.x + c * p.y) + 0.5;
  if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) discard;
  vec4 t = ${textured ? 'texture2D(map, uv)' : 'vec4(1.0, 1.0, 1.0, 1.0 - smoothstep(0.2, 0.5, length(p)))'};
  ${FRAGMENT[blend] || FRAGMENT.mix}
}`;
}
function blending(material, blend) {
  material.blending = THREE.CustomBlending;
  if (blend === 'add') { material.blendSrc = THREE.SrcAlphaFactor; material.blendDst = THREE.OneFactor; }
  else if (blend === 'invdest_add') { material.blendSrc = THREE.OneFactor; material.blendDst = THREE.OneFactor; }
  else if (blend === 'invdest') { material.blendSrc = THREE.OneFactor; material.blendDst = THREE.OneMinusSrcAlphaFactor; }
  else if (blend === 'multiply') { material.blendSrc = THREE.DstColorFactor; material.blendDst = THREE.ZeroFactor; }
  else { material.blendSrc = THREE.SrcAlphaFactor; material.blendDst = THREE.OneMinusSrcAlphaFactor; }
}

export class NifParticleSystem extends THREE.Points {
  constructor(spec, texture) {
    const life = Math.max(Number(spec.lifetime) || 0, 0.05), lifeRandom = Number(spec.lifetime_random) || 0;
    const count = Math.min(512, Math.max(1, Number(spec.max_particles) || 0, Math.ceil((Number(spec.emit_rate) || 0) * (life + lifeRandom))));
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
    geometry.setAttribute('tint', new THREE.BufferAttribute(new Float32Array(count * 4), 4));
    geometry.setAttribute('size', new THREE.BufferAttribute(new Float32Array(count), 1));
    geometry.setAttribute('angle', new THREE.BufferAttribute(new Float32Array(count), 1));
    const material = new THREE.ShaderMaterial({uniforms: {map: {value: texture}, scale: {value: 500}}, vertexShader: VERTEX,
      fragmentShader: fragment(spec.blend, Boolean(texture)), transparent: true, depthWrite: false});
    blending(material, spec.blend);
    super(geometry, material);
    this.frustumCulled = false;
    this.spec = spec; this.life = life; this.lifeRandom = lifeRandom; this.count = count;
    this.pool = Array.from({length: count}, () => ({age: 0, life: 0, p: new THREE.Vector3(), v: new THREE.Vector3(), angle: 0, spin: 0}));
    this.alive = 0; this.carry = 0;
    const b = spec.emitter.basis, o = spec.emitter.origin;
    this.emitter = new THREE.Matrix4().set(b[0][0], b[0][1], b[0][2], o[0], b[1][0], b[1][1], b[1][2], o[1], b[2][0], b[2][1], b[2][2], o[2], 0, 0, 0, 1);
    this.basis = new THREE.Matrix3().setFromMatrix4(this.emitter);
    this.origin = new THREE.Vector3(...o);
    this.direction = new THREE.Vector3(0, 1, 0).applyAxisAngle(new THREE.Vector3(1, 0, 0), Number(spec.declination) || 0)
      .applyAxisAngle(new THREE.Vector3(0, 1, 0), Number(spec.planar_angle) || 0);
    this.gravity = new THREE.Vector3();
    this.colors = null; this.growfade = null; this.spinSpeed = 0;
    for (const m of spec.modifiers || []) {
      if (m.type === 'gravity') {
        const dir = m.kind === 'spherical' ? new THREE.Vector3(...m.position).sub(this.origin).normalize() : new THREE.Vector3(...m.direction);
        this.gravity.addScaledVector(dir, Number(m.force) || 0);
      } else if (m.type === 'color' && m.keys?.length) this.colors = [...m.keys].sort((x, y) => x[0] - y[0]);
      else if (m.type === 'growfade') this.growfade = {grow: Math.min(1, (Number(m.grow) || 0) / life), fade: Math.min(1, (Number(m.fade) || 0) / life)};
      else if (m.type === 'rotation') this.spinSpeed = Number(m.speed) || 0;
    }
    this.baseSize = spec.quad ? Math.max(...spec.quad) : (Number(spec.size) || 0.1) * 2;
    // Already burning when it comes into view, like the client's preprocess.
    for (let t = 0; t < life + lifeRandom; t += 1 / 30) this.update(1 / 30);
  }
  emit() {
    if (this.alive >= this.count) return;
    const s = this.spec, q = this.pool[this.alive++];
    q.age = 0; q.life = Math.max(0.05, this.life + (Math.random() * 2 - 1) * this.lifeRandom);
    const box = s.box || [0, 0, 0];
    q.p.set((Math.random() - 0.5) * box[0], (Math.random() - 0.5) * box[1], (Math.random() - 0.5) * box[2]).applyMatrix4(this.emitter);
    // A random direction inside the cone around the emission direction.
    const spread = Number(s.declination_variation) || 0, theta = Math.acos(1 - Math.random() * (1 - Math.cos(spread))), phi = Math.random() * Math.PI * 2;
    const axis = this.direction.clone(), ortho = Math.abs(axis.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
    const u = ortho.cross(axis).normalize(), w = axis.clone().cross(u);
    const dir = axis.multiplyScalar(Math.cos(theta)).addScaledVector(u, Math.sin(theta) * Math.cos(phi)).addScaledVector(w, Math.sin(theta) * Math.sin(phi));
    const speed = Math.max(0, (Number(s.speed) || 0) + (Math.random() * 2 - 1) * (Number(s.speed_random) || 0));
    q.v.copy(dir.applyMatrix3(this.basis).normalize().multiplyScalar(speed));
    q.angle = Math.random() * Math.PI * 2; q.spin = this.spinSpeed;
  }
  tint(t, out) {
    if (!this.colors) return out.set(1, 1, 1, 1);
    const k = this.colors;
    if (t <= k[0][0]) return out.set(...k[0][1]);
    for (let i = 1; i < k.length; i++) if (t <= k[i][0]) {
      const a = k[i - 1], b = k[i], f = (t - a[0]) / Math.max(b[0] - a[0], 1e-6);
      return out.set(...a[1].map((v, j) => v + (b[1][j] - v) * f));
    }
    return out.set(...k[k.length - 1][1]);
  }
  update(dt, viewportScale) {
    if (viewportScale) this.material.uniforms.scale.value = viewportScale;
    this.carry += (Number(this.spec.emit_rate) || 0) * dt;
    while (this.carry >= 1) { this.carry -= 1; this.emit(); }
    const pos = this.geometry.attributes.position, tint = this.geometry.attributes.tint, size = this.geometry.attributes.size, angle = this.geometry.attributes.angle;
    const c = new THREE.Vector4();
    for (let i = 0; i < this.alive;) {
      const q = this.pool[i];
      q.age += dt;
      if (q.age >= q.life) { this.pool[i] = this.pool[--this.alive]; this.pool[this.alive] = q; continue; }
      q.v.addScaledVector(this.gravity, dt); q.p.addScaledVector(q.v, dt); q.angle += q.spin * dt;
      const t = q.age / q.life;
      let scale = 1;
      if (this.growfade) {
        if (this.growfade.grow > 0 && t < this.growfade.grow) scale = t / this.growfade.grow;
        if (this.growfade.fade > 0 && t > 1 - this.growfade.fade) scale = Math.min(scale, (1 - t) / this.growfade.fade);
      }
      this.tint(t, c);
      pos.setXYZ(i, q.p.x, q.p.y, q.p.z); tint.setXYZW(i, c.x, c.y, c.z, c.w); size.setX(i, this.baseSize * scale); angle.setX(i, q.angle);
      i++;
    }
    this.geometry.setDrawRange(0, this.alive);
    pos.needsUpdate = tint.needsUpdate = size.needsUpdate = angle.needsUpdate = true;
  }
  dispose() { this.geometry.dispose(); this.material.dispose(); }
}

// Every particle system of one converted effect glTF.
export async function loadParticles(gltf, base) {
  const specs = gltf.parser.json.extras?.nif_particles || [];
  const loader = new THREE.TextureLoader(), systems = [];
  for (const spec of specs) {
    let texture = null;
    if (spec.texture) {
      try { texture = await loader.loadAsync(`${base}textures/${spec.texture}.png`); texture.colorSpace = THREE.SRGBColorSpace; }
      catch { texture = null; }
    }
    systems.push(new NifParticleSystem(spec, texture));
  }
  return systems;
}

// glTF materials named "nifmat:<n>" carry their NetImmerse settings in extras.nif_materials[n] (nif_static):
// additive glows, alpha blend / cut-outs and camera-facing cards. three.js only sees the plain PBR part.
export function applyNifMaterials(gltf) {
  const specs = gltf.parser.json.extras?.nif_materials || [], billboards = [];
  gltf.scene.traverse(node => {
    if (!node.isMesh) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    const fixed = materials.map(m => {
      const spec = specs[Number(/^nifmat:(\d+)$/.exec(m.name || '')?.[1] ?? -1)];
      if (!spec) return m;
      if (spec.billboard) billboards.push(node);
      if (spec.alpha === 'add' || spec.alpha === 'screen' || spec.alpha === 'invdest_add') {
        // Glow cards: unlit, black adds nothing; the emissive colour tints a grey glow texture.
        const e = spec.emissive || [0, 0, 0], tint = Math.max(...e) > 0.05 ? e : (spec.tint || [1, 1, 1]);
        const glow = new THREE.MeshBasicMaterial({map: m.map, color: new THREE.Color(...tint), transparent: true, depthWrite: false,
          blending: THREE.AdditiveBlending, side: THREE.DoubleSide, opacity: spec.opacity ?? 1});
        m.dispose();
        return glow;
      }
      if (spec.alpha === 'blend') { m.transparent = true; m.depthWrite = false; m.opacity = spec.opacity ?? 1; }
      if (spec.cut > 0) m.alphaTest = spec.cut;
      if (spec.double_sided) m.side = THREE.DoubleSide;
      return m;
    });
    node.material = Array.isArray(node.material) ? fixed : fixed[0];
  });
  return billboards;
}

// Turn camera-facing cards toward the camera (world orientation = the camera's).
const parentQuat = new THREE.Quaternion();
export function faceCamera(nodes, camera) {
  for (const node of nodes) {
    node.parent?.getWorldQuaternion(parentQuat);
    node.quaternion.copy(parentQuat.invert().multiply(camera.quaternion));
  }
}
