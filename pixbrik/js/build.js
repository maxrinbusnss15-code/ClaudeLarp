// A "build" is a voxel grid of palette indices. Pictures are one layer deep,
// signs are two layers (backing + raised letters), sculptures are full 3D.
// This module turns a grid into a parts list, size, build time and price.

import { PALETTE } from './palette.js';

export const STUD_CM = 0.8;      // one stud pitch
export const BRICK_CM = 0.96;    // brick height
export const PLATE_CM = 0.32;    // plate height

export function createGrid(w, h, d, { kind = 'picture', name = 'My build', studs = 'front' } = {}) {
  return { w, h, d, kind, name, studs, data: new Int16Array(w * h * d).fill(-1) };
}

export const idx = (g, x, y, z) => x + g.w * (y + g.h * z);
export const get = (g, x, y, z) =>
  x < 0 || y < 0 || z < 0 || x >= g.w || y >= g.h || z >= g.d ? -1 : g.data[idx(g, x, y, z)];
export const set = (g, x, y, z, c) => { g.data[idx(g, x, y, z)] = c; };

export function cloneGrid(g) {
  return { ...g, data: new Int16Array(g.data) };
}

// Hollow version of a 3D grid: keeps the outer shell, the bottom two layers
// and a column every 4 studs so the build stays strong.
export function hollowGrid(g) {
  if (g.kind !== 'sculpture') return g;
  const out = cloneGrid(g);
  for (let z = 0; z < g.d; z++)
    for (let y = 2; y < g.h; y++)
      for (let x = 0; x < g.w; x++) {
        if (get(g, x, y, z) < 0) continue;
        const enclosed = [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1],[1,1,0],[-1,-1,0],[0,0,2],[0,0,-2],[2,0,0],[-2,0,0]]
          .every(([a, b, c]) => get(g, x + a, y + b, z + c) >= 0);
        const support = x % 4 === 0 && z % 4 === 0;
        if (enclosed && !support) set(out, x, y, z, -1);
      }
  return out;
}

// Greedy row merge: runs of the same colour become 1x4, 1x3, 1x2 and 1x1 pieces.
// Returns the list of placed pieces (used for the parts list and the build guide).
export function pieces(g) {
  const isPlate = g.kind === 'picture';
  const list = [];
  for (let z = 0; z < g.d; z++)
    for (let y = 0; y < g.h; y++) {
      // Alternate the run direction every layer so seams overlap (stronger builds).
      let x = 0;
      while (x < g.w) {
        const c = get(g, x, y, z);
        if (c < 0) { x++; continue; }
        let run = 1;
        while (x + run < g.w && get(g, x + run, y, z) === c) run++;
        let pos = x;
        let left = run;
        const first = (y + z) % 2 === 1 && left > 1 ? 1 : 0; // stagger
        if (first) { list.push({ x: pos, y, z, len: 1, colour: c, plate: isPlate }); pos += 1; left -= 1; }
        while (left > 0) {
          const len = Math.min(4, left === 5 ? 3 : left);
          list.push({ x: pos, y, z, len, colour: c, plate: isPlate });
          pos += len; left -= len;
        }
        x += run;
      }
    }
  return list;
}

const UNIT_PRICE = { 1: 0.05, 2: 0.07, 3: 0.09, 4: 0.11 };

export function partName(p) {
  return `${p.plate ? 'Plate' : 'Brick'} 1 x ${p.len}`;
}

export function billOfMaterials(g) {
  const map = new Map();
  for (const p of pieces(g)) {
    const key = `${partName(p)}|${p.colour}`;
    const row = map.get(key) || { part: partName(p), colour: PALETTE[p.colour], len: p.len, plate: p.plate, qty: 0 };
    row.qty++;
    map.set(key, row);
  }
  const rows = [...map.values()].sort((a, b) => a.colour.name.localeCompare(b.colour.name) || a.len - b.len);
  if (g.kind !== 'sculpture') {
    const plates = Math.ceil(g.w / 16) * Math.ceil(g.h / 16);
    rows.push({ part: 'Baseplate 16 x 16', colour: { name: 'Black', rgb: '#1b1b1b' }, len: 16, plate: true, qty: plates, base: true });
  }
  return rows;
}

export function stats(g) {
  const bom = billOfMaterials(g);
  const parts = bom.reduce((s, r) => s + r.qty, 0);
  const colours = new Set(bom.filter((r) => !r.base).map((r) => r.colour.name)).size;
  const price = bom.reduce((s, r) => {
    const unit = r.base ? 1.5 : UNIT_PRICE[r.len] * (r.plate ? 0.8 : 1);
    return s + unit * r.qty;
  }, 0);
  let size;
  if (g.kind === 'sculpture') {
    size = [g.w * STUD_CM, g.d * STUD_CM, g.h * BRICK_CM];
  } else {
    size = [g.w * STUD_CM, g.h * STUD_CM, g.kind === 'sign' ? BRICK_CM * 2 : PLATE_CM * 2];
  }
  const minutes = Math.max(10, Math.round((parts * 12) / 60));
  return { bom, parts, colours, price, size, minutes };
}

export function formatSize([a, b, c]) {
  return `${Math.round(a)} × ${Math.round(b)} × ${Math.max(1, Math.round(c))} cm`;
}

export function formatTime(min) {
  return min < 90 ? `${min} min` : `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')}`;
}

export const euro = (n) => `€${n.toFixed(2)}`;
