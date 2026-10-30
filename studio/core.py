"""Studio core, shared by the web server (server.py), the MCP server (mcp_server.py) and background jobs (jobs.py).

- Store: timeline.json read/write guarded by an ETag (sha1 of the file bytes) and a lock file, so the user in the UI
  and the agent over MCP never overwrite each other. Every write keeps the previous file in render/studio/history.
- Ops: clip edits (move/trim/split/set/add/delete) that re-anchor moved clips to the nearest sentence edge or word,
  so a later voice change still retimes them (scripts/timeline.py).
- Picture state: which video/overlay clips differ from the ones baked into render/picture.mp4. Only those time
  ranges need frames rendered again; audio-only edits re-mix and mux onto the existing picture.
- Framer: one preview frame through scripts/render.py (same Photo, overlays, subtitles, grain, vignette).
- preview(): a short range as MP4; export(): partial picture re-render + full mix + mux to a new file.
"""
import copy, hashlib, json, math, os, shutil, subprocess, sys, threading, time
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import timeline as T  # noqa: E402

PICTURE_TRACKS = ('video', 'overlay')
AUDIO_TRACKS = ('music', 'original', 'sfx')
EDITABLE = PICTURE_TRACKS + AUDIO_TRACKS


def is_pic(tr):
    """Tracks whose clips are drawn into the picture: video, overlay and effect tracks (kind fx)."""
    return tr['id'] in PICTURE_TRACKS or tr.get('kind') == 'fx'


def editable(tr):
    return tr['id'] in EDITABLE or tr.get('kind') == 'fx'
NOTE_STATUS = ('open', 'doing', 'done')
VENV_PY = ROOT / '.venv' / 'Scripts' / 'python.exe'
PY = str(VENV_PY if VENV_PY.exists() else Path(sys.executable))


class Conflict(Exception):
    def __init__(self, etag):
        super().__init__(f'timeline changed (current etag {etag})'); self.etag = etag


class OpError(ValueError):
    pass


def etag_of(b):
    return hashlib.sha1(b).hexdigest()[:16]


def dumps(tl):
    return json.dumps(tl, ensure_ascii=False, indent=1).encode('utf-8')  # same layout as scripts/common.write


def projects():
    return sorted(p.name for p in (ROOT / 'projects').iterdir() if (p / 'timeline.json').exists())


def last_project():
    p = ROOT / 'studio' / '.last_project'
    return p.read_text(encoding='utf-8').strip() if p.exists() else None


# ---------------------------------------------------------------- project + store
class Project:
    def __init__(self, pid):
        self.id = pid
        self.d = ROOT / 'projects' / pid
        self.tl_path = self.d / 'timeline.json'
        if not self.tl_path.exists():
            raise FileNotFoundError(f'no timeline.json in projects/{pid}')
        self.work = self.d / 'render' / 'studio'
        for sub in ('history', 'jobs', 'previews', 'tmp', 'peaks', 'frames'):
            (self.work / sub).mkdir(parents=True, exist_ok=True)
        self.picture = self.d / 'render' / 'picture.mp4'
        self.out_dir = ROOT / 'output' / pid
        self._timing = None

    # -- lock (cross-process: UI server, MCP server and jobs all write through here)
    def _lock(self, timeout=10.0):
        lk = self.tl_path.with_suffix('.json.lock'); t0 = time.time()
        while True:
            try:
                fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd)
                return lk
            except FileExistsError:
                try:
                    if time.time() - lk.stat().st_mtime > 30:
                        lk.unlink(); continue  # stale lock from a crashed writer
                except FileNotFoundError:
                    continue
                if time.time() - t0 > timeout:
                    raise TimeoutError('timeline.json is locked by another writer')
                time.sleep(0.05)

    def read_bytes(self):
        return self.tl_path.read_bytes()

    def read(self):
        b = self.read_bytes()
        return json.loads(b.decode('utf-8')), etag_of(b)

    def etag(self):
        return etag_of(self.read_bytes())

    def _write_locked(self, tl, old_bytes, who, why):
        stamp = time.strftime('%Y%m%d-%H%M%S') + f'-{int(time.time() * 1000) % 1000:03d}'
        (self.work / 'history' / f'{stamp}-{who}.json').write_bytes(old_bytes)
        hist = sorted((self.work / 'history').glob('*.json'))
        for p in hist[:-300]:
            p.unlink(missing_ok=True)
        log = self.work / 'history' / 'log.jsonl'
        with log.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'who': who, 'why': why, 'before': f'{stamp}-{who}.json'},
                               ensure_ascii=False) + '\n')
        nb = dumps(tl)
        tmp = self.tl_path.with_suffix('.json.tmp'); tmp.write_bytes(nb); os.replace(tmp, self.tl_path)
        return etag_of(nb)

    def transact(self, fn, if_match=None, who='studio', why=''):
        """Read, check if_match, let fn(tl) mutate it (returns a result), write. Returns (result, new_etag)."""
        lk = self._lock()
        try:
            b = self.read_bytes(); cur = etag_of(b)
            if if_match and if_match != cur:
                raise Conflict(cur)
            tl = json.loads(b.decode('utf-8'))
            res = fn(tl)
            if res is False:
                return None, cur
            return res, self._write_locked(tl, b, who, why)
        finally:
            lk.unlink(missing_ok=True)

    def put(self, tl, if_match, who='user', why='save'):
        validate(tl)
        def repl(cur):
            cur.clear(); cur.update(tl)
        return self.transact(repl, if_match, who, why)[1]

    def history_count(self):
        p = self.work / 'history' / 'log.jsonl'
        return sum(1 for _ in p.open(encoding='utf-8')) if p.exists() else 0

    def history(self, n=30):
        p = self.work / 'history' / 'log.jsonl'
        rows = p.read_text(encoding='utf-8').strip().split('\n') if p.exists() else []
        return [json.loads(r) for r in rows[-n:] if r]

    # -- voice timing (snap targets + anchors)
    def timing(self):
        p = self.d / 'voice' / 'timing.json'
        m = p.stat().st_mtime if p.exists() else 0
        if not self._timing or self._timing[0] != m:
            t = json.loads(p.read_text(encoding='utf-8'))['sentences'] if p.exists() else {}
            self._timing = (m, t, Anchors(t))
        return self._timing[1]

    def anchors(self):
        self.timing(); return self._timing[2]


def validate(tl):
    if not isinstance(tl, dict) or not isinstance(tl.get('tracks'), list):
        raise OpError('timeline must have tracks')
    for k in ('fps', 'duration', 'width', 'height'):
        if k not in tl:
            raise OpError(f'timeline missing {k}')
    seen = set()
    for tr in tl['tracks']:
        for c in tr.get('clips', []):
            if c.get('id') in seen:
                raise OpError(f'duplicate clip id {c.get("id")}')
            seen.add(c.get('id'))
            if 'start' in c and 'end' in c and c['end'] <= c['start']:
                raise OpError(f'{c["id"]}: end <= start')


# ---------------------------------------------------------------- anchors
class Anchors:
    """Sentence edges and word onsets, for snapping and for re-anchoring a moved clip."""
    def __init__(self, timing):
        pts = []
        for sid, s in timing.items():
            pts.append((s['start'], {'sentence': sid, 'edge': 'start'}))
            pts.append((s['end'], {'sentence': sid, 'edge': 'end'}))
            for i, w in enumerate(s.get('words') or []):
                if i:  # word 0 is the sentence start
                    pts.append((w['start'], {'sentence': sid, 'word': i}))
        pts.sort(key=lambda p: p[0])
        self.t = [p[0] for p in pts]; self.a = [p[1] for p in pts]

    def nearest(self, t):
        if not self.t:
            return None, None
        i = bisect_right(self.t, t)
        best = min((j for j in (i - 1, i) if 0 <= j < len(self.t)), key=lambda j: abs(self.t[j] - t))
        return self.t[best], self.a[best]

    def anchor(self, t):
        at, a = self.nearest(t)
        if a is None:
            return None
        return dict(a, offset=round(t - at, 4))

    def sentence_at(self, timing, t):
        for sid, s in timing.items():
            if s['start'] - 0.3 <= t <= s['end'] + 0.3:
                return sid, s
        return None, None


