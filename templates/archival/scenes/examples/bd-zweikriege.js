// S146: the army that held four years on the Western Front collapsed in six weeks. Board: two exhibits side by side, time bars, takeaway.
// no-real-media: (board with real photos, no drawn characters)
window.SCENE = {
  duration: 7.55, bg: 'paper', vignette: 0.2,
  images: { wk1: '/projects/look-test/media/commons-39576555.jpg', paris: '/projects/look-test/media/commons-5365658.jpg' },
  draw(c, T, L) {
    K.board(c, L, T, [
      { k: 'title', s: 'Frankreichs Armee: 1914–1918 und 1940', x: 120, y: 120, size: 44, at: 0 },
      { k: 'photo', key: 'wk1', x: 120, y: 190, w: 640, h: 400, cap: 'Westfront 1914–1918', sub: 'Foto, Erster Weltkrieg', at: @{S146 "Ersten Weltkrieg"}-0.6 },
      { k: 'bar', x: 120, y: 760, w: 640, h: 24, frac: 1, label: 'hielt stand', value: '4 Jahre', at: @{S146 "vier Jahre"} },
      { k: 'photo', key: 'paris', x: 1160, y: 190, w: 640, h: 400, cap: 'Paris, 14. Juni 1940', sub: 'Deutsche Siegesparade, Avenue Foch', at: @{S146 "unterlag"}-0.3 },
      { k: 'bar', x: 1160, y: 760, w: 640, h: 24, frac: 0.05, label: 'brach zusammen', value: '6 Wochen', color: L.C.accent2, at: @{S146 "sechs Wochen"} },
      { k: 'link', from: [790, 390], to: [1130, 390], arrow: true, dash: true, at: @{S146 "unterlag"}-0.5 },
      { k: 'conclude', s: 'Dieselbe Armee – ein anderer Krieg', x: 860, y: 860, size: 38, at: @{S146 "sechs Wochen"}+0.7 },
    ]);
  },
};
