// Shared drawing kit for this film's scenes (prepended to every scene by scenes/src/build.py). Template: templates/archival/scenes/src/_kit.js.
// Smoke, flashes, muskets, cannon, riders (black-powder era: add the film's own era helpers here) plus K.doll: egg-shaped period
// characters, the LAST resort for people/units with no real or stand-in picture (docs/WORKFLOW.md stage 6, scripts/dollcheck.py).
const K = {
  N: 10,  // nominal length the scene times were written for; draw() rescales t to the real duration
  T(T0) { return T0 * K.N / window.SCENE.duration; },
  smoke(c, L, x, y, t, t0, o = {}) {  // billowing powder smoke cloud
    const age = t - t0; if (age < 0) return;
    const n = o.n || 14, R = (o.r || 120) * (0.4 + 0.6 * L.easeOut(age / (o.grow || 1.6))), life = o.life || 6;
    const a = (o.alpha ?? 0.8) * Math.max(0, 1 - age / life);
    for (let i = 0; i < n; i++) {
      const ang = L.rnd(i, 7) * 6.28, d = L.rnd(i, 8) * R, rr = R * (0.35 + 0.4 * L.rnd(i, 9));
      const px = x + Math.cos(ang) * d + age * (o.drift || 18), py = y + Math.sin(ang) * d * 0.6 - age * 10;
      const g = c.createRadialGradient(px, py, 0, px, py, rr);
      g.addColorStop(0, `rgba(${o.col || '225,220,210'},${a * 0.55})`); g.addColorStop(1, `rgba(${o.col || '225,220,210'},0)`);
      c.fillStyle = g; c.fillRect(px - rr, py - rr, 2 * rr, 2 * rr);
    }
  },
  flash(c, L, x, y, t, t0, s = 1) {  // muzzle flash
    const age = t - t0; if (age < 0 || age > 0.25) return;
    const a = 1 - age / 0.25, r = 70 * s * (0.6 + age * 3);
    const g = c.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, `rgba(255,240,190,${a})`); g.addColorStop(0.4, `rgba(255,150,50,${a * 0.8})`); g.addColorStop(1, 'rgba(255,80,20,0)');
    c.fillStyle = g; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill();
  },
  musket(c, x, y, len, o = {}) {  // side-view matchlock, muzzle to the right
    c.save(); c.translate(x, y); c.rotate(o.rot || 0); const s = len / 600;
    c.fillStyle = o.wood || '#6b4a2e'; c.strokeStyle = o.line || 'rgba(0,0,0,0.5)'; c.lineWidth = 2;
    c.beginPath(); c.moveTo(-300 * s, -10 * s); c.lineTo(-120 * s, -14 * s); c.lineTo(40 * s, -12 * s); c.lineTo(40 * s, 8 * s);
    c.lineTo(-110 * s, 10 * s); c.lineTo(-300 * s, 40 * s); c.closePath(); c.fill(); c.stroke();
    c.fillStyle = o.metal || '#8d8a82'; c.fillRect(-40 * s, -20 * s, 340 * s, 11 * s);  // barrel
    c.fillStyle = '#b08a3a'; c.fillRect(-150 * s, -26 * s, 30 * s, 10 * s);  // pan
    c.strokeStyle = '#4a3a2a'; c.lineWidth = 5 * s; c.beginPath(); c.moveTo(-160 * s, 6 * s); c.quadraticCurveTo(-200 * s, -40 * s, -140 * s, -34 * s); c.stroke();  // serpentine
    c.restore();
  },
  cannon(c, x, y, len, o = {}) {  // bronze barrel, muzzle to the right (dir -1 to the left)
    c.save(); c.translate(x, y); c.scale(o.dir || 1, 1); c.rotate(o.rot || 0); const s = len / 400;
    const g = c.createLinearGradient(0, -40 * s, 0, 40 * s);
    g.addColorStop(0, o.light || '#d6a85a'); g.addColorStop(0.5, o.col || '#a0742e'); g.addColorStop(1, '#4e3612');
    c.fillStyle = g; c.beginPath(); c.moveTo(-200 * s, -40 * s); c.lineTo(200 * s, -24 * s); c.lineTo(200 * s, 24 * s); c.lineTo(-200 * s, 40 * s);
    c.arc(-200 * s, 0, 40 * s, Math.PI / 2, Math.PI * 1.5); c.fill();
    c.fillStyle = 'rgba(0,0,0,0.35)'; [-120, -20, 120, 190].forEach(u => c.fillRect(u * s, -36 * s, 10 * s, 72 * s));
    c.restore();
  },
  boat(c, L, x, y, len, t, o = {}) {  // mông đồng galley, side view, bow to the right
    c.save(); c.translate(x, y); c.scale(o.dir || 1, 1); const s = len / 800;
    c.fillStyle = o.hull || '#3a2a1c'; c.strokeStyle = o.line || 'rgba(237,231,220,0.35)'; c.lineWidth = 2;
    c.beginPath(); c.moveTo(-400 * s, -50 * s); c.lineTo(380 * s, -50 * s); c.lineTo(420 * s, -80 * s); c.lineTo(400 * s, -20 * s);
    c.quadraticCurveTo(360 * s, 30 * s, 300 * s, 30 * s); c.lineTo(-340 * s, 30 * s); c.quadraticCurveTo(-400 * s, 20 * s, -420 * s, -70 * s); c.closePath(); c.fill(); c.stroke();
    c.fillStyle = o.armor || '#5a4030'; c.fillRect(-340 * s, -90 * s, 680 * s, 40 * s);  // hide/plank bulwark
    c.strokeStyle = 'rgba(0,0,0,0.4)'; for (let u = -320; u < 340; u += 40) { c.beginPath(); c.moveTo(u * s, -90 * s); c.lineTo(u * s, -50 * s); c.stroke(); }
    if (o.oars !== false) {  // oars sweep in rhythm
      const ph = Math.sin((t || 0) * (o.stroke || 3));
      c.strokeStyle = o.oarCol || '#c9b48a'; c.lineWidth = 4 * s + 1;
      for (let u = -300; u <= 280; u += 45) { c.beginPath(); c.moveTo(u * s, -20 * s); c.lineTo((u - 40 + ph * 30) * s, 90 * s); c.stroke(); }
    }
    if (o.gun !== false) K.cannon(c, 400 * s, -70 * s, 140 * s, { rot: 0 });
    c.restore();
  },
  elephant(c, x, y, h, o = {}) {  // war elephant silhouette facing right (dir -1 left), h = shoulder height px
    c.save(); c.translate(x, y); c.scale((o.dir || 1) * h / 300, h / 300);
    const step = Math.sin((o.t || 0) * (o.gait || 6)) * 12;
    c.fillStyle = o.col || '#2a2420';
    c.beginPath(); c.ellipse(0, -190, 190, 120, 0, 0, 7); c.fill();  // body
    c.beginPath(); c.ellipse(235, -235, 80, 78, 0.2, 0, 7); c.fill();  // head
    c.beginPath(); c.moveTo(285, -220); c.quadraticCurveTo(340 + step, -80, 300 + step, 20); c.lineTo(276 + step, 16); c.quadraticCurveTo(300, -90, 250, -180); c.fill();  // trunk
    c.fillStyle = o.tusk || '#e8e0cc'; c.beginPath(); c.moveTo(275, -185); c.quadraticCurveTo(350, -160, 365, -205); c.lineTo(356, -200); c.quadraticCurveTo(330, -170, 278, -172); c.fill();
    c.fillStyle = o.col || '#2a2420';
    [[-130, step], [-60, -step], [60, step], [130, -step]].forEach(([lx, d]) => c.fillRect(lx - 28 + d * 0.5, -120, 56, 120));
    c.beginPath(); c.ellipse(180, -235, 55, 78, -0.2, 0, 7); c.fillStyle = o.ear || '#3d342d'; c.fill();  // ear
    if (o.howdah !== false) {
      c.fillStyle = '#6b3a22'; c.fillRect(-110, -340, 170, 50); c.fillStyle = '#c8372d'; c.fillRect(-120, -296, 190, 14);
      c.fillStyle = '#2a2420'; [[-80, -380], [-20, -386], [30, -378]].forEach(([px, py]) => { c.beginPath(); c.arc(px, py, 16, 0, 7); c.fill(); c.fillRect(px - 10, py, 20, 40); });
    }
    c.restore();
  },
  mosquito(c, L, x, y, s, t, o = {}) {  // side-view mosquito, facing left
    c.save(); c.translate(x, y); c.scale(s / 100, s / 100); c.globalAlpha *= o.alpha ?? 1;
    const col = o.col || '#1a1512'; c.fillStyle = col; c.strokeStyle = col; c.lineWidth = 3;
    c.beginPath(); c.ellipse(40, 0, 50, 10, 0.25, 0, 7); c.fill();  // abdomen
    c.beginPath(); c.ellipse(-10, -8, 22, 16, 0, 0, 7); c.fill();  // thorax
    c.beginPath(); c.arc(-36, -6, 9, 0, 7); c.fill();
    c.beginPath(); c.moveTo(-44, -4); c.lineTo(-100, 14); c.stroke();  // proboscis
    for (let i = 0; i < 3; i++) { c.beginPath(); c.moveTo(-10 + i * 10, 4); c.quadraticCurveTo(-30 + i * 25, 40, -50 + i * 40, 70); c.stroke(); }
    const fl = Math.sin(t * 90) * 0.5;
    c.fillStyle = o.wing || 'rgba(200,200,190,0.35)';
    c.save(); c.rotate(-0.6 + fl); c.beginPath(); c.ellipse(20, -40, 45, 12, 0.2, 0, 7); c.fill(); c.restore();
    c.restore();
  },
  soldier(c, x, y, h, o = {}) {  // standing musketeer silhouette facing right
    c.save(); c.translate(x, y); c.scale((o.dir || 1) * h / 200, h / 200); c.fillStyle = o.col || '#1d1a17';
    c.beginPath(); c.arc(0, -180, 16, 0, 7); c.fill();
    c.beginPath(); c.moveTo(-34, -186); c.lineTo(34, -186); c.lineTo(0, -214); c.closePath(); c.fill();  // conical hat
    c.fillRect(-16, -164, 32, 84); c.fillRect(-16, -80, 13, 80); c.fillRect(3, -80, 13, 80);
    if (o.aim) { c.fillRect(0, -150, 60, 10); c.fillRect(30, -156, 110, 7); } else { c.fillRect(10, -230, 6, 150); }
    c.restore();
  },
  stake(c, x, y, h, col) { c.fillStyle = col || '#4a3624'; c.beginPath(); c.moveTo(x - 9, y); c.lineTo(x + 9, y); c.lineTo(x + 2, y - h); c.lineTo(x - 2, y - h); c.fill(); },
  water(c, L, top, t, o = {}) {  // river cross-section with a moving surface
    const pts = []; for (let x = 0; x <= 1920; x += 20) pts.push([x, top + Math.sin(x / 90 + t * 1.6) * (o.amp || 6)]);
    c.save(); c.beginPath(); c.moveTo(0, 1080); pts.forEach(p => c.lineTo(p[0], p[1])); c.lineTo(1920, 1080); c.closePath();
    const g = c.createLinearGradient(0, top, 0, 1080); g.addColorStop(0, o.c0 || 'rgba(70,90,80,0.85)'); g.addColorStop(1, o.c1 || 'rgba(20,28,26,0.95)');
    c.fillStyle = g; c.fill(); c.restore();
    L.line(c, pts, 1, { color: 'rgba(200,220,210,0.5)', width: 2 });
  },
  fog(c, L, t, a = 0.5) {
    for (let i = 0; i < 9; i++) {
      const y = 200 + L.rnd(i, 2) * 700, x = ((L.rnd(i, 1) * 2400 + t * (20 + 20 * L.rnd(i, 3))) % 2600) - 340;
      const g = c.createRadialGradient(x, y, 0, x, y, 420); g.addColorStop(0, `rgba(210,215,210,${a * 0.35})`); g.addColorStop(1, 'rgba(210,215,210,0)');
      c.fillStyle = g; c.fillRect(x - 420, y - 420, 840, 840);
    }
  },
  shake(c, t, t0, amp = 12, k = 5) { const a = t > t0 ? amp * Math.exp(-(t - t0) * k) : 0; c.translate(Math.sin(t * 90) * a, Math.cos(t * 77) * a); },
  black(c, L, t, a, b) { const f = L.seg(t, a, b); if (f > 0) { c.fillStyle = `rgba(0,0,0,${f})`; c.fillRect(0, 0, 1920, 1080); } },
  krupp(c, x, y, len, o = {}) {  // steel breech-loader on a wheeled carriage, muzzle to the right (dir -1 left)
    c.save(); c.translate(x, y); c.scale(o.dir || 1, 1); const s = len / 400, rec = o.recoil || 0;
    c.fillStyle = o.carriage || '#3b3a36'; c.beginPath(); c.moveTo(-40 * s, -10 * s); c.lineTo(-260 * s, 60 * s); c.lineTo(-250 * s, 74 * s); c.lineTo(-20 * s, 14 * s); c.closePath(); c.fill();
    c.save(); c.translate(-rec * 30 * s, 0);
    const g = c.createLinearGradient(0, -26 * s, 0, 26 * s); g.addColorStop(0, '#b8bcc0'); g.addColorStop(0.5, o.col || '#6d7378'); g.addColorStop(1, '#2a2d30');
    c.fillStyle = g; c.beginPath(); c.moveTo(-90 * s, -26 * s); c.lineTo(220 * s, -14 * s); c.lineTo(220 * s, 14 * s); c.lineTo(-90 * s, 26 * s); c.closePath(); c.fill();
    c.fillStyle = '#1c1e20'; c.fillRect(-110 * s, -22 * s, 26 * s, 44 * s);  // wedge breech block
    c.restore();
    c.strokeStyle = '#2a2420'; c.lineWidth = 9 * s; c.beginPath(); c.arc(0, 30 * s, 70 * s, 0, 7); c.stroke();
    c.lineWidth = 4 * s; for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6 + (o.roll || 0); c.beginPath(); c.moveTo(0, 30 * s); c.lineTo(Math.cos(a) * 66 * s, 30 * s + Math.sin(a) * 66 * s); c.stroke(); }
    c.restore();
  },
  infantry(c, x, y, h, o = {}) {  // Prussian infantryman with Pickelhaube facing right; o.kepi = French kepi; o.aim / o.run
    c.save(); c.translate(x, y); c.scale((o.dir || 1) * h / 200, h / 200); c.fillStyle = o.col || '#1d1a17';
    c.beginPath(); c.arc(0, -180, 16, 0, 7); c.fill();
    if (o.kepi) { c.fillRect(-14, -206, 26, 22); c.fillRect(-14, -190, 34, 6); }
    else { c.beginPath(); c.arc(0, -192, 18, Math.PI, 0); c.fill(); c.fillRect(-2, -224, 4, 20); c.fillRect(-22, -194, 46, 5); }
    c.fillRect(-16, -164, 32, 84);
    const st = o.run ? Math.sin((o.phase || 0) * 9) * 18 : 0;
    c.save(); c.translate(-9, -80); c.rotate(st / 60); c.fillRect(-7, 0, 13, 80); c.restore();
    c.save(); c.translate(9, -80); c.rotate(-st / 60); c.fillRect(-6, 0, 13, 80); c.restore();
    if (o.aim) { c.fillRect(0, -150, 60, 10); c.fillRect(30, -156, 120, 7); } else { c.save(); c.translate(12, -150); c.rotate(o.run ? 0.5 : 0); c.fillRect(-3, -80, 6, 150); c.restore(); }
    c.fillRect(-30, -160, 16, 50);  // knapsack
    c.restore();
  },
  rider(c, x, y, h, t, o = {}) {  // galloping cavalryman facing right with lance or sabre
    c.save(); c.translate(x, y); c.scale((o.dir || 1) * h / 200, h / 200); c.fillStyle = o.col || '#1d1a17';
    const g = Math.sin(t * 14 + (o.phase || 0));
    c.beginPath(); c.ellipse(0, -110, 90, 38, 0, 0, 7); c.fill();  // horse body
    c.save(); c.translate(80, -130); c.rotate(-0.7 + g * 0.08); c.fillRect(0, -16, 70, 30); c.beginPath(); c.ellipse(80, -4, 34, 16, 0.3, 0, 7); c.fill(); c.restore();
    [[-60, 1], [-40, -1], [50, 1], [70, -1]].forEach(([lx, ph]) => { c.save(); c.translate(lx, -90); c.rotate(g * 0.6 * ph); c.fillRect(-6, 0, 12, 85); c.restore(); });
    c.save(); c.translate(-80, -120); c.rotate(0.6 + g * 0.1); c.fillRect(-40, -6, 50, 12); c.restore();  // tail
    c.fillRect(-14, -210, 28, 70); c.beginPath(); c.arc(0, -222, 15, 0, 7); c.fill(); c.fillRect(-16, -244, 32, 14);
    if (o.lance) { c.save(); c.translate(0, -190); c.rotate(-0.25); c.fillRect(-60, -3, 300, 6); c.fillStyle = o.flag || '#c8372d'; c.fillRect(220, -20, 30, 16); c.restore(); }
    else { c.save(); c.translate(10, -200); c.rotate(-1.0); c.fillStyle = '#b8bcc0'; c.fillRect(0, -3, 120, 6); c.restore(); }
    c.restore();
  },
  train(c, L, x, y, len, t, o = {}) {  // locomotive with wagons running right; len = locomotive length
    c.save(); c.translate(x, y); const s = len / 300; c.fillStyle = o.col || '#1d1a17';
    c.fillRect(-150 * s, -110 * s, 200 * s, 70 * s); c.fillRect(30 * s, -170 * s, 90 * s, 130 * s);  // boiler, cab
    c.fillRect(-130 * s, -170 * s, 30 * s, 60 * s); c.beginPath(); c.moveTo(-150 * s, -60 * s); c.lineTo(-200 * s, -20 * s); c.lineTo(-150 * s, -20 * s); c.fill();
    for (let k = 0; k < 3; k++) { c.beginPath(); c.arc((-100 + k * 70) * s, -30 * s, 28 * s, 0, 7); c.fill(); }
    for (let w = 0; w < (o.wagons ?? 6); w++) { const wx = 140 * s + w * 210 * s; c.fillRect(wx, -150 * s, 190 * s, 110 * s); c.beginPath(); c.arc(wx + 40 * s, -30 * s, 22 * s, 0, 7); c.arc(wx + 150 * s, -30 * s, 22 * s, 0, 7); c.fill(); }
    c.restore();
    for (let i = 0; i < 6; i++) { const age = ((t * 1.3 + i / 6) % 1); K.puff(c, x - 115 * s - age * 220 * s, y - 180 * s - age * 160 * s, (20 + age * 70) * s, 0.5 * (1 - age)); }
  },
  puff(c, x, y, r, a) { const g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, `rgba(220,215,205,${a})`); g.addColorStop(1, 'rgba(220,215,205,0)'); c.fillStyle = g; c.fillRect(x - r, y - r, 2 * r, 2 * r); },
  burst(c, L, x, y, t, t0, s = 1) {  // shell burst: flash, ring, smoke
    const age = t - t0; if (age < 0) return;
    K.flash(c, L, x, y, t, t0, 1.4 * s);
    if (age < 0.6) L.circle(c, x, y, 40 * s + age * 260 * s, { stroke: `rgba(255,200,120,${0.8 * (1 - age / 0.6)})`, width: 4 });
    K.smoke(c, L, x, y, t, t0 + 0.05, { r: 110 * s, n: 10, life: 4, drift: 14, alpha: 0.7, col: '120,110,100' });
  },
  // Egg-shaped period character ("doll"), facing the viewer. Use ONLY where no real picture of the person/unit exists.
  // One egg: face in the upper part, coat below (like the reference Short). (x, y) = feet centre; h = height without hat.
  // o.side: 'pru' (Prussian dark blue, red facings), 'fra' (French blue, white facings, white cross-belts), 'brit' (red coat), 'civ' (Landwehr brown), 'rus'
  // o.hat: 'bicorne' | 'shako' | 'bearskin' | 'cap' (Prussian/Landwehr Schirmmütze) | 'hussar' (busby) | 'none'
  // o.face: 'calm' | 'grim' | 'shock' | 'dead' | 'shout' | 'smile'; o.hair: 'grey' | 'white' | 'dark' | 'bald'
  // o.musket, o.sabre (o.raise), o.epaulettes (officer), o.moustache, o.bob (idle-bounce phase), o.tilt (radians, e.g. falling)
  // Vietnam 1860s: side 'dnam' (Nguyễn soldier, hat 'nondau'), 'quan' (mandarin, hat 'canhchuon'), 'dan' (commoner, hat 'khan'); 'mar' = French marine (hat 'kepi', o.cover);
  // o.beard (long grey scholar's beard), o.spear (giáo)
  doll(c, L, x, y, h, t, o = {}) {
    const C = { pru: ['#141a2b', '#c0282d', '#ece6d8'], fra: ['#2f5fc4', '#f4f0e6', '#ece6d8'], brit: ['#b52a2c', '#ece6d8', '#22305a'], civ: ['#6a5238', '#d9cfb8', '#3a2e22'], rus: ['#34552f', '#c0282d', '#ece6d8'], dnam: ['#7a1f1a', '#1a1612', '#c9a24a'], quan: ['#1f2a5a', '#c9a24a', '#c9a24a'], dan: ['#3a3128', '#2a221a', '#5a4a38'], mar: ['#1c2440', '#c0282d', '#ece6d8'] }[o.side || 'pru'];
    if (o.coat) C[0] = o.coat;  // e.g. the emperor's yellow robe
    const bob = Math.sin((t || 0) * 3 + (o.bob || 0)) * 3;
    c.save(); c.translate(x, y + bob); c.rotate(o.tilt || 0); c.scale((o.dir || 1) * h / 400, h / 400);
    c.fillStyle = 'rgba(0,0,0,0.3)'; c.beginPath(); c.ellipse(0, 4, 120, 18, 0, 0, 7); c.fill();  // ground shadow
    const egg = () => { c.beginPath(); c.moveTo(-118, -8); c.bezierCurveTo(-140, -200, -100, -400, 0, -400); c.bezierCurveTo(100, -400, 140, -200, 118, -8); c.quadraticCurveTo(0, 12, -118, -8); };
    // skin fills the whole egg, coat is clipped to the lower part
    c.save(); egg(); c.clip();
    c.fillStyle = o.skin || '#f2d9c2'; c.fillRect(-160, -420, 320, 440);
    const g = c.createLinearGradient(-130, 0, 130, 0); g.addColorStop(0, C[0]); g.addColorStop(0.6, C[0]); g.addColorStop(1, '#0b0e18');
    c.fillStyle = g; c.beginPath(); c.moveTo(-160, -205); c.quadraticCurveTo(0, -175, 160, -205); c.lineTo(160, 20); c.lineTo(-160, 20); c.fill();
    c.fillStyle = C[1]; c.fillRect(-160, -212, 320, 18);  // collar
    // chest tells the armies apart (1815): French habit-veste = wide white plastron with two button rows;
    // Prussian Kollet = plain near-black coat, one row of buttons, red collar only; others keep the V facings
    if (o.side === 'fra') {
      c.fillStyle = C[1]; c.beginPath(); c.moveTo(-64, -196); c.lineTo(64, -196); c.lineTo(58, -96); c.quadraticCurveTo(0, -78, -58, -96); c.closePath(); c.fill();
      c.fillStyle = '#c0282d'; c.fillRect(-160, -100, 320, 0);
      c.fillStyle = '#d8b450'; for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(-48, -180 + i * 26, 5, 0, 7); c.arc(48, -180 + i * 26, 5, 0, 7); c.fill(); }
    } else if (o.side === 'dnam' || o.side === 'dan') {  // áo nẹp / áo dài closing on the right shoulder, sash
      c.strokeStyle = C[1]; c.lineWidth = 10; c.beginPath(); c.moveTo(-20, -200); c.quadraticCurveTo(60, -170, 70, -80); c.stroke();
      if (o.side === 'dnam') { c.fillStyle = '#c9a24a'; c.beginPath(); c.arc(0, -140, 26, 0, 7); c.fill(); c.fillStyle = '#7a1f1a'; c.font = 'bold 30px serif'; c.textAlign = 'center'; c.fillText('兵', 0, -129); }
      c.fillStyle = C[2]; c.fillRect(-160, -64, 320, 14);
    } else if (o.side === 'quan') {  // áo thụng with a square rank badge (bổ tử)
      c.strokeStyle = C[1]; c.lineWidth = 8; c.beginPath(); c.moveTo(-20, -200); c.quadraticCurveTo(60, -170, 70, -80); c.stroke();
      c.fillStyle = '#c9a24a'; c.fillRect(-46, -170, 92, 84); c.fillStyle = '#1f2a5a'; c.fillRect(-36, -160, 72, 64); c.strokeStyle = '#c9a24a'; c.lineWidth = 3; c.beginPath(); c.arc(0, -128, 18, 0, 7); c.stroke();
    } else if (o.side === 'mar') {  // infanterie de marine 1860s: dark blue tunic, one brass row, red piping
      c.fillStyle = '#d8b450'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(0, -184 + i * 28, 5, 0, 7); c.fill(); }
    } else if (o.side === 'pru') {
      c.fillStyle = '#e8e2d2'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(0, -184 + i * 28, 5, 0, 7); c.fill(); }
      c.fillStyle = C[1]; c.fillRect(-160, -60, 320, 0);
    } else {
      c.beginPath(); c.moveTo(-40, -196); c.lineTo(0, -70); c.lineTo(40, -196); c.lineTo(22, -196); c.lineTo(0, -120); c.lineTo(-22, -196); c.fill();  // facings
      c.fillStyle = '#e0bd5a'; for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(-12, -170 + i * 34, 5, 0, 7); c.arc(12, -170 + i * 34, 5, 0, 7); c.fill(); }
    }
    if (o.belts !== false && !o.epaulettes && !['dnam', 'quan', 'dan'].includes(o.side)) { c.strokeStyle = C[2]; c.lineWidth = 12; c.beginPath(); c.moveTo(-90, -190); c.lineTo(90, -20); c.moveTo(90, -190); c.lineTo(-90, -20); c.stroke(); }
    if (o.epaulettes) { c.fillStyle = C[1]; c.fillRect(-160, -80, 320, 14); }  // sash
    // soft shading on the right side, highlight on the left
    const sh = c.createRadialGradient(-50, -300, 20, 0, -200, 260); sh.addColorStop(0, 'rgba(255,255,255,0.18)'); sh.addColorStop(0.6, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.35)');
    c.fillStyle = sh; c.fillRect(-160, -420, 320, 440);
    c.restore();
    c.strokeStyle = 'rgba(0,0,0,0.55)'; c.lineWidth = 4; egg(); c.stroke();
    if (o.epaulettes) { c.fillStyle = '#e0bd5a'; [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 105, -190, 34, 12, sd * 0.35, 0, 7); c.fill(); c.strokeStyle = 'rgba(0,0,0,0.4)'; c.lineWidth = 2; c.stroke(); }); }
    const hair = { grey: '#a19d96', white: '#ece8e0', dark: '#3e2c1f', bald: null }[o.hair || 'dark'];
    if (hair && o.hat !== 'bearskin' && o.hat !== 'hussar') { c.fillStyle = hair; c.beginPath(); c.ellipse(-92, -290, 20, 40, 0.15, 0, 7); c.ellipse(92, -290, 20, 40, -0.15, 0, 7); c.fill(); if (o.hat === 'none') { c.beginPath(); c.ellipse(0, -372, 80, 34, 0, Math.PI, 0); c.fill(); } }
    if (o.moustache) { c.fillStyle = hair || '#3e2c1f'; c.beginPath(); c.ellipse(-18, -246, 22, 7, 0.25, 0, 7); c.ellipse(18, -246, 22, 7, -0.25, 0, 7); c.fill(); }
    // face: dot eyes and one stroke
    c.fillStyle = '#16120f'; c.strokeStyle = '#16120f'; c.lineWidth = 5; const f = o.face || 'calm';
    if (f === 'dead') { [[-30, -290], [30, -290]].forEach(([ex, ey]) => { c.beginPath(); c.moveTo(ex - 11, ey - 11); c.lineTo(ex + 11, ey + 11); c.moveTo(ex + 11, ey - 11); c.lineTo(ex - 11, ey + 11); c.stroke(); }); }
    else { c.beginPath(); c.ellipse(-30, -290, 8, 11, 0, 0, 7); c.ellipse(30, -290, 8, 11, 0, 0, 7); c.fill(); }
    if (f === 'grim') { c.beginPath(); c.moveTo(-50, -318); c.lineTo(-16, -308); c.moveTo(50, -318); c.lineTo(16, -308); c.moveTo(-16, -258); c.lineTo(16, -258); c.stroke(); }
    else if (f === 'shock') { c.fillStyle = '#5a1a14'; c.beginPath(); c.ellipse(0, -246, 17, 26, 0, 0, 7); c.fill(); }
    else if (f === 'shout') { c.fillStyle = '#5a1a14'; c.beginPath(); c.ellipse(0, -250, 22, 15, 0, 0, 7); c.fill(); }
    else if (f === 'smile') { c.beginPath(); c.arc(0, -266, 16, 0.25, Math.PI - 0.25); c.stroke(); }
    else if (f !== 'dead') { c.beginPath(); c.moveTo(-11, -258); c.lineTo(11, -258); c.stroke(); }
    // hats: dark felt with a light rim stroke so they read on dark backgrounds
    const hat = o.hat || 'shako', rim = () => { c.strokeStyle = 'rgba(210,205,195,0.55)'; c.lineWidth = 3; c.stroke(); };
    const felt = (x0, y0, x1, y1) => { const hg = c.createLinearGradient(x0, y0, x1, y1); hg.addColorStop(0, '#3b3b3e'); hg.addColorStop(1, '#0d0d0f'); return hg; };
    if (hat === 'bicorne') {  // worn sideways (en bataille), wide and tall
      c.fillStyle = felt(0, -500, 0, -360); c.beginPath(); c.moveTo(-175, -350); c.quadraticCurveTo(-60, -520, 0, -505); c.quadraticCurveTo(60, -520, 175, -350); c.quadraticCurveTo(0, -385, -175, -350); c.fill(); rim();
      if (o.cockade !== false) { c.fillStyle = o.side === 'fra' ? '#c0282d' : '#ece6d8'; c.beginPath(); c.arc(50, -420, 16, 0, 7); c.fill(); c.fillStyle = o.side === 'fra' ? '#ece6d8' : '#16120f'; c.beginPath(); c.arc(50, -420, 10, 0, 7); c.fill(); c.fillStyle = o.side === 'fra' ? '#2a4c9a' : '#ece6d8'; c.beginPath(); c.arc(50, -420, 5, 0, 7); c.fill(); }
    } else if (hat === 'shako') {
      c.fillStyle = felt(-70, 0, 70, 0); c.beginPath(); c.moveTo(-74, -370); c.lineTo(-84, -490); c.lineTo(84, -490); c.lineTo(74, -370); c.closePath(); c.fill(); rim();
      c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(0, -368, 96, 16, 0, 0, Math.PI); c.fill();  // peak
      if (o.side === 'fra') {  // French 1812 shako: brass lozenge plate with eagle, brass top band, red pompon, chinscales
        c.fillStyle = '#e0bd5a'; c.beginPath(); c.moveTo(0, -470); c.lineTo(34, -428); c.lineTo(0, -386); c.lineTo(-34, -428); c.closePath(); c.fill();
        c.fillStyle = '#9a7a2a'; c.beginPath(); c.arc(0, -428, 9, 0, 7); c.fill();
        c.fillStyle = '#e0bd5a'; c.fillRect(-84, -494, 168, 10); c.fillRect(-80, -378, 10, 30); c.fillRect(70, -378, 10, 30);
        c.fillStyle = '#c0282d'; c.beginPath(); c.ellipse(0, -508, 20, 18, 0, 0, 7); c.fill();
      } else {  // Prussian shako 1815: plain black (often in oilcloth), small black-white cockade, no plate
        c.fillStyle = '#ece6d8'; c.beginPath(); c.arc(0, -462, 12, 0, 7); c.fill(); c.fillStyle = '#16120f'; c.beginPath(); c.arc(0, -462, 6, 0, 7); c.fill();
        c.strokeStyle = 'rgba(255,255,255,0.18)'; c.lineWidth = 3; c.beginPath(); c.moveTo(-80, -440); c.lineTo(80, -440); c.stroke();
      }
    } else if (hat === 'cap') {
      c.fillStyle = felt(0, -420, 0, -360); c.beginPath(); c.ellipse(0, -400, 100, 34, 0, 0, 7); c.fill(); rim();
      c.fillRect(-88, -398, 176, 30); c.fillStyle = C[1]; c.fillRect(-88, -384, 176, 14);
      c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(0, -366, 92, 16, 0, 0, Math.PI); c.fill();
      if (o.side === 'civ') { c.fillStyle = '#ece6d8'; c.beginPath(); c.moveTo(-10, -378); c.lineTo(10, -378); c.lineTo(0, -392); c.fill(); }  // Landwehr cross hint
    } else if (hat === 'bearskin') {
      c.fillStyle = felt(-90, 0, 90, 0); c.beginPath(); c.ellipse(0, -440, 96, 120, 0, 0, 7); c.fill(); rim();
      c.fillStyle = '#c0282d'; c.fillRect(56, -500, 16, 90); c.fillStyle = '#e0bd5a'; c.fillRect(-70, -350, 140, 10);
    } else if (hat === 'hussar') {
      c.fillStyle = felt(0, -460, 0, -360); c.beginPath(); c.ellipse(0, -410, 92, 64, 0, 0, 7); c.fill(); rim();
      c.fillStyle = C[1]; c.beginPath(); c.moveTo(60, -440); c.quadraticCurveTo(130, -400, 100, -330); c.lineTo(78, -360); c.fill();
    }
    else if (hat === 'kepi') {  // French 1860s kepi with a white sun cover (couvre-nuque) for Cochinchina
      c.fillStyle = o.cover ? '#e8e2d2' : '#1c2440'; c.beginPath(); c.moveTo(-80, -370); c.lineTo(-70, -455); c.lineTo(76, -445); c.lineTo(80, -370); c.closePath(); c.fill(); rim();
      c.fillStyle = '#c0282d'; c.fillRect(-82, -392, 164, 12); c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(20, -366, 90, 14, 0, 0, Math.PI); c.fill();
      if (o.cover) { c.fillStyle = '#e8e2d2'; c.beginPath(); c.moveTo(-82, -380); c.lineTo(-110, -300); c.lineTo(-40, -330); c.closePath(); c.fill(); }
    } else if (hat === 'nondau') {  // Nguyễn soldier's small conical hat with a red tuft
      c.fillStyle = '#d9c48c'; c.beginPath(); c.moveTo(-150, -350); c.lineTo(0, -470); c.lineTo(150, -350); c.quadraticCurveTo(0, -330, -150, -350); c.fill(); rim();
      c.strokeStyle = 'rgba(90,70,40,0.5)'; c.lineWidth = 2; for (let k = -2; k <= 2; k++) { c.beginPath(); c.moveTo(0, -470); c.lineTo(k * 60, -345); c.stroke(); }
      c.fillStyle = '#c0282d'; c.beginPath(); c.ellipse(0, -478, 18, 22, 0, 0, 7); c.fill();
    } else if (hat === 'canhchuon') {  // mandarin's black hat with side wings
      c.fillStyle = felt(0, -470, 0, -360); c.beginPath(); c.moveTo(-84, -360); c.lineTo(-74, -450); c.quadraticCurveTo(0, -480, 74, -450); c.lineTo(84, -360); c.closePath(); c.fill(); rim();
      c.fillStyle = '#16120f'; [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 140, -400, 60, 16, sd * -0.2, 0, 7); c.fill(); });
      c.fillStyle = '#c9a24a'; c.fillRect(-84, -380, 168, 8);
    } else if (hat === 'khan') {  // khăn vấn (wrapped turban)
      c.fillStyle = '#1a1612'; c.beginPath(); c.ellipse(0, -372, 104, 40, 0, Math.PI, 0); c.fill(); rim();
      c.strokeStyle = 'rgba(210,205,195,0.25)'; c.lineWidth = 3; for (let k = 0; k < 3; k++) { c.beginPath(); c.ellipse(0, -360 - k * 10, 100 - k * 8, 30, 0, Math.PI * 1.05, Math.PI * 1.95); c.stroke(); }
    }
    if (o.beard) { c.fillStyle = hair || '#a19d96'; c.beginPath(); c.moveTo(-34, -240); c.quadraticCurveTo(0, -150, 34, -240); c.quadraticCurveTo(0, -226, -34, -240); c.fill(); }
    if (o.spear) { c.save(); c.translate(120, -40); c.fillStyle = '#6b4a2e'; c.fillRect(-6, -420, 12, 450); c.fillStyle = '#c9ccd0'; c.beginPath(); c.moveTo(-14, -420); c.lineTo(0, -500); c.lineTo(14, -420); c.closePath(); c.fill(); c.fillStyle = '#c0282d'; c.fillRect(-12, -420, 24, 16); c.restore(); }
    if (o.musket) { c.save(); c.translate(120, -40); c.rotate(-0.18); c.fillStyle = '#6b4a2e'; c.fillRect(-8, -230, 16, 260); c.fillStyle = '#9a978f'; c.fillRect(-4, -330, 8, 110); if (o.bayonet !== false) { c.fillStyle = '#d4d8dc'; c.fillRect(-3, -400, 6, 72); } c.restore(); }
    if (o.sabre) { c.save(); c.translate(115, -110); c.rotate(o.raise ? -2.2 : -0.35); c.fillStyle = '#d4d8dc'; c.fillRect(0, -4, 200, 8); c.fillStyle = '#e0bd5a'; c.fillRect(-16, -11, 20, 22); c.restore(); }
    c.restore();
  },
  gunboat(c, L, x, y, len, t, o = {}) {  // 1860s steam gunboat (canonnière), side view, bow to the right; funnel smoke drifts back. o.fire = time of a bow-gun shot
    c.save(); c.translate(x, y); c.scale(o.dir || 1, 1); const s = len / 800;
    c.fillStyle = o.hull || '#22201d'; c.strokeStyle = o.line || 'rgba(237,231,220,0.4)'; c.lineWidth = 2;
    c.beginPath(); c.moveTo(-400 * s, -60 * s); c.lineTo(370 * s, -60 * s); c.lineTo(420 * s, -78 * s); c.quadraticCurveTo(400 * s, 10 * s, 330 * s, 26 * s);
    c.lineTo(-360 * s, 26 * s); c.quadraticCurveTo(-410 * s, 10 * s, -400 * s, -60 * s); c.closePath(); c.fill(); c.stroke();
    c.fillStyle = 'rgba(237,231,220,0.12)'; c.fillRect(-390 * s, -40 * s, 760 * s, 6 * s);  // sheer stripe
    c.fillStyle = o.house || '#3a3631'; c.fillRect(-120 * s, -110 * s, 200 * s, 50 * s);  // deckhouse
    c.fillStyle = o.funnel || '#141210'; c.fillRect(-40 * s, -230 * s, 46 * s, 120 * s);  // funnel
    c.strokeStyle = o.mastCol || '#2c2925'; c.lineWidth = 7 * s; [[-260, -330], [200, -300]].forEach(([mx, my]) => { c.beginPath(); c.moveTo(mx * s, -60 * s); c.lineTo(mx * s, my * s); c.stroke(); });
    c.lineWidth = 2; c.strokeStyle = 'rgba(237,231,220,0.25)'; c.beginPath(); c.moveTo(-260 * s, -330 * s); c.lineTo(-400 * s, -62 * s); c.moveTo(200 * s, -300 * s); c.lineTo(410 * s, -76 * s); c.stroke();
    if (o.flag !== false) { const w = Math.sin((t || 0) * 5) * 4; c.fillStyle = '#2f5fc4'; c.fillRect(-260 * s, -330 * s, 22 * s, 30 * s); c.fillStyle = '#f4f0e6'; c.fillRect(-238 * s, -330 * s + w * s, 22 * s, 30 * s); c.fillStyle = '#c0282d'; c.fillRect(-216 * s, -330 * s + 2 * w * s, 22 * s, 30 * s); }
    K.krupp(c, 300 * s, -78 * s, 150 * s, { recoil: o.fire != null ? Math.max(0, 1 - Math.abs(((t || 0) - o.fire) * 4)) * (t > o.fire ? 1 : 0) : 0 });
    c.restore();
    const fx = x + (o.dir || 1) * (-17 * s), fy = y - 230 * s;
    for (let i = 0; i < 8; i++) { const age = (((t || 0) * 0.35 + i / 8) % 1); K.puff(c, fx - (o.dir || 1) * age * 420 * s, fy - age * 200 * s, (26 + age * 120) * s, (o.smoke ?? 0.55) * (1 - age)); }
    if (o.fire != null) { const mx = x + (o.dir || 1) * 525 * s, my = y - 78 * s; K.flash(c, L, mx, my, t, o.fire, 1.6 * s * 2); K.smoke(c, L, mx, my, t, o.fire, { r: 160 * s * 2, n: 10, drift: -(o.dir || 1) * 30, life: 4, alpha: 0.7 }); }
  },
  // Declarative doll stage (film 6): one config per scene instead of a hand-drawn scene. Times are on the 10 s scale.
  // cfg: { set: 'citadel'|'river'|'court'|'hq'|'field'|'village'|'port'|'night'|'workshop'|'rain', gy (ground y, 820),
  //   walls: [{x0, x1, y, h, gate, crumble}], boats: [{x, y, len, dir, fire:[t], move:[x0, x1, t0, t1], smoke}],
  //   cannons: [{x, y, len, dir, fire:[t], col}], shells: [{from:[x,y], to:[x,y], t0, t1, arc}], bursts: [{x, y, t, s}],
  //   cast: [{side, hat, x, y, h, dir, face, faceAt:[t, face], move:[x0, x1, t0, t1], aim, fire:[t], fall:t, tremble, bow, carry, shovel, write, point:[x, y, t], opts}],
  //   props: [{k:'table'|'kegs'|'bags'|'bricks'|'flag'|'scroll'|'map'|'fire'|'house'|'tree'|'sampan', ...}], rain, fog, night,
  //   tag: [text, sub, t0], title: [text, t0, color], push }
  stage(c, L, t, g) {
    const { C, seg } = L, gy = g.gy || 820, S = g.set || 'field';
    const pz = 1 + (g.push ?? 0.04) * L.lin(t, 0, 10);
    c.save(); c.translate(960, 600); c.scale(pz, pz); c.translate(-960, -600);
    // ---- set
    const sky = { night: ['#0b0f18', '#1a2230'], rain: ['#2a3038', '#4a525a'], river: ['#3a4652', '#7d8378'], citadel: ['#3a4652', '#8a8478'], field: ['#4a5260', '#a09a88'], village: ['#4a5260', '#a09a88'], port: ['#3a4652', '#8a8a80'] }[S];
    if (sky) { const gr = c.createLinearGradient(0, 0, 0, gy); gr.addColorStop(0, sky[0]); gr.addColorStop(1, sky[1]); c.fillStyle = gr; c.fillRect(0, 0, 1920, gy); }
    if (S === 'night' || g.night) L.dot(c, 1620, 170, 42, 'rgba(230,225,200,0.85)');
    if (S === 'court' || S === 'hq') { c.fillStyle = S === 'court' ? '#3a1410' : '#21160f'; c.fillRect(0, 0, 1920, gy); c.fillStyle = '#4a1d16'; [160, 1760].forEach(x => c.fillRect(x - 30, 60, 60, gy)); c.fillStyle = '#2a1a12'; c.fillRect(0, 60, 1920, 36);
      [560, 1360].forEach((x, i) => { const a = Math.sin(t * 2 + i) * 0.07; c.save(); c.translate(x, 96); c.rotate(a); L.line(c, [[0, 0], [0, 80]], 1, { color: '#1a1612', width: 3 }); c.fillStyle = '#b8352a'; c.beginPath(); c.ellipse(0, 128, 36, 46, 0, 0, 7); c.fill(); c.restore(); });
      if (S === 'court') { c.fillStyle = '#c9a24a'; c.fillRect(760, 150, 400, 12); c.fillStyle = '#5a1e14'; c.fillRect(780, 162, 360, 260); } }
    if (S === 'workshop') { c.fillStyle = '#1e1813'; c.fillRect(0, 0, 1920, gy); const f = 0.6 + 0.4 * Math.sin(t * 9); const gr = c.createRadialGradient(400, 700, 0, 400, 700, 600); gr.addColorStop(0, `rgba(255,140,50,${0.35 * f})`); gr.addColorStop(1, 'rgba(255,140,50,0)'); c.fillStyle = gr; c.fillRect(0, 100, 1000, 900); }
    if (S === 'river' || S === 'port' || g.water) K.water(c, L, g.wy || gy - 40, t, { amp: 3 });
    if (S === 'village') { [[260, 0.9], [620, 1.1], [1500, 1]].forEach(([x, s]) => { c.fillStyle = '#3a2c1e'; c.fillRect(x - 110 * s, gy - 150 * s, 220 * s, 150 * s); c.fillStyle = '#6b5a3a'; c.beginPath(); c.moveTo(x - 150 * s, gy - 140 * s); c.lineTo(x, gy - 260 * s); c.lineTo(x + 150 * s, gy - 140 * s); c.fill(); }); }
    if (S !== 'river' && S !== 'port' && !g.noGround) K.ground(c, gy, S === 'court' || S === 'hq' ? '#2a1c14' : '#2c261e');
    if (S === 'port' || S === 'river') { c.fillStyle = '#3a3226'; c.fillRect(0, gy - 40, g.quay ?? 0, 1080); }
    // ---- walls (brick rampart with crenels, optional gate, optional crumble at t)
    (g.walls || []).forEach(w => { const y = w.y ?? gy, h = w.h ?? 260, br = w.crumble != null && t > w.crumble ? L.easeOut(L.lin(t, w.crumble, w.crumble + 1.4)) : 0;
      for (let yy = y - h; yy < y; yy += 40) for (let x = w.x0 + ((yy / 40) % 2) * 32; x < w.x1; x += 64) { const cx = (w.x0 + w.x1) / 2, d = Math.abs(x - cx);
        if (br && d < (w.x1 - w.x0) * 0.25 && yy < y - 40) { const k = L.rnd(x, yy); if (k < br) continue; }
        c.fillStyle = (Math.round(x / 64) + Math.round(yy / 40)) % 3 ? '#7a4630' : '#8a5236'; c.fillRect(x, yy, 60, 36); }
      c.fillStyle = '#6e563f'; for (let x = w.x0; x < w.x1 - 40; x += 110) c.fillRect(x, y - h - 50, 66, 50);
      if (w.gate) { const gx = (w.x0 + w.x1) / 2, o = w.open != null ? L.ease(L.lin(t, w.open, w.open + 2)) : 0; c.fillStyle = '#c9b48a'; c.beginPath(); c.moveTo(gx - 110, y); c.lineTo(gx - 110, y - 150); c.arc(gx, y - 150, 110, Math.PI, 0); c.lineTo(gx + 110, y); c.fill();
        c.fillStyle = '#5a3a22'; c.fillRect(gx - 110, y - 200, 110 * (1 - o) + 2, 200); c.fillRect(gx + 110 - 110 * (1 - o) - 2, y - 200, 110 * (1 - o) + 2, 200); }
      if (br) for (let i = 0; i < 3; i++) K.burst(c, L, (w.x0 + w.x1) / 2 + (i - 1) * 80, y - h * 0.5, t, w.crumble + i * 0.12, 1.8); });
    // ---- props
    (g.props || []).forEach(p => { const a = p.t0 != null ? seg(t, p.t0, p.t0 + 0.4) : 1; if (a <= 0) return; c.save(); c.globalAlpha *= a;
      if (p.k === 'table') { c.fillStyle = '#3a2416'; c.fillRect(p.x - (p.w || 300) / 2, p.y, p.w || 300, 26); c.fillRect(p.x - (p.w || 300) / 2 + 20, p.y + 26, 18, gy - p.y - 26); c.fillRect(p.x + (p.w || 300) / 2 - 38, p.y + 26, 18, gy - p.y - 26); }
      else if (p.k === 'kegs') for (let i = 0; i < (p.n || 4); i++) { c.fillStyle = '#5a3a22'; c.fillRect(p.x + i * 70, gy - 90, 60, 90); c.fillStyle = '#2a1a10'; c.fillRect(p.x + i * 70, gy - 70, 60, 8); c.fillRect(p.x + i * 70, gy - 30, 60, 8); }
      else if (p.k === 'bags') for (let i = 0; i < (p.n || 8); i++) { const r = Math.floor(i / 4); c.fillStyle = '#b8a070'; c.beginPath(); c.ellipse(p.x + (i % 4) * 70 + r * 35, gy - 30 - r * 50, 36, 28, 0, 0, 7); c.fill(); }
      else if (p.k === 'bricks') for (let i = 0; i < (p.n || 12); i++) { c.fillStyle = '#8a4b32'; c.fillRect(p.x + (i % 5) * 64 + (Math.floor(i / 5) % 2) * 32, gy - 40 - Math.floor(i / 5) * 40, 60, 36); }
      else if (p.k === 'flag') { const up = p.raise != null ? L.ease(L.lin(t, p.raise, p.raise + 2.5)) : 1, fy = p.y - (p.h || 300) * (0.25 + 0.75 * up); L.line(c, [[p.x, p.y], [p.x, p.y - (p.h || 300)]], 1, { color: '#2c2925', width: 6 }); const w = Math.sin(t * 5) * 5;
        const cols = p.fr ? ['#2f5fc4', '#f4f0e6', '#c0282d'] : ['#d8a520', '#d8a520', '#d8a520']; cols.forEach((col, k) => { c.fillStyle = col; c.fillRect(p.x + k * 40, fy + w * k * 0.5, 40, 80); }); }
      else if (p.k === 'scroll') { c.fillStyle = '#ece2c8'; c.fillRect(p.x, p.y, p.w || 120, p.h || 160); c.fillStyle = '#1a1612'; for (let i = 0; i < 6; i++) c.fillRect(p.x + 14 + (i % 3) * 34, p.y + 16 + Math.floor(i / 3) * 70, 12, 50); c.fillStyle = '#c9a24a'; c.fillRect(p.x - 8, p.y - 6, (p.w || 120) + 16, 10); }
      else if (p.k === 'map') { c.fillStyle = '#d9c9a2'; c.fillRect(p.x, p.y, p.w || 400, p.h || 220); L.line(c, [[p.x + 20, p.y + 150], [p.x + 140, p.y + 120], [p.x + 260, p.y + 140], [p.x + (p.w || 400) - 20, p.y + 80]], 1, { color: '#4f7f99', width: 10 }); if (p.mark) L.circle(c, p.x + p.mark[0], p.y + p.mark[1], 26, { stroke: C.red, width: 5, alpha: seg(t, p.markAt || 0, (p.markAt || 0) + 0.4) }); }
      else if (p.k === 'fire') { for (let i = 0; i < 5; i++) { const u = (t * 1.2 + i / 5) % 1; K.puff(c, p.x + Math.sin(i * 3 + t) * 30, p.y - u * 200, 30 + u * 80, 0.5 * (1 - u)); } const f = 0.6 + 0.4 * Math.sin(t * 13); const gr = c.createRadialGradient(p.x, p.y, 0, p.x, p.y, 120); gr.addColorStop(0, `rgba(255,160,60,${0.8 * f})`); gr.addColorStop(1, 'rgba(255,90,20,0)'); c.fillStyle = gr; c.fillRect(p.x - 120, p.y - 120, 240, 240); }
      else if (p.k === 'house') { const s = p.s || 1; c.fillStyle = '#3a2c1e'; c.fillRect(p.x - 110 * s, (p.y || gy) - 150 * s, 220 * s, 150 * s); c.fillStyle = '#6b5a3a'; c.beginPath(); c.moveTo(p.x - 150 * s, (p.y || gy) - 140 * s); c.lineTo(p.x, (p.y || gy) - 260 * s); c.lineTo(p.x + 150 * s, (p.y || gy) - 140 * s); c.fill(); }
      else if (p.k === 'tree') { c.fillStyle = '#2a2018'; c.fillRect(p.x - 10, gy - 260, 20, 260); c.fillStyle = '#26361f'; c.beginPath(); c.arc(p.x, gy - 300, 110, 0, 7); c.fill(); }
      else if (p.k === 'sampan') { const x = p.move ? L.lerp(p.move[0], p.move[1], L.lin(t, p.move[2], p.move[3])) : p.x; K.boat(c, L, x, p.y, p.len || 320, t, { gun: false, dir: p.dir || 1, stroke: 4, hull: '#3a2a1c' }); }
      else if (p.k === 'press') { const cyc = (t * 1.6) % 1, dn = cyc < 0.3 ? cyc / 0.3 : Math.max(0, 1 - (cyc - 0.3) / 0.4); c.fillStyle = '#4a4440'; c.fillRect(p.x, p.y, 260, 50); c.fillRect(p.x + 30, p.y + 50 + dn * 100, 200, 40); c.fillRect(p.x - 20, p.y + 250, 300, 30); }
      c.restore(); });
    // ---- cannons (bronze on a fixed bed)
    (g.cannons || []).forEach(k => { K.cannon(c, k.x, k.y, k.len || 260, { dir: k.dir || 1, col: k.col }); (k.fire || []).forEach(f => { const mx = k.x + (k.dir || 1) * (k.len || 260) * 0.52; K.flash(c, L, mx, k.y, t, f, 1.3); K.smoke(c, L, mx, k.y, t, f, { r: 140, n: 10, life: 4, alpha: 0.7, drift: (k.dir || 1) * 20 }); }); });
    // ---- boats
    (g.boats || []).forEach(b => { const x = b.move ? L.lerp(b.move[0], b.move[1], L.ease(L.lin(t, b.move[2], b.move[3]))) : b.x;
      (b.fire || [null]).forEach((f, i) => { if (i === 0) K.gunboat(c, L, x, b.y, b.len || 520, t, { dir: b.dir || 1, fire: f, smoke: b.smoke }); else if (f != null) { const mx = x + (b.dir || 1) * 525 * (b.len || 520) / 800, my = b.y - 78 * (b.len || 520) / 800; K.flash(c, L, mx, my, t, f, 1.6); K.smoke(c, L, mx, my, t, f, { r: 150, n: 10, life: 4, alpha: 0.7 }); } }); });
    // ---- cast
    (g.cast || []).forEach((p, i) => {
      let x = p.x, y = p.y ?? gy, tilt = p.tilt || 0, face = p.face;
      if (p.move) x = L.lerp(p.move[0], p.move[1], L.lin(t, p.move[2], p.move[3]));
      if (p.faceAt && t > p.faceAt[0]) face = p.faceAt[1];
      if (p.tremble) x += Math.sin(t * 34 + i * 2) * 3;
      if (p.bow) tilt += Math.max(0, Math.sin(t * 1.4 + i)) * 0.25 * (p.dir || 1);
      if (p.fall != null && t > p.fall) { const u = L.easeOut(L.lin(t, p.fall, p.fall + 0.7)); tilt += u * 1.35 * (p.fallDir || -1); y += u * 40; face = 'dead'; }
      if (p.carry) tilt += 0.1 * (p.dir || 1);
      const walk = p.move && t > p.move[2] && t < p.move[3];
      K.doll(c, L, x, y, p.h || 260, walk ? t * 3 + i : (p.still ? 0 : t + i), Object.assign({ side: p.side, hat: p.hat, dir: p.dir || 1, face, tilt }, p.opts || {}));
      const s = (p.h || 260) / 400, d = p.dir || 1;
      if (p.aim) { c.save(); c.translate(x + d * 40 * s, y - 230 * s); c.scale(d, 1); K.musket(c, 120 * s, 0, 420 * s, {}); c.restore();
        (p.fire || []).forEach(f => { const mx = x + d * 360 * s, my = y - 240 * s; K.flash(c, L, mx, my, t, f, 0.6); K.smoke(c, L, mx, my, t, f, { r: 60, n: 6, life: 2.5, alpha: 0.55, drift: d * 12 }); }); }
      if (p.carry) { c.fillStyle = p.carry === 'coal' ? '#141210' : p.carry === 'brick' ? '#8a4b32' : '#b8a070'; c.beginPath(); c.ellipse(x, y - 440 * s, 70 * s, 34 * s, 0, 0, 7); c.fill(); }
      if (p.shovel) { const ph = Math.sin(t * 5 + i); L.line(c, [[x + d * 60 * s, y - 200 * s], [x + d * (180 + ph * 50) * s, y - (40 + ph * 30) * s]], 1, { color: '#8a6a44', width: 8 }); }
      if (p.write) { const bx = x + d * 140 * s + Math.sin(t * 8) * 4; L.line(c, [[bx, y - 190 * s], [bx + 30, y - 260 * s]], 1, { color: '#6b4a2e', width: 5 }); }
      if (p.point) { const a = seg(t, p.point[2], p.point[2] + 0.5); L.arrow(c, [[x + d * 120 * s, y - 230 * s], [L.lerp(x + d * 120 * s, p.point[0], a), L.lerp(y - 230 * s, p.point[1], a)]], a, { color: 'rgba(237,231,220,0.7)', width: 7 }); }
    });
    // ---- shells and bursts
    (g.shells || []).forEach(sh => { const u = L.lin(t, sh.t0, sh.t1); if (t > sh.t0 && u < 1) { const x = L.lerp(sh.from[0], sh.to[0], u), y = L.lerp(sh.from[1], sh.to[1], u) - Math.sin(u * Math.PI) * (sh.arc ?? 200); L.dot(c, x, y, 11, '#1d1a17'); L.circle(c, x, y, 17, { stroke: 'rgba(255,190,90,0.6)', width: 2 }); } });
    (g.bursts || []).forEach(b => { K.burst(c, L, b.x, b.y, t, b.t, b.s || 1.6); if (t > b.t && t < b.t + 0.15) { c.fillStyle = `rgba(255,220,170,${0.3 * (1 - (t - b.t) / 0.15)})`; c.fillRect(-200, -200, 2400, 1500); } });
    if (g.fog) K.fog(c, L, t, g.fog);
    if (g.rain || S === 'rain') for (let i = 0; i < 150; i++) { const x = (L.rnd(i, 1) * 2100 + t * 120) % 2100 - 90, y = (L.rnd(i, 2) * 1100 + t * 900) % 1100 - 40; L.line(c, [[x, y], [x - 8, y + 34]], 1, { color: 'rgba(200,215,230,0.35)', width: 2 }); }
    c.restore();
    if (g.tag) L.tag(c, g.tag[0], 120, 150, t, g.tag[2] ?? 0.5, { size: 34, accent: g.tag[3] || C.red, sub: g.tag[1] });
    if (g.title) L.text(c, g.title[0], 960, g.title[3] || 260, { size: 54, align: 'center', color: g.title[2] || C.redhot, alpha: seg(t, g.title[1], g.title[1] + 0.5), shadow: true });
  },
  // ---- real photos inside motion graphics (film 6): SCENE.images = {key: url}; engine.html preloads them into IMG
  photo(c, L, key, x, y, w, h, o = {}) {  // cover-crop into a rect; o.zoom (Ken Burns scale), o.fx/o.fy focus 0..1, o.grade (false = natural), o.frame, o.alpha, o.rot
    const im = IMG[key]; if (!im) return;
    const z = o.zoom || 1, r = Math.max(w / im.width, h / im.height) * z, sw = w / r, sh = h / r;
    const sx = Math.max(0, Math.min(im.width - sw, (o.fx ?? 0.5) * im.width - sw / 2)), sy = Math.max(0, Math.min(im.height - sh, (o.fy ?? 0.5) * im.height - sh / 2));
    c.save(); c.globalAlpha *= o.alpha ?? 1; c.translate(x + w / 2, y + h / 2); if (o.rot) c.rotate(o.rot); if (o.scale) c.scale(o.scale, o.scale);
    if (o.frame) { c.shadowColor = 'rgba(0,0,0,0.7)'; c.shadowBlur = 40; c.fillStyle = '#ece6d8'; c.fillRect(-w / 2 - 12, -h / 2 - 12, w + 24, h + 24); c.shadowBlur = 0; }
    if (o.grade !== false) c.filter = o.filter || 'sepia(0.55) contrast(1.1) brightness(0.9)';
    c.drawImage(im, sx, sy, sw, sh, -w / 2, -h / 2, w, h); c.filter = 'none'; c.restore();
  },
  flashAt(c, t, t0, d = 0.18, a = 0.6) { if (t > t0 && t < t0 + d) { c.fillStyle = `rgba(255,240,220,${a * (1 - (t - t0) / d)})`; c.fillRect(-200, -200, 2400, 1500); } },
  streaks(c, L, t, t0, t1, o = {}) {  // speed lines for a whoosh between beats
    const u = L.lin(t, t0, t1); if (u <= 0 || u >= 1) return; const a = Math.sin(u * Math.PI);
    for (let i = 0; i < 26; i++) { const y = L.rnd(i, 4) * 1080, x = ((L.rnd(i, 5) * 2600 + u * 3600 * (o.dir || 1)) % 2600) - 300; L.line(c, [[x, y], [x - (o.dir || 1) * (200 + L.rnd(i, 6) * 400), y]], 1, { color: `rgba(237,231,220,${0.5 * a})`, width: 2 + L.rnd(i, 7) * 3 }); }
  },
  sweep(c, L, x, y, w, h, t, t0, d = 0.9) {  // light sweep across a framed photo
    const u = L.lin(t, t0, t0 + d); if (u <= 0 || u >= 1) return; const sx = x - w * 0.4 + u * w * 1.8;
    c.save(); c.beginPath(); c.rect(x, y, w, h); c.clip(); const g = c.createLinearGradient(sx - 120, 0, sx + 120, 0);
    g.addColorStop(0, 'rgba(255,245,225,0)'); g.addColorStop(0.5, 'rgba(255,245,225,0.35)'); g.addColorStop(1, 'rgba(255,245,225,0)'); c.fillStyle = g; c.fillRect(x, y, w, h); c.restore();
  },
  stamp(c, L, text, x, y, t, t0, o = {}) {  // red rubber stamp that slams in with a small shake
    const a = L.seg(t, t0, t0 + 0.12); if (a <= 0) return; const s = 1.6 - 0.6 * L.easeOut(L.lin(t, t0, t0 + 0.2));
    c.save(); c.translate(x, y); c.rotate(o.rot ?? -0.08); c.scale(s, s); c.globalAlpha *= a; const fs = o.size || 96;
    L.text(c, text, 0, fs * 0.36, { size: fs, align: 'center', color: o.color || '#d23a2c' }); const w = (o.w || text.length * fs * 0.52) / 2;
    c.strokeStyle = o.color || '#d23a2c'; c.lineWidth = 8; c.strokeRect(-w - 30, -fs * 0.62, 2 * w + 60, fs * 1.3); c.restore();
  },
  ground(c, y, col = '#2a241d') { c.fillStyle = col; c.fillRect(0, y, 1920, 1080 - y); },
};