# ---------------------------------------------------------------- clip ops
def find(tl, cid):
    for tr in tl['tracks']:
        for i, c in enumerate(tr['clips']):
            if c.get('id') == cid:
                return tr, i, c
    raise OpError(f'no clip {cid}')


def track(tl, tid):
    for tr in tl['tracks']:
        if tr['id'] == tid:
            return tr
    raise OpError(f'no track {tid}')


def new_id(tl, base):
    ids = {c.get('id') for tr in tl['tracks'] for c in tr['clips']}
    if base.isalpha():  # a track prefix (V, O, X, F...): next free number after the highest one
        nums = [int(i[len(base):]) for i in ids if i and i.startswith(base) and i[len(base):].isdigit()]
        return f'{base}{(max(nums) if nums else 0) + 1:03d}'
    for k in range(2, 1000):
        cand = f'{base}.{k}'
        if cand not in ids:
            return cand
    raise OpError('cannot make a new id')


def _place(c, start, end, fps, anchors, re_end=True):
    start = T.snap(max(0.0, start), fps); end = T.snap(end, fps)
    if end <= start:
        raise OpError(f'{c["id"]}: end {end} <= start {start}')
    if 'anchor' in c and anchors is not None and abs(start - c['start']) > 1e-4:
        c['anchor'] = anchors.anchor(start) or c['anchor']
    if 'end_anchor' in c and anchors is not None and re_end and abs(end - c.get('end', end)) > 1e-4:
        c['end_anchor'] = anchors.anchor(end) or c['end_anchor']
    c['start'], c['end'], c['frame'] = start, end, round(start * fps)


def _audio_in(tr, c):
    return tr['id'] in AUDIO_TRACKS or (tr['id'] == 'video' and c.get('kind') == 'video')


def apply_ops(tl, ops, anchors=None):
    """Apply clip ops in order; returns a list of human-readable changes. Raises OpError (nothing is written then).

    {"op": "move",   "id": "X012", "start": 812.4}            or "delta": -0.25   (keeps the length)
    {"op": "trim",   "id": "V101", "start": 400.0, "end": 404.5, "roll": true}  (roll: the touching video neighbour follows)
    {"op": "split",  "id": "V101", "t": 402.0}
    {"op": "set",    "id": "X012", "fields": {"gain_db": -6, "mute": false, "props": {...}}}  (null deletes a field)
    {"op": "add",    "track": "sfx", "clip": {"src": "...", "start": 10, "end": 12, "gain_db": -12}}
    {"op": "delete", "id": "X012"}
    {"op": "fx",     "fields": {"grain": true, "subtitles": true}}
    """
    fps = tl['fps']; log = []
    for op in ops:
        kind = op.get('op')
        if kind == 'fx':
            tl.setdefault('fx', {}).update(op['fields']); log.append(f'fx {op["fields"]}'); continue
        if kind == 'subtitle':  # {"op": "subtitle", "key": "15116", "text": "...", "start": 15.1, "end": 18.0}; "reset": true drops the edit
            ov = tl.setdefault('subtitle_overrides', {}); k = str(op['key'])
            if op.get('reset'):
                ov.pop(k, None)
            else:
                o = ov.setdefault(k, {})
                for f in ('text', 'start', 'end'):
                    if f in op:
                        o[f] = op[f] if f == 'text' else round(float(op[f]), 3)
                if 'start' in o and 'end' in o and o['end'] <= o['start']:
                    raise OpError('subtitle end must be after its start')
            if not ov:
                tl.pop('subtitle_overrides', None)
            log.append(f'subtitle {k} {"reset" if op.get("reset") else "edited"}'); continue
        if kind == 'subtitle_style':  # {"op": "subtitle_style", "fields": {"size": 50, "y": 0.86, ...}} (null = default)
            st = tl.setdefault('subtitle_style', {})
            for k, v in op['fields'].items():
                st.pop(k, None) if v is None else st.__setitem__(k, v)
            log.append(f'subtitle style {op["fields"]}'); continue
        if kind == 'insert':  # {"op": "insert", "src": "media/x.jpg", "t": 120.0, "dur": 5.0, "kind": "photo"}: new shot on the video track
            vt = track(tl, 'video'); t0 = T.snap(float(op['t']), fps); t1 = T.snap(t0 + float(op.get('dur', 5.0)), fps)
            under = [c for c in vt['clips'] if c['start'] < t1 and c['end'] > t0]
            for c in under:
                if c['start'] < t0 and c['end'] > t1:  # the new shot sits inside one clip: keep both ends of it
                    b = copy.deepcopy(c); b['id'] = new_id(tl, c['id'])
                    if c.get('kind') == 'video':
                        b['in'] = round(c.get('in', 0.0) + (t1 - c['start']), 4)
                    b.pop('transition_in', None); b['start'], b['frame'] = t1, round(t1 * fps)
                    if anchors is not None and 'anchor' in c:
                        b['anchor'] = anchors.anchor(t1); c['end_anchor'] = anchors.anchor(t0)
                    c['end'] = t0; vt['clips'].append(b)
                elif c['start'] < t0:
                    c['end'] = t0
                    if anchors is not None and 'end_anchor' in c:
                        c['end_anchor'] = anchors.anchor(t0)
                elif c['end'] > t1:
                    if c.get('kind') == 'video':
                        c['in'] = round(c.get('in', 0.0) + (t1 - c['start']), 4)
                    _place(c, t1, c['end'], fps, anchors)
                else:
                    vt['clips'].remove(c)
            k = op.get('kind') or ('video' if media_kind(op['src']) == 'video' else 'photo')
            n = {'id': new_id(tl, 'V'), 'start': t0, 'end': t1, 'src': op['src'], 'kind': k, 'grade': op.get('grade', 'archival' if k == 'photo' else 'modern'),
                 'frame': round(t0 * fps)}
            if k == 'photo':
                n['motion'] = {'type': 'push', 'dx': 0.04}
            if anchors is not None:
                n['anchor'] = anchors.anchor(t0)
            vt['clips'].append(n); vt['clips'].sort(key=lambda x: x['start'])
            log.append(f'insert {n["id"]} {op["src"]} {t0:.2f}-{t1:.2f}'); continue
        if kind == 'add_track':  # {"op": "add_track", "kind": "fx", "name": "Hiệu ứng 2"}
            if op.get('kind', 'fx') != 'fx':
                raise OpError('only effect tracks (kind fx) can be added')
            ids = {t['id'] for t in tl['tracks']}; n = 1
            while f'fx{n if n > 1 else ""}' in ids:
                n += 1
            tid = op.get('id') or f'fx{n if n > 1 else ""}'
            tl['tracks'].append({'id': tid, 'kind': 'fx', 'name': op.get('name') or f'Hiệu ứng {n}', 'clips': []})
            log.append(f'add track {tid}'); continue
        if kind == 'track':  # {"op": "track", "id": "fx", "fields": {"hidden": true, "name": "..."}}
            tr = track(tl, op['id'])
            for k, v in op['fields'].items():
                if k in ('hidden', 'name', 'locked', 'height'):
                    tr.pop(k, None) if v is None else tr.__setitem__(k, v)
            if op['fields'].get('delete') and tr.get('kind') == 'fx' and not tr['clips']:
                tl['tracks'].remove(tr)
            log.append(f'track {op["id"]} {op["fields"]}'); continue
        if kind == 'add':
            tr = track(tl, op['track'])
            if not editable(tr):
                raise OpError(f'track {tr["id"]} is read-only here')
            c = copy.deepcopy(op['clip'])
            c.setdefault('id', new_id(tl, {'video': 'V', 'overlay': 'O', 'music': 'M', 'original': 'A', 'sfx': 'X'}.get(tr['id'], 'F')))
            if c['id'] in {x.get('id') for t in tl['tracks'] for x in t['clips']}:
                raise OpError(f'id {c["id"]} exists')
            if anchors is not None and op.get('anchor', True):
                c.setdefault('anchor', anchors.anchor(c['start']))
            if tr['id'] == 'video' and c.get('src') and c.get('kind', 'photo') == 'photo':
                c.setdefault('kind', 'photo'); c.setdefault('motion', {'type': 'push', 'dx': 0.04})  # explicit: no index-dependent Ken Burns
            _place(c, c['start'], c['end'], fps, None)
            tr['clips'].append(c); tr['clips'].sort(key=lambda x: x.get('start', 0))
            log.append(f'add {c["id"]} on {tr["id"]} {c["start"]:.2f}-{c["end"]:.2f}'); continue
        tr, i, c = find(tl, op['id'])
        if not editable(tr):
            raise OpError(f'{op["id"]} is on the {tr["id"]} track: the voice is rebuilt by doc.py assemble, not edited here')
        if kind == 'move':
            start = op['start'] if 'start' in op else c['start'] + op['delta']
            length = c['end'] - c['start']
            _place(c, start, start + length, fps, anchors)
            log.append(f'move {c["id"]} -> {c["start"]:.3f}')
        elif kind == 'trim':
            s0, e0 = c['start'], c['end']
            s1, e1 = op.get('start', s0), op.get('end', e0)
            if _audio_in(tr, c) and abs(s1 - s0) > 1e-6 and not c.get('loop'):
                c['in'] = round(max(0.0, c.get('in', 0.0) + (s1 - s0)), 4)
            _place(c, s1, e1, fps, anchors)
            if op.get('roll') and tr['id'] == 'video':
                vids = sorted(tr['clips'], key=lambda x: x['start'])
                j = vids.index(c)
                if abs(e1 - e0) > 1e-6 and j + 1 < len(vids) and abs(vids[j + 1]['start'] - e0) < 1.5 / fps:
                    n = vids[j + 1]; _place(n, c['end'], n['end'], fps, anchors); log.append(f'roll {n["id"]} start -> {n["start"]:.3f}')
                if abs(s1 - s0) > 1e-6 and j > 0 and abs(vids[j - 1]['end'] - s0) < 1.5 / fps:
                    p = vids[j - 1]; _place(p, p['start'], c['start'], fps, anchors); log.append(f'roll {p["id"]} end -> {p["end"]:.3f}')
            log.append(f'trim {c["id"]} {c["start"]:.3f}-{c["end"]:.3f}')
        elif kind == 'split':
            t = T.snap(op['t'], fps)
            if not c['start'] < t < c['end']:
                raise OpError(f'{c["id"]}: split point {t} is outside {c["start"]}-{c["end"]}')
            b = copy.deepcopy(c); b['id'] = op.get('new_id') or new_id(tl, c['id'])
            if _audio_in(tr, c) and not c.get('loop'):
                b['in'] = round(c.get('in', 0.0) + (t - c['start']), 4)
            b.pop('transition_in', None)
            if 'anchor' in c and anchors is not None:
                b['anchor'] = anchors.anchor(t)
                c['end_anchor'] = anchors.anchor(t)
            b['start'], b['frame'] = t, round(t * fps); c['end'] = t
            if _audio_in(tr, c):  # no click at the cut
                c['fade_out'] = min(c.get('fade_out', 0.3), 0.02); b['fade_in'] = 0.02
            tr['clips'].insert(i + 1, b)
            log.append(f'split {c["id"]} at {t:.3f} -> {b["id"]}')
        elif kind == 'set':
            f = dict(op['fields'])
            if 'id' in f:
                raise OpError('ids cannot be changed')
            s, e = f.pop('start', None), f.pop('end', None)
            for k, v in f.items():
                if v is None:
                    c.pop(k, None)
                else:
                    c[k] = v
            if s is not None or e is not None:
                _place(c, c['start'] if s is None else s, c['end'] if e is None else e, fps, anchors)
            log.append(f'set {c["id"]} {sorted(op["fields"])}')
        elif kind == 'delete':
            tr['clips'].pop(i); log.append(f'delete {c["id"]}')
        else:
            raise OpError(f'unknown op {kind}')
        if tr['id'] != 'voice':
            tr['clips'].sort(key=lambda x: x.get('start', 0))
    validate(tl)
    return log


