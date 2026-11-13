"""Local receiver for images generated in Google Flow (story mode, docs/STORY_MODE.md).

A small script running inside the user's Flow tab (driven by Claude in Chrome) POSTs each finished
image here; this saves it into the story's image folder. The Flow page itself does the generation
(the user's own account, the page's own checks); this only receives files.

    PY scripts/flow_receiver.py "input/<story>" [--port 47188]

POST /save?name=001.png  body = image bytes (jpeg/png) -> <story>/001.png (converted to PNG)
POST /save?name=refs/Joachim.png                      -> <story>/refs/Joachim.png
GET  /jobs                                            -> <story>/_gen/flow_jobs.json (prompts for the page)
GET  /status                                          -> which NNN.png exist
"""
import argparse, io, json, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('story'); ap.add_argument('--port', type=int, default=47188)
A = ap.parse_args(); ROOT = Path(A.story).resolve()
NAME = re.compile(r'^(refs/[A-Za-z0-9_-]+|_gen/[A-Za-z0-9_-]+|\d{3,4})\.png$')


class H(BaseHTTPRequestHandler):
    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')

    def reply(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.cors()
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path
        if p == '/jobs':
            f = ROOT / '_gen' / 'flow_jobs.json'
            return self.reply(200, json.loads(f.read_text(encoding='utf-8')) if f.exists() else [])
        if p == '/status':
            return self.reply(200, sorted(x.name for x in ROOT.glob('[0-9][0-9][0-9]*.png')))
        self.reply(404, {'error': 'no'})

    def do_POST(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path != '/save':
            return self.reply(404, {'error': 'no'})
        name = (q.get('name') or [''])[0]
        if not NAME.match(name):
            return self.reply(400, {'error': 'bad name'})
        data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        out = ROOT / name; out.parent.mkdir(parents=True, exist_ok=True)
        try:
            Image.open(io.BytesIO(data)).convert('RGB').save(out)
        except Exception as e:
            return self.reply(400, {'error': str(e)})
        print('saved', name, len(data), flush=True)
        self.reply(200, {'ok': name})

    def log_message(self, *a):
        pass


print(f'flow receiver on http://127.0.0.1:{A.port} -> {ROOT}', flush=True)
ThreadingHTTPServer(('127.0.0.1', A.port), H).serve_forever()
