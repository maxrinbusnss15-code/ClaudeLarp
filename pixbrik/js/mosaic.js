// Photo -> flat brick mosaic. Everything runs on the device in a <canvas>.

import { PALETTE, nearestColour, hexToRgb } from './palette.js';
import { createGrid, set } from './build.js';

export const COLOUR_MODES = {
  full: { label: 'Full colour', indices: PALETTE.map((c) => c.index) },
  warm: {
    label: 'Portrait tones',
    indices: ['Black', 'Dark Brown', 'Reddish Brown', 'Dark Orange', 'Medium Dark Flesh', 'Nougat', 'Light Flesh',
      'Tan', 'Dark Tan', 'White', 'Light Bluish Gray', 'Dark Bluish Gray', 'Dark Red', 'Red', 'Bright Pink', 'Light Pink',
      'Dark Blue', 'Sand Blue', 'Dark Green'].map((n) => PALETTE.find((c) => c.name === n).index),
  },
  mono: {
    label: 'Black & white',
    indices: ['Black', 'Dark Bluish Gray', 'Light Bluish Gray', 'White'].map((n) => PALETTE.find((c) => c.name === n).index),
  },
  sepia: {
    label: 'Sepia',
    indices: ['Dark Brown', 'Reddish Brown', 'Dark Tan', 'Tan', 'Light Flesh', 'White'].map((n) => PALETTE.find((c) => c.name === n).index),
  },
};

export const SIZES = [
  { key: 'efficient', label: 'Efficient', note: 'Fewest pieces · quick build', studs: 24 },
  { key: 'balanced', label: 'Balanced', note: 'Balanced photo detail and size', studs: 32 },
  { key: 'detailed', label: 'Detailed', note: 'More photo detail · larger frame', studs: 48 },
];

export function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('That file could not be read as an image.'));
    img.src = url;
  });
}

// Draw the photo into a square canvas using the user's framing (zoom + pan).
export function frameImage(img, { zoom = 1, panX = 0, panY = 0 }, size = 512) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d');
  const base = Math.max(size / img.width, size / img.height) * zoom;
  const w = img.width * base, h = img.height * base;
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, size, size);
  ctx.drawImage(img, (size - w) / 2 + panX * size, (size - h) / 2 + panY * size, w, h);
  return c;
}

// Cheap on-device background removal: flood-fill from the edges across pixels
// similar to the border colour. Works well on plain backdrops.
function backgroundMask(data, w, h, tolerance) {
  const mask = new Uint8Array(w * h);
  const border = [];
  for (let x = 0; x < w; x++) border.push(x, x + (h - 1) * w);
  for (let y = 0; y < h; y++) border.push(y * w, y * w + w - 1);
  let r = 0, g = 0, b = 0;
  for (const i of border) { r += data[i * 4]; g += data[i * 4 + 1]; b += data[i * 4 + 2]; }
  r /= border.length; g /= border.length; b /= border.length;
  const tol2 = tolerance * tolerance;
  const stack = [...border];
  while (stack.length) {
    const i = stack.pop();
    if (mask[i]) continue;
    const dr = data[i * 4] - r, dg = data[i * 4 + 1] - g, db = data[i * 4 + 2] - b;
    if (dr * dr + dg * dg + db * db > tol2) continue;
    mask[i] = 1;
    const x = i % w, y = (i / w) | 0;
    if (x > 0) stack.push(i - 1);
    if (x < w - 1) stack.push(i + 1);
    if (y > 0) stack.push(i - w);
    if (y < h - 1) stack.push(i + w);
  }
  return mask;
}

export function makeMosaic(framed, opts) {
  const {
    studs = 32, brightness = 0, contrast = 0, saturation = 0, dither = false,
    colourMode = 'full', removeBg = false, bgTolerance = 60, bgColour = '#fffffa', name = 'My brick picture',
  } = opts;
  const c = document.createElement('canvas');
  c.width = c.height = studs;
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(framed, 0, 0, studs, studs);
  const img = ctx.getImageData(0, 0, studs, studs);
  const px = img.data;
  const mask = removeBg ? backgroundMask(px, studs, studs, bgTolerance) : null;

  // Colour adjustments
  const cf = (259 * (contrast + 255)) / (255 * (259 - contrast));
  const buf = new Float32Array(studs * studs * 3);
  for (let i = 0; i < studs * studs; i++) {
    let r = px[i * 4], g = px[i * 4 + 1], b = px[i * 4 + 2];
    const grey = 0.299 * r + 0.587 * g + 0.114 * b;
    const s = 1 + saturation / 100;
    r = grey + (r - grey) * s; g = grey + (g - grey) * s; b = grey + (b - grey) * s;
    r = cf * (r - 128) + 128 + brightness; g = cf * (g - 128) + 128 + brightness; b = cf * (b - 128) + 128 + brightness;
    buf[i * 3] = r; buf[i * 3 + 1] = g; buf[i * 3 + 2] = b;
  }

  const allowed = COLOUR_MODES[colourMode].indices;
  const bgIndex = nearestColour(hexToRgb(bgColour), PALETTE.map((p) => p.index));
  const grid = createGrid(studs, studs, 1, { kind: 'picture', name, studs: 'front' });
  const clamp = (v) => Math.max(0, Math.min(255, v));
  for (let y = 0; y < studs; y++)
    for (let x = 0; x < studs; x++) {
      const i = y * studs + x;
      if (mask && mask[i]) { set(grid, x, studs - 1 - y, 0, bgIndex); continue; }
      const rgb = [clamp(buf[i * 3]), clamp(buf[i * 3 + 1]), clamp(buf[i * 3 + 2])];
      const ci = nearestColour(rgb, allowed);
      set(grid, x, studs - 1 - y, 0, ci);
      if (dither) {
        // Floyd–Steinberg error diffusion
        const p = PALETTE[ci].rgbArr;
        const err = [rgb[0] - p[0], rgb[1] - p[1], rgb[2] - p[2]];
        const spread = (dx, dy, f) => {
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || nx >= studs || ny >= studs) return;
          const j = (ny * studs + nx) * 3;
          buf[j] += err[0] * f; buf[j + 1] += err[1] * f; buf[j + 2] += err[2] * f;
        };
        spread(1, 0, 7 / 16); spread(-1, 1, 3 / 16); spread(0, 1, 5 / 16); spread(1, 1, 1 / 16);
      }
    }
  return grid;
}