def note_ops(tl, op):
    notes = tl.setdefault('review_notes', [])
    if op['op'] == 'add':
        ids = {n['id'] for n in notes}; k = len(notes) + 1
        while f'N{k}' in ids:
            k += 1
        n = {'id': f'N{k}', 't': round(float(op['t']), 3), 'rect': [round(float(x), 4) for x in op.get('rect') or [0, 0, 1, 1]],
             'text': op['text'].strip(), 'status': 'open', 'author': op.get('author', 'user'), 'created': time.strftime('%Y-%m-%d %H:%M')}
        notes.append(n); return n
    n = next((n for n in notes if n['id'] == op['id']), None)
    if n is None:
        raise OpError(f'no note {op["id"]}')
    if op['op'] == 'delete':
        notes.remove(n); return n
    if 'status' in op:
        if op['status'] not in NOTE_STATUS:
            raise OpError(f'status must be one of {NOTE_STATUS}')
        n['status'] = op['status']
    for k in ('text', 'reply', 'rect', 't'):
        if k in op:
            n[k] = op[k]
    n['updated'] = time.strftime('%Y-%m-%d %H:%M')
    return n


# ---------------------------------------------------------------- picture state (what render/picture.mp4 contains)
def _num(v):
    """3792 and 3792.0 are the same time (a browser JSON round trip drops the .0)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    if isinstance(v, dict):
        return {k: _num(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_num(x) for x in v]
    return v


def _sig(c):
    return json.dumps(_num({k: v for k, v in c.items() if k not in ('anchor', 'end_anchor', 'frame', 'need')}), sort_keys=True,
                      ensure_ascii=False)


def _file_sig(p):
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12] if p.exists() else None


def picture_sig(proj, tl):
    return {'clips': {tr['id']: {c['id']: [_num(c['start']), _num(c['end']), _sig(c)] for c in tr['clips']}
                      for tr in tl['tracks'] if is_pic(tr) and not tr.get('hidden')},
            'subtitle_style': json.dumps(_num(tl.get('subtitle_style') or {}), sort_keys=True),
            'subs': {k: v for k, v in sub_spans(proj, tl).items()},
            'fx': json.dumps(_num(tl.get('fx') or {}), sort_keys=True), 'language': tl.get('language'),
            'srt': _file_sig(proj.d / 'voice' / 'voice.srt'), 'duration': tl['duration']}


def sub_spans(proj, tl):
    """{cue key: [start, end, text]} of the edited cues, original and edited span (for dirty ranges)."""
    ov = tl.get('subtitle_overrides') or {}
    if not ov:
        return {}
    import render as R
    srt = proj.d / 'voice' / 'voice.srt'
    orig = {R.sub_key(a): (a, b) for a, b, _ in (R.read_srt(srt) if srt.exists() else [])}
    out = {}
    for k, o in ov.items():
        a, b = orig.get(k, (int(k) / 1000, int(k) / 1000 + 1))
        out[k] = [_num(min(a, o.get('start', a))), _num(max(b, o.get('end', b))), json.dumps(_num(o), sort_keys=True, ensure_ascii=False)]
    return out


def subtitle_cues(proj, tl):
    """All cues for the studio: key, original and current text/times, edited flag."""
    import render as R
    srt = proj.d / 'voice' / 'voice.srt'
    ov = tl.get('subtitle_overrides') or {}; out = []
    for a, b, x in (R.read_srt(srt) if srt.exists() else []):
        k = R.sub_key(a); o = ov.get(k) or {}
        out.append({'key': k, 'start': o.get('start', a), 'end': o.get('end', b), 'text': o.get('text', x),
                    'orig': {'start': a, 'end': b, 'text': x}, 'edited': bool(o), 'hidden': 'text' in o and not o['text'].strip()})
    return out


def subtitle_at(proj, tl, t):
    """The cue on screen at t (if subtitles are on) with its box on the frame as fractions [x, y, w, h]."""
    import render as R
    for c in subtitle_cues(proj, tl):
        if c['start'] <= t < c['end'] and not c['hidden']:
            _, _, _, (x0, y0, x1, y1) = R.subtitle_layout(c['text'], tl.get('subtitle_style'))
            c['box'] = [x0 / R.W, y0 / R.H, (x1 - x0) / R.W, (y1 - y0) / R.H]
            return c
    return None


def _pic_id(p):
    st = p.stat(); return {'size': st.st_size, 'mtime': int(st.st_mtime)}


def state_path(proj):
    return proj.work / 'picture_state.json'


def load_state(proj):
    p = state_path(proj)
    if not p.exists():
        return None
    st = json.loads(p.read_text(encoding='utf-8'))
    if st.get('v') != 2:  # states written before numbers were normalised: compare like with like
        st['clips'] = {tid: {k: [_num(x[0]), _num(x[1]), json.dumps(_num(json.loads(x[2])), sort_keys=True, ensure_ascii=False)]
                             for k, x in cs.items()} for tid, cs in st['clips'].items()}
        st['fx'] = json.dumps(_num(json.loads(st.get('fx') or '{}')), sort_keys=True)
        st['v'] = 2; p.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
    return st


def save_state(proj, tl, assumed=False):
    s = picture_sig(proj, tl); s['picture'] = _pic_id(proj.picture); s['assumed'] = assumed
    s['saved'] = time.strftime('%Y-%m-%d %H:%M:%S'); s['v'] = 2
    state_path(proj).write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')


def chunk_starts(proj):
    """Start times of the parallel-render chunks that built picture.mp4 (render_parallel.py), else [0]."""
    lst = proj.d / 'render' / 'chunks' / 'list.txt'
    if not lst.exists():
        return [0.0]
    files = [Path(r[6:-1]) for r in lst.read_text(encoding='utf-8').split('\n') if r.startswith("file '")]
    if not files or not all(f.exists() and f.stat().st_mtime <= proj.picture.stat().st_mtime + 5 for f in files):
        return [0.0]
    starts, t = [], 0.0
    for f in files:
        starts.append(t); t += probe_duration(f)
    return starts if abs(t - probe_duration(proj.picture)) < 0.5 else [0.0]


def freeze_motion(proj, tl):
    """Photos without an explicit `motion` get their Ken Burns direction from their index inside the render pass
    (render.Photo: idx % 3 == 2 pulls out, dx alternates). Writing the effective motion down keeps every photo moving
    exactly as in picture.mp4 when clips are split, inserted or rendered in another chunk. Returns how many changed."""
    vids = sorted([c for tr in tl['tracks'] if tr['id'] == 'video' for c in tr['clips']], key=lambda c: c['start'])
    fps = tl['fps']
    starts = [round(round(s * fps) / fps, 4) for s in (chunk_starts(proj) if proj.picture.exists() else [0.0])]
    first = {}  # chunk -> global index of its first clip: render_parallel.chunk_tl keeps every clip with end > t0
    for ch, s in enumerate(starts):
        first[ch] = next((k for k, c in enumerate(vids) if c['end'] > s), 0)
    for k, c in enumerate(vids):
        mid = (c['start'] + c['end']) / 2  # a clip cut by a chunk edge moves as in the chunk that drew most of it
        ch = max(i for i, s in enumerate(starts) if mid >= s)
        if c.get('motion') or c.get('kind') == 'card' or not c.get('src'):
            continue
        if c.get('kind') == 'video' or str(c['src']).lower().endswith(('.mp4', '.webm', '.mov', '.mkv')):
            continue
        idx = k - first[ch]
        c['motion'] = {'type': 'pull' if idx % 3 == 2 else 'push', 'dx': 0.04 if idx % 2 else -0.04}
    return sum(1 for c in vids if c.get('motion'))


def open_project(pid):
    """Open for the studio: on the first open of a rendered film, pin Ken Burns and record what picture.mp4 holds."""
    proj = Project(pid)
    (ROOT / 'studio' / '.last_project').write_text(pid, encoding='utf-8')
    st = load_state(proj)
    if proj.picture.exists() and (not st or st.get('picture') != _pic_id(proj.picture)):  # first open, or re-rendered outside
        tl, _ = proj.read()
        if any(not c.get('motion') for tr in tl['tracks'] if tr['id'] == 'video' for c in tr['clips']):
            proj.transact(lambda t: freeze_motion(proj, t), who='studio', why='pin Ken Burns direction of every photo (same as picture.mp4)')
            tl, _ = proj.read()
        save_state(proj, tl, assumed=True)  # the studio assumes the current video/overlay tracks are what was rendered
    return proj


def dirty_ranges(proj, tl, pad=0.0):
    """Time ranges whose picture differs from render/picture.mp4 (merged). None if there is no usable picture."""
    if not proj.picture.exists():
        return None
    st = load_state(proj)
    if not st or st.get('picture') != _pic_id(proj.picture):
        return None
    cur = picture_sig(proj, tl)
    if any(cur.get(k) != st.get(k, cur.get(k) if k == 'subtitle_style' else None) for k in ('fx', 'language', 'srt', 'duration', 'subtitle_style')):
        return [[0.0, tl['duration']]]
    spans = []
    for tid in set(st['clips']) | set(cur['clips']):
        a, b = st['clips'].get(tid, {}), cur['clips'].get(tid, {})
        for cid in set(a) | set(b):
            if a.get(cid) != b.get(cid):
                spans += [[x[0], x[1]] for x in (a.get(cid), b.get(cid)) if x]
    a, b = st.get('subs', {}), cur.get('subs', {})
    for k in set(a) | set(b):
        if a.get(k) != b.get(k):
            spans += [[x[0], x[1]] for x in (a.get(k), b.get(k)) if x]
    spans.sort(); out = []
    for s, e in spans:
        s, e = max(0.0, s - pad), min(tl['duration'], e + pad)
        if out and s <= out[-1][1] + 0.5:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def edit_kind(tl_before, tl_after):
    """'picture' if a video/overlay clip or fx changed, 'audio' if only sound clips changed, None if nothing did."""
    def part(tl, pic):
        return json.dumps([tr for tr in tl['tracks'] if (is_pic(tr) if pic else tr['id'] in AUDIO_TRACKS)], sort_keys=True)
    if (part(tl_before, True) != part(tl_after, True) or tl_before.get('fx') != tl_after.get('fx')
            or tl_before.get('subtitle_style') != tl_after.get('subtitle_style')
            or tl_before.get('subtitle_overrides') != tl_after.get('subtitle_overrides')):
        return 'picture'
    if part(tl_before, False) != part(tl_after, False):
        return 'audio'
    return None


# ---------------------------------------------------------------- media helpers
_dur = {}


def probe_duration(p):
    p = Path(p); key = (str(p), p.stat().st_mtime)
    if key not in _dur:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)],
                             capture_output=True, text=True).stdout.strip()
        _dur[key] = float(out or 0)
    return _dur[key]


def keyframes(proj):
    """{pts: dts} of the keyframes of picture.mp4 (cached by size+mtime): splice points for a partial re-render."""
    cache = proj.work / 'keyframes.json'; pid = _pic_id(proj.picture)
    if cache.exists():
        k = json.loads(cache.read_text(encoding='utf-8'))
        if k.get('picture') == pid and 'kf' in k:
            return {a: b for a, b in k['kf']}
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts_time,dts_time,flags',
                          '-of', 'csv=p=0', str(proj.picture)], capture_output=True, text=True).stdout
    kf = sorted((float(r[0]), float(r[1])) for r in (x.split(',') for x in out.split('\n')) if len(r) >= 3 and 'K' in r[2])
    cache.write_text(json.dumps({'picture': pid, 'kf': kf}), encoding='utf-8')
    return dict(kf)


def resolve_media(proj, rel):
    """Project-relative src -> absolute path, only inside the workspace."""
    p = (proj.d / rel).resolve()
    if ROOT.resolve() not in p.parents:
        raise PermissionError(rel)
    return p


def peaks(proj, rel, per_sec=100):
    """Absolute peak per 1/per_sec s (uint8 0..255) of an audio file, cached."""
    import numpy as np
    p = resolve_media(proj, rel)
    key = hashlib.sha1(f'{p}|{p.stat().st_size}|{p.stat().st_mtime}|{per_sec}'.encode()).hexdigest()[:16]
    cache = proj.work / 'peaks' / f'{key}.bin'
    if cache.exists():
        return cache.read_bytes()
    sr = 8000; hop = sr // per_sec
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(p), '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                          stdout=subprocess.PIPE)
    out = bytearray(); rest = np.zeros(0, np.float32)
    while True:
        b = pr.stdout.read(hop * 4 * 4000)
        if not b:
            break
        x = np.concatenate([rest, np.frombuffer(b, np.float32)])
        n = len(x) // hop * hop; rest = x[n:]
        if n:
            out += (np.clip(np.abs(x[:n]).reshape(-1, hop).max(1), 0, 1) * 255).astype(np.uint8).tobytes()
    pr.wait()
    cache.write_bytes(bytes(out))
    return bytes(out)


# ---------------------------------------------------------------- frames (preview == render)
class _VideoAt:
    """One graded frame of a video clip at clip time lt (studio preview: random access, not a decoder stream)."""
    def __init__(self, framer, path, c):
        self.framer, self.path, self.c = framer, path, c

    def frame(self, lt):
        return self.framer._video_frame(self.path, self.c, lt)


class Framer:
    """Draws one frame at film time t exactly like render.picture() (Photo, transitions, grain, overlays, credit,
    subtitles, vignette). Photo objects are cached; one frame at a time (render.py keeps module-level caches)."""
    def __init__(self, proj):
        import render as R
        import render_fx as FX
        self.R, self.FX, self.proj = R, FX, proj
        self.lock = threading.Lock()
        self.photos = {}; self.cache = {}; self._subs = None; self.media = {}

    def subs(self, tl):
        p = self.proj.d / 'voice' / 'voice.srt'
        m = (p.stat().st_mtime if p.exists() else 0, json.dumps(tl.get('subtitle_overrides') or {}, sort_keys=True))
        if not self._subs or self._subs[0] != m:
            s = self.R.subtitles(self.proj.d, tl)
            self._subs = (m, s, [x[0] for x in s])
        return self._subs[1], self._subs[2]

    def _obj(self, c, k):
        """Frame source for clip c like render.picture's src(): a cached Photo (Ken Burns on the GPU or CPU), a Blank,
        or a one-frame video grabber."""
        R = self.R
        if c.get('kind') == 'card' or not c.get('src'):
            return R.Blank()
        path = resolve_media(self.proj, c['src'])
        if c.get('kind') == 'video' or str(c['src']).lower().endswith(('.mp4', '.webm', '.mov', '.mkv')):
            return _VideoAt(self, path, c)
        key = (c['id'], c['src'], c.get('grade'), json.dumps([c.get('motion'), c.get('color')], sort_keys=True), c['start'], c['end'], k)
        if key not in self.photos:
            if len(self.photos) > 24:
                self.photos.pop(next(iter(self.photos)))
            self.photos[key] = R.Photo(path, c, k)
        return self.photos[key]

    def _src(self, c, k, lt):
        return self._obj(c, k).frame(lt)

    def _video_frame(self, path, c, lt):
        import numpy as np
        R = self.R; W, H = R.W, R.H  # same scale/crop as render.Video, one frame at in + lt
        info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                          '-of', 'json', str(path)], capture_output=True).stdout)['streams'][0]
        vf = (f'scale={int(W * 0.8)}:{int(H * 0.86)}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0c0b0a'
              if R.is_print(info['width'], info['height']) else f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}')
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{c.get("in", 0.0) + max(0.0, lt):.3f}', '-i', str(path), '-an',
                              '-frames:v', '1', '-vf', f'{vf},format=rgb24', '-f', 'rawvideo', '-'], capture_output=True).stdout
        if len(raw) != W * H * 3:
            return np.zeros((H, W, 3), np.uint8)
        return self.FX.apply_color(R.grade(np.frombuffer(raw, np.uint8).reshape(H, W, 3), c.get('grade', 'modern')), c.get('color'))

    def frame(self, tl, t):
        import numpy as np
        R = self.R
        with self.lock:
            R.LANG = tl.get('language') or 'en'
            vids = sorted([c for tr in tl['tracks'] if tr['id'] == 'video' for c in tr['clips']], key=lambda c: c['start'])
            overlays = sorted([c for tr in tl['tracks'] if tr['id'] == 'overlay' for c in tr['clips'] if 'start' in c],
                              key=lambda o: o.get('type') in ('date_tag', 'lower_third', 'callout'))
            if not vids:
                return np.zeros((R.H, R.W, 3), np.uint8)
            k = max(0, bisect_right([c['start'] for c in vids], t) - 1); c = vids[k]
            act = sorted([e for e in self.FX.effect_clips(tl) if e['start'] <= t < e['end']], key=lambda e: e['start'])
            media = {}
            for e in act:
                src = (e.get('params') or {}).get('src')
                if e['type'] == 'media_overlay' and src:
                    key = (src, json.dumps(e['params'], sort_keys=True))
                    if key not in self.media:
                        if len(self.media) > 8:
                            self.media.pop(next(iter(self.media)))
                        self.media[key] = self.FX.MediaLayer(resolve_media(self.proj, src), e['params'], tl['fps'], sequential=False)
                    media[e['id']] = self.media[key]
            sub = None
            if (tl.get('fx') or {}).get('subtitles'):
                subs, starts = self.subs(tl); j = bisect_right(starts, t) - 1
                if j >= 0 and subs[j][0] <= t < subs[j][1]:
                    sub = subs[j][2]
            R.USE_GPU = settings().get('gpu_render', True)
            return R.render_frame(t, vids, k, lambda j: self._obj(vids[j], j), overlays, sub, tl.get('fx') or {}, self.cache, act, media,
                                  tl['fps'], tl.get('subtitle_style'), as_bytes=False)

    def jpeg(self, tl, t, width=960, quality=82):
        from io import BytesIO
        from PIL import Image
        im = Image.fromarray(self.frame(tl, t))
        if width and width < im.width:
            im = im.resize((width, round(im.height * width / im.width)), Image.BILINEAR)
        b = BytesIO(); im.save(b, 'JPEG', quality=quality); return b.getvalue()


# ---------------------------------------------------------------- loudness
def mix_offset(proj):
    """dB that the export's loudnorm adds to the premix (cached): the studio monitor plays windows at that gain."""
    pre = proj.d / 'render' / 'premix.wav'; cache = proj.work / 'loudness.json'
    if not pre.exists():
        return None
    key = {'size': pre.stat().st_size, 'mtime': int(pre.stat().st_mtime)}
    if cache.exists():
        c = json.loads(cache.read_text(encoding='utf-8'))
        if c.get('premix') == key:
            return c['offset_db']
    m = measure(pre)
    if m is None:
        return None
    tl, _ = proj.read()
    off = round(tl.get('loudness', {}).get('target_lufs', -14.0) - m['I'], 2)
    cache.write_text(json.dumps({'premix': key, 'premix_lufs': m['I'], 'offset_db': off}), encoding='utf-8')
    return off


