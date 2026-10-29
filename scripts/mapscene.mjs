// Record a map scene (maps/engine.html) frame by frame in headless Chromium and encode it with ffmpeg.
//   node scripts/mapscene.mjs <scene.json> <out.mp4> [--fps 24] [--dur seconds]
// Every frame waits until the terrain/imagery tiles are loaded, so output is deterministic (slow first run, tiles
// are then in the browser cache for the rest of the scene).
import fs from 'fs'; import http from 'http'; import path from 'path'; import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright-core';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2), opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const scene = JSON.parse(fs.readFileSync(args[0], 'utf8')), out = path.resolve(args[1]);
const FPS = +opt('--fps', 24), DUR = +opt('--dur', scene.duration || 6);

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.ttf': 'font/ttf', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({ headless: true, args: ['--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--use-angle=d3d11'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('page error:', e.message));
await page.goto(`http://127.0.0.1:${port}/maps/engine.html`);
await page.evaluate(s => window.setup(s), scene);

fs.mkdirSync(path.dirname(out), { recursive: true });
const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
const n = Math.ceil(DUR * FPS), t0 = Date.now();
for (let i = 0; i < n; i++) {
  await page.evaluate(t => window.renderAt(t), i / FPS);
  const jpg = await page.screenshot({ type: 'jpeg', quality: 93 });
  if (!ff.stdin.write(jpg)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % FPS === 0) process.stdout.write(`  map ${i}/${n} (${((Date.now() - t0) / 1000).toFixed(0)} s)\n`);
}
ff.stdin.end(); await new Promise(r => ff.on('close', r));
await browser.close(); server.close();
console.log(`map scene -> ${out}`);
