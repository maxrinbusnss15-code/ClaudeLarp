// Ready-made library: brick signs built from a 5x7 pixel font, plus heart and tree motifs.

import { paletteByName } from './palette.js';
import { createGrid, set } from './build.js';

const FONT = {
  A: ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
  B: ['11110', '10001', '10001', '11110', '10001', '10001', '11110'],
  C: ['01111', '10000', '10000', '10000', '10000', '10000', '01111'],
  D: ['11110', '10001', '10001', '10001', '10001', '10001', '11110'],
  E: ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
  F: ['11111', '10000', '10000', '11110', '10000', '10000', '10000'],
  G: ['01111', '10000', '10000', '10011', '10001', '10001', '01111'],
  H: ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
  I: ['11111', '00100', '00100', '00100', '00100', '00100', '11111'],
  J: ['00111', '00010', '00010', '00010', '00010', '10010', '01100'],
  K: ['10001', '10010', '10100', '11000', '10100', '10010', '10001'],
  L: ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
  M: ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
  N: ['10001', '11001', '10101', '10011', '10001', '10001', '10001'],
  O: ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
  P: ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
  Q: ['01110', '10001', '10001', '10001', '10101', '10010', '01101'],
  R: ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
  S: ['01111', '10000', '10000', '01110', '00001', '00001', '11110'],
  T: ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
  U: ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
  V: ['10001', '10001', '10001', '10001', '10001', '01010', '00100'],
  W: ['10001', '10001', '10001', '10101', '10101', '10101', '01010'],
  X: ['10001', '10001', '01010', '00100', '01010', '10001', '10001'],
  Y: ['10001', '10001', '01010', '00100', '00100', '00100', '00100'],
  Z: ['11111', '00001', '00010', '00100', '01000', '10000', '11111'],
  0: ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
  1: ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
  2: ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
  3: ['11110', '00001', '00001', '01110', '00001', '00001', '11110'],
  4: ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
  5: ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
  6: ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
  7: ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
  8: ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
  9: ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
  '&': ['01100', '10010', '10100', '01000', '10101', '10010', '01101'],
  '!': ['00100', '00100', '00100', '00100', '00100', '00000', '00100'],
  '.': ['00000', '00000', '00000', '00000', '00000', '00000', '00100'],
  "'": ['00100', '00100', '00000', '00000', '00000', '00000', '00000'],
  '-': ['00000', '00000', '00000', '11111', '00000', '00000', '00000'],
  '♥': ['00000', '01010', '11111', '11111', '01110', '00100', '00000'],
  ' ': ['000', '000', '000', '000', '000', '000', '000'],
};

const HEART = ['0110110', '1111111', '1111111', '1111111', '0111110', '0011100', '0001000'];
const TREE = ['0001000', '0011100', '0111110', '0011100', '0111110', '1111111', '0001000'];

export const CATEGORIES = ['ALL', 'CHRISTMAS', 'HEARTS', 'YOUR MESSAGE', 'ROMANCE', 'ENGAGEMENT', 'WEDDING', 'BIRTHDAY',
  'GRADUATION', "FATHER'S DAY", "MOTHER'S DAY", 'THANKSGIVING', 'GIFT'];