def measure(path, t0=None, dur=None):
    """Integrated loudness / true peak / LRA of a file (ffmpeg ebur128)."""
    pre = ['-ss', f'{t0:.3f}'] if t0 is not None else []
    pre += ['-t', f'{dur:.3f}'] if dur else []
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', *pre, '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    tail = err[err.rfind('Summary:'):]
    def val(key):
        i = tail.find(key)
        if i < 0:
            return None
        try:
            return float(tail[i + len(key):].split()[0])
        except (ValueError, IndexError):
            return None
    I = val('I:')
    return None if I is None else {'I': I, 'LRA': val('LRA:'), 'TP': val('Peak:')}


def audio_window(proj, tl, t0, t1, only=None):
    """WAV bytes of the voice-led premix for [t0, t1] (monitor playback, mute/solo via `only`)."""
    import render as R
    out = proj.work / 'tmp' / f'mon-{os.getpid()}-{threading.get_ident()}-premix.wav'
    R.premix(proj.d, tl, out, t0, t1, only=only, codec='pcm_s16le')
    b = out.read_bytes(); out.unlink(missing_ok=True)
    return b


# ---------------------------------------------------------------- range render (preview + partial export)
def range_timeline(proj, tl, t0, t1, work):
    """Picture-only timeline for [t0, t1) shifted to 0, with absolute media paths, and its own subtitle file in work/voice.
    Clips cut by t0 keep their motion (start < 0); video sources skip ahead so they stay in sync."""
    ex = copy.deepcopy(tl); ex['duration'] = round(t1 - t0, 6); ex['t_offset'] = t0
    for tr in ex['tracks']:
        if not is_pic(tr):
            tr['clips'] = []; continue
        keep = []
        for c in tr['clips']:
            if 'start' not in c or c['end'] <= t0 or c['start'] >= t1:
                continue
            if tr['id'] == 'video' and c['start'] < t0 and (c.get('kind') == 'video' or str(c.get('src', '')).lower().endswith(('.mp4', '.webm', '.mov', '.mkv'))):
                c['in'] = c.get('in', 0.0) + (t0 - c['start'])
            c['start'] = round(c['start'] - t0, 6); c['end'] = round(c['end'] - t0, 6)
            if c.get('src'):
                c['src'] = str(resolve_media(proj, c['src']))
            if (c.get('params') or {}).get('src'):
                c['params']['src'] = str(resolve_media(proj, c['params']['src']))
                if c['start'] < 0:
                    c['params']['_skip'] = -c['start']  # overlay footage keeps its place in a range render
            keep.append(c)
        tr['clips'] = keep
    vids = [c for tr in ex['tracks'] if tr['id'] == 'video' for c in tr['clips']]
    if not any(c['start'] <= 0 for c in vids):  # a gap at t0: the clip still showing from before continues
        prev = [c for tr in tl['tracks'] if tr['id'] == 'video' for c in tr['clips'] if c['start'] < t0]
        if prev:
            c = copy.deepcopy(max(prev, key=lambda c: c['start'])); c['start'] -= t0; c['end'] -= t0
            if c.get('src'):
                c['src'] = str(resolve_media(proj, c['src']))
            next(tr for tr in ex['tracks'] if tr['id'] == 'video')['clips'].insert(0, c)
    import render as R
    (work / 'voice').mkdir(parents=True, exist_ok=True)
    srt = proj.d / 'voice' / 'voice.srt'
    rows = [s for s in R.subtitles(proj.d, tl) if s[0] < t1 and s[1] > t0] if srt.exists() else []
    ex.pop('subtitle_overrides', None)
    fmt = lambda t: f'{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)) % 1000:03d}'
    (work / 'voice' / 'voice.srt').write_text('\n'.join(f'{k}\n{fmt(max(0.0, a - t0))} --> {fmt(min(b, t1) - t0)}\n{x}\n'
                                                       for k, (a, b, x) in enumerate(rows, 1)), encoding='utf-8')
    return ex


