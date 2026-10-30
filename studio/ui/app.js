/* Studio phim tài liệu: preview player, multi-track timeline, media/audio libraries, text, motion, effects, transitions,
   colour, voice recording, review notes, preview renders and export. Plain JS, no build.
   The server (studio/server.py) owns timeline.json; every edit goes through /api/ops or PUT /api/timeline with the ETag,
   so edits from the agent (MCP) and from here never overwrite each other. Sliders show a draft frame (POST /api/frame)
   and save when released. */
'use strict';
const $ = s => document.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'class') e.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(e.style, v);
    else if (v !== undefined && v !== null && v !== false) e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
};

const TRACK_STYLE = {
  video: { name: 'Cảnh', h: 46, color: '#5b6cff', order: 0 },
  overlay: { name: 'Chữ / thẻ', h: 30, color: '#d9a53a', order: 1 },
  fx: { name: 'Hiệu ứng', h: 28, color: '#c25fd6', order: 2 },
  voice: { name: 'Lời đọc', h: 40, color: '#3fa36b', order: 3, locked: true },
  music: { name: 'Nhạc', h: 34, color: '#2f9bb3', order: 4 },
  original: { name: 'Nền', h: 26, color: '#8a74c4', order: 5 },
  sfx: { name: 'Tiếng động', h: 30, color: '#d0613f', order: 6 },
};
const AUDIO = ['voice', 'music', 'original', 'sfx'];
const RULER = 28;
const S = {
  proj: null, tl: null, etag: null, sentences: [], snapT: [], snapA: [], t: 0, playing: false, sel: null, multi: new Set(),
  pps: 8, view0: 0, mute: {}, solo: {}, locked: {}, noting: false, undo: [], redo: [], busy: 0, dirty: [], noteFilter: 'all',
  peaks: {}, thumbs: {}, jobsSeen: {}, cat: null, tab: 'media', lib: {}, libScope: 'project', libQuery: '', draft: null,
};

