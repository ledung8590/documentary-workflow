// S151-S153: the gamble becomes doctrine, a dangerous confusion: the recipe is to be repeated against the Soviet Union.
// no-real-media: no picture shows "doctrine"; the officer doll stands for the planners who believed in the recipe
window.SCENE = {
  duration: 14.65, bg: 'paper', vignette: 0.2,
  draw(c, T, L) {
    K.board(c, L, T, [
      { k: 'title', s: 'Aus dem Glücksspiel wird eine Doktrin', x: 120, y: 120, size: 46, at: 0.1 },
      { k: 'box', s: 'Glücksspiel', sub: 'Frankreich, Mai 1940', x: 120, y: 300, w: 420, h: 130, at: 0.4 },
      { k: 'link', from: [545, 365], to: [735, 365], arrow: true, at: @{S151 "Doktrin"}-0.5 },
      { k: 'box', s: 'Doktrin', sub: 'ein Rezept für jeden Feldzug', x: 740, y: 300, w: 440, h: 130, at: @{S151 "Doktrin"} },
      { k: 'ring', x: 640, y: 365, rx: 120, ry: 60, at: @{S152 "Verwechslung"} },
      { k: 'conclude', s: 'Glück verwechselt mit Können', x: 160, y: 560, size: 40, at: @{S152 "Verwechslung"}+0.3 },
      { k: 'doll', x: 960, y: 820, h: 200, o: { side: 'wehr', hat: 'peaked', face: 'smile' }, at: @{S153 "glaubte"} },
      { k: 'link', from: [1185, 365], to: [1375, 365], arrow: true, dash: true, at: @{S153 "wiederholen"}-0.6 },
      { k: 'box', s: 'Sowjetunion 1941?', sub: 'derselbe Plan, ein anderes Land', x: 1380, y: 300, w: 420, h: 130, at: @{S153 "wiederholen"} },
    ]);
  },
};
