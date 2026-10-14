// PixBrik app shell: hash router, shared state and every screen.

import { PALETTE } from './palette.js';
import { stats, hollowGrid, formatSize, formatTime, euro, pieces, partName } from './build.js';
import { SIZES, COLOUR_MODES, loadImageFromFile, frameImage, makeMosaic, sampleImage, drawGrid2D } from './mosaic.js';
import { CATEGORIES, ITEMS, itemMatches, buildSign } from './library.js';

const view = document.getElementById('view');
const $ = (sel, root = view) => root.querySelector(sel);
const $$ = (sel, root = view) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

// ---- shared state ---------------------------------------------------------------

const state = {
  mode: 'picture',         // 'picture' | 'sculpture'
  subject: 'person',
  photo: null,             // HTMLImageElement
  photoIsSample: false,
  framing: { zoom: 1, panX: 0, panY: 0 },
  adjust: { brightness: 0, contrast: 0, saturation: 0, dither: false, colourMode: 'full', removeBg: false, bgTolerance: 60, bgColour: '#fffffa' },
  size: 'balanced',
  name: 'My brick picture',
  model: null,             // THREE.Object3D for sculptures
  modelName: '',
  sculptRes: 24,
  build: null,             // current grid
  fill: 'hollow',          // 'hollow' | 'solid'
  ship: 'FR',
  libCategory: 'ALL', libQuery: '', libSort: 'featured', libPage: 0,
};

const SHIPPING = {
  FR: { label: 'France', cost: 4.9, days: [4, 6] },
  GB: { label: 'United Kingdom', cost: 7.9, days: [5, 8] },
  US: { label: 'United States', cost: 14.9, days: [7, 12] },
};

let viewer = null;          // active three.js viewer
let threeMod = null;        // lazily loaded viewer module
async function three() {
  if (!threeMod) threeMod = await import('./viewer3d.js');
  return threeMod;
}
function dropViewer() { if (viewer) { viewer.dispose(); viewer = null; } }

async function mountViewer(el, show) {
  dropViewer();
  const T = await three();
  if (!document.body.contains(el)) return null;
  viewer = new T.Viewer(el);
  show(viewer, T);
  const bar = el.parentElement.querySelector('.viewer-toolbar');
  if (bar) T.bindToolbar(bar, viewer);
  return viewer;
}

const ORDERS_KEY = 'pixbrik.orders';
function loadOrders() { try { return JSON.parse(localStorage.getItem(ORDERS_KEY) || '[]'); } catch { return []; } }
function saveOrders(o) { try { localStorage.setItem(ORDERS_KEY, JSON.stringify(o)); return true; } catch { return false; } }

function deliveryWindow(code) {
  const [a, b] = SHIPPING[code].days;
  const f = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d; };
  const m = f(b).toLocaleString('en-GB', { month: 'short' }).toUpperCase();
  return `${f(a).getDate()}–${f(b).getDate()} ${m}`;
}

function currentBuild() {
  if (!state.build) return null;
  return state.build.kind === 'sculpture' && state.fill === 'hollow' ? hollowGrid(state.build) : state.build;
}

// ---- shared bits of markup --------------------------------------------------------

const backBtn = (to) => `<a class="back" href="${to}" aria-label="Back">←</a>`;
const progress = (label, pct) => `
  <div class="step-head">${backBtn(history.length > 1 ? 'javascript:history.back()' : '#/')}
    <div class="step-meta"><div class="eyebrow">${label}</div><div class="bar"><span style="width:${pct}%"></span></div></div>
  </div>`;
const viewerBlock = (title, hint, label) => `
  <div class="viewer-card">
    <div class="viewer-head"><div class="live"><span class="dot"></span>${title}</div><div class="hint">${hint}</div></div>
    <div class="viewer" role="img" aria-label="${label}"></div>
    <div class="viewer-toolbar" role="toolbar">
      <button data-act="out" aria-label="Zoom out">−</button>
      <button data-act="in" aria-label="Zoom in">+</button>
      <button data-act="left" aria-label="Rotate left">←</button>
      <button data-act="reset" class="wide" aria-label="Reset view">RESET VIEW</button>
      <button data-act="right" aria-label="Rotate right">→</button>
    </div>
  </div>`;
const cta = (label, href, disabled = false) =>
  `<div class="cta-bar"><a class="cta ${disabled ? 'disabled' : ''}" href="${disabled ? '#' : href}">${label}</a></div>`;

// ---- screens --------------------------------------------------------------------