// ------------------------------------------------------------------ utils
const fps = () => (S.tl ? S.tl.fps : 24);
const dur = () => (S.tl ? S.tl.duration : 1);
const snapF = t => Math.round(t * fps()) / fps();
function tc(t) {
  t = Math.max(0, t); const f = Math.round(t * fps()); const F = f % fps(), s = Math.floor(f / fps());
  return `${Math.floor(s / 3600)}:${String(Math.floor(s / 60) % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}:${String(F).padStart(2, '0')}`;
}
const mmss = t => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, '0')}`;
function toast(msg, err = false) {
  const d = h('div', { class: err ? 'err' : '' }, msg); $('#toast').append(d); setTimeout(() => d.remove(), err ? 7000 : 3500);
}
async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  const ct = r.headers.get('Content-Type') || '';
  const body = ct.includes('json') ? await r.json() : await r.arrayBuffer();
  if (!r.ok) { const e = new Error((body && (body.message || body.error)) || r.statusText); e.status = r.status; e.body = body; throw e; }
  return { body, r };
}
const post = (path, obj) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(obj) });
const styleOf = tr => TRACK_STYLE[tr.kind === 'fx' ? 'fx' : tr.id] || { name: tr.name || tr.id, h: 30, color: '#888', order: 9 };
const trackRows = () => S.tl.tracks.slice().sort((a, b) => styleOf(a).order - styleOf(b).order || S.tl.tracks.indexOf(a) - S.tl.tracks.indexOf(b));
const tracksById = () => Object.fromEntries(S.tl.tracks.map(t => [t.id, t]));
function findClip(id) {
  for (const tr of S.tl.tracks) for (const c of tr.clips) if (c.id === id) return [tr, c];
  return [null, null];
}
function selected() { return [...new Set([S.sel, ...S.multi])].filter(Boolean).map(findClip).filter(x => x[1]); }
const selectedOn = pred => selected().filter(([tr]) => pred(tr));
function setSave(state, text) { const p = $('#saveState'); p.className = 'pill ' + state; p.textContent = text; }
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
const fileName = s => (s || '').split('/').pop();

// ------------------------------------------------------------------ load
async function loadProject() {
  const { body: p } = await api('/api/project'); S.proj = p; S.dirty = p.dirty || [];
  $('#projTitle').textContent = p.title;
  $('#projMeta').textContent = `${p.id} · ${tc(p.duration)} · ${p.fps} fps` + (p.picture ? '' : ' · chưa có picture.mp4');
  $('#verPill').textContent = `bản ${p.history_count ?? (p.history || []).length}`;
  document.title = `${p.title} — Studio`;
  if (p.picture && !$('#vid').src) $('#vid').src = '/picture.mp4';
}
async function loadTimeline(why) {
  const r = await fetch('/api/timeline'); S.tl = await r.json(); S.etag = r.headers.get('ETag').replace(/"/g, '');
  if (why) toast(why);
  setSave('ok', 'Đã lưu');
  afterTimeline();
}
async function loadTiming() {
  const { body } = await api('/api/timing'); S.sentences = body.sentences.sort((a, b) => a.start - b.start);
  const pts = [];
  for (const s of S.sentences) {
    pts.push([s.start, `câu ${s.id}`], [s.end, `hết ${s.id}`]);
    s.words.forEach((w, i) => { if (i) pts.push([w[0], `“${w[2]}”`]); });
  }
  pts.sort((a, b) => a[0] - b[0]); S.snapT = pts.map(p => p[0]); S.snapA = pts.map(p => p[1]);
}
function afterTimeline() {
  if (S.sel && !findClip(S.sel)[1]) S.sel = null;
  for (const id of [...S.multi]) if (!findClip(id)[1]) S.multi.delete(id);
  S.draft = null; $('#draftTag').classList.add('hidden'); cueAt = -1;
  buildHeads(); resizeTL(); renderPanel(true); renderInspector(); requestFrame(true); audio.invalidate(); drawNotesOnFrame();
  const open = (S.tl.review_notes || []).filter(n => n.status !== 'done').length;
  $('#noteCount').textContent = open; $('#noteCount').style.display = open ? '' : 'none';
}

// ------------------------------------------------------------------ edits
async function ops(list, label) {
  const before = JSON.stringify(S.tl);
  S.busy++; setSave('busy', 'Đang lưu…');
  try {
    const { body } = await api('/api/ops', { method: 'POST', headers: { 'Content-Type': 'application/json', 'If-Match': S.etag }, body: JSON.stringify({ ops: list }) });
    S.undo.push(before); S.redo = []; if (S.undo.length > 100) S.undo.shift();
    S.tl = body.timeline; S.etag = body.etag; S.dirty = body.dirty || [];
    setSave('ok', 'Đã lưu'); afterTimeline(); bumpVersion();
    if (label) toast(label + (body.kind === 'audio' ? ' · chỉ đổi tiếng (xuất nhanh)' : body.kind === 'picture' ? ' · đổi hình (đoạn này dựng lại khi xuất)' : ''));
    return body;
  } catch (e) {
    if (e.status === 412) { setSave('err', 'Xung đột'); toast('Timeline vừa được sửa ở nơi khác (agent?). Đã tải bản mới, hãy thao tác lại.', true); await loadTimeline(); await refreshProject(); }
    else { setSave('err', 'Lỗi'); toast('Không lưu được: ' + e.message, true); await loadTimeline(); }
  } finally { S.busy--; }
}
function bumpVersion() { const m = $('#verPill').textContent.match(/\d+/); $('#verPill').textContent = `bản ${(m ? +m[0] : 0) + 1}`; }
async function putTimeline(json, why) {
  S.busy++; setSave('busy', 'Đang lưu…');
  try {
    const { body } = await api('/api/timeline', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'If-Match': S.etag, 'X-Why': why }, body: json });
    S.etag = body.etag; S.tl = JSON.parse(json); setSave('ok', 'Đã lưu'); afterTimeline(); bumpVersion(); await refreshProject(); return true;
  } catch (e) {
    if (e.status === 412) { toast('Không hoàn tác được: timeline vừa được sửa ở nơi khác. Đã tải bản mới.', true); await loadTimeline(); }
    else toast('Lỗi lưu: ' + e.message, true);
    return false;
  } finally { S.busy--; }
}
async function undo() {
  if (!S.undo.length) return toast('Không còn gì để hoàn tác');
  const cur = JSON.stringify(S.tl); const prev = S.undo.pop();
  if (await putTimeline(prev, 'undo')) { S.redo.push(cur); toast('Đã hoàn tác'); } else S.undo.push(prev);
}
async function redo() {
  if (!S.redo.length) return;
  const cur = JSON.stringify(S.tl); const nxt = S.redo.pop();
  if (await putTimeline(nxt, 'redo')) { S.undo.push(cur); toast('Đã làm lại'); } else S.redo.push(nxt);
}
async function refreshProject() {
  try { const { body } = await api('/api/project'); S.proj = body; S.dirty = body.dirty || []; drawTL(); if (['build', 'log'].includes(S.tab)) renderPanel(); } catch (e) { /* server restarting */ }
}
function splitSel() {
  const [tr, c] = findClip(S.sel || '');
  let target = c;
  if (!target || !(c.start < S.t && S.t < c.end)) {
    const tid = tr ? tr.id : 'video';
    target = (tracksById()[tid] || { clips: [] }).clips.find(x => x.start < S.t && S.t < x.end);
  }
  if (!target) return toast('Đặt đầu phát lên một clip để tách', true);
  if (findClip(target.id)[0].id === 'voice') return toast('Lời đọc khoá: sửa giọng bằng doc.py', true);
  ops([{ op: 'split', id: target.id, t: S.t }], `Đã tách ${target.id}`);
}
function deleteSel() {
  const list = selected().filter(([tr]) => tr.id !== 'voice');
  if (!list.length) return;
  ops(list.map(([, c]) => ({ op: 'delete', id: c.id })), `Đã xoá ${list.length} clip`); S.sel = null; S.multi.clear();
}
function select(id, add) {
  if (add) { if (S.multi.has(id) || S.sel === id) { S.multi.delete(id); if (S.sel === id) S.sel = [...S.multi][0] || null; } else { if (S.sel) S.multi.add(S.sel); S.sel = id; S.multi.add(id); } }
  else { S.sel = id; S.multi = new Set(id ? [id] : []); }
  renderInspector(); if (['motion', 'color', 'trans', 'effects', 'text', 'audio'].includes(S.tab)) renderPanel(); drawTL();
}

// ------------------------------------------------------------------ audio monitor (WebAudio, server-mixed windows)
const audio = {
  ctx: null, master: null, an: null, chunk: 10, pre: 3, cache: new Map(), srcs: [], t0: 0, c0: 0, next: 0, gainDb: 0, timer: null,
  init() {
    if (this.ctx) return;
    const ctx = this.ctx = new AudioContext({ sampleRate: 48000 });
    this.master = ctx.createGain(); this.master.connect(ctx.destination);
    const hs = ctx.createBiquadFilter(); hs.type = 'highshelf'; hs.frequency.value = 1681; hs.gain.value = 4;  // K-weighting (BS.1770)
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 38; hp.Q.value = 0.5;
    this.an = ctx.createAnalyser(); this.an.fftSize = 16384;
    this.peakAn = ctx.createAnalyser(); this.peakAn.fftSize = 2048;
    this.master.connect(hs); hs.connect(hp); hp.connect(this.an); this.master.connect(this.peakAn);
  },
  only() {
    const solo = AUDIO.filter(t => S.solo[t]); const on = solo.length ? solo : AUDIO.filter(t => !S.mute[t]);
    return on.length === AUDIO.length ? null : on.join(',');
  },
  key(i) { return `${S.etag}|${this.only()}|${i}`; },
  invalidate() { for (const k of [...this.cache.keys()]) if (!k.startsWith(S.etag + '|')) this.cache.delete(k); },
  async get(i) {
    const k = this.key(i);
    if (this.cache.has(k)) return this.cache.get(k);
    const p = (async () => {
      const a = i * this.chunk, b = Math.min(dur(), a + this.chunk), pre = Math.min(this.pre, a);
      const only = this.only();
      const r = await fetch(`/api/audio?t0=${(a - pre).toFixed(3)}&t1=${b.toFixed(3)}` + (only !== null ? `&only=${only}` : ''));
      if (!r.ok) throw new Error('audio ' + r.status);
      this.gainDb = parseFloat(r.headers.get('X-Gain-Db') || '0');
      const buf = await this.ctx.decodeAudioData(await r.arrayBuffer());
      return { buf, a, b, pre };
    })();
    this.cache.set(k, p); if (this.cache.size > 40) this.cache.delete(this.cache.keys().next().value);
    p.catch(() => this.cache.delete(k));
    return p;
  },
  now() { return S.playing ? this.t0 + (this.ctx.currentTime - this.c0) : S.t; },
  async play(from) {
    this.init(); await this.ctx.resume(); this.stopSources();
    const i0 = Math.floor(from / this.chunk);
    setSave('busy', 'Đang trộn…');
    let first;
    try { first = await this.get(i0); } catch (e) { toast('Không trộn được tiếng: ' + e.message, true); stop(); return; }
    setSave('ok', 'Đã lưu');
    if (!S.playing) return;
    this.master.gain.value = Math.pow(10, this.gainDb / 20);
    this.t0 = from; this.c0 = this.ctx.currentTime + 0.05; this.next = i0;
    this.schedule(first); this.next = i0 + 1;
    clearInterval(this.timer); this.timer = setInterval(() => this.pump(), 250); this.pump();
  },
  schedule(ch) {
    const when = this.c0 + (ch.a - this.t0); const now = this.ctx.currentTime;
    let off = ch.pre, len = ch.b - ch.a, at = when;
    if (ch.a < this.t0) { off += this.t0 - ch.a; len -= this.t0 - ch.a; at = this.c0; }
    if (at < now) { const late = now - at; off += late; len -= late; at = now; }
    if (len <= 0.01) return;
    const src = this.ctx.createBufferSource(); src.buffer = ch.buf; src.connect(this.master); src.start(at, off, len);
    this.srcs.push(src); src.onended = () => { this.srcs = this.srcs.filter(s => s !== src); };
  },
  pump() {
    if (!S.playing) return;
    const ahead = this.now() + 14;
    while (this.next * this.chunk < Math.min(ahead, dur())) {
      const i = this.next++; const tag = this.key(i);
      this.get(i).then(ch => { if (S.playing && tag === this.key(i)) this.schedule(ch); }).catch(e => toast('Thiếu tiếng đoạn ' + mmss(i * this.chunk) + ': ' + e.message, true));
    }
    if (this.now() >= dur()) stop();
  },
  stopSources() { for (const s of this.srcs) { try { s.stop(); } catch (e) { /* already stopped */ } } this.srcs = []; clearInterval(this.timer); },
  meter() {
    if (!this.an || !S.playing) return null;
    const a = new Float32Array(this.an.fftSize); this.an.getFloatTimeDomainData(a);
    let ms = 0; for (const x of a) ms += x * x; ms /= a.length;
    const p = new Float32Array(this.peakAn.fftSize); this.peakAn.getFloatTimeDomainData(p);
    let pk = 0; for (const x of p) pk = Math.max(pk, Math.abs(x));
    return { lufs: -0.691 + 10 * Math.log10(2 * ms + 1e-12), peak: 20 * Math.log10(pk + 1e-9) };
  },
};
function play() {
  if (S.playing) return stop();
  if (S.t >= dur() - 0.1) S.t = 0;
  $('#auPreview').pause();
  S.playing = true; $('#bPlay').textContent = '❚❚'; audio.play(S.t); tick();
}
function stop() {
  if (!S.playing) return;
  S.t = snapF(audio.now()); S.playing = false; $('#bPlay').textContent = '▶'; audio.stopSources();
  const v = $('#vid'); v.pause(); v.classList.remove('show'); requestFrame(true); drawTL(); updateTC();
  drawMeter(); $('#meterTxt').textContent = '– LUFS';
}
function seek(t) {
  t = Math.max(0, Math.min(dur(), t));
  if (S.playing) { S.t = t; audio.play(t); } else { S.t = snapF(t); requestFrame(true); }
  updateTC(); drawTL(); followPlayhead();
  if (!S.playing) { drawNotesOnFrame(); if (S.tab === 'speech') highlightSentence(); if (!S.sel) renderInspector(); }
}
function followPlayhead() {
  const w = laneW(); const x = (S.t - S.view0) * S.pps;
  if (x < 0 || x > w - 40) { S.view0 = Math.max(0, S.t - (w * 0.15) / S.pps); drawTL(); }
}

// ------------------------------------------------------------------ frames
const frameCv = $('#frame'), fctx = frameCv.getContext('2d');
let frameBusy = false, frameWant = null, lastFrameT = -1;
function requestFrame(force) { frameWant = { t: S.t, force }; pumpFrame(); }
async function pumpFrame() {
  if (frameBusy || !frameWant || !S.tl) return;
  const want = frameWant; frameWant = null;
  if (!want.force && Math.abs(want.t - lastFrameT) < 1e-4) return;
  frameBusy = true;
  try {
    const w = S.playing ? 960 : 1280;
    const r = S.draft && !S.playing
      ? await fetch('/api/frame', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ t: want.t, w, ops: S.draft }) })
      : await fetch(`/api/frame?t=${want.t.toFixed(4)}&w=${w}&e=${S.etag}`);
    if (r.ok) {
      const bmp = await createImageBitmap(await r.blob());
      if (frameCv.width !== bmp.width) { frameCv.width = bmp.width; frameCv.height = bmp.height; }
      fctx.drawImage(bmp, 0, 0); lastFrameT = want.t;
      $('#frameTag').textContent = frameLabel(want.t);
      if (!S.playing) refreshCue();
    } else if (S.draft) { toast('Không xem nháp được: ' + (await r.text()).slice(0, 120), true); }
  } catch (e) { /* server busy */ }
  frameBusy = false;
  if (frameWant) pumpFrame();
}
/* draft = ops applied to a copy on the server for the preview frame only; the slider's change event saves them. */
function draft(list) { S.draft = list; $('#draftTag').classList.remove('hidden'); requestFrame(true); }
function clearDraft() { S.draft = null; $('#draftTag').classList.add('hidden'); }
function frameLabel(t) {
  const v = clipAt('video', t); const o = S.tl.tracks.filter(tr => tr.id === 'overlay' || tr.kind === 'fx').flatMap(tr => tr.clips).filter(c => c.start <= t && t < c.end);
  return [v && v.id, ...o.map(c => c.id + ' ' + c.type), isDirty(t) ? 'đã sửa hình' : ''].filter(Boolean).join(' · ');
}
function clipAt(tid, t) {
  const cs = (tracksById()[tid] || { clips: [] }).clips; let best = null;
  for (const c of cs) if (c.start <= t && (tid === 'video' || t < c.end)) best = c;
  return best;
}
const isDirty = t => (S.dirty || []).some(([a, b]) => a <= t && t < b);

function tick() {
  if (!S.playing) return;
  const t = audio.now(); S.t = t; updateTC();
  const v = $('#vid');
  const useVid = $('#smooth').checked && S.proj.picture && !isDirty(t) && !isDirty(t + 0.5);
  if (useVid) {
    if (v.paused || Math.abs(v.currentTime - t) > 0.25) { v.currentTime = t; v.play().catch(() => {}); }
    v.classList.add('show'); $('#frameTag').textContent = frameLabel(t) + ' · picture.mp4';
  } else {
    if (!v.paused) v.pause(); v.classList.remove('show');
    if (!frameBusy) { frameWant = { t: t + 0.12, force: true }; pumpFrame(); }
  }
  if ((S.t - S.view0) * S.pps > laneW() - 30) { S.view0 = S.t - 30 / S.pps; }
  drawTL(); drawMeter(); drawNotesOnFrame();
  requestAnimationFrame(tick);
}
function updateTC() { $('#tc').textContent = tc(S.t); }
function drawMeter() {
  const m = audio.meter(); const cv = $('#meterBar'), g = cv.getContext('2d'), W = cv.width, H = cv.height;
  g.fillStyle = '#0e1014'; g.fillRect(0, 0, W, H);
  const x = v => Math.max(0, Math.min(W, ((v + 48) / 48) * W));
  g.fillStyle = '#2c313b'; for (const d of [-36, -24, -18, -12, -6]) g.fillRect(x(d), 0, 1, H);
  if (m) {
    g.fillStyle = m.lufs > -10 ? '#e0533f' : m.lufs > -16 ? '#b8f03c' : '#3fa36b'; g.fillRect(0, 2, x(m.lufs), H / 2 - 2);
    g.fillStyle = m.peak > -1 ? '#e0533f' : '#8b93a1'; g.fillRect(0, H / 2 + 1, x(m.peak), H / 2 - 3);
    $('#meterTxt').textContent = `M ${m.lufs.toFixed(1)} LUFS · đỉnh ${m.peak.toFixed(1)} dB`;
  }
  g.fillStyle = '#fff'; g.fillRect(x(-14), 0, 2, H);
}

// ------------------------------------------------------------------ notes on the frame
const noteLayer = $('#noteLayer');
function drawNotesOnFrame() {
  noteLayer.innerHTML = '';
  for (const n of S.tl.review_notes || []) {
    if (Math.abs(n.t - S.t) > 1.5 || (n.status === 'done' && !S.noting)) continue;
    const [x, y, w, hh] = n.rect || [0, 0, 1, 1];
    noteLayer.append(h('div', { class: 'nrect' + (n.status === 'done' ? ' done' : ''), style: `left:${x * 100}%;top:${y * 100}%;width:${w * 100}%;height:${hh * 100}%` }, h('span', {}, `${n.id} · ${n.text}`)));
  }
}
function setNoting(on) {
  S.noting = on; $('#frameBox').classList.toggle('noting', on); $('#btnNotesMode').classList.toggle('on', on);
  if (on) { stop(); switchTab('notes'); toast('Chế độ góp ý: kéo khung trên hình rồi gõ góp ý. Esc để thoát.'); }
  $('#noteBox').classList.add('hidden'); drawNotesOnFrame();
}
let drag = null, pendingRect = null;
noteLayer.addEventListener('pointerdown', e => {
  if (!S.noting) return;
  const b = noteLayer.getBoundingClientRect(); const x = (e.clientX - b.left) / b.width, y = (e.clientY - b.top) / b.height;
  const el = h('div', { class: 'nrect', style: `left:${x * 100}%;top:${y * 100}%;width:0;height:0` }); noteLayer.append(el);
  drag = { x, y, el, b }; noteLayer.setPointerCapture(e.pointerId);
});
noteLayer.addEventListener('pointermove', e => {
  if (!drag) return;
  const { b } = drag; const x = Math.max(0, Math.min(1, (e.clientX - b.left) / b.width)), y = Math.max(0, Math.min(1, (e.clientY - b.top) / b.height));
  drag.r = [Math.min(x, drag.x), Math.min(y, drag.y), Math.abs(x - drag.x), Math.abs(y - drag.y)];
  Object.assign(drag.el.style, { left: drag.r[0] * 100 + '%', top: drag.r[1] * 100 + '%', width: drag.r[2] * 100 + '%', height: drag.r[3] * 100 + '%' });
});
noteLayer.addEventListener('pointerup', e => {
  if (!drag) return;
  let r = drag.r; if (!r || r[2] < 0.01 || r[3] < 0.01) r = [0.02, 0.02, 0.96, 0.96];
  pendingRect = { r: r.map(v => +v.toFixed(4)), t: S.t };
  const box = $('#noteBox'); box.classList.remove('hidden');
  box.style.left = Math.min(window.innerWidth - 360, e.clientX + 10) + 'px'; box.style.top = Math.min(window.innerHeight - 160, e.clientY + 10) + 'px';
  $('#noteText').value = ''; $('#noteText').focus(); drag = null;
});
async function saveNote() {
  const text = $('#noteText').value.trim(); if (!text || !pendingRect) return;
  try {
    const { body } = await post('/api/notes', { op: 'add', t: pendingRect.t, rect: pendingRect.r, text });
    toast(`Đã lưu góp ý ${body.note.id}`); $('#noteBox').classList.add('hidden'); pendingRect = null; await loadTimeline(); switchTab('notes');
  } catch (e) { toast('Không lưu được góp ý: ' + e.message, true); }
}
async function noteOp(op) {
  try { await post('/api/notes', op); await loadTimeline(); } catch (e) { toast('Lỗi góp ý: ' + e.message, true); }
}

// ------------------------------------------------------------------ subtitles: click the cue on the preview to edit it
/* Edits are stored in timeline.json ("subtitle_overrides", keyed by the cue's original start in ms); voice.srt stays
   untouched, and only the edited cue's range is re-rendered at export. */
let curCue = null, cueAt = -1, subEdit = null;
async function refreshCue() {
  if (S.playing || !S.tl || !(S.tl.fx || {}).subtitles) { curCue = null; return; }
  const t = S.t; if (Math.abs(t - cueAt) < 1e-4 && curCue !== undefined) return;
  try { const { body } = await api(`/api/subtitle?t=${t.toFixed(4)}`); curCue = body.cue; cueAt = t; } catch (e) { curCue = null; }
}
function frameXY(e) { const b = $('#frameBox').getBoundingClientRect(); return [(e.clientX - b.left) / b.width, (e.clientY - b.top) / b.height]; }
const inBox = ([x, y], bx, m = 0.01) => bx && x >= bx[0] - m && x <= bx[0] + bx[2] + m && y >= bx[1] - m && y <= bx[1] + bx[3] + m;
$('#frameBox').addEventListener('mousemove', e => {
  const hint = $('#subHint'); const on = !S.noting && !S.playing && curCue && inBox(frameXY(e), curCue.box);
  $('#frameBox').classList.toggle('subhover', !!on);
  if (on) { const [x, y, w, hh] = curCue.box; Object.assign(hint.style, { display: 'block', left: x * 100 + '%', top: y * 100 + '%', width: w * 100 + '%', height: hh * 100 + '%' }); }
  else hint.style.display = 'none';
});
$('#frameBox').addEventListener('mouseleave', () => { $('#subHint').style.display = 'none'; });
$('#frameBox').addEventListener('click', async e => {
  if (S.noting || S.playing) return;
  await refreshCue();
  if (curCue && inBox(frameXY(e), curCue.box, 0.03)) openSubEditor(curCue, e.clientX, e.clientY);
});
function openSubEditor(cue, cx, cy) {
  subEdit = { key: cue.key, orig: cue.orig };
  $('#subText').value = cue.text; $('#subStart').value = (+cue.start).toFixed(3); $('#subEnd').value = (+cue.end).toFixed(3);
  $('#subMeta').textContent = ` ${tc(cue.start)} → ${tc(cue.end)}`;
  $('#subOrig').textContent = cue.edited ? `Gốc: “${cue.orig.text}” (${tc(cue.orig.start)} → ${tc(cue.orig.end)})` : 'Chữ gốc từ voice.srt. Sửa ở đây không đụng tới voice.srt.';
  const box = $('#subBox'); box.classList.remove('hidden');
  const b = $('#frameBox').getBoundingClientRect();
  box.style.left = Math.max(8, Math.min(window.innerWidth - 430, (cx ?? b.left + b.width / 2) - 210)) + 'px';
  box.style.top = Math.max(50, Math.min(window.innerHeight - 260, (cy ?? b.bottom) - 250)) + 'px';
  $('#subText').focus(); $('#subText').select();
}
function closeSubEditor() { $('#subBox').classList.add('hidden'); subEdit = null; clearDraft(); requestFrame(true); }
function subOp(extra) {
  const op = { op: 'subtitle', key: subEdit.key, ...extra };
  return op;
}
const subLive = debounce(() => { if (subEdit) draft([subOp({ text: $('#subText').value })]); }, 350);
$('#subText').addEventListener('input', subLive);
async function saveSub(fields, label) {
  if (!subEdit) return;
  const o = subEdit.orig; const f = { ...fields };
  for (const k of ['start', 'end']) if (f[k] != null && Math.abs(f[k] - o[k]) < 1e-3) delete f[k];
  const same = (f.text === undefined || f.text === o.text) && f.start === undefined && f.end === undefined;
  const op = same ? subOp({ reset: true }) : subOp(f);
  closeSubEditor(); await ops([op], label); cueAt = -1; refreshCue();
  if (S.tab === 'speech') renderPanel();
}
$('#subSave').onclick = () => saveSub({ text: $('#subText').value.replace(/\s+$/, ''), start: parseFloat($('#subStart').value), end: parseFloat($('#subEnd').value) }, 'Đã sửa phụ đề');
$('#subHide').onclick = () => saveSub({ text: '' }, 'Đã ẩn câu phụ đề');
$('#subReset').onclick = () => { const k = subEdit && subEdit.key; closeSubEditor(); ops([{ op: 'subtitle', key: k, reset: true }], 'Phụ đề về bản gốc').then(() => { cueAt = -1; refreshCue(); if (S.tab === 'speech') renderPanel(); }); };
$('#subClose').onclick = closeSubEditor;
$('#subStartNow').onclick = () => { $('#subStart').value = S.t.toFixed(3); };
$('#subEndNow').onclick = () => { $('#subEnd').value = S.t.toFixed(3); };

// ------------------------------------------------------------------ timeline canvas
const tlCv = $('#tl'), tctx = tlCv.getContext('2d'), ovCv = $('#overview'), octx = ovCv.getContext('2d');
const laneW = () => $('#lanes').clientWidth;
function layout() {
  let y = RULER; const rows = [];
  for (const tr of trackRows()) { const st = styleOf(tr); const hh = tr.height || st.h; rows.push({ ...st, id: tr.id, tr, y, h: hh }); y += hh; }
  return { rows, H: y + 8 };
}
function buildHeads() {
  const el = $('#heads'); el.innerHTML = '';
  el.append(h('div', { style: `height:${22 + 1 + RULER}px;flex:none` }));
  for (const tr of trackRows()) {
    const st = styleOf(tr); const n = tr.clips.length; const isA = AUDIO.includes(tr.id); const isFx = tr.kind === 'fx';
    el.append(h('div', { class: 'head', style: `height:${tr.height || st.h}px;--c:${st.color}` },
      h('span', { class: 'nm', title: st.locked ? 'Khoá: lời đọc dựng lại bằng doc.py' : tr.name || '' }, (isFx ? (tr.name || st.name) : st.name) + ' ', h('small', {}, String(n)), st.locked ? ' 🔒' : ''),
      isFx ? h('button', { title: tr.hidden ? 'Bật track hiệu ứng' : 'Tắt track hiệu ứng (không dựng)', onclick: () => ops([{ op: 'track', id: tr.id, fields: { hidden: tr.hidden ? null : true } }]) }, tr.hidden ? '◌' : '👁') : null,
      !st.locked ? h('button', { class: 'm' + (S.locked[tr.id] ? ' on' : ''), title: 'Khoá track (không kéo nhầm)', onclick: () => { S.locked[tr.id] = !S.locked[tr.id]; buildHeads(); } }, S.locked[tr.id] ? '🔒' : '🔓') : null,
      isA ? h('button', { class: 'm' + (S.mute[tr.id] ? ' on' : ''), title: 'Tắt tiếng track khi nghe (không ảnh hưởng bản xuất)', onclick: () => { S.mute[tr.id] = !S.mute[tr.id]; buildHeads(); monitorChanged(); } }, 'M') : null,
      isA ? h('button', { class: 's' + (S.solo[tr.id] ? ' on' : ''), title: 'Chỉ nghe track này', onclick: () => { S.solo[tr.id] = !S.solo[tr.id]; buildHeads(); monitorChanged(); } }, 'S') : null,
      isFx && !n ? h('button', { title: 'Xoá track hiệu ứng trống', onclick: () => ops([{ op: 'track', id: tr.id, fields: { delete: true } }]) }, '✕') : null));
  }
}
function monitorChanged() { if (S.playing) audio.play(audio.now()); }
function resizeTL() {
  if (!S.tl) return;
  const { H } = layout(); const w = laneW(), dpr = devicePixelRatio || 1;
  tlCv.width = w * dpr; tlCv.height = H * dpr; tlCv.style.height = H + 'px'; tctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ovCv.width = w * dpr; ovCv.height = 22 * dpr; octx.setTransform(dpr, 0, 0, dpr, 0, 0);
  document.body.style.setProperty('--tlh', Math.min(window.innerHeight * 0.45, H + 22 + 40 + 8) + 'px');
  $('#heads').scrollTop = $('#laneScroll').scrollTop;
  drawTL();
}
const zoomToPps = z => 0.25 * Math.pow(2, z / 10);
const ppsToZoom = p => 10 * Math.log2(p / 0.25);
function setZoom(pps, anchorT) {
  const w = laneW(); anchorT = anchorT ?? S.t; const ax = (anchorT - S.view0) * S.pps;
  S.pps = Math.max(w / dur() * 0.9, Math.min(256, pps)); $('#zoom').value = ppsToZoom(S.pps);
  S.view0 = Math.max(0, anchorT - ax / S.pps); drawTL();
}
const X = t => (t - S.view0) * S.pps;
const Tx = x => S.view0 + x / S.pps;

function drawTL() {
  if (!S.tl) return;
  const w = laneW(), { rows, H } = layout(), g = tctx;
  g.clearRect(0, 0, w, H); g.fillStyle = '#15171c'; g.fillRect(0, 0, w, H);
  const t0 = S.view0, t1 = Tx(w);
  g.fillStyle = '#1d2027'; g.fillRect(0, 0, w, RULER);
  const steps = [0.04, 0.2, 1, 2, 5, 10, 30, 60, 120, 300, 600, 1200];
  const step = steps.find(s => s * S.pps >= 70) || 1800;
  g.fillStyle = '#8b93a1'; g.font = '11px Consolas, monospace'; g.textBaseline = 'top';
  for (let t = Math.floor(t0 / step) * step; t < t1; t += step) { const x = X(t); g.fillRect(x, RULER - 8, 1, 8); g.fillText(step < 1 ? tc(t) : mmss(t).replace(/\.0$/, ''), x + 3, 3); }
  for (const [a, b] of S.dirty || []) { g.fillStyle = 'rgba(224,83,63,.85)'; g.fillRect(X(a), RULER - 4, Math.max(2, (b - a) * S.pps), 4); }
  for (const m of S.tl.markers || []) if (m.t >= t0 && m.t <= t1) { g.fillStyle = '#d9a53a'; g.fillRect(X(m.t), 0, 2, RULER); g.fillText(m.label || '', X(m.t) + 4, 14); }
  for (const n of S.tl.review_notes || []) if (n.t >= t0 - 1 && n.t <= t1) {
    g.fillStyle = n.status === 'done' ? '#5a8' : n.status === 'doing' ? '#e0a030' : '#e0533f';
    g.beginPath(); g.moveTo(X(n.t) - 6, 0); g.lineTo(X(n.t) + 6, 0); g.lineTo(X(n.t), 10); g.fill();
  }
  for (const R of rows) {
    g.fillStyle = R.tr.hidden ? '#1a1416' : '#15171c'; g.fillRect(0, R.y, w, R.h);
    g.fillStyle = '#23272f'; g.fillRect(0, R.y + R.h - 1, w, 1);
    if (R.id === 'voice') drawVoice(g, R);
    for (const c of R.tr.clips) {
      const end = c.end ?? c.start + 0.1;
      if (end < t0 || c.start > t1) continue;
      drawClip(g, R, c, end);
    }
  }
  if (TL.dropAt) { g.fillStyle = 'rgba(184,240,60,.25)'; g.fillRect(X(TL.dropAt.t), TL.dropAt.y, Math.max(3, TL.dropAt.d * S.pps), TL.dropAt.h); }
  if (TL.guide != null) { g.fillStyle = '#b8f03c'; g.fillRect(X(TL.guide), RULER, 1, H - RULER); }
  const px = X(S.playing ? audio.now() : S.t);
  g.fillStyle = '#ff4d5e'; g.fillRect(px - 0.5, 0, 1.5, H);
  g.beginPath(); g.moveTo(px - 6, 0); g.lineTo(px + 6, 0); g.lineTo(px, 8); g.fill();
  drawOverview();
}
function drawVoice(g, R) {
  const pk = S.peaks['voice/voice.wav'];
  if (pk && pk !== 'loading') {
    g.fillStyle = 'rgba(63,163,107,.45)'; const mid = R.y + R.h / 2;
    const step = Math.max(1, Math.floor(100 / S.pps / 2));
    for (let x = 0; x < laneW(); x += 1) {
      const a = Math.floor(Tx(x) * 100), b = Math.floor(Tx(x + 1) * 100); let m = 0;
      for (let i = a; i <= b; i += step) m = Math.max(m, pk[i] || 0);
      const hh = (m / 255) * (R.h / 2 - 3); g.fillRect(x, mid - hh, 1, hh * 2);
    }
  } else loadPeaks('voice/voice.wav');
}
function drawClip(g, R, c, end) {
  const x = X(c.start), w = Math.max(1, (end - c.start) * S.pps), y = R.y + 2, hh = R.h - 4;
  const sel = c.id === S.sel || S.multi.has(c.id); const muted = c.mute;
  g.fillStyle = R.color + (R.id === 'voice' ? '33' : muted || R.tr.hidden ? '30' : '66');
  g.fillRect(x, y, w, hh);
  if (R.id === 'video' && w > 34 && c.src) drawThumb(g, c.src, x, y, w, hh);
  if (R.tr.kind === 'fx' && c.type === 'media_overlay' && (c.params || {}).src && w > 34) drawThumb(g, c.params.src, x, y, w, hh);
  if (['music', 'original', 'sfx'].includes(R.id) && c.src && w > 6) drawClipWave(g, c, x, y, w, hh, R.color);
  if (R.id === 'video') {
    const tr = c.transition_in; if (tr && tr.type) { g.fillStyle = '#fff8'; g.beginPath(); g.moveTo(x, y + hh); g.lineTo(x + Math.min(w, (tr.dur || 0.5) * S.pps), y); g.lineTo(x, y); g.fill(); }
    if (c.color && Object.keys(c.color).length && w > 20) { g.fillStyle = '#ffb347'; g.fillRect(x + w - 8, y + 2, 6, 6); }
  }
  if (R.tr.kind === 'fx') {
    const fi = (c.fade_in || 0) * S.pps, fo = (c.fade_out || 0) * S.pps; g.strokeStyle = '#fff9'; g.beginPath();
    g.moveTo(x, y + hh); g.lineTo(x + fi, y + 2); g.lineTo(x + w - fo, y + 2); g.lineTo(x + w, y + hh); g.stroke();
  }
  g.strokeStyle = sel ? '#b8f03c' : R.color; g.lineWidth = sel ? 2 : 1; g.strokeRect(x + 0.5, y + 0.5, w - 1, hh - 1);
  if (w > 26) {
    g.save(); g.beginPath(); g.rect(x, y, w - 2, hh); g.clip();
    g.fillStyle = '#fff'; g.font = '11px Segoe UI, sans-serif'; g.textBaseline = 'top';
    g.fillText(clipLabel(R, c), x + 4, y + 2);
    if (['music', 'original', 'sfx'].includes(R.id) && hh > 22) { g.fillStyle = '#ddd'; g.fillText(`${(c.gain_db ?? 0).toFixed(1)} dB${muted ? ' · tắt' : ''}${c.loop ? ' · lặp' : ''}`, x + 4, y + hh - 13); }
    g.restore();
  }
  if (c.anchor && w > 8) { g.fillStyle = '#b8f03c'; g.fillRect(x, y + hh - 3, 3, 3); }
}
const FX_NAMES = { old_film: 'Phim cũ', grain: 'Hạt phim', dust_scratches: 'Bụi & xước', flicker: 'Nháy sáng', jitter: 'Rung khung', vignette: 'Viền tối', light_leak: 'Lóa sáng', blur: 'Làm mờ', letterbox: 'Khung điện ảnh', color: 'Chỉnh màu', flash: 'Chớp trắng', media_overlay: 'Lớp phủ media' };
const OVERLAY_NAMES = { text: 'Chữ tự do', date_tag: 'Tag ngày/giờ', lower_third: 'Lower third', callout: 'Chú thích lớn', title_card: 'Thẻ tiêu đề', question: 'Câu hỏi', chapter: 'Chương', stat: 'Số liệu', quote: 'Trích dẫn đánh máy' };
function clipLabel(R, c) {
  if (R.id === 'voice') return S.pps > 30 ? `${c.id} ${c.text || ''}` : c.id;
  if (R.id === 'overlay') { const p = c.props || {}; return `${c.id} ${OVERLAY_NAMES[c.type] || c.type}: ${p.text || p.name || p.title || (p.lines || [])[0] || ''}`; }
  if (R.tr.kind === 'fx') return `${c.id} ${c.label || FX_NAMES[c.type] || c.type}${c.type === 'media_overlay' ? ' · ' + fileName((c.params || {}).src) : ''}`;
  if (R.id === 'video') return `${c.id}${c.caption ? ' · ' + c.caption : ''}`;
  return `${c.id} ${(c.src || '').split('/').slice(-2).join('/')}`;
}
function drawThumb(g, src, x, y, w, hh) {
  let im = S.thumbs[src];
  if (!im) { im = S.thumbs[src] = new Image(); im.onload = () => drawTL(); im.src = '/api/thumb?w=160&src=' + encodeURIComponent(src); return; }
  if (!im.complete || !im.naturalWidth) return;
  const tw = Math.min(w - 2, hh * im.naturalWidth / im.naturalHeight);
  g.globalAlpha = 0.85; g.drawImage(im, x + 1, y + 1, tw, hh - 2); g.globalAlpha = 1;
}
function drawClipWave(g, c, x, y, w, hh, color) {
  const pk = S.peaks[c.src];
  if (!pk) { loadPeaks(c.src); return; }
  if (pk === 'loading') return;
  g.fillStyle = color + 'cc'; const mid = y + hh / 2, n = pk.length, inn = (c.in || 0) * 100;
  const x0 = Math.max(x, 0), x1 = Math.min(x + w, laneW());
  for (let px = x0; px < x1; px++) {
    let i = Math.floor(inn + (px - x) / S.pps * 100);
    if (c.loop && n) i = i % n; const m = pk[i] || 0;
    const a = (m / 255) * (hh / 2 - 2); g.fillRect(px, mid - a, 1, a * 2);
  }
}
async function loadPeaks(src) {
  if (S.peaks[src]) return; S.peaks[src] = 'loading';
  try { const r = await fetch('/api/peaks?src=' + encodeURIComponent(src)); S.peaks[src] = new Uint8Array(await r.arrayBuffer()); drawTL(); }
  catch (e) { S.peaks[src] = new Uint8Array(0); }
}
function drawOverview() {
  const w = laneW(), g = octx, D = dur(); g.clearRect(0, 0, w, 22); g.fillStyle = '#0e1014'; g.fillRect(0, 0, w, 22);
  const x = t => (t / D) * w;
  for (const m of S.tl.markers || []) { g.fillStyle = '#d9a53a'; g.fillRect(x(m.t), 0, 1, 22); }
  for (const tr of S.tl.tracks) if (tr.kind === 'fx') for (const c of tr.clips) { g.fillStyle = '#c25fd6'; g.fillRect(x(c.start), 11, Math.max(2, x(c.end) - x(c.start)), 4); }
  for (const [a, b] of S.dirty || []) { g.fillStyle = '#e0533f'; g.fillRect(x(a), 16, Math.max(2, x(b) - x(a)), 6); }
  for (const n of S.tl.review_notes || []) { g.fillStyle = n.status === 'done' ? '#5a8' : '#e0533f'; g.fillRect(x(n.t) - 1, 0, 3, 10); }
  g.strokeStyle = '#b8f03c'; g.strokeRect(x(S.view0) + 0.5, 0.5, Math.max(3, x(Tx(w)) - x(S.view0)), 21);
  g.fillStyle = '#ff4d5e'; g.fillRect(x(S.t), 0, 1.5, 22);
}

// ------------------------------------------------------------------ timeline interaction
const TL = { mode: null, guide: null, dropAt: null };
function rowAt(y) { const { rows } = layout(); return rows.find(r => y >= r.y && y < r.y + r.h); }
function hit(ev) {
  const b = tlCv.getBoundingClientRect(); const x = ev.clientX - b.left, y = ev.clientY - b.top;
  if (y < RULER) return { x, y, ruler: true };
  const R = rowAt(y); if (!R) return { x, y };
  const t = Tx(x); let c = null, edge = null;
  for (const k of R.tr.clips) {
    const e = k.end ?? k.start; const x0 = X(k.start), x1 = X(e);
    if (x >= x0 - 4 && x <= x1 + 4) {
      c = k;
      if (R.id !== 'voice' && x1 - x0 > 12) { if (x - x0 < 6) edge = 'start'; else if (x1 - x < 6) edge = 'end'; }
      if (x >= x0 && x <= x1) break;
    }
  }
  return { x, y, t, R, tr: R.tr, c, edge };
}
function snapTo(t, exclude, alt) {
  if (!$('#snap').checked || alt) return { t, label: null };
  const tol = 8 / S.pps; let best = null;
  const consider = (v, label) => { const d = Math.abs(v - t); if (d <= tol && (!best || d < best.d)) best = { d, v, label }; };
  let i = lowerBound(S.snapT, t - tol);
  for (; i < S.snapT.length && S.snapT[i] <= t + tol; i++) consider(S.snapT[i], S.snapA[i]);
  consider(S.t, 'đầu phát');
  for (const tr of S.tl.tracks) {
    if (tr.id === 'voice') continue;
    for (const c of tr.clips) if (c.id !== exclude && Math.abs(c.start - t) < tol + 50) { consider(c.start, 'mép ' + c.id); if (c.end != null) consider(c.end, 'mép ' + c.id); }
  }
  return best ? { t: best.v, label: best.label } : { t, label: null };
}
function lowerBound(a, v) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] < v) lo = m + 1; else hi = m; } return lo; }
function tip(x, y, text) { const t = $('#tip'); if (!text) { t.style.display = 'none'; return; } t.style.display = 'block'; t.textContent = text; t.style.left = Math.min(laneW() - 240, x + 12) + 'px'; t.style.top = (y + 22 + 12 - $('#laneScroll').scrollTop) + 'px'; }

tlCv.addEventListener('pointerdown', ev => {
  if (!S.tl) return;
  const H = hit(ev); tlCv.setPointerCapture(ev.pointerId);
  const add = ev.shiftKey || ev.ctrlKey || ev.metaKey;
  if (H.ruler || !H.c) { TL.mode = 'scrub'; seek(Tx(H.x)); if (!H.ruler && !add) select(null); return; }
  select(H.c.id, add);
  if (H.R.locked) { TL.mode = 'scrub'; seek(Tx(H.x)); return; }
  if (S.locked[H.R.id] || add) { TL.mode = null; return; }
  const c = H.c; const len = (c.end ?? c.start) - c.start;
  let mode = H.edge ? 'trim-' + H.edge : 'move', partner = null;
  if (H.R.id === 'video' && H.edge && !ev.altKey) {
    const vids = H.tr.clips; const i = vids.indexOf(c);
    if (H.edge === 'end' && vids[i + 1] && Math.abs(vids[i + 1].start - c.end) < 1.5 / fps()) partner = vids[i + 1];
    if (H.edge === 'start' && vids[i - 1] && Math.abs(vids[i - 1].end - c.start) < 1.5 / fps()) partner = vids[i - 1];
  }
  TL.mode = mode; TL.d = { c, x0: H.x, s0: c.start, e0: c.end ?? c.start, len, partner, moved: false };
});
tlCv.addEventListener('pointermove', ev => {
  const H = hit(ev);
  if (!TL.mode) {
    tlCv.style.cursor = H.edge ? 'ew-resize' : H.c && !(H.R && H.R.locked) ? 'grab' : 'default';
    if (H.c) tip(H.x, H.y, `${H.c.id}  ${tc(H.c.start)} → ${tc(H.c.end ?? H.c.start)}${H.c.gain_db != null ? '  ' + H.c.gain_db + ' dB' : ''}${H.R.id === 'voice' ? '  ' + (H.c.text || '').slice(0, 70) : ''}`);
    else tip(0, 0, null);
    return;
  }
  if (TL.mode === 'scrub') { seek(Tx(H.x)); return; }
  const d = TL.d, dt = (H.x - d.x0) / S.pps; if (Math.abs(H.x - d.x0) > 2) d.moved = true; if (!d.moved) return;
  const c = d.c; let label = null;
  if (TL.mode === 'move') {
    let s = Math.max(0, d.s0 + dt);
    const a = snapTo(s, c.id, ev.altKey), b = snapTo(s + d.len, c.id, ev.altKey);
    if (a.label && (!b.label || Math.abs(a.t - s) <= Math.abs(b.t - s - d.len))) { s = a.t; label = a.label; TL.guide = a.t; }
    else if (b.label) { s = b.t - d.len; label = b.label; TL.guide = b.t; } else TL.guide = null;
    c.start = s; if (c.end != null) c.end = s + d.len;
  } else if (TL.mode === 'trim-start') {
    let s = Math.min(d.e0 - 1 / fps(), Math.max(0, d.s0 + dt)); const a = snapTo(s, c.id, ev.altKey); s = Math.min(d.e0 - 1 / fps(), a.t); label = a.label; TL.guide = a.label ? s : null;
    c.start = s; if (d.partner) d.partner.end = s;
  } else {
    let e = Math.max(d.s0 + 1 / fps(), d.e0 + dt); const a = snapTo(e, c.id, ev.altKey); e = Math.max(d.s0 + 1 / fps(), a.t); label = a.label; TL.guide = a.label ? e : null;
    c.end = e; if (d.partner) d.partner.start = e;
  }
  tip(H.x, H.y, `${c.id}  ${tc(c.start)} → ${tc(c.end ?? c.start)}  (${((c.end ?? c.start) - c.start).toFixed(2)} s)${label ? '  ⇢ ' + label : ''}`);
  drawTL();
});
tlCv.addEventListener('pointerup', () => {
  const mode = TL.mode, d = TL.d; TL.mode = null; TL.guide = null; tip(0, 0, null);
  if (!mode || mode === 'scrub' || !d || !d.moved) { drawTL(); return; }
  const c = d.c; let op;
  if (mode === 'move') op = { op: 'move', id: c.id, start: +c.start.toFixed(4) };
  else op = { op: 'trim', id: c.id, start: +c.start.toFixed(4), end: +(c.end ?? c.start).toFixed(4), roll: !!d.partner };
  ops([op], mode === 'move' ? `Đã dời ${c.id} tới ${tc(c.start)}` : `Đã cắt ${c.id}`);
});
tlCv.addEventListener('dblclick', ev => { const H = hit(ev); if (H.c) seek(H.c.start); });
$('#lanes').addEventListener('wheel', ev => {
  if (ev.ctrlKey || ev.metaKey) { ev.preventDefault(); const b = tlCv.getBoundingClientRect(); setZoom(S.pps * (ev.deltaY < 0 ? 1.25 : 0.8), Tx(ev.clientX - b.left)); }
  else if (ev.shiftKey || Math.abs(ev.deltaX) > Math.abs(ev.deltaY)) { ev.preventDefault(); S.view0 = Math.max(0, Math.min(dur() - 5, S.view0 + (ev.deltaY + ev.deltaX) / S.pps * 0.6)); drawTL(); }
  else if ($('#laneScroll').scrollHeight <= $('#laneScroll').clientHeight + 2) { ev.preventDefault(); S.view0 = Math.max(0, Math.min(dur() - 5, S.view0 + ev.deltaY / S.pps * 0.6)); drawTL(); }
}, { passive: false });
$('#laneScroll').addEventListener('scroll', () => { $('#heads').scrollTop = $('#laneScroll').scrollTop; });
let ovDrag = false;
const ovSeek = ev => { const b = ovCv.getBoundingClientRect(); const t = (ev.clientX - b.left) / b.width * dur(); S.view0 = Math.max(0, t - laneW() / S.pps / 2); drawTL(); };
ovCv.addEventListener('pointerdown', ev => { ovDrag = true; ovCv.setPointerCapture(ev.pointerId); ovSeek(ev); });
ovCv.addEventListener('pointermove', ev => { if (ovDrag) ovSeek(ev); });
ovCv.addEventListener('pointerup', () => { ovDrag = false; });

/* drag & drop from the panels (media, audio, effects, text) onto the timeline */
let dragItem = null;
function draggable(el, item) {
  el.draggable = true;
  el.addEventListener('dragstart', e => { dragItem = item; e.dataTransfer.setData('text/plain', JSON.stringify(item)); e.dataTransfer.effectAllowed = 'copy'; });
  el.addEventListener('dragend', () => { dragItem = null; TL.dropAt = null; drawTL(); });
}
function dropTarget(ev) {
  const b = tlCv.getBoundingClientRect(); const x = ev.clientX - b.left, y = ev.clientY - b.top; const R = rowAt(y);
  return { R, t: Math.max(0, snapTo(Tx(x), null, ev.altKey).t), y: R ? R.y : 0, h: R ? R.h : 0 };
}
tlCv.addEventListener('dragover', ev => {
  if (!dragItem) return; ev.preventDefault();
  const d = dropTarget(ev); TL.dropAt = d.R ? { t: d.t, y: d.y, h: d.h, d: dragItem.dur || 5 } : null; drawTL();
});
tlCv.addEventListener('dragleave', () => { TL.dropAt = null; drawTL(); });
tlCv.addEventListener('drop', ev => {
  ev.preventDefault(); const it = dragItem; TL.dropAt = null; dragItem = null; const d = dropTarget(ev);
  if (!it || !d.R) return drawTL();
  placeItem(it, d.R.tr, d.t, ev.altKey);
});
function placeItem(it, tr, t, replace) {
  if (it.kind === 'image' || it.kind === 'video') {
    if (tr.kind === 'fx') return addEffect('media_overlay', { src: it.src, blend: 'screen' }, t, it.dur || 10, tr.id, 'Lớp phủ ' + fileName(it.src));
    if (tr.id !== 'video') return toast('Thả ảnh/video vào track Cảnh (chèn cảnh) hoặc track Hiệu ứng (lớp phủ)', true);
    const under = clipAt('video', t);
    if (replace && under) return ops([{ op: 'set', id: under.id, fields: { src: it.src, kind: it.kind === 'video' ? 'video' : 'photo' } }], `Đã thay ảnh ${under.id}`);
    return ops([{ op: 'insert', src: it.src, t, dur: it.dur || 5, kind: it.kind === 'video' ? 'video' : 'photo' }], `Đã chèn ${fileName(it.src)} tại ${tc(t)}`);
  }
  if (it.kind === 'audio') {
    const tid = ['music', 'original', 'sfx'].includes(tr.id) ? tr.id : it.track || 'sfx';
    const d = it.dur || 3;
    return ops([{ op: 'add', track: tid, clip: { src: it.src, start: t, end: t + d, gain_db: tid === 'music' ? -16 : tid === 'original' ? -18 : -12, ...(tid === 'sfx' ? {} : { fade_in: 0.5, fade_out: 1.0 }) } }], `Đã thêm ${fileName(it.src)} vào ${styleOf(tracksById()[tid]).name}`);
  }
  if (it.kind === 'effect') return addEffect(it.type, it.params, t, it.dur || 10, tr.kind === 'fx' ? tr.id : null, it.label);
  if (it.kind === 'text') return addText(it.type, t, it.props);
}

// ------------------------------------------------------------------ panels (left)
function switchTab(t) {
  S.tab = t;
  for (const b of document.querySelectorAll('#tabs button')) b.classList.toggle('on', b.dataset.tab === t);
  renderPanel();
}
const PANELS = {};
function renderPanel(soft) {
  if (!S.cat || !S.tl) return;
  if (soft && ['media', 'audio', 'record', 'speech'].includes(S.tab)) return;  // keep scroll/search of libraries on timeline reloads
  const el = $('#panel'); const keep = el.scrollTop; el.innerHTML = ''; (PANELS[S.tab] || (() => {}))(el); if (soft) el.scrollTop = keep;
}
function field(label, input) { return h('div', { class: 'field' }, h('label', {}, label), input); }
function num(v, onchange, step = 0.01, attrs = {}) { return h('input', { type: 'number', step, value: v ?? '', ...attrs, onchange: e => onchange(e.target.value === '' ? null : parseFloat(e.target.value)) }); }
function txt(v, onchange, attrs = {}) { return h('input', { type: 'text', value: v ?? '', ...attrs, onchange: e => onchange(e.target.value) }); }
function sel(v, options, onchange) { return h('select', { onchange: e => onchange(e.target.value) }, options.map(([val, lab]) => h('option', { value: val, selected: String(v) === String(val) }, lab))); }
/* slider: live draft while dragging (input), saves on release (change) */
function slider(label, value, [min, max], step, live, commit, fmt = v => (+v).toFixed(2)) {
  const r = h('input', { type: 'range', min, max, step, value: value ?? min }); const v = h('span', { class: 'v' }, fmt(value ?? min));
  r.oninput = () => { v.textContent = fmt(r.value); live && live(parseFloat(r.value)); };
  r.onchange = () => { clearDraft(); commit(parseFloat(r.value)); };
  return h('div', { class: 'sl' }, h('label', {}, label), r, v);
}
const sec = (t, extra) => h('div', { class: 'sec' }, t, extra || '');
const empty = t => h('div', { class: 'empty' }, t);
const playheadSpan = () => { const v = selectedOn(tr => tr.id === 'video')[0]; return v ? [v[1].start, v[1].end] : [S.t, Math.min(dur(), S.t + 10)]; };
const playheadSpanArgs = () => { const [a, b] = playheadSpan(); return [a, b - a]; };
function searchBox(ph) {
  const s = h('input', { type: 'text', placeholder: ph, value: S.libQuery, style: 'width:100%' });
  s.oninput = debounce(() => { S.libQuery = s.value; renderPanel(); const n = $('#panel input[type=text]'); if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }, 250);
  return s;
}

/* ---- Media */
async function loadLib(scope, force) {
  if (!S.lib[scope] || force) { const { body } = await api('/api/library?scope=' + scope); S.lib[scope] = body.files; }
  return S.lib[scope];
}
async function uploadFiles(files, after) {
  for (const f of files) {
    try { const { body } = await api('/api/import?name=' + encodeURIComponent(f.name), { method: 'POST', body: f }); toast(`Đã nhập ${fileName(body.src)}`); }
    catch (e) { toast(`Không nhập được ${f.name}: ${e.message}`, true); }
  }
  S.lib = {}; (after || renderPanel)();
}
function dropZone(label, after) {
  const inp = h('input', { type: 'file', multiple: true, style: 'display:none', onchange: e => uploadFiles(e.target.files, after) });
  const z = h('div', { class: 'drop' }, label, h('br'), h('button', { onclick: () => inp.click() }, '⇪ Chọn file…'), inp);
  z.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); z.classList.add('over'); } });
  z.addEventListener('dragleave', () => z.classList.remove('over'));
  z.addEventListener('drop', e => { e.preventDefault(); z.classList.remove('over'); uploadFiles(e.dataTransfer.files, after); });
  return z;
}
function mediaGrid(el, files, onPick) {
  const q = S.libQuery.toLowerCase(); const grid = h('div', { class: 'grid' });
  const list = files.filter(f => !q || f.src.toLowerCase().includes(q));
  for (const f of list.slice(0, 300)) {
    const tile = h('div', { class: 'tile', title: `${f.src}\n${(f.size / 1e6).toFixed(1)} MB${f.used ? ` · đang dùng ${f.used} lần` : ''}\nKéo vào timeline · bấm để xem/chèn` },
      h('img', { loading: 'lazy', src: '/api/thumb?w=200&src=' + encodeURIComponent(f.src) }), h('span', { class: 'kind' }, f.kind === 'video' ? '▶ video' : 'ảnh'),
      f.used ? h('span', { class: 'used' }, f.used) : null, h('div', { class: 'nm' }, f.name));
    tile.onclick = () => onPick(f); draggable(tile, { kind: f.kind, src: f.src, dur: f.kind === 'video' ? 6 : 5 });
    grid.append(tile);
  }
  el.append(h('div', { class: 'muted', style: 'font-size:11px;margin:4px 0' }, `${list.length} file${list.length > 300 ? ' (hiện 300 đầu)' : ''}`), grid);
}
function pickMedia(f) {
  $('#modalTitle').textContent = f.src;
  const body = $('#modalBody'); body.innerHTML = '';
  body.append(f.kind === 'video' ? h('video', { src: '/media/' + f.src, controls: true, autoplay: true }) : h('img', { src: '/media/' + f.src, style: 'width:100%;max-height:60vh;object-fit:contain;background:#000' }));
  const v = selectedOn(tr => tr.id === 'video')[0];
  body.append(h('div', { class: 'toolbar' },
    h('button', { class: 'primary', onclick: () => { closeModal(); placeItem({ kind: f.kind, src: f.src, dur: 5 }, tracksById().video, S.t, false); } }, `Chèn vào Cảnh tại ${tc(S.t)} (5 s)`),
    v ? h('button', { onclick: () => { closeModal(); ops([{ op: 'set', id: v[1].id, fields: { src: f.src, kind: f.kind === 'video' ? 'video' : 'photo' } }], `Đã thay ảnh ${v[1].id}`); } }, `Thay ảnh ${v[1].id}`) : null,
    h('button', { onclick: () => { closeModal(); addEffect('media_overlay', { src: f.src, blend: 'screen' }, ...playheadSpanArgs(), null, 'Lớp phủ ' + f.name); } }, 'Dùng làm lớp phủ (Hiệu ứng)')));
  $('#modal').classList.remove('hidden');
}
PANELS.media = async el => {
  el.append(h('div', { class: 'chips' }, [['project', 'Phim này'], ['overlays', 'Lớp phủ / đã nhập']].map(([k, l]) => h('button', { class: S.libScope === k ? 'on' : '', onclick: () => { S.libScope = k; renderPanel(); } }, l))));
  el.append(searchBox('Tìm file…'), dropZone('Thả ảnh / video vào đây để nhập (lưu ở media/import/)'));
  el.append(h('p', { class: 'muted', style: 'font-size:11px' }, 'Kéo ô vào track Cảnh để chèn cảnh (giữ Alt khi thả lên một cảnh để thay ảnh), vào track Hiệu ứng để làm lớp phủ. Bấm ô để xem lớn.'));
  try { mediaGrid(el, (await loadLib(S.libScope)).filter(f => f.kind !== 'audio'), pickMedia); } catch (e) { el.append(empty('Lỗi đọc kho media: ' + e.message)); }
};

/* ---- Âm thanh */
PANELS.audio = async el => {
  el.append(searchBox('Tìm (vd: jeep, riser, tension)…'), dropZone('Thả file âm thanh vào đây để nhập'));
  const [tr, c] = findClip(S.sel || '');
  if (c && ['music', 'original', 'sfx'].includes(tr.id)) el.append(sec('Clip đang chọn: ' + c.id), audioControls(tr, c));
  let files; try { files = await loadLib('audio'); } catch (e) { el.append(empty('Lỗi: ' + e.message)); return; }
  const q = S.libQuery.toLowerCase(); const groups = {};
  for (const f of files.filter(f => !q || f.src.toLowerCase().includes(q))) (groups[f.folder] = groups[f.folder] || []).push(f);
  const list = h('div', { class: 'alist' });
  for (const [g, fs] of Object.entries(groups)) {
    const isMusic = g.includes('/music'); const body = h('div', {});
    list.append(h('div', { class: 'grp', onclick: () => body.classList.toggle('hidden') }, `${g.replace(/^assets\//, '').replace(/^projects\/[^/]+\//, '')} (${fs.length})`), body);
    for (const f of fs) {
      const it = h('div', { class: 'it', title: f.src + (f.used ? ` · đang dùng ${f.used} lần` : '') },
        h('button', { title: 'Nghe thử', onclick: () => previewAudio(f.src) }, '▶'), h('span', { class: 'nm' }, f.name), f.used ? h('span', { class: 'badge', style: 'background:#2f3a1a;color:#b8f03c' }, f.used) : null,
        h('button', { title: `Thêm vào ${isMusic ? 'Nhạc' : 'Tiếng động'} tại đầu phát`, onclick: () => addAudioAt(f, isMusic ? 'music' : 'sfx') }, '+'));
      draggable(it, { kind: 'audio', src: f.src, track: isMusic ? 'music' : 'sfx', dur: isMusic ? 30 : 3 });
      body.append(it);
    }
  }
  el.append(h('p', { class: 'muted', style: 'font-size:11px' }, 'Bấm + để thêm tại đầu phát (độ dài theo file), hoặc kéo vào track Nhạc / Nền / Tiếng động.'), list);
};
function previewAudio(src) { const a = $('#auPreview'); if (a.dataset.src === src && !a.paused) { a.pause(); return; } a.dataset.src = src; a.src = '/media/' + src; a.play(); }
function addAudioAt(f, tid) {
  const a = new Audio('/media/' + f.src);
  a.onloadedmetadata = () => { const d = Math.min(isFinite(a.duration) ? a.duration : 3, tid === 'music' ? 600 : 30); placeItem({ kind: 'audio', src: f.src, dur: +d.toFixed(3) }, tracksById()[tid], S.t); };
  a.onerror = () => placeItem({ kind: 'audio', src: f.src, dur: 3 }, tracksById()[tid], S.t);
}
function audioControls(tr, c) {
  const box = h('div', {});
  box.append(slider('Âm lượng', c.gain_db ?? -12, [-40, 6], 0.5, null, v => setF(c, { gain_db: v }, `${c.id}: ${v} dB`), v => (+v).toFixed(1) + ' dB'),
    slider('Fade vào', c.fade_in ?? (tr.id === 'sfx' ? 0.005 : 0.15), [0, 5], 0.05, null, v => setF(c, { fade_in: v }), v => (+v).toFixed(2) + ' s'),
    slider('Fade ra', c.fade_out ?? 0.3, [0, 8], 0.05, null, v => setF(c, { fade_out: v }), v => (+v).toFixed(2) + ' s'),
    h('div', { class: 'toolbar' },
      h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: !!c.mute, onchange: e => setF(c, { mute: e.target.checked || null }) }), 'Tắt tiếng clip'),
      h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: !!c.loop, onchange: e => setF(c, { loop: e.target.checked || null }) }), 'Lặp'),
      h('button', { onclick: () => { S.solo = { [tr.id]: true }; buildHeads(); seek(Math.max(0, c.start - 1)); if (!S.playing) play(); } }, '▶ Nghe riêng track'),
      h('button', { onclick: () => { S.solo = {}; S.mute = {}; buildHeads(); monitorChanged(); } }, 'Nghe tất cả')));
  return box;
}

