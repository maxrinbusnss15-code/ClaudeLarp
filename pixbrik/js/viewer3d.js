// three.js viewer: renders brick grids (with studs) or raw 3D models, with
// drag-to-orbit, pinch/scroll zoom and button controls. Also voxelises a raw
// model into a brick sculpture.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { PALETTE, nearestColour } from './palette.js';
import { createGrid, set, get } from './build.js';

const BRICK_H = 1.2;  // brick height in stud units
const PLATE_H = 0.4;  // plate height in stud units

export class Viewer {
  constructor(container, { background = 0xefe9dc } = {}) {
    this.container = container;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(background);
    this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 2000);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.shadowMap.enabled = true;
    this.renderer.domElement.style.touchAction = 'none';
    this.renderer.domElement.style.display = 'block';
    container.appendChild(this.renderer.domElement);

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7f6a, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(30, 60, 40);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    this.sun = sun;
    this.scene.add(sun);
    const fill = new THREE.DirectionalLight(0xfff2dd, 0.8);
    fill.position.set(-40, 20, -30);
    this.scene.add(fill);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.enablePan = false;

    this.content = new THREE.Group();
    this.scene.add(this.content);
    this.home = { pos: new THREE.Vector3(0, 0, 50), target: new THREE.Vector3() };

    this._resize = () => this.resize();
    this._ro = new ResizeObserver(this._resize);
    this._ro.observe(container);
    this.resize();
    this.renderer.setAnimationLoop(() => {
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    });
  }

  resize() {
    const w = this.container.clientWidth || 300, h = this.container.clientHeight || 300;
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = '100%';
    this.renderer.domElement.style.height = '100%';
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  clear() {
    this.content.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) [].concat(o.material).forEach((m) => m.dispose());
    });
    this.content.clear();
  }

  // Frame the camera on the current content from a pleasant 3/4 angle.
  frame(dir = new THREE.Vector3(0.55, 0.45, 1)) {
    const box = new THREE.Box3();
    this.content.children.forEach((o) => { if (!o.userData.ground) box.expandByObject(o); });
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const radius = size.length() / 2 || 10;
    const dist = radius / Math.sin(THREE.MathUtils.degToRad(this.camera.fov / 2)) * 0.85;
    this.home.target.copy(center);
    this.home.pos.copy(center).add(dir.normalize().multiplyScalar(dist));
    this.controls.minDistance = radius * 0.6;
    this.controls.maxDistance = radius * 6;
    this.camera.near = radius / 50;
    this.camera.far = radius * 50;
    this.camera.updateProjectionMatrix();
    const s = this.sun.shadow.camera;
    s.left = s.bottom = -radius * 1.5; s.right = s.top = radius * 1.5; s.far = radius * 20;
    this.sun.position.copy(center).add(new THREE.Vector3(radius, radius * 2.5, radius * 1.5));
    this.sun.target.position.copy(center);
    this.sun.target.updateMatrixWorld();
    s.updateProjectionMatrix();
    this.reset();
  }

  reset() {
    this.camera.position.copy(this.home.pos);
    this.controls.target.copy(this.home.target);
    this.controls.update();
  }

  zoom(factor) {
    const t = this.controls.target;
    const v = this.camera.position.clone().sub(t).multiplyScalar(factor);
    const len = THREE.MathUtils.clamp(v.length(), this.controls.minDistance, this.controls.maxDistance);
    this.camera.position.copy(t).add(v.setLength(len));
  }

  rotate(angle) {
    const t = this.controls.target;
    const v = this.camera.position.clone().sub(t).applyAxisAngle(new THREE.Vector3(0, 1, 0), angle);
    this.camera.position.copy(t).add(v);
  }

  snapshot() {
    this.renderer.render(this.scene, this.camera);
    return this.renderer.domElement.toDataURL('image/png');
  }

  // ---- Brick grid rendering -------------------------------------------------

  showGrid(grid, { ground = true } = {}) {
    this.clear();
    const front = grid.studs === 'front';
    const layerH = grid.kind === 'picture' ? PLATE_H : BRICK_H;
    const exposed = [];
    for (let z = 0; z < grid.d; z++)
      for (let y = 0; y < grid.h; y++)
        for (let x = 0; x < grid.w; x++) {
          const c = get(grid, x, y, z);
          if (c < 0) continue;
          const hidden = get(grid, x + 1, y, z) >= 0 && get(grid, x - 1, y, z) >= 0 && get(grid, x, y + 1, z) >= 0 &&
            get(grid, x, y - 1, z) >= 0 && get(grid, x, y, z + 1) >= 0 && get(grid, x, y, z - 1) >= 0;
          if (!hidden) exposed.push([x, y, z, c]);
        }

    const gap = 0.02;
    const boxGeo = front
      ? new THREE.BoxGeometry(1 - gap, 1 - gap, layerH - gap)
      : new THREE.BoxGeometry(1 - gap, BRICK_H - gap, 1 - gap);
    const studGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.2, 16);
    if (front) studGeo.rotateX(Math.PI / 2);
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.35, metalness: 0.0 });
    const studMat = new THREE.MeshStandardMaterial({ roughness: 0.35 });
    const boxes = new THREE.InstancedMesh(boxGeo, mat, exposed.length);
    const studCells = exposed.filter(([x, y, z]) => (front ? get(grid, x, y, z + 1) < 0 : get(grid, x, y + 1, z) < 0));
    const studs = new THREE.InstancedMesh(studGeo, studMat, studCells.length);
    boxes.castShadow = boxes.receiveShadow = studs.castShadow = true;

    const m = new THREE.Matrix4();
    const col = new THREE.Color();
    const ox = grid.w / 2, oy = front ? grid.h / 2 : 0, oz = grid.d / 2;
    const place = ([x, y, z]) =>
      front
        ? new THREE.Vector3(x - ox + 0.5, y - oy + 0.5, z * layerH + layerH / 2)
        : new THREE.Vector3(x - ox + 0.5, y * BRICK_H + BRICK_H / 2, z - oz + 0.5);
    exposed.forEach((cell, i) => {
      const p = place(cell);
      m.makeTranslation(p.x, p.y, p.z);
      boxes.setMatrixAt(i, m);
      boxes.setColorAt(i, col.set(PALETTE[cell[3]].rgb));
    });
    studCells.forEach((cell, i) => {
      const p = place(cell);
      if (front) p.z += layerH / 2 + 0.1; else p.y += BRICK_H / 2 + 0.1;
      m.makeTranslation(p.x, p.y, p.z);
      studs.setMatrixAt(i, m);
      studs.setColorAt(i, col.set(PALETTE[cell[3]].rgb));
    });
    this.content.add(boxes, studs);

    if (front) {
      // backing board behind pictures and signs
      const back = new THREE.Mesh(
        new THREE.BoxGeometry(grid.w + 0.6, grid.h + 0.6, 0.3),
        new THREE.MeshStandardMaterial({ color: 0x2b2722, roughness: 0.6 })
      );
      back.position.z = -0.15;
      back.receiveShadow = true;
      this.content.add(back);
    } else if (ground) {
      this.addGround(Math.max(grid.w, grid.d) * 1.6);
    }
    this.frame(front ? new THREE.Vector3(0.35, 0.15, 1) : new THREE.Vector3(0.9, 0.7, 1));
  }

  addGround(size, y = 0) {
    const g = new THREE.Mesh(
      new THREE.CircleGeometry(size / 2, 64),
      new THREE.MeshStandardMaterial({ color: 0xe0d8c6, roughness: 0.9 })
    );
    g.rotation.x = -Math.PI / 2;
    g.position.y = y - 0.01;
    g.receiveShadow = true;
    g.userData.ground = true;
    this.content.add(g);
  }

  // ---- Raw model display ----------------------------------------------------

  showModel(object) {
    this.clear();
    const box = new THREE.Box3().setFromObject(object);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const scale = 30 / Math.max(size.x, size.y, size.z);
    object.scale.multiplyScalar(scale);
    object.position.sub(center.multiplyScalar(scale));
    object.position.y += (size.y * scale) / 2;
    object.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.content.add(object);
    this.addGround(Math.max(size.x, size.z) * scale * 1.6);
    this.frame(new THREE.Vector3(1, 0.6, 1));
  }

  dispose() {
    this.renderer.setAnimationLoop(null);
    this._ro.disconnect();
    this.clear();
    this.controls.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}

