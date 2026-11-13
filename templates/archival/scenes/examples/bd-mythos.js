// S148-S150: the Blitzkrieg myth vs Frieser's finding. One board for three sentences: the claim is struck out, the real causes
// branch from "Improvisation", Guderian's exhibit joins the third cause; a staff officer doll carries the human side.
// no-real-media: no photo of the planning staff improvising; Guderian photo used where he is named
window.SCENE = {
  duration: 29.95, bg: 'paper', vignette: 0.2,
  images: { pz: '/projects/look-test/media/commons-5419235.jpg', gud: '/projects/look-test/media/commons-5477765.jpg' },
  draw(c, T, L) {
    const S150 = @{S150};
    K.board(c, L, T, [
      { k: 'title', s: 'Der Mythos „Blitzkrieg“', x: 120, y: 120, size: 50, at: 0.1 },
      { k: 'photo', key: 'pz', x: 120, y: 200, w: 520, h: 340, cap: 'Panzer IV in Frankreich, 1940', sub: 'Foto der Propagandakompanie', at: 0.3,
        move: [S150 - 0.6, S150 + 0.4, { w: 300, h: 196 }], dim: [S150, 0.55] },
      { k: 'box', s: 'Ein lange durchdachter Plan', sub: 'so erzählte es die Propaganda', x: 760, y: 210, w: 520, h: 120, at: @{S148 "Mythos"} },
      { k: 'box', s: 'Karl-Heinz Frieser', sub: '„Blitzkrieg-Legende“ (1995)', x: 1400, y: 210, w: 400, h: 120, at: @{S149 "Frieser"} },
      { k: 'link', from: [1400, 270], to: [1290, 270], arrow: true, at: @{S149 "gezeigt"} },
      { k: 'strike', x0: 790, x1: 1250, y: 262, at: @{S149 "keineswegs"} },
      { k: 'link', from: [1020, 335], to: [1020, 412], arrow: true, at: @{S150 "riskante"}-0.2 },
      { k: 'box', s: 'Riskante Improvisation', x: 760, y: 415, w: 520, h: 96, at: @{S150 "riskante"} },
      { k: 'link', from: [1020, 515], to: [725, 600], at: @{S150 "Kette"} },
      { k: 'box', s: 'Fehler der Gegner', x: 560, y: 600, w: 330, h: 84, size: 28, at: @{S150 "Kette"} },
      { k: 'link', from: [1020, 515], to: [1020, 600], at: @{S150 "Glück"} },
      { k: 'box', s: 'Glück', x: 920, y: 600, w: 200, h: 84, size: 28, at: @{S150 "Glück"} },
      { k: 'link', from: [1020, 515], to: [1315, 600], at: @{S150 "Eigenmächtigkeit"} },
      { k: 'box', s: 'Eigenmächtigkeit', x: 1150, y: 600, w: 330, h: 84, size: 28, at: @{S150 "Eigenmächtigkeit"} },
      { k: 'photo', key: 'gud', x: 1540, y: 560, w: 260, h: 180, cap: 'Heinz Guderian', sub: 'Mai 1940', at: @{S150 "Heinz Guderian"}-0.4, fx: 0.4 },
      { k: 'link', from: [1480, 642], to: [1530, 642], at: @{S150 "Heinz Guderian"} },
      { k: 'doll', x: 300, y: 830, h: 210, o: { side: 'wehr', hat: 'peaked', face: 'grim', binos: true }, at: @{S150 "Panzerkommandeure"}-0.6 },
      { k: 'conclude', s: 'Ein Sieg aus Glück und Improvisation – kein Plan', x: 560, y: 830, size: 38, at: @{S150$}-1.2 },
    ]);
  },
};