/* ---- Chữ */
const TEXT_TEMPLATES = [
  ['text', 'Chữ tự do', 'T', { text: 'Chữ mới', y: 0.18, size: 72, box: 0.45, anim: 'slide_up' }],
  ['text', 'Tiêu đề giữa', 'H', { text: 'TIÊU ĐỀ', y: 0.45, size: 120, upper: true, anim: 'fade', shadow: 0.8 }],
  ['text', 'Chú thích góc', '▭', { text: 'Ảnh minh hoạ', x: 0.04, y: 0.92, size: 30, align: 'left', font: 'body', box: 0.5, anim: 'fade' }],
  ['text', 'Đánh máy', '⌨', { text: 'Ghi chép ngày 23.11.1970', y: 0.8, size: 54, font: 'monomed', anim: 'typewriter', box: 0.55 }],
  ['date_tag', 'Tag ngày/giờ', '⏱', { text: '03:17 · 23.11.1970' }],
  ['lower_third', 'Lower third', '▁', { kicker: 'Nhân vật', name: 'Họ và tên', sub: 'Vai trò' }],
  ['callout', 'Chú thích lớn', '❝', { text: 'Chú thích' }],
  ['title_card', 'Thẻ tiêu đề', '▣', { text: 'TIÊU ĐỀ', sub: 'Phụ đề' }],
  ['question', 'Câu hỏi', '?', { text: 'Vì sao?' }],
  ['chapter', 'Chương', '§', { n: 1, title: 'Tên chương' }],
  ['stat', 'Số liệu', '#', { title: 'Tiêu đề', items: [{ value: '55', label: 'ngày đêm' }, { value: '16.000', label: 'quân' }] }],
  ['quote', 'Trích dẫn đánh máy', '“', { kicker: 'Nguồn', title: 'Tiêu đề', lines: ['Dòng thứ nhất', 'dòng thứ hai'], source: '— Nguồn trích', cps: 16 }],
];
function addText(type, t, props) { return ops([{ op: 'add', track: 'overlay', clip: { type, start: t, end: Math.min(dur(), t + 5), props } }], `Đã thêm ${OVERLAY_NAMES[type] || type} tại ${tc(t)}`); }
PANELS.text = el => {
  el.append(sec('Thêm chữ tại đầu phát (hoặc kéo vào track Chữ)'));
  const grid = h('div', { class: 'grid' });
  for (const [type, label, ic, props] of TEXT_TEMPLATES) {
    const tile = h('div', { class: 'tile ftile', onclick: () => addText(type, S.t, props) }, h('div', {}, h('span', { class: 'ic' }, ic), label));
    draggable(tile, { kind: 'text', type, props, dur: 5 }); grid.append(tile);
  }
  el.append(grid);
  const [tr, c] = findClip(S.sel || '');
  if (c && tr.id === 'overlay') el.append(sec('Đang chọn: ' + c.id), h('p', { class: 'muted' }, 'Sửa nội dung ở bảng Thuộc tính bên phải.'));
  const st = { ...S.cat.subtitle_default, ...(S.tl.subtitle_style || {}) };
  const setSub = (k, v) => ops([{ op: 'subtitle_style', fields: { [k]: v } }], 'Đã đổi kiểu phụ đề');
  const liveSub = (k, v) => draft([{ op: 'subtitle_style', fields: { [k]: v } }]);
  el.append(sec('Phụ đề (in lên hình)'),
    h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: !!(S.tl.fx || {}).subtitles, onchange: e => ops([{ op: 'fx', fields: { subtitles: e.target.checked } }], e.target.checked ? 'Bật phụ đề' : 'Tắt phụ đề') }), 'Hiện phụ đề từ voice.srt'),
    h('p', { class: 'muted', style: 'font-size:11px' }, 'Sửa chữ một câu: dừng hình rồi bấm thẳng vào phụ đề trên khung xem trước (hoặc tab Lời nói → Phụ đề). Kéo thanh để xem nháp, thả để lưu.'),
    h('div', { class: 'muted', style: 'font-size:11px;margin-top:6px' }, 'Chữ'),
    field('Phông', sel(st.font || 'body', [['body', 'Be Vietnam Pro'], ['bodyreg', 'Be Vietnam Pro mảnh'], ['head', 'Oswald'], ['monomed', 'IBM Plex Mono']], v => setSub('font', v))),
    slider('Cỡ chữ', st.size, [24, 90], 1, v => liveSub('size', v), v => setSub('size', v), v => Math.round(v)),
    field('In hoa', h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: !!st.upper, onchange: e => setSub('upper', e.target.checked || null) }), 'VIẾT HOA TOÀN BỘ PHỤ ĐỀ')),
    field('Màu chữ', h('input', { type: 'color', class: 'colorin', value: st.color || '#EDE7DC', onchange: e => setSub('color', e.target.value) })),
    slider('Vị trí dọc', st.y ?? 0.8815, [0.05, 0.95], 0.005, v => liveSub('y', v), v => setSub('y', v)),
    h('div', { class: 'muted', style: 'font-size:11px;margin-top:6px' }, 'Viền & bóng'),
    slider('Độ dày viền', st.stroke, [0, 8], 1, v => liveSub('stroke', v), v => setSub('stroke', v), v => Math.round(v)),
    field('Màu viền', h('input', { type: 'color', class: 'colorin', value: st.stroke_color || '#0A0908', onchange: e => setSub('stroke_color', e.target.value) })),
    slider('Bóng chữ', st.shadow ?? 1, [0, 1], 0.05, v => liveSub('shadow', v), v => setSub('shadow', v)),
    h('div', { class: 'muted', style: 'font-size:11px;margin-top:6px' }, 'Nền phụ đề'),
    slider('Độ đậm nền', st.box, [0, 1], 0.05, v => liveSub('box', v), v => setSub('box', v), v => Math.round(v * 100) + '%'),
    field('Màu nền', h('input', { type: 'color', class: 'colorin', value: st.box_color || '#0A0908', onchange: e => { if (!st.box) ops([{ op: 'subtitle_style', fields: { box_color: e.target.value, box: 0.6 } }], 'Bật nền phụ đề'); else setSub('box_color', e.target.value); } })),
    slider('Lề nền', st.box_pad ?? 18, [0, 60], 1, v => liveSub('box_pad', v), v => setSub('box_pad', v), v => Math.round(v) + ' px'),
    slider('Bo góc', st.box_radius ?? 0, [0, 40], 1, v => liveSub('box_radius', v), v => setSub('box_radius', v), v => Math.round(v) + ' px'),
    h('div', { class: 'toolbar' },
      h('button', { onclick: () => ops([{ op: 'subtitle_style', fields: { box: 0.6, box_color: '#000000', box_pad: 16, box_radius: 8, shadow: 0, stroke: 0 } }], 'Kiểu: nền đen mờ') }, 'Mẫu: nền đen mờ'),
      h('button', { onclick: () => ops([{ op: 'subtitle_style', fields: { upper: true, font: 'head', size: 52, stroke: 4 } }], 'Kiểu: in hoa đậm') }, 'Mẫu: in hoa đậm'),
      h('button', { onclick: () => ops([{ op: 'subtitle_style', fields: Object.fromEntries(Object.keys(S.cat.subtitle_default).map(k => [k, null])) }], 'Phụ đề về mặc định') }, 'Về mặc định')),
    h('p', { class: 'muted', style: 'font-size:11px' }, 'Đổi kiểu phụ đề là đổi hình cả phim: lần xuất sau dựng lại toàn bộ hình. Sửa chữ một câu chỉ dựng lại đoạn câu đó.'));
};

