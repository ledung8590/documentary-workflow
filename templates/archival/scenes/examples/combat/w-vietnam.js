// no-real-media: real Vietnam film is used on the neighbouring shots (v-b-vietnam, p-b-cav, p-b-101, p-b-25id, p-b-marines); a firefight at a landing zone with no repeat of those cuts – drawn
// S227 "Units like the 1st Cavalry Division (Airmobile), the 101st Airborne Division ... were all committed in Southeast Asia.": a Huey
// flares into a jungle landing zone, its door gunner firing; infantry jump out, run to cover and fire into the treeline; green enemy
// tracers come back, mortar rounds burst in the trees, a second Huey passes overhead.
window.SCENE = {
  duration: 8, bg: 'paper', vignette: 0.2,
  events: [[0.2, 'flyby', 'Huey comes in'], [2.4, 'mg', 'enemy fire from the treeline'], [3.0, 'mg', 'door gunner'], [3.5, 'gunshot', 'riflemen fire'], [4.1, 'gunshot', 'riflemen fire'],
    [4.6, 'burst', 'mortar in the treeline'], [5.0, 'flyby', 'second Huey overhead'], [5.3, 'gunshot', 'riflemen fire'], [5.8, 'mg', 'enemy fire'], [6.3, 'burst', 'mortar in the treeline'],
    [6.7, 'gunshot', 'riflemen fire'], [7.3, 'mg', 'door gunner'], [7.6, 'gunshot', 'riflemen fire'], [8.3, 'burst', 'mortar (if extended)'], [8.8, 'gunshot', 'riflemen fire (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, gy = 760, ev = k => wK.ev(S, k);
    c.save(); ev('burst').forEach(tt => K.shake(c, T, tt, 5, 5));
    // jungle: back canopy, palms
    c.fillStyle = C.green; c.globalAlpha = 0.45; c.beginPath(); c.moveTo(-50, gy); for (let i = 0; i <= 26; i++) { const x = -50 + i * 80, y = gy - 260 - 50 * L.rnd(i, 1); c.quadraticCurveTo(x - 40, y - 70, x + 40, y); } c.lineTo(2000, gy); c.closePath(); c.fill(); c.globalAlpha = 1;
    const palm = (x, h, s) => { c.strokeStyle = C.fg; c.lineWidth = 12 * s; c.beginPath(); c.moveTo(x, gy); c.quadraticCurveTo(x + 30 * s, gy - h / 2, x + 10 * s, gy - h); c.stroke();
      for (let k = 0; k < 6; k++) { const a = -Math.PI / 2 + (k - 2.5) * 0.55 + Math.sin(T * 2 + x) * 0.05; c.strokeStyle = C.green; c.lineWidth = 16 * s; c.beginPath(); c.moveTo(x + 10 * s, gy - h); c.quadraticCurveTo(x + 10 * s + Math.cos(a) * 120 * s, gy - h + Math.sin(a) * 120 * s - 30 * s, x + 10 * s + Math.cos(a) * 200 * s, gy - h + Math.sin(a) * 160 * s + 70 * s); c.stroke(); } };
    // treeline on the left where the enemy is
    for (let i = 0; i < 6; i++) palm(40 + i * 90, 360 + 60 * L.rnd(i, 3), 0.9);
    c.fillStyle = C.green; for (let i = 0; i < 9; i++) { c.beginPath(); c.arc(20 + i * 70, gy - 40, 70 + 20 * L.rnd(i, 4), Math.PI, 0); c.fill(); }
    palm(1700, 420, 1); palm(1860, 360, 0.9);
    wK.ground(c, L, gy);
    // grass flattened by the rotor wash
    const hx = 1250, hy = L.lerp(-150, 560, L.easeOut(L.lin(T, 0, 2.8))) + Math.sin(T * 2) * 6;
    const wash = L.seg(T, 1.2, 2.6);
    for (let i = 0; i < 40; i++) { const x = 620 + i * 32, d = (x - hx) / 500, bend = wash * Math.max(0, 1 - Math.abs(d)) * Math.sign(d) * 26 * (1 + 0.3 * Math.sin(T * 12 + i)); L.line(c, [[x, gy + 6], [x + bend, gy - 30 + Math.abs(bend) * 0.4]], 1, { color: C.green, width: 5 }); }
    // enemy muzzle flashes and green tracers from the treeline
    ev('mg').filter((_, j) => j % 2 === 0 || j === 2).forEach((f, j) => { for (let b = 0; b < 5; b++) { const tb = f + b * 0.09, ox = 260 + ((j * 3 + b) % 4) * 90, oy = gy - 60 - (b % 3) * 30; K.flash(c, L, ox, oy, T, tb, 0.35); wK.tracer(c, ox, oy, 1500 + b * 60, oy - 120 + b * 30, L.lin(T, tb, tb + 0.45), 'rgba(110,150,80,0.95)', 0.15, 4); } });
    // mortar rounds in the treeline
    [[4.6, 220], [6.3, 420], [8.3, 120]].forEach(([tt, x]) => { wK.blast(c, L, x, gy - 10, T, tt, 0.8, { dark: true }); });
    // the Huey: comes in, flares, hovers; door gunner fires left
    wK.huey(c, L, hx, hy, 520, T, { dir: -1, rot: -0.12 * L.seg(T, 1.6, 2.8) + 0.1 * (1 - L.seg(T, 0, 1.6)), star: true });
    [3.0, 7.3].forEach(f => { for (let b = 0; b < 7; b++) { const tb = f + b * 0.08; K.flash(c, L, hx + 10, hy + 0, T, tb, 0.3); wK.tracer(c, hx + 10, hy, 330 + b * 40, gy - 60 - b * 12, L.lin(T, tb, tb + 0.4), 'rgba(235,110,60,0.95)', 0.15, 4); } });
    // second Huey high and small across the top
    const h2 = L.lin(T, 4.6, 8.6); if (h2 > 0 && h2 < 1) wK.huey(c, L, L.lerp(2100, -200, h2), 200 + Math.sin(T) * 8, 260, T, { dir: -1, rot: 0.08, star: true, door: false });
    // infantry: jump out of the door, run left to cover, kneel and fire
    for (let i = 0; i < 5; i++) { const t0 = 2.8 + i * 0.32; if (T < t0) continue; const u = L.lin(T, t0, t0 + 1.4), dx = 640 + i * 165, y = gy + 70 + (i % 2) * 25;
      const x = L.lerp(hx - 40, dx, L.easeOut(u)), yy = L.lerp(hy + 70, y, Math.min(1, u * 3));
      const doll = { side: 'us', hat: 'm1', helmCol: '#5c5e3a' };
      if (u < 1) K.doll(c, L, x, yy, 150, T * 5 + i, Object.assign({ face: 'shout', rifle: true, tilt: -0.12 }, doll));
      else { const fires = ev('gunshot').filter(tt => tt > t0 + 1.4 && (i + Math.round(tt * 10)) % 2 === 0); const [mx, my] = wK.shooter(c, L, x, y, 150, T + i, { dir: -1, gun: 'rifle', fire: fires, doll });
        fires.forEach(f => wK.tracer(c, mx, my, 200, my - 80, L.lin(T, f, f + 0.35), 'rgba(235,110,60,0.9)', 0.2, 3)); } }
    c.restore();
    L.tag(c, 'South Vietnam · 1965–68', 120, 140, T, 0.2, { size: 34, sub: 'Airmobile assault (illustrative)' });
  },
};