function Home() {
  view.innerHTML = `
  <section class="hero">
    <div class="hero-copy">
      <div class="eyebrow"><span class="dot"></span>PERSONAL PHOTOS. HANDS-ON ART.</div>
      <h1>Memories,<br>piece by piece.</h1>
      <p class="lead">Turn your favourite person, pet or moment into a brick picture. Start with one photo. Make it yours.</p>
      <a class="cta big" href="#/create?mode=picture">Create my brick picture <span>⟶</span></a>
      <p class="small">Take or upload a photo · preview before deciding</p>
    </div>
    <figure class="hero-art">
      <div class="frame"><canvas id="hero-mosaic"></canvas></div>
      <figcaption>Display frame illustration · frame not included</figcaption>
    </figure>
  </section>
  <section>
    <h2>Your photo, your way.</h2>
    <p class="muted">A picture to display, or a shape to explore.</p>
    <div class="choice-grid">
      <a class="choice" href="#/create?mode=picture" aria-label="Create a flat photo panel, best for matching your photo">
        <div class="choice-icon yellow">⠿</div><div class="tag">CLOSEST PHOTO MATCH</div>
        <h3>Brick picture</h3>
        <p>Your photo as a flat brick mosaic. Our starting point for portraits and favourite moments.</p>
        <p class="small">One photo · choose your size · build by hand</p>
        <span class="link">Make a brick picture →</span>
      </a>
      <a class="choice" href="#/create?mode=sculpture" aria-label="Create a 3D sculpture from a 3D model">
        <div class="choice-icon">▲</div><div class="tag">EXPERIMENTAL · 3D</div>
        <h3>3D sculpture</h3>
        <p>Explore your subject from every angle. Review the 3D model before it becomes bricks.</p>
        <p class="small">Upload a .glb / .obj model or try the sample car.</p>
        <span class="link">Explore 3D →</span>
      </a>
    </div>
  </section>
  <section class="steps">
    ${[['Add your photo', 'Pick a clear photo of your subject.'], ['Review the preview', 'Adjust the result before continuing.'], ['Get the build details', 'See the parts list and assembly guide.']]
      .map(([t, d], i) => `<div class="step"><div class="num">${i + 1}</div><h4>${t}</h4><p>${d}</p></div>`).join('')}
  </section>
  <a class="explore" href="#/library"><div><strong>Prefer to explore first?</strong><br><span class="muted">Browse ready-made models in the library.</span></div><span>→</span></a>
  <p class="fine">Your photo stays on your device. Everything in this prototype runs in your browser. Use photos you own or have permission to use.<br>
  PixBrik is a prototype. Checkout does not take payment or start kit fulfilment.</p>`;

  // live demo mosaic made from the sample image
  sampleImage().then((img) => {
    const c = document.getElementById('hero-mosaic');
    if (!c) return;
    const g = makeMosaic(frameImage(img, { zoom: 1, panX: 0, panY: 0 }), { studs: 40, colourMode: 'full' });
    drawGrid2D(c, g, { cell: 12 });
  });
}

function Create(params) {
  state.mode = params.get('mode') === 'sculpture' ? 'sculpture' : 'picture';
  const sculpt = state.mode === 'sculpture';
  view.innerHTML = `
    ${progress(sculpt ? '1 / PREPARE YOUR SUBJECT' : '1 / YOUR PHOTO', 25)}
    <h1 class="title">${sculpt ? 'Add your 3D model.' : 'Add your photo.'}</h1>
    <p class="muted">${sculpt
      ? 'Upload a 3D model (.glb, .gltf or .obj), for example one exported from a 3D-scan or AI 3D app. You can turn it a full 360° before turning it into bricks.'
      : 'Pick a favourite from your camera roll, or take a new photo. A clear, well-lit subject works best.'}</p>
    ${sculpt ? '' : `<div class="chips" role="radiogroup">
      ${[['person', 'A person'], ['pet', 'Your pet'], ['object', 'An object']].map(([k, l]) =>
        `<button class="chip ${state.subject === k ? 'on' : ''}" data-subject="${k}">${l}</button>`).join('')}
    </div>`}
    <label class="drop">
      <input type="file" id="file" accept="${sculpt ? '.glb,.gltf,.obj' : 'image/*'}" ${sculpt ? '' : 'capture="environment"'} hidden>
      <div class="plus">＋</div>
      <div class="drop-title">${sculpt ? 'START WITH YOUR MODEL' : 'START WITH YOUR PHOTO'}</div>
      <div class="muted">${sculpt ? '.glb · .gltf · .obj' : 'Camera or photo library'}</div>
    </label>
    <p class="small" id="file-status">${sculpt ? 'The model is opened in your browser only. Nothing is uploaded.' : 'Framing and the brick-picture preview stay on this device.'}</p>
    <button class="text-link" id="sample">${sculpt ? 'No model handy? Use the sample car →' : 'No photo handy? Use the sample object →'}</button>
    ${cta(sculpt ? 'ADD A MODEL' : 'ADD A PHOTO', '#', true)}`;

  $$('.chip').forEach((b) => b.onclick = () => {
    state.subject = b.dataset.subject;
    $$('.chip').forEach((x) => x.classList.toggle('on', x === b));
  });
  const ready = (msg) => {
    $('#file-status').textContent = msg;
    const a = $('.cta');
    a.classList.remove('disabled');
    a.textContent = sculpt ? 'VIEW THE 3D MODEL →' : 'CHOOSE MY SIZE →';
    a.href = sculpt ? '#/sculpture' : '#/picture';
  };
  $('#file').onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      if (sculpt) {
        $('#file-status').textContent = 'Opening model…';
        const T = await three();
        state.model = await T.loadModelFile(f);
        state.modelName = f.name.replace(/\.\w+$/, '');
        ready(`${f.name} loaded ✓`);
      } else {
        state.photo = await loadImageFromFile(f);
        state.photoIsSample = false;
        state.framing = { zoom: 1, panX: 0, panY: 0 };
        state.name = `My ${state.subject === 'pet' ? 'pet' : state.subject === 'object' ? 'object' : 'person'} picture`;
        ready(`${f.name} selected ✓`);
      }
    } catch (err) {
      $('#file-status').textContent = err.message;
    }
  };
  $('#sample').onclick = async () => {
    if (sculpt) {
      const T = await three();
      state.model = T.sampleCar();
      state.modelName = 'Flame Coupe';
      ready('Sample car selected ✓');
    } else {
      state.photo = await sampleImage();
      state.photoIsSample = true;
      state.framing = { zoom: 1, panX: 0, panY: 0 };
      state.name = 'Signal Fox';
      ready('Sample object selected ✓');
    }
  };
}