/* ---- Lời nói (câu đọc) + Phụ đề (cues, editable) */
PANELS.speech = el => {
  S.speechMode = S.speechMode || 'cues';
  el.append(h('div', { class: 'chips' }, [['cues', 'Phụ đề (sửa được)'], ['sents', 'Câu đọc']].map(([k, l]) => h('button', { class: S.speechMode === k ? 'on' : '', onclick: () => { S.speechMode = k; renderPanel(); } }, l))));
  if (S.speechMode === 'cues') return cuePanel(el);
  const search = h('input', { type: 'text', placeholder: 'Tìm trong lời đọc…', value: S.speechQ || '', style: 'width:100%' });
  const list = h('div', { id: 'sentList' });
  const fill = () => {
    const q = (S.speechQ || '').toLowerCase(); list.innerHTML = '';
    const shown = S.sentences.filter(s => !q || (s.text || '').toLowerCase().includes(q));
    for (const s of shown.slice(0, 400)) list.append(h('div', { class: 'sent', 'data-id': s.id, onclick: () => seek(s.start) }, h('div', { class: 'tm' }, `${s.id} · ${tc(s.start)} → ${tc(s.end)}`), s.text));
    if (shown.length > 400) list.append(h('div', { class: 'muted' }, `… ${shown.length - 400} câu nữa (gõ để lọc)`));
    highlightSentence();
  };
  search.oninput = debounce(() => { S.speechQ = search.value; fill(); }, 200);
  el.append(search, h('p', { class: 'muted', style: 'font-size:11px' }, `${S.sentences.length} câu. Bấm một câu để tới đó. Lời đọc khoá trong studio: đổi câu / khoảng nghỉ bằng doc.py rồi mọi clip có neo tự dời theo.`), list);
  fill();
};
async function cuePanel(el) {
  const search = h('input', { type: 'text', placeholder: 'Tìm trong phụ đề…', value: S.cueQ || '', style: 'width:100%' });
  const info = h('p', { class: 'muted', style: 'font-size:11px' }, 'Bấm một câu để tới đó và sửa. Câu đã sửa có nhãn “đã sửa”; câu ẩn bị gạch.');
  const list = h('div', { id: 'cueList' });
  const only = h('label', { class: 'chk', style: 'margin:4px 0' }, h('input', { type: 'checkbox', checked: !!S.cueEdited, onchange: e => { S.cueEdited = e.target.checked; fill(); } }), 'Chỉ câu đã sửa / ẩn');
  el.append(search, only, info, list);
  if (!(S.tl.fx || {}).subtitles) el.insertBefore(h('p', { style: 'color:var(--amber)' }, 'Phụ đề đang tắt (tab Chữ → Phụ đề).'), info);
  let cues; try { cues = (await api('/api/subtitles')).body.cues; } catch (e) { list.append(empty('Lỗi: ' + e.message)); return; }
  const fill = () => {
    const q = (S.cueQ || '').toLowerCase(); list.innerHTML = '';
    let shown = cues.filter(c => (!q || c.text.toLowerCase().includes(q) || c.orig.text.toLowerCase().includes(q)) && (!S.cueEdited || c.edited));
    if (!q && !S.cueEdited) {  // a window around the playhead
      const i = Math.max(0, shown.findIndex(c => c.end > S.t)); shown = shown.slice(Math.max(0, i - 40));
      if (i > 40) list.append(h('div', { class: 'muted', style: 'font-size:11px;padding:4px' }, `… ${i - 40} câu trước (gõ để tìm, hoặc dời đầu phát)`));
    }
    for (const c of shown.slice(0, 500)) list.append(h('div', { class: 'cue' + (c.edited ? ' edited' : '') + (c.hidden ? ' hid' : ''), 'data-k': c.key,
      onclick: ev => { seek(c.start + Math.min(0.1, (c.end - c.start) / 2)); openSubEditor(c, ev.clientX + 360, ev.clientY); } },
      h('div', { class: 'tm' }, `${tc(c.start)} → ${tc(c.end)}`), c.hidden ? c.orig.text : c.text));
    if (shown.length > 500) list.append(h('div', { class: 'muted' }, `… ${shown.length - 500} câu nữa (gõ để lọc)`));
    info.textContent = `${cues.length} câu phụ đề · ${cues.filter(c => c.edited).length} đã sửa. Bấm một câu để tới đó và sửa.`;
    highlightCue();
  };
  search.oninput = debounce(() => { S.cueQ = search.value; fill(); }, 200);
  S.cues = cues; fill();
}
function highlightCue() {
  const list = $('#cueList'); if (!list || !S.cues) return;
  for (const e of list.querySelectorAll('.cue.cur')) e.classList.remove('cur');
  const c = S.cues.find(x => x.start <= S.t && S.t < x.end); if (!c) return;
  const e = list.querySelector(`[data-k="${c.key}"]`); if (e) { e.classList.add('cur'); if (!S.playing) e.scrollIntoView({ block: 'nearest' }); }
}
function highlightSentence() {
  highlightCue();
  const list = $('#sentList'); if (!list) return;
  for (const e of list.querySelectorAll('.sent.cur')) e.classList.remove('cur');
  const s = S.sentences.find(x => x.start - 0.2 <= S.t && S.t <= x.end + 0.2); if (!s) return;
  const e = list.querySelector(`[data-id="${s.id}"]`); if (e) { e.classList.add('cur'); if (!S.playing) e.scrollIntoView({ block: 'nearest' }); }
}

