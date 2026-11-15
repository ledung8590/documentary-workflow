// no-real-media: Desert Storm film/photos (v-e-dstorm, p-e-dstorm) are used on neighbouring shots; searched DVIDS/Commons "VII Corps M1A1 Desert Storm firing", "73 Easting" – no unused free film of the attack – drawn
// S694 "The famous 'left hook' by VII Corps and XVIII Airborne Corps swept around Iraqi defenses in late February 1991...": the camera
// rides with an echelon of M1A1 Abrams sweeping across flat desert, dust trailing; one after another they fire, and dug-in Iraqi
// tanks behind sand berms burst and burn as the column passes; Iraqi soldiers run.
window.SCENE = {
  duration: 8, bg: 'paper', vignette: 0.2,
  events: [[0.2, 'engine', 'Abrams column'], [1.0, 'cannon', 'Abrams fires'], [1.25, 'blast', 'Iraqi tank hit'], [2.2, 'cannon', 'Abrams fires'], [2.45, 'blast', 'Iraqi tank hit'],
    [3.4, 'cannon', 'Abrams fires'], [3.65, 'blast', 'Iraqi tank hit'], [4.6, 'cannon', 'Abrams fires'], [4.85, 'blast', 'Iraqi tank hit'], [5.8, 'cannon', 'Abrams fires'], [6.05, 'blast', 'Iraqi tank hit'],
    [7.0, 'cannon', 'Abrams fires'], [7.25, 'blast', 'Iraqi tank hit'], [8.2, 'cannon', 'Abrams fires (if extended)'], [8.45, 'blast', 'hit (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, hz = 520, ev = k => wK.ev(S, k), fires = ev('cannon');
    const scroll = 260 * T;  // the world slides left: the column advances right
    c.save(); ev('blast').forEach(tt => K.shake(c, T, tt, 5, 5));
    // desert: flat ground, faint ripple lines sliding past, haze on the horizon
    { const g = c.createLinearGradient(0, hz, 0, 1080); g.addColorStop(0, C.bg2); g.addColorStop(1, C.rule); c.fillStyle = g; c.fillRect(-100, hz, 2120, 700); } L.line(c, [[-100, hz], [2020, hz]], 1, { color: C.rule, width: 2 });
    for (let r = 0; r < 9; r++) { const y = hz + 20 + r * r * 7, sp = (0.3 + r * 0.18) * scroll; for (let k = -1; k < 9; k++) { const x = ((k * 260 - sp) % 2340 + 2340) % 2340 - 210; L.line(c, [[x, y], [x + 90 + r * 10, y]], 1, { color: L.FG(0.18 + r * 0.015), width: 2 }); } }
    // dug-in Iraqi T-72s behind berms, in the far line; each is hit when an Abrams fires at it
    const targets = fires.map((f, k) => ({ f, h: f + 0.25, wx: 1500 + f * 260 + (k % 2 ? 160 : -60), y: hz + 70 + (k % 3) * 34 }));
    targets.forEach((tg, k) => { const x = tg.wx - scroll * 0.6 + 0.6 * 260 * tg.f; if (x < -300 || x > 2300) return;
      const hit = T > tg.h, pop = hit ? L.easeOut(L.lin(T, tg.h, tg.h + 0.6)) : 0;
      wK.tank(c, L, x, tg.y, 250, T, { kind: 't72', dir: -1, col: C.fg2, roll: 0, elev: -0.25 * pop });
      c.fillStyle = C.bg2; c.beginPath(); c.moveTo(x - 150, tg.y + 2); c.quadraticCurveTo(x, tg.y - 44, x + 150, tg.y + 2); c.fill(); c.strokeStyle = L.FG(0.4); c.lineWidth = 2; c.stroke();  // sand berm
      wK.blast(c, L, x, tg.y - 20, T, tg.h, 0.8, { dark: true }); if (hit) { wK.fire(c, L, x, tg.y - 22, 110, T, { h: 90 }); wK.column(c, L, x, tg.y - 50, T, { t0: tg.h + 0.2, h: 420, r: 22, drift: -60 }); }
      // crew bailing out and running
      if (k % 2 === 0 && T > tg.h - 0.6) { for (let j = 0; j < 2; j++) { const run = T - tg.h + 0.6, px = x + 60 + j * 50 + run * 120, py = tg.y + 30 + j * 12; K.doll(c, L, px, py, 70, T * 6 + j, { side: 'iraq', hat: 'beret', face: 'shock', tilt: 0.15 }); } } });
    // the Abrams echelon: three tanks, dust, each fires in turn
    const M = [[260, 900, 520], [760, 800, 400], [1180, 720, 300]];
    M.forEach(([x0, y, w], k) => { const myF = fires.filter((_, j) => j % 3 === k), x = x0 + Math.sin(T * 0.7 + k) * 12;
      const [mx, my] = wK.tank(c, L, x, y, w, T, { kind: 'm1', dir: 1, col: C.fg, fire: myF, dust: true, mark: true, roll: scroll * 3, elev: 0.05 + 0.02 * k });
      myF.forEach(f => { const tg = targets.find(q => q.f === f); if (!tg) return; const tx = tg.wx - scroll * 0.6 + 0.6 * 260 * tg.f; wK.tracer(c, mx, my, tx, tg.y - 20, L.lin(T, f, tg.h), 'rgba(255,215,140,0.95)', 0.35, 4); }); });
    // haze of dust over everything low in the frame
    c.restore();
    L.tag(c, 'Desert Storm · February 1991', 120, 140, T, 0.2, { size: 34, sub: 'VII Corps "left hook" (illustrative)' });
  },
};
