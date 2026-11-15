// no-real-media: the U-boat photo (p-e-uboat) and Liberty ship film (v-e-liberty) are used on neighbouring shots; no free film of a torpedo hit on a merchant ship without repeats (searched Commons/NARA "torpedoed tanker 1942", "U-boat attack convoy") – drawn
// S676 "German U-boats sank ships faster than any navy in history up to that point...": cutaway at the waterline: a U-boat at
// periscope depth fires a torpedo, the bubble track runs under the surface into a Liberty cargo ship, a water column and fire,
// she breaks her back and settles; further off another ship in the convoy is hit.
window.SCENE = {
  duration: 7, bg: 'paper', vignette: 0.2,
  events: [[0.6, 'whoosh', 'torpedo fired'], [2.6, 'blast', 'torpedo hits the cargo ship'], [3.3, 'thud', 'secondary explosion in the hold'], [5.2, 'blast', 'second ship hit further off'], [6.2, 'thud', 'hull breaks'], [8.0, 'blast', 'third ship hit (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, wl = 520, tH = 2.6;
    c.save(); wK.ev(S, 'blast').forEach(tt => K.shake(c, T, tt, tt === tH ? 14 : 4, 4));
    // underwater: the look's navy, darker with depth; light shafts
    const g = c.createLinearGradient(0, wl, 0, 1080); g.addColorStop(0, C.accent); g.addColorStop(1, C.fg); c.fillStyle = g; c.fillRect(-100, wl, 2120, 700);
    for (let i = 0; i < 6; i++) { const x = 200 + i * 320 + Math.sin(T * 0.6 + i) * 30; c.fillStyle = L.BOX(0.05); c.beginPath(); c.moveTo(x, wl); c.lineTo(x + 80, wl); c.lineTo(x + 200, 1080); c.lineTo(x + 40, 1080); c.fill(); }
    // surface line and ripples
    c.strokeStyle = L.BOX(0.7); c.lineWidth = 3; c.beginPath(); for (let x = -20; x <= 1940; x += 30) c.lineTo(x, wl + Math.sin(x * 0.015 + T * 1.6) * 4); c.stroke();
    // convoy ship further off (hit at 5.2)
    const t2 = 5.2; wK.above(c, wl + 2, () => wK.ship(c, L, 260, wl + 2, 300, T, { kind: 'cargo', col: C.fg2, list: 0.06 * L.seg(T, t2, t2 + 3), sink: 40 * L.seg(T, t2 + 0.6, 9) }));
    wK.blast(c, L, 270, wl - 30, T, t2, 0.6, { dark: true }); wK.fire(c, L, 270, wl - 26, 120, T, { a: L.seg(T, t2 + 0.3, t2 + 1), h: 70 }); wK.column(c, L, 270, wl - 40, T, { t0: t2 + 0.4, h: 400, r: 20, drift: -100 });
    { const t3 = 8.0; wK.blast(c, L, 1700, wl - 20, T, t3, 0.5, { dark: true }); }
    // the Liberty ship: steams right, hit amidships, breaks her back and settles
    const sx = 760 + 18 * T, brk = L.seg(T, tH + 0.6, 9), sink = 200 * L.ease(L.lin(T, tH + 0.8, 10));
    wK.above(c, wl + 3, () => { c.save(); c.beginPath(); c.rect(-400, -400, sx + 400, 2000); c.clip(); wK.ship(c, L, sx, wl, 760, T, { kind: 'cargo', col: C.fg, list: -0.12 * brk, sink }); c.restore();
      c.save(); c.beginPath(); c.rect(sx, -400, 2400, 2000); c.clip(); wK.ship(c, L, sx, wl, 760, T, { kind: 'cargo', col: C.fg, list: 0.1 * brk, sink: sink * 0.8 }); c.restore(); });
    c.save(); c.globalAlpha = 0.28; wK.below(c, wl + 3, () => wK.ship(c, L, sx, wl, 760, T, { kind: 'cargo', col: C.fg, sink })); c.restore();  // hull under water, faint
    for (let i = 0; i < 6; i++) { const ph = (T * 0.5 + i / 6) % 1; if (T < tH) L.line(c, [[sx - 400 - ph * 300, wl + 4], [sx - 340 - ph * 300, wl + 4]], 1, { color: L.BOX(0.7 * (1 - ph)), width: 4 }); }
    // the U-boat at periscope depth, facing left; periscope wake
    const ux = 1560 + Math.sin(T * 0.5) * 6, uy = 740; wK.ship(c, L, ux, uy, 560, T, { kind: 'sub', col: C.fg, dir: -1 });
    L.line(c, [[ux + 2, uy - 106], [ux + 2, wl - 30]], 1, { color: C.fg, width: 5 }); L.line(c, [[ux - 10, wl - 30], [ux + 10, wl - 30]], 1, { color: C.fg, width: 8 });
    for (let i = 0; i < 4; i++) { const ph = (T * 0.8 + i / 4) % 1; L.line(c, [[ux + 10 + ph * 120, wl + 2], [ux + 40 + ph * 120, wl + 2]], 1, { color: L.BOX(0.8 * (1 - ph)), width: 3 }); }
    // the torpedo: out of the bow tube, running at depth to the hull, bubble track behind
    const t0 = 0.6, bx = ux - 290, by = uy - 4, hx = sx + 30, hy = wl + 70;
    if (T > t0) { const u = Math.min(1, L.lin(T, t0, tH)), x = L.lerp(bx, hx, u), y = L.lerp(by, hy, u);
      for (let i = 0; i < 30; i++) { const ui = u - i * 0.012; if (ui < 0) break; const bxi = L.lerp(bx, hx, ui), byi = L.lerp(by, hy, ui), a = (1 - i / 30) * (T < tH + 1.5 ? 1 : 0); L.dot(c, bxi + L.rnd(i, 3) * 10, byi - 8 + L.rnd(i, 4) * 16 - (T - t0) * 3 * (i / 30), 3 + i * 0.15, L.BOX(0.55 * a)); }
      if (u < 1) { c.save(); c.translate(x, y); c.rotate(Math.atan2(hy - by, hx - bx)); c.fillStyle = C.panel; c.beginPath(); c.ellipse(0, 0, 46, 8, 0, 0, 7); c.fill(); c.fillRect(-56, -10, 8, 20); c.restore(); }
      K.flash(c, L, bx, by, T, t0, 0.6); }
    // the hit: underwater flash, water column, fire and smoke
    K.flash(c, L, hx, hy, T, tH, 2.4); wK.splash(c, L, hx, wl, T, tH, 1.4); wK.blast(c, L, hx, wl - 50, T, tH + 0.05, 1.1, { dark: true }); wK.blast(c, L, hx - 120, wl - 100, T, 3.3, 0.7, { dark: true, air: true });
    wK.fire(c, L, hx, wl - 70 + sink * 0.6, 260, T, { a: L.seg(T, tH + 0.4, tH + 1.2), h: 150 }); wK.column(c, L, hx, wl - 120 + sink * 0.5, T, { t0: tH + 0.5, h: 500, r: 40, drift: -140, n: 20 });
    c.restore();
    L.tag(c, 'Battle of the Atlantic · 1942', 120, 140, T, 0.2, { size: 34, sub: 'U-boat attack on a convoy (illustrative)' });
  },
};