/* ---- Quay (record from the microphone) */
const rec = { mr: null, chunks: [], t0: 0, at: 0 };
PANELS.record = el => {
  el.append(sec('Thu âm từ micro'), h('p', { class: 'muted', style: 'font-size:12px' }, 'Thu một câu đọc thêm, tiếng nền hay hiệu ứng. File lưu ở media/import/ (WAV) rồi đặt vào track bạn chọn, tại vị trí đầu phát lúc bắt đầu thu.'));
  const target = sel(S.recTrack || 'original', [['original', 'Nền'], ['sfx', 'Tiếng động'], ['music', 'Nhạc']], v => { S.recTrack = v; });
  const status = h('div', { class: 'muted', style: 'margin:8px 0' }, rec.mr ? '' : 'Sẵn sàng.');
  const btn = h('button', { class: 'primary', style: 'width:100%' }, rec.mr ? '■ Dừng & lưu' : '● Bắt đầu thu');
  btn.onclick = async () => {
    if (rec.mr) { rec.mr.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      rec.mr = new MediaRecorder(stream); rec.chunks = []; rec.at = S.t; rec.t0 = Date.now();
      rec.mr.ondataavailable = e => rec.chunks.push(e.data);
      rec.mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop()); const blob = new Blob(rec.chunks, { type: rec.mr.mimeType }); rec.mr = null; renderPanel();
        try {
          const { body } = await api(`/api/import?audio=1&name=${encodeURIComponent('thu-am-' + new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '') + '.webm')}`, { method: 'POST', body: blob });
          await ops([{ op: 'add', track: S.recTrack || 'original', clip: { src: body.src, start: rec.at, end: rec.at + body.duration, gain_db: -6, fade_in: 0.05, fade_out: 0.2 } }], `Đã thêm bản thu ${fileName(body.src)} (${body.duration.toFixed(1)} s)`);
          S.lib = {};
        } catch (e) { toast('Không lưu được bản thu: ' + e.message, true); }
      };
      rec.mr.start(); renderPanel();
      const upd = () => { if (!rec.mr) return; const s = $('#recStatus'); if (s) s.textContent = `Đang thu ${((Date.now() - rec.t0) / 1000).toFixed(1)} s · bắt đầu tại ${tc(rec.at)}`; setTimeout(upd, 200); }; upd();
    } catch (e) { toast('Không mở được micro: ' + e.message, true); }
  };
  if (rec.mr) status.append(h('span', { class: 'recdot' }), ' ', h('span', { id: 'recStatus' }, 'Đang thu…'));
  el.append(field('Đặt vào track', target), status, btn);
};

