"""Measure ducked music vs voice (LUFS) in a 50 s window in the middle of every music bed. PY qa/music_level.py [first last]"""
import json, re, subprocess, sys
from pathlib import Path

D = Path(__file__).resolve().parents[1]
ROOT = D.parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'studio')]
import render as R  # noqa: E402

tl = json.loads((D / 'timeline.json').read_text(encoding='utf-8'))
mus = [c for t in tl['tracks'] if t['id'] == 'music' for c in t['clips']]
a, b = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, len(mus))


def lufs(p):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(p), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    return float(m[-1]) if m else None


out = D / 'qa' / 'lvl'; out.mkdir(exist_ok=True)
for m in mus[a:b]:
    mid = (m['start'] + m['end']) / 2; t0, t1 = max(m['start'] + 5, mid - 25), min(m['end'] - 5, mid + 25)
    res = {}
    for k in ('music', 'voice'):
        p = out / f'premix_{m["id"]}_{k}.wav'
        R.premix(D, tl, p, t0, t1, only={k})
        res[k] = lufs(p); p.unlink(missing_ok=True)
    diff = None if None in res.values() else res['voice'] - res['music']
    flag = '' if diff and 29.5 <= diff <= 33 else '  <-- adjust'
    print(f"{m['id']} {m['mood']:12s} {m['src'].split('music/')[-1]:22s} gain {m['gain_db']:6.1f}  voice {res['voice']}  music {res['music']}  "
          f"diff {diff if diff is None else round(diff, 1)}{flag}", flush=True)
