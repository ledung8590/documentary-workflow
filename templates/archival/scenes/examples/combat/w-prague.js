// no-real-media: the Prague 1968 photos on Commons are mostly copyrighted press work (Koudelka, ČTK); the one free still (p-b-prague) is used elsewhere; searched "Prague 1968 tanks", "Operation Danube" – drawn
// S237 "In Operation Danube, they invaded Czechoslovakia with a force ... with thousands of tanks.": a column of Soviet T-55s with red
// stars rolls into a Prague street under the towers of the Old Town; a crowd shouts at them, one man waves the Czechoslovak flag; a
// tank fires a machine-gun burst over their heads and the crowd flinches.
window.SCENE = {
  duration: 7, bg: 'paper', vignette: 0.2,
  events: [[0.2, 'engine', 'tank column rumbles in'], [2.9, 'mg', 'burst over the crowd'], [3.3, 'mg', 'second burst'], [5.6, 'mg', 'burst from the second tank'], [8.2, 'mg', 'burst (if extended)']],
  draw(c, T, L) {
    const S = window.SCENE, C = L.C, gy = 760, mg = wK.ev(S, 'mg');
    // Old Town skyline: Týn church spires, house fronts
    c.fillStyle = C.rule; [[300, 120], [420, 120]].forEach(([x]) => { c.fillRect(x - 40, gy - 520, 80, 520); c.beginPath(); c.moveTo(x - 50, gy - 520); c.lineTo(x, gy - 700); c.lineTo(x + 50, gy - 520); c.fill(); for (let k = -1; k <= 1; k += 2) { c.beginPath(); c.moveTo(x + k * 40 - 12, gy - 520); c.lineTo(x + k * 40, gy - 590); c.lineTo(x + k * 40 + 12, gy - 520); c.fill(); } });
    c.fillRect(250, gy - 460, 220, 460);
    wK.houses(c, L, 520, 1960, gy, { col: C.rule, h: [300, 380], w: [180, 240], seed: 3 });
    wK.houses(c, L, -60, 240, gy, { col: C.rule, h: [280, 340], seed: 9 });
    wK.ground(c, L, gy);
    // tram rails
    [800, 830].forEach(y => L.line(c, [[0, y], [1920, y]], 1, { color: L.FG(0.25), width: 3 }));
    // tank column rolling left, commander in the hatch
    [[0, 560], [1, 620], [2, 680]].forEach(([k, w]) => {
      const x = 2250 + k * 760 - 230 * T - (k ? 0 : 60 * Math.max(0, T - 4)), y = gy + 20 + k * 0;
      if (x < -500 || x > 2600) return;
      const turX = x - (w / 200) * 4 * 1, turY = y - (w / 200) * 62;
      K.doll(c, L, turX + 10, turY + 6, 80, T + k, { side: 'sov', hat: 'pilotka', face: 'grim' });
      wK.tank(c, L, x, y, w, T, { kind: 't55', dir: -1, star: true, dust: true, elev: 0.02 * Math.sin(T + k) });
      if (k === 0 || k === 1) mg.filter((_, j) => j % 2 === k || k === 0 && j < 2).forEach(f => { for (let b = 0; b < 6; b++) { const tb = f + b * 0.07, v = L.lin(T, tb, tb + 0.5); wK.tracer(c, turX - 30, turY - 50, turX - 700, turY - 600, v, 'rgba(240,150,60,0.95)', 0.12, 3); } K.flash(c, L, turX - 30, turY - 50, T, f, 0.4); K.flash(c, L, turX - 30, turY - 50, T, f + 0.2, 0.4); });
    });
    // the crowd in front: shouting, a fist, the flag; flinches on the bursts
    const fl = t0 => mg.reduce((a, f) => a + (T > f && T < f + 0.8 ? Math.sin((T - f) / 0.8 * Math.PI) : 0), 0);
    const crowd = [[150, 'work', 'flatcap'], [300, 'suit', 'none'], [450, 'work', 'none'], [600, 'suit', 'fedora'], [760, 'work', 'flatcap'], [910, 'suit', 'none'], [1060, 'work', 'none']];
    crowd.forEach(([x, side, hat], i) => { const back = fl() * 30, y = 848 - (i % 2) * 18, shout = Math.sin(T * 4 + i * 1.7) > -0.2;
      K.doll(c, L, x - back * 0.3 + Math.sin(T * 2 + i) * 6, y, 200 - (i % 2) * 14, T * 2 + i, { side, hat, face: back > 5 ? 'shock' : shout ? 'shout' : 'grim', hair: i === 1 ? 'grey' : 'dark', tie: C.accent });
      if (i === 4) wK.flag(c, L, x + 70, y - 120, 150, 'cz', T, { pole: 300 }); });
    L.tag(c, 'Prague · 21 August 1968', 120, 140, T, 0.2, { size: 34, sub: 'Warsaw Pact tanks enter the city (illustrative)' });
  },
};
