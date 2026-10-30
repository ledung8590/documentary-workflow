"""Documentary Studio: web UI + API for one project (docs/STUDIO.md).

  PY studio/server.py <project> [--port 5280] [--no-browser]

The server writes only projects/<id>/timeline.json (ETag-guarded) plus its own work files in render/studio/.
Renders run as background jobs (studio/jobs.py); exports go to output/<id>/video-studio-<time>.mp4.
"""
import argparse, json, mimetypes, os, re, sys, threading, time, traceback, webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core as C  # noqa: E402

UI = Path(__file__).resolve().parent / 'ui'
mimetypes.add_type('text/javascript', '.js'); mimetypes.add_type('audio/mpeg', '.mp3'); mimetypes.add_type('audio/wav', '.wav')


class App:
    def __init__(self, pid):
        self.proj = C.open_project(pid)
        self.framer = C.Framer(self.proj)
        self._tl = (None, None)  # (etag, parsed timeline) cache for frame/audio requests
        self.offset = None
        threading.Thread(target=self._offset, daemon=True).start()

    def _offset(self):
        try:
            self.offset = C.mix_offset(self.proj)
        except Exception:  # noqa: BLE001 - monitor gain is a convenience
            traceback.print_exc()

    def timeline(self):
        b = self.proj.read_bytes(); tag = C.etag_of(b)
        if self._tl[0] != tag:
            self._tl = (tag, json.loads(b.decode('utf-8')))
        return self._tl[1], tag


