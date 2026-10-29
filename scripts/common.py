"""Shared helpers: paths, JSON, ffmpeg, audio decode, API key lookup. No network calls here."""
import hashlib, json, os, subprocess, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / 'projects'
SR = 48000


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def write(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(p)


def digest(*parts, n=10):
    h = hashlib.sha256()
    for x in parts:
        h.update(json.dumps(x, ensure_ascii=False, sort_keys=True).encode('utf-8'))
    return h.hexdigest()[:n]


def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, **kw)


def probe(p):
    out = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate',
               '-of', 'json', p]).stdout
    return json.loads(out)


def load_audio(p, sr=SR):
    """Decode any audio file to mono float32 at `sr`. Read-only view (40-min narrations: no second copy)."""
    raw = run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-']).stdout
    return np.frombuffer(raw, dtype=np.float32)


def save_wav(p, x, sr=SR):
    import soundfile as sf
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(p), np.asarray(x, dtype=np.float32), sr, subtype='PCM_24')


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-9))


def job_dir(job):
    d = Path(job)
    if not d.is_absolute():
        d = PROJECTS / job
    if not (d / 'state.json').exists():
        sys.exit(f'no such job: {job} (run: doc.py ingest)')
    return d


def mark(d, stage, **info):
    st = read(d / 'state.json')
    st.setdefault('stages', {})[stage] = {'done': True, **info}
    write(d / 'state.json', st)


def elevenlabs_key():
    """Process env first, then the Windows *user* environment (set by the user, never stored in the repo)."""
    k = os.environ.get('ELEVENLABS_API_KEY')
    if not k and sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
                k = winreg.QueryValueEx(h, 'ELEVENLABS_API_KEY')[0]
        except OSError:
            k = None
    return k or None
