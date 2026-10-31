// Drawing kit for motion-graphics scenes (scenes/engine.html). House style: docs/STYLE.md.
// Every helper is a pure function of t, so any frame can be drawn on its own.
// Times: p = L.seg(t, a, b) is 0..1 progress between scene seconds a and b (eased with L.ease).
(function () {
  const W = 1920, H = 1080;
  const C = {
    offwhite: '#EDE7DC', red: '#C8372D', redhot: '#e0402f', amber: '#E0A030', parch: '#D9CCAA', brown: '#2B2119',
    ink: '#1a1512', blue: '#6f94d8', bluedeep: '#20324a', grey: '#8f877b', steel: '#b9b3a8', green: '#7fae7a',
  };
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ease = x => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const easeOut = x => 1 - Math.pow(1 - clamp(x), 3);
  const lerp = (a, b, p) => a + (b - a) * p;
  const seg = (t, a, b) => ease((t - a) / Math.max(1e-6, b - a));
  const lin = (t, a, b) => clamp((t - a) / Math.max(1e-6, b - a));
  // deterministic pseudo-random
  const rnd = (i, k = 0) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };

  // ---------- backgrounds
  let texCache = {};
  function texture(kind) {  // static mottled texture, cached per kind
    if (texCache[kind]) return texCache[kind];
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const g = cv.getContext('2d');
    const base = { brown: [43, 33, 25], parchment: [217, 204, 170], black: [14, 13, 12], ocean: [14, 24, 34], slate: [30, 32, 34] }[kind] || [14, 13, 12];
    g.fillStyle = `rgb(${base})`; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 900; i++) {  // soft blotches
      const x = rnd(i, 1) * W, y = rnd(i, 2) * H, r = 30 + rnd(i, 3) * 160, d = (rnd(i, 4) - 0.5) * (kind === 'parchment' ? 26 : 14);
      const gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, `rgba(${d > 0 ? '255,255,255' : '0,0,0'},${Math.abs(d) / 255})`); gr.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r);
    }
    return (texCache[kind] = cv);
  }
  function background(c, kind, t) {
    if (kind === 'none') { c.clearRect(0, 0, W, H); return; }
    c.drawImage(texture(kind), 0, 0);
    if (kind === 'ocean') {  // faint depth gradient
      const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, 'rgba(60,90,110,0.25)'); g.addColorStop(1, 'rgba(0,0,0,0.35)');
      c.fillStyle = g; c.fillRect(0, 0, W, H);
    }
  }
  function vignette(c, s) {
    if (!s) return;
    const g = c.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.0);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${s})`); c.fillStyle = g; c.fillRect(0, 0, W, H);
  }
  function grid(c, a, step = 80, color = 'rgba(237,231,220,0.06)') {  // blueprint/plotting grid
    c.save(); c.globalAlpha = a; c.strokeStyle = color; c.lineWidth = 1; c.beginPath();
    for (let x = 0; x <= W; x += step) { c.moveTo(x, 0); c.lineTo(x, H); }
    for (let y = 0; y <= H; y += step) { c.moveTo(0, y); c.lineTo(W, y); }
    c.stroke(); c.restore();
  }

  // ---------- text
  const FONTS = { head: '700 {s}px Oswald', headlight: '400 {s}px Oswald', body: '{s}px BeVN', mono: '{s}px Plex' };
  function font(c, f, s) { c.font = FONTS[f].replace('{s}', s); }
  function text(c, str, x, y, o = {}) {  // o: size, font, color, align, alpha, upper, spacing, base, shadow
    const s = o.size || 40; font(c, o.font || 'head', s);
    c.save(); c.globalAlpha *= o.alpha ?? 1; c.fillStyle = o.color || C.offwhite; c.textAlign = o.align || 'left';
    c.textBaseline = o.base || 'alphabetic';
    if (o.spacing) c.letterSpacing = o.spacing + 'px';
    if (o.shadow) { c.shadowColor = 'rgba(0,0,0,0.7)'; c.shadowBlur = 12; }
    const v = o.upper === false ? str : (o.font === 'body' || o.font === 'mono' ? str : str.toUpperCase());
    c.fillText(v, x, y); c.restore();
    font(c, o.font || 'head', s); return c.measureText(v).width;
  }
  function textW(c, str, f, s) { font(c, f, s); return c.measureText(str).width; }
  // typed text: reveals chars at cps from t0, block cursor
  function typed(c, str, x, y, t, t0, o = {}) {
    const n = Math.floor(clamp((t - t0) * (o.cps || 18), 0, str.length)); const part = str.slice(0, n);
    if (t >= t0 && n < str.length) window.__typing = true;  // read by scripts/jsscene.mjs --typing (typewriter SFX timing)
    const w = text(c, part, x, y, Object.assign({ font: 'mono', upper: false }, o));
    if (t >= t0 && (n < str.length || Math.floor(t * 2) % 2 === 0)) {
      c.fillStyle = o.color || C.offwhite; const s = o.size || 40; c.fillRect(x + w + 4, y - s * 0.85, s * 0.5, s);
    }
    return n >= str.length;
  }
  // card heading: small mono kicker, Oswald title, red rule that grows (stat/quote cards use this)
  function heading(c, kicker, title, t, o = {}) {
    const x = o.x ?? 150, y = o.y ?? 150, a = seg(t, o.t0 ?? 0, (o.t0 ?? 0) + 0.5);
    const dark = o.dark ?? true, col = dark ? C.offwhite : C.ink, sub = dark ? 'rgba(220,210,195,0.85)' : 'rgba(43,33,25,0.75)';
    if (kicker) text(c, kicker, x, y, { font: 'mono', size: 24, color: sub, alpha: a, upper: true });
    text(c, title, x, y + 58, { size: o.size || 52, color: col, alpha: a });
    c.fillStyle = C.red; c.fillRect(x, y + 80, (o.rule || 90) * seg(t, (o.t0 ?? 0) + 0.2, (o.t0 ?? 0) + 0.8), 5);
  }
  // credit line, bottom right (the renderer also draws clip credits; use this only for scene-internal sources)
  function source(c, str, a = 1) { text(c, str, W - 60, H - 40, { font: 'body', size: 22, align: 'right', color: 'rgba(237,231,220,0.8)', alpha: a, shadow: true }); }

  // ---------- strokes
  function path(c, pts) { c.beginPath(); pts.forEach((q, i) => i ? c.lineTo(q[0], q[1]) : c.moveTo(q[0], q[1])); }
  function partial(pts, p) {  // first p (0..1) of a polyline by length
    if (p >= 1) return pts; if (p <= 0) return [pts[0]];
    const d = [0]; for (let i = 1; i < pts.length; i++) d.push(d[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const L0 = d[d.length - 1] * p, out = [pts[0]];
    for (let i = 1; i < pts.length; i++) {
      if (d[i] >= L0) { const k = (L0 - d[i - 1]) / (d[i] - d[i - 1] || 1); out.push([lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k)]); break; }
      out.push(pts[i]);
    }
    return out;
  }
  function curve(a, b, bend = 0.2, n = 48) {  // quadratic arc between two points
    const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1];
    const cx = mx - dy * bend, cy = my + dx * bend, out = [];
    for (let i = 0; i <= n; i++) { const u = i / n; out.push([(1 - u) ** 2 * a[0] + 2 * (1 - u) * u * cx + u * u * b[0], (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * cy + u * u * b[1]]); }
    return out;
  }
  function line(c, pts, p = 1, o = {}) {  // o: color, width, dash, glow, alpha, march (dash offset speed, needs t)
    const q = partial(pts, p); if (q.length < 2) return q[q.length - 1];
    c.save(); c.globalAlpha *= o.alpha ?? 1; c.lineCap = 'round'; c.lineJoin = 'round';
    if (o.glow) { c.shadowColor = o.color || C.red; c.shadowBlur = o.glow; }
    c.strokeStyle = o.color || C.red; c.lineWidth = o.width || 4;
    if (o.dash) { c.setLineDash(o.dash); c.lineDashOffset = -(o.march || 0); }
    path(c, q); c.stroke(); c.restore(); return q[q.length - 1];
  }
  function arrow(c, pts, p = 1, o = {}) {  // tapered glowing arrow that grows along pts
    const q = partial(pts, p); if (q.length < 2) return;
    const w = o.width || 26, col = o.color || C.redhot, n = q.length;
    const L0 = q.map((_, i) => i);  // taper by index
    const left = [], right = [];
    for (let i = 0; i < n - 1; i++) {
      const a = q[i], b = q[i + 1], ang = Math.atan2(b[1] - a[1], b[0] - a[0]), ww = w * (0.35 + 0.5 * i / (n - 1)) / 2;
      left.push([a[0] + Math.cos(ang - Math.PI / 2) * ww, a[1] + Math.sin(ang - Math.PI / 2) * ww]);
      right.push([a[0] + Math.cos(ang + Math.PI / 2) * ww, a[1] + Math.sin(ang + Math.PI / 2) * ww]);
    }
    const e = q[n - 1], f = q[n - 2], ang = Math.atan2(e[1] - f[1], e[0] - f[0]), hw = w * 1.1, hl = w * 1.5;
    const base = [e[0] - Math.cos(ang) * hl, e[1] - Math.sin(ang) * hl];
    c.save(); c.globalAlpha *= o.alpha ?? 1; c.fillStyle = col; c.shadowColor = col; c.shadowBlur = o.glow ?? 24;
    c.beginPath(); left.forEach((pt, i) => i ? c.lineTo(...pt) : c.moveTo(...pt));
    c.lineTo(base[0] + Math.cos(ang - Math.PI / 2) * w * 0.42, base[1] + Math.sin(ang - Math.PI / 2) * w * 0.42);
    c.lineTo(base[0] + Math.cos(ang - Math.PI / 2) * hw, base[1] + Math.sin(ang - Math.PI / 2) * hw); c.lineTo(e[0], e[1]);
    c.lineTo(base[0] + Math.cos(ang + Math.PI / 2) * hw, base[1] + Math.sin(ang + Math.PI / 2) * hw);
    c.lineTo(base[0] + Math.cos(ang + Math.PI / 2) * w * 0.42, base[1] + Math.sin(ang + Math.PI / 2) * w * 0.42);
    right.slice().reverse().forEach(pt => c.lineTo(...pt)); c.closePath(); c.fill(); c.restore();
  }
  function circle(c, x, y, r, o = {}) {
    c.save(); c.globalAlpha *= o.alpha ?? 1; c.beginPath(); c.arc(x, y, Math.max(0, r), o.a0 ?? 0, o.a1 ?? Math.PI * 2);
    if (o.fill) { c.fillStyle = o.fill; c.fill(); }
    if (o.stroke) { c.strokeStyle = o.stroke; c.lineWidth = o.width || 3; if (o.dash) c.setLineDash(o.dash); if (o.glow) { c.shadowColor = o.stroke; c.shadowBlur = o.glow; } c.stroke(); }
    c.restore();
  }
  // expanding rings (sonar ping, impact, pulse): one ring every `every` s from t0, each grows to rmax over `life` s
  function rings(c, x, y, t, o = {}) {
    const t0 = o.t0 ?? 0, every = o.every ?? 1.2, life = o.life ?? 2.4, rmax = o.rmax ?? 300, col = o.color || C.offwhite;
    if (t < t0) return;
    for (let k = Math.max(0, Math.floor((t - t0 - life) / every)); k <= Math.floor((t - t0) / every); k++) {
      if (o.count && k >= o.count) break;
      const age = t - t0 - k * every; if (age < 0 || age > life) continue;
      const u = age / life; circle(c, x, y, easeOut(u) * rmax, { stroke: col, width: (o.width || 3) * (1 - u * 0.6), alpha: (1 - u) * (o.alpha ?? 0.9), glow: 10, a0: o.a0, a1: o.a1 });
    }
  }
  function dot(c, x, y, r, col, a = 1) { circle(c, x, y, r, { fill: col, alpha: a }); }
  // black map-style tag with a red accent bar; pops in at t0
  function tag(c, str, x, y, t, t0, o = {}) {
    const a = seg(t, t0, t0 + 0.35); if (a <= 0) return;
    const s = o.size || 34, sub = o.sub; font(c, 'head', s); const tw = c.measureText(str.toUpperCase()).width;
    const sw = sub ? textW(c, sub, 'body', s * 0.6) : 0, bw = Math.max(tw, sw) + 36, bh = sub ? s * 2.05 : s * 1.45;
    const bx = o.align === 'right' ? x - bw : o.align === 'center' ? x - bw / 2 : x, by = y - bh / 2 + (1 - a) * 12;
    c.save(); c.globalAlpha *= a; c.fillStyle = 'rgba(10,9,8,0.86)'; c.fillRect(bx, by, bw, bh);
    c.fillStyle = o.accent || C.red; c.fillRect(bx, by, 6, bh); c.restore();
    text(c, str, bx + 20, by + s * 1.08, { size: s, alpha: a });
    if (sub) text(c, sub, bx + 20, by + s * 1.75, { font: 'body', size: s * 0.6, color: '#d8d2c6', alpha: a });
  }

  // ---------- vessels (side view silhouettes, facing right; flip with dir -1)
  // kind: 'akula' (long hump fin + pod on rudder), 'la' (US Los Angeles: fin forward, fairwater planes), 'victor', 'typhoon', 'ssbn', 'ship'
  function sub(c, x, y, len, o = {}) {
    const k = o.kind || 'akula', dir = o.dir || 1, col = o.color || C.steel;
    c.save(); c.translate(x, y); c.scale(dir * len / 400, len / 400); c.globalAlpha *= o.alpha ?? 1;
    c.fillStyle = col; if (o.glow) { c.shadowColor = o.glowColor || col; c.shadowBlur = o.glow; }
    c.beginPath();
    if (k === 'ship') {  // surface warship
      c.moveTo(-200, -10); c.lineTo(190, -10); c.lineTo(205, -26); c.lineTo(180, 22); c.lineTo(-180, 22); c.closePath(); c.fill();
      c.fillRect(-60, -40, 90, 32); c.fillRect(-20, -70, 30, 32); c.fillRect(-120, -26, 40, 18); c.fillRect(80, -26, 40, 18);
      c.restore(); return;
    }
    const hl = k === 'typhoon' ? 26 : k === 'ssbn' ? 20 : 17;  // half height of the hull
    c.moveTo(-200, 0); c.bezierCurveTo(-190, -hl, -150, -hl, -120, -hl); c.lineTo(150, -hl);
    c.bezierCurveTo(185, -hl, 200, -8, 202, 0); c.bezierCurveTo(200, 8, 185, hl, 150, hl); c.lineTo(-120, hl);
    c.bezierCurveTo(-150, hl, -185, 8, -200, 0); c.closePath(); c.fill();
    // fin / sail
    c.beginPath();
    if (k === 'akula') { c.moveTo(20, -hl + 1); c.bezierCurveTo(30, -hl - 44, 95, -hl - 46, 120, -hl - 30); c.lineTo(140, -hl + 1); c.closePath(); }
    else if (k === 'la') { c.moveTo(70, -hl + 1); c.lineTo(78, -hl - 46); c.lineTo(118, -hl - 46); c.lineTo(124, -hl + 1); c.closePath(); c.fillRect(56, -hl - 34, 82, 5); }
    else if (k === 'victor') { c.moveTo(30, -hl + 1); c.bezierCurveTo(40, -hl - 36, 100, -hl - 38, 116, -hl - 24); c.lineTo(126, -hl + 1); c.closePath(); }
    else if (k === 'typhoon') { c.moveTo(-10, -hl + 1); c.bezierCurveTo(0, -hl - 40, 50, -hl - 42, 70, -hl - 30); c.lineTo(84, -hl + 1); c.closePath(); }
    else { c.moveTo(40, -hl + 1); c.lineTo(48, -hl - 40); c.lineTo(90, -hl - 40); c.lineTo(98, -hl + 1); c.closePath(); }
    c.fill();
    // rudder / tail + akula pod
    c.beginPath(); c.moveTo(-170, -hl + 6); c.lineTo(-200, -hl - 22); c.lineTo(-188, -hl - 22); c.lineTo(-150, -hl + 2); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(-170, hl - 6); c.lineTo(-200, hl + 18); c.lineTo(-188, hl + 18); c.lineTo(-150, hl - 2); c.closePath(); c.fill();
    if (k === 'akula') { c.beginPath(); c.ellipse(-182, -hl - 26, 14, 7, 0, 0, Math.PI * 2); c.fill(); }
    c.restore();
  }
  // propeller wash / noise: little arcs radiating backwards from the stern
  function noise(c, x, y, t, o = {}) {
    const dir = o.dir || 1, n = o.n || 4, col = o.color || C.amber, strength = o.strength ?? 1;
    for (let i = 0; i < n; i++) {
      const u = ((t * (o.speed || 0.9) + i / n) % 1), r = 20 + u * (o.reach || 260) * strength;
      circle(c, x, y, r, { stroke: col, width: 3, alpha: (1 - u) * 0.8 * strength, a0: dir > 0 ? Math.PI * 0.7 : -Math.PI * 0.3, a1: dir > 0 ? Math.PI * 1.3 : Math.PI * 0.3, glow: 8 });
    }
  }
  // water column with surface line and depth layers; returns y of the surface
  function sea(c, o = {}) {
    const top = o.top ?? 200, g = c.createLinearGradient(0, top, 0, H);
    g.addColorStop(0, o.c0 || 'rgba(70,100,120,0.35)'); g.addColorStop(1, o.c1 || 'rgba(5,10,16,0.75)');
    c.fillStyle = g; c.fillRect(0, top, W, H - top);
    if (o.surface !== false) line(c, wavePts(0, W, top, 6, o.t || 0, 140), 1, { color: 'rgba(237,231,220,0.55)', width: 2 });
    return top;
  }
  function wavePts(x0, x1, y, amp, t, len = 120, n = 160) {
    const out = []; for (let i = 0; i <= n; i++) { const x = lerp(x0, x1, i / n); out.push([x, y + Math.sin(x / len * Math.PI * 2 + t * 1.6) * amp]); } return out;
  }

  // ---------- data
  // animated counter text: value v reached at progress p (formats thousands with commas)
  function counter(v, p, dec = 0) { const x = v * ease(p); return x.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }); }
  // horizontal bars: items [{label, value, color, note}], max, box {x,y,w,h}, staggered from t0
  function hbars(c, items, t, t0, box, o = {}) {
    const n = items.length, gap = box.h / n, max = o.max || Math.max(...items.map(i => i.value));
    items.forEach((it, i) => {
      const a = t0 + i * (o.stagger ?? 0.6), p = seg(t, a, a + (o.grow ?? 1.2)), y = box.y + i * gap, bh = Math.min(70, gap * 0.55);
      text(c, it.label, box.x, y + bh * 0.2, { size: 34, alpha: seg(t, a - 0.2, a + 0.2), color: o.dark === false ? C.ink : C.offwhite });
      c.fillStyle = 'rgba(237,231,220,0.08)'; c.fillRect(box.x, y + bh * 0.45, box.w, bh);
      c.save(); c.fillStyle = it.color || C.red; c.shadowColor = it.color || C.red; c.shadowBlur = 12;
      c.fillRect(box.x, y + bh * 0.45, box.w * (it.value / max) * p, bh); c.restore();
      const lbl = (o.fmt ? o.fmt(it.value * p, it) : counter(it.value, p)) + (it.unit || '');
      text(c, lbl, box.x + box.w * (it.value / max) * p + 18, y + bh * 1.25, { size: 44, alpha: seg(t, a, a + 0.3), color: o.dark === false ? C.ink : C.offwhite });
      if (it.note) text(c, it.note, box.x, y + bh * 2.15, { font: 'body', size: 22, color: o.dark === false ? 'rgba(43,33,25,0.75)' : 'rgba(220,210,195,0.8)', alpha: seg(t, a + 0.5, a + 0.9) });
    });
  }
  // timeline axis with events [{t:year, label, sub, at:sceneSec, color}]
  function timeline(c, y0, y1, years, events, t, o = {}) {
    const x0 = o.x0 ?? 160, x1 = o.x1 ?? W - 160, X = yr => lerp(x0, x1, (yr - years[0]) / (years[1] - years[0]));
    line(c, [[x0, y0], [x1, y0]], seg(t, o.t0 ?? 0, (o.t0 ?? 0) + 1.2), { color: 'rgba(237,231,220,0.7)', width: 3 });
    for (let yr = Math.ceil(years[0] / (o.tick || 10)) * (o.tick || 10); yr <= years[1]; yr += o.tick || 10)
      text(c, String(yr), X(yr), y0 + 50, { size: 26, align: 'center', color: C.grey, alpha: seg(t, (o.t0 ?? 0) + 0.6, (o.t0 ?? 0) + 1.2) });
    events.forEach((e, i) => {
      const a = seg(t, e.at, e.at + 0.4), x = X(e.t), up = i % 2 === 0, h = up ? -(y0 - y1) : (y0 - y1) * 0.55;
      if (a <= 0) return; dot(c, x, y0, 10 * a, e.color || C.red);
      line(c, [[x, y0], [x, y0 + h * 0.35]], a, { color: e.color || C.red, width: 2 });
      text(c, e.label, x, y0 + h * 0.35 + (up ? -16 : 40), { size: 34, align: 'center', alpha: a });
      if (e.sub) text(c, e.sub, x, y0 + h * 0.35 + (up ? -60 : 74), { font: 'body', size: 22, align: 'center', color: 'rgba(220,210,195,0.85)', alpha: a });
    });
  }
  // node graph: nodes {id:[x,y,label,sub,at]}, edges [[a,b,at,{color,dash}]]
  function network(c, nodes, edges, t, o = {}) {
    edges.forEach(([a, b, at, eo = {}]) => { const A = nodes[a], B = nodes[b]; line(c, [[A[0], A[1]], [B[0], B[1]]], seg(t, at, at + 0.7), Object.assign({ color: 'rgba(200,55,45,0.85)', width: 3, dash: [10, 8], march: t * 30 }, eo)); });
    Object.values(nodes).forEach(([x, y, label, sub, at, col]) => {
      const a = seg(t, at, at + 0.4); if (a <= 0) return;
      circle(c, x, y, 34 * easeOut(a), { fill: '#120f0d', stroke: col || C.red, width: 4, glow: 14 });
      text(c, label, x, y + 82, { size: 32, align: 'center', alpha: a });
      if (sub) text(c, sub, x, y + 114, { font: 'body', size: 21, align: 'center', color: 'rgba(220,210,195,0.85)', alpha: a });
    });
  }

  window.L = { W, H, C, clamp, ease, easeOut, lerp, seg, lin, rnd, background, vignette, grid, text, textW, typed, heading, source,
               path, partial, curve, line, arrow, circle, rings, dot, tag, sub, noise, sea, wavePts, counter, hbars, timeline, network };
})();