class Handler(BaseHTTPRequestHandler):
    app: App = None
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *a):
        if '/api/frame' in self.path or '/api/etag' in self.path or '/api/jobs' in self.path:
            return
        sys.stderr.write(f'{time.strftime("%H:%M:%S")} {fmt % a}\n')

    # ---------------------------------------------------------------- helpers
    def send(self, code, body=b'', ctype='application/json; charset=utf-8', headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        if 'Cache-Control' not in (headers or {}):
            self.send_header('Cache-Control', 'no-store')
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def body(self):
        return json.loads(self._raw.decode('utf-8')) if self._raw else {}

    def file(self, p, ctype=None):
        """Static file with HTTP Range (the browser seeks inside 4 GB picture.mp4 and long WAVs)."""
        p = Path(p)
        if not p.is_file():
            return self.send(404, {'error': 'not found'})
        size = p.stat().st_size; ctype = ctype or mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        rng = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range') or '')
        start, end = 0, size - 1
        if rng and (rng.group(1) or rng.group(2)):
            if rng.group(1):
                start = int(rng.group(1)); end = int(rng.group(2)) if rng.group(2) else size - 1
            else:
                start = size - int(rng.group(2))
            end = min(end, size - 1, start + 8 * 1024 * 1024 - 1)
        self.send_response(206 if rng else 200)
        self.send_header('Content-Type', ctype); self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if rng:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if self.command == 'HEAD':
            return
        with p.open('rb') as f:
            f.seek(start); left = end - start + 1
            while left > 0:
                b = f.read(min(1 << 20, left))
                if not b:
                    break
                try:
                    self.wfile.write(b)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    return
                left -= len(b)

    # ---------------------------------------------------------------- routes
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self.route('GET')

    def do_POST(self):
        self.route('POST')

    def do_PUT(self):
        self.route('PUT')

    def do_DELETE(self):
        self.route('DELETE')

    def route(self, method):
        n = int(self.headers.get('Content-Length') or 0)
        self._raw = self.rfile.read(n) if n else b''  # always drain the body: keep-alive stays in sync on early errors
        u = urlparse(self.path); q = {k: v[-1] for k, v in parse_qs(u.query).items()}; path = unquote(u.path)
        app, proj = self.app, self.app.proj
        try:
            if method == 'GET' and path in ('/', '/index.html'):
                return self.file(UI / 'index.html', 'text/html; charset=utf-8')
            if method == 'GET' and path.startswith('/ui/'):
                p = (UI / path[4:]).resolve()
                return self.file(p) if UI in p.parents else self.send(403, {'error': 'forbidden'})
            if method == 'GET' and path.startswith('/media/'):
                return self.file(C.resolve_media(proj, path[7:]))
            if method == 'GET' and path == '/picture.mp4':
                return self.file(proj.picture, 'video/mp4')
            if method == 'GET' and path.startswith('/previews/'):
                return self.file(proj.work / 'previews' / Path(path).name, 'video/mp4')
            if method == 'GET' and path.startswith('/exports/'):
                return self.file(proj.out_dir / Path(path).name, 'video/mp4')

            if path == '/api/project' and method == 'GET':
                tl, tag = app.timeline()
                return self.send(200, {'id': proj.id, 'title': tl.get('title') or proj.id, 'fps': tl['fps'], 'duration': tl['duration'],
                                       'language': tl.get('language'), 'etag': tag, 'picture': proj.picture.exists(),
                                       'dirty': C.dirty_ranges(proj, tl), 'state': C.load_state(proj), 'monitor_gain_db': app.offset,
                                       'projects': C.projects(), 'history': proj.history(40), 'history_count': proj.history_count()})
            if path == '/api/timeline':
                if method == 'GET':
                    b = proj.read_bytes()
                    return self.send(200, b, headers={'ETag': f'"{C.etag_of(b)}"'})
                if method == 'PUT':
                    m = (self.headers.get('If-Match') or '').strip('"')
                    if not m:
                        return self.send(428, {'error': 'If-Match (ETag) required'})
                    tag = proj.put(self.body(), m, who='user', why=self.headers.get('X-Why') or 'save from studio')
                    return self.send(200, {'etag': tag}, headers={'ETag': f'"{tag}"'})
            if path == '/api/etag' and method == 'GET':
                return self.send(200, {'etag': proj.etag()})
            if path == '/api/ops' and method == 'POST':
                b = self.body(); m = (self.headers.get('If-Match') or '').strip('"') or b.get('etag')
                before = None
                def fn(tl):
                    nonlocal before
                    before = json.loads(json.dumps(tl))
                    return C.apply_ops(tl, b['ops'], proj.anchors())
                log, tag = proj.transact(fn, m, who='user', why='; '.join(o.get('op', '') + ' ' + str(o.get('id', '')) for o in b['ops']))
                tl, _ = app.timeline()
                return self.send(200, {'etag': tag, 'log': log, 'kind': C.edit_kind(before, tl), 'dirty': C.dirty_ranges(proj, tl),
                                       'timeline': tl}, headers={'ETag': f'"{tag}"'})
            if path == '/api/timing' and method == 'GET':
                timing = proj.timing(); tl, _ = app.timeline()
                texts = {c['id']: c.get('text', '') for tr in tl['tracks'] if tr['id'] == 'voice' for c in tr['clips']}
                return self.send(200, {'sentences': [{'id': k, 'start': s['start'], 'end': s['end'], 'text': texts.get(k, ''),
                                                      'words': [[round(w['start'], 3), round(w.get('end', w['start']), 3), w.get('w', '')]
                                                                for w in s.get('words') or []]} for k, s in timing.items()]})
            if path == '/api/subtitle' and method == 'GET':  # cue on screen at t (click-to-edit)
                tl, _ = app.timeline()
                return self.send(200, {'cue': C.subtitle_at(proj, tl, float(q['t'])) if (tl.get('fx') or {}).get('subtitles') else None})
            if path == '/api/subtitles' and method == 'GET':
                tl, _ = app.timeline()
                return self.send(200, {'cues': C.subtitle_cues(proj, tl)})
            if path == '/api/settings':
                if method == 'POST':
                    return self.send(200, C.save_settings(self.body()))
                return self.send(200, dict(C.settings(), cpu_count=os.cpu_count(), nvenc=C.nvenc_ok()))
            if path == '/api/catalog' and method == 'GET':
                return self.send(200, C.catalog())
            if path == '/api/library' and method == 'GET':
                return self.send(200, {'files': C.library(proj, q.get('scope', 'project'))})
            if path == '/api/thumb' and method == 'GET':
                return self.send(200, C.thumb(proj, q['src'], int(q.get('w', 240))), 'image/jpeg', {'Cache-Control': 'max-age=86400'})
            if path == '/api/import' and method == 'POST':  # raw file body, ?name=<file name>
                return self.send(200, C.import_media(proj, q['name'], self._raw, q.get('audio') == '1'))
            if path == '/api/frame' and method == 'POST':  # draft frame: ops applied to a copy, nothing saved (live sliders)
                b = self.body(); tl, _ = app.timeline(); tl = json.loads(json.dumps(tl))
                if b.get('ops'):
                    C.apply_ops(tl, b['ops'], proj.anchors())
                jpg = app.framer.jpeg(tl, float(b.get('t', 0)), int(b.get('w', 960)), 80)
                return self.send(200, jpg, 'image/jpeg')
            if path == '/api/frame' and method == 'GET':
                tl, _ = app.timeline()
                jpg = app.framer.jpeg(tl, float(q.get('t', 0)), int(q.get('w', 960)), int(q.get('q', 80)))
                return self.send(200, jpg, 'image/jpeg')
            if path == '/api/audio' and method == 'GET':
                tl, _ = app.timeline()
                t0 = max(0.0, float(q['t0'])); t1 = min(tl['duration'], float(q['t1']))
                only = set(q['only'].split(',')) if q.get('only') is not None else None
                wav = C.audio_window(proj, tl, t0, t1, only)
                return self.send(200, wav, 'audio/wav', {'X-Gain-Db': str(app.offset or 0.0)})
            if path == '/api/peaks' and method == 'GET':
                return self.send(200, C.peaks(proj, q['src']), 'application/octet-stream')
            if path == '/api/measure' and method == 'GET':
                tl, _ = app.timeline(); t0 = float(q['t0']); t1 = float(q['t1'])
                out = proj.work / 'tmp' / f'measure-{threading.get_ident()}-premix.wav'
                import render as R
                R.premix(proj.d, tl, out, t0, t1)
                m = C.measure(out); out.unlink(missing_ok=True)
                if m and app.offset is not None:
                    m['I_film'] = round(m['I'] + app.offset, 1)  # at the export's loudnorm gain
                    m['TP_film'] = round(m['TP'] + app.offset, 1) if m.get('TP') is not None else None
                return self.send(200, m or {})
            if path == '/api/at' and method == 'GET':
                tl, _ = app.timeline()
                return self.send(200, C.at_time(proj, tl, float(q['t'])))

            if path == '/api/notes':
                if method == 'GET':
                    tl, tag = app.timeline()
                    return self.send(200, {'etag': tag, 'notes': tl.get('review_notes', [])})
                if method == 'POST':  # {op: add|update|delete, ...}; notes merge into the current file (no If-Match needed)
                    b = self.body(); b.setdefault('op', 'add')
                    note, tag = proj.transact(lambda tl: C.note_ops(tl, b), who='user', why=f'note {b["op"]} {b.get("id", "")}')
                    return self.send(200, {'etag': tag, 'note': note})

            if path == '/api/render' and method == 'POST':
                b = self.body()
                return self.send(200, {'job': C.start_job(proj, 'preview', {'t0': float(b['t0']), 't1': float(b['t1']), 'mode': b.get('mode', 'auto')})})
            if path == '/api/export' and method == 'POST':
                if (proj.work / 'export.lock').exists():
                    return self.send(409, {'error': 'Đang có một lần xuất bản chạy'})
                return self.send(200, {'job': C.start_job(proj, 'export', {})})
            if path == '/api/jobs' and method == 'GET':
                return self.send(200, {'jobs': C.jobs(proj)})
            m = re.match(r'/api/jobs/([\w.-]+)(/cancel)?$', path)
            if m:
                return self.send(200, C.cancel_job(proj, m.group(1)) if m.group(2) and method == 'POST' else C.job(proj, m.group(1)))
            if path == '/api/exports' and method == 'GET':
                files = sorted(proj.out_dir.glob('video*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True) if proj.out_dir.exists() else []
                return self.send(200, {'files': [{'name': p.name, 'size': p.stat().st_size, 'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))} for p in files]})
            return self.send(404, {'error': f'no route {method} {path}'})
        except C.Conflict as e:
            return self.send(412, {'error': 'conflict', 'etag': e.etag, 'message': 'Timeline vừa được sửa ở nơi khác (agent?). Tải lại rồi sửa tiếp.'})
        except (C.OpError, KeyError, ValueError) as e:
            return self.send(400, {'error': str(e)})
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self.send(500, {'error': f'{type(e).__name__}: {e}'})


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace'); sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project', nargs='?', default=C.last_project())
    ap.add_argument('--port', type=int, default=5280); ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()
    if not a.project:
        sys.exit(f'which project? {C.projects()}')
    Handler.app = App(a.project)
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), Handler)
    url = f'http://localhost:{a.port}/'
    print(f'Studio: {a.project} -> {url}  (Ctrl+C to stop)', flush=True)
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