/* ---- Chuyển động */
const MOTION_LABELS = { push: 'Đẩy vào', pull: 'Kéo ra', pan_left: 'Lia trái', pan_right: 'Lia phải', pan_up: 'Lia lên', pan_down: 'Lia xuống', push_left: 'Đẩy lệch trái', push_right: 'Đẩy lệch phải', none: 'Đứng yên', handheld: 'Cầm tay (rung nhẹ)' };
function motionOf(c) {
  const m = c.motion || {};
  if (m.type === 'custom') return JSON.parse(JSON.stringify(m));
  if (m.type === 'none') return { type: 'custom', from: { zoom: 1, x: 0.5, y: 0.5 }, to: { zoom: 1, x: 0.5, y: 0.5 } };
  const dx = m.dx ?? 0.04; const a = { zoom: 1, x: 0.5 - dx * 0.25, y: 0.5 }, b = { zoom: 1.07, x: 0.5 + dx * 0.25, y: 0.5 };  // close to the classic push, as a starting point
  return { type: 'custom', from: m.type === 'pull' ? b : a, to: m.type === 'pull' ? a : b, ease: 'smooth' };
}
PANELS.motion = el => {
  const vids = selectedOn(tr => tr.id === 'video');
  el.append(sec(vids.length ? `Áp cho ${vids.length} cảnh đã chọn` : 'Chọn một hay nhiều cảnh (Shift+click) trên track Cảnh'));
  const grid = h('div', { class: 'grid' });
  for (const [k, m] of Object.entries(S.cat.motion_presets)) grid.append(h('div', { class: 'tile ftile', onclick: () => vids.length ? ops(vids.map(([, c]) => ({ op: 'set', id: c.id, fields: { motion: m } })), `${MOTION_LABELS[k] || k} cho ${vids.length} cảnh`) : toast('Chọn cảnh trước', true) }, MOTION_LABELS[k] || k));
  el.append(grid);
  if (vids.length !== 1) return;
  const c = vids[0][1]; const m = motionOf(c);
  const live = () => draft([{ op: 'set', id: c.id, fields: { motion: m } }]);
  const save = () => ops([{ op: 'set', id: c.id, fields: { motion: m } }], `Đã chỉnh chuyển động ${c.id}`);
  el.append(sec(`Tuỳ chỉnh ${c.id}`), h('p', { class: 'muted', style: 'font-size:11px' }, 'Đặt đầu phát trong cảnh để xem nháp khi kéo. Thả chuột là lưu.'));
  for (const [side, lab] of [['from', 'Đầu cảnh'], ['to', 'Cuối cảnh']]) {
    m[side] = { zoom: 1, x: 0.5, y: 0.5, ...m[side] };
    el.append(h('div', { class: 'muted', style: 'font-size:11px;margin-top:6px' }, lab),
      slider('Phóng', m[side].zoom, [1, 2], 0.01, v => { m[side].zoom = v; live(); }, v => { m[side].zoom = v; save(); }),
      slider('Ngang (x)', m[side].x, [0, 1], 0.005, v => { m[side].x = v; live(); }, v => { m[side].x = v; save(); }),
      slider('Dọc (y)', m[side].y, [0, 1], 0.005, v => { m[side].y = v; live(); }, v => { m[side].y = v; save(); }));
  }
  el.append(field('Gia tốc', sel(m.ease || 'smooth', [['smooth', 'Mượt'], ['linear', 'Đều'], ['in', 'Chậm → nhanh'], ['out', 'Nhanh → chậm']], v => { m.ease = v; save(); })),
    slider('Rung tay', m.shake || 0, [0, 1], 0.05, v => { m.shake = v; live(); }, v => { m.shake = v; save(); }),
    h('div', { class: 'toolbar' }, h('button', { onclick: () => seek(c.start + 0.05) }, 'Đầu cảnh'), h('button', { onclick: () => seek((c.start + c.end) / 2) }, 'Giữa cảnh'), h('button', { onclick: () => seek(c.end - 0.05) }, 'Cuối cảnh')));
};

/* ---- Hiệu ứng */
function addEffect(type, params, t, d, trackId, label) {
  const fxTracks = S.tl.tracks.filter(tr => tr.kind === 'fx'); const list = [];
  let tid = trackId || (fxTracks.find(tr => !tr.clips.some(c => c.start < t + d && c.end > t)) || {}).id;
  if (!tid) { const n = fxTracks.length + 1; tid = n > 1 ? `fx${n}` : 'fx'; list.push({ op: 'add_track', kind: 'fx', id: tid, name: n > 1 ? `Hiệu ứng ${n}` : 'Hiệu ứng' }); }
  list.push({ op: 'add', track: tid, clip: { type, label, start: t, end: Math.min(dur(), t + d), params: { ...(S.cat.effects[type] || {}), ...params }, opacity: 1, fade_in: 0.3, fade_out: 0.3 } });
  return ops(list, `Đã thêm ${label || FX_NAMES[type]} ${tc(t)} → ${tc(Math.min(dur(), t + d))}`);
}
PANELS.effects = el => {
  const [a, b] = playheadSpan();
  el.append(sec('Thêm hiệu ứng'), h('p', { class: 'muted', style: 'font-size:11px' }, `Bấm ô: thêm cho ${selectedOn(tr => tr.id === 'video').length ? 'cảnh đang chọn' : '10 s từ đầu phát'} (${tc(a)} → ${tc(b)}). Kéo ô vào track Hiệu ứng để đặt chỗ khác; kéo mép clip hiệu ứng để đổi độ dài. Chọn clip hiệu ứng để chỉnh thông số ở bảng bên phải.`));
  const grid = h('div', { class: 'grid' });
  for (const [label, type, params] of S.cat.effect_presets) {
    const tile = h('div', { class: 'tile ftile', onclick: () => type === 'media_overlay' ? chooseOverlay(null, { ...S.cat.effects.media_overlay }, a, b - a) : addEffect(type, params, a, b - a, null, label) }, label);
    draggable(tile, { kind: 'effect', type, params, label, dur: 10 }); grid.append(tile);
  }
  el.append(grid, sec('Cả phim'), h('div', { class: 'toolbar' },
    h('button', { onclick: () => { const p = S.cat.effect_presets[0]; addEffect(p[1], p[2], 0, dur(), null, p[0] + ' (cả phim)'); } }, 'Phim cũ nhẹ cho cả phim'),
    h('button', { onclick: () => addEffect('grain', { amount: 0.3 }, 0, dur(), null, 'Hạt phim (cả phim)') }, 'Hạt phim cả phim')),
    h('p', { class: 'muted', style: 'font-size:11px' }, 'Lưu ý: hiệu ứng trên cả phim nghĩa là lần xuất sau dựng lại toàn bộ hình (lâu). Nên thử trên một đoạn rồi "Dựng xem trước" trước.'),
    sec('Lớp phủ từ file của bạn'), h('p', { class: 'muted', style: 'font-size:11px' }, 'Video/ảnh bụi phim, hạt, lóa sáng, logo… Chọn kiểu hoà trộn (Screen cho nền đen, Multiply cho nền trắng) và hạ Độ đậm.'),
    h('button', { class: 'primary', onclick: () => chooseOverlay(null, { ...S.cat.effects.media_overlay }, a, b - a) }, '＋ Thêm lớp phủ media…'));
};
function effectControls(c) {
  const box = h('div', {}); const p = { ...(S.cat.effects[c.type] || {}), ...(c.params || {}) };
  const live = (k, v) => draft([{ op: 'set', id: c.id, fields: { params: { ...p, [k]: v } } }]);
  const save = (k, v) => { p[k] = v; ops([{ op: 'set', id: c.id, fields: { params: { ...p } } }], `Đã chỉnh ${c.id}`); };
  const NAMES = { grain: 'Hạt', scratches: 'Vết xước', dust: 'Bụi', flicker: 'Nháy', jitter: 'Rung khung', vignette: 'Viền tối', sepia: 'Sepia', amount: 'Mức', size: 'Kích thước', hue: 'Màu (độ)', speed: 'Tốc độ', radius: 'Bán kính', ratio: 'Tỉ lệ', x: 'Vị trí ngang', y: 'Vị trí dọc',
    exposure: 'Phơi sáng', brightness: 'Độ sáng', contrast: 'Tương phản', saturation: 'Bão hoà', temperature: 'Nhiệt màu', tint: 'Tint', gamma: 'Gamma', fade: 'Bạc màu', shadows: 'Vùng tối', highlights: 'Vùng sáng' };
  box.append(field('Tên', txt(c.label || '', v => setF(c, { label: v || null }))),
    slider('Độ đậm', c.opacity ?? 1, [0, 1], 0.01, v => draft([{ op: 'set', id: c.id, fields: { opacity: v } }]), v => setF(c, { opacity: v })),
    slider('Fade vào', c.fade_in || 0, [0, 5], 0.05, null, v => setF(c, { fade_in: v }), v => (+v).toFixed(2) + ' s'),
    slider('Fade ra', c.fade_out || 0, [0, 5], 0.05, null, v => setF(c, { fade_out: v }), v => (+v).toFixed(2) + ' s'));
  if (c.type === 'media_overlay') {
    box.append(sec('Lớp phủ'), h('div', { class: 'toolbar' }, h('span', { class: 'kv' }, p.src || '(chưa chọn file)'), h('button', { onclick: () => chooseOverlay(c, p) }, 'Chọn file…')),
      p.src ? h('img', { src: '/api/thumb?w=280&src=' + encodeURIComponent(p.src), style: 'width:100%;border-radius:4px' }) : null,
      field('Hoà trộn', sel(p.blend || 'screen', S.cat.blends.map(b => [b, { normal: 'Thường', screen: 'Screen (bỏ nền đen)', multiply: 'Multiply (bỏ nền trắng)', overlay: 'Overlay', add: 'Cộng sáng', lighten: 'Lighten', darken: 'Darken', soft_light: 'Soft light' }[b] || b]), v => save('blend', v))),
      field('Khung', sel(p.scale || 'cover', [['cover', 'Phủ kín'], ['contain', 'Vừa khung'], ['stretch', 'Kéo giãn']], v => save('scale', v))),
      field('Lặp', h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: p.loop !== false, onchange: e => save('loop', e.target.checked) }), 'lặp video lớp phủ')));
    for (const k of ['size', 'x', 'y', 'speed']) box.append(slider(NAMES[k], p[k], S.cat.ranges[k] || [0, 1], 0.01, v => live(k, v), v => save(k, v)));
    return box;
  }
  box.append(sec('Thông số'));
  for (const [k, v] of Object.entries(p)) {
    if (typeof v !== 'number') continue;
    const rg = S.cat.ranges[k] || [0, 1]; const step = rg[1] - rg[0] > 10 ? 1 : 0.01;
    box.append(slider(NAMES[k] || k, v, rg, step, x => live(k, x), x => save(k, x)));
  }
  box.append(h('button', { onclick: () => setF(c, { params: { ...(S.cat.effects[c.type] || {}) } }, 'Về thông số mặc định') }, 'Về mặc định'));
  return box;
}
/* c = existing effect clip (change its file) or null (new overlay over [t, t+d]) */
async function chooseOverlay(c, p, t, d) {
  $('#modalTitle').textContent = 'Chọn media cho lớp phủ'; const body = $('#modalBody'); body.innerHTML = '';
  const fill = async () => {
    body.innerHTML = ''; body.append(dropZone('Thả video/ảnh lớp phủ (bụi phim, hạt, lóa sáng, logo…) để nhập', fill));
    const files = (await loadLib('overlays', true)).concat(await loadLib('project', true)).filter(f => f.kind !== 'audio');
    mediaGrid(body, files, f => {
      closeModal();
      if (c) setF(c, { params: { ...p, src: f.src } }, 'Đã chọn ' + f.name);
      else addEffect('media_overlay', { ...p, src: f.src }, t ?? S.t, d ?? 10, null, 'Lớp phủ ' + f.name);
    });
  };
  await fill(); $('#modal').classList.remove('hidden');
}

/* ---- Chuyển cảnh */
const TRANS_LABELS = { '': 'Cắt thẳng', fade: 'Hoà', dip: 'Qua đen', dip_white: 'Qua trắng', wipe_left: 'Gạt trái', wipe_right: 'Gạt phải', wipe_up: 'Gạt lên', wipe_down: 'Gạt xuống', slide_left: 'Trượt trái', slide_right: 'Trượt phải', slide_up: 'Trượt lên', slide_down: 'Trượt xuống', zoom: 'Phóng qua', blur: 'Mờ qua', circle_open: 'Mở tròn', circle_close: 'Đóng tròn', pixelize: 'Vỡ điểm ảnh', radial: 'Quét tròn' };
PANELS.trans = el => {
  const vids = selectedOn(tr => tr.id === 'video');
  S.transDur = S.transDur || 0.6;
  el.append(sec(vids.length ? `Áp vào đầu ${vids.length} cảnh đã chọn` : 'Chọn cảnh (Shift+click chọn nhiều): chuyển cảnh nằm ở đầu cảnh'));
  el.append(slider('Độ dài', S.transDur, [0.1, 3], 0.05, v => { S.transDur = v; }, v => { S.transDur = v; }, v => (+v).toFixed(2) + ' s'));
  const grid = h('div', { class: 'grid' });
  for (const k of ['', ...S.cat.transitions]) {
    const on = vids.length && vids.every(([, c]) => ((c.transition_in || {}).type || '') === k);
    grid.append(h('div', { class: 'tile ftile' + (on ? ' on' : ''), onclick: () => vids.length
      ? ops(vids.map(([, c]) => ({ op: 'set', id: c.id, fields: { transition_in: k ? { type: k, dur: S.transDur } : null } })), `${TRANS_LABELS[k] || k} cho ${vids.length} cảnh`).then(() => { if (vids.length === 1) seek(vids[0][1].start + Math.min(0.3, S.transDur / 2)); })
      : toast('Chọn cảnh trước', true) }, TRANS_LABELS[k] || k));
  }
  el.append(grid, h('p', { class: 'muted', style: 'font-size:11px' }, 'Tam giác trắng ở đầu clip trên track Cảnh = có chuyển cảnh. Đầu phát tự nhảy vào giữa chuyển cảnh để bạn xem; phát thử từ trước điểm cắt.'));
};

