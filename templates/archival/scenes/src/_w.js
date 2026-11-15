// Group W helpers (combat scenes w-*, 2026-11-14): flat book-style vehicles, ships, aircraft, blasts and smoke in the look's
// colours (L.C); only flashes, fire and tracers are warm. Every scene lists its shots/blasts in SCENE.events = [[t, kind, note]]
// and draws them from the same list (events-w-*.txt is written from it, so picture and sound stay in sync).
const wK = {
  ev(S, kind) { return S.events.filter(e => !kind || (Array.isArray(kind) ? kind.includes(e[1]) : e[1] === kind)).map(e => e[0]); },
  // smoke puff: light = paper puff with an ink outline (book style), dark = ink wash (burning oil, fires)
  puff(c, L, x, y, r, a, dark) {
    if (a <= 0.01) return; c.save(); c.globalAlpha *= a;
    if (dark) { c.fillStyle = L.FG(0.55); c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); }
    else { c.fillStyle = L.C.bg2; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); c.strokeStyle = L.FG(0.3); c.lineWidth = 2; c.stroke(); }
    c.restore();
  },
  // rising smoke column in a loop from t0 (fires, burning ships); o: h height, n puffs, speed, drift, r, dark, a
  column(c, L, x, y, t, o = {}) {
    const t0 = o.t0 || 0; if (t < t0) return; const n = o.n || 18, H = o.h || 420, sp = o.speed || 0.3;
    for (let i = 0; i < n; i++) { const ph = (t - t0) * sp - i / n; if (ph < 0) continue; const u = ph % 1;
      const px = x + (L.rnd(i, 41) - 0.5) * (o.w ?? 70) * (1 + u) + u * (o.drift ?? 90) + Math.sin(i * 2.3 + t * 0.8) * 12 * (1 + u), py = y - u * H * (0.8 + 0.4 * L.rnd(i, 42)), r = (o.r || 34) * (0.6 + u * 1.8) * (0.7 + 0.6 * L.rnd(i, 43));
      wK.puff(c, L, px, py, r, (o.a ?? 0.8) * Math.min(1, u * 6) * (1 - u), o.dark ?? true); }
  },
  // flickering flames (warm) on a base line (x, y), width w
  fire(c, L, x, y, w, t, o = {}) {
    const h = o.h || w * 0.8, a = o.a ?? 1; if (a <= 0) return; c.save(); c.globalAlpha *= a;
    const gr = c.createRadialGradient(x, y - h * 0.3, 0, x, y - h * 0.3, w * 0.8); gr.addColorStop(0, 'rgba(255,170,70,0.3)'); gr.addColorStop(1, 'rgba(255,120,40,0)');
    c.fillStyle = gr; c.beginPath(); c.arc(x, y - h * 0.3, w * 0.8, 0, 7); c.fill();
    const n = o.n || 7;
    for (let i = 0; i < n; i++) { const fx = x + (L.rnd(i, 31) - 0.5) * w * 0.85, fh = h * (0.35 + 0.65 * L.rnd(i, 32)) * (0.75 + 0.25 * Math.sin(t * (8 + i) + i * 2.1)), fw = w / n * (1.4 + L.rnd(i, 33));
      const g = c.createLinearGradient(0, y, 0, y - fh); g.addColorStop(0, 'rgba(190,60,25,0.95)'); g.addColorStop(0.45, 'rgba(240,135,45,0.9)'); g.addColorStop(1, 'rgba(255,215,120,0)');
      const sw = Math.sin(t * 6 + i * 1.7) * fw * 0.35;
      c.fillStyle = g; c.beginPath(); c.moveTo(fx - fw / 2, y); c.bezierCurveTo(fx - fw * 0.6, y - fh * 0.45, fx + sw - fw * 0.2, y - fh * 0.7, fx + sw, y - fh); c.bezierCurveTo(fx + sw + fw * 0.1, y - fh * 0.6, fx + fw * 0.6, y - fh * 0.4, fx + fw / 2, y); c.fill(); }
    c.restore();
  },
  // explosion on the ground or a deck: flash, fireball, debris, rolling book-style smoke (o.dark adds an ink cloud; o.up = no lower half)
  blast(c, L, x, y, t, t0, s = 1, o = {}) {
    const age = t - t0; if (age < 0) return; const C = L.C;
    K.flash(c, L, x, y, t, t0, 2.2 * s);
    if (age < 1.0) { const u = age, R = s * (40 + 210 * L.easeOut(u / 0.45));
      c.save(); if (!o.air) { c.beginPath(); c.rect(-400, -400, 2720, y + 410); c.clip(); } c.globalAlpha *= Math.pow(1 - u, 1.2);
      for (let i = 0; i < 10; i++) { const an = Math.PI * (o.air ? 2 * L.rnd(i, 51) : 1 + L.rnd(i, 51)), d = R * 0.6 * L.rnd(i, 52), r = R * (0.32 + 0.3 * L.rnd(i, 53));
        c.fillStyle = i % 3 === 0 ? 'rgba(255,225,150,0.95)' : i % 3 === 1 ? 'rgba(240,145,55,0.92)' : 'rgba(200,80,35,0.9)';
        c.beginPath(); c.arc(x + Math.cos(an) * d, y + Math.sin(an) * d * 0.8 - (o.air ? 0 : R * 0.3), r, 0, 7); c.fill(); }
      c.restore(); }
    if (age < 1.4) for (let i = 0; i < 14; i++) { const an = Math.PI * (1.1 + 0.8 * L.rnd(i, 11)), v = (260 + 380 * L.rnd(i, 12)) * Math.sqrt(s);
      const dx = Math.cos(an) * v * age, dy = Math.sin(an) * v * age + 700 * age * age, r = (4 + 6 * L.rnd(i, 13)) * Math.sqrt(s);
      c.save(); c.globalAlpha *= 1 - age / 1.4; c.translate(x + dx, y + dy); c.rotate(age * 9 + i); c.fillStyle = C.fg; c.fillRect(-r, -r * 0.6, 2 * r, 1.2 * r); c.restore(); }
    if (o.dark) aSmoke(c, L, x, y - 30 * s, t, t0 + 0.1, { r: 260 * s, n: 12, size: 60 * s, alpha: 0.7, a0: Math.PI, a1: Math.PI * 2, rise: 200 * s, life: 4 });
    aSmoke(c, L, x, y, t, t0 + 0.05, { r: 320 * s, n: 16, size: 56 * s, alpha: 0.9, a0: Math.PI, a1: Math.PI * 2, rise: 110 * s, life: o.life || 3.5 });
  },
  // water column from a bomb or torpedo (paper-white spray with ink outline)
  splash(c, L, x, y, t, t0, s = 1) {
    const age = t - t0; if (age < 0 || age > 3) return; const up = L.easeOut(Math.min(1, age / 0.45)), fall = L.lin(age, 0.9, 3), H = 430 * s * up * (1 - 0.7 * fall), W = 70 * s * (1 + fall * 2);
    c.save(); c.globalAlpha *= 1 - fall * 0.9; c.fillStyle = L.C.panel; c.strokeStyle = L.FG(0.4); c.lineWidth = 2;
    c.beginPath(); c.moveTo(x - W, y); c.quadraticCurveTo(x - W * 0.6, y - H * 0.6, x - W * 0.3, y - H); c.quadraticCurveTo(x, y - H * 1.12, x + W * 0.3, y - H); c.quadraticCurveTo(x + W * 0.6, y - H * 0.6, x + W, y); c.closePath(); c.fill(); c.stroke();
    for (let i = 0; i < 10; i++) { const an = -Math.PI / 2 + (L.rnd(i, 3) - 0.5) * 1.6, v = 420 * s * (0.5 + L.rnd(i, 4)); L.dot(c, x + Math.cos(an) * v * age, y - H + Math.sin(an) * v * age + 500 * age * age * s, 6 * s, L.C.panel, 1 - fall); }
    c.restore(); K.flash(c, L, x, y, t, t0, 1.2 * s);
  },
  // tracer streak without glow (look rule), u 0..1 along the line
  tracer(c, x0, y0, x1, y1, u, col = 'rgba(240,150,60,0.95)', len = 0.1, w = 4) {
    if (u < 0 || u > 1) return; const a = Math.max(0, u - len);
    c.save(); c.strokeStyle = col; c.lineWidth = w; c.lineCap = 'round'; c.beginPath(); c.moveTo(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a); c.lineTo(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u); c.stroke(); c.restore();
  },
  // flight path through keys [[t, x, y], ...] (Catmull-Rom); returns {x, y, dir, rot} for wK.plane / A.side, or null outside the keys
  path(t, K) {
    const n = K.length; if (t < K[0][0] || t > K[n - 1][0]) return null;
    const cr = (a, b, c, d, u) => 0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u * u * u);
    const at = tt => { let i = 0; while (i < n - 2 && tt > K[i + 1][0]) i++; const u = Math.min(1, Math.max(0, (tt - K[i][0]) / (K[i + 1][0] - K[i][0])));
      const p0 = K[Math.max(0, i - 1)], p1 = K[i], p2 = K[i + 1], p3 = K[Math.min(n - 1, i + 2)]; return [cr(p0[1], p1[1], p2[1], p3[1], u), cr(p0[2], p1[2], p2[2], p3[2], u)]; };
    const [x, y] = at(t), t2 = Math.min(K[n - 1][0], t + 0.03), t1 = t2 - 0.03, [ax, ay] = at(t1), [bx, by] = at(t2), dx = bx - ax, dy = by - ay;
    return { x, y, dir: dx < 0 ? -1 : 1, rot: Math.atan2(dy, Math.abs(dx) + 1e-6) };
  },
  // falling bomb from (x0, y0) at t0 to (x1, y1) at t1 (ballistic arc), nose following the fall
  bomb(c, L, x0, y0, x1, y1, t, t0, t1, s = 1) {
    if (t < t0 || t > t1) return; const u = (t - t0) / (t1 - t0), x = x0 + (x1 - x0) * u, y = y0 + (y1 - y0) * u * u, an = Math.atan2(2 * (y1 - y0) * u, x1 - x0);
    c.save(); c.translate(x, y); c.rotate(an); c.fillStyle = L.C.fg; c.beginPath(); c.ellipse(0, 0, 22 * s, 8 * s, 0, 0, 7); c.fill(); c.fillRect(-30 * s, -9 * s, 10 * s, 18 * s); c.restore();
  },
  recoil(t, fires, d = 0.35) { let r = 0; (fires || []).forEach(f => { if (t > f && t < f + d) r = Math.max(r, 1 - (t - f) / d); }); return r; },
  star(c, x, y, r, col) { c.fillStyle = col; c.beginPath(); for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rr = k % 2 ? r * 0.42 : r; c.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); } c.closePath(); c.fill(); },
  // tank, side view facing right (o.dir -1 left); kind 'm1' | 't55' | 't72'; (x, y) = ground under the hull centre; w = length.
  // o.fire [t] (recoil + flash + smoke), o.elev (gun elevation rad), o.star (red star on the turret), o.dust (track dust), o.col
  tank(c, L, x, y, w, t, o = {}) {
    const C = L.C, u = w / 200, d = o.dir || 1, k = o.kind || 'm1', col = o.col || C.fg, rc = wK.recoil(t, o.fire) * 18;
    c.save(); c.translate(x, y); c.scale(d * u, u); c.fillStyle = col;
    const poly = pts => { c.beginPath(); pts.forEach(([px, py], i) => i ? c.lineTo(px, py) : c.moveTo(px, py)); c.closePath(); c.fill(); };
    // tracks and wheels
    c.beginPath(); c.moveTo(-96, -20); c.lineTo(94, -20); c.quadraticCurveTo(104, -10, 92, 0); c.lineTo(-90, 0); c.quadraticCurveTo(-104, -10, -96, -20); c.fill();
    const nw = k === 't55' ? 5 : 6, sp = 168 / (nw - 1), rot = (o.roll ?? x) / (u * 9);
    for (let i = 0; i < nw; i++) { const wx = -84 + i * sp; c.fillStyle = C.bg2; c.beginPath(); c.arc(wx, -10, k === 't55' ? 13 : 10, 0, 7); c.fill(); c.strokeStyle = col; c.lineWidth = 2.5;
      c.beginPath(); c.moveTo(wx + Math.cos(rot) * 9, -10 + Math.sin(rot) * 9); c.lineTo(wx - Math.cos(rot) * 9, -10 - Math.sin(rot) * 9); c.stroke(); }
    c.fillStyle = col;
    let gun;
    if (k === 'm1') { poly([[-100, -18], [-98, -42], [74, -42], [102, -26], [96, -16]]); poly([[-78, -42], [-72, -64], [34, -66], [62, -50], [56, -42]]); c.fillRect(-60, -72, 22, 8); gun = [56, -54, 96]; }
    else if (k === 't55') { poly([[-98, -16], [-94, -38], [84, -38], [102, -20]]); c.beginPath(); c.ellipse(-4, -38, 44, 26, 0, Math.PI, 0); c.fill(); c.fillRect(-22, -70, 18, 8); gun = [36, -50, 112]; }
    else { poly([[-98, -16], [-94, -36], [84, -36], [102, -20]]); c.beginPath(); c.ellipse(-2, -36, 46, 20, 0, Math.PI, 0); c.fill(); gun = [38, -46, 110]; }
    c.save(); c.translate(gun[0], gun[1]); c.rotate(-(o.elev || 0)); c.fillRect(-6 - rc, -4, gun[2], 8); if (k !== 'm1') c.fillRect(gun[2] * 0.55 - rc, -6, 14, 12); c.restore();
    if (o.star) wK.star(c, k === 't55' ? -6 : 0, k === 't55' ? -48 : -50, 10, C.accent2);
    if (o.mark) { c.fillStyle = C.bg2; c.fillRect(-40, -38, 26, 10); }  // inverted-V / panel marking
    c.restore();
    const an = -(o.elev || 0), L0 = gun[2] - 6;
    const mx = x + d * u * (gun[0] + Math.cos(an) * L0), my = y + u * (gun[1] + Math.sin(an) * L0);
    (o.fire || []).forEach(f => { K.flash(c, L, mx, my, t, f, 1.4 * u * 2); aSmoke(c, L, mx, my, t, f, { r: 120 * u * 2, n: 8, size: 26 * u * 2, alpha: 0.85, a0: d > 0 ? -0.8 : Math.PI - 0.8, a1: d > 0 ? 0.8 : Math.PI + 0.8, life: 2.2, rise: 30 }); });
    if (o.dust) for (let i = 0; i < 6; i++) { const ph = ((t * 1.3 + i / 6) % 1); wK.puff(c, L, x - d * u * (100 + ph * 160), y - 12 - ph * 40, (10 + ph * 30) * u * 1.6, 0.7 * (1 - ph), false); }
    return [mx, my];
  },
  // WWII aircraft from the kit's A.side ('tail' = nose engine), in the look's ink; o.mark 'hino' (red disc) | 'us' (white star in navy disc)
  plane(c, L, x, y, len, o = {}) {
    const C = L.C; A.side(c, x, y, len, { kind: o.kind || 'tail', dir: o.dir || 1, rot: o.rot || 0, fill: o.col || C.fg, wing: o.wing || C.fg, glass: C.bg2, gear: !!o.gear, alpha: o.alpha });
    const s = len / 1000; c.save(); c.translate(x, y); c.scale((o.dir || 1) * s, s); if (o.rot) c.rotate(o.rot);
    if (o.mark === 'hino') { c.fillStyle = C.panel; c.beginPath(); c.arc(-170, -4, 40, 0, 7); c.fill(); c.fillStyle = C.accent2; c.beginPath(); c.arc(-170, -4, 32, 0, 7); c.fill(); }
    else if (o.mark === 'us') { c.fillStyle = C.accent; c.beginPath(); c.arc(-170, -4, 36, 0, 7); c.fill(); wK.star(c, -170, -4, 30, C.panel); }
    c.strokeStyle = L.FG(0.5); c.lineWidth = 3 / s; c.beginPath(); c.moveTo(512, -150 * Math.abs(Math.sin((o.t || 0) * 40))); c.lineTo(512, 150 * Math.abs(Math.sin((o.t || 0) * 40))); c.stroke();
    c.restore();
  },
  // Martin MB-2 style twin-engine biplane bomber, side view, nose right
  biplane(c, L, x, y, len, t, o = {}) {
    const C = L.C, s = len / 1000; c.save(); c.translate(x, y); c.scale((o.dir || 1) * s, s); if (o.rot) c.rotate(o.rot); c.fillStyle = o.col || C.fg; c.strokeStyle = o.col || C.fg;
    c.beginPath(); c.moveTo(470, -10); c.quadraticCurveTo(480, -50, 420, -56); c.lineTo(-440, -30); c.lineTo(-470, -14); c.lineTo(-440, 4); c.lineTo(420, 30); c.quadraticCurveTo(476, 26, 470, -10); c.fill();
    c.fillRect(-180, -176, 420, 16); c.fillRect(-160, 34, 400, 14);  // upper and lower wing
    c.lineWidth = 7; [-140, 0, 200].forEach(sx => { c.beginPath(); c.moveTo(sx, -160); c.lineTo(sx, 36); c.stroke(); }); c.lineWidth = 3; c.beginPath(); c.moveTo(-140, -160); c.lineTo(0, 36); c.moveTo(0, -160); c.lineTo(200, 36); c.stroke();
    c.beginPath(); c.ellipse(110, -64, 90, 30, 0, 0, 7); c.fill();  // engine nacelle
    c.beginPath(); c.moveTo(-390, -32); c.lineTo(-440, -140); c.lineTo(-480, -140); c.lineTo(-470, -20); c.fill(); c.fillRect(-500, -16, 110, 10);
    c.lineWidth = 6; c.strokeStyle = L.FG(0.5); const pr = 120 * Math.abs(Math.sin((t || 0) * 37)); c.beginPath(); c.moveTo(206, -64 - pr); c.lineTo(206, -64 + pr); c.stroke();
    c.strokeStyle = o.col || C.fg; c.lineWidth = 6; c.beginPath(); c.moveTo(80, 48); c.lineTo(60, 110); c.moveTo(140, 48); c.lineTo(60, 110); c.stroke(); c.beginPath(); c.arc(60, 112, 26, 0, 7); c.fill();
    if (o.mark !== false) { c.fillStyle = C.panel; c.beginPath(); c.arc(-300, -8, 26, 0, 7); c.fill(); c.fillStyle = C.accent2; c.beginPath(); c.arc(-300, -8, 18, 0, 7); c.fill(); c.fillStyle = C.accent; c.beginPath(); c.arc(-300, -8, 9, 0, 7); c.fill(); }
    c.restore();
  },
  // UH-1 "Huey", side view nose right; t spins the rotors
  huey(c, L, x, y, len, t, o = {}) {
    const C = L.C, s = len / 1000, col = o.col || C.fg; c.save(); c.translate(x, y); c.scale((o.dir || 1) * s, s); if (o.rot) c.rotate(o.rot); c.fillStyle = col;
    c.beginPath(); c.moveTo(-170, -130); c.lineTo(150, -140); c.quadraticCurveTo(330, -130, 350, -20); c.quadraticCurveTo(340, 50, 250, 60); c.lineTo(-170, 60); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(-170, -120); c.lineTo(-600, -90); c.lineTo(-600, -60); c.lineTo(-170, -10); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(-560, -80); c.lineTo(-620, -200); c.lineTo(-660, -200); c.lineTo(-620, -60); c.fill(); c.fillRect(-470, -96, 60, 16);
    c.fillStyle = C.bg2; c.beginPath(); c.moveTo(200, -120); c.quadraticCurveTo(320, -110, 336, -30); c.lineTo(200, -30); c.closePath(); c.fill();  // windscreen
    if (o.door !== false) { c.fillStyle = L.FG2(0.9); c.fillRect(-120, -110, 230, 150); }
    c.fillStyle = col; c.fillRect(-30, -190, 50, 60);  // mast
    c.strokeStyle = col; c.lineWidth = 9; c.beginPath(); c.moveTo(-200, 120); c.lineTo(300, 120); c.quadraticCurveTo(340, 120, 340, 100); c.moveTo(-120, 60); c.lineTo(-140, 120); c.moveTo(180, 60); c.lineTo(200, 120); c.stroke();
    const r = 620 * Math.cos(t * 23); c.lineWidth = 10; c.beginPath(); c.moveTo(-5 - r, -192); c.lineTo(-5 + r, -192); c.stroke();
    c.strokeStyle = L.FG(0.18); c.lineWidth = 4; c.beginPath(); c.ellipse(-5, -192, 620, 22, 0, 0, 7); c.stroke();
    const tr = 70 * Math.cos(t * 41); c.strokeStyle = col; c.lineWidth = 7; c.beginPath(); c.moveTo(-630, -150 - tr); c.lineTo(-630, -150 + tr); c.stroke();
    if (o.star) { c.fillStyle = C.panel; c.beginPath(); c.arc(-330, -70, 26, 0, 7); c.fill(); wK.star(c, -330, -70, 22, col); }
    c.restore();
  },
  // ships, side view facing right; (x, y) = waterline centre, len px. kind 'bb' battleship | 'cv' carrier (oblique deck, o.hino) | 'cargo' Liberty | 'sub' U-boat
  ship(c, L, x, y, len, t, o = {}) {
    const C = L.C, s = len / 1000, col = o.col || C.fg; c.save(); c.translate(x, y + (o.sink || 0)); c.rotate(o.list || 0); c.scale((o.dir || 1) * s, s); c.fillStyle = col;
    const poly = pts => { c.beginPath(); pts.forEach(([px, py], i) => i ? c.lineTo(px, py) : c.moveTo(px, py)); c.closePath(); c.fill(); };
    const k = o.kind || 'bb';
    if (k === 'bb') {
      poly([[-500, -46], [470, -56], [510, -80], [470, 40], [-460, 40], [-505, -26]]);
      c.fillRect(-150, -110, 260, 66); c.fillRect(40, -170, 70, 70); c.fillRect(-120, -160, 50, 52); c.fillRect(-40, -150, 44, 44);  // superstructure, bridge, funnels
      c.lineWidth = 9; c.strokeStyle = col; c.beginPath(); c.moveTo(75, -170); c.lineTo(75, -330); c.moveTo(40, -170); c.lineTo(75, -320); c.moveTo(110, -170); c.lineTo(75, -320); c.moveTo(-230, -56); c.lineTo(-230, -290); c.stroke();
      c.fillRect(55, -350, 40, 24); c.fillRect(-250, -300, 40, 20);
      [[300, -56, 1], [200, -90, 1], [-280, -90, -1], [-380, -56, -1]].forEach(([tx, ty, dd]) => { c.fillRect(tx - 44, ty - 34, 88, 36); c.fillRect(tx + (dd > 0 ? 30 : -120), ty - 24, 90, 9); c.fillRect(tx + (dd > 0 ? 30 : -120), ty - 12, 90, 9); });
      if (o.mast !== false) { c.strokeStyle = L.FG(0.3); c.lineWidth = 2; c.beginPath(); c.moveTo(75, -340); c.lineTo(500, -70); c.moveTo(-230, -290); c.lineTo(-500, -48); c.stroke(); }
    } else if (k === 'cv') {
      poly([[-480, -40], [470, -40], [500, -60], [460, 40], [-450, 40], [-490, -20]]);
      c.fillStyle = L.FG2(1); c.fillRect(-470, -78, 920, 38); c.fillStyle = col;  // open hangar side
      for (let i = 0; i < 12; i++) c.fillRect(-460 + i * 78, -78, 8, 38);
      c.fillStyle = C.bg2; c.beginPath(); c.moveTo(-540, -80); c.lineTo(540, -80); c.lineTo(500, -150); c.lineTo(-500, -150); c.closePath(); c.fill();  // oblique flight deck
      c.strokeStyle = col; c.lineWidth = 5; c.stroke(); c.lineWidth = 2; c.strokeStyle = L.FG(0.3); for (let i = 1; i < 6; i++) { c.beginPath(); c.moveTo(-520 + i * 4, -80 - i * 12); c.lineTo(520 - i * 4, -80 - i * 12); c.stroke(); }
      if (o.hino !== false) { c.fillStyle = C.accent2; c.beginPath(); c.ellipse(330, -114, 46, 18, 0, 0, 7); c.fill(); }
      c.fillStyle = col; c.fillRect(-40, -210, 70, 64); c.fillRect(-10, -260, 16, 50);  // island
      (o.parked || []).forEach(px => { c.fillStyle = col; c.fillRect(px - 26, -126, 52, 8); c.fillRect(px - 6, -140, 12, 30); });
    } else if (k === 'cargo') {
      poly([[-500, -60], [470, -70], [510, -96], [470, 40], [-460, 40], [-505, -40]]);
      c.fillRect(-90, -160, 180, 100); c.fillRect(-20, -230, 44, 70); c.fillRect(-120, -190, 240, 30);
      c.lineWidth = 8; c.strokeStyle = col; [[-300, -330], [270, -320]].forEach(([mx, my]) => { c.beginPath(); c.moveTo(mx, -64); c.lineTo(mx, my); c.stroke(); });
      c.lineWidth = 4; c.beginPath(); c.moveTo(-300, -260); c.lineTo(-420, -80); c.moveTo(270, -250); c.lineTo(400, -90); c.stroke();
      [-380, -220, 190, 340].forEach(bx => c.fillRect(bx - 40, -100, 80, 36));  // deck cargo
    } else {  // Type VII U-boat
      c.beginPath(); c.moveTo(-500, 0); c.quadraticCurveTo(-200, -40, 300, -36); c.quadraticCurveTo(470, -30, 510, -6); c.quadraticCurveTo(470, 26, 300, 30); c.quadraticCurveTo(-200, 34, -500, 0); c.fill();
      poly([[-90, -36], [-70, -110], [80, -110], [110, -36]]); c.fillRect(-10, -190, 8, 80); c.fillRect(150, -56, 70, 10);
    }
    c.restore();
  },
  // flat sea from y top to the bottom: navy band with moving cream wave lines; returns surface y at x
  sea(c, L, top, t, o = {}) {
    const C = L.C; c.fillStyle = o.col || C.accent; c.beginPath(); c.moveTo(0, 1080); for (let x = 0; x <= 1920; x += 40) c.lineTo(x, top + Math.sin(x * 0.012 + t * 1.6) * 4); c.lineTo(1920, 1080); c.fill();
    for (let i = 0; i < (o.lines ?? 9); i++) { const y = top + 18 + i * i * 7, sh = (t * (20 + i * 6)) % 160; c.strokeStyle = L.BOX(0.18 + 0.02 * i); c.lineWidth = 2;
      for (let x = -160 + sh; x < 1920; x += 160) { c.beginPath(); c.moveTo(x, y); c.quadraticCurveTo(x + 30, y - 5, x + 60, y); c.stroke(); } }
  },
  // clip helper: draw fn only above (or below) the waterline y
  above(c, y, fn) { c.save(); c.beginPath(); c.rect(-400, -400, 2720, y + 400); c.clip(); fn(); c.restore(); },
  below(c, y, fn) { c.save(); c.beginPath(); c.rect(-400, y, 2720, 1500); c.clip(); fn(); c.restore(); },
  // terraced street front: buildings between x0 and x1 standing on gy; o.h [min, max], o.col, o.win, o.seed, o.roof
  houses(c, L, x0, x1, gy, o = {}) {
    const C = L.C, out = []; let x = x0, i = o.seed || 0;
    while (x < x1) { const w = (o.w || [150, 240])[0] + L.rnd(i, 21) * ((o.w || [150, 240])[1] - (o.w || [150, 240])[0]), h = (o.h || [220, 380])[0] + L.rnd(i, 22) * ((o.h || [220, 380])[1] - (o.h || [220, 380])[0]);
      c.fillStyle = o.col || C.fg2; c.fillRect(x, gy - h, w - 4, h);
      if (o.roof !== false) { c.beginPath(); c.moveTo(x - 6, gy - h); c.lineTo(x + w / 2, gy - h - 50 * L.rnd(i, 23)); c.lineTo(x + w + 2, gy - h); c.fill(); c.fillRect(x + w * 0.7, gy - h - 40, 18, 40); }
      c.fillStyle = o.win || C.bg2; for (let r = 0; r < Math.floor(h / 80) - 1; r++) for (let q = 0; q < Math.floor(w / 60); q++) c.fillRect(x + 18 + q * 60, gy - h + 30 + r * 80, 26, 38);
      out.push([x, w, h]); x += w; i++; }
    return out;
  },
  // drawn soldier holding a long arm level and firing it: K.doll + musket/rifle; o.gun 'musket' | 'rifle'; o.fire [t]; o.aim (raise level)
  shooter(c, L, x, y, h, t, o = {}) {
    const d = o.dir || 1, s = h / 400;
    K.doll(c, L, x, y, h, t, Object.assign({ face: 'grim' }, o.doll || {}, { dir: d }));
    const rc = wK.recoil(t, o.fire, 0.25) * 18 * s, gy = y - 210 * s, gx = x + d * (60 * s - rc);
    c.save(); c.translate(gx, gy); c.scale(d, 1); c.rotate(-(o.elev || 0));
    if ((o.gun || 'musket') === 'musket') K.musket(c, 120 * s, 0, 480 * s, { wood: '#5a3e26', metal: '#55524c' });
    else { c.fillStyle = '#3a3226'; c.fillRect(-40 * s, -10 * s, 150 * s, 22 * s); c.fillStyle = '#26241f'; c.fillRect(100 * s, -8 * s, 200 * s, 12 * s); c.fillRect(30 * s, 8 * s, 18 * s, 40 * s); }
    c.restore();
    const reach = (o.gun || 'musket') === 'musket' ? 410 : 300, mx = gx + d * reach * s * Math.cos(o.elev || 0), my = gy - 6 * s - reach * s * Math.sin(o.elev || 0);
    (o.fire || []).forEach(f => { K.flash(c, L, mx, my, t, f, (o.gun || 'musket') === 'musket' ? 0.7 : 0.45);
      if ((o.gun || 'musket') === 'musket') aSmoke(c, L, mx + d * 20, my, t, f, { r: 90, n: 6, size: 26, alpha: 0.8, a0: d > 0 ? -0.6 : Math.PI - 0.6, a1: d > 0 ? 0.6 : Math.PI + 0.6, life: 2.6, rise: 20 }); });
    return [mx, my];
  },
  // Civil War field gun (12-pdr Napoleon): spoked wheel, trail, barrel in ink; fires to dir with recoil, flash and a big white cloud
  gun(c, L, x, y, len, t, o = {}) {
    const C = L.C, d = o.dir || 1, s = len / 300, rc = wK.recoil(t, o.fire, 0.5) * 30 * s, X = x - d * rc, R = 62 * s;
    c.save(); c.strokeStyle = C.fg; c.lineWidth = 10 * s; c.beginPath(); c.moveTo(X, y - R); c.lineTo(X - d * 200 * s, y - 4); c.stroke(); c.restore();
    K.cannon(c, X + d * 40 * s, y - R - 20 * s, 220 * s, { dir: d, rot: -0.06, light: C.fg2, col: C.fg });
    c.strokeStyle = C.fg; c.lineWidth = 7 * s; c.beginPath(); c.arc(X, y - R, R, 0, 7); c.stroke(); const wr = -rc / R;
    for (let k = 0; k < 7; k++) { const a = k * Math.PI / 7 * 2 + wr; c.lineWidth = 4 * s; c.beginPath(); c.moveTo(X, y - R); c.lineTo(X + Math.cos(a) * R, y - R + Math.sin(a) * R); c.stroke(); }
    const mx = X + d * 150 * s, my = y - R - 30 * s;
    (o.fire || []).forEach(f => { K.flash(c, L, mx, my, t, f, 1.6 * s); aSmoke(c, L, mx + d * 40 * s, my, t, f, { r: 260 * s, n: 12, size: 54 * s, alpha: 0.9, a0: d > 0 ? -0.9 : Math.PI - 0.9, a1: d > 0 ? 0.7 : Math.PI + 0.7, life: 3.5, rise: 40 }); });
    return [mx, my];
  },
  // waving flag on a pole held at (x, y) (pole foot); kind 'csa' battle flag | 'usa' | 'cz' (Czechoslovakia) | 'irq'; w cloth width
  flag(c, L, x, y, w, kind, t, o = {}) {
    const C = L.C, h = w * 0.66, pole = o.pole || w * 1.9, top = y - pole, n = 14;
    c.strokeStyle = C.fg; c.lineWidth = Math.max(3, w / 30); c.beginPath(); c.moveTo(x, y); c.lineTo(x, top - 6); c.stroke();
    const d = o.dir || 1, wv = u => Math.sin(t * 6 - u * 5) * w * 0.06 * u;
    const at = (u, v) => [x + d * u * w, top + v * h + wv(u)];
    for (let i = 0; i < n; i++) { const u0 = i / n, u1 = (i + 1) / n;
      const strip = (v0, v1, col) => { const a = at(u0, v0), b = at(u1, v0), e = at(u1, v1), f = at(u0, v1); c.fillStyle = col; c.beginPath(); c.moveTo(...a); c.lineTo(...b); c.lineTo(...e); c.lineTo(...f); c.closePath(); c.fill(); };
      if (kind === 'csa') { strip(0, 1, C.accent2); }
      else if (kind === 'usa') { for (let k = 0; k < 7; k++) { strip(k / 7, (k + 0.5) / 7, C.accent2); strip((k + 0.5) / 7, (k + 1) / 7, C.panel); } if (u1 <= 0.43) strip(0, 0.54, C.accent); }
      else if (kind === 'cz') { strip(0, 0.5, C.panel); strip(0.5, 1, C.accent2); if (u1 <= 0.5) strip(u0, 1 - u0, C.accent); }
      else if (kind === 'irq') { strip(0, 0.33, C.accent2); strip(0.33, 0.66, C.panel); strip(0.66, 1, C.fg); } }
    if (kind === 'csa') { c.strokeStyle = C.panel; c.lineWidth = w * 0.16; c.beginPath(); c.moveTo(...at(0, 0)); c.lineTo(...at(1, 1)); c.moveTo(...at(1, 0)); c.lineTo(...at(0, 1)); c.stroke();
      c.strokeStyle = C.accent; c.lineWidth = w * 0.1; c.stroke(); for (let k = 1; k < 6; k++) { [[k / 6, k / 6], [k / 6, 1 - k / 6]].forEach(([u, v]) => L.dot(c, ...at(u, v), w * 0.018, C.panel)); } }
    c.strokeStyle = L.FG(0.5); c.lineWidth = 1.2; c.beginPath(); c.moveTo(...at(0, 0)); for (let i = 1; i <= n; i++) c.lineTo(...at(i / n, 0)); for (let i = n; i >= 0; i--) c.lineTo(...at(i / n, 1)); c.closePath(); c.stroke();
  },
  // ground band from gy down with a ruled horizon (book style)
  ground(c, L, gy, o = {}) { c.fillStyle = o.col || L.C.bg2; c.fillRect(-100, gy, 2120, 1300 - gy); L.line(c, [[-100, gy], [2020, gy]], 1, { color: L.C.fg, width: 3 }); },
};
