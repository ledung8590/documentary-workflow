// no-real-media: the real Pearl Harbor photos/film (p-b-pearl and others) are well worn and an earlier film used them; searched Commons "Pearl Harbor attack film", "USS Arizona explosion" – this beat is drawn instead
// S282 "After the Japanese attack on Pearl Harbor on December 7, 1941, America didn't negotiate or step back.": Battleship Row at
// anchor; Japanese dive bombers plunge and pull out, a torpedo plane drops low, a torpedo runs into the outboard battleship, a bomb
// sets off the middle ship's magazine; anti-aircraft bursts fill the sky, the ships burn.
window.SCENE = {
  duration: 7, bg: 'paper', vignette: 0.2,
  events: [[0.3, 'dive', 'first dive bomber'], [1.4, 'flyby', 'torpedo plane low'], [1.85, 'blast', 'bomb hits the right battleship'], [2.4, 'dive', 'second dive bomber'], [2.7, 'mg', 'anti-aircraft fire'],
    [3.3, 'blast', 'torpedo hits the outboard battleship'], [3.85, 'burst', 'bomb hits the middle battleship'], [4.25, 'blast', 'magazine explodes'], [4.8, 'dive', 'third dive bomber'],
    [5.3, 'mg', 'anti-aircraft fire'], [6.25, 'blast', 'bomb hits the right battleship'], [6.8, 'flyby', 'plane pulls out'], [7.3, 'burst', 'anti-aircraft burst']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, sea = 620, wl = 720;
    c.save(); wK.ev(S, 'blast').forEach(tt => K.shake(c, T, tt, tt === 4.25 ? 26 : 8, 3));
    // Oahu hills and Ford Island behind
    c.fillStyle = C.rule; c.beginPath(); c.moveTo(0, sea); [[0, 470], [300, 420], [520, 500], [900, 380], [1250, 470], [1600, 400], [1920, 480]].forEach(([x, y]) => c.lineTo(x, y)); c.lineTo(1920, sea); c.fill();
    // anti-aircraft bursts (ink puffs) all over the sky
    for (let i = 0; i < 26; i++) { const t0 = 0.6 + i * 0.27, a = T - t0; if (a < 0 || a > 2.2) continue; const x = 200 + L.rnd(i, 61) * 1600, y = 120 + L.rnd(i, 62) * 300;
      if (a < 0.1) L.dot(c, x, y, 10, 'rgba(255,200,120,0.9)'); wK.puff(c, L, x + a * 10, y - a * 6, 14 + 26 * Math.min(1, a * 3), 0.9 * (1 - a / 2.2), true); }
    wK.sea(c, L, sea, T, { lines: 6 });
    // Battleship Row
    const sink1 = L.seg(T, 3.4, 9), sink2 = L.seg(T, 4.3, 9);
    const ships = [[400, { list: 0.22 * sink1, sink: 40 * sink1 }], [1000, { sink: 70 * sink2, list: -0.04 * sink2 }], [1600, { list: 0.03 * L.seg(T, 1.9, 6) }]];
    wK.above(c, wl + 6, () => ships.forEach(([x, o]) => wK.ship(c, L, x, wl, 560, T, Object.assign({ kind: 'bb', col: C.fg2 }, o))));
    // fires and smoke on the hit ships
    wK.fire(c, L, 1600, wl - 60, 180, T, { a: L.seg(T, 2.0, 2.6), h: 110 }); wK.column(c, L, 1600, wl - 100, T, { t0: 2.1, h: 520, r: 30, drift: -120 });
    wK.fire(c, L, 420, wl - 40, 200, T, { a: L.seg(T, 3.5, 4.2), h: 100 }); wK.column(c, L, 420, wl - 80, T, { t0: 3.6, h: 480, r: 30, drift: -120 });
    wK.fire(c, L, 1000, wl - 70, 360, T, { a: L.seg(T, 4.3, 4.8), h: 220 }); wK.column(c, L, 1000, wl - 140, T, { t0: 4.4, h: 760, r: 56, n: 22, drift: -160, w: 160 });
    // AA tracers going up from the ships
    [2.7, 5.3].forEach(f => { for (let b = 0; b < 8; b++) { const tb = f + b * 0.09, ox = [1600, 1000, 400][b % 3] + 40, oy = wl - 150; wK.tracer(c, ox, oy, ox + 300 - b * 70, 80, L.lin(T, tb, tb + 0.6), 'rgba(240,150,60,0.95)', 0.12, 3); } });
    // torpedo run: dropped by the low plane, a wake in front of the row toward the outboard ship
    const tw0 = 1.95, tw1 = 3.3; if (T > tw0) { const u = Math.min(1, L.lin(T, tw0, tw1)), x = L.lerp(1720, 430, u); if (u < 1) { L.line(c, [[1720, wl + 40], [x, wl + 40]], 1, { color: L.BOX(0.85), width: 6 }); for (let i = 0; i < 12; i++) L.dot(c, x + i * 30 + L.rnd(i, 7) * 10, wl + 34 + L.rnd(i, 8) * 12, 4, L.BOX(0.9)); } }
    wK.splash(c, L, 1720, wl + 40, T, tw0, 0.4); wK.splash(c, L, 430, wl, T, tw1, 1.1); wK.blast(c, L, 430, wl - 30, T, tw1, 0.9, { dark: true });
    // bombs and hits
    wK.blast(c, L, 1600, wl - 70, T, 1.85, 1.0, { dark: true }); wK.blast(c, L, 1580, wl - 70, T, 6.25, 1.0, { dark: true });
    wK.blast(c, L, 990, wl - 70, T, 3.85, 0.8); wK.blast(c, L, 1000, wl - 100, T, 4.25, 2.1, { dark: true, life: 4.5 });
    // aircraft: three Val dive bombers and a Kate torpedo plane
    const vals = [[[0.3, 2100, -100], [1.0, 1800, 230], [1.5, 1660, 450], [2.0, 1400, 520], [2.8, 800, 260], [3.5, 200, -160]], 1.45, [1600, wl - 70], 1.85],
      v2 = [[[2.4, 2100, -100], [3.0, 1300, 280], [3.5, 1100, 470], [4.0, 820, 500], [4.8, 220, 160], [5.5, -300, -120]], 3.45, [990, wl - 70], 3.85],
      v3 = [[[4.8, 2100, -100], [5.4, 1750, 280], [5.85, 1620, 460], [6.3, 1360, 520], [7.1, 700, 220], [7.8, 0, -160]], 5.8, [1580, wl - 70], 6.25];
    [vals, v2, v3].forEach(([keys, tr, tgt, th]) => { const p = wK.path(T, keys); if (p) wK.plane(c, L, p.x, p.y, 260, { dir: p.dir, rot: p.rot, col: C.fg, mark: 'hino', gear: true, t: T });
      const r = wK.path(tr, keys); if (r) wK.bomb(c, L, r.x - 40, r.y + 20, tgt[0], tgt[1], T, tr, th, 1); });
    const kate = wK.path(T, [[1.4, 2200, 520], [2.2, 1400, 580], [3.0, 600, 560], [3.8, -300, 480]]); if (kate) wK.plane(c, L, kate.x, kate.y, 280, { dir: kate.dir, rot: kate.rot, col: C.fg, mark: 'hino', t: T });
    c.restore();
    K.flashAt(c, T, 4.25, 0.35, 0.8);
    L.tag(c, 'Pearl Harbor · 7 December 1941', 120, 140, T, 0.2, { size: 34, sub: 'Battleship Row (illustrative)' });
  },
};