/* ---- Màu */
const COLOR_NAMES = { exposure: 'Phơi sáng', brightness: 'Độ sáng', contrast: 'Tương phản', saturation: 'Bão hoà', temperature: 'Nhiệt màu', tint: 'Tint (xanh↔hồng)', gamma: 'Gamma', shadows: 'Vùng tối', highlights: 'Vùng sáng', fade: 'Bạc màu', sepia: 'Sepia' };
PANELS.color = el => {
  const vids = selectedOn(tr => tr.id === 'video');
  el.append(sec(vids.length ? `Màu cho ${vids.length} cảnh đã chọn` : 'Chọn cảnh (Shift+click chọn nhiều) để chỉnh màu riêng'));
  const grid = h('div', { class: 'grid' });
  for (const [label, p] of Object.entries(S.cat.color_presets)) grid.append(h('div', { class: 'tile ftile', onclick: () => vids.length ? ops(vids.map(([, c]) => ({ op: 'set', id: c.id, fields: { color: Object.keys(p).length ? p : null } })), `Màu "${label}" cho ${vids.length} cảnh`) : toast('Chọn cảnh trước', true) }, label));
  el.append(grid);
  if (vids.length) {
    const base = { ...S.cat.color_default, ...(vids[0][1].color || {}) };
    const fields = v => vids.map(([, c]) => ({ op: 'set', id: c.id, fields: { color: v } }));
    for (const k of Object.keys(S.cat.color_default)) {
      el.append(slider(COLOR_NAMES[k] || k, base[k], S.cat.ranges[k] || [0, 1], 0.01, v => { base[k] = v; draft(fields({ ...base })); }, v => { base[k] = v; ops(fields({ ...base }), `Đã chỉnh màu ${vids.length} cảnh`); }));
    }
    el.append(h('div', { class: 'toolbar' }, h('button', { onclick: () => ops(fields(null), 'Bỏ chỉnh màu') }, 'Bỏ chỉnh màu'),
      h('label', { class: 'muted' }, 'Màu nền: ', sel(vids[0][1].grade || 'archival', [['archival', 'Tư liệu (sepia)'], ['film', 'Phim cũ'], ['modern', 'Hiện đại'], ['none', 'Giữ nguyên']], v => ops(vids.map(([, c]) => ({ op: 'set', id: c.id, fields: { grade: v } })), 'Đổi màu nền')))));
  }
  el.append(sec('Cả một đoạn / cả phim'), h('p', { class: 'muted', style: 'font-size:11px' }, 'Thêm lớp "Chỉnh màu" trên track Hiệu ứng: áp lên mọi cảnh trong khoảng đó, có fade vào/ra. Chọn clip đó để chỉnh thanh trượt.'),
    h('div', { class: 'toolbar' }, h('button', { onclick: () => addEffect('color', { saturation: 0.8 }, ...playheadSpanArgs(), null, 'Chỉnh màu đoạn') }, 'Lớp màu cho đoạn này'),
      h('button', { onclick: () => addEffect('color', { saturation: 0.85, contrast: 1.05 }, 0, dur(), null, 'Chỉnh màu cả phim') }, 'Lớp màu cả phim')));
};

/* ---- Góp ý */
PANELS.notes = el => {
  const notes = S.tl.review_notes || []; const cnt = st => notes.filter(n => st === 'all' || n.status === st).length;
  el.append(h('button', { class: S.noting ? 'on' : 'primary', style: 'width:100%', onclick: () => setNoting(!S.noting) }, S.noting ? '◎ Tắt chế độ góp ý (C / Esc)' : '◎ Bật chế độ góp ý (C)'));
  el.append(h('div', { class: 'chips' }, [['all', 'Tất cả'], ['open', 'Mở'], ['doing', 'Đang sửa'], ['done', 'Xong']].map(([k, l]) =>
    h('button', { class: S.noteFilter === k ? 'on' : '', onclick: () => { S.noteFilter = k; renderPanel(); } }, `${l} ${cnt(k)}`))));
  const list = notes.filter(n => S.noteFilter === 'all' || n.status === S.noteFilter).sort((a, b) => a.t - b.t);
  if (!list.length) el.append(empty(notes.length ? 'Không có góp ý ở mục này.' : 'Chưa có góp ý. Dừng hình ở chỗ cần sửa, bấm C (hoặc nút Góp ý), kéo khung trên hình rồi gõ góp ý. Agent đọc bằng list_review_notes.'));
  for (const n of list) {
    const s = sel(n.status, [['open', 'Mở'], ['doing', 'Đang sửa'], ['done', 'Xong']], v => noteOp({ op: 'update', id: n.id, status: v }));
    s.addEventListener('click', e => e.stopPropagation());
    el.append(h('div', { class: 'note', onclick: () => seek(n.t) },
      h('div', { class: 'h' }, h('b', { class: 'st-' + n.status }, n.id), h('span', { class: 'mono' }, tc(n.t)), h('span', {}, n.author === 'agent' ? 'agent' : ''), h('div', { class: 'grow' }), s,
        h('button', { title: 'Xoá góp ý', onclick: e => { e.stopPropagation(); if (confirm(`Xoá góp ý ${n.id}?`)) noteOp({ op: 'delete', id: n.id }); } }, '✕')),
      h('div', { class: 'tx' }, n.text), n.reply ? h('div', { class: 'rp' }, '↳ ' + n.reply) : null));
  }
  el.append(h('div', { class: 'muted', style: 'margin-top:8px;font-size:12px' }, `${notes.length} góp ý · ${cnt('open')} mở`));
};

/* ---- Bản dựng */
let rangeVals = null;
function fillRange(a, b) { rangeVals = [Math.max(0, a), Math.min(dur(), b)]; switchTab('build'); }
PANELS.build = el => {
  if (!rangeVals) rangeVals = [Math.max(0, S.t - 3), Math.min(dur(), S.t + 9)];
  const dirty = S.dirty || [];
  const a = h('input', { type: 'number', step: 0.1, value: rangeVals[0].toFixed(2) }), b = h('input', { type: 'number', step: 0.1, value: rangeVals[1].toFixed(2) });
  const mode = sel(S.prevMode || 'auto', [['auto', 'Tự động'], ['fast', 'Nhanh (vẽ 12 khung/giây, như Whisk)'], ['frames', 'Luôn dựng khung hình'], ['cut', 'Cắt từ picture.mp4']], v => { S.prevMode = v; });
  el.append(sec('Xem trước một đoạn (MP4 có tiếng)'), field('Từ (s)', a), field('Đến (s)', b), field('Hình', mode),
    h('div', { class: 'row' }, h('button', { onclick: () => { a.value = Math.max(0, S.t - 3).toFixed(2); b.value = Math.min(dur(), S.t + 9).toFixed(2); } }, 'Quanh đầu phát'),
      h('div', { class: 'grow' }), h('button', { class: 'primary', onclick: async () => {
        rangeVals = [parseFloat(a.value), parseFloat(b.value)];
        try { const { body } = await post('/api/render', { t0: rangeVals[0], t1: rangeVals[1], mode: mode.value }); toast('Đang dựng xem trước ' + body.job); pollJobs(); }
        catch (e) { toast(e.message, true); }
      } }, 'Dựng xem trước')),
    h('p', { class: 'muted', style: 'font-size:12px' }, 'Tự động: đoạn có sửa hình thì dựng khung từ timeline, đoạn chỉ đổi tiếng thì cắt từ picture.mp4 rồi trộn lại tiếng. Tối đa 180 s.'));
  el.append(sec('Xuất bản'));
  if (!S.proj.picture) el.append(h('p', {}, 'Chưa có render/picture.mp4: xuất bản sẽ dựng toàn bộ hình (rất lâu).'));
  else if (dirty.length) {
    const tot = dirty.reduce((s, [x, y]) => s + (y - x), 0);
    el.append(h('p', {}, `Hình đã sửa ở ${dirty.length} đoạn (${tot.toFixed(1)} s): chỉ dựng lại các đoạn này rồi ghép vào picture.mp4, sau đó trộn lại toàn bộ tiếng.`));
    for (const [x, y] of dirty.slice(0, 30)) el.append(h('div', { class: 'rng' }, `${tc(x)} → ${tc(y)}`, h('button', { onclick: () => seek(x) }, 'Xem'), h('button', { onclick: () => fillRange(x - 1, Math.min(y + 1, x + 179)) }, 'Xem trước')));
  } else el.append(h('p', {}, 'Hình chưa đổi: xuất nhanh = trộn lại tiếng rồi ghép vào picture.mp4, không dựng khung hình.'));
  el.append(h('p', { class: 'muted', style: 'font-size:12px' }, `Lần xuất đầu tiên ra output/${S.proj.id}/video.mp4; các lần sau ra video-studio-<giờ>.mp4, không ghi đè video.mp4.`), h('button', { class: 'primary', style: 'width:100%', onclick: doExport }, '⇪ Xuất bản'));
  const cfgBox = h('div', {});
  el.append(sec('Tốc độ dựng'), cfgBox);
  api('/api/settings').then(({ body: c }) => {
    const save = f => post('/api/settings', f).then(() => toast('Đã lưu thiết lập dựng'));
    cfgBox.append(
      slider('Luồng song song', c.render_workers, [1, Math.min(16, c.cpu_count || 8)], 1, null, v => save({ render_workers: v }), v => Math.round(v)),
      h('label', { class: 'chk', style: 'display:flex' }, h('input', { type: 'checkbox', checked: c.gpu_render !== false, onchange: e => save({ gpu_render: e.target.checked }) }),
        'Vẽ khung bằng GPU (OpenGL): ~150 khung/giây thay vì ~22; tắt nếu máy không có card rời'),
      h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: !!c.gpu_encode, disabled: !c.nvenc, onchange: e => save({ gpu_encode: e.target.checked }) }),
        c.nvenc ? 'Mã hoá bằng card NVIDIA (NVENC) cho bản xem trước và dựng lại toàn bộ' : 'Không thấy NVENC: mã hoá bằng CPU'),
      h('p', { class: 'muted', style: 'font-size:11px' }, `Máy có ${c.cpu_count} luồng CPU. Mỗi luồng dựng một phần của đoạn rồi ghép lại. Đoạn ghép vào picture.mp4 cũ luôn mã hoá bằng x264 để khớp file gốc.`));
  });
  el.append(sec('Việc đang chạy / vừa xong'), h('div', { id: 'jobList' }), sec('Bản đã xuất'), h('div', { id: 'expList' }));
  renderJobs(); renderExports();
};
let jobsCache = [];
async function pollJobs() {
  try { const { body } = await api('/api/jobs'); jobsCache = body.jobs; } catch (e) { return; }
  for (const j of jobsCache) {
    const was = S.jobsSeen[j.id];
    if (was && was !== j.status && (j.status === 'done' || j.status === 'error')) {
      if (j.status === 'done' && j.kind === 'preview') { toast(`Xem trước xong (${j.result.seconds} s)`); openPreview(j); }
      else if (j.status === 'done') { toast('Xuất bản xong: ' + j.result.path); refreshProject(); }
      else toast(`${j.kind} lỗi: ${j.error}`, true);
    }
    S.jobsSeen[j.id] = j.status;
  }
  if (S.tab === 'build') renderJobs();
}
function renderJobs() {
  const el = $('#jobList'); if (!el) return; el.innerHTML = '';
  if (!jobsCache.length) el.append(h('div', { class: 'muted' }, 'Chưa có.'));
  for (const j of jobsCache.slice(0, 8)) {
    const a = j.args || {};
    el.append(h('div', { class: 'job' },
      h('div', { class: 'row' }, h('b', {}, j.kind === 'preview' ? `Xem trước ${mmss(a.t0)}–${mmss(a.t1)}` : 'Xuất bản'), h('span', { class: 'st-' + (j.status === 'done' ? 'done' : j.status === 'error' ? 'open' : 'doing') }, j.status), h('div', { class: 'grow' }),
        j.status === 'running' ? h('button', { onclick: () => api(`/api/jobs/${j.id}/cancel`, { method: 'POST' }).then(pollJobs) }, 'Dừng') : null,
        j.status === 'done' && j.kind === 'preview' ? h('button', { class: 'primary', onclick: () => openPreview(j) }, '▶ Xem') : null),
      j.status === 'running' ? h('div', { class: 'bar' }, h('i', { style: `width:${Math.round((j.progress || 0) * 100)}%` })) : null,
      h('pre', {}, (j.error ? j.error + '\n' : '') + (j.log || []).slice(-3).join('\n'))));
  }
}
async function renderExports() {
  const el = $('#expList'); if (!el) return;
  try {
    const { body } = await api('/api/exports'); el.innerHTML = '';
    for (const f of body.files) el.append(h('div', { class: 'rng' }, h('a', { href: '/exports/' + f.name, target: '_blank', style: 'color:var(--accent)' }, f.name), h('span', { class: 'muted' }, `${(f.size / 1e9).toFixed(2)} GB · ${f.mtime}`)));
  } catch (e) { /* ignore */ }
}
function openPreview(j) {
  const r = j.result; $('#modalTitle').textContent = `Xem trước ${tc(r.t0)} → ${tc(r.t1)} · ${r.frames_rendered ? 'dựng khung từ timeline' : 'cắt từ picture.mp4'}` + (r.loudness ? ` · ${r.loudness.I} LUFS, đỉnh ${r.loudness.TP} dB` : '');
  const v = h('video', { src: r.url, controls: true, autoplay: true }); $('#modalBody').innerHTML = ''; $('#modalBody').append(v, h('div', { class: 'kv' }, r.path));
  stop(); $('#modal').classList.remove('hidden');
}
async function doExport() {
  const dirty = S.dirty || [];
  const what = !S.proj.picture ? 'dựng TOÀN BỘ hình (rất lâu)' : dirty.length ? `dựng lại ${dirty.length} đoạn hình đã sửa, ghép vào picture.mp4, trộn lại tiếng` : 'chỉ trộn lại tiếng rồi ghép vào picture.mp4';
  if (!confirm(`Xuất bản ${S.proj.id}?\n\nSẽ ${what}.\nRa output/${S.proj.id}/video.mp4 nếu chưa có, có rồi thì video-studio-<giờ>.mp4 (không ghi đè video.mp4).`)) return;
  try { const { body } = await api('/api/export', { method: 'POST' }); toast('Bắt đầu xuất bản: ' + body.job); switchTab('build'); pollJobs(); }
  catch (e) { toast(e.message, true); }
}

/* ---- Lịch sử */
PANELS.log = el => {
  el.append(h('p', { class: 'muted', style: 'font-size:12px' }, 'Mỗi lần ghi timeline.json (của bạn hay của agent) đều giữ bản trước trong render/studio/history.'));
  for (const r of (S.proj.history || []).slice().reverse()) el.append(h('div', { class: 'job' }, h('div', { class: 'row' }, h('b', {}, r.who === 'agent' ? 'Agent' : r.who === 'user' ? 'Bạn' : r.who), h('span', { class: 'muted mono' }, r.t)), h('div', { style: 'font-size:12px' }, r.why)));
  const st = S.proj.state;
  if (st) el.append(sec('picture.mp4'), h('div', { class: 'kv' }, `ghi nhận ${st.saved}${st.assumed ? ' (giả định khớp timeline lúc mở studio lần đầu)' : ''}`));
};

