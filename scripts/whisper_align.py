"""Whisper timing for the voice (docs/VOICE.md#chunked-ai84): the OmniVoice Playground logic, never AI84's transcript.

- WhisperWorker: runs scripts/whisper_worker.py under a Python that has faster-whisper (this venv, or the user's system
  Python as OmniVoice uses it), with the medium model from TOOL SY when present. Start it *before* the voice is
  generated (the model takes ~15 s to load), feed it each chunk as it arrives, close() it when done: the process exits
  and the GPU memory is released.
- char_times(): the script's own text aligned 100 % to Whisper's words, character by character (difflib matching blocks
  of >= 3 characters, linear interpolation in between), exactly as OmniVoice's align_original_text.
- split_subtitles() / cue_times(): OmniVoice's subtitle splitting (sentence ends, phrase breaks after 10+ characters,
  42 characters + 15 tolerance) and its cue timing rules (no overlap, minimum duration by length).
- cut_points(): where to cut a chunk into sentences: the quietest 10 ms between one sentence's last character and the
  next one's first.
"""
import bisect, difflib, json, os, queue, subprocess, sys, threading, time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAX_CHARS = 42
SY_MEDIUM = Path(r'D:\YOUTUBE\TOOL_CODE_BY_ME\TOOL SY\.dev-user-data\models\medium')
QUOTES_CLOSE = set('」』"\'”’')
BREAK_MINOR = set('、，,;；:：—–-')


# ---------------------------------------------------------------- worker
def find_python(cfg=None):
    """A Python that can import faster_whisper: brief voice.whisper_python, env WHISPER_PYTHON, this venv, the user's
    system Pythons, OmniVoice's backend venv."""
    home = Path(os.environ.get('USERPROFILE', str(Path.home())))
    cands = [(cfg or {}).get('whisper_python'), os.environ.get('WHISPER_PYTHON'), sys.executable,
             home / 'AppData/Local/Programs/Python/Python313/python.exe', home / 'AppData/Local/Programs/Python/Python312/python.exe',
             ROOT.parent / 'OmniVoice_Playground/backend/.venv/Scripts/python.exe']
    for c in cands:
        if not c or not Path(c).exists():
            continue
        r = subprocess.run([str(c), '-c', 'import faster_whisper'], capture_output=True)
        if r.returncode == 0:
            return str(c)
    raise RuntimeError('no Python with faster-whisper found: set brief voice.whisper_python or env WHISPER_PYTHON')


def model_path(cfg=None):
    m = (cfg or {}).get('whisper_model')
    if m:
        return m
    return str(SY_MEDIUM) if SY_MEDIUM.exists() else 'medium'


