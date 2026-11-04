"""Footage or pictures an earlier film already showed (film 88, 2026-11-04: the opening cannon had already opened films 6 and 75).
Searches return the same few Commons files, and plan.py's own repeat check only sees one film. Compares by source id against
evidence/*/project/timeline.json. check(D, sh) prints one !! line per repeat and returns the count."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARD_SECONDS = 90  # user 2026-11-04: with hundreds of films a total ban is impractical; !! for this opening and all film cuts, ! for later stills


def source_id(name):
    m = re.search(r'(commons|dvids|nara|openverse)-([\w-]+?)\.\w+$', Path(name).name)
    return f'{m.group(1)}-{m.group(2)}' if m else None


def past_films():
    """{source id: [film number or name, ...]} from every finished film."""
    out = {}
    for p in sorted(ROOT.glob('evidence/*/project/timeline.json')):
        film = p.parents[1].name.split('.')[0]
        try:
            tl = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for t in tl.get('tracks', []):
            if t.get('id') != 'video':
                continue
            for c in t.get('clips', []):
                for s in [c.get('src')] + list(c.get('uses') or []):
                    k = source_id(s) if s else None
                    if k and film not in out.setdefault(k, []):
                        out[k].append(film)
    return out


def check(D, sh):
    past = past_films(); warn = 0
    for i, s in enumerate(sh):
        kind, _, rest = s['src'].partition(':')
        if kind not in ('pick', 'vid'):
            continue
        tag, _, k = rest.split('@')[0].partition('#')
        try:
            c = json.loads((Path(D) / 'media' / 'candidates' / tag / 'candidates.json').read_text(encoding='utf-8'))['candidates'][int(k) - 1]
        except (OSError, IndexError, ValueError, KeyError):
            continue
        key = f"{c['source'].split(':')[0]}-{re.sub(r'[^A-Za-z0-9_-]', '', str(c['id']))}"
        if key in past:
            hard = s['t0'] < HARD_SECONDS or kind == 'vid'  # the opening and film cuts are what viewers recognise; later stills may repeat
            print(f'{"!!" if hard else "!"} shot {i} {s["src"]}: already in film {", ".join(past[key])} ({key})')
            warn += 1
    return warn
