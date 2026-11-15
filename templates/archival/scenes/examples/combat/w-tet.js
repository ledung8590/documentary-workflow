// no-real-media: one free Tet photo (p-e-tet) is used on the neighbouring shot; searched Commons/NARA "Tet Offensive Hue night", "Saigon 1968 street fighting" – no free night combat film – drawn
// S616 "The Tet Offensive of January 1968 had shattered public trust in official optimism about the war.": night street fighting in
// a city: flares drift down on parachutes and light the roofs, green and red tracers cross the street, rockets burst on a building,
// a house burns, US Marines fire from behind sandbags.
window.SCENE = {
  duration: 7, bg: 'paper', vignette: 0.25,
  events: [[0.4, 'mg', 'enemy fire from the windows'], [0.9, 'gunshot', 'Marines fire'], [1.6, 'mg', 'enemy fire'], [2.0, 'blast', 'rocket hits the building'], [2.6, 'gunshot', 'Marines fire'],
    [3.2, 'mg', 'Marine machine gun'], [3.8, 'gunshot', 'Marines fire'], [4.5, 'burst', 'mortar in the street'], [5.0, 'mg', 'enemy fire'], [5.6, 'gunshot', 'Marines fire'],
    [6.3, 'burst', 'mortar on a roof'], [6.8, 'gunshot', 'Marines fire'], [7.5, 'mg', 'enemy fire (if extended)'], [8.2, 'blast', 'rocket (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, gy = 780, ev = k => wK.ev(S, k);
    // night: the look's navy sky, ink buildings
    const g = c.createLinearGradient(0, 0, 0, gy); g.addColorStop(0, C.fg); g.addColorStop(1, C.accent); c.fillStyle = g; c.fillRect(0, 0, 1920, 1080);
    c.save(); ev(['burst', 'blast']).forEach(tt => K.shake(c, T, tt, 6, 5));
    // flares: drift down swinging, light pools
    const flares = [[0.0, 700, 6], [2.2, 1300, 6], [4.4, 420, 6]];
    let light = 0; flares.forEach(([t0, x0, life]) => { const u = L.lin(T, t0, t0 + life); if (T < t0 || u >= 1) return; const fx = x0 + Math.sin(T * 1.3 + x0) * 30 + u * 120, fy = 90 + u * 420, a = Math.min(1, (T - t0) * 3) * (1 - u * 0.6);
      light = Math.max(light, a); const gr = c.createRadialGradient(fx, fy, 0, fx, fy, 700); gr.addColorStop(0, `rgba(255,236,190,${0.35 * a})`); gr.addColorStop(1, 'rgba(255,236,190,0)'); c.fillStyle = gr; c.fillRect(fx - 700, fy - 700, 1400, 1400);
      L.line(c, [[fx, fy], [fx - 30, fy - 60], [fx + 30, fy - 60], [fx, fy]], 1, { color: L.BOX(0.6), width: 2 }); c.fillStyle = L.BOX(0.7); c.beginPath(); c.arc(fx, fy - 70, 32, Math.PI, 0); c.fill();
      L.dot(c, fx, fy, 9, `rgba(255,245,220,${a})`); wK.puff(c, L, fx - 10, fy - 120 - u * 40, 30, 0.3 * a, false); });
    // buildings (shophouses) in ink, lit windows
    const B = [[-40, 260, 430], [220, 220, 360], [440, 300, 470], [1180, 260, 400], [1440, 240, 330], [1680, 300, 450]];
    B.forEach(([x, w, h], i) => { c.fillStyle = C.fg; c.fillRect(x, gy - h, w - 8, h); c.fillRect(x - 10, gy - h - 16, w + 12, 16);
      for (let r = 0; r < Math.floor(h / 90); r++) for (let q = 0; q < Math.floor(w / 70); q++) { const on = L.rnd(i * 10 + r, q) < 0.35; c.fillStyle = on ? `rgba(184,134,43,${0.6 + 0.3 * Math.sin(T * 3 + r + q)})` : L.BOX(0.08 + 0.12 * light); c.fillRect(x + 22 + q * 70, gy - h + 30 + r * 90, 30, 44); } });
    // the hit building burns
    const tR = 2.0; wK.blast(c, L, 560, gy - 360, T, tR, 1.0, { air: true, dark: true }); wK.fire(c, L, 590, gy - 420, 200, T, { a: L.seg(T, tR + 0.3, tR + 1), h: 140 }); wK.column(c, L, 590, gy - 470, T, { t0: tR + 0.5, h: 420, r: 30, dark: true });
    wK.fire(c, L, 1560, gy - 330, 160, T, { h: 100 }); wK.column(c, L, 1560, gy - 380, T, { h: 380, r: 26 });
    // street
    c.fillStyle = C.fg2; c.fillRect(-100, gy, 2120, 400); L.line(c, [[-100, gy], [2020, gy]], 1, { color: L.BOX(0.3), width: 2 });
    // tracers: enemy (green) from the left windows, Marines (red) from the right
    ev('mg').forEach((f, j) => { const enemy = j !== 2; for (let b = 0; b < 6; b++) { const tb = f + b * 0.08;
      if (enemy) { const ox = 300 + (b % 3) * 80, oy = gy - 220 - (b % 2) * 90; K.flash(c, L, ox, oy, T, tb, 0.3); wK.tracer(c, ox, oy, 1500, gy - 60 + b * 10, L.lin(T, tb, tb + 0.45), 'rgba(120,170,90,0.95)', 0.14, 4); }
      else { K.flash(c, L, 1300, gy - 80, T, tb, 0.35); wK.tracer(c, 1300, gy - 80, 300 + b * 30, gy - 260 - b * 20, L.lin(T, tb, tb + 0.4), 'rgba(235,110,60,0.95)', 0.14, 4); } } });
    [[4.5, 900, gy + 20], [6.3, 1480, gy - 330], [8.2, 300, gy - 300]].forEach(([tt, x, y]) => wK.blast(c, L, x, y, T, tt, 0.8, { dark: true }));
    // sandbags and the Marines behind them
    for (let r = 0; r < 3; r++) for (let k = 0; k < 9; k++) { c.fillStyle = r % 2 ? C.rule : C.bg2; c.beginPath(); c.ellipse(1250 + k * 70 + (r % 2) * 35, gy + 60 - r * 34, 40, 20, 0, 0, 7); c.fill(); c.strokeStyle = L.FG(0.5); c.lineWidth = 2; c.stroke(); }
    [1320, 1500, 1680].forEach((x, i) => { const fires = ev('gunshot').filter(tt => (i + Math.round(tt * 10)) % 2 === 0); const [mx, my] = wK.shooter(c, L, x, gy + 10, 170, T + i, { dir: -1, gun: 'rifle', fire: fires, doll: { side: 'us', hat: 'm1', helmCol: '#4e5034' } });
      fires.forEach(f => wK.tracer(c, mx, my, 250, my - 140, L.lin(T, f, f + 0.35), 'rgba(235,110,60,0.95)', 0.2, 3)); });
    for (let r = 0; r < 2; r++) for (let k = 0; k < 9; k++) { c.fillStyle = r % 2 ? C.rule : C.bg2; c.beginPath(); c.ellipse(1250 + k * 70 + (r % 2) * 35, gy + 120 - r * 34, 40, 20, 0, 0, 7); c.fill(); c.strokeStyle = L.FG(0.5); c.lineWidth = 2; c.stroke(); }
    c.restore();
    L.tag(c, 'Tet Offensive · 1968', 120, 140, T, 0.2, { size: 34, sub: 'Night street fighting (illustrative)' });
  },
};