WORKERS = 6  # default parallel picture renders (the user runs Whisk HyperFrames with 6 too); studio/settings.json overrides
SETTINGS = ROOT / 'studio' / 'settings.json'


def settings():
    s = {'render_workers': WORKERS, 'gpu_encode': True, 'gpu_render': True}
    if SETTINGS.exists():
        try:
            s.update(json.loads(SETTINGS.read_text(encoding='utf-8')))
        except json.JSONDecodeError:
            pass
    return s


def save_settings(new):
    s = settings()
    if 'render_workers' in new:
        s['render_workers'] = max(1, min(int(new['render_workers']), os.cpu_count() or 8))
    if 'gpu_encode' in new:
        s['gpu_encode'] = bool(new['gpu_encode'])
    if 'gpu_render' in new:
        s['gpu_render'] = bool(new['gpu_render'])
    SETTINGS.write_text(json.dumps(s, indent=1), encoding='utf-8')
    return s


def _render_frames(proj, tl, f0, f1, out):
    """Frames [f0, f1) of the film into out (exactly f1 - f0 frames, same encoder settings as render.picture)."""
    import render as R
    fps = tl['fps']
    work = out.parent / (out.stem + '_work'); work.mkdir(parents=True, exist_ok=True)
    ex = range_timeline(proj, tl, f0 / fps, f1 / fps, work)
    ex['duration'] = (f1 - f0 - 0.5) / fps  # render.picture draws ceil(duration * fps) frames
    R.picture(work, ex, out)
    shutil.rmtree(work, ignore_errors=True)
    return out