class WhisperWorker:
    """One faster-whisper process; transcribe() calls are served in order."""

    def __init__(self, cfg=None, log=print):
        self.log = log; self.lines = queue.Queue(); self.lock = threading.Lock()
        py = find_python(cfg)
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        self.p = subprocess.Popen([py, str(ROOT / 'scripts' / 'whisper_worker.py'), model_path(cfg)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8', env=env,
                                  creationflags=flags)
        threading.Thread(target=self._read, daemon=True).start()
        self.ready = threading.Event(); self.t0 = time.time()
        log(f'whisper: loading {Path(model_path(cfg)).name} with {py} (in the background)')

    def _read(self):
        for line in self.p.stdout:
            line = line.rstrip()
            if line.startswith('READY'):
                self.ready.set(); self.log(f'whisper: model ready ({line[6:]})')
            elif line.startswith('INFO'):
                self.log('whisper: ' + line[5:])
            else:
                self.lines.put(line)
        self.ready.set(); self.lines.put('EXIT')

    def transcribe(self, wav, lang, out):
        """Words [{'word', 'start', 'end'}] of wav (also written to out)."""
        with self.lock:
            self.ready.wait()
            if self.p.poll() is not None:
                raise RuntimeError('whisper worker exited')
            self.p.stdin.write(json.dumps({'wav': str(wav), 'out': str(out), 'lang': lang}) + '\n'); self.p.stdin.flush()
            while True:
                line = self.lines.get()
                if line == 'EXIT':
                    raise RuntimeError('whisper worker exited')
                if line.startswith('DONE') or line.startswith('ERR'):
                    break
            if line.startswith('ERR'):
                raise RuntimeError(line)
            return json.loads(Path(out).read_text(encoding='utf-8'))['words']

    def close(self):
        """Free the model: the worker exits, which releases its GPU memory."""
        if self.p.poll() is None:
            try:
                self.p.stdin.write(json.dumps({'quit': True}) + '\n'); self.p.stdin.flush(); self.p.stdin.close()
                self.p.wait(timeout=60)
            except Exception:  # noqa: BLE001
                self.p.kill()
        self.log('whisper: closed, GPU memory released')


# ---------------------------------------------------------------- OmniVoice alignment logic
def char_times(orig_text, words, is_cjk=False):
    """Time of every character of orig_text (spaces included, interpolated), from Whisper words: OmniVoice's
    align_original_text (character-level difflib, blocks >= 3 chars, linear interpolation, ends extrapolated to the
    audio's first/last word)."""
    w_chars, w_times = [], []
    for w in words:
        s = (w.get('word') or '').strip()
        if not s:
            continue
        dur = max(0.01, w['end'] - w['start'])
        for ci, ch in enumerate(s):
            w_chars.append(ch.lower()); w_times.append(w['start'] + ci / max(1, len(s)) * dur)
    pos = [i for i, ch in enumerate(orig_text) if not ch.isspace()]
    if not pos or not w_chars:
        return None
    orig = [orig_text[i].lower() for i in pos]
    blocks = [b for b in difflib.SequenceMatcher(None, orig, w_chars, autojunk=False).get_matching_blocks()
              if b.size >= (2 if is_cjk else 3)]
    t = [None] * len(orig)
    anchors = []
    for a, b, size in blocks:
        for k in range(size):
            t[a + k] = w_times[b + k]; anchors.append((a + k, w_times[b + k]))
    if not anchors:
        step = (w_times[-1] - w_times[0]) / max(1, len(orig))
        t = [w_times[0] + i * step for i in range(len(orig))]
    else:
        ai = [i for i, _ in anchors]; at = [x for _, x in anchors]
        for i in range(len(orig)):
            if t[i] is None:
                p = bisect.bisect_left(ai, i)
                if p == 0:
                    t[i] = w_times[0] + i / max(1, ai[0]) * (at[0] - w_times[0])
                elif p >= len(ai):
                    t[i] = at[-1] + (i - ai[-1]) / max(1, len(orig) - 1 - ai[-1]) * (w_times[-1] - at[-1])
                else:
                    t[i] = at[p - 1] + (i - ai[p - 1]) / max(1, ai[p] - ai[p - 1]) * (at[p] - at[p - 1])
    full = [None] * len(orig_text)
    for k, i in enumerate(pos):
        full[i] = t[k]
    for i in range(len(full)):  # spaces: the next character's time
        if full[i] is None:
            nxt = next((full[j] for j in range(i + 1, len(full)) if full[j] is not None), None)
            full[i] = nxt if nxt is not None else full[i - 1]
    return full


def split_subtitles(text, max_chars=MAX_CHARS, is_cjk=False):
    """OmniVoice's split_text_into_subtitles: break at sentence ends; a long sentence at phrase marks (10+ chars before,
    8+ after) or at the last space before max_chars; never leave < 6 chars on their own."""
    clean = text.replace('\r\n', '\n').replace('\r', '\n')
    sents, cur, i = [], '', 0
    while i < len(clean):
        c = clean[i]; cur += c; brk = False
        if c == '\n':
            brk = True
        elif c in '。！？.!?':
            while i + 1 < len(clean) and clean[i + 1] in QUOTES_CLOSE:
                cur += clean[i + 1]; i += 1
            brk = True
        if brk:
            if cur.strip():
                sents.append(cur.strip())
            cur = ''
        i += 1
    if cur.strip():
        sents.append(cur.strip())
    chunks, tol = [], (8 if is_cjk else 15)
    for s in sents:
        if len(s) <= max_chars + tol:
            chunks.append(s); continue
        parts, part, j = [], '', 0
        while j < len(s):
            ch = s[j]; part += ch
            while j + 1 < len(s) and s[j + 1] in QUOTES_CLOSE:
                part += s[j + 1]; j += 1
            rem = len(s) - (j + 1)
            if rem < 6:
                part += s[j + 1:]; parts.append(part.strip()); part = ''; break
            if ch in BREAK_MINOR and len(part) >= 10 and rem >= 8:
                parts.append(part.strip()); part = ''
            elif len(part) >= max_chars:
                if not is_cjk and ' ' in part and part.rfind(' ') > 12:
                    k = part.rfind(' '); parts.append(part[:k].strip()); part = part[k + 1:]
                else:
                    parts.append(part.strip()); part = ''
            j += 1
        if part.strip():
            parts.append(part.strip())
        chunks += parts
    return [c for c in chunks if c]


def cue_times(spans, is_cjk=False):
    """OmniVoice's cue timing over [(first char time, last char time, text)] in order: starts never before the previous
    end, a minimum duration by length (0.8 s or 0.03 s/char), ends pulled back to the next start."""
    out, prev_end = [], 0.0
    for k, (a, b, text) in enumerate(spans):
        if a < prev_end:
            a = prev_end
        min_dur = max(0.8, len(text) * (0.05 if is_cjk else 0.03))
        if b - a < min_dur:
            b = a + min_dur
        if k + 1 < len(spans):
            nxt = spans[k + 1][0]
            if nxt > a and b > nxt:
                b = max(a + 0.5, nxt)
        out.append((a, b, text)); prev_end = b
    return out


def silences(x, sr, min_len=0.08):
    """[(start s, end s, quietest sample)] of the pauses inside x: 10 ms frames 32 dB under the speech level, >= min_len."""
    hop = sr // 100; n = len(x) // hop
    if n < 3:
        return []
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-9
    floor = np.percentile(rms, 95) * 10 ** (-32 / 20)
    quiet = rms < floor; out, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * hop / sr >= min_len and i > 0 and j < n:  # pauses between sounds, not the chunk's edges
                k = i + int(np.argmin(rms[i:j]))
                out.append((i * hop / sr, j * hop / sr, k * hop + hop // 2))
            i = j
        else:
            i += 1
    return out


def cut_points(x, sr, spans, reach=1.5):
    """Sample index to cut between consecutive sentences. Each boundary goes into a real pause of the audio: the pauses
    are matched to the boundaries Whisper predicts ((end of sentence k + start of k+1) / 2) by dynamic programming (in
    order, least total distance, within `reach` s), so short sentences heard as one ("Gạo. Muối. Đèn.") still split at
    their own pauses. A boundary with no pause in reach is cut at the quietest 10 ms near its prediction."""
    hop = sr // 100
    pred = [(b0 + a1) / 2 for (_, b0), (a1, _) in zip(spans, spans[1:])]
    gaps = silences(x, sr)

    def quietest(p, w=0.15):
        i0, i1 = max(0, int((p - w) * sr)), min(len(x), int((p + w) * sr))
        seg = x[i0:i1]; n = len(seg) // hop
        if n < 1:
            return int(p * sr)
        rms = np.sqrt(np.mean(seg[:n * hop].reshape(n, hop) ** 2, axis=1))
        return i0 + int(np.argmin(rms)) * hop + hop // 2
    cands = []
    for p in pred:
        c = [(abs((g0 + g1) / 2 - p) - 0.25 * min(g1 - g0, 0.6), q) for g0, g1, q in gaps if abs((g0 + g1) / 2 - p) <= reach]
        c.append((0.9, quietest(p)))  # no pause near: costs more than any pause in reach
        cands.append(c)
    INF = float('inf'); best = [[(c, -1) for c, _ in cands[0]]] if cands else []
    for k in range(1, len(cands)):
        row = []
        for c, q in cands[k]:
            prev = [(best[k - 1][j][0], j) for j, (_, q0) in enumerate(cands[k - 1]) if q0 + 0.1 * sr < q]
            row.append((c + min(prev)[0], min(prev)[1]) if prev else (INF, -1))
        best.append(row)
    if not best:
        return []
    j = min(range(len(best[-1])), key=lambda j: best[-1][j][0]); out = []
    for k in range(len(best) - 1, -1, -1):
        out.append(cands[k][j][1]); j = best[k][j][1]
    return out[::-1]
