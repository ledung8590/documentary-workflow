// Render the exact HyperFrames "Film grain" tile (AutoVeo3 core/whisk_hf_engine.py, _CSS_GRAIN) in Chromium so the
// Python renderer can composite the same noise: fractalNoise baseFrequency 0.75, 4 octaves, desaturated, 200x200.
//   node scripts/grain_tile.mjs assets/fx/grain_tile.png
import fs from 'fs'; import path from 'path';
import { chromium } from 'playwright-core';

const out = path.resolve(process.argv[2] || 'assets/fx/grain_tile.png');
const svg = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'>" +
  "<feTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/>" +
  "<feColorMatrix type='saturate' values='0'/></filter><rect width='200' height='200' filter='url(%23n)'/></svg>";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 200, height: 200 }, deviceScaleFactor: 1 });
await page.setContent(`<html><body style="margin:0;background:transparent">
  <div style="width:200px;height:200px;background-image:url(&quot;${svg}&quot;);background-size:200px 200px"></div></body></html>`);
fs.mkdirSync(path.dirname(out), { recursive: true });
await page.screenshot({ path: out, omitBackground: true, clip: { x: 0, y: 0, width: 200, height: 200 } });
await browser.close();
console.log(`grain tile -> ${out}`);