export const ITEMS = [
  { id: 'i-love', title: 'I LOVE ... Sign', category: 'HEARTS', lines: ['I ♥', 'YOU'], fg: 'White', bg: 'Red', editable: true },
  { id: 'be-mine', title: 'BE MINE Sign', category: 'ROMANCE', lines: ['BE', 'MINE'], fg: 'White', bg: 'Dark Red' },
  { id: 'xoxo', title: 'XOXO Sign', category: 'ROMANCE', lines: ['XOXO'], fg: 'Red', bg: 'Bright Pink' },
  { id: 'marry-me', title: 'MARRY ME Sign', category: 'ENGAGEMENT', lines: ['MARRY', 'ME?'], fg: 'White', bg: 'Dark Red' },
  { id: 'we-said-yes', title: 'WE SAID YES Sign', category: 'ENGAGEMENT', lines: ['WE SAID', 'YES!'], fg: 'Yellow', bg: 'Dark Blue' },
  { id: 'just-married', title: 'JUST MARRIED Sign', category: 'WEDDING', lines: ['JUST', 'MARRIED'], fg: 'Black', bg: 'White' },
  { id: 'couple-names', title: 'Couple Names Sign', category: 'WEDDING', lines: ['ANNA', '&', 'LEO'], fg: 'White', bg: 'Sand Blue', editable: true },
  { id: 'happy-bday', title: 'HAPPY BDAY Sign', category: 'BIRTHDAY', lines: ['HAPPY', 'BDAY!'], fg: 'Yellow', bg: 'Dark Purple' },
  { id: 'age', title: 'Birthday Age Sign', category: 'BIRTHDAY', lines: ['21'], fg: 'White', bg: 'Medium Azure', editable: true },
  { id: 'grad', title: 'CLASS OF Sign', category: 'GRADUATION', lines: ['CLASS', 'OF 26'], fg: 'Yellow', bg: 'Black', editable: true },
  { id: 'dad', title: 'BEST DAD Sign', category: "FATHER'S DAY", lines: ['BEST', 'DAD'], fg: 'White', bg: 'Blue' },
  { id: 'mum', title: 'LOVE YOU MUM Sign', category: "MOTHER'S DAY", lines: ['LOVE', 'U MUM'], fg: 'Magenta', bg: 'Light Pink' },
  { id: 'thanks', title: 'GIVE THANKS Sign', category: 'THANKSGIVING', lines: ['GIVE', 'THANKS'], fg: 'Bright Light Orange', bg: 'Reddish Brown' },
  { id: 'heart', title: 'Brick Heart', category: 'HEARTS', motif: HEART, fg: 'Red', bg: 'White', scale: 3 },
  { id: 'tree', title: 'Christmas Tree', category: 'CHRISTMAS', motif: TREE, fg: 'Green', bg: 'White', scale: 3 },
  { id: 'message', title: 'Your Message Sign', category: 'YOUR MESSAGE', lines: ['YOUR', 'TEXT'], fg: 'Black', bg: 'Yellow', editable: true },
];
ITEMS.forEach((it, i) => { it.featured = i; if (it.category === 'YOUR MESSAGE' || it.editable) it.alsoGift = true; });

export function itemMatches(it, category) {
  return category === 'ALL' || it.category === category || (category === 'GIFT' && it.alsoGift) ||
    (category === 'YOUR MESSAGE' && it.editable);
}

function lineBitmap(text) {
  const glyphs = [...text.toUpperCase()].map((ch) => FONT[ch] || FONT[' ']);
  const rows = [];
  for (let r = 0; r < 7; r++) rows.push(glyphs.map((g) => g[r]).join('0'));
  return rows;
}

// Build a two-layer sign grid: backing colour on layer 0, raised letters on layer 1.
export function buildSign(item, { lines = item.lines, fg = item.fg, bg = item.bg } = {}) {
  let bitmap;
  if (item.motif) {
    const s = item.scale || 1;
    bitmap = item.motif.flatMap((row) => Array(s).fill([...row].map((c) => c.repeat(s)).join('')));
  } else {
    bitmap = [];
    lines.filter((l) => l.trim()).forEach((l, i) => {
      if (i) bitmap.push('');
      bitmap.push(...lineBitmap(l.trim()));
    });
  }
  const pad = 2;
  const textW = Math.max(...bitmap.map((r) => r.length), 1);
  const w = textW + pad * 2, h = bitmap.length + pad * 2;
  const grid = createGrid(w, h, 2, { kind: 'sign', name: item.title, studs: 'front' });
  const fgI = paletteByName(fg).index, bgI = paletteByName(bg).index;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) set(grid, x, y, 0, bgI);
  bitmap.forEach((row, r) => {
    const off = pad + Math.floor((textW - row.length) / 2);
    [...row].forEach((bit, c) => {
      if (bit === '1') set(grid, off + c, h - 1 - (pad + r), 1, fgI);
    });
  });
  return grid;
}
