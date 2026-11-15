// no-real-media: no photograph of a Civil War battle in progress exists (only aftermath and portraits; Lee's portrait p-d-lee is used nearby); searched Commons "Second Manassas battle", "Seven Days battle" – drawn
// S526-S527 "...the Confederacy won a string of brilliant battlefield victories in 1861 and 1862 ... Robert E. Lee kept winning battles.":
// a Confederate battery on the left fires shell after shell into the Union line; the grey infantry advances firing volleys, the blue
// line wavers, breaks and runs, its flag going down; Lee, grey-bearded, points the advance on with his sword.
window.SCENE = {
  duration: 8, bg: 'paper', vignette: 0.2,
  events: [[0.4, 'cannon', 'Confederate battery'], [0.8, 'gunshot', 'Union fire'], [0.9, 'burst', 'shell in the Union line'], [1.3, 'volley', 'Confederate volley'], [1.9, 'cannon', 'battery'],
    [2.2, 'gunshot', 'Union fire'], [2.4, 'burst', 'shell'], [3.0, 'volley', 'Confederate volley'], [3.4, 'cannon', 'battery'], [3.6, 'gunshot', 'ragged Union fire'], [3.9, 'burst', 'shell'],
    [4.9, 'cannon', 'battery'], [5.0, 'volley', 'Confederate volley'], [5.4, 'burst', 'shell among the fleeing'], [6.4, 'cannon', 'battery'], [6.9, 'burst', 'shell'], [7.0, 'volley', 'Confederate volley'], [7.9, 'cannon', 'battery (if extended)'], [8.4, 'burst', 'shell (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, gy = 780, ev = k => wK.ev(S, k), vol = ev('volley'), brk = 4.3;
    c.save(); ev('cannon').forEach(tt => K.shake(c, T, tt, 3, 6));
    // rolling Virginia fields, a farmhouse and a worm fence
    c.fillStyle = C.bg2; c.beginPath(); c.moveTo(0, gy - 120); c.quadraticCurveTo(500, gy - 200, 1000, gy - 140); c.quadraticCurveTo(1500, gy - 90, 1920, gy - 170); c.lineTo(1920, gy); c.lineTo(0, gy); c.fill();
    c.fillStyle = C.rule; c.fillRect(1500, gy - 230, 140, 90); c.beginPath(); c.moveTo(1490, gy - 230); c.lineTo(1570, gy - 290); c.lineTo(1650, gy - 230); c.fill();
    for (let i = 0; i < 12; i++) { const x = 900 + i * 50; L.line(c, [[x, gy - 140], [x + 50, gy - 160 + (i % 2) * 20]], 1, { color: C.rule, width: 4 }); }
    wK.ground(c, L, gy);
    // shells bursting in the Union line (on the right)
    ev('burst').forEach((tt, k) => { const x = 1300 + ((k * 211) % 500) + (tt > brk ? 120 : 0); wK.blast(c, L, x, gy + 10 - (k % 2) * 30, T, tt, 0.8); });
    // the Union line: fires back, wavers, breaks and runs right; some fall
    for (let i = 0; i < 7; i++) { const x0 = 1220 + i * 100, rank = i % 2, y = gy + 40 + rank * 30;
      let fallT = null; ev('burst').forEach((b, k) => { if (fallT == null && L.rnd(i, k + 20) < 0.18) fallT = b + 0.1; });
      const run = Math.max(0, T - brk - L.rnd(i, 5) * 0.4), x = x0 + run * 320 + Math.min(run, 0.3) * 0;
      const doll = { side: 'union', hat: 'kepi' };
      if (fallT != null && T > fallT) { const u = L.easeOut(L.lin(T, fallT, fallT + 0.6)), xf = x0 + Math.max(0, fallT - brk) * 320; K.doll(c, L, xf + 30 * u, y + 20 * u, 170, 0, Object.assign({}, doll, { face: 'dead', tilt: 1.35 * u })); continue; }
      if (run > 0) K.doll(c, L, x, y, 170, T * 6 + i, Object.assign({ face: 'shock', musket: true, tilt: 0.16 }, doll));
      else { const fires = ev('gunshot').filter(tt => (i + Math.round(tt * 10)) % 2 === 0); wK.shooter(c, L, x, y, 170, T + i, { dir: -1, fire: fires, doll: Object.assign({ face: T > brk - 1 ? 'shock' : 'grim' }, doll) }); } }
    { const run = Math.max(0, T - brk - 0.2), fx = 1560 + run * 300; wK.flag(c, L, fx, gy + 10, 110, 'usa', T, { dir: -1, pole: 260 - 160 * L.seg(T, brk + 0.2, brk + 1.4) }); }
    // the Confederate battery on the left
    ev('cannon').forEach(() => {}); [[180, 0], [400, 0.15]].forEach(([gx, d]) => wK.gun(c, L, gx, gy + 30, 170, T, { fire: ev('cannon').map(f => f + d) }));
    // Lee with his staff sword, on the left behind the guns
    K.doll(c, L, 90, gy - 10, 210, T, { side: 'confed', hat: 'slouch', capCol: '#5a5248', face: 'grim', hair: 'white', beard: true, sabre: true, raise: T > 1 });
    // the grey infantry advancing to the right, firing volleys, cheering after the break
    for (let i = 0; i < 8; i++) { const rank = i % 2, x = 520 + Math.floor(i / 2) * 120 + rank * 50 + 55 * T + 80 * Math.max(0, T - brk), y = gy + 60 + rank * 40;
      const doll = { side: 'confed', hat: L.rnd(i, 3) < 0.6 ? 'slouch' : 'kepi', butternut: L.rnd(i, 4) < 0.4, face: T > brk ? 'shout' : 'grim' };
      if (rank === 0) { const fires = vol.map(f => f + (i % 4) * 0.04); wK.shooter(c, L, x, y, 180, T * 3 + i, { fire: fires, doll }); }
      else K.doll(c, L, x, y, 180, T * 3 + i, Object.assign({ musket: true }, doll));
      if (i === 3) wK.flag(c, L, x + 40, y - 120, 120, 'csa', T, { pole: 270 }); }
    c.restore();
    L.tag(c, 'Virginia · 1862', 120, 140, T, 0.2, { size: 34, sub: "Lee's army on the attack (illustrative)" });
  },
};