function Picture() {
  if (!state.photo) { location.hash = '#/create?mode=picture'; return; }
  const a = state.adjust;
  view.innerHTML = `
    ${progress('2 / MAKE IT YOURS', 60)}
    <h1 class="title">Your brick picture.</h1>
    <p class="muted">Real brick colours. Choose your size below.</p>
    <div class="tabs"><button class="on" data-tab="pic">PICTURE</button><button data-tab="3d">ROTATE PANEL</button></div>
    <div class="stage">
      <div class="pane" data-pane="pic"><div class="frame"><canvas id="mosaic"></canvas></div><p class="cap">Display frame illustration · frame not included</p></div>
      <div class="pane" data-pane="3d" hidden>${viewerBlock('LIVE 3D PANEL', 'DRAG · PINCH TO ZOOM', 'Brick picture in 3D')}</div>
    </div>
    <div class="stats" id="stats"></div>

    <h3 class="section">CHOOSE YOUR SIZE &amp; DETAIL</h3>
    <p class="small">Tap a size to see it in the main preview. Larger pictures show more detail and use more pieces.</p>
    <div class="sizes" id="sizes"></div>

    <details class="panel" open>
      <summary>Frame your photo</summary>
      <div class="frame-tools">
        <canvas id="framed" class="framed" title="Drag to move your photo"></canvas>
        <div class="sliders">
          ${slider('zoom', 'Zoom', 1, 3, 0.01, state.framing.zoom)}
          <p class="small">Drag the photo to move it inside the square.</p>
        </div>
      </div>
    </details>
    <details class="panel">
      <summary>Colour &amp; light</summary>
      ${slider('brightness', 'Brightness', -80, 80, 1, a.brightness)}
      ${slider('contrast', 'Contrast', -80, 80, 1, a.contrast)}
      ${slider('saturation', 'Colour intensity', -100, 100, 1, a.saturation)}
      <label class="field">Colours
        <select id="colourMode">${Object.entries(COLOUR_MODES).map(([k, m]) => `<option value="${k}" ${a.colourMode === k ? 'selected' : ''}>${m.label}</option>`).join('')}</select>
      </label>
      <label class="check"><input type="checkbox" id="dither" ${a.dither ? 'checked' : ''}> Smooth shading (dithering)</label>
    </details>
    <details class="panel">
      <summary>Background</summary>
      <label class="check"><input type="checkbox" id="removeBg" ${a.removeBg ? 'checked' : ''}> Replace a plain background</label>
      ${slider('bgTolerance', 'Background tolerance', 10, 160, 1, a.bgTolerance)}
      <div class="swatches" id="bgSwatches">${['White', 'Light Flesh', 'Tan', 'Light Bluish Gray', 'Black', 'Yellow', 'Bright Light Blue', 'Sand Green', 'Light Pink']
        .map((n) => { const c = PALETTE.find((p) => p.name === n); return `<button class="sw ${a.bgColour === c.rgb ? 'on' : ''}" data-rgb="${c.rgb}" title="${n}" style="background:${c.rgb}"></button>`; }).join('')}</div>
    </details>
    <details class="panel">
      <summary>Name, parts &amp; build information</summary>
      <label class="field">Name of your picture <input id="name" maxlength="40" value="${esc(state.name)}"></label>
      <p><a href="#/parts">View the parts list →</a> · <a href="#/guide">Open phone, print and PDF build guide →</a></p>
    </details>
    ${cta('REVIEW KIT &amp; PRICE →', '#/kit')}`;

  const framedCanvas = $('#framed');
  const mosaicCanvas = $('#mosaic');
  let framed;
  const render = () => {
    framed = frameImage(state.photo, state.framing, 384);
    framedCanvas.width = framedCanvas.height = 384;
    framedCanvas.getContext('2d').drawImage(framed, 0, 0);
    const studs = SIZES.find((s) => s.key === state.size).studs;
    state.build = makeMosaic(framed, { ...state.adjust, studs, name: state.name });
    drawGrid2D(mosaicCanvas, state.build, { cell: Math.max(8, Math.floor(720 / studs)) });
    const st = stats(state.build);
    $('#stats').innerHTML = statRow(st);
    renderSizes(framed);
    if (viewer && !$('[data-pane="3d"]').hidden) viewer.showGrid(state.build);
  };
  const renderSizes = (fr) => {
    $('#sizes').innerHTML = SIZES.map((s) => {
      const g = makeMosaic(fr, { ...state.adjust, studs: s.studs });
      const st = stats(g);
      return `<button class="size ${state.size === s.key ? 'on' : ''}" data-size="${s.key}">
        <div><strong>${s.label}</strong><div class="small">${s.note} · ${formatSize(st.size)} · ${st.parts} parts</div></div>
        <div class="price">${euro(st.price)}<div class="small">PANEL KIT</div></div></button>`;
    }).join('');
    $$('.size').forEach((b) => b.onclick = () => { state.size = b.dataset.size; render(); });
  };
  let pending = 0;
  const schedule = () => { cancelAnimationFrame(pending); pending = requestAnimationFrame(render); };

  $$('input[type=range]').forEach((r) => r.oninput = () => {
    const v = parseFloat(r.value);
    r.closest('.slider').querySelector('output').textContent = r.value;
    if (r.id === 'zoom') state.framing.zoom = v; else state.adjust[r.id] = v;
    schedule();
  });
  $('#colourMode').onchange = (e) => { state.adjust.colourMode = e.target.value; schedule(); };
  $('#dither').onchange = (e) => { state.adjust.dither = e.target.checked; schedule(); };
  $('#removeBg').onchange = (e) => { state.adjust.removeBg = e.target.checked; schedule(); };
  $$('#bgSwatches .sw').forEach((b) => b.onclick = () => {
    state.adjust.bgColour = b.dataset.rgb;
    $$('#bgSwatches .sw').forEach((x) => x.classList.toggle('on', x === b));
    schedule();
  });
  $('#name').oninput = (e) => { state.name = e.target.value || 'My brick picture'; if (state.build) state.build.name = state.name; };

  // drag to pan
  let drag = null;
  framedCanvas.onpointerdown = (e) => { drag = { x: e.clientX, y: e.clientY, ...state.framing }; framedCanvas.setPointerCapture(e.pointerId); };
  framedCanvas.onpointermove = (e) => {
    if (!drag) return;
    const r = framedCanvas.getBoundingClientRect();
    state.framing.panX = drag.panX + (e.clientX - drag.x) / r.width;
    state.framing.panY = drag.panY + (e.clientY - drag.y) / r.height;
    schedule();
  };
  framedCanvas.onpointerup = () => { drag = null; };

  bindTabs(() => mountViewer($('[data-pane="3d"] .viewer'), (v) => v.showGrid(state.build)));
  render();
}