// Built-in sample subject so the flow can be tried without a photo.
export function sampleImage(size = 512) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const x = c.getContext('2d');
  const s = size / 100;
  x.fillStyle = '#e8e3d6'; x.fillRect(0, 0, size, size);
  const poly = (pts, col) => { x.fillStyle = col; x.beginPath(); pts.forEach(([a, b], i) => (i ? x.lineTo(a * s, b * s) : x.moveTo(a * s, b * s))); x.closePath(); x.fill(); };
  // tail
  poly([[60, 78], [92, 52], [96, 62], [70, 86]], '#f57d20');
  poly([[88, 55], [96, 50], [97, 62], [92, 60]], '#fffffa');
  // body
  x.fillStyle = '#f57d20'; x.beginPath(); x.ellipse(52 * s, 74 * s, 22 * s, 16 * s, 0, 0, Math.PI * 2); x.fill();
  x.fillStyle = '#fffffa'; x.beginPath(); x.ellipse(45 * s, 78 * s, 10 * s, 11 * s, 0, 0, Math.PI * 2); x.fill();
  // legs
  x.fillStyle = '#3b180d'; x.fillRect(36 * s, 84 * s, 6 * s, 12 * s); x.fillRect(56 * s, 84 * s, 6 * s, 12 * s);
  // head + ears
  poly([[22, 14], [30, 36], [20, 38]], '#f57d20');
  poly([[50, 14], [52, 38], [42, 36]], '#f57d20');
  poly([[24, 20], [28, 33], [23, 34]], '#3b180d');
  poly([[48, 20], [49, 34], [45, 33]], '#3b180d');
  x.fillStyle = '#f57d20'; x.beginPath(); x.ellipse(36 * s, 44 * s, 16 * s, 13 * s, 0, 0, Math.PI * 2); x.fill();
  poly([[22, 46], [36, 62], [50, 46], [36, 52]], '#fffffa');
  x.fillStyle = '#1b1b1b';
  x.beginPath(); x.arc(30 * s, 42 * s, 2.2 * s, 0, Math.PI * 2); x.fill();
  x.beginPath(); x.arc(42 * s, 42 * s, 2.2 * s, 0, Math.PI * 2); x.fill();
  x.beginPath(); x.arc(36 * s, 58 * s, 2.4 * s, 0, Math.PI * 2); x.fill();
  const img = new Image();
  img.src = c.toDataURL();
  return new Promise((r) => { img.onload = () => r(img); });
}

// 2D preview: draws a grid face-on with studs, for thumbnails and the picture view.
export function drawGrid2D(canvas, grid, { cell = 12, layer = 'top' } = {}) {
  const { w, h, d } = grid;
  canvas.width = w * cell; canvas.height = h * cell;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#e8e3d6'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let c = -1, zHit = 0;
      for (let z = d - 1; z >= 0 && c < 0; z--) { c = grid.data[x + w * (y + h * z)]; zHit = z; }
      if (c < 0) continue;
      const px = x * cell, py = (h - 1 - y) * cell;
      ctx.fillStyle = PALETTE[c].rgb;
      ctx.fillRect(px, py, cell, cell);
      if (d > 1 && zHit === 0) { ctx.fillStyle = 'rgba(0,0,0,.18)'; ctx.fillRect(px, py, cell, cell); }
      ctx.strokeStyle = 'rgba(0,0,0,.22)'; ctx.lineWidth = 1;
      ctx.strokeRect(px + 0.5, py + 0.5, cell - 1, cell - 1);
      if (cell >= 8) {
        ctx.beginPath(); ctx.arc(px + cell / 2, py + cell / 2, cell * 0.3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,.16)'; ctx.fill();
        ctx.strokeStyle = 'rgba(0,0,0,.18)'; ctx.stroke();
      }
    }
}