_nvenc = None


def nvenc_ok():
    """True if ffmpeg can encode H.264 on the NVIDIA GPU here (checked once)."""
    global _nvenc
    if _nvenc is None:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=black:s=1920x1080:d=0.2', '-c:v', 'h264_nvenc', '-f', 'null', '-'],
                           capture_output=True)
        _nvenc = r.returncode == 0
    return _nvenc


def _render_part(args):
    """Process-pool entry: one part of a parallel range render."""
    import render as R
    pid, tl, f0, f1, out, enc, step, use_gpu = args
    R.ENC_THREADS[:] = ['-threads', '2']; R.FRAME_STEP = step; R.USE_GPU = use_gpu
    R.VIDEO_ENC = R.NVENC if enc == 'nvenc' else R.X264
    return str(_render_frames(Project(pid), tl, f0, f1, Path(out)))


def count_frames(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
                          '-of', 'csv=p=0', str(path)], capture_output=True, text=True).stdout.strip()
    return int(out or 0)


def render_range(proj, tl, t0, t1, out, log=print, workers=None, enc='x264', step=1):
    """Picture of [t0, t1) into out. Long ranges are cut into parts rendered side by side on the CPU cores (the frame
    loop is single-threaded) and joined by stream copy; every part starts on an exact frame and the total is checked.
    enc: 'x264' (same stream as render/picture.mp4: required when splicing into it) or 'nvenc' (GPU encode, for
    previews and whole-picture renders; falls back to x264 when there is no NVIDIA encoder)."""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import render as R
    cfg = settings()
    enc = 'nvenc' if enc == 'nvenc' and cfg['gpu_encode'] and nvenc_ok() else 'x264'
    fps = tl['fps']; f0, f1 = round(t0 * fps), round(t1 * fps); n = f1 - f0
    cap = 8 if enc == 'nvenc' else 64  # GeForce cards run at most 8 NVENC sessions at once
    R.USE_GPU = cfg['gpu_render']
    if cfg['gpu_render'] and enc == 'nvenc':
        cap = 3  # GPU frames: the encoder is the limit, 3 parts already reach ~157 fps (6 give no more)
    parts = max(1, min(workers or cfg['render_workers'], cap, n // (2 * fps)))  # at least ~2 s a part: each part loads its photos again
    if parts == 1:
        R.VIDEO_ENC = R.NVENC if enc == 'nvenc' else R.X264; R.FRAME_STEP = step
        try:
            return _render_frames(proj, tl, f0, f1, out)
        finally:
            R.VIDEO_ENC = R.X264; R.FRAME_STEP = 1
    bounds = [f0 + n * i // parts for i in range(parts + 1)]
    outs = [out.with_name(f'{out.stem}_p{i:02d}.mp4') for i in range(parts)]
    log(f'{n} frames in {parts} parallel parts ({"GPU NVENC" if enc == "nvenc" else "x264"} encode)')
    done = 0
    for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):  # one BLAS thread per part: 10 parts x 20 threads thrash
        os.environ[k] = '1'
    with ProcessPoolExecutor(max_workers=parts) as pool:
        futs = [pool.submit(_render_part, (proj.id, tl, a, b, str(o), enc, step, cfg['gpu_render'])) for a, b, o in zip(bounds, bounds[1:], outs)]
        for fu in as_completed(futs):
            fu.result(); done += 1
            log(f'  frame {done * n // parts}/{n}')  # progress line the job runner understands
    lst = out.with_name(out.stem + '_parts.txt')
    lst.write_text(''.join(f"file '{o.as_posix()}'\n" for o in outs), encoding='utf-8')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', '-movflags', '+faststart', str(out)],
                   check=True)
    got = count_frames(out)
    for o in outs + [lst]:
        o.unlink(missing_ok=True)
    if got != n:
        raise RuntimeError(f'range render has {got} frames, expected {n}')
    return out


def snap_range(tl, t0, t1):
    fps = tl['fps']
    return round(round(max(0.0, t0) * fps) / fps, 4), round(round(min(tl['duration'], t1) * fps) / fps, 4)


def preview(proj, t0, t1, mode='auto', log=print):
    """Short MP4 of [t0, t1] from the current timeline. mode auto: frames are rendered only if the range has picture
    edits (or there is no picture.mp4), else the range is cut from picture.mp4. Audio: the window's premix at the
    film's loudness offset."""
    import render as R
    tl, tag = proj.read()
    t0, t1 = snap_range(tl, t0, t1)
    if not 0 < t1 - t0 <= 180:
        raise OpError('preview range must be 0-180 s')
    dirty = dirty_ranges(proj, tl)
    hit = dirty is None or any(s < t1 and e > t0 for s, e in dirty)
    frames = mode in ('frames', 'fast') or (mode == 'auto' and hit)
    name = f'preview-{t0:08.2f}-{t1:08.2f}-{time.strftime("%H%M%S")}'
    folder = proj.work / 'previews'
    pic = folder / f'{name}-picture.mp4'
    t_start = time.time()
    if frames:
        log(f'rendering {round((t1 - t0) * tl["fps"])} frames {t0:.2f}-{t1:.2f} from the timeline')
        render_range(proj, tl, t0, t1, pic, log, enc='nvenc', step=2 if mode == 'fast' else 1)
    else:
        log(f'cutting {t0:.2f}-{t1:.2f} from picture.mp4 (no picture edits in this range)')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.4f}', '-i', str(proj.picture), '-t', f'{t1 - t0:.4f}', '-an',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', str(pic)], check=True)
    log('mixing the audio window')
    pre = folder / f'{name}-premix.wav'
    R.premix(proj.d, tl, pre, t0, t1)
    off = mix_offset(proj) or 0.0
    out = folder / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(pic), '-i', str(pre), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-af', f'volume={off}dB,alimiter=limit=0.89:level=disabled', '-c:a', 'aac', '-b:a', '256k', '-shortest',
                    '-movflags', '+faststart', str(out)], check=True)
    for p in (pic, pre, pre.with_name(pre.stem.replace('premix', 'mix') + '_graph.txt')):
        p.unlink(missing_ok=True)
    m = measure(out)
    log(f'preview -> {out}')
    return {'path': str(out), 'url': f'/previews/{out.name}', 't0': t0, 't1': t1, 'frames_rendered': frames, 'etag': tag,
            'seconds': round(time.time() - t_start, 1), 'loudness': m, 'monitor_gain_db': off}


