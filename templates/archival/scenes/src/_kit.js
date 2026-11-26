// Shared drawing kit for this film's scenes (prepended to every scene by scenes/src/build.py). Template: templates/archival/scenes/src/_kit.js.
// Smoke, flashes, muskets, cannon, riders (black-powder era: add the film's own era helpers here) plus K.doll: egg-shaped period
// characters for the key human moments no real picture shows, target 20-30 % of a film (docs/WORKFLOW.md stage 6, scripts/dollcheck.py).
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
  // Egg-shaped period character ("doll"), facing the viewer. Film 75 style; the only character style. Key human moments with no real picture.
  // One egg: face in the upper part, coat below (like the reference Short). (x, y) = feet centre; h = height without hat.
  // o.side: 'pru' (Prussian dark blue, red facings), 'fra' (French blue, white facings, white cross-belts), 'brit' (red coat), 'civ' (Landwehr brown), 'rus'
  // o.hat: 'bicorne' | 'shako' | 'bearskin' | 'cap' (Prussian/Landwehr Schirmmütze) | 'hussar' (busby) | 'none'
  // o.face: 'calm' | 'grim' | 'shock' | 'dead' | 'shout' | 'smile'; o.hair: 'grey' | 'white' | 'dark' | 'bald'
  // o.musket, o.sabre (o.raise), o.epaulettes (officer), o.moustache, o.bob (idle-bounce phase), o.tilt (radians, e.g. falling)
  // Vietnam 1860s: side 'dnam' (Nguyễn soldier, hat 'nondau'), 'quan' (mandarin, hat 'canhchuon'), 'dan' (commoner, hat 'khan'); 'mar' = French marine (hat 'kepi', o.cover);
  // o.beard (long grey scholar's beard), o.spear (giáo)
  // 20th century (2026-11-14, same egg as film 75; never a second character style):
  //   side 'wehr' (feldgrau), 'sov' (Red Army gymnastyorka), 'us' (olive drab), 'tommy' (British khaki), 'jap' (IJA khaki),
  //   'navy' (dark blue, brass buttons), 'suit' (politician/civilian: dark suit, shirt, tie), 'work' (worker's jacket)
  //   hats 'stahlhelm' | 'pilotka' | 'ushanka' | 'm1' | 'brodie' | 'jpcap' (o.flaps) | 'peaked' (officer, colour by side) | 'fedora' | 'flatcap'
  //   since 2026-11-14 (space race film): 'usaf' (blue service dress, ribbons; hat 'peaked'), 'astro' (US white pressure suit, flag patch),
  //   'cosmo' (Soviet white suit, red СССР), 'lab' (engineer's white coat, tie); hat 'space' (clear helmet bubble, neck ring)
  //   since 2026-11-14 (combat scenes): 'union' (US Civil War Union: dark blue sack coat, sky-blue trousers, four brass buttons, black sling,
  //   oval US belt plate; hat 'kepi' turns into the dark blue forage cap with a brass bugle), 'confed' (Confederate cadet-grey shell jacket,
  //   o.butternut for the brown-yellow homespun, light-blue collar trim, seven brass buttons, white haversack strap, CS plate; hat 'slouch'
  //   = wide soft felt hat, o.capCol), 'iraq' (Iraqi army 1991 olive field tunic; hat 'beret', black by default, o.capCol for the
  //   Republican Guard red). since 2026-11-16 (Stalingrad film): 'rum' (Romanian army 1942 khaki-brown tunic, blue-yellow-red breast patch;
  //   hat 'rumhelm' = M1939 Dutch-pattern helmet with an even all-round brim, or 'peaked' for officers). Sheet: projects/<film-90+>/qa/w/doll-costumes.jpg
  //   since 2026-11-16 (Nagato film): 'ijn' (IJN officer, dark navy 詰襟 standing collar closed at the throat, black braid edge, one row of
  //   5 gold buttons; o.whites = summer whites 第二種軍装 with shoulder boards; o.stripes = number of gold sleeve stripes; hat 'peaked' =
  //   dark cap, black band, gold anchor in cherry-blossom wreath, white cover with o.whites), 'ijnrate' (IJN 水兵: navy jumper, square
  //   sailor collar with white stripes, white neckerchief; hat 'jpsailor' = brimless round cap, black ribbon with gold dashes, two tails),
  //   'usn' (US Navy enlisted 1940s: chambray shirt + dark dungaree trousers, o.whites = white jumper with navy square collar and black
  //   neckerchief; hat 'dixie' = white dixie cup). US Navy officers: side 'navy' + 'peaked' (white top, gold eagle-and-anchors badge, o.whites too).
  //   since 2026-11-16 (Nagato film): 'kmrate' (Kaiserliche Marine sailor 1914-1919: dark navy jumper, square sailor collar with THREE
  //   white stripes, black neckerchief knotted with a white bow; hat 'kmsailor' = wide flat Tellermütze, black ribbon band with small gold
  //   dashes (no text), two long black ribbon tails hanging down at the back). Reads apart from 'ijnrate' (two stripes, white
  //   neckerchief, smaller 'jpsailor' cap with short tails).
  //   since 2026-11-17 (Berlin 1945 film): 'ss' (Waffen-SS: field-grey tunic under a pea-dot camouflage smock, black collar patch),