// Wires the − + ← RESET → buttons inside a toolbar element to a viewer.
export function bindToolbar(toolbar, viewer) {
  toolbar.querySelector('[data-act=out]').onclick = () => viewer.zoom(1.2);
  toolbar.querySelector('[data-act=in]').onclick = () => viewer.zoom(1 / 1.2);
  toolbar.querySelector('[data-act=left]').onclick = () => viewer.rotate(-Math.PI / 8);
  toolbar.querySelector('[data-act=right]').onclick = () => viewer.rotate(Math.PI / 8);
  toolbar.querySelector('[data-act=reset]').onclick = () => viewer.reset();
}

// ---- Loading models ---------------------------------------------------------

export async function loadModelFile(file) {
  const name = file.name.toLowerCase();
  const url = URL.createObjectURL(file);
  try {
    if (name.endsWith('.glb') || name.endsWith('.gltf')) {
      const gltf = await new GLTFLoader().loadAsync(url);
      return gltf.scene;
    }
    if (name.endsWith('.obj')) {
      return await new OBJLoader().loadAsync(url);
    }
    throw new Error('Use a .glb, .gltf or .obj file.');
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
}

// A small built-in model (a classic coupe) so the 3D flow works without a file.
export function sampleCar() {
  const g = new THREE.Group();
  const paint = new THREE.MeshStandardMaterial({ color: 0x0b5d2a, roughness: 0.3, metalness: 0.3 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x6b3a1e, roughness: 0.1 });
  const tyre = new THREE.MeshStandardMaterial({ color: 0x1b1b1b, roughness: 0.8 });
  const chrome = new THREE.MeshStandardMaterial({ color: 0xdddddd, roughness: 0.2, metalness: 0.9 });
  const flame = new THREE.MeshStandardMaterial({ color: 0xfbab18, roughness: 0.4 });
  const light = new THREE.MeshStandardMaterial({ color: 0xff2020, roughness: 0.3 });
  const add = (geo, mat, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); g.add(m); return m; };
  add(new THREE.BoxGeometry(10, 1.6, 4.2), paint, 0, 1.6, 0);          // body
  add(new THREE.BoxGeometry(5, 1.4, 3.8), glass, -0.4, 3.1, 0);        // cabin glass
  add(new THREE.BoxGeometry(4.4, 0.25, 3.9), paint, -0.4, 3.9, 0);     // roof
  add(new THREE.BoxGeometry(2.6, 0.08, 1.6), flame, 3, 2.42, 0);       // bonnet flame
  add(new THREE.BoxGeometry(0.1, 0.5, 4), chrome, 5.05, 1.2, 0);       // front bumper
  add(new THREE.BoxGeometry(0.1, 0.5, 4), chrome, -5.05, 1.2, 0);      // rear bumper
  add(new THREE.BoxGeometry(0.12, 0.5, 0.6), light, -5.05, 1.9, 1.5);
  add(new THREE.BoxGeometry(0.12, 0.5, 0.6), light, -5.05, 1.9, -1.5);
  const wheel = new THREE.CylinderGeometry(1, 1, 0.8, 24).rotateX(Math.PI / 2);
  for (const [x, z] of [[3.2, 2], [3.2, -2], [-3.2, 2], [-3.2, -2]]) add(wheel, tyre, x, 1, z);
  return g;
}