def splice(proj, tl, ranges, log=print):
    """New picture = picture.mp4 with `ranges` re-rendered. Each range is widened to keyframes of picture.mp4 (outside any
    fade), rendered with the same encoder settings, and stream-copied between the untouched parts. Returns the path."""
    kfd = keyframes(proj); kf = sorted(kfd); dur = probe_duration(proj.picture); fps = tl['fps']
    trans = [(c['start'], c['start'] + (c.get('transition_in') or {}).get('dur', 0.5)) for tr in tl['tracks'] if tr['id'] == 'video'
             for c in tr['clips'] if c.get('transition_in')]
    def inside_fade(t):
        return any(a < t < b for a, b in trans)
    segs = []
    for s, e in ranges:
        a = max([k for k in kf if k <= s + 1e-6 and not inside_fade(k)] or [0.0])
        b = min([k for k in kf if k >= e - 1e-6 and not inside_fade(k)] or [dur])
        if segs and a <= segs[-1][1]:
            segs[-1][1] = max(segs[-1][1], b)
        else:
            segs.append([a, b])
    work = proj.work / 'splice'; work.mkdir(exist_ok=True)
    for p in work.glob('seg-*.mp4'):
        p.unlink()
    lines = []; pos = 0.0
    for i, (a, b) in enumerate(segs):
        log(f'render picture {a:.2f}-{b:.2f} ({b - a:.1f} s, {round((b - a) * fps)} frames)')
        seg = render_range(proj, tl, a, b, work / f'seg-{i:02d}.mp4', log)
        if a > pos + 1e-6:
            # the concat demuxer cuts on decode time: stop just before the keyframe's DTS (B-frames delay it ~2 frames)
            # and state the duration, so the next file starts exactly at a
            lines += [f"file '{proj.picture.as_posix()}'", f'inpoint {pos:.6f}' if pos else '',
                      f'outpoint {kfd[a] - 0.5 / fps:.6f}', f'duration {a - pos:.6f}']
        lines.append(f"file '{seg.as_posix()}'")
        pos = b
    if pos < dur - 1e-6:
        lines += [f"file '{proj.picture.as_posix()}'", f'inpoint {pos:.6f}']
    lst = work / 'list.txt'; lst.write_text('\n'.join(x for x in lines if x) + '\n', encoding='utf-8')
    new = proj.d / 'render' / 'picture.new.mp4'
    log('splice (stream copy)')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', '-movflags', '+faststart',
                    str(new)], check=True)
    want = round(dur * fps)
    got = int(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                              'stream=nb_read_packets', '-of', 'csv=p=0', str(new)], capture_output=True, text=True).stdout.strip() or 0)
    if abs(got - want) > 1:
        raise RuntimeError(f'spliced picture has {got} frames, expected {want}: kept the old picture.mp4')
    log(f'spliced picture: {got} frames, {len(segs)} re-rendered range(s)')
    return new, segs


def export(proj, log=print):
    """Studio export: picture (re-render only the edited ranges), the same voice-led mix and mux as doc.py build.
    The first export writes output/<id>/video.mp4; once it exists, exports go to video-studio-<time>.mp4 (never over it)."""
    import render as R
    tl, tag = proj.read()
    if tl.get('mock_voice'):
        raise OpError('mock voice in the timeline: not deliverable')
    t_start = time.time(); info = {'etag': tag}
    dirty = dirty_ranges(proj, tl)
    if dirty is None:
        log(f'no usable picture.mp4: rendering the whole picture in {settings()["render_workers"]} parallel parts')
        new = proj.d / 'render' / 'picture.new.mp4'
        render_range(proj, tl, 0.0, tl['duration'], new, log, enc='nvenc')
        os.replace(new, proj.picture); save_state(proj, tl); info['picture'] = 'full render'
    elif dirty:
        new, segs = splice(proj, tl, dirty, log)
        os.replace(new, proj.picture); save_state(proj, tl)
        info['picture'] = f're-rendered {len(segs)} range(s): ' + ', '.join(f'{a:.1f}-{b:.1f}' for a, b in segs)
    else:
        info['picture'] = 'reused render/picture.mp4 (audio-only changes)'
    log(info['picture'])
    log('mix (voice-led, two-pass loudnorm)')
    aud = proj.d / 'render' / 'mix.wav'
    n = R.mix(proj.d, tl, aud)
    first = proj.out_dir / 'video.mp4'  # the film's first export is the deliverable name; later ones never overwrite it
    out = first if not first.exists() else proj.out_dir / f'video-studio-{time.strftime("%Y%m%d-%H%M")}.mp4'
    log(f'mux -> {out}')
    R.mux(proj.picture, aud, out)
    write_credits(proj, tl, out.parent)
    m = measure(aud)
    info.update(path=str(out), clips_mixed=n, loudness=m, seconds=round(time.time() - t_start, 1))
    log(f'done: {out} ({info["seconds"]} s)')
    return info


def write_credits(proj, tl, out_dir):
    """Same LICENSES.md / credits.txt as doc.py build: only media actually on screen."""
    used = {c['src'] for t in tl['tracks'] for c in t['clips'] if c.get('src') and t['id'] != 'voice'}
    lic = proj.d / 'LICENSES.md'
    if lic.exists():
        rows = lic.read_text(encoding='utf-8').split('\n')
        keep = [r for r in rows if not r.startswith('| media/') or r.split('|')[1].strip() in used]
        (out_dir / 'LICENSES.md').write_text('\n'.join(keep), encoding='utf-8')
    lines = sorted({c['line'] + (f' - {c["page"]}' if c.get('page') else '') for c in tl.get('credits', []) if c['file'] in used})
    (out_dir / 'credits.txt').write_text('Archival media:\n' + '\n'.join(lines) + '\n', encoding='utf-8')


