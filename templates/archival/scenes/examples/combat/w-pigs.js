// no-real-media: searched Commons/NARA "Bay of Pigs landing", "Playa Giron 1961", "Brigade 2506 beach" – only captured-prisoner and aftermath photos (one used as p-a-pigs); no free film of the landing under fire – drawn
// S098 "Five days later, the Bay of Pigs invasion hit the beaches of Cuba, and within three days it had collapsed.": seen from the beach,
// landing craft of Brigade 2506 drop their ramps, the exiles wade ashore under mortar fire, go to ground and fire inland (right) while a
// Cuban Sea Fury strafes the sand and a supply ship burns on the horizon.
window.SCENE = {
  duration: 8, bg: 'paper', vignette: 0.2,
  events: [[0.9, 'burst', 'mortar splash by the landing craft'], [1.5, 'dive', 'Sea Fury dives on the beach'], [2.0, 'mg', 'strafing run'], [2.5, 'mg', 'strafing run'],
    [3.0, 'gunshot', 'exiles fire inland'], [3.4, 'burst', 'mortar on the sand'], [3.7, 'gunshot', 'exiles fire'], [4.3, 'burst', 'mortar splash'], [4.7, 'gunshot', 'exiles fire'],
    [5.0, 'dive', 'second strafing pass'], [5.5, 'mg', 'strafing'], [5.9, 'blast', 'supply ship hit offshore'], [6.1, 'mg', 'strafing'], [6.6, 'gunshot', 'exiles fire'],
    [7.1, 'burst', 'mortar on the sand'], [7.5, 'gunshot', 'exiles fire'], [8.4, 'burst', 'mortar (if extended)'], [9.2, 'dive', 'third pass (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, hy = 430, sy = 660, ev = k => wK.ev(S, k);
    c.save(); ev(['burst', 'blast']).forEach(tt => K.shake(c, T, tt, 6, 5));
    wK.sea(c, L, hy, T, { lines: 6 });
    // supply ship on the horizon (the Houston and Rio Escondido were sunk from the air)
    const tS = 5.9; wK.above(c, hy + 3, () => wK.ship(c, L, 300, hy + 4, 330, T, { kind: 'cargo', col: C.fg2, list: 0.05 * L.seg(T, tS, tS + 3), sink: 26 * L.seg(T, tS + 0.5, tS + 4) }));
    wK.blast(c, L, 300, hy - 24, T, tS, 0.6, { dark: true }); wK.fire(c, L, 300, hy - 20, 140, T, { a: L.seg(T, tS + 0.3, tS + 1), h: 80 }); wK.column(c, L, 300, hy - 50, T, { t0: tS + 0.4, h: 380, r: 20, drift: 140 });
    // beach in front, surf line moving
    c.fillStyle = C.bg2; c.beginPath(); c.moveTo(0, 1080); for (let x = 0; x <= 1920; x += 30) c.lineTo(x, sy + Math.sin(x * 0.01 + T * 1.5) * 8); c.lineTo(1920, 1080); c.fill();
    c.strokeStyle = L.BOX(0.9); c.lineWidth = 5; c.beginPath(); for (let x = 0; x <= 1920; x += 30) c.lineTo(x, sy - 6 + Math.sin(x * 0.01 + T * 1.5) * 8); c.stroke();
    c.fillStyle = C.green; [[1700, 640, 120], [1850, 650, 150], [1580, 660, 90]].forEach(([x, y, r]) => { c.beginPath(); c.arc(x, y, r, Math.PI, 0); c.fill(); });  // scrub at the right edge
    // mortar splashes in the shallows
    [[0.9, 980], [4.3, 520], [8.4, 1200]].forEach(([tt, x]) => wK.splash(c, L, x, sy - 40, T, tt, 0.7));
    // landing craft seen bow-on: run in, ramp drops
    const craft = (x0, t0) => { const u = L.easeOut(L.lin(T, t0, t0 + 1.5)), s = 0.55 + 0.45 * u, x = x0, y = L.lerp(hy + 30, sy - 10, u), r = L.seg(T, t0 + 1.5, t0 + 2.0);
      const w = 300 * s, h = 120 * s; c.fillStyle = C.fg; c.beginPath(); c.moveTo(x - w / 2, y); c.lineTo(x + w / 2, y); c.lineTo(x + w / 2 - 14 * s, y - h); c.lineTo(x - w / 2 + 14 * s, y - h); c.fill();
      if (r > 0) { c.fillStyle = C.fg2; c.fillRect(x - w / 2 + 22 * s, y - h + 14 * s, w - 44 * s, h - 14 * s); c.fillStyle = C.fg; c.beginPath(); c.moveTo(x - w / 2 + 16 * s, y); c.lineTo(x + w / 2 - 16 * s, y); c.lineTo(x + w / 2 - 6 * s, y + h * r * 0.7); c.lineTo(x - w / 2 + 6 * s, y + h * r * 0.7); c.fill(); }
      for (let i = 0; i < 5; i++) { const ph = (T * 1.2 + i / 5) % 1; c.strokeStyle = L.BOX(0.7 * (1 - ph)); c.lineWidth = 3; c.beginPath(); c.ellipse(x, y + 4, w * (0.5 + ph * 0.5), 8 + ph * 10, 0, 0, Math.PI); c.stroke(); }
      return [x, y]; };
    const crafts = [craft(760, 0), craft(1240, 0.5)];
    // the exiles: out of the ramp, wade ashore toward us, go to ground and fire inland (right)
    const men = []; for (let i = 0; i < 9; i++) { const k = i % 2, t0 = 2.0 + k * 0.5 + Math.floor(i / 2) * 0.32; if (T < t0) continue;
      const u = L.lin(T, t0, t0 + 2.0), [cx, cy] = crafts[k], dx = 200 + (i * 173) % 1200, dy = 780 + (i * 37) % 70;
      men.push({ i, x: L.lerp(cx + (i % 3 - 1) * 30, dx, L.easeOut(u)), y: L.lerp(cy + 10, dy, L.easeOut(u)), h: L.lerp(70, 160 + (dy - 780) * 0.5, L.easeOut(u)), u, t0 }); }
    men.sort((a, b) => a.y - b.y).forEach(m => {
      const doll = { side: 'us', hat: 'm1', coat: '#565a3a' };
      if (m.u < 1) K.doll(c, L, m.x, m.y, m.h, T * 5 + m.i, Object.assign({ face: 'shout', rifle: true, tilt: Math.sin(T * 9 + m.i) * 0.06 }, doll));
      else { const fires = ev('gunshot').filter(tt => tt > m.t0 + 2 && (m.i + Math.round(tt * 10)) % 2 === 0);
        const [mx, my] = wK.shooter(c, L, m.x, m.y, m.h, T + m.i, { gun: 'rifle', fire: fires, doll });
        fires.forEach(f => wK.tracer(c, mx, my, 1990, my - 40, L.lin(T, f, f + 0.3), 'rgba(240,150,60,0.9)', 0.2, 3)); }
    });
    // mortar rounds on the sand
    [[3.4, 1450, 760], [7.1, 620, 720]].forEach(([tt, x, y]) => wK.blast(c, L, x, y, T, tt, 0.8));
    // Sea Fury strafing passes from the right along the beach
    [[1.5, 3.3], [5.0, 6.8], [9.2, 11]].forEach(([a, b], k) => { if (T < a || T > b) return; const u = L.lin(T, a, b);
      const x = L.lerp(2200, -300, u), y = 150 + 170 * Math.sin(u * Math.PI) + k * 20, rot = 0.3 * Math.cos(u * Math.PI);
      wK.plane(c, L, x, y, 340, { dir: -1, rot, col: C.fg2, t: T });
      for (let j = 0; j < 14; j++) { const tj = a + 0.35 + j * 0.06; if (T < tj || T > tj + 0.7) continue; const gx = L.lerp(2200, -300, L.lin(tj, a, b)) - 420, gy = 700 + (j % 3) * 30, v = T - tj;
        if (v < 0.12) wK.tracer(c, L.lerp(2200, -300, L.lin(tj, a, b)) - 170, 150 + 170 * Math.sin(L.lin(tj, a, b) * Math.PI) + 30, gx, gy, v / 0.12, 'rgba(240,150,60,0.95)', 0.5, 3);
        else wK.puff(c, L, gx, gy - v * 70, 12 + v * 40, 1 - v / 0.7, false); }
    });
    c.restore();
    L.tag(c, 'Bay of Pigs · 17 April 1961', 120, 140, T, 0.2, { size: 34, sub: 'Brigade 2506 lands (illustrative)' });
  },
};