// ------------------------------------------------------------------ inspector (right)
const setF = (c, fields, label) => ops([{ op: 'set', id: c.id, fields }], label || `Đã sửa ${c.id}`);
function anchorText(a) {
  if (!a) return 'không neo (đứng yên khi giọng đổi)';
  return `${a.sentence || 'cue ' + a.cue}${a.word != null ? ' từ ' + a.word : a.edge === 'end' ? ' cuối câu' : ' đầu câu'}${a.offset ? ` ${a.offset > 0 ? '+' : ''}${a.offset}s` : ''}`;
}
function renderInspector() {
  const el = $('#inspBody'); if (!S.tl || !S.cat) return; el.innerHTML = '';
  const sels = selected();
  $('#selInfo').textContent = sels.length > 1 ? `${sels.length} clip` : '';
  if (sels.length > 1) {
    el.append(h('p', {}, `${sels.length} clip đang chọn: ${sels.map(([, c]) => c.id).join(', ')}`),
      h('p', { class: 'muted' }, 'Dùng tab Màu / Chuyển động / Chuyển cảnh để áp cho cả nhóm, Delete để xoá.'));
    const au = sels.filter(([tr]) => ['music', 'original', 'sfx'].includes(tr.id));
    if (au.length) el.append(slider('Âm lượng (nhóm)', au[0][1].gain_db ?? -12, [-40, 6], 0.5, null, v => ops(au.map(([, c]) => ({ op: 'set', id: c.id, fields: { gain_db: v } })), `Âm lượng ${au.length} clip: ${v} dB`), v => (+v).toFixed(1) + ' dB'));
    return;
  }
  const [tr, c] = findClip(S.sel || '');
  if (!c) {
    el.append(h('div', { class: 'empty' }, 'Chọn một clip trên timeline.', h('br'), `Đầu phát: ${tc(S.t)}`));
    const v = clipAt('video', S.t); if (v) el.append(sec('Cảnh ở đầu phát'), h('div', { class: 'kv' }, `${v.id} · ${v.src || ''}`), h('div', { class: 'muted', style: 'font-size:12px;margin-top:4px' }, v.need || ''));
    const s = S.sentences.find(x => x.start - 0.2 <= S.t && S.t <= x.end + 0.2); if (s) el.append(sec('Lời đọc ' + s.id), h('div', {}, s.text));
    return;
  }
  const st = styleOf(tr);
  el.append(h('div', { class: 'row' }, h('b', { style: `color:${st.color}` }, `${tr.kind === 'fx' ? tr.name || st.name : st.name} · ${c.id}`), h('div', { class: 'grow' }), h('button', { onclick: () => seek(c.start) }, 'Tới')));
  if (tr.id === 'voice') {
    el.append(h('p', {}, c.text), field('Bắt đầu', h('span', { class: 'mono' }, tc(c.start))), field('Kết thúc', h('span', { class: 'mono' }, tc(c.end))),
      field('Cảm xúc', h('span', {}, c.emotion || '')), field('Nghỉ sau', h('span', {}, (c.pause_after ?? '') + ' s')),
      h('p', { class: 'muted' }, 'Lời đọc khoá trong studio. Đổi câu/khoảng nghỉ bằng doc.py (assemble) rồi mọi clip có neo tự dời theo.'));
    return;
  }
  el.append(field('Bắt đầu', num(c.start, v => setF(c, { start: v }), 1 / fps())), field('Kết thúc', num(c.end, v => setF(c, { end: v }), 1 / fps())),
    field('Độ dài', h('span', { class: 'mono' }, ((c.end ?? c.start) - c.start).toFixed(2) + ' s')),
    field('Neo', h('span', { class: 'kv' }, anchorText(c.anchor) + (c.end_anchor ? ' → ' + anchorText(c.end_anchor) : ''))));
  if (tr.id === 'video') {
    el.append(sec('Hình'),
      c.src ? h('img', { src: '/api/thumb?w=280&src=' + encodeURIComponent(c.src), style: 'width:100%;border-radius:4px;margin:4px 0' }) : null,
      field('Nguồn', txt(c.src, v => setF(c, { src: v || null }))),
      field('Chú thích', txt(c.caption, v => setF(c, { caption: v || null }))),
      field('Nguồn ảnh', txt(c.credit, v => setF(c, { credit: v || null }))),
      h('div', { class: 'toolbar' }, h('button', { onclick: () => switchTab('color') }, 'Màu…'), h('button', { onclick: () => switchTab('motion') }, 'Chuyển động…'), h('button', { onclick: () => switchTab('trans') }, 'Chuyển cảnh…'), h('button', { onclick: () => switchTab('media') }, 'Thay ảnh…')),
      c.need ? h('div', { class: 'muted', style: 'font-size:12px;margin-top:6px' }, c.need) : null);
  } else if (tr.id === 'overlay') {
    el.append(sec(OVERLAY_NAMES[c.type] || c.type), overlayForm(c));
  } else if (tr.kind === 'fx') {
    el.append(sec(FX_NAMES[c.type] || c.type), effectControls(c));
  } else {
    el.append(sec('Âm thanh'), audioControls(tr, c), field('Nguồn', txt(c.src, v => setF(c, { src: v }))), field('Từ giây', num(c.in ?? 0, v => setF(c, { in: v }), 0.05)));
  }
  el.append(h('div', { class: 'toolbar', style: 'margin-top:12px' }, h('button', { onclick: splitSel }, '✂ Tách'), h('button', { onclick: deleteSel }, '🗑 Xoá'),
    h('div', { class: 'grow' }), h('button', { onclick: () => fillRange(c.start - 1, Math.min((c.end ?? c.start) + 1, c.start + 179)) }, 'Dựng xem trước')));
}
function overlayForm(c) {
  const box = h('div', {}); const p = JSON.parse(JSON.stringify(c.props || {}));
  const save = () => setF(c, { props: p });
  const live = (k, v) => { p[k] = v; draft([{ op: 'set', id: c.id, fields: { props: { ...p } } }]); };
  const commit = (k, v) => { p[k] = v; save(); };
  const ta = (k, label, rows = 2) => { const t = h('textarea', { rows }); t.value = Array.isArray(p[k]) ? p[k].join('\n') : (p[k] ?? ''); t.onchange = () => { p[k] = k === 'lines' ? t.value.split('\n') : t.value; save(); }; return field(label, t); };
  const tx = (k, label) => field(label, txt(p[k], v => { p[k] = v; save(); }));
  box.append(field('Loại', sel(c.type, Object.entries(OVERLAY_NAMES), v => setF(c, { type: v }))));
  if (c.type === 'text') {
    const d = { ...S.cat.text_default, ...p };
    box.append(ta('text', 'Nội dung', 3),
      slider('Cỡ chữ', d.size, [16, 220], 1, v => live('size', v), v => commit('size', v), v => Math.round(v)),
      slider('Ngang (x)', d.x, [0, 1], 0.005, v => live('x', v), v => commit('x', v)), slider('Dọc (y)', d.y, [0, 1], 0.005, v => live('y', v), v => commit('y', v)),
      field('Căn', sel(d.align, [['center', 'Giữa'], ['left', 'Trái'], ['right', 'Phải']], v => commit('align', v))),
      field('Phông', sel(d.font, [['head', 'Oswald (tiêu đề)'], ['body', 'Be Vietnam Pro'], ['bodyreg', 'Be Vietnam Pro mảnh'], ['mono', 'IBM Plex Mono'], ['monomed', 'IBM Plex Mono đậm']], v => commit('font', v))),
      field('Màu chữ', h('input', { type: 'color', class: 'colorin', value: d.color, onchange: e => commit('color', e.target.value) })),
      slider('Viền', d.stroke, [0, 10], 1, v => live('stroke', v), v => commit('stroke', v), v => Math.round(v)),
      slider('Bóng', d.shadow, [0, 1], 0.05, v => live('shadow', v), v => commit('shadow', v)),
      slider('Nền hộp', d.box, [0, 1], 0.05, v => live('box', v), v => commit('box', v)),
      field('Màu nền', h('input', { type: 'color', class: 'colorin', value: d.box_color, onchange: e => commit('box_color', e.target.value) })),
      field('Hiệu ứng vào', sel(d.anim, [['fade', 'Hiện dần'], ['slide_up', 'Trượt lên'], ['slide_left', 'Trượt ngang'], ['typewriter', 'Đánh máy'], ['none', 'Không']], v => commit('anim', v))),
      field('IN HOA', h('label', { class: 'chk' }, h('input', { type: 'checkbox', checked: !!d.upper, onchange: e => commit('upper', e.target.checked) }), 'viết hoa')));
  } else if (['date_tag', 'callout', 'question'].includes(c.type)) box.append(tx('text', 'Chữ'));
  else if (c.type === 'lower_third') box.append(tx('kicker', 'Dòng nhỏ'), tx('name', 'Tên'), tx('sub', 'Vai trò'));
  else if (c.type === 'title_card') box.append(tx('text', 'Tiêu đề'), tx('sub', 'Dòng phụ'));
  else if (c.type === 'chapter') box.append(field('Số', num(p.n, v => { p.n = v; save(); }, 1)), tx('title', 'Tên chương'));
  else if (c.type === 'quote') box.append(tx('kicker', 'Dòng nhỏ'), tx('title', 'Tiêu đề'), ta('lines', 'Các dòng', 4), tx('highlight', 'Tô sáng'), tx('source', 'Nguồn'), field('Tốc độ gõ', num(p.cps ?? 16, v => { p.cps = v; save(); }, 1)));
  if (!['text', 'date_tag', 'callout', 'question', 'lower_third', 'title_card', 'chapter', 'quote'].includes(c.type)) {
    const t = h('textarea', { rows: 8, class: 'mono', style: 'font-size:12px' }); t.value = JSON.stringify(p, null, 1);
    box.append(h('label', { class: 'muted' }, 'Nội dung (JSON)'), t, h('button', { class: 'primary', onclick: () => { try { setF(c, { props: JSON.parse(t.value) }); } catch (e) { toast('JSON sai: ' + e.message, true); } } }, 'Áp dụng'));
  }
  return box;
}

// ------------------------------------------------------------------ agent + keys + buttons
function agentInfo() {
  $('#modalTitle').textContent = 'Agent (Claude Code qua MCP)';
  const notes = (S.tl.review_notes || []).filter(n => n.status !== 'done');
  $('#modalBody').innerHTML = '';
  $('#modalBody').append(
    h('p', {}, 'Mở Claude Code trong thư mục documentary-workflow (server MCP "documentary-studio" khai báo trong .mcp.json, duyệt một lần). Agent đọc góp ý, sửa timeline, xem lại khung hình; thay đổi hiện ở đây sau vài giây.'),
    h('p', {}, `Góp ý đang mở: ${notes.length}.`), h('p', { class: 'muted' }, 'Câu lệnh gợi ý (dán vào Claude Code):'),
    h('pre', { class: 'kv', style: 'white-space:pre-wrap;background:#0e1014;padding:8px;border-radius:6px' }, `Đọc các góp ý đang mở của phim ${S.proj.id} bằng list_review_notes, sửa từng cái bằng update_clips, kiểm tra bằng render_frame, rồi đặt góp ý sang "doing" kèm trả lời. Không xuất bản.`),
    h('p', { class: 'muted' }, 'Công cụ: get_timeline, update_clips, list_review_notes, set_note_status, render_frame, render_preview, export, get_job, effect_catalog.'));
  $('#modal').classList.remove('hidden');
}
function help() {
  $('#modalTitle').textContent = 'Phím tắt';
  const rows = [['Space', 'Phát / dừng'], ['← / →', 'Lùi / tới 1 khung'], ['Shift + ← / →', 'Lùi / tới 5 giây'], ['Home / End', 'Đầu / cuối phim'], ['[ / ]', 'Câu trước / câu sau'], ['C', 'Bật/tắt chế độ góp ý'], ['Esc', 'Thoát góp ý, bỏ chọn'],
    ['S', 'Tách clip tại đầu phát'], ['Delete', 'Xoá clip đang chọn'], ['Shift / Ctrl + click', 'Chọn nhiều clip'], ['Ctrl+Z / Ctrl+Shift+Z', 'Hoàn tác / làm lại'], ['+ / −', 'Phóng to / thu nhỏ timeline'], ['Ctrl + cuộn', 'Phóng to quanh chuột'], ['Shift + cuộn', 'Cuộn ngang'], ['Alt khi kéo', 'Tắt hút mốc; mép cảnh chỉ kéo một bên; thả media lên cảnh = thay ảnh']];
  $('#modalBody').innerHTML = ''; $('#modalBody').append(h('table', { class: 'kb' }, rows.map(([k, v]) => h('tr', {}, h('td', {}, k), h('td', {}, v)))));
  $('#modal').classList.remove('hidden');
}
document.addEventListener('keydown', e => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (e.target.id === 'subText' || (e.target.closest && e.target.closest('#subBox'))) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); $('#subSave').click(); }
    if (e.key === 'Escape') closeSubEditor();
    return;
  }
  if (e.target.id === 'noteText') {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveNote(); }
    if (e.key === 'Escape') $('#noteBox').classList.add('hidden');
    return;
  }
  if (['input', 'textarea', 'select'].includes(tag) && !['range', 'checkbox'].includes(e.target.type)) return;
  const k = e.key;
  if (k === ' ') { e.preventDefault(); play(); }
  else if (k === 'ArrowLeft' && e.target.type !== 'range') { e.preventDefault(); seek(S.t - (e.shiftKey ? 5 : 1 / fps())); }
  else if (k === 'ArrowRight' && e.target.type !== 'range') { e.preventDefault(); seek(S.t + (e.shiftKey ? 5 : 1 / fps())); }
  else if (k === 'Home') seek(0); else if (k === 'End') seek(dur());
  else if (k === 'c' || k === 'C') setNoting(!S.noting);
  else if (k === 'Escape') { if (!$('#modal').classList.contains('hidden')) closeModal(); else if (S.noting) setNoting(false); else select(null); }
  else if (k === 's' || k === 'S') { if (!e.ctrlKey) splitSel(); }
  else if (k === 'Delete' || k === 'Backspace') deleteSel();
  else if ((k === 'z' || k === 'Z') && (e.ctrlKey || e.metaKey)) { e.preventDefault(); e.shiftKey ? redo() : undo(); }
  else if (k === 'y' && e.ctrlKey) { e.preventDefault(); redo(); }
  else if (k === '+' || k === '=') setZoom(S.pps * 1.5); else if (k === '-') setZoom(S.pps / 1.5);
  else if (k === '[' || k === ']') {
    const i = S.sentences.findIndex(s => s.start > S.t + 0.01); const j = i < 0 ? S.sentences.length : i;
    const tgt = k === ']' ? S.sentences[j] : S.sentences[Math.max(0, j - 2)]; if (tgt) seek(tgt.start);
  }
});
function closeModal() { $('#modal').classList.add('hidden'); for (const v of document.querySelectorAll('#modal video')) v.pause(); }
$('#modalClose').onclick = closeModal;
$('#modal').addEventListener('click', e => { if (e.target.id === 'modal') closeModal(); });
$('#bPlay').onclick = play; $('#bPrev').onclick = () => seek(S.t - 1 / fps()); $('#bNext').onclick = () => seek(S.t + 1 / fps());
$('#bBack5').onclick = () => seek(S.t - 5); $('#bFwd5').onclick = () => seek(S.t + 5);
$('#bUndo').onclick = undo; $('#bRedo').onclick = redo; $('#bSplit').onclick = splitSel; $('#bDelete').onclick = deleteSel;
$('#bAddFx').onclick = () => ops([{ op: 'add_track', kind: 'fx' }], 'Đã thêm track hiệu ứng');
$('#zoom').oninput = e => setZoom(zoomToPps(+e.target.value));
$('#bZoomIn').onclick = () => setZoom(S.pps * 1.5); $('#bZoomOut').onclick = () => setZoom(S.pps / 1.5);
$('#bFit').onclick = () => { S.view0 = 0; setZoom(laneW() / dur(), 0); S.view0 = 0; drawTL(); };
$('#btnNotesMode').onclick = () => setNoting(!S.noting); $('#btnHelp').onclick = help; $('#btnExport').onclick = doExport;
$('#btnMedia').onclick = () => switchTab('media'); $('#btnAgent').onclick = agentInfo;
$('#noteSave').onclick = saveNote; $('#noteCancel').onclick = () => { $('#noteBox').classList.add('hidden'); pendingRect = null; drawNotesOnFrame(); };
for (const b of document.querySelectorAll('#tabs button')) b.onclick = () => switchTab(b.dataset.tab);
$('#bMeasure').onclick = async () => {
  const a = Math.max(0, S.t - 15), b = Math.min(dur(), S.t + 15); $('#meterTxt').textContent = 'đang đo…';
  try { const { body: m } = await api(`/api/measure?t0=${a}&t1=${b}`); $('#meterTxt').textContent = m.I_film != null ? `${mmss(a)}–${mmss(b)}: ${m.I_film} LUFS · đỉnh ${m.TP_film} dB` : `${m.I} LUFS (chưa trộn chuẩn)`; }
  catch (e) { $('#meterTxt').textContent = 'lỗi đo'; }
};
window.addEventListener('resize', resizeTL);

// ------------------------------------------------------------------ watch for agent edits
setInterval(async () => {
  if (!S.etag || S.busy || TL.mode || S.draft) return;
  try {
    const { body } = await api('/api/etag');
    if (body.etag !== S.etag) { await loadTimeline('Timeline vừa được cập nhật (agent hoặc tab khác).'); await refreshProject(); }
  } catch (e) { setSave('err', 'Mất kết nối'); }
}, 1500);
setInterval(() => { if (S.tab === 'build' || jobsCache.some(j => j.status === 'running' || j.status === 'queued')) pollJobs(); }, 2000);

(async function boot() {
  const { body: cat } = await api('/api/catalog'); S.cat = cat;
  await loadProject(); await loadTimeline(); await loadTiming();
  $('#durTxt').textContent = '/ ' + tc(dur());
  S.pps = 8; $('#zoom').value = ppsToZoom(S.pps); resizeTL(); requestFrame(true); updateTC(); pollJobs(); renderPanel();
  const open = (S.tl.review_notes || []).filter(n => n.status !== 'done').length;
  if (open) toast(`${open} góp ý đang mở`);
})();
