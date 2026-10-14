// Brick colour palette (solid, non-metallic colours) and colour matching helpers.

export const PALETTE = [
  { id: 10, name: 'Red', rgb: '#ff0000' },
  { id: 11, name: 'Bright Pink', rgb: '#f6adcd' },
  { id: 12, name: 'Dark Pink', rgb: '#e95da2' },
  { id: 13, name: 'Magenta', rgb: '#b51c7d' },
  { id: 14, name: 'Dark Red', rgb: '#7f131b' },
  { id: 17, name: 'Light Pink', rgb: '#f2c6cf' },
  { id: 18, name: 'Coral Orange', rgb: '#ff5869' },
  { id: 21, name: 'Orange', rgb: '#f57d20' },
  { id: 29, name: 'Light Yellow', rgb: '#ecd898' },
  { id: 30, name: 'Yellow', rgb: '#ffcd03' },
  { id: 31, name: 'Tan', rgb: '#ddc48e' },
  { id: 32, name: 'Light Flesh', rgb: '#f2e0bd' },
  { id: 34, name: 'Dark Tan', rgb: '#947e5f' },
  { id: 36, name: 'Bright Light Orange', rgb: '#fbab18' },
  { id: 38, name: 'Nougat', rgb: '#dd8c59' },
  { id: 40, name: 'Green', rgb: '#009247' },
  { id: 42, name: 'Lime', rgb: '#9aca3c' },
  { id: 43, name: 'Bright Green', rgb: '#00af4d' },
  { id: 45, name: 'Light Aqua', rgb: '#c1e4da' },
  { id: 46, name: 'Medium Azure', rgb: '#00bed3' },
  { id: 47, name: 'Dark Green', rgb: '#004a2d' },
  { id: 48, name: 'Sand Green', rgb: '#a0bcac' },
  { id: 50, name: 'Blue', rgb: '#006cb7' },
  { id: 52, name: 'Medium Blue', rgb: '#489ece' },
  { id: 53, name: 'Bright Light Blue', rgb: '#78bfea' },
  { id: 54, name: 'Sand Blue', rgb: '#7a89c0' },
  { id: 55, name: 'Dark Blue', rgb: '#00395e' },
  { id: 60, name: 'Dark Purple', rgb: '#4c2f92' },
  { id: 62, name: 'Medium Lavender', rgb: '#9675b4' },
  { id: 63, name: 'Lavender', rgb: '#bca6d0' },
  { id: 71, name: 'Light Bluish Gray', rgb: '#a0a19f' },
  { id: 72, name: 'Dark Bluish Gray', rgb: '#646767' },
  { id: 80, name: 'Black', rgb: '#1b1b1b' },
  { id: 81, name: 'Reddish Brown', rgb: '#692e14' },
  { id: 82, name: 'Dark Brown', rgb: '#3b180d' },
  { id: 83, name: 'Dark Orange', rgb: '#a65322' },
  { id: 84, name: 'Medium Dark Flesh', rgb: '#af7446' },
  { id: 90, name: 'White', rgb: '#fffffa' },
];

export function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// sRGB -> CIE Lab, so "closest colour" matches what the eye sees.
export function rgbToLab([r, g, b]) {
  const lin = (c) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const R = lin(r), G = lin(g), B = lin(b);
  const X = (R * 0.4124 + G * 0.3576 + B * 0.1805) / 0.95047;
  const Y = R * 0.2126 + G * 0.7152 + B * 0.0722;
  const Z = (R * 0.0193 + G * 0.1192 + B * 0.9505) / 1.08883;
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  const fx = f(X), fy = f(Y), fz = f(Z);
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

PALETTE.forEach((c, i) => {
  c.index = i;
  c.rgbArr = hexToRgb(c.rgb);
  c.lab = rgbToLab(c.rgbArr);
});

export function paletteByName(name) {
  return PALETTE.find((c) => c.name === name) || PALETTE[0];
}

// Returns the palette index closest to an [r,g,b] colour, limited to `allowed` indices.
export function nearestColour(rgb, allowed) {
  const lab = rgbToLab(rgb);
  let best = allowed[0], bestD = Infinity;
  for (const i of allowed) {
    const p = PALETTE[i].lab;
    const d = (p[0] - lab[0]) ** 2 + (p[1] - lab[1]) ** 2 + (p[2] - lab[2]) ** 2;
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}
