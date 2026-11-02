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
  doll(c, L, x, y, h, t, o = {}) {
    const C = { pru: ['#141a2b', '#c0282d', '#ece6d8'], fra: ['#2f5fc4', '#f4f0e6', '#ece6d8'], brit: ['#b52a2c', '#ece6d8', '#22305a'], civ: ['#6a5238', '#d9cfb8', '#3a2e22'], rus: ['#34552f', '#c0282d', '#ece6d8'] }[o.side || 'pru'];
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
    } else if (o.side === 'pru') {
      c.fillStyle = '#e8e2d2'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(0, -184 + i * 28, 5, 0, 7); c.fill(); }
      c.fillStyle = C[1]; c.fillRect(-160, -60, 320, 0);
    } else {
      c.beginPath(); c.moveTo(-40, -196); c.lineTo(0, -70); c.lineTo(40, -196); c.lineTo(22, -196); c.lineTo(0, -120); c.lineTo(-22, -196); c.fill();  // facings
      c.fillStyle = '#e0bd5a'; for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(-12, -170 + i * 34, 5, 0, 7); c.arc(12, -170 + i * 34, 5, 0, 7); c.fill(); }
    }
    if (o.belts !== false && !o.epaulettes) { c.strokeStyle = C[2]; c.lineWidth = 12; c.beginPath(); c.moveTo(-90, -190); c.lineTo(90, -20); c.moveTo(90, -190); c.lineTo(-90, -20); c.stroke(); }
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
    if (o.musket) { c.save(); c.translate(120, -40); c.rotate(-0.18); c.fillStyle = '#6b4a2e'; c.fillRect(-8, -230, 16, 260); c.fillStyle = '#9a978f'; c.fillRect(-4, -330, 8, 110); if (o.bayonet !== false) { c.fillStyle = '#d4d8dc'; c.fillRect(-3, -400, 6, 72); } c.restore(); }
    if (o.sabre) { c.save(); c.translate(115, -110); c.rotate(o.raise ? -2.2 : -0.35); c.fillStyle = '#d4d8dc'; c.fillRect(0, -4, 200, 8); c.fillStyle = '#e0bd5a'; c.fillRect(-16, -11, 20, 22); c.restore(); }
    c.restore();
  },
  ground(c, y, col = '#2a241d') { c.fillStyle = col; c.fillRect(0, y, 1920, 1080 - y); },
};
