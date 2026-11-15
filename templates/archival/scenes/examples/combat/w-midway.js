// no-real-media: Midway photos (p-d-midway, p-d-hiryu, p-d-sbd) are used on the neighbouring shots; no free film of the dive on the Japanese carriers exists (searched Commons/NARA "Midway dive bombers Kaga Akagi") – drawn
// S577 "...on June 4, 1942, American dive bombers sank four Japanese fleet carriers in a single day.": three Dauntless dive bombers
// plunge almost vertically on a Japanese carrier, release and pull out; bombs burst on the flight deck among the parked planes,
// fires run along the deck, secondary explosions, anti-aircraft tracers chase the attackers.
window.SCENE = {
  duration: 7, bg: 'paper', vignette: 0.2,
  events: [[0.2, 'dive', 'first Dauntless dives'], [0.9, 'mg', 'anti-aircraft fire'], [1.1, 'dive', 'second Dauntless'], [1.6, 'blast', 'hit on the flight deck'], [2.0, 'dive', 'third Dauntless'],
    [2.5, 'blast', 'second hit'], [3.0, 'flyby', 'pull-out'], [3.4, 'blast', 'third hit'], [4.0, 'mg', 'anti-aircraft fire'], [4.6, 'blast', 'fuel and bombs on deck explode'],
    [5.8, 'burst', 'secondary explosion'], [6.6, 'thud', 'deck collapses']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, sea = 560, wl = 770, cx = 960, sc = 1.3;
    c.save(); wK.ev(S, 'blast').forEach(tt => K.shake(c, T, tt, 9, 4));
    wK.sea(c, L, sea, T, { lines: 8 });
    // escort on the horizon
    wK.above(c, sea + 3, () => wK.ship(c, L, 260, sea + 4, 260, T, { kind: 'bb', col: C.rule, mast: false }));
    // the carrier, wake at the stern
    for (let i = 0; i < 8; i++) { const ph = (T * 0.8 + i / 8) % 1; L.line(c, [[cx - 680 - ph * 300, wl + 10 + i % 2 * 10], [cx - 600 - ph * 300, wl + 10 + i % 2 * 10]], 1, { color: L.BOX(0.7 * (1 - ph)), width: 4 }); }
    wK.above(c, wl + 4, () => wK.ship(c, L, cx, wl, 1000 * sc, T, { kind: 'cv', col: C.fg, parked: T < 4.6 ? [-420, -340, -260, -180, 160, 240] : [-260, 160], list: 0.02 * L.seg(T, 4.6, 8) }));
    const deckY = wl - 112 * sc;
    // hits and fires along the deck
    const hits = [[1.6, cx - 120], [2.5, cx + 230], [3.4, cx - 420]];
    hits.forEach(([tt, x]) => { wK.blast(c, L, x, deckY, T, tt, 1.1, { dark: true }); wK.fire(c, L, x, deckY, 220, T, { a: L.seg(T, tt + 0.2, tt + 0.8), h: 130 }); wK.column(c, L, x, deckY - 40, T, { t0: tt + 0.3, h: 520, r: 34, drift: -150 }); });
    wK.blast(c, L, cx - 300, deckY, T, 4.6, 1.8, { dark: true }); wK.fire(c, L, cx - 280, deckY, 520, T, { a: L.seg(T, 4.8, 5.4), h: 220 });
    wK.blast(c, L, cx + 120, deckY + 20, T, 5.8, 1.3, { dark: true });
    // AA tracers from the ship toward the divers
    [0.9, 4.0].forEach(f => { for (let b = 0; b < 8; b++) { const tb = f + b * 0.09, ox = cx - 400 + b * 110, oy = deckY - 20; wK.tracer(c, ox, oy, 300 + b * 90, -40, L.lin(T, tb, tb + 0.7), 'rgba(240,150,60,0.95)', 0.1, 3); } });
    // three Dauntless dive bombers: near-vertical dive, release, pull out to the right
    [[0.2, cx - 120 - 60, 1.6], [1.1, cx + 230 - 60, 2.5], [2.0, cx - 420 - 60, 3.4]].forEach(([t0, tx, th]) => {
      const keys = [[t0, tx - 250, -160], [t0 + 0.7, tx - 90, 230], [t0 + 1.0, tx - 20, 400], [t0 + 1.4, tx + 200, 470], [t0 + 2.1, tx + 800, 260], [t0 + 2.8, tx + 1400, -160]];
      const p = wK.path(T, keys); if (p) wK.plane(c, L, p.x, p.y, 230, { dir: p.dir, rot: p.rot, col: C.accent, mark: 'us', t: T });
      const r = wK.path(t0 + 1.0, keys); wK.bomb(c, L, r.x + 10, r.y + 30, tx + 60, deckY, T, t0 + 1.0, th, 1.1); });
    c.restore();
    L.tag(c, 'Midway · 4 June 1942', 120, 140, T, 0.2, { size: 34, sub: 'Dive bombers on a Japanese carrier (illustrative)' });
  },
};