function slider(id, label, min, max, step, value) {
  return `<label class="slider">${label}<input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${value}"><output>${value}</output></label>`;
}
function statRow(st) {
  return `<div><strong>${st.parts}</strong><span>PIECES</span></div>
    <div><strong>${formatSize(st.size)}</strong><span>FINISHED SIZE</span></div>
    <div><strong>${formatTime(st.minutes)}</strong><span>BUILD TIME</span></div>`;
}
function bindTabs(on3d) {
  $$('.tabs button').forEach((b) => b.onclick = () => {
    $$('.tabs button').forEach((x) => x.classList.toggle('on', x === b));
    $$('.pane').forEach((p) => { p.hidden = p.dataset.pane !== b.dataset.tab; });
    if (b.dataset.tab === 'pic') dropViewer(); else on3d(b.dataset.tab);
  });
}

function Sculpture() {
  if (!state.model) { location.hash = '#/create?mode=sculpture'; return; }
  const RES = [{ key: 16, label: 'Efficient', note: 'Fewest pieces' }, { key: 24, label: 'Balanced', note: 'Good shape detail' }, { key: 32, label: 'Detailed', note: 'Most detail · largest' }];
  view.innerHTML = `
    ${progress('2 / REVIEW YOUR MODEL', 60)}
    <h1 class="title">${esc(state.modelName || 'Your 3D model')}</h1>
    <p class="muted">Turn the model a full 360° to check every side. Then see it as bricks.</p>
    <div class="tabs"><button class="on" data-tab="raw">RAW MODEL</button><button data-tab="bricks">BRICK BUILD</button></div>
    <div class="stage">
      <div class="pane" data-pane="raw">${viewerBlock('LIVE 3D MODEL', 'DRAG · PINCH TO ZOOM', 'Raw 3D model')}</div>
      <div class="pane" data-pane="bricks" hidden>${viewerBlock('BRICK PROPOSAL', 'DRAG · PINCH TO ZOOM', 'Brick build of the model')}</div>
    </div>
    <div class="stats" id="stats"></div>
    <h3 class="section">CHOOSE YOUR SIZE &amp; DETAIL</h3>
    <div class="sizes">${RES.map((r) => `<button class="size ${state.sculptRes === r.key ? 'on' : ''}" data-res="${r.key}">
      <div><strong>${r.label}</strong><div class="small">${r.note} · ${r.key} studs wide</div></div><div class="price" data-price="${r.key}">…</div></button>`).join('')}</div>
    <div class="note"><strong>SOURCE 3D LINKED TO THIS BUILD</strong><br>
      <span class="small">Changing size rebuilds the bricks from the same model. Upload a new model from step 1 to replace it.</span></div>
    ${cta('REVIEW KIT &amp; PRICE →', '#/kit')}`;

  let T;
  const rebuild = () => {
    const source = state.model.clone(true);
    state.build = T.voxelise(source, state.sculptRes, state.modelName || 'My 3D sculpture');
    $('#stats').innerHTML = statRow(stats(hollowGrid(state.build)));
  };
  const show = async (tab) => {
    T = await three();
    if (tab === 'raw') mountViewer($('[data-pane="raw"] .viewer'), (v) => v.showModel(state.model.clone(true)));
    else mountViewer($('[data-pane="bricks"] .viewer'), (v) => v.showGrid(state.build));
  };
  bindTabs(show);
  $$('[data-res]').forEach((b) => b.onclick = () => {
    state.sculptRes = +b.dataset.res;
    $$('[data-res]').forEach((x) => x.classList.toggle('on', x === b));
    rebuild();
    if (viewer && !$('[data-pane="bricks"]').hidden) viewer.showGrid(state.build);
  });
  (async () => {
    T = await three();
    for (const r of RES) {
      const g = T.voxelise(state.model.clone(true), r.key);
      const el = $(`[data-price="${r.key}"]`);
      if (el) el.innerHTML = `${euro(stats(hollowGrid(g)).price)}<div class="small">BRICK KIT</div>`;
    }
    rebuild();
    show('raw');
  })();
}