//   'frau' (civilian woman 1945: plain wool coat, three big buttons; hat 'kopftuch' = headscarf knotted under the chin, o.capCol),
//   hat 'tankist' (Soviet padded leather tank helmet: three ridges, ear flaps), o.armband = 'vs' (Volkssturm yellow band with dark
//   lettering dashes) | 'hj' (red-white-red band, no emblem) | 'white' (surrender/parlementaire) | any CSS colour, on the left upper coat.
//   o.rifle (bolt-action), o.binos (binoculars on the chest), o.helmCol (helmet paint). A film needing a costume not listed here
//   since 2026-11-18 (MiG-25 film): 'flight' (jet pilot one-piece coverall + harness; o.air = 'usaf' sage + name tape/wings, 'pvo' grey-olive
//   VKK suit with lacing tubes + red star, 'iaf' olive + white/blue star patch, 'irq' olive + red-white-black patch, 'jasdf' + red disc),
//   hat 'flighthelmet' (hard shell over the ears, visor housing; o.visor dark visor down, o.mask oxygen mask + hose, o.helmCol).
  //   since 2026-11-24 (Meuse-Argonne film): 'kaiser' (German Army 1914-18 feldgrau field tunic, plain stand collar with thin red piping,
  //   no eagle or Litzen; hat 'm1916' = WWI Stahlhelm with deep flared skirt and side lugs, 'peaked' for officers), 'poilu' (French 1915-18
  //   horizon-blue greatcoat, two button rows, brown belt + pouches; hat 'adrian' = Adrian helmet with crest). AEF doughboys: 'us' + 'brodie'.
  //   since 2026-11-24 (Königgrätz 1866 film): 'aut' (Austrian 1866 white Waffenrock, o.facing = regimental colour, one brass row, black belt;
  //   hat 'autshako' = low black Tschako with brass double-eagle plate + rosette; generals hat 'federhut' = bicorne with green plume),
  //   'sax' (Saxon light-blue tunic, same cut); Prussians 1866: 'pru' + hat 'pickel' (Pickelhaube: black dome, brass spike, eagle plate).
  //   since 2026-11-25 (20 July 1944 film): o.eyepatch (true = doll's left eye), o.emptySleeve (pinned right sleeve), o.general (Wehrmacht
  //   general: red/gold collar patches, gold cap cord), o.glasses, o.toothbrush; sides 'sd' (SS/SD/Gestapo officer, grey tunic, black patches,
  //   no runes), 'nsdap' (plain double-breasted grey-brown jacket, tie; Hitler = nsdap + hat 'none' + toothbrush), 'roman' (toga; hat
  //   'laurel'), 'robe' (People's Court judge, hat 'robecap'), 'guardia' (Guardia Civil 1981, hat 'tricornio').
  //   since 2026-11-25 (Pershing II film): 'bdu' (US Army 1981-2005 woodland camouflage; hat 'pasgt' = Kevlar helmet with camouflage cover and
  //   swept ear guards, 'bducap' = woodland patrol cap), 'polizei' (West German police 1980s: moss-green jacket, mustard shirt; hat 'polcap').
  //   adds it in THIS function (templates/archival kit), drawn the same way, so every later film has it.
  // Outdoor and night pictures in the paper look: fade the frame's edge into the paper so the film stays on its ground colour (lookcheck).
  // Call it last in draw(); keep light text inside x 140-1780, y 150-930.
  paperEdge(c, L) {
    const [r, g, b] = L.C.bg.match(/[0-9a-f]{2}/gi).map(x => parseInt(x, 16)), W = 1920, H = 1080, col = a => `rgba(${r},${g},${b},${a})`;
    [[0, 0, 125, 0, 0, 0, 125, H, 0.5], [W, 0, W - 125, 0, W - 125, 0, 125, H, 0.5], [0, 0, 0, 140, 0, 0, W, 140, 0.55], [0, H, 0, H - 140, 0, H - 140, W, 140, 0.55]].forEach(([x0, y0, x1, y1, x, y, w, h, k]) => {
      const gr = c.createLinearGradient(x0, y0, x1, y1); gr.addColorStop(0, col(1)); gr.addColorStop(k, col(1)); gr.addColorStop(1, col(0)); c.fillStyle = gr; c.fillRect(x, y, w, h); });
  },
  doll(c, L, x, y, h, t, o = {}) {
    const C = ({ pru: ['#141a2b', '#c0282d', '#ece6d8'], aut: ['#ece8dc', o.facing || '#8a1f2a', '#141210'], sax: ['#6b8fbf', '#1c2440', '#141210'], fra: ['#2f5fc4', '#f4f0e6', '#ece6d8'], brit: ['#b52a2c', '#ece6d8', '#22305a'], civ: ['#6a5238', '#d9cfb8', '#3a2e22'], rus: ['#34552f', '#c0282d', '#ece6d8'], dnam: ['#7a1f1a', '#1a1612', '#c9a24a'], quan: ['#1f2a5a', '#c9a24a', '#c9a24a'], dan: ['#3a3128', '#2a221a', '#5a4a38'], mar: ['#1c2440', '#c0282d', '#ece6d8'],
      lycourt: ['#704638', '#d3b89a', '#987755'], trancourt: ['#34465a', '#abbaaf', '#6d5d55'],
      lyking: ['#c59632', '#7a1f1a', '#e0bd5a'], lymonk: ['#7b6652', '#cfbc9c', '#5a4432'],
      lystaff: ['#595849', '#b8a47c', '#8f7c5b'], lysoldier: ['#4d4236', '#2b241d', '#8f7c5b'],
      transoldier: ['#2f3d4c', '#1c242e', '#8f7c5b'], mongol: ['#52483c', '#8b7a64', '#2a221c'],
      wehr: ['#5b6150', '#3d4a3a', '#1e1c18'], sov: ['#7c7550', '#6e6844', '#4a3424'], us: ['#6b6440', '#5c5636', '#4a4630'], tommy: ['#7a6a48', '#6a5c3e', '#5a4a30'], jap: ['#8a7a4a', '#7a6a40', '#5a4228'],
      navy: ['#1c2440', '#141a30', '#d8b450'], usaf: ['#3a4b6e', '#2c3a58', '#1a1c22'], astro: ['#e8e6e0', '#c9c6be', '#8a8a90'], cosmo: ['#e4e0d6', '#c0282d', '#8a8a90'], lab: ['#ecebe6', '#d8d6cf', '#3a3a40'], suit: ['#23262c', '#1a1c22', '#7a1f1a'], work: ['#4a4a52', '#3a3a40', '#2a2420'],
      union: ['#232c4a', '#1c2440', '#d8b450'], confed: ['#7d796e', '#6a665c', '#d8b450'], iraq: ['#5a5c3c', '#4c4e32', '#3a3424'], rum: ['#6e6244', '#5e5438', '#3a2c1e'],
      ss: ['#5a5f4c', '#16120f', '#1e1c18'], frau: ['#4e463e', '#3e3832', '#2a2420'], ijn: ['#151a2a', '#0e1220', '#d8b450'], ijnrate: ['#1a2034', '#141a30', '#ece8e0'], kmrate: ['#161c2e', '#10152a', '#ece8e0'], usn: ['#8fa6c4', '#8296b2', '#232a3e'], flight: ['#5f6a4e', '#535d44', '#2a2a24'], kaiser: ['#6a6d58', '#525642', '#1e1c18'], sd: ['#666a66', '#16120f', '#16120f'], nsdap: ['#75705f', '#5e5a4c', '#1e1c18'], roman: ['#ece6d8', '#7a2a4a', '#7a2a4a'], robe: ['#9a2226', '#6a1418', '#6a1418'], guardia: ['#5a6548', '#4a543a', '#1e1c18'], bdu: ['#59603f', '#4a5236', '#26241a'], polizei: ['#46563f', '#3a4835', '#1e1c18'], poilu: ['#8296ae', '#6c7f99', '#3a3428'] }[o.side || 'pru']).slice();
    const MOD = ['wehr', 'sov', 'us', 'tommy', 'jap', 'iraq', 'rum', 'ss', 'kaiser', 'sd', 'guardia', 'bdu', 'polizei'].includes(o.side), NEW = MOD || ['nsdap', 'roman', 'robe', 'frau', 'navy', 'suit', 'work', 'usaf', 'astro', 'cosmo', 'lab', 'union', 'confed', 'ijn', 'ijnrate', 'kmrate', 'usn', 'flight', 'poilu'].includes(o.side);
    if (o.side === 'flight' && !o.coat) C[0] = { usaf: '#5f6a4e', pvo: '#77745e', iaf: '#6a6c4a', irq: '#646a4c', jasdf: '#5a6450' }[o.air || 'usaf'];
    if (o.whites && (o.side === 'ijn' || o.side === 'usn')) { C[0] = '#eeebe2'; C[1] = '#e2ded4'; }
    if (o.side === 'confed' && o.butternut) C[0] = '#8c7148';
    const star = (sx, sy, r, col) => { c.fillStyle = col; c.beginPath(); for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rr = k % 2 ? r * 0.42 : r; c.lineTo(sx + Math.cos(a) * rr, sy + Math.sin(a) * rr); } c.closePath(); c.fill(); };
    if (o.coat) C[0] = o.coat;  // e.g. the emperor's yellow robe
    const bob = Math.sin((t || 0) * 3 + (o.bob || 0)) * 3;
    c.save(); c.translate(x, y + bob); c.rotate(o.tilt || 0); c.scale((o.dir || 1) * h / 400, h / 400);
    c.fillStyle = 'rgba(0,0,0,0.3)'; c.beginPath(); c.ellipse(0, 4, 120, 18, 0, 0, 7); c.fill();  // ground shadow
    const egg = () => { c.beginPath(); c.moveTo(-118, -8); c.bezierCurveTo(-140, -200, -100, -400, 0, -400); c.bezierCurveTo(100, -400, 140, -200, 118, -8); c.quadraticCurveTo(0, 12, -118, -8); };
    // skin fills the whole egg, coat is clipped to the lower part
    c.save(); egg(); c.clip();
    c.fillStyle = o.skin || '#f2d9c2'; c.fillRect(-160, -420, 320, 440);
    const g = c.createLinearGradient(-130, 0, 130, 0); g.addColorStop(0, C[0]); g.addColorStop(0.6, C[0]); g.addColorStop(1, (o.whites && (o.side === 'ijn' || o.side === 'usn')) || o.side === 'aut' ? '#a29e94' : '#0b0e18');
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
      if (o.side === 'dnam') { c.fillStyle = '#c9a24a'; c.beginPath(); c.arc(0, -140, 26, 0, 7); c.fill(); c.fillStyle = '#7a1f1a'; c.font = 'bold 30px serif'; c.textAlign = 'center'; c.fillText(String.fromCharCode(0x5175), 0, -129); }
      c.fillStyle = C[2]; c.fillRect(-160, -64, 320, 14);
    } else if (['lycourt', 'trancourt', 'lyking', 'lymonk', 'lystaff'].includes(o.side)) {  // Plain cross-collared robes, early Đại Việt (illustrative)
      c.strokeStyle = C[1]; c.lineWidth = 11;
      c.beginPath(); c.moveTo(-72, -205); c.quadraticCurveTo(-22, -168, 80, -134); c.stroke();
      c.beginPath(); c.moveTo(66, -205); c.quadraticCurveTo(52, -182, 10, -163); c.stroke();
      if (o.side === 'lymonk') {  // monastic kasaya sash draped across left shoulder + prayer beads
        c.fillStyle = C[2]; c.beginPath(); c.moveTo(-120, -205); c.lineTo(-42, -205); c.lineTo(135, -35); c.lineTo(125, 18); c.lineTo(50, 18); c.closePath(); c.fill();
        c.strokeStyle = '#3b2b1e'; c.lineWidth = 3; c.stroke();
        c.fillStyle = '#3b2b1e'; for (let k = -3; k <= 3; k++) { c.beginPath(); c.arc(k * 13, -182 + Math.abs(k) * 5, 4.5, 0, 7); c.fill(); }
      } else if (o.side === 'lyking') {  // imperial belt with jade/gold clasp
        c.fillStyle = '#7a1f1a'; c.fillRect(-140, -70, 280, 16);
        c.fillStyle = '#e0bd5a'; c.beginPath(); c.ellipse(0, -62, 20, 13, 0, 0, 7); c.fill();
      } else {
        c.fillStyle = C[2]; c.fillRect(-140, -67, 280, 12);
      }
    } else if (o.side === 'lysoldier' || o.side === 'transoldier') {  // Lý-Trần infantry: buffalo-leather lamellar/jerkin + chest mirror + waist belt
      c.strokeStyle = C[1]; c.lineWidth = 9;
      c.beginPath(); c.moveTo(-66, -205); c.quadraticCurveTo(-18, -172, 72, -140); c.stroke();
      c.fillStyle = C[1]; c.fillRect(-76, -185, 152, 112);  // leather cuirass
      c.strokeStyle = 'rgba(210,195,165,0.35)'; c.lineWidth = 2.5;
      for (let ry = -162; ry <= -94; ry += 22) { c.beginPath(); c.moveTo(-72, ry); c.lineTo(72, ry); c.stroke(); }
      c.fillStyle = '#b8a06a'; c.beginPath(); c.arc(0, -138, 18, 0, 7); c.fill();  // bronze chest disc (hộ tâm kính)
      c.fillStyle = C[2]; c.fillRect(-140, -72, 280, 14);
    } else if (o.side === 'mongol') {  // Mongol warrior: fur-trimmed steppe deel coat + waist sash
      c.fillStyle = C[1]; c.beginPath(); c.moveTo(-70, -205); c.lineTo(66, -130); c.lineTo(66, 20); c.lineTo(44, 20); c.lineTo(44, -120); c.lineTo(-92, -205); c.closePath(); c.fill();
      c.fillStyle = C[2]; c.fillRect(-140, -74, 280, 16); c.fillStyle = '#c9a24a'; c.fillRect(-16, -76, 32, 20);
    } else if (o.side === 'quan') {  // áo thụng with a square rank badge (bổ tử)
      c.strokeStyle = C[1]; c.lineWidth = 8; c.beginPath(); c.moveTo(-20, -200); c.quadraticCurveTo(60, -170, 70, -80); c.stroke();
      c.fillStyle = '#c9a24a'; c.fillRect(-46, -170, 92, 84); c.fillStyle = '#1f2a5a'; c.fillRect(-36, -160, 72, 64); c.strokeStyle = '#c9a24a'; c.lineWidth = 3; c.beginPath(); c.arc(0, -128, 18, 0, 7); c.stroke();
    } else if (o.side === 'mar') {  // infanterie de marine 1860s: dark blue tunic, one brass row, red piping
      c.fillStyle = '#d8b450'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(0, -184 + i * 28, 5, 0, 7); c.fill(); }
    } else if (o.side === 'union' || o.side === 'confed') {  // Civil War: trousers below the coat, sling across the chest, brass buttons, belt plate
      const U = o.side === 'union';
      c.fillStyle = U ? '#7f97b8' : (o.butternut ? '#9a8458' : '#8a867a'); c.fillRect(-160, -50, 320, 72);  // trousers
      c.strokeStyle = 'rgba(0,0,0,0.35)'; c.lineWidth = 4; c.beginPath(); c.moveTo(0, -50); c.lineTo(0, 22); c.stroke();
      if (!U) { c.fillStyle = '#8fa6c4'; c.fillRect(-160, -212, 320, 16); }  // light-blue infantry trim on the collar
      c.strokeStyle = U ? '#141210' : '#e8e2d2'; c.lineWidth = 13; c.beginPath(); c.moveTo(-96, -196); c.lineTo(96, -64); c.stroke();  // cartridge-box sling / haversack strap
      c.fillStyle = '#d8b450'; const nb = U ? 4 : 7; for (let i = 0; i < nb; i++) { c.beginPath(); c.arc(-8, -186 + i * (U ? 30 : 16), 6, 0, 7); c.fill(); }
      c.fillStyle = '#141210'; c.fillRect(-160, -84, 320, 18); c.fillStyle = '#d8b450'; c.beginPath(); c.ellipse(0, -75, 26, 14, 0, 0, 7); c.fill();  // belt + plate
      c.fillStyle = '#141210'; c.font = 'bold 15px serif'; c.textAlign = 'center'; c.fillText(U ? 'US' : 'CS', 0, -70);
    } else if (MOD) {  // field tunic: breast pockets with flaps, one button row (sov: short placket), waist belt
      if (o.side === 'bdu') { [['#3b4a2c', 0], ['#6b5638', 3], ['#1f2018', 7]].forEach(([col, k]) => { c.fillStyle = col; for (let i = 0; i < 9; i++) { const px = -120 + (i % 3) * 92 + (Math.floor(i / 3) % 2) * 34 + k * 8, py = -180 + Math.floor(i / 3) * 62 + (i % 3) * 14 + k * 6; c.beginPath(); c.ellipse(px, py, 24 - k, 9 + (i % 3) * 3, (i + k) * 0.8, 0, 7); c.fill(); } }); }  // woodland blotches: green, brown, black
      if (o.side === 'polizei') { c.fillStyle = '#c9b582'; c.beginPath(); c.moveTo(-40, -206); c.lineTo(0, -130); c.lineTo(40, -206); c.fill(); c.fillStyle = '#2c3a2a'; c.beginPath(); c.moveTo(-8, -198); c.lineTo(8, -198); c.lineTo(10, -146); c.lineTo(0, -134); c.lineTo(-10, -146); c.fill(); }  // mustard shirt, green tie
      const btn = o.side === 'us' || o.side === 'tommy' || o.side === 'iraq' || o.side === 'rum' ? '#8a7a4a' : o.side === 'jap' ? '#c9a24a' : '#9a9a8a';
      c.fillStyle = 'rgba(0,0,0,0.18)'; [-1, 1].forEach(sd => { c.fillRect(sd * 62 - 30, -170, 60, 54); c.fillStyle = 'rgba(0,0,0,0.3)'; c.fillRect(sd * 62 - 32, -172, 64, 14); c.fillStyle = 'rgba(0,0,0,0.18)'; });
      c.fillStyle = btn; const nb = o.side === 'sov' ? 2 : 5; for (let i = 0; i < nb; i++) { c.beginPath(); c.arc(0, -186 + i * 26, 5, 0, 7); c.fill(); }
      if (o.side === 'wehr') { c.fillStyle = '#c9ccc0'; [-1, 1].forEach(sd => c.fillRect(sd * 40 - 14, -210, 28, 7)); c.fillStyle = '#b8b8a8'; c.beginPath(); c.moveTo(-40, -150); c.lineTo(-62, -160); c.lineTo(-40, -144); c.lineTo(-18, -160); c.closePath(); c.fill(); }  // collar Litzen, breast eagle
      if (o.side === 'wehr' && o.general) [-1, 1].forEach(sd => { c.fillStyle = '#b0302a'; c.fillRect(sd * 46 - 18, -214, 36, 20); c.fillStyle = '#d8b450'; c.fillRect(sd * 46 - 12, -209, 24, 4); c.fillRect(sd * 46 - 12, -202, 24, 4); });  // Wehrmacht general: red collar patches, gold embroidery
      if (o.side === 'sd') { c.fillStyle = '#16120f'; [-1, 1].forEach(sd => c.fillRect(sd * 46 - 18, -214, 36, 20)); c.fillStyle = '#c9ccc0'; [-1, 1].forEach(sd => c.fillRect(sd * 46 - 5, -207, 10, 6)); }  // SS/SD/Gestapo officer: grey tunic, black collar patches (no runes)
      if (o.side === 'sov') { c.fillStyle = '#c0282d'; [-1, 1].forEach(sd => c.fillRect(sd * 46 - 14, -212, 28, 16)); }  // collar tabs
      if (o.side === 'kaiser') { c.fillStyle = '#3e4232'; c.fillRect(-60, -214, 120, 12); c.fillStyle = '#b0302a'; c.fillRect(-60, -204, 120, 3); }  // WWI German M1915 Bluse: plain darker stand collar with thin red piping, no eagle
      if (o.side === 'jap') { c.fillStyle = '#c0282d'; [-1, 1].forEach(sd => c.fillRect(sd * 44 - 14, -212, 28, 14)); }
      if (o.side === 'ss') {  // pea-dot camouflage smock over the tunic (Erbsenmuster), black collar patch
        const dots = [['#7a6a3c', 0], ['#3e4a2c', 1], ['#8a5a32', 2], ['#2a2a1e', 3]]; dots.forEach(([col, k]) => { c.fillStyle = col; for (let i = 0; i < 26; i++) { const dx = ((i * 73 + k * 41) % 300) - 150, dy = -196 + ((i * 37 + k * 59) % 190); c.beginPath(); c.ellipse(dx, dy, 13 - k * 2, 8, (i + k) * 0.7, 0, 7); c.fill(); } });
        c.fillStyle = '#16120f'; c.fillRect(-56, -212, 30, 18); c.fillRect(26, -212, 30, 18);
      }
      if (o.side === 'rum') { [['#2a4c9a', -10], ['#e0bd5a', 0], ['#c0282d', 10]].forEach(([col, dx]) => { c.fillStyle = col; c.fillRect(-66 + dx - 5, -168, 10, 24); }); }  // Romanian blue-yellow-red patch on the left breast
      c.fillStyle = C[2]; c.fillRect(-160, -78, 320, 18); c.fillStyle = '#9a9a8a'; c.fillRect(-16, -80, 32, 22);  // belt + buckle
    } else if (o.side === 'nsdap') {  // plain double-breasted grey-brown jacket over white shirt and dark tie (no emblems)
      c.fillStyle = '#ece6d8'; c.beginPath(); c.moveTo(-36, -204); c.lineTo(0, -140); c.lineTo(36, -204); c.fill(); c.fillStyle = '#16120f'; c.beginPath(); c.moveTo(-8, -198); c.lineTo(8, -198); c.lineTo(10, -150); c.lineTo(0, -138); c.lineTo(-10, -150); c.closePath(); c.fill();
      c.strokeStyle = 'rgba(0,0,0,0.4)'; c.lineWidth = 5; c.beginPath(); c.moveTo(-44, -206); c.lineTo(-10, -120); c.lineTo(22, -20); c.moveTo(44, -206); c.lineTo(4, -124); c.stroke(); c.fillStyle = '#d8b450'; [0, 1, 2].forEach(i => { [-1, 1].forEach(sd => { c.beginPath(); c.arc(sd * 34, -110 + i * 34, 6, 0, 7); c.fill(); }); });
    } else if (o.side === 'roman') {  // white toga with a purple-red band falling over one shoulder
      c.fillStyle = '#7a2a4a'; c.beginPath(); c.moveTo(-110, -206); c.quadraticCurveTo(-10, -120, 60, 10); c.lineTo(30, 10); c.quadraticCurveTo(-40, -110, -130, -190); c.closePath(); c.fill(); c.strokeStyle = 'rgba(90,80,60,0.45)'; c.lineWidth = 4; [0, 1, 2, 3].forEach(i => { c.beginPath(); c.moveTo(90 - i * 8, -190 + i * 26); c.quadraticCurveTo(20, -120 + i * 34, -30 + i * 12, 10); c.stroke(); });
    } else if (o.side === 'robe') {  // People's Court judge: wine-red robe, broad satin facings, white cravat
      c.fillStyle = '#6a1418'; c.fillRect(-58, -206, 34, 220); c.fillRect(24, -206, 34, 220); c.fillStyle = '#ece6d8'; c.beginPath(); c.moveTo(-18, -206); c.lineTo(18, -206); c.lineTo(10, -150); c.lineTo(-10, -150); c.closePath(); c.fill();
    } else if (o.side === 'frau') {  // plain wool coat with a turned-down collar and three large buttons
      c.fillStyle = C[1]; c.beginPath(); c.moveTo(-70, -206); c.lineTo(0, -150); c.lineTo(70, -206); c.lineTo(48, -212); c.lineTo(0, -170); c.lineTo(-48, -212); c.closePath(); c.fill();
      c.fillStyle = '#1e1a16'; for (let i = 0; i < 3; i++) { c.beginPath(); c.arc(14, -140 + i * 40, 8, 0, 7); c.fill(); }
    } else if (o.side === 'poilu') {  // French 1915-18 horizon-blue capote: turned-down collar, two button rows, leather belt + brown cartridge pouches
      c.fillStyle = C[1]; c.beginPath(); c.moveTo(-64, -210); c.lineTo(0, -170); c.lineTo(64, -210); c.lineTo(44, -214); c.lineTo(0, -186); c.lineTo(-44, -214); c.closePath(); c.fill();
      c.fillStyle = '#c9b98a'; for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(-34, -156 + i * 28, 5, 0, 7); c.arc(34, -156 + i * 28, 5, 0, 7); c.fill(); }
      c.fillStyle = '#5a3e24'; c.fillRect(-160, -80, 320, 16); [-1, 1].forEach(sd => c.fillRect(sd * 70 - 22, -96, 44, 30));
    } else if (o.side === 'navy') {  // reefer jacket, double row of brass buttons
      c.fillStyle = '#ece6d8'; c.beginPath(); c.moveTo(-30, -200); c.lineTo(0, -150); c.lineTo(30, -200); c.fill(); c.fillStyle = '#16120f'; c.fillRect(-6, -196, 12, 40);
      c.fillStyle = C[2]; for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(-36, -150 + i * 30, 6, 0, 7); c.arc(36, -150 + i * 30, 6, 0, 7); c.fill(); }
    } else if (o.side === 'ijn') {  // IJN officer 第一種軍装 (dark navy 詰襟, closed at the throat, black braid edging, one row of 5 gold buttons) / o.whites 第二種軍装
      const W = o.whites;
      c.strokeStyle = W ? 'rgba(0,0,0,0.18)' : '#06080e'; c.lineWidth = W ? 3 : 7; c.beginPath(); c.moveTo(0, -196); c.lineTo(0, 20); c.stroke();  // front opening (braid edge)
      if (!W) { c.strokeStyle = '#06080e'; c.lineWidth = 5; c.beginPath(); c.moveTo(-160, -194); c.quadraticCurveTo(0, -186, 160, -194); c.stroke(); }  // braid under the standing collar
      c.fillStyle = '#d8b450'; for (let i = 0; i < 5; i++) { c.beginPath(); c.arc(0, -178 + i * 34, 6, 0, 7); c.fill(); }
      if (W) { c.fillStyle = '#16120f'; [-1, 1].forEach(sd => { c.fillRect(sd * 98 - 22, -206, 44, 13); c.fillStyle = '#d8b450'; c.fillRect(sd * 98 - 22, -202, 44, 3); c.beginPath(); c.arc(sd * 98 + sd * 12, -199, 3, 0, 7); c.fill(); c.fillStyle = '#16120f'; }); }  // shoulder boards
      if (o.stripes && !W) { c.fillStyle = '#d8b450'; [-1, 1].forEach(sd => { for (let k = 0; k < o.stripes; k++) c.fillRect(sd * 128 - 20, -58 + k * 11, 40, 5); }); }  // sleeve rank stripes
    } else if (o.side === 'ijnrate' || o.side === 'usn') {  // sailors: square collar with stripes + neckerchief (IJN 水兵 / USN whites), or USN chambray shirt + dark trousers
      const SQ = o.side === 'ijnrate' || o.whites, colCol = o.side === 'ijnrate' ? '#141a30' : '#1c2440';
      if (SQ) {
        c.fillStyle = colCol; c.beginPath(); c.moveTo(-110, -206); c.lineTo(-56, -206); c.lineTo(0, -120); c.lineTo(56, -206); c.lineTo(110, -206); c.lineTo(110, -170); c.lineTo(0, -96); c.lineTo(-110, -170); c.closePath(); c.fill();
        if (o.side === 'ijnrate') { c.fillStyle = C[0]; c.beginPath(); c.moveTo(-40, -206); c.lineTo(0, -140); c.lineTo(40, -206); c.fill(); }  // jumper V front under the collar
        else { c.fillStyle = '#ece8e0'; c.beginPath(); c.moveTo(-40, -206); c.lineTo(0, -140); c.lineTo(40, -206); c.fill(); }
        c.strokeStyle = '#ece8e0'; c.lineWidth = 4; [7, 15].forEach(d => { c.beginPath(); c.moveTo(-112, -170 - d); c.lineTo(0, -96 - d); c.lineTo(112, -170 - d); c.stroke(); });  // collar stripes
        const nk = o.side === 'ijnrate' ? '#f4f2ec' : '#141418';  // neckerchief
        c.fillStyle = nk; c.beginPath(); c.moveTo(-26, -150); c.lineTo(26, -150); c.lineTo(10, -118); c.lineTo(-10, -118); c.closePath(); c.fill();
        c.beginPath(); c.moveTo(-10, -120); c.lineTo(-20, -70); c.lineTo(-4, -76); c.lineTo(0, -116); c.lineTo(4, -76); c.lineTo(20, -70); c.lineTo(10, -120); c.closePath(); c.fill();
      } else {  // USN dungarees: chambray work shirt (open collar, two patch pockets) over dark denim trousers
        c.fillStyle = '#16120f'; c.globalAlpha = 0.25; c.beginPath(); c.moveTo(-40, -206); c.lineTo(0, -160); c.lineTo(40, -206); c.fill(); c.globalAlpha = 1;
        c.fillStyle = '#f2d9c2'; c.beginPath(); c.moveTo(-26, -206); c.lineTo(0, -170); c.lineTo(26, -206); c.fill();  // open neck
        c.strokeStyle = 'rgba(0,0,0,0.3)'; c.lineWidth = 3; c.beginPath(); c.moveTo(0, -170); c.lineTo(0, -60); c.stroke(); [-1, 1].forEach(sd => c.strokeRect(sd * 58 - 24, -150, 48, 44));
        c.fillStyle = '#ece8e0'; for (let i = 0; i < 3; i++) { c.beginPath(); c.arc(0, -150 + i * 34, 4, 0, 7); c.fill(); }
        c.fillStyle = '#232a3e'; c.fillRect(-160, -56, 320, 80); c.fillStyle = '#141418'; c.fillRect(-160, -60, 320, 10);  // trousers + belt
      }
    } else if (o.side === 'kmrate') {  // Kaiserliche Marine Matrose: wide square collar with three white stripes, black neckerchief tied in a white bow
      c.fillStyle = '#0e1326'; c.beginPath(); c.moveTo(-124, -206); c.lineTo(-60, -206); c.lineTo(0, -116); c.lineTo(60, -206); c.lineTo(124, -206); c.lineTo(124, -160); c.lineTo(0, -82); c.lineTo(-124, -160); c.closePath(); c.fill();
      c.fillStyle = C[0]; c.beginPath(); c.moveTo(-44, -206); c.lineTo(0, -136); c.lineTo(44, -206); c.fill();  // jumper V front under the collar
      c.strokeStyle = '#f4f2ec'; c.lineWidth = 4; [6, 14, 22].forEach(d => { c.beginPath(); c.moveTo(-126, -160 - d); c.lineTo(0, -82 - d); c.lineTo(126, -160 - d); c.stroke(); });  // three collar stripes
      c.fillStyle = '#0a0a0c'; c.beginPath(); c.moveTo(-30, -152); c.lineTo(30, -152); c.lineTo(12, -116); c.lineTo(-12, -116); c.closePath(); c.fill();  // black neckerchief
      c.beginPath(); c.moveTo(-12, -118); c.lineTo(-24, -60); c.lineTo(-6, -66); c.lineTo(0, -112); c.lineTo(6, -66); c.lineTo(24, -60); c.lineTo(12, -118); c.closePath(); c.fill();
      c.fillStyle = '#f4f2ec'; [-1, 1].forEach(sd => { c.beginPath(); c.moveTo(0, -116); c.lineTo(sd * 24, -128); c.lineTo(sd * 22, -102); c.closePath(); c.fill(); });  // white bow at the knot
      c.beginPath(); c.arc(0, -115, 6, 0, 7); c.fill();
    } else if (o.side === 'suit' || o.side === 'work') {  // jacket lapels; suit: white shirt and tie
      if (o.side === 'suit') { c.fillStyle = '#ece6d8'; c.beginPath(); c.moveTo(-44, -204); c.lineTo(0, -110); c.lineTo(44, -204); c.fill(); c.fillStyle = o.tie || C[2]; c.beginPath(); c.moveTo(-9, -198); c.lineTo(9, -198); c.lineTo(13, -128); c.lineTo(0, -112); c.lineTo(-13, -128); c.closePath(); c.fill(); }
      c.strokeStyle = 'rgba(0,0,0,0.45)'; c.lineWidth = 6; c.beginPath(); c.moveTo(-50, -206); c.lineTo(-6, -100); c.lineTo(-6, 0); c.moveTo(50, -206); c.lineTo(6, -100); c.stroke();
      c.fillStyle = '#16120f'; for (let i = 0; i < 2; i++) { c.beginPath(); c.arc(-24, -84 + i * 34, 5, 0, 7); c.fill(); }
    } else if (o.side === 'usaf') {  // USAF service dress 1960s: blue coat, light-blue shirt, dark tie, silver buttons, ribbon bar
      c.fillStyle = '#b8c8dc'; c.beginPath(); c.moveTo(-44, -204); c.lineTo(0, -120); c.lineTo(44, -204); c.fill();
      c.fillStyle = '#1a1c22'; c.beginPath(); c.moveTo(-8, -198); c.lineTo(8, -198); c.lineTo(11, -136); c.lineTo(0, -122); c.lineTo(-11, -136); c.closePath(); c.fill();
      c.strokeStyle = 'rgba(0,0,0,0.45)'; c.lineWidth = 6; c.beginPath(); c.moveTo(-50, -206); c.lineTo(-6, -110); c.lineTo(-6, 0); c.moveTo(50, -206); c.lineTo(6, -110); c.stroke();
      c.fillStyle = '#c9ccd0'; for (let i = 0; i < 3; i++) { c.beginPath(); c.arc(-22, -96 + i * 30, 5, 0, 7); c.fill(); }
      [['#c0282d', -84], ['#d8b450', -60], ['#2a4c9a', -36]].forEach(([col, rx]) => { c.fillStyle = col; c.fillRect(rx, -170, 22, 10); });  // ribbon bar
    } else if (o.side === 'astro' || o.side === 'cosmo') {  // white pressure suit: zip, chest box with hose connectors; astro: flag patch, cosmo: red "СССР"
      c.strokeStyle = 'rgba(0,0,0,0.25)'; c.lineWidth = 4; c.beginPath(); c.moveTo(0, -200); c.lineTo(0, 0); c.stroke();
      c.fillStyle = '#9a9aa0'; c.fillRect(-52, -150, 104, 54); c.strokeStyle = 'rgba(0,0,0,0.4)'; c.lineWidth = 2; c.strokeRect(-52, -150, 104, 54);
      c.fillStyle = '#c0282d'; c.beginPath(); c.arc(-26, -123, 11, 0, 7); c.fill(); c.fillStyle = '#2a4c9a'; c.beginPath(); c.arc(26, -123, 11, 0, 7); c.fill();
      if (o.side === 'astro') { c.fillStyle = '#ece6d8'; c.fillRect(-104, -186, 40, 26); c.fillStyle = '#c0282d'; for (let k = 0; k < 4; k++) c.fillRect(-104, -186 + k * 7, 40, 3); c.fillStyle = '#2a4c9a'; c.fillRect(-104, -186, 17, 13); }
      else { c.fillStyle = '#c0282d'; c.fillRect(-160, -64, 320, 12); c.fillRect(-104, -186, 40, 26); }  // red band + arm patch (СССР is on the helmet)
    } else if (o.side === 'lab') {  // engineer's white lab coat over shirt and dark tie, pens in the pocket
      c.fillStyle = '#f4f2ec'; c.beginPath(); c.moveTo(-36, -204); c.lineTo(0, -140); c.lineTo(36, -204); c.fill();
      c.fillStyle = o.tie || '#23262c'; c.beginPath(); c.moveTo(-7, -198); c.lineTo(7, -198); c.lineTo(10, -146); c.lineTo(0, -134); c.lineTo(-10, -146); c.closePath(); c.fill();
      c.strokeStyle = 'rgba(0,0,0,0.3)'; c.lineWidth = 5; c.beginPath(); c.moveTo(-56, -206); c.lineTo(-4, -96); c.lineTo(-4, 0); c.moveTo(56, -206); c.lineTo(4, -96); c.stroke();
      c.strokeStyle = 'rgba(0,0,0,0.3)'; c.lineWidth = 3; c.strokeRect(46, -150, 44, 40); c.fillStyle = '#2a4c9a'; c.fillRect(54, -168, 5, 24); c.fillStyle = '#c0282d'; c.fillRect(64, -164, 5, 20);
    } else if (o.side === 'flight') {  // jet pilot 1960s-90s: one-piece flight coverall, zip, chest pockets, harness straps; o.air = usaf|pvo|iaf|irq|jasdf picks colour + patch
      c.strokeStyle = 'rgba(0,0,0,0.35)'; c.lineWidth = 4; c.beginPath(); c.moveTo(0, -204); c.lineTo(0, 0); c.stroke();  // zip
      c.fillStyle = 'rgba(0,0,0,0.18)'; [-1, 1].forEach(sd => c.fillRect(sd * 52 - 26, -170, 52, 40));  // pockets
      c.strokeStyle = '#2a2a24'; c.lineWidth = 11; c.beginPath(); c.moveTo(-70, -204); c.lineTo(-56, 0); c.moveTo(70, -204); c.lineTo(56, 0); c.moveTo(-60, -60); c.lineTo(60, -60); c.stroke();  // parachute/G-suit harness
      c.fillStyle = '#9a9a8a'; c.fillRect(-12, -70, 24, 22);  // harness buckle
      const air = o.air || 'usaf';
      if (air === 'pvo') { c.strokeStyle = 'rgba(40,38,30,0.55)'; c.lineWidth = 6; [-1, 1].forEach(sd => { c.beginPath(); c.moveTo(sd * 104, -200); c.lineTo(sd * 96, 0); c.stroke(); }); star(-110, -170, 18, '#c0282d'); }  // VKK pressure suit lacing tubes + red star
      else if (air === 'usaf') { c.fillStyle = '#ece6d8'; c.fillRect(-82, -192, 52, 12); c.fillStyle = '#c9ccd0'; c.beginPath(); c.moveTo(-82, -204); c.lineTo(-30, -204); c.lineTo(-56, -196); c.fill(); }  // name tape + wings
      else if (air === 'iaf') { c.fillStyle = '#f2efe8'; c.fillRect(-122, -184, 36, 26); c.strokeStyle = '#2a4c9a'; c.lineWidth = 3; c.beginPath(); c.moveTo(-104, -180); c.lineTo(-113, -164); c.lineTo(-95, -164); c.closePath(); c.moveTo(-104, -158); c.lineTo(-113, -174); c.lineTo(-95, -174); c.closePath(); c.stroke(); }  // white-blue star patch
      else if (air === 'irq') { [['#c0282d', 0], ['#f2efe8', 9], ['#16120f', 18]].forEach(([col, dy]) => { c.fillStyle = col; c.fillRect(-122, -184 + dy, 36, 9); }); }
      else if (air === 'jasdf') { c.fillStyle = '#f2efe8'; c.fillRect(-122, -184, 36, 26); c.fillStyle = '#c0282d'; c.beginPath(); c.arc(-104, -171, 8, 0, 7); c.fill(); }
    } else if (o.side === 'aut' || o.side === 'sax') {  // Austrian 1866 white Waffenrock (o.facing = regimental colour) / Saxon light blue: one brass row, black belt
      c.fillStyle = 'rgba(0,0,0,0.25)'; c.fillRect(-2, -196, 4, 130);
      c.fillStyle = '#d8b450'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(0, -184 + i * 24, 6, 0, 7); c.fill(); }
      c.fillStyle = C[1]; c.fillRect(-160, -66, 320, 0);
      c.fillStyle = '#141210'; c.fillRect(-160, -66, 320, 16); c.fillStyle = '#d8b450'; c.fillRect(-15, -68, 30, 20);
    } else if (o.side === 'pru') {
      c.fillStyle = '#e8e2d2'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(0, -184 + i * 28, 5, 0, 7); c.fill(); }
      if (o.hat === 'pickel' && !o.epaulettes) { c.fillStyle = '#141210'; c.fillRect(-160, -74, 320, 16); [-1, 1].forEach(sd => { c.fillStyle = '#1e1a16'; c.fillRect(sd * 60 - 22, -84, 44, 34); }); c.fillStyle = '#d8b450'; c.fillRect(-14, -76, 28, 20); }  // 1866 Waffenrock: black belt, two front cartridge pouches, brass buckle
      c.fillStyle = C[1]; c.fillRect(-160, -60, 320, 0);
    } else {
      c.beginPath(); c.moveTo(-40, -196); c.lineTo(0, -70); c.lineTo(40, -196); c.lineTo(22, -196); c.lineTo(0, -120); c.lineTo(-22, -196); c.fill();  // facings
      c.fillStyle = '#e0bd5a'; for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(-12, -170 + i * 34, 5, 0, 7); c.arc(12, -170 + i * 34, 5, 0, 7); c.fill(); }
    }
    if (o.belts !== false && !o.epaulettes && o.hat !== 'pickel' && ['pru', 'fra', 'brit', 'civ', 'rus'].includes(o.side || 'pru')) { c.strokeStyle = C[2]; c.lineWidth = 12; c.beginPath(); c.moveTo(-90, -190); c.lineTo(90, -20); c.moveTo(90, -190); c.lineTo(-90, -20); c.stroke(); }
    if (o.epaulettes) { c.fillStyle = C[1]; c.fillRect(-160, -80, 320, 14); }  // sash
    if (o.armband) {  // band round the left upper arm (viewer's right edge of the coat)
      const ab = { vs: '#d8b440', hj: '#c0282d', white: '#f2efe8' }[o.armband] || o.armband; c.fillStyle = ab; c.beginPath(); c.moveTo(78, -176); c.lineTo(170, -184); c.lineTo(170, -146); c.lineTo(80, -140); c.closePath(); c.fill();
      if (o.armband === 'hj') { c.fillStyle = '#f2efe8'; c.beginPath(); c.moveTo(79, -166); c.lineTo(170, -172); c.lineTo(170, -158); c.lineTo(79, -151); c.closePath(); c.fill(); }
      if (o.armband === 'vs') { c.fillStyle = '#16120f'; for (let k = 0; k < 4; k++) c.fillRect(90 + k * 18, -164 + k * -0.6, 12, 4); }
    }
    // soft shading on the right side, highlight on the left
    const sh = c.createRadialGradient(-50, -300, 20, 0, -200, 260); sh.addColorStop(0, 'rgba(255,255,255,0.18)'); sh.addColorStop(0.6, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.35)');
    c.fillStyle = sh; c.fillRect(-160, -420, 320, 440);
    c.restore();
    c.strokeStyle = 'rgba(0,0,0,0.55)'; c.lineWidth = 4; egg(); c.stroke();
    if (o.epaulettes) { c.fillStyle = '#e0bd5a'; [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 105, -190, 34, 12, sd * 0.35, 0, 7); c.fill(); c.strokeStyle = 'rgba(0,0,0,0.4)'; c.lineWidth = 2; c.stroke(); }); }
    const hair = { grey: '#a19d96', white: '#ece8e0', dark: '#3e2c1f', bald: null }[o.hair || 'dark'];
    if (hair && o.hat !== 'bearskin' && o.hat !== 'hussar' && o.hat !== 'flighthelmet') { c.fillStyle = hair; c.beginPath(); c.ellipse(-92, -290, 20, 40, 0.15, 0, 7); c.ellipse(92, -290, 20, 40, -0.15, 0, 7); c.fill(); if (o.hat === 'none') { c.beginPath(); c.ellipse(0, -372, 80, 34, 0, Math.PI, 0); c.fill(); } }
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
    if (o.eyepatch) { const ex = o.eyepatch === 'right' ? -30 : 30; c.strokeStyle = '#16120f'; c.lineWidth = 5; c.beginPath(); c.moveTo(-88, -322); c.lineTo(ex, -296); c.lineTo(96, -306); c.stroke(); c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(ex, -290, 22, 20, 0, 0, 7); c.fill(); }  // black eye patch, the doll's left eye by default (viewer's right): Stauffenberg
    if (o.glasses) { c.strokeStyle = '#2a2420'; c.lineWidth = 4; [-30, 30].forEach(gx => { c.beginPath(); c.arc(gx, -290, 20, 0, 7); c.stroke(); }); c.beginPath(); c.moveTo(-10, -290); c.lineTo(10, -290); c.stroke(); }
    if (o.toothbrush) { c.fillStyle = '#16120f'; c.fillRect(-11, -272, 22, 9); }
    if (o.emptySleeve) { c.fillStyle = 'rgba(0,0,0,0.28)'; c.beginPath(); c.moveTo(-116, -190); c.quadraticCurveTo(-136, -120, -120, -70); c.lineTo(-84, -92); c.quadraticCurveTo(-92, -140, -88, -186); c.closePath(); c.fill(); c.strokeStyle = 'rgba(0,0,0,0.5)'; c.lineWidth = 3; c.stroke(); c.fillStyle = '#c9ccd0'; c.fillRect(-104, -92, 14, 4); }  // folded, pinned right sleeve (viewer's left)
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
    else if (hat === 'pickel') {  // Prussian Pickelhaube 1860s: tall black leather dome, front + rear peak, brass spike on a cross base, brass eagle plate, black-white cockade
      const lg = c.createLinearGradient(-90, 0, 90, 0); lg.addColorStop(0, '#3a3a3e'); lg.addColorStop(0.45, '#1a1a1d'); lg.addColorStop(1, '#050506');
      c.fillStyle = lg; c.beginPath(); c.moveTo(-96, -366); c.bezierCurveTo(-104, -500, 104, -500, 96, -366); c.closePath(); c.fill(); rim();
      c.fillStyle = 'rgba(255,255,255,0.22)'; c.beginPath(); c.ellipse(-40, -440, 14, 34, -0.3, 0, 7); c.fill();  // leather shine
      c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(0, -364, 104, 18, 0, 0, Math.PI); c.fill();  // front peak
      c.fillStyle = '#d8b450'; c.fillRect(-100, -370, 200, 5);  // brass peak trim
      c.beginPath(); c.ellipse(0, -478, 30, 9, 0, 0, 7); c.fill(); c.beginPath(); c.moveTo(-14, -482); c.lineTo(0, -548); c.lineTo(14, -482); c.closePath(); c.fill();  // cross base + spike
      c.fillStyle = '#e0bd5a'; c.beginPath(); c.ellipse(0, -416, 22, 28, 0, 0, 7); c.fill();  // eagle plate body
      c.beginPath(); c.moveTo(-18, -426); c.lineTo(-52, -446); c.lineTo(-40, -404); c.closePath(); c.moveTo(18, -426); c.lineTo(52, -446); c.lineTo(40, -404); c.closePath(); c.fill();  // spread wings
      c.fillStyle = '#9a7a2a'; c.beginPath(); c.arc(0, -420, 7, 0, 7); c.fill();
      c.fillStyle = '#ece6d8'; c.beginPath(); c.arc(84, -392, 12, 0, 7); c.fill(); c.fillStyle = '#16120f'; c.beginPath(); c.arc(84, -392, 6, 0, 7); c.fill();
    } else if (hat === 'autshako') {  // Austrian infantry Tschako 1860s: low black shako narrowing upward, brass double-eagle plate, black-yellow rosette, short peak
      c.fillStyle = felt(-70, 0, 70, 0); c.beginPath(); c.moveTo(-84, -368); c.lineTo(-72, -468); c.lineTo(72, -468); c.lineTo(84, -368); c.closePath(); c.fill(); rim();
      c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(0, -366, 100, 16, 0, 0, Math.PI); c.fill();
      c.fillStyle = '#d8b450'; c.fillRect(-84, -380, 168, 6);
      c.fillStyle = '#e0bd5a'; c.beginPath(); c.arc(0, -414, 18, 0, 7); c.fill(); c.beginPath(); c.moveTo(-12, -420); c.lineTo(-40, -436); c.lineTo(-30, -400); c.closePath(); c.moveTo(12, -420); c.lineTo(40, -436); c.lineTo(30, -400); c.closePath(); c.fill();
      c.fillStyle = '#e0bd5a'; c.beginPath(); c.arc(0, -458, 13, 0, 7); c.fill(); c.fillStyle = '#16120f'; c.beginPath(); c.arc(0, -458, 6, 0, 7); c.fill();
    } else if (hat === 'federhut') {  // Austrian general's bicorne (Generalshut) worn sideways with a green feather plume (Benedek, Ramming, Gablenz)
      c.fillStyle = felt(0, -500, 0, -360); c.beginPath(); c.moveTo(-170, -352); c.quadraticCurveTo(-60, -500, 0, -488); c.quadraticCurveTo(60, -500, 170, -352); c.quadraticCurveTo(0, -386, -170, -352); c.fill(); rim();
      c.fillStyle = '#d8b450'; c.fillRect(-4, -470, 8, 90);
      const fg = ['#2f6a3a', '#3f8a4a', '#24502c']; for (let i = 0; i < 9; i++) { c.fillStyle = fg[i % 3]; c.beginPath(); c.ellipse(-120 + i * 30, -470 - Math.sin(i / 8 * Math.PI) * 40, 34, 16, -0.4 + i * 0.1, 0, 7); c.fill(); }
    }
    else if (hat === 'kepi' && (o.side === 'union' || o.side === 'confed')) {  // Civil War forage cap ("bummer"): soft crown slumped forward-right, plain band, brass bugle (Union)
      c.fillStyle = o.capCol || (o.side === 'union' ? '#1f2846' : '#7d796e'); c.beginPath(); c.moveTo(-86, -368); c.lineTo(-80, -432); c.quadraticCurveTo(-30, -478, 60, -474); c.quadraticCurveTo(104, -470, 98, -440); c.lineTo(86, -368); c.closePath(); c.fill(); rim();
      c.fillStyle = 'rgba(0,0,0,0.28)'; c.fillRect(-86, -394, 172, 20);
      c.fillStyle = '#141210'; c.beginPath(); c.ellipse(6, -366, 96, 15, 0, 0, Math.PI); c.fill();
      if (o.side === 'union') { c.strokeStyle = '#d8b450'; c.lineWidth = 5; c.beginPath(); c.arc(0, -420, 15, 0.3, Math.PI * 1.7); c.stroke(); c.beginPath(); c.moveTo(12, -428); c.lineTo(32, -436); c.stroke(); }
    }
    else if (hat === 'slouch') {  // Civil War slouch hat: wide soft brim drooping at the sides, dented crown, dark band
      c.fillStyle = o.capCol || '#4e4436'; c.beginPath(); c.moveTo(-178, -338); c.quadraticCurveTo(-160, -394, 0, -396); c.quadraticCurveTo(160, -394, 178, -338); c.quadraticCurveTo(110, -372, 0, -372); c.quadraticCurveTo(-110, -372, -178, -338); c.fill(); rim();
      c.beginPath(); c.moveTo(-82, -388); c.lineTo(-76, -452); c.quadraticCurveTo(-40, -478, 0, -458); c.quadraticCurveTo(40, -478, 76, -452); c.lineTo(82, -388); c.closePath(); c.fill(); rim();
      c.fillStyle = '#1a1612'; c.fillRect(-82, -406, 164, 16);
    } else if (hat === 'beret') {  // beret pulled down to the right, leather band, brass badge over the left eye
      c.fillStyle = o.capCol || '#26241f'; c.beginPath(); c.moveTo(-104, -372); c.quadraticCurveTo(-110, -430, -10, -442); c.quadraticCurveTo(120, -450, 150, -400); c.quadraticCurveTo(156, -360, 112, -352); c.quadraticCurveTo(100, -372, 0, -376); c.closePath(); c.fill(); rim();
      c.strokeStyle = '#1a1612'; c.lineWidth = 9; c.beginPath(); c.moveTo(-102, -374); c.quadraticCurveTo(0, -386, 104, -366); c.stroke();
      c.fillStyle = '#d8b450'; c.beginPath(); c.arc(-50, -394, 13, 0, 7); c.fill();
    }
    else if (hat === 'kepi') {  // French 1860s kepi with a white sun cover (couvre-nuque) for Cochinchina
      c.fillStyle = o.cover ? '#e8e2d2' : '#1c2440'; c.beginPath(); c.moveTo(-80, -370); c.lineTo(-70, -455); c.lineTo(76, -445); c.lineTo(80, -370); c.closePath(); c.fill(); rim();
      c.fillStyle = '#c0282d'; c.fillRect(-82, -392, 164, 12); c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(20, -366, 90, 14, 0, 0, Math.PI); c.fill();
      if (o.cover) { c.fillStyle = '#e8e2d2'; c.beginPath(); c.moveTo(-82, -380); c.lineTo(-110, -300); c.lineTo(-40, -330); c.closePath(); c.fill(); }
    } else if (hat === 'lycap') {  // Simple cloth head covering, deliberately without speculative court insignia
      c.fillStyle = felt(0, -455, 0, -348); c.beginPath();
      c.moveTo(-103, -357); c.quadraticCurveTo(-96, -428, -40, -437);
      c.quadraticCurveTo(28, -455, 72, -405); c.lineTo(108, -357);
      c.quadraticCurveTo(0, -332, -103, -357); c.fill(); rim();
      c.strokeStyle = 'rgba(210,205,195,0.28)'; c.lineWidth = 5;
      c.beginPath(); c.moveTo(-96, -365); c.quadraticCurveTo(0, -347, 98, -365); c.stroke();
    } else if (hat === 'xungthien') {  // Lý-Trần royal crown (mũ Xung Thiên / Bình Đính viền vàng)
      c.fillStyle = felt(0, -475, 0, -350); c.beginPath();
      c.moveTo(-98, -356); c.lineTo(-88, -445); c.quadraticCurveTo(0, -482, 88, -445); c.lineTo(98, -356); c.quadraticCurveTo(0, -336, -98, -356); c.fill(); rim();
      c.fillStyle = '#d8b450'; c.fillRect(-94, -372, 188, 12); c.beginPath(); c.arc(0, -412, 12, 0, 7); c.fill();
      [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 114, -395, 28, 11, sd * 0.25, 0, 7); c.fill(); });
    } else if (hat === 'phocdau') {  // Lý-Trần court official hat (phốc đầu / cánh nhỏ)
      c.fillStyle = felt(0, -460, 0, -355); c.beginPath();
      c.moveTo(-94, -356); c.lineTo(-82, -432); c.quadraticCurveTo(0, -462, 82, -432); c.lineTo(94, -356); c.quadraticCurveTo(0, -340, -94, -356); c.fill(); rim();
      c.fillStyle = '#16120f'; [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 124, -384, 42, 11, sd * 0.12, 0, 7); c.fill(); rim(); });
    } else if (hat === 'daumau') {  // Lý-Trần conical leather/iron helmet (mũ đầu mâu)
      c.fillStyle = '#4e4842'; c.beginPath(); c.moveTo(-124, -350); c.lineTo(0, -466); c.lineTo(124, -350); c.quadraticCurveTo(0, -332, -124, -350); c.fill(); rim();
      c.strokeStyle = 'rgba(210,205,195,0.4)'; c.lineWidth = 3; c.beginPath(); c.moveTo(0, -466); c.lineTo(0, -342); c.stroke();
      c.fillStyle = '#8f7c5b'; c.beginPath(); c.arc(0, -470, 9, 0, 7); c.fill();
    } else if (hat === 'mongolhat') {  // Mongol fur-brimmed conical steppe cap
      c.fillStyle = '#5c4e3e'; c.beginPath(); c.moveTo(-98, -364); c.lineTo(0, -468); c.lineTo(98, -364); c.closePath(); c.fill(); rim();
      c.fillStyle = '#3a2e22'; c.beginPath(); c.ellipse(0, -364, 114, 24, 0, 0, 7); c.fill(); rim();
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
    else if (hat === 'adrian') {  // French M1915 Adrian helmet: rounded crown, front visor + rear brim, raised crest along the top
      const col = o.helmCol || '#6f8099'; const hg = c.createLinearGradient(-110, -470, 110, -340); hg.addColorStop(0, col); hg.addColorStop(1, '#2a3040'); c.fillStyle = hg;
      c.beginPath(); c.moveTo(-150, -350); c.quadraticCurveTo(-120, -366, -96, -368); c.bezierCurveTo(-100, -470, 100, -470, 96, -368); c.quadraticCurveTo(120, -366, 150, -350); c.quadraticCurveTo(0, -372, -150, -350); c.closePath(); c.fill(); rim();
      c.fillStyle = col; c.beginPath(); c.moveTo(-70, -418); c.quadraticCurveTo(0, -474, 70, -418); c.quadraticCurveTo(0, -440, -70, -418); c.fill(); rim();  // crest on the crown
      c.fillStyle = '#c9b98a'; c.beginPath(); c.arc(0, -410, 10, 0, 7); c.fill();  // grenade badge (plain disc)
      c.strokeStyle = 'rgba(255,255,255,0.22)'; c.lineWidth = 6; c.beginPath(); c.arc(-14, -398, 50, Math.PI * 1.15, Math.PI * 1.45); c.stroke();
    } else if (hat === 'stahlhelm' || hat === 'm1916' || hat === 'm1' || hat === 'brodie' || hat === 'rumhelm') {  // steel helmets: dome + (M35) flared skirt / (M1) small rim / (Brodie) wide brim
      const col = o.helmCol || { stahlhelm: '#565d4c', m1916: '#5c6150', m1: '#5a5a3c', brodie: '#5e5a40', rumhelm: '#5c5a3e' }[hat];
      const hg = c.createLinearGradient(-110, -470, 110, -340); hg.addColorStop(0, col); hg.addColorStop(1, '#1e2018'); c.fillStyle = hg; c.beginPath();
      if (hat === 'm1916') { c.moveTo(-100, -364); c.bezierCurveTo(-108, -490, 108, -490, 100, -364); c.lineTo(108, -330); c.lineTo(146, -296); c.quadraticCurveTo(118, -318, 94, -330); c.lineTo(-94, -330); c.quadraticCurveTo(-118, -318, -146, -296); c.lineTo(-108, -330); c.closePath(); }  // WWI M1916: deeper skirt, big flare over the neck
      else if (hat === 'stahlhelm') { c.moveTo(-100, -360); c.bezierCurveTo(-108, -488, 108, -488, 100, -360); c.lineTo(134, -316); c.quadraticCurveTo(112, -330, 92, -338); c.lineTo(-92, -338); c.quadraticCurveTo(-112, -330, -134, -316); c.closePath(); }
      else if (hat === 'm1') { c.moveTo(-114, -346); c.bezierCurveTo(-116, -486, 116, -486, 114, -346); c.quadraticCurveTo(0, -362, -114, -346); }
      else if (hat === 'rumhelm') { c.moveTo(-138, -342); c.quadraticCurveTo(-118, -356, -104, -360); c.bezierCurveTo(-112, -486, 112, -486, 104, -360); c.quadraticCurveTo(118, -356, 138, -342); c.quadraticCurveTo(0, -330, -138, -342); }  // Romanian M1939 (Dutch pattern): high dome, even all-round brim
      else { c.ellipse(0, -372, 158, 24, 0, 0, 7); c.moveTo(-92, -372); c.bezierCurveTo(-96, -460, 96, -460, 92, -372); }
      c.fill(); rim();
      c.strokeStyle = 'rgba(255,255,255,0.22)'; c.lineWidth = 6; c.beginPath(); c.arc(-14, -392, 52, Math.PI * 1.15, Math.PI * 1.45); c.stroke();  // highlight
      if (hat === 'm1916') { c.fillStyle = '#3a3e30'; [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 92, -380, 9, 12, 0, 0, 7); c.fill(); }); }  // ventilation lugs (Stirnpanzer mounts)
      if (hat === 'm1' && o.side === 'us') { c.strokeStyle = 'rgba(40,36,24,0.6)'; c.lineWidth = 3; c.beginPath(); c.moveTo(-100, -352); c.quadraticCurveTo(0, -300, 100, -352); c.stroke(); }  // chinstrap
    } else if (hat === 'pasgt' || hat === 'bducap') {  // 1980s US Army: PASGT Kevlar helmet (deep brow, swept ear guards, camo cover) / woodland patrol cap
      const path = () => { c.beginPath(); if (hat === 'pasgt') { c.moveTo(-84, -352); c.quadraticCurveTo(-92, -312, -118, -300); c.quadraticCurveTo(-136, -302, -124, -372); c.bezierCurveTo(-120, -492, 120, -492, 124, -372); c.quadraticCurveTo(136, -302, 118, -300); c.quadraticCurveTo(92, -312, 84, -352); c.quadraticCurveTo(0, -340, -84, -352); } else { c.moveTo(-98, -374); c.lineTo(-92, -448); c.quadraticCurveTo(0, -470, 92, -448); c.lineTo(98, -374); c.quadraticCurveTo(0, -356, -98, -374); } c.closePath(); };
      path(); c.fillStyle = o.helmCol || '#59603f'; c.fill(); c.save(); path(); c.clip();
      [['#3b4a2c', 0], ['#6b5638', 3], ['#1f2018', 7]].forEach(([col, k]) => { c.fillStyle = col; for (let i = 0; i < 6; i++) { c.beginPath(); c.ellipse(-120 + ((i * 71 + k * 37) % 240), -330 - ((i * 47 + k * 23) % 130), 22, 9, (i + k) * 0.7, 0, 7); c.fill(); } });
      c.restore(); path(); rim();
      if (hat === 'pasgt') { c.strokeStyle = '#2c2c20'; c.lineWidth = 8; c.beginPath(); c.moveTo(-122, -392); c.quadraticCurveTo(0, -376, 122, -392); c.stroke(); } else { c.fillStyle = '#4a5236'; c.beginPath(); c.ellipse(0, -370, 96, 20, 0, 0, Math.PI); c.fill(); }
    } else if (hat === 'kopftuch') {  // headscarf over the hair, knotted under the chin
      c.fillStyle = o.capCol || '#6a5a4a'; c.beginPath(); c.moveTo(-112, -250); c.bezierCurveTo(-130, -470, 130, -470, 112, -250); c.quadraticCurveTo(96, -330, 0, -352); c.quadraticCurveTo(-96, -330, -112, -250); c.closePath(); c.fill(); rim();
      c.beginPath(); c.moveTo(-20, -214); c.lineTo(-44, -176); c.lineTo(-8, -196); c.lineTo(20, -176); c.lineTo(10, -214); c.closePath(); c.fill();
    } else if (hat === 'tankist') {  // Soviet padded tank helmet: dark leather, three padded ridges, ear flaps
      const th = () => { c.beginPath(); c.moveTo(-106, -300); c.bezierCurveTo(-120, -478, 120, -478, 106, -300); c.lineTo(92, -296); c.quadraticCurveTo(96, -360, 0, -364); c.quadraticCurveTo(-96, -360, -92, -296); c.closePath(); };
      c.fillStyle = '#2a241e'; th(); c.fill(); rim();
      c.save(); th(); c.clip(); c.strokeStyle = '#4a423a'; c.lineWidth = 14; [-44, 0, 44].forEach(dx => { c.beginPath(); c.moveTo(dx * 1.5, -362); c.quadraticCurveTo(dx * 1.2, -420, dx * 0.5, -446); c.stroke(); }); c.restore();
      c.fillStyle = '#2a241e'; [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 104, -310, 24, 40, 0, 0, 7); c.fill(); });
    } else if (hat === 'pilotka') {  // Soviet side cap with red star
      c.fillStyle = felt(0, -440, 0, -370); c.fillStyle = '#6e6844'; c.beginPath(); c.moveTo(-98, -370); c.lineTo(-84, -432); c.quadraticCurveTo(0, -448, 84, -432); c.lineTo(98, -370); c.quadraticCurveTo(0, -388, -98, -370); c.fill(); rim();
      c.strokeStyle = 'rgba(0,0,0,0.3)'; c.lineWidth = 3; c.beginPath(); c.moveTo(-94, -394); c.quadraticCurveTo(0, -410, 94, -394); c.stroke(); star(0, -404, 16, '#c0282d');
    } else if (hat === 'ushanka') {  // fur hat, flaps tied up
      c.fillStyle = '#6a5a46'; c.beginPath(); c.ellipse(0, -430, 100, 56, 0, Math.PI, 0); c.lineTo(100, -380); c.lineTo(-100, -380); c.fill(); rim();
      c.fillStyle = '#7a6a54'; c.beginPath(); c.ellipse(0, -384, 112, 30, 0, 0, 7); c.fill(); [-1, 1].forEach(sd => { c.beginPath(); c.ellipse(sd * 104, -410, 26, 40, 0, 0, 7); c.fill(); });
      c.strokeStyle = 'rgba(30,24,18,0.35)'; c.lineWidth = 2; for (let k = -4; k <= 4; k++) { c.beginPath(); c.moveTo(k * 24, -404); c.lineTo(k * 24 + 6, -370); c.stroke(); } star(0, -392, 14, '#c0282d');
    } else if (hat === 'jpcap') {  // IJA field cap: soft crown, short peak, yellow star; o.flaps = neck cloth
      if (o.flaps) { c.fillStyle = '#b8a878'; [-1, 1].forEach(sd => { c.beginPath(); c.moveTo(sd * 96, -380); c.lineTo(sd * 128, -276); c.lineTo(sd * 70, -300); c.closePath(); c.fill(); }); }
      c.fillStyle = '#8a7a4a'; c.beginPath(); c.ellipse(0, -398, 98, 52, 0, Math.PI, 0); c.lineTo(98, -372); c.lineTo(-98, -372); c.fill(); rim();
      c.fillStyle = '#4a3a24'; c.beginPath(); c.ellipse(0, -368, 94, 14, 0, 0, Math.PI); c.fill(); star(0, -404, 15, '#e0bd5a');
    } else if (hat === 'peaked' || hat === 'polcap') {  // officer's peaked cap: band colour + badge by side
      const top = o.capCol || (o.whites && (o.side === 'ijn' || o.side === 'navy') ? '#eeebe2' : null) || { ijn: '#151a2a', usaf: '#3a4b6e', wehr: '#5b6150', sd: '#666a66', nsdap: '#75705f', sov: '#6e6844', us: '#6b6440', navy: '#ece8e0', jap: '#8a7a4a', tommy: '#7a6a48', rum: '#6e6244', kaiser: '#6a6d58', poilu: '#7d90aa', polizei: '#46563f' }[o.side] || '#2a2a2e';
      const band = { ijn: '#0a0a0c', usaf: '#16120f', wehr: '#3d4a3a', sd: '#16120f', nsdap: '#4a3a2a', sov: '#c0282d', navy: '#16120f', jap: '#c0282d', tommy: '#5a4a30', rum: '#3a2c1e', kaiser: '#b0302a', poilu: '#2a3450' }[o.side] || '#3a3a30';
      c.fillStyle = band; c.fillRect(-88, -420, 176, 52); c.fillStyle = top; c.beginPath(); c.moveTo(-88, -418); c.quadraticCurveTo(-150, -470, -60, -476); c.quadraticCurveTo(0, -470, 60, -476); c.quadraticCurveTo(150, -470, 88, -418); c.closePath(); c.fill(); rim();
      c.fillStyle = '#16120f'; c.beginPath(); c.ellipse(0, -366, 100, 18, 0, 0, Math.PI); c.fill();
      if (o.side === 'sov') { c.fillStyle = '#d8b450'; c.beginPath(); c.arc(0, -398, 19, 0, 7); c.fill(); star(0, -398, 14, '#c0282d'); } else if (o.side === 'wehr') { c.fillStyle = '#c9ccc0'; c.beginPath(); c.moveTo(-34, -440); c.lineTo(0, -428); c.lineTo(34, -440); c.lineTo(0, -420); c.closePath(); c.fill(); c.beginPath(); c.arc(0, -396, 9, 0, 7); c.fill(); }
      else if (o.side === 'polizei') { star(0, -396, 16, '#c9ccc0'); }
      else if (o.side === 'ijn') {  // IJN cap badge: gold anchor inside a ring of cherry-blossom leaves
        c.fillStyle = '#d8b450'; for (let k = 0; k < 7; k++) { const a = Math.PI * (0.15 + k * 0.7 / 6) * 2 - Math.PI * 0.2; c.beginPath(); c.ellipse(Math.cos(a + Math.PI / 2) * 20, -396 + Math.sin(a + Math.PI / 2) * 20, 6, 4, a, 0, 7); c.fill(); }
        c.beginPath(); c.arc(0, -418, 7, 0, 7); c.fill(); c.strokeStyle = '#d8b450'; c.lineWidth = 4; c.beginPath(); c.moveTo(0, -410); c.lineTo(0, -386); c.moveTo(-9, -404); c.lineTo(9, -404); c.stroke(); c.beginPath(); c.arc(0, -394, 10, 0.3, Math.PI - 0.3); c.stroke();
      } else if (o.side === 'navy') {  // US Navy officer: gold eagle with spread wings over a silver shield, gold chin strap
        c.fillStyle = '#d8b450'; c.beginPath(); c.moveTo(-36, -414); c.quadraticCurveTo(-14, -392, 0, -404); c.quadraticCurveTo(14, -392, 36, -414); c.quadraticCurveTo(14, -400, 0, -394); c.quadraticCurveTo(-14, -400, -36, -414); c.fill();
        c.beginPath(); c.arc(0, -410, 6, 0, 7); c.fill(); c.fillStyle = '#c9ccd0'; c.beginPath(); c.moveTo(-9, -398); c.lineTo(9, -398); c.lineTo(9, -388); c.lineTo(0, -380); c.lineTo(-9, -388); c.closePath(); c.fill();
        c.fillStyle = '#d8b450'; c.fillRect(-88, -376, 176, 5);
      } else { c.fillStyle = '#d8b450'; c.beginPath(); c.arc(0, -400, 12, 0, 7); c.fill(); }
      if (o.side === 'wehr' && o.general) { c.strokeStyle = '#d8b450'; c.lineWidth = 4; c.beginPath(); c.moveTo(-88, -372); c.quadraticCurveTo(0, -362, 88, -372); c.moveTo(-88, -419); c.lineTo(88, -419); c.stroke(); }  // gold cord + piping
      if (o.side === 'sd') { c.fillStyle = '#c9ccc0'; c.beginPath(); c.moveTo(-30, -442); c.lineTo(0, -430); c.lineTo(30, -442); c.lineTo(0, -422); c.closePath(); c.fill(); c.beginPath(); c.arc(0, -397, 9, 0, 7); c.fill(); }
    } else if (hat === 'robecap') {  // judge's round cap
      c.fillStyle = '#7a181c'; c.beginPath(); c.moveTo(-92, -366); c.lineTo(-98, -432); c.quadraticCurveTo(0, -458, 98, -432); c.lineTo(92, -366); c.quadraticCurveTo(0, -352, -92, -366); c.fill(); rim();
    } else if (hat === 'tricornio') {  // Guardia Civil patent-leather tricorne: low crown, flat upright back brim
      c.fillStyle = '#0d0d0f'; c.beginPath(); c.moveTo(-128, -372); c.lineTo(-120, -440); c.lineTo(-60, -452); c.quadraticCurveTo(0, -466, 60, -452); c.lineTo(120, -440); c.lineTo(128, -372); c.quadraticCurveTo(0, -350, -128, -372); c.fill(); rim();
    } else if (hat === 'laurel') {  // laurel wreath
      c.fillStyle = '#5e7a3e'; for (let k = 0; k < 9; k++) { const a = Math.PI * (1.08 + k * 0.105); c.beginPath(); c.ellipse(Math.cos(a) * 88, -330 + Math.sin(a) * 60, 18, 8, a + 1.2, 0, 7); c.fill(); }
    } else if (hat === 'jpsailor') {  // IJN 水兵帽: round brimless cap, black ribbon band with gold characters (dashes), two short tails at the back
      c.fillStyle = '#141a30'; c.beginPath(); c.ellipse(0, -420, 112, 30, 0, 0, 7); c.fill(); rim();
      c.beginPath(); c.moveTo(-96, -414); c.lineTo(-92, -366); c.quadraticCurveTo(0, -356, 92, -366); c.lineTo(96, -414); c.closePath(); c.fill();
      c.fillStyle = '#0a0a0c'; c.beginPath(); c.moveTo(-94, -394); c.quadraticCurveTo(0, -384, 94, -394); c.lineTo(92, -368); c.quadraticCurveTo(0, -358, -92, -368); c.closePath(); c.fill();
      c.fillStyle = '#d8b450'; for (let k = -3; k <= 3; k++) c.fillRect(k * 16 - 5, -382 + Math.abs(k) * 0.6, 10, 4);
      c.fillStyle = '#0a0a0c'; [[96, -380, 120, -326], [90, -376, 104, -322]].forEach(([a1, b1, a2, b2]) => { c.beginPath(); c.moveTo(a1, b1); c.lineTo(a2, b2); c.lineTo(a2 - 9, b2 + 4); c.lineTo(a1 - 10, b1 + 4); c.closePath(); c.fill(); });
    } else if (hat === 'kmsailor') {  // Kaiserliche Marine Tellermütze: wide flat crown, black ribbon band with gold dashes (no text), two long tails down the back
      c.fillStyle = '#0a0a0c'; [[106, -378, 170, -244], [94, -374, 150, -232]].forEach(([a1, b1, a2, b2]) => { c.beginPath(); c.moveTo(a1, b1); c.lineTo(a2, b2); c.lineTo(a2 - 12, b2 + 6); c.lineTo(a2 - 18, b2 - 2); c.lineTo(a1 - 12, b1 + 4); c.closePath(); c.fill(); });  // long tails
      c.fillStyle = '#121830'; c.beginPath(); c.ellipse(0, -426, 136, 30, 0, 0, 7); c.fill(); rim();
      c.beginPath(); c.moveTo(-108, -420); c.lineTo(-100, -364); c.quadraticCurveTo(0, -354, 100, -364); c.lineTo(108, -420); c.closePath(); c.fill();
      c.fillStyle = '#0a0a0c'; c.beginPath(); c.moveTo(-104, -398); c.quadraticCurveTo(0, -388, 104, -398); c.lineTo(100, -366); c.quadraticCurveTo(0, -356, -100, -366); c.closePath(); c.fill();
      c.fillStyle = '#d8b450'; for (let k = -4; k <= 4; k++) c.fillRect(k * 18 - 5, -384 + Math.abs(k) * 0.6, 10, 4);
    } else if (hat === 'dixie') {  // US Navy white "dixie cup": round crown, brim turned up all round
      c.fillStyle = '#f2efe8'; c.beginPath(); c.moveTo(-84, -380); c.bezierCurveTo(-90, -470, 90, -470, 84, -380); c.closePath(); c.fill(); c.strokeStyle = 'rgba(60,60,70,0.55)'; c.lineWidth = 3; c.stroke();
      c.fillStyle = '#ffffff'; c.beginPath(); c.moveTo(-104, -404); c.quadraticCurveTo(0, -418, 104, -404); c.lineTo(96, -366); c.quadraticCurveTo(0, -354, -96, -366); c.closePath(); c.fill(); c.stroke();
      c.strokeStyle = 'rgba(60,60,70,0.3)'; c.lineWidth = 2; for (let k = 0; k < 2; k++) { c.beginPath(); c.moveTo(-98, -396 + k * 12); c.quadraticCurveTo(0, -408 + k * 12, 98, -396 + k * 12); c.stroke(); }
    } else if (hat === 'space') {  // pressure-suit helmet: clear bubble over the head, metal neck ring; cosmo: red "СССР" on the shell
      c.fillStyle = 'rgba(200,220,240,0.16)'; c.beginPath(); c.ellipse(0, -292, 150, 140, 0, 0, 7); c.fill();
      c.strokeStyle = 'rgba(70,70,76,0.85)'; c.lineWidth = 9; c.stroke();
      c.strokeStyle = 'rgba(255,255,255,0.55)'; c.lineWidth = 6; c.beginPath(); c.arc(0, -292, 120, 3.6, 4.4); c.stroke();
      c.fillStyle = '#8a8a90'; c.beginPath(); c.ellipse(0, -198, 128, 22, 0, 0, 7); c.fill(); c.strokeStyle = 'rgba(0,0,0,0.45)'; c.lineWidth = 3; c.stroke();
      if (o.side === 'cosmo') { c.fillStyle = '#c0282d'; c.font = 'bold 30px sans-serif'; c.textAlign = 'center'; c.fillText('СССР', 0, -404); }
    } else if (hat === 'flighthelmet') {  // jet pilot hard helmet: shell over the head and ears, visor housing, o.visor = dark visor down, o.mask = oxygen mask + hose; o.helmCol (USAF grey/white, Soviet ZSh white, IAF olive)
      const col = o.helmCol || { usaf: '#d9dbd6', pvo: '#e6e4dc', iaf: '#7a7c5a', irq: '#c9c9bf', jasdf: '#e4e4dc' }[o.air || 'usaf'];
      const hg = c.createLinearGradient(-130, -470, 130, -260); hg.addColorStop(0, col); hg.addColorStop(1, '#5a5a56'); c.fillStyle = hg;
      c.beginPath(); c.moveTo(-122, -236); c.bezierCurveTo(-140, -500, 140, -500, 122, -236); c.lineTo(96, -236); c.quadraticCurveTo(104, -330, 0, -344); c.quadraticCurveTo(-104, -330, -96, -236); c.closePath(); c.fill(); rim();
      c.fillStyle = 'rgba(0,0,0,0.22)'; c.beginPath(); c.ellipse(0, -360, 98, 22, 0, Math.PI, 0); c.fill();  // visor housing
      if (o.visor) { c.fillStyle = 'rgba(30,34,44,0.88)'; c.beginPath(); c.moveTo(-96, -350); c.quadraticCurveTo(0, -364, 96, -350); c.lineTo(88, -262); c.quadraticCurveTo(0, -244, -88, -262); c.closePath(); c.fill(); c.strokeStyle = 'rgba(255,255,255,0.35)'; c.lineWidth = 5; c.beginPath(); c.moveTo(-60, -334); c.quadraticCurveTo(-40, -300, -56, -276); c.stroke(); }
      if (o.mask) { c.fillStyle = '#4a4c44'; c.beginPath(); c.moveTo(-36, -276); c.quadraticCurveTo(0, -292, 36, -276); c.lineTo(26, -222); c.quadraticCurveTo(0, -210, -26, -222); c.closePath(); c.fill(); c.strokeStyle = '#3a3c36'; c.lineWidth = 12; c.beginPath(); c.moveTo(0, -214); c.quadraticCurveTo(30, -170, 20, -120); c.stroke(); }
      if ((o.air || 'usaf') === 'pvo') star(0, -404, 15, '#c0282d');
    } else if (hat === 'fedora' || hat === 'flatcap') {  // civilian hats
      c.fillStyle = felt(0, -470, 0, -360);
      if (hat === 'fedora') { c.beginPath(); c.ellipse(0, -372, 140, 20, 0, 0, 7); c.fill(); rim(); c.beginPath(); c.moveTo(-78, -374); c.lineTo(-70, -452); c.quadraticCurveTo(0, -430, 70, -452); c.lineTo(78, -374); c.closePath(); c.fill(); rim(); c.fillStyle = '#16120f'; c.fillRect(-78, -396, 156, 16); }
      else { c.fillStyle = '#4a4440'; c.beginPath(); c.ellipse(0, -386, 106, 36, 0, Math.PI, 0); c.quadraticCurveTo(80, -354, 0, -352); c.quadraticCurveTo(-110, -356, -106, -386); c.fill(); rim(); c.fillStyle = '#2e2a26'; c.beginPath(); c.ellipse(20, -356, 92, 14, 0, 0, Math.PI); c.fill(); }
    }
    if (o.binos) { c.fillStyle = '#1a1a1a'; [-18, 18].forEach(bx => { c.beginPath(); c.ellipse(bx, -150, 14, 22, 0, 0, 7); c.fill(); }); c.strokeStyle = '#2a2420'; c.lineWidth = 3; c.beginPath(); c.moveTo(-30, -170); c.lineTo(-60, -210); c.moveTo(30, -170); c.lineTo(60, -210); c.stroke(); }
    if (o.rifle) { c.save(); c.translate(120, -40); c.rotate(-0.18); c.fillStyle = '#5a3a22'; c.fillRect(-9, -220, 18, 250); c.fillStyle = '#2e2e30'; c.fillRect(-4, -360, 8, 150); c.fillRect(6, -230, 16, 6); c.restore(); }
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
  // ---- analysis board (2026-11-14, the 通史3 reference: one frame = one argument). Real photos hang as small exhibits
  // beside diagrams, links and a conclusion, each element on its word (T in REAL seconds; build.py turns @{S146 "vier Jahre"}
  // into scene seconds). One board spans several sentences of the same idea and keeps its elements: later items move,
  // shrink or dim the earlier ones instead of cutting to a new picture. SCENE.images = {key: '/projects/<id>/media/x.jpg'}.
  // items: {k, at, until, id, move:[t0, t1, {x, y, w, h, s}], dim:[t, alpha]} plus per kind:
  //   photo {key, x, y, w, h, cap, sub, fx, fy}       mounted print, caption under it
  //   title {s, x, y, size, align}                      serif heading with a thin rule under it
  //   text  {s, x, y, size, font, color, align}         plain line (font 'body' for small text)
  //   tag   {s, sub, x, y}                              navy label box (the look's tag)
  //   box   {s, sub, x, y, w, h}                        thin-ruled box with centred text (org charts, ideas)
  //   link  {from:[x, y], to:[x, y], arrow, dash, dur, color}   thin line drawn on, optional arrow head
  //   bar   {x, y, w, h, frac, label, value, dur, color}         flat bar that grows (comparisons in time/size)
  //   strike{x0, x1, y, dur}                            red strike-through over a claim that is refuted
  //   ring  {x, y, rx, ry, dur}                         hand-drawn red ellipse around a detail
  //   conclude {s, x, y, size}                          the takeaway: serif line with a red bar on its left
  //   doll  {x, y, h, o:{side, hat, face, ...}}         drawn character (K.doll)
  // 通史3 grammar (2026-11-14, user: "vẽ ghi chú như họ" – our boxes/scales/strike boxes read as PowerPoint):
  //   exhibit {key, x, y, w | maxh, cap, sub, hl:[u0,v0,u1,v1], hlAt, align}  real print at its own aspect + bold caption + grey source; hl = blue box on a document line
  //   note    {x, y, lines:[[text, size], ...]}           big serif year/number then 1-2 short lines, no box
  //   craft   {kind: rocket|missile|sat|ship|tank|plane, x, y, size, side: 1 ink | 2 navy | 3 grey, name, sub: 'USA · 1967 · 2,900 t', mark, o:{stages, boosters}}
  //   legend  {x, y, items:[[1,'American'],[2,'Soviet']], note}   frame {s, x, y, size}  outlined serif word   question {s, sub}  centred question line
  //   Rules: every board has a real exhibit or a craft line-up; text is a few words; no 'box'/'tag'/'strike' chains, no scales, no icons.
  //   ship / tank / plane {x, y, w, color}              flat silhouettes (K.sil)
  board(c, L, T, items) {
    const { C, seg, lerp } = L;
    const geo = it => { let { x, y, w, h } = it, s = 1;
      if (it.move) { const [a, b, to] = it.move, p = seg(T, a, b); x = lerp(x, to.x ?? x, p); y = lerp(y, to.y ?? y, p); w = lerp(w ?? 0, to.w ?? w ?? 0, p); h = lerp(h ?? 0, to.h ?? h ?? 0, p); s = lerp(1, to.s ?? 1, p); }
      return { x, y, w, h, s }; };
    for (const it of items) {
      const at = it.at ?? 0, a0 = seg(T, at, at + 0.45); if (a0 <= 0) continue;
      const out = it.until != null ? 1 - seg(T, it.until, it.until + 0.4) : 1; if (out <= 0) continue;
      let a = a0 * out; if (it.dim && T > it.dim[0]) a *= lerp(1, it.dim[1] ?? 0.35, seg(T, it.dim[0], it.dim[0] + 0.5));
      const g = geo(it), rise = (1 - a0) * 14;
      c.save(); c.globalAlpha *= a;
      if (it.k === 'photo') {
        const m = 9, { x, y, w, h } = g;
        c.fillStyle = 'rgba(60,45,25,0.22)'; c.fillRect(x - m + 8, y - m + 10 + rise, w + 2 * m, h + 2 * m);
        c.fillStyle = L.LOOK && L.LOOK.name === 'dark' ? C.panel : '#F4F1E8'; c.fillRect(x - m, y - m + rise, w + 2 * m, h + 2 * m);
        K.photo(c, L, it.key, x, y + rise, w, h, { fx: it.fx, fy: it.fy, zoom: 1 + 0.03 * L.lin(T, at, at + 12), filter: 'sepia(0.35) contrast(1.05)' });
        if (it.cap) L.text(c, it.cap, x - m, y + h + m + 34 + rise, { size: 28, font: 'head' });
        if (it.sub) L.text(c, it.sub, x - m, y + h + m + 64 + rise, { size: 21, font: 'body', color: C.fg2 });
      } else if (it.k === 'title') {
        const w = L.text(c, it.s, g.x, g.y + rise, { size: it.size || 46, align: it.align || 'left' });
        const x0 = it.align === 'center' ? g.x - w / 2 : g.x;
        L.line(c, [[x0, g.y + 18], [x0 + w, g.y + 18]], seg(T, at + 0.2, at + 0.9), { color: C.rule, width: 2 });
      } else if (it.k === 'text') {
        L.text(c, it.s, g.x, g.y + rise, { size: it.size || 30, font: it.font || 'body', color: it.color || C.fg, align: it.align || 'left' });
      } else if (it.k === 'tag') {
        L.tag(c, it.s, g.x, g.y, T, at, { size: it.size || 30, sub: it.sub, accent: C.accent2, align: it.align });
      } else if (it.k === 'box') {
        const { x, y, w, h } = g; c.fillStyle = C.panel; c.fillRect(x, y + rise, w, h); c.strokeStyle = C.fg; c.lineWidth = 1.6; c.strokeRect(x, y + rise, w, h);
        L.text(c, it.s, x + w / 2, y + h / 2 + (it.sub ? 0 : 11) + rise, { size: it.size || 32, align: 'center' });
        if (it.sub) L.text(c, it.sub, x + w / 2, y + h / 2 + 32 + rise, { size: 20, font: 'body', align: 'center', color: C.fg2 });
      } else if (it.k === 'link') {
        const p = seg(T, at, at + (it.dur ?? 0.8)), pts = [it.from, it.to];
        c.globalAlpha = out * (it.dim && T > it.dim[0] ? it.dim[1] ?? 0.35 : 1);
        L.line(c, pts, p, { color: it.color || C.fg, width: it.width || 2, dash: it.dash ? [8, 7] : undefined });
        if (it.arrow && p > 0.95) { const [x0, y0] = it.from, [x1, y1] = it.to, an = Math.atan2(y1 - y0, x1 - x0);
          c.fillStyle = it.color || C.fg; c.beginPath(); c.moveTo(x1, y1); c.lineTo(x1 - 18 * Math.cos(an - 0.4), y1 - 18 * Math.sin(an - 0.4)); c.lineTo(x1 - 18 * Math.cos(an + 0.4), y1 - 18 * Math.sin(an + 0.4)); c.fill(); }
      } else if (it.k === 'bar') {
        const p = seg(T, at, at + (it.dur ?? 1.2)), { x, y, w, h } = g;
        c.fillStyle = L.FG(0.08); c.fillRect(x, y, w, h); c.fillStyle = it.color || C.fg; c.fillRect(x, y, w * (it.frac ?? 1) * p, h);
        if (it.label) L.text(c, it.label, x, y - 14, { size: 26, font: 'body', color: C.fg2 });
        if (it.value) L.text(c, it.value, x + w * (it.frac ?? 1) * p + 16, y + h * 0.75, { size: it.vsize || 36, alpha: seg(T, at + 0.6, at + 1) });
      } else if (it.k === 'strike') {
        L.line(c, [[it.x0, it.y], [it.x1, it.y]], seg(T, at, at + (it.dur ?? 0.5)), { color: C.accent2, width: 5 });
      } else if (it.k === 'ring') {
        const p = seg(T, at, at + (it.dur ?? 0.7)); c.strokeStyle = C.accent2; c.lineWidth = 4; c.beginPath();
        for (let i = 0; i <= 60 * p; i++) { const u = i / 60 * Math.PI * 2.15 - 0.3, wob = 1 + 0.03 * Math.sin(i * 0.9); c.lineTo(it.x + Math.cos(u) * it.rx * wob, it.y + Math.sin(u) * it.ry * wob); } c.stroke();
      } else if (it.k === 'conclude') {
        const s = it.size || 40; c.fillStyle = C.accent2; c.fillRect(g.x - 22, g.y - s * 0.95 + rise, 5, s * 1.25);
        L.text(c, it.s, g.x, g.y + rise, { size: s });
      } else if (it.k === 'exhibit') {  // 通史3 grammar: a real print kept at its own aspect, thin light mat, bold caption + grey source line
        const im = IMG[it.key]; if (im) {
          let w = g.w || 520, h = it.h || w * im.height / im.width; if (it.maxh && h > it.maxh) { h = it.maxh; w = h * im.width / im.height; }
          const x = it.align === 'right' ? g.x - w : g.x, y = g.y + rise, m = 7;
          c.fillStyle = 'rgba(60,45,25,0.16)'; c.fillRect(x - m + 5, y - m + 7, w + 2 * m, h + 2 * m);
          c.fillStyle = L.LOOK && L.LOOK.name === 'dark' ? C.panel : '#F5F2EA'; c.fillRect(x - m, y - m, w + 2 * m, h + 2 * m);
          K.photo(c, L, it.key, x, y, w, h, { zoom: 1 + 0.02 * L.lin(T, at, at + 14), filter: it.filter || 'grayscale(0.85) sepia(0.25) contrast(1.05)', fx: it.fx, fy: it.fy });
          if (it.hl) { const [u0, v0, u1, v1] = it.hl, p = seg(T, it.hlAt ?? at + 0.8, (it.hlAt ?? at + 0.8) + 0.5); c.strokeStyle = C.accent; c.lineWidth = 3; c.globalAlpha *= p;
            c.strokeRect(x + u0 * w, y + v0 * h, (u1 - u0) * w, (v1 - v0) * h); }
          if (it.cap) L.text(c, it.cap, x, y + h + m + 38, { size: it.capSize || 30 });
          if (it.sub) L.text(c, it.sub, x, y + h + m + 68, { size: 20, font: 'body', color: C.fg2 });
        }
      } else if (it.k === 'note') {  // big serif year/number, then short lines (no boxes): {lines: [['1969', 56], ['N1 vs Saturn V', 34]], gap}
        let y = g.y + rise; (it.lines || []).forEach(([s, size, col], i) => { const sz = size || (i ? 34 : 54); L.text(c, s, g.x, y, { size: sz, color: col || (i ? C.fg : C.fg), align: it.align || 'left', font: it.font }); y += sz * 1.35 + (it.gap || 4); });
      } else if (it.k === 'craft') {  // flat silhouette of the real object + name + 'country · year · spec' (通史3 ship line-up)
        const col = it.side === 2 ? C.accent : it.side === 3 ? L.FG(0.35) : C.fg;
        K.craft(c, it.kind || 'rocket', g.x, g.y + rise, it.size || 200, col, it.o || {});
        if (it.name) L.text(c, it.name, g.x, g.y + 46 + rise, { size: it.nsize || 30, align: 'center', color: it.side === 2 ? C.accent : C.fg });
        if (it.sub) L.text(c, it.sub, g.x, g.y + 76 + rise, { size: 20, font: 'body', align: 'center', color: it.side === 2 ? C.accent : C.fg2 });
        if (it.mark) { L.text(c, it.mark, g.x, g.y - (it.size || 200) - 34 + rise, { size: 36, align: 'center' }); }
      } else if (it.k === 'legend') {  // small squares + words, bottom-left under a line-up
        (it.items || []).forEach(([side, s], i) => { const x = g.x + i * (it.step || 170); c.fillStyle = side === 2 ? C.accent : side === 3 ? L.FG(0.35) : C.fg; c.fillRect(x, g.y - 16, 22, 16); L.text(c, s, x + 32, g.y, { size: 22, font: 'body' }); });
        if (it.note) L.text(c, it.note, g.x, g.y + 30, { size: 19, font: 'body', color: C.fg2 });
      } else if (it.k === 'frame') {  // outlined serif label (the reference's 「買」/「局外中立」 boxes): ink outline, no fill colour
        c.font = `${it.size || 40}px ${L.FONT ? L.FONT.head : 'serif'}`; const tw = L.text(c, it.s, -9999, -9999, { size: it.size || 40 }), pad = 14;
        c.strokeStyle = C.fg; c.lineWidth = 2; c.strokeRect(g.x - tw / 2 - pad, g.y - (it.size || 40) * 0.95 + rise, tw + 2 * pad, (it.size || 40) * 1.35);
        L.text(c, it.s, g.x, g.y + rise, { size: it.size || 40, align: 'center' });
      } else if (it.k === 'question') {  // the reference's question frame: one centred serif line, nothing else
        L.text(c, it.s, g.x || 960, (g.y || 470) + rise, { size: it.size || 64, align: 'center' });
        if (it.sub) L.text(c, it.sub, g.x || 960, (g.y || 470) + 56 + rise, { size: 24, font: 'body', align: 'center', color: C.fg2 });
      } else if (it.k === 'doll') {
        K.doll(c, L, g.x, g.y, it.h || 220, T, it.o || {});
      } else if (['ship', 'tank', 'plane'].includes(it.k) && K.sil) {
        K.sil(c, it.k, g.x, g.y + rise, it.w || 220, it.color || C.fg);
      }
      c.restore();
    }
  },
  // flat silhouettes of real hardware for 通史3-style line-ups: (x, y) = base centre, size = height (rockets) or length (others)
  craft(c, kind, x, y, size, col, o = {}) {
    c.save(); c.translate(x, y); c.fillStyle = col;
    if (kind === 'rocket' || kind === 'missile') {  // o.stages [[width frac, height frac], ...] bottom-up, o.fins, o.boosters (R-7), o.cone
      const H = size, st = o.stages || (kind === 'missile' ? [[0.1, 0.62], [0.085, 0.24]] : [[0.13, 0.36], [0.13, 0.27], [0.1, 0.15], [0.07, 0.12]]); let yy = 0;
      st.forEach(([wf, hf]) => { const w = wf * H, h = hf * H; c.fillRect(-w / 2, yy - h, w, h); yy -= h; });
      const tw = st[st.length - 1][0] * H; c.beginPath(); c.moveTo(-tw / 2, yy); c.lineTo(0, yy - (o.cone ?? 0.1) * H); c.lineTo(tw / 2, yy); c.fill();
      if (o.boosters) { const bw = st[0][0] * H * 0.55; [-1, 1].forEach(sd => { c.beginPath(); c.moveTo(sd * st[0][0] * H / 2, 0); c.lineTo(sd * (st[0][0] * H / 2 + bw), 0); c.lineTo(sd * st[0][0] * H / 2, -H * 0.42); c.fill(); }); }
      if (o.fins !== false) { const w0 = st[0][0] * H; [-1, 1].forEach(sd => { c.beginPath(); c.moveTo(sd * w0 / 2, 0); c.lineTo(sd * (w0 / 2 + H * 0.035), 0); c.lineTo(sd * w0 / 2, -H * 0.07); c.fill(); }); }
    } else if (kind === 'sat') { const s = size / 200; c.scale(s, s); c.fillRect(-30, -60, 60, 60); c.fillRect(-120, -42, 80, 24); c.fillRect(40, -42, 80, 24); c.fillRect(-4, -80, 8, 20); }
    else { c.restore(); return K.sil(c, kind, x, y, size, col); }
    c.restore();
  },
  // flat silhouettes for boards (side view, facing right; (x, y) = waterline/ground centre, w = length)
  sil(c, kind, x, y, w, col) {
    c.save(); c.translate(x, y); const s = w / 200; c.scale(s, s); c.fillStyle = col; c.beginPath();
    if (kind === 'ship') { c.moveTo(-100, -14); c.lineTo(96, -14); c.lineTo(104, -26); c.lineTo(90, 6); c.lineTo(-92, 6); c.closePath(); c.fill();
      c.fillRect(-40, -34, 60, 20); c.fillRect(-14, -58, 14, 26); c.fillRect(30, -40, 6, 26); c.fillRect(-70, -44, 4, 30); c.fillRect(56, -24, 34, 6); }
    else if (kind === 'tank') { c.fillRect(-90, -30, 180, 34); c.beginPath(); c.ellipse(0, 6, 92, 16, 0, 0, 7); c.fill(); c.fillRect(-40, -58, 80, 30); c.fillRect(40, -48, 80, 8); }
    else { c.beginPath(); c.ellipse(0, 0, 100, 12, 0, 0, 7); c.fill(); c.beginPath(); c.moveTo(-10, 0); c.lineTo(20, -6); c.lineTo(-30, -70); c.lineTo(-50, -70); c.closePath(); c.fill(); c.beginPath(); c.moveTo(-90, 0); c.lineTo(-100, -30); c.lineTo(-84, -30); c.lineTo(-70, 0); c.fill(); }
    c.restore();
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
