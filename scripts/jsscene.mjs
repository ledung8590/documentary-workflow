// Record a motion-graphics scene (scenes/engine.html + a scene .js) frame by frame in headless Chromium, encode with ffmpeg.
//   node scripts/jsscene.mjs <scene.js> <out.mp4> [--fps 24] [--dur seconds] [--still t out.jpg]
//   node scripts/jsscene.mjs <scene.js> <spans.json> --typing     typing spans, for typewriter SFX
//   node scripts/jsscene.mjs <scene.js> <out.mov> --alpha           transparent overlay (bg 'none', vignette 0) for a media_overlay fx clip
// The scene file sets window.SCENE = {duration, bg, draw(c, t, L)}; see docs/SCENES.md.
import fs from 'fs'; import http from 'http'; import path from 'path'; import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright-core';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2), opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const sceneFile = path.resolve(args[0]), out = path.resolve(args[1]);
if (!sceneFile.startsWith(ROOT)) throw new Error('scene file must be inside the workspace');
const FPS = +opt('--fps', 24);

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.ttf': 'font/ttf', '.json': 'application/json',
                '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p).toLowerCase()] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({ headless: true, args: ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
let err = null; page.on('pageerror', e => { err = e; console.error('page error:', e.message); });
await page.goto(`http://127.0.0.1:${port}/scenes/engine.html`);
const rel = '/' + path.relative(ROOT, sceneFile).split(path.sep).join('/');
const info = await page.evaluate(s => window.setup(s), rel);
const DUR = +opt('--dur', info.duration || 6);

if (args.includes('--typing')) {  // spans [[a, b], ...] (scene seconds) where L.typed() is still typing, for typewriter SFX
  const spans = []; let a = null;
  for (let i = 0; i <= Math.ceil(DUR * FPS); i++) {
    const on = await page.evaluate(t => { window.renderAt(t); return window.__typing; }, i / FPS);
    if (on && a === null) a = i / FPS;
    if (!on && a !== null) { spans.push([+a.toFixed(3), +(i / FPS).toFixed(3)]); a = null; }
  }
  if (a !== null) spans.push([+a.toFixed(3), +DUR.toFixed(3)]);
  fs.writeFileSync(out, JSON.stringify(spans));
} else if (args.includes('--still')) {  // one frame as jpg, for checking
  const i = args.indexOf('--still'), t = +args[i + 1];
  await page.evaluate(t => window.renderAt(t), t); await page.screenshot({ path: out, type: 'jpeg', quality: 90 });
} else {
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const alpha = args.includes('--alpha');  // PNG frames with transparency -> PNG-in-MOV (rgba), read by render_fx.MediaLayer
  if (alpha) await page.evaluate(() => { document.documentElement.style.background = document.body.style.background = 'transparent'; });
  const enc = alpha ? ['-c:v', 'png', '-pix_fmt', 'rgba', out] : ['-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', out];
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', alpha ? 'png' : 'mjpeg', '-i', '-',
    ...enc], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.ceil(DUR * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.renderAt(t), i / FPS);
    const jpg = alpha ? await page.screenshot({ type: 'png', omitBackground: true }) : await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(jpg)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close(); server.close();
if (err) process.exit(1);
console.log(`scene -> ${out}`);
