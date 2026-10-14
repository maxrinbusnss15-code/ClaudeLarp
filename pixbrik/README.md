# PixBrik (editable version)

Turn a photo into a flat brick picture, or a 3D model into a brick sculpture, then get the price, parts list and build guide.
Plain HTML, CSS and JavaScript with no build step. 3D uses [three.js](https://threejs.org) from a CDN.

## Run it

**Windows (nothing to install):** double-click `Start PixBrik (Windows).bat`. A window opens and your browser goes to PixBrik.
Keep that window open while you use it; close it to stop. If Windows shows "Windows protected your PC", click **More info → Run anyway**.

**Mac / other:** browsers block JavaScript modules opened straight from a file (`file://`), so serve the folder:

```bash
cd pixbrik
npx http-server -p 8080     # or: python3 -m http.server 8080
```

Then open http://localhost:8080.

## Screens (hash routes)

| Route | What it does |
|---|---|
| `#/` | Landing page |
| `#/create?mode=picture` | Add a photo (or the sample fox) |
| `#/picture` | Mosaic preview, framing, colour/light, background, size (Efficient / Balanced / Detailed), 3D "Rotate panel" |
| `#/create?mode=sculpture` | Add a `.glb` / `.gltf` / `.obj` model (or the sample car) |
| `#/sculpture` | Live 3D model you can turn 360°, plus the brick version |
| `#/library`, `#/item/<id>` | Ready-made signs: search, filter, sort, edit text and colours |
| `#/kit` | Price, hollow vs solid fill (sculptures), shipping |
| `#/parts` | Bill of materials (CSV download) |
| `#/guide` | Step-by-step build guide (print / save as PDF) |
| `#/checkout`, `#/account` | Prototype checkout; demo orders saved in the browser |
| `#/contact` | Contact form (not wired to email yet) |

## Code map

| File | Responsibility |
|---|---|
| `js/app.js` | Router, shared state, all screens |
| `js/palette.js` | Brick colours and closest-colour matching (CIE Lab) |
| `js/build.js` | Voxel grid model, piece merging (1x1–1x4), parts list, size, build time, price |
| `js/mosaic.js` | Photo → mosaic (framing, adjustments, dithering, plain-background replace), 2D drawing |
| `js/viewer3d.js` | three.js viewer (orbit, zoom, buttons), model loading, model → bricks voxeliser |
| `js/library.js` | Pixel font, sign designs and categories |
| `css/styles.css` | All styling |

## Not built yet (needs a backend or paid service)

- AI photo → 3D model generation (the sculpture flow takes a ready 3D file instead)
- AI background removal (a simple on-device "plain background" replace is included)
- Accounts/sign-in, real payment, order fulfilment, sending contact messages
- Prices use a sample price list in `js/build.js` (`UNIT_PRICE`), not live supplier prices