function Library() {
  const q = state.libQuery.trim().toLowerCase();
  let list = ITEMS.filter((it) => itemMatches(it, state.libCategory) && (!q || `${it.title} ${it.category}`.toLowerCase().includes(q)));
  if (state.libSort === 'az') list.sort((a, b) => a.title.localeCompare(b.title));
  if (state.libSort === 'za') list.sort((a, b) => b.title.localeCompare(a.title));
  if (state.libSort === 'category') list.sort((a, b) => a.category.localeCompare(b.category));
  const per = 8;
  const pages = Math.max(1, Math.ceil(list.length / per));
  state.libPage = Math.min(state.libPage, pages - 1);
  const shown = list.slice(state.libPage * per, state.libPage * per + per);
  view.innerHTML = `
    <div class="step-head">${backBtn('#/')}</div>
    <div class="eyebrow">LIBRARY / BROWSE AND CUSTOMISE</div>
    <h1 class="title">Find your next build</h1>
    <p class="muted">${ITEMS.length} ready-made designs. Search, filter, choose colours and make it yours.</p>
    <label class="search"><span>⌕</span><input id="q" placeholder="Search signs, hearts, birthday…" value="${esc(state.libQuery)}"></label>
    <div class="eyebrow">CATEGORY OR THEME</div>
    <div class="chips scroll">${CATEGORIES.map((c) => `<button class="chip ${state.libCategory === c ? 'on' : ''}" data-cat="${esc(c)}">${c}</button>`).join('')}</div>
    <div class="sortbar"><strong>${list.length} IDEAS</strong>${[['featured', 'FEATURED'], ['az', 'A-Z'], ['za', 'Z-A'], ['category', 'CATEGORY']]
      .map(([k, l]) => `<button class="pill ${state.libSort === k ? 'on' : ''}" data-sort="${k}">${l}</button>`).join('')}</div>
    <div class="cards">${shown.map((it) => `<a class="card" href="#/item/${it.id}"><canvas data-thumb="${it.id}"></canvas>
      <div class="card-body"><div>${esc(it.title)}</div><div class="tag">${esc(it.category)}</div></div></a>`).join('') || '<p class="muted">No designs match. Try another search.</p>'}</div>
    <div class="pager"><button id="prev" ${state.libPage === 0 ? 'disabled' : ''}>← PREVIOUS</button><span>${state.libPage + 1} / ${pages}</span><button id="next" ${state.libPage >= pages - 1 ? 'disabled' : ''}>NEXT →</button></div>
    <p class="fine">ORIGINAL GENERIC DESIGNS.</p>`;
  $$('[data-thumb]').forEach((c) => drawGrid2D(c, buildSign(ITEMS.find((i) => i.id === c.dataset.thumb)), { cell: 10 }));
  const q$ = $('#q');
  q$.oninput = () => { state.libQuery = q$.value; state.libPage = 0; Library(); const n = $('#q'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); };
  $$('[data-cat]').forEach((b) => b.onclick = () => { state.libCategory = b.dataset.cat; state.libPage = 0; Library(); });
  $$('[data-sort]').forEach((b) => b.onclick = () => { state.libSort = b.dataset.sort; Library(); });
  $('#prev').onclick = () => { state.libPage--; Library(); };
  $('#next').onclick = () => { state.libPage++; Library(); };
}

