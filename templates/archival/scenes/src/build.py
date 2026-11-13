"""Build scenes/<name>.js = _kit.js + src/<name>.js, with duration set from durations.json (written by plan.py).
python build.py [name ...]
Scene sources may write @{S146 "vier Jahre"} for "the moment that word is spoken" in scene seconds (analysis boards)."""
import json, re, sys
from pathlib import Path

SRC = Path(__file__).parent
OUT = SRC.parent
kit = '\n'.join((SRC / f).read_text(encoding='utf-8') for f in ['_kit.js'] + sorted(x.name for x in SRC.glob('_*.js') if x.name != '_kit.js'))  # _kit.js + film helpers (_j.js, _m.js ...)
dur = json.loads((SRC / 'durations.json').read_text(encoding='utf-8')) if (SRC / 'durations.json').exists() else {}
names = sys.argv[1:] or [p.stem for p in SRC.glob('*.js') if not p.stem.startswith('_')]
starts = json.loads((SRC / 'starts.json').read_text(encoding='utf-8')) if (SRC / 'starts.json').exists() else {}
WORDS = OUT.parent / 'voice' / 'words.json'
_words = None


def _norm(w):
    import unicodedata
    return re.sub(r'[^\w]', '', unicodedata.normalize('NFC', w.lower()))


def word_time(n, tok):
    """@{S146 "vier Jahre"+0.2} / @{S146} / @{S146$}: film time of that word (sentence start / end) minus the scene's start,
    so board items appear on the narrator's word (K.board works in real seconds)."""
    global _words
    if _words is None:
        _words = json.loads(WORDS.read_text(encoding='utf-8'))
    m = re.match(r'^\s*(S\d{3,4})(\$)?(?:\s+"([^"]+)")?\s*([+-][\d.]+)?\s*$', tok)
    if not m or n not in starts:
        raise SystemExit(f'{n}: cannot resolve @{{{tok}}} (needs scenes/src/starts.json from plan.py durations)')
    sid, end, ph, off = m.groups(); ws = [w for w in _words if w['sentence'] == sid]
    if not ws:
        raise SystemExit(f'{n}: no words for {sid}')
    t = ws[-1]['end'] if end else ws[0]['start']
    if ph:
        want = [_norm(x) for x in ph.split()]; nw = [_norm(w['w']) for w in ws]
        hit = next((i for i in range(len(nw)) if nw[i:i + len(want)] == want), None)
        if hit is None:
            raise SystemExit(f'{n}: phrase "{ph}" not in {sid}')
        t = ws[hit]['start']
    return round(t + float(off or 0) - starts[n], 2)


for n in names:
    body = (SRC / f'{n}.js').read_text(encoding='utf-8')
    body = re.sub(r'@\{([^}]+)\}', lambda m: str(word_time(n, m.group(1))), body)
    if n in dur:
        body = re.sub(r'duration:\s*[\d.]+', f'duration: {dur[n]:.3f}', body, count=1)
    (OUT / f'{n}.js').write_text(kit + '\n' + body, encoding='utf-8')
print(f'built {len(names)} scenes')
