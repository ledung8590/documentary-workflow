"""AI84.pro TTS client (ElevenLabs voices incl. eleven_v4 with [emotion] audio tags). Async: create job, poll, download.

Key lookup (never printed or written anywhere): env AI84_API_KEY, Windows user env AI84_API_KEY, then the
`xi-api-key:` value inside the user's "Tài liệu api AI84.PRO.txt" in the workspace root (the user's own file,
gitignored together with key.txt).
"""
import json, os, random, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

from common import ROOT

BASE = 'https://api.ai84.pro'


def key():
    k = os.environ.get('AI84_API_KEY')
    if not k and sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
                k = winreg.QueryValueEx(h, 'AI84_API_KEY')[0]
        except OSError:
            k = None
    if not k:
        for p in ROOT.glob('*AI84*.txt'):
            m = re.search(r'xi-api-key:\s*([A-Za-z0-9_\-]{16,})', p.read_text(encoding='utf-8', errors='ignore'))
            if m:
                k = m.group(1); break
    if not k:
        raise RuntimeError('AI84 API key not found (set user env AI84_API_KEY)')
    return k


def _req(method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={'xi-api-key': key(), 'Content-Type': 'application/json', 'User-Agent': 'documentary-workflow/0.1'})
    for attempt in range(30):  # a lost poll loses a job already paid for: keep backing off on 429 instead of giving up
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get('Retry-After') or 5) + random.uniform(0, 3) + min(attempt, 10)); continue
            if e.code >= 500 and method == 'GET':
                time.sleep(3); continue
            raise RuntimeError(f'AI84 HTTP {e.code}: {e.read()[:300].decode("utf-8", "replace")}') from None
    raise RuntimeError('AI84: too many retries')


def voices(search, page_size=20):
    q = urllib.parse.urlencode({'search': search, 'page_size': page_size, 'page': 0})
    return _req('GET', f'/v1/shared-voices?{q}')


def tts(text, voice_id, model='eleven_v4', settings=None, language_code=None, out=None, deadline=600):
    """Create a TTS job, poll until done, download the audio to `out`. Returns (path, credit_cost)."""
    body = {'text': text, 'voice_id': voice_id, 'model_id': model, 'output_format': 'mp3_44100_192'}
    if settings: body['voice_settings'] = settings
    if language_code: body['language_code'] = language_code
    job = _req('POST', '/v2/text-to-speech/async', body)
    jid, cost, t0 = job['job_id'], job.get('credit_cost'), time.time()
    while time.time() - t0 < deadline:
        time.sleep(4.0)
        j = _req('GET', f'/v2/text-to-speech/async/{jid}')['job']
        if j['status'] == 'done':
            req = urllib.request.Request(j['audioUrl'], headers={'User-Agent': 'documentary-workflow/0.1'})
            with urllib.request.urlopen(req, timeout=120) as resp:
                Path(out).write_bytes(resp.read())
            return out, j.get('credit_cost', cost)
        if j['status'] == 'failed':
            raise RuntimeError(f'AI84 job failed: {j.get("errorMessage") or j.get("errorCode")}')
    raise RuntimeError('AI84 job timed out')