# ---------------------------------------------------------------- jobs (background processes shared by UI and MCP)
def start_job(proj, kind, args):
    jid = f'{kind}-{time.strftime("%Y%m%d-%H%M%S")}-{os.getpid() % 1000:03d}{int(time.time() * 1000) % 1000:03d}'
    st = proj.work / 'jobs' / f'{jid}.json'
    st.write_text(json.dumps({'id': jid, 'kind': kind, 'args': args, 'status': 'queued', 'log': [],
                              'started': time.strftime('%Y-%m-%d %H:%M:%S')}, ensure_ascii=False), encoding='utf-8')
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    logf = open(proj.work / 'jobs' / f'{jid}.log', 'w', encoding='utf-8')
    subprocess.Popen([PY, str(ROOT / 'studio' / 'jobs.py'), proj.id, jid], cwd=str(ROOT), stdout=logf, stderr=subprocess.STDOUT,
                     creationflags=flags)
    return jid


def job(proj, jid):
    p = proj.work / 'jobs' / f'{jid}.json'
    if not p.exists():
        raise OpError(f'no job {jid}')
    for _ in range(5):
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            time.sleep(0.05)
    return {'id': jid, 'status': 'unknown'}


def jobs(proj, n=20):
    out = []
    for p in sorted((proj.work / 'jobs').glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:n]:
        try:
            out.append(json.loads(p.read_text(encoding='utf-8')))
        except json.JSONDecodeError:
            pass
    return out


def wait_job(proj, jid, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = job(proj, jid)
        if j.get('status') in ('done', 'error', 'cancelled'):
            return j
        time.sleep(0.5)
    return job(proj, jid)


def cancel_job(proj, jid):
    j = job(proj, jid)
    if j.get('pid') and j.get('status') == 'running':
        subprocess.run(['taskkill', '/PID', str(j['pid']), '/T', '/F'], capture_output=True)
        j['status'] = 'cancelled'; j['ended'] = time.strftime('%Y-%m-%d %H:%M:%S')
        (proj.work / 'jobs' / f'{jid}.json').write_text(json.dumps(j, ensure_ascii=False), encoding='utf-8')
    return j


def at_time(proj, tl, t):
    """What is on screen and heard at t: for notes and for the agent."""
    out = {'t': t}
    for tr in tl['tracks']:
        if tr['id'] == 'voice':
            continue
        hit = [c for c in tr['clips'] if 'start' in c and c['start'] <= t < c.get('end', c['start'])]
        if tr['id'] == 'video' and not hit:
            prev = [c for c in tr['clips'] if c['start'] <= t]
            hit = prev[-1:] if prev else []
        if hit:
            out[tr['id']] = [{k: v for k, v in c.items() if k in ('id', 'start', 'end', 'src', 'type', 'props', 'caption', 'credit', 'gain_db', 'need')}
                             for c in hit]
    sid, s = proj.anchors().sentence_at(proj.timing(), t)
    if sid:
        v = next((c for tr in tl['tracks'] if tr['id'] == 'voice' for c in tr['clips'] if c['id'] == sid), {})
        out['sentence'] = {'id': sid, 'start': s['start'], 'end': s['end'], 'text': v.get('text')}
    return out


# ---------------------------------------------------------------- media library (Media / Âm thanh / Hiệu ứng panels)
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')
VIDEO_EXT = ('.mp4', '.webm', '.mov', '.mkv', '.avi', '.gif')
AUDIO_EXT = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac')


def media_kind(name):
    n = name.lower()
    return 'image' if n.endswith(IMAGE_EXT) else 'video' if n.endswith(VIDEO_EXT) else 'audio' if n.endswith(AUDIO_EXT) else None


def library(proj, scope):
    """Files for a panel. scope: project (this film's media, maps, imports), audio (shared music/sfx + the film's),
    overlays (assets/overlays + imports: footage for 'Lớp phủ media'). Paths are project-relative (timeline src)."""
    roots = {'project': [proj.d / 'media', proj.d / 'maps'],
             'audio': [ROOT / 'assets' / 'music', ROOT / 'assets' / 'sfx', proj.d / 'music', proj.d / 'sfx', proj.d / 'media' / 'import'],
             'overlays': [ROOT / 'assets' / 'overlays', proj.d / 'media' / 'import']}[scope]
    used = {}
    tl, _ = proj.read()
    for tr in tl['tracks']:
        for c in tr['clips']:
            for s in (c.get('src'), (c.get('params') or {}).get('src')):
                if s:
                    used[s] = used.get(s, 0) + 1
    out = []
    for r in roots:
        if not r.exists():
            continue
        for p in sorted(r.rglob('*')):
            k = media_kind(p.name) if p.is_file() else None
            if not k or (scope == 'audio' and k != 'audio') or (scope != 'audio' and k == 'audio'):
                continue
            rel = os.path.relpath(p, proj.d).replace(os.sep, '/')
            out.append({'src': rel, 'name': p.name, 'folder': os.path.relpath(p.parent, ROOT).replace(os.sep, '/'), 'kind': k,
                        'size': p.stat().st_size, 'used': used.get(rel, 0)})
    return out


def import_media(proj, name, data, as_audio=False):
    """Save an uploaded file in media/import/. as_audio: a browser recording (webm/ogg) converted to WAV (Quay)."""
    safe = ''.join(ch if ch.isalnum() or ch in '._- ' else '_' for ch in Path(name).name).strip() or 'file'
    if as_audio:
        folder = proj.d / 'media' / 'import'; folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / ('_rec_' + safe); tmp.write_bytes(data)
        out = folder / (Path(safe).stem + '.wav'); k = 2
        while out.exists():
            out = folder / f'{Path(safe).stem}-{k}.wav'; k += 1
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(tmp), '-ar', '48000', '-ac', '1', str(out)], check=True)
        tmp.unlink(missing_ok=True)
        return {'src': os.path.relpath(out, proj.d).replace(os.sep, '/'), 'kind': 'audio', 'size': out.stat().st_size,
                'duration': probe_duration(out)}
    if not media_kind(safe):
        raise OpError(f'unsupported file type: {safe}')
    folder = proj.d / 'media' / 'import'; folder.mkdir(parents=True, exist_ok=True)
    p = folder / safe; stem, ext = p.stem, p.suffix; k = 2
    while p.exists():
        p = folder / f'{stem}-{k}{ext}'; k += 1
    p.write_bytes(data)
    return {'src': os.path.relpath(p, proj.d).replace(os.sep, '/'), 'kind': media_kind(p.name), 'size': len(data)}


def thumb(proj, rel, w=240):
    """Small JPEG of an image or of a video's first second (cached)."""
    from PIL import Image, ImageOps
    from io import BytesIO
    p = resolve_media(proj, rel)
    key = hashlib.sha1(f'{p}|{p.stat().st_mtime}|{w}'.encode()).hexdigest()[:16]
    cache = proj.work / 'thumbs' / f'{key}.jpg'; cache.parent.mkdir(exist_ok=True)
    if cache.exists():
        return cache.read_bytes()
    if media_kind(p.name) == 'video':
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '0.5', '-i', str(p), '-frames:v', '1', '-vf', f'scale={w}:-2', '-f', 'mjpeg', '-'],
                             capture_output=True).stdout
        if not raw:
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-frames:v', '1', '-vf', f'scale={w}:-2', '-f', 'mjpeg', '-'],
                                 capture_output=True).stdout
        cache.write_bytes(raw); return raw
    im = ImageOps.exif_transpose(Image.open(p)).convert('RGB'); im.thumbnail((w, w * 2))
    b = BytesIO(); im.save(b, 'JPEG', quality=80); cache.write_bytes(b.getvalue()); return b.getvalue()


def catalog():
    """Everything the editor panels offer (built from render_fx so UI and renderer cannot drift)."""
    import render_fx as FX
    return {'effects': FX.EFFECTS, 'ranges': FX.RANGES, 'blends': FX.BLENDS, 'transitions': FX.TRANSITIONS,
            'motion_presets': FX.MOTION_PRESETS, 'color_default': FX.COLOR_DEFAULT, 'text_default': FX.TEXT_DEFAULT,
            'subtitle_default': FX.SUB_DEFAULT, 'color_presets': FX.COLOR_PRESETS, 'effect_presets': FX.EFFECT_PRESETS}