function Item(id) {
  const it = ITEMS.find((i) => i.id === id);
  if (!it) { location.hash = '#/library'; return; }
  const opts = { lines: [...(it.lines || [])], fg: it.fg, bg: it.bg };
  const colourOptions = (sel) => PALETTE.map((c) => `<option ${c.name === sel ? 'selected' : ''}>${c.name}</option>`).join('');
  view.innerHTML = `
    <div class="step-head">${backBtn('#/library')}<div class="step-meta"><div class="eyebrow">LIBRARY / CUSTOMISE YOUR BUILD</div></div></div>
    <h1 class="title">${esc(it.title)}</h1>
    <div class="tabs"><button class="on" data-tab="pic">FRONT</button><button data-tab="3d">ROTATE</button></div>
    <div class="stage">
      <div class="pane" data-pane="pic"><div class="frame"><canvas id="sign"></canvas></div></div>
      <div class="pane" data-pane="3d" hidden>${viewerBlock('LIVE 3D PREVIEW', 'DRAG · PINCH TO ZOOM', 'Sign in 3D')}</div>
    </div>
    <div class="stats" id="stats"></div>
    <div class="panel">
      ${it.lines ? `<div class="eyebrow">YOUR TEXT</div>${[0, 1, 2].map((i) => `<input class="line" data-line="${i}" maxlength="10" placeholder="Line ${i + 1}" value="${esc(opts.lines[i] || '')}">`).join('')}
        <p class="small">A–Z, 0–9, & ! . ' - and ♥ · up to 10 characters a line.</p>` : ''}
      <label class="field">${it.motif ? 'Shape colour' : 'Letter colour'} <select id="fg">${colourOptions(opts.fg)}</select></label>
      <label class="field">Background colour <select id="bg">${colourOptions(opts.bg)}</select></label>
    </div>
    ${cta('REVIEW KIT &amp; PRICE →', '#/kit')}`;
  const render = () => {
    state.build = buildSign(it, opts);
    drawGrid2D($('#sign'), state.build, { cell: 16 });
    $('#stats').innerHTML = statRow(stats(state.build));
    if (viewer && !$('[data-pane="3d"]').hidden) viewer.showGrid(state.build);
  };
  $$('.line').forEach((inp) => inp.oninput = () => { opts.lines[+inp.dataset.line] = inp.value; render(); });
  $('#fg').onchange = (e) => { opts.fg = e.target.value; render(); };
  $('#bg').onchange = (e) => { opts.bg = e.target.value; render(); };
  bindTabs(() => mountViewer($('[data-pane="3d"] .viewer'), (v) => v.showGrid(state.build)));
  render();
}

function Kit() {
  if (!state.build) { location.hash = '#/'; return; }
  const sculpt = state.build.kind === 'sculpture';
  const solid = stats(state.build);
  const hollow = sculpt ? stats(hollowGrid(state.build)) : solid;
  const chosen = sculpt && state.fill === 'hollow' ? hollow : solid;
  const ship = SHIPPING[state.ship];
  const total = chosen.price + ship.cost;
  const [whole, cents] = euro(total).slice(1).split('.');
  const saving = solid.parts ? Math.round((1 - hollow.parts / solid.parts) * 100) : 0;
  view.innerHTML = `
    <div class="step-head">${backBtn('javascript:history.back()')}<div class="step-meta center"><strong>YOUR KIT</strong></div></div>
    <div class="eyebrow">${esc(state.build.name).toUpperCase()} · ESTIMATE</div>
    <div class="bigprice">€${whole}<small>.${cents}</small></div>
    <p class="small">Kit + shipping · excludes tax · prototype, no payment taken</p>
    <p class="small">Estimate based on a sample price list, not a live supplier quote.</p>
    ${sculpt ? `<div class="fills">
      <button class="fill ${state.fill === 'hollow' ? 'on' : ''}" data-fill="hollow"><div class="ico hollow"></div><strong>REINFORCED HOLLOW</strong>
        <span>${hollow.parts} parts · −${saving}% · internal supports</span><b>${euro(hollow.price)}</b></button>
      <button class="fill ${state.fill === 'solid' ? 'on' : ''}" data-fill="solid"><div class="ico"></div><strong>SOLID · COLLECTOR</strong>
        <span>${solid.parts} parts · filled core</span><b>${euro(solid.price)}</b></button>
    </div>
    <p class="small">Same outside. Reinforced hollow keeps two base layers plus internal columns; solid fills the entire hidden core.</p>`
    : `<div class="fills"><div class="fill on"><div class="ico"></div><strong>${state.build.kind === 'sign' ? 'SIGN KIT' : 'PANEL KIT'}</strong>
        <span>${solid.parts} parts · ${solid.colours} colours</span><b>${euro(solid.price)}</b></div></div>`}
    <p><a href="#/parts">View the full parts list →</a> · <a href="#/guide">Build guide →</a></p>
    <div class="eyebrow">SHIP TO</div>
    <div class="chips">${Object.entries(SHIPPING).map(([k, s]) => `<button class="chip ${state.ship === k ? 'on' : ''}" data-ship="${k}">${k} ${state.ship === k ? s.label : ''}</button>`).join('')}</div>
    <p><span class="dot red"></span> <strong>Estimated delivery ${deliveryWindow(state.ship)} · ${euro(ship.cost)} shipping</strong></p>
    <div class="checkout-bar"><div><div class="tag">TOTAL</div><strong>${euro(total)}</strong></div><a class="cta" href="#/checkout">CHECKOUT →</a></div>`;
  $$('[data-fill]').forEach((b) => b.onclick = () => { state.fill = b.dataset.fill; Kit(); });
  $$('[data-ship]').forEach((b) => b.onclick = () => { state.ship = b.dataset.ship; Kit(); });
}

function Parts() {
  const g = currentBuild();
  if (!g) { location.hash = '#/'; return; }
  const st = stats(g);
  view.innerHTML = `
    <div class="step-head">${backBtn('javascript:history.back()')}<div class="step-meta"><div class="eyebrow">BILL OF MATERIALS</div></div></div>
    <h1 class="title">Parts list</h1>
    <p class="muted">${esc(g.name)} · ${st.parts} parts · ${st.colours} colours · ${formatSize(st.size)}</p>
    <table class="bom"><thead><tr><th></th><th>Part</th><th>Colour</th><th>Qty</th></tr></thead><tbody>
      ${st.bom.map((r) => `<tr><td><span class="sw small" style="background:${r.colour.rgb}"></span></td><td>${r.part}</td><td>${r.colour.name}</td><td>${r.qty}</td></tr>`).join('')}
    </tbody><tfoot><tr><td></td><td colspan="2">Total</td><td>${st.parts}</td></tr></tfoot></table>
    <p><button class="btn" id="csv">Download CSV</button> <a class="btn" href="#/guide">Open build guide</a></p>`;
  $('#csv').onclick = () => {
    const rows = [['Part', 'Colour', 'Quantity'], ...st.bom.map((r) => [r.part, r.colour.name, r.qty])];
    const blob = new Blob([rows.map((r) => r.join(',')).join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${g.name.replace(/\W+/g, '-').toLowerCase()}-parts.csv`;
    a.click();
  };
}

