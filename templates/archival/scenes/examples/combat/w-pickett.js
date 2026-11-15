// no-real-media: no photograph of Pickett's Charge exists (1863 cameras could not take action; only aftermath plates, searched Commons "Pickett's Charge", "Gettysburg July 3 1863") – drawn
// S147 "...and Pickett's Charge broke against that position on July 3, 1863.": the grey Confederate line climbs the slope with
// battle flags and fixed bayonets; behind the stone wall on Cemetery Ridge the blue Union line fires volley after volley, a battery
// fires canister; men fall, the charge stalls short of the wall.
window.SCENE = {
  duration: 9, bg: 'paper', vignette: 0.2,
  events: [[0.5, 'cannon', 'Union battery'], [0.85, 'burst', 'shell over the grey line'], [1.2, 'volley', 'Union volley from the wall'], [2.4, 'cannon', 'Union battery'], [2.5, 'gunshot', 'ragged Confederate fire'],
    [2.75, 'burst', 'canister'], [3.2, 'volley', 'Union volley'], [4.4, 'cannon', 'Union battery'], [4.75, 'burst', 'canister'], [5.2, 'volley', 'Union volley'], [6.1, 'gunshot', 'Confederate fire'],
    [6.4, 'cannon', 'Union battery'], [6.75, 'burst', 'canister'], [7.2, 'volley', 'Union volley'], [8.4, 'cannon', 'Union battery'], [8.75, 'burst', 'canister'], [9.2, 'volley', 'Union volley (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, ev = k => wK.ev(S, k), vol = ev('volley'), can = ev('cannon');
    const gY = x => 900 - Math.max(0, Math.min(1, x / 1500)) * 230;  // slope up to the ridge
    c.save(); can.forEach(tt => K.shake(c, T, tt, 4, 6));
    // ground
    c.fillStyle = C.bg2; c.beginPath(); c.moveTo(-50, 1100); for (let x = -50; x <= 1980; x += 40) c.lineTo(x, gY(x)); c.lineTo(1980, 1100); c.fill();
    L.line(c, Array.from({ length: 51 }, (_, i) => [-50 + i * 40, gY(-50 + i * 40)]), 1, { color: C.fg, width: 3 });
    // fence on the Emmitsburg Road, grass tufts
    for (let i = 0; i < 9; i++) { const x = 380 + i * 40; L.line(c, [[x, gY(x)], [x, gY(x) - 40]], 1, { color: C.fg2, width: 4 }); } L.line(c, [[380, gY(380) - 30], [700, gY(700) - 30]], 1, { color: C.fg2, width: 3 });
    // Union battery on the ridge (behind the infantry)
    [1745, 1855].forEach((gx, k) => { const fires = can.map(f => f + k * 0.15); wK.gun(c, L, gx, gY(1500) + 4, 150, T, { dir: -1, fire: fires }); });
    // Union infantry behind the wall: upper bodies show above the stones
    const ux = [1420, 1500, 1580, 1660];
    ux.forEach((x, i) => { const fires = vol.map(f => f + (i % 3) * 0.05); const [mx, my] = wK.shooter(c, L, x, gY(1500) + 4, 180, T + i, { dir: -1, fire: fires, doll: { side: 'union', hat: 'kepi', face: 'grim' } });
      fires.forEach(f => { if (T > f && T < f + 1.6) aSmoke(c, L, mx - 30, my, T, f, { r: 120, n: 5, size: 36, alpha: 0.6, a0: Math.PI - 0.4, a1: Math.PI + 0.4, life: 3, rise: 30 }); }); });
    wK.flag(c, L, 1730, gY(1500) - 40, 110, 'usa', T, { dir: -1, pole: 300 });
    // the stone wall
    for (let r = 0; r < 3; r++) for (let x = 1370 + (r % 2) * 22; x < 1700; x += 44) { const y = gY(1500) - 6 - r * 26; c.fillStyle = (r + Math.round(x / 44)) % 2 ? C.fg2 : C.rule; c.beginPath(); c.ellipse(x, y, 24, 14, 0, 0, 7); c.fill(); c.strokeStyle = L.FG(0.4); c.lineWidth = 2; c.stroke(); }
    // the Confederate line: two ranks climbing the slope, faster on "charge"; men fall to the volleys; stalls short of the wall
    const pos = (x0, T) => Math.min(1200, x0 + 70 * T + 70 * Math.max(0, T - 3.5));
    const men = []; for (let i = 0; i < 14; i++) { const rank = i % 2, x0 = -260 + Math.floor(i / 2) * 150 + rank * 70;
      let fallT = null; vol.forEach((v, k) => { if (fallT == null && L.rnd(i, k + 3) < 0.22 && i !== 6) fallT = v + 0.15; });
      const xs = fallT != null && T > fallT ? pos(x0, fallT) : pos(x0, T); men.push({ i, rank, x: xs, fallT }); }
    men.sort((a, b) => a.rank - b.rank).forEach(m => {
      const y = gY(m.x) + (m.rank ? 30 : 0), h = 180, but = L.rnd(m.i, 9) < 0.45, hat = L.rnd(m.i, 10) < 0.25 ? 'kepi' : 'slouch';
      const doll = { side: 'confed', hat, butternut: but, face: 'shout', hair: L.rnd(m.i, 11) < 0.2 ? 'grey' : 'dark' };
      if (m.fallT != null && T > m.fallT) { const u = L.easeOut(L.lin(T, m.fallT, m.fallT + 0.6)); K.doll(c, L, m.x - 30 * u, y + 20 * u, h, 0, Object.assign({}, doll, { face: 'dead', tilt: -1.35 * u })); return; }
      if (m.rank === 0 && m.i !== 6) { const fires = ev('gunshot').filter(tt => (m.i + Math.round(tt * 10)) % 3 === 0); wK.shooter(c, L, m.x, y, h, T * 3 + m.i, { fire: fires, doll }); }
      else K.doll(c, L, m.x, y, h, T * 3 + m.i, Object.assign({ musket: true }, doll));
      if (m.i === 6) wK.flag(c, L, m.x + 30, y - 120, 120, 'csa', T, { pole: 260 });
    });
    // canister and shell bursts over the grey line
    ev('burst').forEach((tt, k) => { const x = pos(-100 + k * 230, tt) + 60; wK.blast(c, L, x, gY(x) - 260 - (k % 2) * 60, T, tt, 0.55, { air: true }); });
    c.restore();
    L.tag(c, 'Gettysburg · 3 July 1863', 120, 140, T, 0.2, { size: 34, sub: "Pickett's Charge (illustrative)" });
  },
};
