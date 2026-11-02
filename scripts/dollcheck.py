"""Drawn-character (K.doll) budget for a film's shot list. Archival first: dolls only where no real picture exists.

Called from each film's `plan.py check` (and runnable alone: PY scripts/dollcheck.py JOB, reads timeline.json).
A doll scene is scenes/src/NAME.js that calls `K.doll(`. Rules (user, 2026-11-02, after film 75 drew dolls in 31 % of shots):
  - at most MAX_SHARE of the shots and of the running time;
  - never more than MAX_RUN doll shots in a row;
  - none in the first HOOK_S seconds (the hook is real film/pictures);
  - each doll scene file states what real media was searched for: a `// no-real-media: ...` comment.
"""
import json, re, sys
from pathlib import Path

MAX_SHARE, MAX_RUN, HOOK_S = 0.10, 2, 60.0
REASON = re.compile(r'//\s*no-real-media:\s*\S')


def doll_scenes(d):
    out = {}
    for f in (Path(d) / 'scenes' / 'src').glob('*.js'):
        if f.name.startswith('_'):
            continue
        s = f.read_text(encoding='utf-8')
        if 'K.doll(' in s:
            out[f.stem] = bool(REASON.search(s))
    return out


def check(d, shots):
    """shots: list of dicts with t0, t1, src ('scene:NAME', 'pick:..', ...). Prints findings, returns the warning count."""
    dolls = doll_scenes(d)
    is_doll = [s['src'].startswith('scene:') and s['src'][6:] in dolls for s in shots]
    n = sum(is_doll); total = sum(s['t1'] - s['t0'] for s in shots) or 1
    secs = sum(s['t1'] - s['t0'] for s, k in zip(shots, is_doll) if k)
    warn = 0
    msg = f'drawn characters: {n}/{len(shots)} shots ({n / max(len(shots), 1):.0%}), {secs:.0f}s of {total:.0f}s ({secs / total:.0%}); limit {MAX_SHARE:.0%}'
    if n > MAX_SHARE * len(shots) or secs > MAX_SHARE * total:
        msg = '!! ' + msg + ': replace dolls with real pictures, modern stand-ins (illustrative), maps or plain graphics'
        warn += 1
    print(msg)
    run = 0
    for i, (s, k) in enumerate(zip(shots, is_doll)):
        run = run + 1 if k else 0
        if run == MAX_RUN + 1:
            print(f'!! {run}+ doll shots in a row from shot {i - run + 1} ({shots[i - run + 1]["t0"]:.1f}s)'); warn += 1
        if k and s['t0'] < HOOK_S:
            print(f'!! doll scene {s["src"]} at {s["t0"]:.1f}s inside the {HOOK_S:.0f}s hook'); warn += 1
    used = {s['src'][6:] for s, k in zip(shots, is_doll) if k}
    for name in sorted(used):
        if not dolls[name]:
            print(f'!! scenes/src/{name}.js draws dolls without a "// no-real-media: <what was searched>" line'); warn += 1
    return warn


if __name__ == '__main__':
    d = Path(sys.argv[1]) if Path(sys.argv[1]).is_dir() else Path(__file__).resolve().parents[1] / 'projects' / sys.argv[1]
    tl = json.loads((d / 'timeline.json').read_text(encoding='utf-8'))
    tr = next(t for t in tl['tracks'] if t.get('id') == 'video')
    shots = []
    for c in tr['clips']:
        m = re.match(r'media/scene-([\w-]+)\.\w+$', c.get('src') or '')
        shots.append({'t0': c['start'], 't1': c['end'], 'src': f'scene:{m.group(1)}' if m else c.get('src') or ''})
    sys.exit(1 if check(d, shots) else 0)
