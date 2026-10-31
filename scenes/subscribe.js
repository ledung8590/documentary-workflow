// Subscribe call-to-action overlay, reused by every film (docs/SCENES.md "Subscribe overlay").
// Rendered transparent:  node scripts/jsscene.mjs scenes/subscribe.js projects/<id>/media/subscribe.mov --alpha
// Put it on the fx track as a media_overlay (blend normal) starting ~1.3 s before the narrator says "subscribe".
// Beats (scene s): 0.0 pop in · 1.3 click Subscribe -> Subscribed + burst · 2.45 click bell -> rings · 3.7 out.
// Clicks for SFX: CLICKS below (mouseclick at each, subscribed at the first, notifybell at the second).
window.SCENE = {
  duration: 4.2, bg: 'none', vignette: 0,
  draw(c, t, L) {
    const CLICK1 = 1.3, CLICK2 = 2.45, OUT = 3.75;
    const cx = 960, cy = 742;                                   // above the subtitle band (y 0.868)
    const pin = L.easeOut(L.lin(t, 0, 0.35)), pout = L.ease(L.lin(t, OUT, 4.15));
    const pop = pin < 1 ? 0.6 + 0.4 * pin + 0.12 * Math.sin(pin * Math.PI) : 1;
    const A = Math.min(pin * 1.4, 1) * (1 - pout);
    if (A <= 0.001) return;
    const subd = t >= CLICK1;
    // button press squish
    const press = (t0) => { const d = t - t0; return d >= -0.08 && d < 0.18 ? 1 - 0.08 * Math.sin(L.clamp((d + 0.08) / 0.26) * Math.PI) : 1; };
    const sc = pop * (1 - 0.15 * pout) * press(CLICK1);

    // ---- card: avatar disc + channel line + button + bell
    const bw = subd ? 410 : 360, bh = 92, gap = 26, bell = 92;
    const total = bw + gap + bell;
    const bx = cx - total / 2, by = cy - bh / 2;
    c.save(); c.globalAlpha = A;
    c.translate(cx, cy); c.scale(sc, sc); c.translate(-cx, -cy);

    // soft shadow plate
    c.save(); c.shadowColor = 'rgba(0,0,0,0.55)'; c.shadowBlur = 40; c.shadowOffsetY = 8;
    const rr = (x, y, w, h, r) => { c.beginPath(); c.roundRect(x, y, w, h, r); };
    // button
    const mix = L.lin(t, CLICK1, CLICK1 + 0.18);
    const col = subd ? `rgb(${Math.round(L.lerp(204, 58, mix))},${Math.round(L.lerp(0, 58, mix))},${Math.round(L.lerp(0, 58, mix))})` : '#CC0000';
    rr(bx, by, bw, bh, bh / 2); c.fillStyle = col; c.fill(); c.restore();
    // sheen sweep before the click
    if (!subd) {
      const sx = bx + ((t * 0.9) % 1.4) / 1.4 * (bw + 200) - 100;
      c.save(); rr(bx, by, bw, bh, bh / 2); c.clip();
      const g = c.createLinearGradient(sx - 60, 0, sx + 60, 0);
      g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(255,255,255,0.28)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      c.fillStyle = g; c.fillRect(bx, by, bw, bh); c.restore();
    }
    // icon: play triangle in a rounded box, or a check mark once subscribed
    const ix = bx + 62, iy = cy;
    if (!subd) {
      rr(ix - 30, iy - 21, 60, 42, 11); c.fillStyle = '#fff'; c.fill();
      c.beginPath(); c.moveTo(ix - 8, iy - 11); c.lineTo(ix + 12, iy); c.lineTo(ix - 8, iy + 11); c.closePath(); c.fillStyle = '#CC0000'; c.fill();
    } else {
      const k = L.easeOut(L.lin(t, CLICK1 + 0.05, CLICK1 + 0.35));
      c.save(); c.strokeStyle = '#fff'; c.lineWidth = 9; c.lineCap = 'round'; c.lineJoin = 'round';
      const pts = [[ix - 20, iy + 1], [ix - 5, iy + 16], [ix + 22, iy - 15]];
      const len1 = Math.hypot(15, 15), len2 = Math.hypot(27, 31), d = k * (len1 + len2);
      c.beginPath(); c.moveTo(...pts[0]);
      if (d <= len1) c.lineTo(pts[0][0] + 15 * d / len1, pts[0][1] + 15 * d / len1);
      else { c.lineTo(...pts[1]); const e = (d - len1) / len2; c.lineTo(pts[1][0] + 27 * e, pts[1][1] - 31 * e); }
      c.stroke(); c.restore();
    }
    c.fillStyle = '#fff'; c.font = '700 50px Oswald'; c.textAlign = 'left'; c.textBaseline = 'middle';
    c.fillText(subd ? 'SUBSCRIBED' : 'SUBSCRIBE', bx + 108, cy + 2);

    // bell
    const bxc = bx + bw + gap + bell / 2, rung = t >= CLICK2;
    c.save(); c.shadowColor = 'rgba(0,0,0,0.55)'; c.shadowBlur = 30; c.shadowOffsetY = 6;
    c.beginPath(); c.arc(bxc, cy, bell / 2, 0, Math.PI * 2); c.fillStyle = rung ? '#3a3a3a' : '#272727'; c.fill(); c.restore();
    const dw = t - CLICK2, wig = rung && dw < 0.9 ? Math.sin(dw * 38) * 0.42 * (1 - dw / 0.9) : 0;
    c.save(); c.translate(bxc, cy - 20); c.rotate(wig); c.translate(-bxc, -(cy - 20));
    c.beginPath();
    c.moveTo(bxc - 19, cy + 12); c.quadraticCurveTo(bxc - 19, cy - 20, bxc, cy - 22); c.quadraticCurveTo(bxc + 19, cy - 20, bxc + 19, cy + 12);
    c.lineTo(bxc + 24, cy + 17); c.lineTo(bxc - 24, cy + 17); c.closePath();
    if (rung) { c.fillStyle = '#fff'; c.fill(); } else { c.strokeStyle = '#fff'; c.lineWidth = 5; c.lineJoin = 'round'; c.stroke(); }
    c.beginPath(); c.arc(bxc, cy + 24, 6, 0, Math.PI * 2); c.fillStyle = '#fff'; c.fill();
    c.restore();
    if (rung && dw < 0.9) {  // ring waves beside the bell
      c.save(); c.strokeStyle = `rgba(255,255,255,${0.9 * (1 - dw / 0.9)})`; c.lineWidth = 4; c.lineCap = 'round';
      for (const s of [-1, 1]) for (const r of [34, 46]) { c.beginPath(); c.arc(bxc, cy - 4, r, s > 0 ? -0.5 : Math.PI - 0.5, s > 0 ? 0.5 : Math.PI + 0.5); c.stroke(); }
      c.restore();
    }
    c.restore();

    // ---- click bursts (outside the scaled group so they stay crisp)
    const burst = (x, y, t0, color, n) => {
      const d = t - t0; if (d < 0 || d > 0.7) return;
      L.rings(c, x, y, t, { t0, every: 99, life: 0.6, rmax: 150, color, alpha: 0.85, width: 5, count: 1 });
      c.save();
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2 + L.rnd(i, 7) * 0.4, sp = 160 + L.rnd(i, 3) * 160, r = L.easeOut(d / 0.7) * sp;
        const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r * 0.75, s = (1 - d / 0.7) * (5 + L.rnd(i, 5) * 6);
        c.globalAlpha = A * (1 - d / 0.7); c.fillStyle = i % 3 ? color : '#fff';
        c.beginPath(); c.moveTo(px, py - s); c.lineTo(px + s * 0.35, py); c.lineTo(px, py + s); c.lineTo(px - s * 0.35, py); c.closePath(); c.fill();
      }
      c.restore();
    };
    burst(bx + bw / 2, cy, CLICK1, '#ff3b3b', 22);
    burst(bxc, cy, CLICK2, '#ffd34d', 14);

    // ---- cursor: glides in, clicks Subscribe, then the bell, then drifts away
    const P0 = [1500, 1010], P1 = [bx + bw * 0.62, cy + 14], P2 = [bxc + 6, cy + 12], P3 = [1580, 1000];
    let p;
    if (t < 0.55) p = P0;
    else if (t < CLICK1 - 0.08) { const k = L.seg(t, 0.55, CLICK1 - 0.08); p = [L.lerp(P0[0], P1[0], k), L.lerp(P0[1], P1[1], k) - Math.sin(k * Math.PI) * 60]; }
    else if (t < CLICK1 + 0.45) p = P1;
    else if (t < CLICK2 - 0.08) { const k = L.seg(t, CLICK1 + 0.45, CLICK2 - 0.08); p = [L.lerp(P1[0], P2[0], k), L.lerp(P1[1], P2[1], k) - Math.sin(k * Math.PI) * 30]; }
    else if (t < CLICK2 + 0.5) p = P2;
    else { const k = L.seg(t, CLICK2 + 0.5, OUT + 0.2); p = [L.lerp(P2[0], P3[0], k), L.lerp(P2[1], P3[1], k)]; }
    const ca = L.lin(t, 0.45, 0.65) * (1 - L.lin(t, OUT - 0.1, OUT + 0.2)) * A;
    const down = [CLICK1, CLICK2].some(k => t >= k - 0.06 && t < k + 0.1);
    if (ca > 0.01) {
      c.save(); c.globalAlpha = ca; c.translate(p[0], p[1]); const s = down ? 1.6 : 1.8; c.scale(s, s);
      c.shadowColor = 'rgba(0,0,0,0.5)'; c.shadowBlur = 8; c.shadowOffsetY = 3;
      c.beginPath(); c.moveTo(0, 0); c.lineTo(0, 30); c.lineTo(7.5, 23); c.lineTo(13, 35); c.lineTo(18, 33); c.lineTo(12.5, 21.5); c.lineTo(22, 21.5); c.closePath();
      c.fillStyle = '#fff'; c.fill(); c.shadowColor = 'transparent'; c.strokeStyle = '#111'; c.lineWidth = 1.8; c.lineJoin = 'round'; c.stroke();
      c.restore();
    }
  },
};
window.SCENE.CLICKS = [1.3, 2.45];