// ---- WWII aircraft (film 90, P-63 Kingcobra): side and top silhouettes in 1000-unit hull coords, nose to the right.
const A = {
  // side view. o.kind 'p63' (mid-engine, nose cannon, tricycle gear) | 'tail' (nose engine, tailwheel: Bf 109 / Fw 190 / Ki-43) | 'jet' (MiG-15 style swept tail)
  side(c, x, y, len, o = {}) {
    const k = o.kind || 'p63', s = len / 1000;
    c.save(); c.translate(x, y); c.scale((o.dir || 1) * s, s); if (o.rot) c.rotate(o.rot); c.globalAlpha *= o.alpha ?? 1;
    const g = c.createLinearGradient(0, -130, 0, 80); g.addColorStop(0, o.top || '#8b8f86'); g.addColorStop(1, o.col || '#3c4038');
    c.fillStyle = o.fill || g; if (o.glow) { c.shadowColor = o.glowColor || 'rgba(237,231,220,0.6)'; c.shadowBlur = o.glow; }
    c.beginPath();
    if (k === 'jet') {
      c.moveTo(500, 0); c.lineTo(470, -38); c.bezierCurveTo(380, -62, 250, -66, 120, -64); c.lineTo(-380, -40); c.lineTo(-500, -18); c.lineTo(-500, 18);
      c.lineTo(-380, 40); c.bezierCurveTo(100, 66, 380, 60, 470, 38); c.closePath();
      c.moveTo(-250, -42); c.lineTo(-430, -250); c.lineTo(-510, -250); c.lineTo(-470, -30); c.closePath();
      c.moveTo(-440, -240); c.lineTo(-560, -240); c.lineTo(-560, -225); c.lineTo(-440, -222); c.closePath();
    } else {
      c.moveTo(505, 0); c.bezierCurveTo(500, -30, 475, -44, 440, -48); c.bezierCurveTo(330, -58, 230, -62, 170, -62);
      c.lineTo(-420, -42); c.lineTo(-500, -30); c.lineTo(-505, 10); c.lineTo(-420, 26); c.bezierCurveTo(-200, 62, 150, 72, 380, 56);
      c.bezierCurveTo(440, 50, 480, 36, 505, 0); c.closePath();
      c.moveTo(-330, -48); c.bezierCurveTo(-390, -120, -430, -215, -455, -232); c.lineTo(-500, -228); c.lineTo(-505, -36); c.closePath();  // fin
      if (k === 'p63') { c.moveTo(-10, -62); c.lineTo(-30, -84); c.lineTo(-110, -84); c.lineTo(-150, -56); c.closePath(); }  // carburettor scoop behind the cockpit
    }
    c.fill(); c.shadowBlur = 0;
    // canopy
    c.fillStyle = o.glass || 'rgba(170,200,215,0.75)'; c.beginPath();
    if (k === 'jet') { c.moveTo(330, -62); c.bezierCurveTo(300, -118, 210, -122, 170, -66); c.closePath(); }
    else if (k === 'p63') { c.moveTo(170, -62); c.bezierCurveTo(150, -118, 60, -124, 10, -64); c.closePath(); }
    else { c.moveTo(40, -60); c.bezierCurveTo(20, -112, -60, -116, -110, -56); c.closePath(); }
    c.fill();
    // wing (seen edge-on) and tailplane
    c.fillStyle = o.wing || 'rgba(30,32,28,0.9)';
    c.beginPath(); c.ellipse(k === 'tail' ? 160 : 70, 42, 150, 13, 0, 0, Math.PI * 2); c.fill();
    c.fillRect(-520, -8, 120, 12);
    if (o.cannon !== false && k === 'p63') { c.fillStyle = '#1c1d1a'; c.fillRect(495, -7, 70, 14); }  // 37 mm barrel through the hub
    // propeller disc
    if (k !== 'jet') { c.strokeStyle = 'rgba(237,231,220,0.35)'; c.lineWidth = 6 / s; c.beginPath(); c.moveTo(512, -150); c.lineTo(512, 150); c.stroke(); }
    // gear
    if (o.gear !== false) {
      c.strokeStyle = '#22231f'; c.fillStyle = '#151513'; c.lineWidth = 14;
      const wheel = (wx, wy, r) => { c.beginPath(); c.moveTo(wx, 50); c.lineTo(wx, wy - r); c.stroke(); c.beginPath(); c.arc(wx, wy, r, 0, 7); c.fill(); };
      if (k === 'p63' || k === 'jet') { wheel(360, 138, 28); wheel(40, 146, 34); }
      else { wheel(230, 146, 34); c.beginPath(); c.moveTo(-420, 20); c.lineTo(-440, 60); c.stroke(); c.beginPath(); c.arc(-440, 70, 16, 0, 7); c.fill(); }
    }
    if (o.star) {  // red star on the fin
      c.fillStyle = '#c8372d'; c.beginPath();
      for (let i = 0; i < 10; i++) { const r = i % 2 ? 22 : 54, a = -Math.PI / 2 + i * Math.PI / 5; c.lineTo(-440 + Math.cos(a) * r, -130 + Math.sin(a) * r); }
      c.closePath(); c.fill(); c.strokeStyle = '#ede7dc'; c.lineWidth = 4; c.stroke();
    }
    if (o.rim) { c.strokeStyle = o.rim; c.lineWidth = (o.rimW || 2) / s; }
    c.restore();
  },
  // P-63 internal layout for cutaways, in the same coords as A.side (call inside your own translate/scale)
  P63: { engine: [-230, -42, 200, 84], driveshaft: [[-30, 8], [440, 8]], gearbox: [420, -18, 40, 36], cockpit: [20, -60, 150, 110], cannon: [380, -10, 190, 20], ammo: [300, -40, 60, 40] },
  // top view, nose to angle (rad); span ≈ 1.17 × length
  top(c, x, y, len, o = {}) {
    const s = len / 1000; c.save(); c.translate(x, y); c.rotate(o.angle || 0); c.scale(s, s); c.globalAlpha *= o.alpha ?? 1;
    c.fillStyle = o.color || '#9a9e94'; if (o.glow) { c.shadowColor = o.glowColor || c.fillStyle; c.shadowBlur = o.glow; }
    c.beginPath(); c.ellipse(0, 0, 500, 55, 0, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.moveTo(150, -40); c.lineTo(80, -585); c.lineTo(-10, -585); c.lineTo(-60, -40); c.lineTo(-60, 40); c.lineTo(-10, 585); c.lineTo(80, 585); c.lineTo(150, 40); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(-400, -30); c.lineTo(-440, -210); c.lineTo(-500, -210); c.lineTo(-500, 210); c.lineTo(-440, 210); c.lineTo(-400, 30); c.closePath(); c.fill();
    if (o.star) { c.fillStyle = '#c8372d'; [-1, 1].forEach(sd => { c.beginPath(); for (let i = 0; i < 10; i++) { const r = i % 2 ? 26 : 62, a = -Math.PI / 2 + i * Math.PI / 5; c.lineTo(30 + Math.cos(a) * r, sd * 400 + Math.sin(a) * r); } c.closePath(); c.fill(); }); }
    c.restore();
  },
};
Object.assign(A, {
  // dusk sky gradient with slow drifting cloud banks; o.horizon y of the ground line (none if 0)
  sky(c, L, t, o = {}) {
    const g = c.createLinearGradient(0, 0, 0, 1080); g.addColorStop(0, o.topCol || '#1a2230'); g.addColorStop(1, o.botCol || '#4a4a48');
    c.fillStyle = g; c.fillRect(0, 0, 1920, 1080);
    for (let i = 0; i < (o.n ?? 9); i++) {
      const w = 260 + L.rnd(i, 1) * 420, y = 80 + L.rnd(i, 2) * 820, x = ((L.rnd(i, 3) * 2600 - t * (12 + 18 * L.rnd(i, 4)) * (o.speed ?? 1)) % 2600 + 2600) % 2600 - 340;
      const gr = c.createRadialGradient(x, y, 0, x, y, w); gr.addColorStop(0, `rgba(210,205,195,${0.10 + 0.08 * L.rnd(i, 5)})`); gr.addColorStop(1, 'rgba(210,205,195,0)');
      c.save(); c.translate(x, y); c.scale(1, 0.28); c.translate(-x, -y); c.fillStyle = gr; c.fillRect(x - w, y - w, 2 * w, 2 * w); c.restore();
    }
    if (o.horizon) { const gg = c.createLinearGradient(0, o.horizon, 0, 1080); gg.addColorStop(0, o.groundTop || '#3a3528'); gg.addColorStop(1, o.groundBot || '#1c1a14'); c.fillStyle = gg; c.fillRect(0, o.horizon, 1920, 1080 - o.horizon); }
  },
  // short bright tracer streak from (x0,y0) toward (x1,y1); u 0..1 position along the line
  tracer(c, x0, y0, x1, y1, u, col = '255,200,90', len = 0.08) {
    if (u < 0 || u > 1) return; const a = Math.max(0, u - len);
    c.save(); c.strokeStyle = `rgba(${col},0.95)`; c.lineWidth = 5; c.shadowColor = `rgb(${col})`; c.shadowBlur = 16; c.lineCap = 'round';
    c.beginPath(); c.moveTo(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a); c.lineTo(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u); c.stroke(); c.restore();
  },
});
