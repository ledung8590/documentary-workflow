// no-real-media: no film or photo catches a V-2 arriving (it fell faster than sound, unseen); searched Commons "V-2 London impact", "V-2 strike 1944" (aftermath stills only, used elsewhere) – drawn street strike
// S044 "More than 3,000 were launched against targets including London and Antwerp.": a London street; a V-2 falls without warning,
// the street explodes, a house front collapses, people run; a second rocket strikes further off.
window.SCENE = {
  duration: 7, bg: 'paper', vignette: 0.2,
  events: [[1.30, 'blast', 'V-2 hits the street'], [1.50, 'burst', 'house front collapses'], [2.10, 'thud', 'falling masonry'], [4.80, 'blast', 'second V-2 further off'], [8.30, 'blast', 'third V-2 far off (only if extended)']],
  draw(c, T, L) {
    const C = L.C, gy = 780, tI = 1.3, t2 = 4.8, t3 = 8.3, ix = 1180;
    c.save(); K.shake(c, T, tI, 20, 3); K.shake(c, T, t2, 6, 4);
    // distant strikes behind the roofs
    [[t2, 420, 1.0], [t3, 1650, 0.8]].forEach(([tt, x, s]) => { const u = L.lin(T, tt - 0.45, tt); if (T > tt - 0.45 && T < tt) { L.line(c, [[x + 120 - 120 * u, -40 + 640 * u - 80], [x + 120 - 120 * u + 10, -40 + 640 * u]], 1, { color: C.fg, width: 6 }); }
      wK.blast(c, L, x, gy - 230, T, tt, s, { dark: true, up: true }); wK.column(c, L, x, gy - 260, T, { t0: tt + 0.5, h: 520, r: 30, n: 10 }); });
    // back row of terraced houses (the ones near the impact are drawn separately)
    const back = wK.houses(c, L, -40, 1960, gy - 40, { col: C.rule, h: [300, 420], w: [170, 230], seed: 7 });
    wK.ground(c, L, gy - 40, { col: C.bg2 });
    // front houses: the hit one collapses
    const H = [[0, 300, 330], [300, 260, 300], [560, 300, 350], [1380, 280, 320], [1660, 300, 360]];
    H.forEach(([x, w, h], i) => { c.fillStyle = C.fg2; c.fillRect(x, gy - h, w - 6, h); c.fillStyle = C.bg2; for (let r = 0; r < 3; r++) for (let q = 0; q < 3; q++) c.fillRect(x + 30 + q * 80, gy - h + 40 + r * 90, 34, 50);
      c.fillStyle = C.fg; c.fillRect(x + w / 2 - 22, gy - 80, 44, 80); c.fillStyle = C.fg2; c.beginPath(); c.moveTo(x - 6, gy - h); c.lineTo(x + w / 2, gy - h - 60); c.lineTo(x + w, gy - h); c.fill(); });
    const fall = L.ease(L.lin(T, tI + 0.1, tI + 1.4)), hh = 340 * (1 - 0.72 * fall);
    c.fillStyle = C.fg2; c.beginPath(); c.moveTo(880, gy); for (let k = 0; k <= 10; k++) c.lineTo(880 + k * 50, gy - hh + (fall > 0 ? (L.rnd(k, 3) * 90 * fall) : (k === 5 ? -60 : 0))); c.lineTo(1380, gy); c.fill();
    if (fall < 0.05) { c.fillStyle = C.bg2; for (let r = 0; r < 3; r++) for (let q = 0; q < 6; q++) c.fillRect(910 + q * 78, gy - 300 + r * 90, 34, 50); }
    for (let i = 0; i < 16; i++) { const a = T - tI - 0.1 - L.rnd(i, 5) * 0.4; if (a < 0 || a > 1.6) continue; const bx = 900 + L.rnd(i, 6) * 460, by = gy - 340 + L.rnd(i, 7) * 120 + 520 * a * a; if (by < gy) { c.fillStyle = C.fg2; c.fillRect(bx, by, 26, 18); } }
    // street lamp posts
    [[240, 1], [1560, 1]].forEach(([x]) => { c.fillStyle = C.fg; c.fillRect(x - 5, gy - 200, 10, 200); c.fillRect(x - 22, gy - 214, 44, 18); });
    // the rocket: falls almost straight down, unseen and unheard until it hits
    if (T < tI) { const u = L.lin(T, 0.55, tI), rx = ix + 140 - 140 * u, ry = -260 + (gy + 260) * u; if (T > 0.55) { c.save(); c.translate(rx, ry); c.rotate(0.19); c.scale(1.5, 1.5); c.fillStyle = C.fg;
      c.beginPath(); c.moveTo(0, 90); c.quadraticCurveTo(14, 60, 14, 20); c.lineTo(14, -70); c.lineTo(-14, -70); c.lineTo(-14, 20); c.quadraticCurveTo(-14, 60, 0, 90); c.fill(); c.fillRect(-28, -90, 56, 24); c.restore();
      for (let k = 1; k < 6; k++) L.line(c, [[rx + 30 * k * 0.19, ry - 80 * k], [rx + 30 * k * 0.19 + 6, ry - 80 * k - 40]], 1, { color: L.FG(0.25), width: 2 }); } }
    // the strike
    wK.blast(c, L, ix, gy, T, tI, 2.0, { dark: true });
    wK.fire(c, L, ix - 40, gy - 30, 300, T, { a: L.seg(T, tI + 0.5, tI + 1.2), h: 200 });
    wK.column(c, L, ix, gy - 120, T, { t0: tI + 0.7, h: 640, r: 46, n: 14, drift: 120 });
    // people: walking before, running for their lives after
    const P = [[700, 'suit', 'fedora', 0], [820, 'work', 'flatcap', 1], [1500, 'suit', 'none', 2], [1640, 'work', 'flatcap', 3], [1780, 'suit', 'fedora', 4], [420, 'work', 'none', 5]];
    P.forEach(([x0, side, hat, i]) => {
      const run = Math.max(0, T - tI - 0.15 - i * 0.06), dirR = x0 > ix ? 1 : -1, x = x0 + 26 * Math.min(T, tI) * (i % 2 ? 1 : -1) + dirR * 420 * run;
      const faceShock = T > tI + 0.1; K.doll(c, L, x, 846 - (i % 3) * 12, 190 + (i % 3) * 14, run > 0 ? T * 5 + i : T + i, { side, hat, face: faceShock ? (i % 2 ? 'shock' : 'shout') : 'calm', hair: i === 4 ? 'grey' : 'dark', tilt: run > 0 ? dirR * 0.14 : 0 });
    });
    c.restore();
    K.flashAt(c, T, tI, 0.25, 0.85);
    L.tag(c, 'London · 1944–45', 120, 140, T, 0.2, { size: 34, sub: 'V-2 strike (illustrative)' });
  },
};
