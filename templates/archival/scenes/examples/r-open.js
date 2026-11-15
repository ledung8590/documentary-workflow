// S001 opening, 通史3 style (their 0-6 s): the reconstruction print of the N1 at Baikonur on the night of 3 July 1969 fades in
// from black with a slow push, the date label top-left, and the film title box laid over the print at 1 s while the voice runs.
// Searchlight beams sweep and the haze drifts so nothing is static. Label: Reconstruction (generated).
// no-real-media: no photograph of 5L on the pad that night is free to use
window.SCENE = { duration: 6, bg: 'paper', vignette: 0, images: { p: '/projects/<job>/media/recon_g/023.jpg' }, draw(c, T, L) {
  const D = window.SCENE.duration, { seg, lin } = L;
  K.photo(c, L, 'p', 0, 0, 1920, 1080, { zoom: 1.0 + 0.09 * lin(T, 0, D + 4), grade: false, fx: 0.62, fy: 0.42 + 0.04 * lin(T, 0, D + 4) });
  // drifting haze bands and two slow searchlight sweeps (warm-neutral, low alpha) so the print breathes
  for (let i = 0; i < 3; i++) { const x = ((T * (18 + i * 9) + i * 700) % 2600) - 400; const g = c.createLinearGradient(x, 0, x + 600, 0);
    g.addColorStop(0, 'rgba(230,214,180,0)'); g.addColorStop(0.5, `rgba(230,214,180,${0.07 + 0.03 * i})`); g.addColorStop(1, 'rgba(230,214,180,0)'); c.fillStyle = g; c.fillRect(x, 520 + i * 70, 600, 160); }
  [[700, 0.35], [1320, -0.28]].forEach(([bx, sp], k) => { const a = -1.15 + Math.sin(T * sp + k) * 0.32; c.save(); c.translate(bx, 760); c.rotate(a);
    const g = c.createLinearGradient(0, 0, 0, -1300); g.addColorStop(0, 'rgba(240,226,190,0.20)'); g.addColorStop(1, 'rgba(240,226,190,0)');
    c.fillStyle = g; c.beginPath(); c.moveTo(-14, 0); c.lineTo(-170, -1300); c.lineTo(170, -1300); c.lineTo(14, 0); c.fill(); c.restore(); });
  // date label (their 「1891年7月 横浜」)
  const a1 = seg(T, 0.4, 0.9); c.globalAlpha = a1; c.fillStyle = 'rgba(28,26,24,0.84)'; c.fillRect(48, 52, 400, 96); c.fillStyle = '#E8DFC9'; c.fillRect(48, 52, 4, 96);
  L.text(c, '3 July 1969 · 23:18', 72, 102, { size: 38, color: '#F1EADB' }); L.text(c, 'Baikonur, Soviet Kazakhstan', 72, 134, { size: 22, font: 'body', color: '#D9CFBA' }); c.globalAlpha = 1;
  // title box laid over the picture (their 「通史3 / 艦は買えた… / ─ 初めての連合艦隊まで ─」)
  const a2 = seg(T, 1.0, 1.6), rise = (1 - a2) * 12; c.globalAlpha = a2;
  c.fillStyle = 'rgba(28,26,24,0.86)'; c.fillRect(440, 230 + rise, 1110, 186);
  L.text(c, 'The space race, part of the Cold War', 474, 272 + rise, { size: 24, font: 'body', color: '#D9CFBA' });
  L.text(c, 'What If the USSR Reached the Moon First?', 474, 336 + rise, { size: 52, color: '#F4EEE0' });
  L.text(c, '— Would Washington redirect its military technology? —', 474, 386 + rise, { size: 26, font: 'body', color: '#D9CFBA' });
  c.globalAlpha = 1;
  // fade in from black (their first half second)
  const f = 1 - seg(T, 0, 0.6); if (f > 0) { c.fillStyle = `rgba(0,0,0,${f})`; c.fillRect(0, 0, 1920, 1080); }
} };
