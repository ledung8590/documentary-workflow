// no-real-media: the 1921 test photos (p-d-ost, p-d-ostfr) are used on the neighbouring shots; searched Commons/NARA "Ostfriesland bombing film 1921" – no free film cut found – drawn
// S485 "On July 21, 1921, General Billy Mitchell's Army Air Service bombers sank the captured German battleship Ostfriesland off the
// Virginia capes.": a formation of Martin MB-2 biplanes crosses over the anchored battleship; near misses throw up water columns,
// a hit bursts on the deck, she lists, settles by the stern and goes down while the bombers come round again.
window.SCENE = {
  duration: 8, bg: 'paper', vignette: 0.2,
  events: [[0.4, 'flyby', 'MB-2 formation'], [2.4, 'blast', 'near miss, water column'], [3.2, 'blast', 'near miss'], [4.0, 'blast', 'hit on the deck'], [5.0, 'flyby', 'bombers come round'],
    [5.6, 'thud', 'hull plates give way'], [6.6, 'blast', 'last near miss'], [7.4, 'thud', 'she goes under']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, sea = 600, wl = 720;
    c.save(); wK.ev(S, 'blast').forEach(tt => K.shake(c, T, tt, 7, 4));
    wK.sea(c, L, sea, T, { lines: 7 });
    // observers' ship on the horizon
    wK.above(c, sea + 3, () => wK.ship(c, L, 220, sea + 4, 220, T, { kind: 'cargo', col: C.rule }));
    // the battleship: lists and settles by the stern after the hit
    const sk = L.seg(T, 4.3, 9.5), list = -0.1 * sk - 0.04 * L.seg(T, 6.5, 9.5), sink = 230 * L.ease(L.lin(T, 4.6, 9.5));
    wK.above(c, wl + 4, () => wK.ship(c, L, 980, wl, 1000, T, { kind: 'bb', col: C.fg2, list, sink }));
    for (let i = 0; i < 10; i++) { const ph = (T * 0.7 + i / 10) % 1; if (T > 4.6) L.dot(c, 560 + L.rnd(i, 3) * 400, wl - ph * 30, 5 * (1 - ph), L.BOX(0.8)); }  // air bubbles at the stern
    wK.fire(c, L, 1060, wl - 120 + sink * 0.4, 160, T, { a: L.seg(T, 4.1, 4.6) * (1 - L.seg(T, 5.8, 6.6)), h: 90 }); wK.column(c, L, 1060, wl - 150 + sink * 0.4, T, { t0: 4.2, h: 460, r: 28, drift: 160 });
    // bombers: three MB-2s crossing left to right, then coming back high from the right
    const pX = (k, t) => -200 + (t - k * 0.35) * 380, pY = (k, t) => 270 + k * 60 + Math.sin(t * 1.2 + k) * 8;
    for (let k = 0; k < 3; k++) { const x = pX(k, T); if (x > -500 && x < 2400) wK.biplane(c, L, x, pY(k, T), 360 - k * 30, T); }
    for (let k = 0; k < 2; k++) { const u = L.lin(T, 4.6 + k * 0.3, 9.0 + k * 0.3); if (u > 0 && u < 1) wK.biplane(c, L, L.lerp(2300, -400, u), 280 + k * 50, 260, T, { dir: -1 }); }
    // bombs: released from the formation, fall forward to splash or hit
    [[0, 1.6, 2.4, wl], [1, 2.4, 3.2, wl], [2, 3.2, 4.0, wl - 110]].forEach(([k, tr, th, ty]) => { const x0 = pX(k, tr), y0 = pY(k, tr) + 30, x1 = x0 + 280;
      wK.bomb(c, L, x0, y0, x1, ty, T, tr, th, 1.3); if (ty === wl) wK.splash(c, L, x1, wl, T, th, 1.1); else { wK.blast(c, L, x1, ty, T, th, 1.2, { dark: true }); } });
    { const tr = 5.8, th = 6.6, u = L.lin(tr, 4.6, 9.0), x0 = L.lerp(2300, -400, u), x1 = x0 - 240; wK.bomb(c, L, x0, 300, x1, wl, T, tr, th, 1.1); wK.splash(c, L, x1, wl, T, th, 1.0); }
    c.restore();
    L.tag(c, 'Off the Virginia Capes · 21 July 1921', 120, 140, T, 0.2, { size: 34, sub: 'Ostfriesland bombing test (illustrative)' });
  },
};