// Build guide: one diagram per layer (sculptures) or per 8-row band (pictures & signs).
function Guide() {
  const g = currentBuild();
  if (!g) { location.hash = '#/'; return; }
  const list = pieces(g);
  const steps = [];
  if (g.kind === 'sculpture') {
    for (let y = 0; y < g.h; y++) steps.push({ title: `Layer ${y + 1} of ${g.h}`, filter: (p) => p.y === y, layer: y });
  } else {
    for (let z = 0; z < g.d; z++)
      for (let y0 = 0; y0 < g.h; y0 += 8)
        steps.push({ title: `${g.d > 1 ? (z ? 'Letters · ' : 'Backing · ') : ''}rows ${y0 + 1}–${Math.min(g.h, y0 + 8)}`, filter: (p) => p.z === z && p.y >= y0 && p.y < y0 + 8, z, y0 });
  }
  view.innerHTML = `
    <div class="step-head no-print">${backBtn('javascript:history.back()')}<div class="step-meta"><div class="eyebrow">BUILD GUIDE</div></div></div>
    <h1 class="title">${esc(g.name)}</h1>
    <p class="muted">${list.length} pieces · ${steps.length} steps. New pieces in each step are outlined.</p>
    <p class="no-print"><button class="btn" onclick="window.print()">Print or save as PDF</button></p>
    <div class="guide">${steps.map((s, i) => `<div class="guide-step"><div class="eyebrow">STEP ${i + 1} · ${s.title}</div><canvas data-step="${i}"></canvas><ul class="small" data-list="${i}"></ul></div>`).join('')}</div>`;
  const W = g.w, H = g.kind === 'sculpture' ? g.d : g.h;
  const cell = Math.max(6, Math.min(16, Math.floor(560 / Math.max(W, H))));
  steps.forEach((s, i) => {
    const c = $(`[data-step="${i}"]`);
    c.width = W * cell; c.height = H * cell;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#efe9dc'; ctx.fillRect(0, 0, c.width, c.height);
    const rect = (p) => (g.kind === 'sculpture'
      ? [p.x * cell, (g.d - 1 - p.z) * cell, p.len * cell, cell]
      : [p.x * cell, (g.h - 1 - p.y) * cell, p.len * cell, cell]);
    // pieces already placed, faded: the layer below (sculptures) or earlier rows of this layer
    const placed = g.kind === 'sculpture'
      ? list.filter((p) => p.y === s.layer - 1)
      : list.filter((p) => p.z < s.z || (p.z === s.z && p.y < s.y0));
    ctx.globalAlpha = 0.25;
    for (const p of placed) { ctx.fillStyle = PALETTE[p.colour].rgb; ctx.fillRect(...rect(p)); }
    ctx.globalAlpha = 1;
    const now = list.filter(s.filter);
    const counts = new Map();
    for (const p of now) {
      ctx.fillStyle = PALETTE[p.colour].rgb;
      const r = rect(p);
      ctx.fillRect(...r);
      ctx.strokeStyle = '#16130f'; ctx.lineWidth = 1.5; ctx.strokeRect(r[0] + 0.75, r[1] + 0.75, r[2] - 1.5, r[3] - 1.5);
      const k = `${partName(p)} · ${PALETTE[p.colour].name}`;
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    $(`[data-list="${i}"]`).innerHTML = [...counts].map(([k, n]) => `<li>${n} × ${k}</li>`).join('');
  });
}

function Checkout() {
  const g = currentBuild();
  if (!g) { location.hash = '#/'; return; }
  const st = stats(g);
  const ship = SHIPPING[state.ship];
  const kind = g.kind === 'sculpture' ? (state.fill === 'hollow' ? 'Hollow Build' : 'Solid Build') : g.kind === 'sign' ? 'Sign Kit' : 'Panel Kit';
  view.innerHTML = `
    <div class="step-head">${backBtn('javascript:history.back()')}<div class="step-meta"><div class="eyebrow">CHECKOUT</div></div></div>
    <h1 class="title">Almost theirs.</h1>
    <p class="muted">One last look. Prototype checkout — no real payment is collected.</p>
    <div class="panel">
      <div class="eyebrow">ORDER SUMMARY</div>
      <div class="row"><strong>${esc(g.name)} · ${kind}</strong><span>${euro(st.price)}</span></div>
      <div class="small">${st.parts} PARTS · ${st.colours} COLOURS · STEP-BY-STEP GUIDE INCLUDED</div>
      <div class="row"><span>SHIPPING (${state.ship})</span><span>${euro(ship.cost)}</span></div>
      <div class="small">ESTIMATED DELIVERY ${deliveryWindow(state.ship)}</div>
      <div class="row total"><strong>Total</strong><strong>${euro(st.price + ship.cost)}</strong></div>
    </div>
    <div class="panel">
      <div class="eyebrow">ACCOUNT &amp; ORDER STORAGE</div>
      <p class="small">NOT SIGNED IN · DEVICE-ONLY DEMO. Saving keeps your build and delivery choice in this browser. A production checkout would collect contact, delivery and payment details here.</p>
    </div>
    <div class="cta-bar"><button class="cta" id="save">SAVE DEMO ORDER ON THIS DEVICE</button></div>`;
  $('#save').onclick = () => {
    const orders = loadOrders();
    orders.unshift({ id: Date.now().toString(36).toUpperCase(), name: g.name, kind, parts: st.parts, total: st.price + ship.cost, ship: state.ship, date: new Date().toISOString() });
    const ok = saveOrders(orders.slice(0, 20));
    $('#save').textContent = ok ? 'SAVED ✓ · SEE ACCOUNT' : 'COULD NOT SAVE IN THIS BROWSER';
    if (ok) $('#save').onclick = () => { location.hash = '#/account'; };
  };
}

function Account() {
  const orders = loadOrders();
  view.innerHTML = `
    <div class="step-head">${backBtn('#/')}<div class="step-meta"><div class="eyebrow">ACCOUNT</div></div></div>
    <h1 class="title">Your saved builds</h1>
    <p class="muted">Demo orders saved in this browser.</p>
    ${orders.length ? `<div class="orders">${orders.map((o) => `<div class="panel"><div class="row"><strong>${esc(o.name)} · ${esc(o.kind)}</strong><span>${euro(o.total)}</span></div>
      <div class="small">#${esc(o.id)} · ${o.parts} parts · ship to ${esc(o.ship)} · ${new Date(o.date).toLocaleDateString('en-GB')}</div></div>`).join('')}</div>
      <button class="btn" id="clear">Clear saved orders</button>` : '<p>No saved orders yet. <a href="#/create?mode=picture">Create a brick picture →</a></p>'}`;
  const c = $('#clear');
  if (c) c.onclick = () => { saveOrders([]); Account(); };
}

function Contact() {
  view.innerHTML = `
    <div class="step-head">${backBtn('#/')}<div class="step-meta"><div class="eyebrow">CONTACT</div></div></div>
    <h1 class="title">Talk to us.</h1>
    <p class="muted">Questions about a build, a custom order or the project.</p>
    <form class="panel" id="contact">
      <label class="field">Name <input name="name" required></label>
      <label class="field">Email <input name="email" type="email" required></label>
      <label class="field">Message <textarea name="msg" rows="5" required></textarea></label>
      <button class="cta" type="submit">SEND MESSAGE</button>
      <p class="small" id="sent"></p>
    </form>`;
  $('#contact').onsubmit = (e) => {
    e.preventDefault();
    $('#sent').textContent = 'Thanks! (Prototype: messages are not sent anywhere yet.)';
    e.target.reset();
  };
}

// ---- router ---------------------------------------------------------------------

function route() {
  dropViewer();
  closeMenu();
  const [path, query] = location.hash.replace(/^#/, '').split('?');
  const params = new URLSearchParams(query || '');
  const parts = (path || '/').split('/').filter(Boolean);
  const routes = { '': Home, create: () => Create(params), picture: Picture, sculpture: Sculpture, library: Library,
    item: () => Item(parts[1]), kit: Kit, parts: Parts, guide: Guide, checkout: Checkout, account: Account, contact: Contact };
  (routes[parts[0] || ''] || Home)();
  window.scrollTo(0, 0);
}

const menu = document.getElementById('menu');
function closeMenu() { menu.hidden = true; }
document.getElementById('menu-btn').onclick = () => { menu.hidden = false; };
document.getElementById('menu-close').onclick = closeMenu;
menu.onclick = (e) => { if (e.target === menu) closeMenu(); };

window.addEventListener('hashchange', route);
route();