// ---- Voxelisation: raw model -> brick sculpture -------------------------------

function textureSampler(texture) {
  const img = texture?.image;
  if (!img || !img.width) return null;
  const c = document.createElement('canvas');
  c.width = Math.min(img.width, 512); c.height = Math.min(img.height, 512);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, c.width, c.height);
  const d = ctx.getImageData(0, 0, c.width, c.height).data;
  return (u, v) => {
    u = ((u % 1) + 1) % 1;
    v = ((v % 1) + 1) % 1;
    if (texture.flipY !== false) v = 1 - v;
    const i = ((Math.floor(v * (c.height - 1)) * c.width) + Math.floor(u * (c.width - 1))) * 4;
    return [d[i] / 255, d[i + 1] / 255, d[i + 2] / 255];
  };
}

// Samples points over every triangle, marks the surface voxels with the colour
// found there, then fills the inside (anything the outside can't flood into).
export function voxelise(object, studsWide = 24, name = 'My 3D sculpture') {
  object.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  const unit = Math.max(size.x, size.z) / studsWide;     // one stud in model units
  const unitY = unit * BRICK_H;
  const w = Math.max(1, Math.ceil(size.x / unit));
  const d = Math.max(1, Math.ceil(size.z / unit));
  const h = Math.max(1, Math.ceil(size.y / unitY));
  const colours = new Map(); // voxel index -> [r,g,b,count]
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), p = new THREE.Vector3();
  const col = new THREE.Color();

  object.traverse((mesh) => {
    if (!mesh.isMesh) return;
    const geo = mesh.geometry;
    const pos = geo.attributes.position;
    const uv = geo.attributes.uv;
    const vcol = geo.attributes.color;
    const mats = [].concat(mesh.material);
    const samplers = mats.map((m) => textureSampler(m.map));
    const index = geo.index;
    const triCount = (index ? index.count : pos.count) / 3;
    const groupOf = (t) => {
      if (!geo.groups.length) return 0;
      const g = geo.groups.find((gr) => t * 3 >= gr.start && t * 3 < gr.start + gr.count);
      return g ? g.materialIndex : 0;
    };
    for (let t = 0; t < triCount; t++) {
      const i0 = index ? index.getX(t * 3) : t * 3;
      const i1 = index ? index.getX(t * 3 + 1) : t * 3 + 1;
      const i2 = index ? index.getX(t * 3 + 2) : t * 3 + 2;
      a.fromBufferAttribute(pos, i0).applyMatrix4(mesh.matrixWorld);
      b.fromBufferAttribute(pos, i1).applyMatrix4(mesh.matrixWorld);
      c.fromBufferAttribute(pos, i2).applyMatrix4(mesh.matrixWorld);
      const longest = Math.max(a.distanceTo(b), b.distanceTo(c), c.distanceTo(a));
      const steps = Math.min(200, Math.ceil((longest / unit) * 2) + 1);
      const mi = groupOf(t);
      const mat = mats[mi] || mats[0];
      const sampler = samplers[mi];
      for (let i = 0; i <= steps; i++)
        for (let j = 0; j <= steps - i; j++) {
          const u = i / steps, v = j / steps, wgt = 1 - u - v;
          p.set(0, 0, 0).addScaledVector(a, wgt).addScaledVector(b, u).addScaledVector(c, v);
          const x = Math.min(w - 1, Math.floor((p.x - box.min.x) / unit));
          const y = Math.min(h - 1, Math.floor((p.y - box.min.y) / unitY));
          const z = Math.min(d - 1, Math.floor((p.z - box.min.z) / unit));
          let rgb;
          if (sampler && uv) {
            const tu = uv.getX(i0) * wgt + uv.getX(i1) * u + uv.getX(i2) * v;
            const tv = uv.getY(i0) * wgt + uv.getY(i1) * u + uv.getY(i2) * v;
            rgb = sampler(tu, tv);
            if (mat.color) { rgb[0] *= mat.color.r; rgb[1] *= mat.color.g; rgb[2] *= mat.color.b; }
          } else if (vcol) {
            rgb = [vcol.getX(i0) * wgt + vcol.getX(i1) * u + vcol.getX(i2) * v,
              vcol.getY(i0) * wgt + vcol.getY(i1) * u + vcol.getY(i2) * v,
              vcol.getZ(i0) * wgt + vcol.getZ(i1) * u + vcol.getZ(i2) * v];
          } else {
            col.copy(mat.color || new THREE.Color(0xa0a19f)).convertLinearToSRGB();
            rgb = [col.r, col.g, col.b];
          }
          const k = x + w * (y + h * z);
          const acc = colours.get(k) || [0, 0, 0, 0];
          acc[0] += rgb[0]; acc[1] += rgb[1]; acc[2] += rgb[2]; acc[3]++;
          colours.set(k, acc);
        }
    }
  });

  // Flood the outside from the grid border; whatever it can't reach is solid.
  const solid = new Uint8Array(w * h * d);
  colours.forEach((_, k) => { solid[k] = 1; });
  const outside = new Uint8Array(w * h * d);
  const stack = [];
  const push = (x, y, z) => {
    if (x < 0 || y < 0 || z < 0 || x >= w || y >= h || z >= d) return;
    const k = x + w * (y + h * z);
    if (solid[k] || outside[k]) return;
    outside[k] = 1; stack.push(k);
  };
  for (let x = 0; x < w; x++) for (let y = 0; y < h; y++) { push(x, y, 0); push(x, y, d - 1); }
  for (let x = 0; x < w; x++) for (let z = 0; z < d; z++) { push(x, 0, z); push(x, h - 1, z); }
  for (let y = 0; y < h; y++) for (let z = 0; z < d; z++) { push(0, y, z); push(w - 1, y, z); }
  while (stack.length) {
    const k = stack.pop();
    const x = k % w, y = Math.floor(k / w) % h, z = Math.floor(k / (w * h));
    push(x + 1, y, z); push(x - 1, y, z); push(x, y + 1, z); push(x, y - 1, z); push(x, y, z + 1); push(x, y, z - 1);
  }

  // grid uses (x, y = height, z) with studs on top
  const grid = createGrid(w, h, d, { kind: 'sculpture', name, studs: 'up' });
  const all = PALETTE.map((q) => q.index);
  const inner = PALETTE.find((q) => q.name === 'Light Bluish Gray').index;
  for (let k = 0; k < w * h * d; k++) {
    if (outside[k]) continue;
    const x = k % w, y = Math.floor(k / w) % h, z = Math.floor(k / (w * h));
    const acc = colours.get(k);
    const ci = acc ? nearestColour([(acc[0] / acc[3]) * 255, (acc[1] / acc[3]) * 255, (acc[2] / acc[3]) * 255], all) : inner;
    set(grid, x, y, z, ci);
  }
  return grid;
}
