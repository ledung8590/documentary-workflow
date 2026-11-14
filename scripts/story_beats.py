"""Story mode: cut image beats from the real voice timing (docs/STORY_MODE.md "Beats and image timing").

  PY scripts/story_beats.py projects/JOB "input/<name>.srt" [max_secs=7.6]

Each beat ends on a sentence end (preferred, beats of 5 s or more) or a clause end (, ; : dash) and lasts at most max_secs
from its first word to the next beat's first word; a sentence with no cut point inside the limit is cut at a word.
Writes projects/JOB/beats.json [{k, sentence, start, end, text}] (story_sheet.py captions, prompt writing) and the image
SRT with beat k at [8(k-1), 8k), so `doc.py story` starts image k on its beat's first word. Vitebsk 2026-11-14: 699 beats
for 69 min, max 7.99 s; doc.py story still found 6 images at 8.1-8.3 s (alignment drift): move the last word of beat k
into beat k+1 for each and rerun."""
import json, sys, re
from pathlib import Path

job = Path(sys.argv[1]); out = Path(sys.argv[2]); MAX = float(sys.argv[3]) if len(sys.argv) > 3 else 7.6
tm = json.loads((job / 'voice' / 'timing.json').read_text(encoding='utf-8'))['sentences']
ids = sorted(tm, key=lambda k: tm[k]['start'])
# flat word list with sentence ids
W = []
for sid in ids:
    ws = tm[sid]['words']
    for i, w in enumerate(ws):
        txt = w.get('word') or w.get('text') or w.get('w') or ''
        W.append({'sid': sid, 't': w['start'], 'e': w['end'], 'txt': txt, 'last': i == len(ws) - 1})
end_all = tm[ids[-1]]['end']

def ok_cut(i):  # may a beat start at word i?
    p = W[i - 1]
    return p['last'] or re.search(r'[,;:—-]$', p['txt'].strip()) is not None

beats = []; i = 0
def cands(i, lim):
    st = W[i]['t']; hard, soft = [], []; j = i + 1
    while j < len(W) and W[j]['t'] - st <= lim:
        (hard if W[j - 1]['last'] else soft if ok_cut(j) else []).append(j); j += 1
    return st, hard, soft, j
while i < len(W):
    st, hard, soft, j = cands(i, MAX)
    if j >= len(W) and end_all - st <= MAX + 0.4:
        nxt = len(W)
    else:
        L = lambda x: W[x]['t'] - st
        h5 = [x for x in hard if L(x) >= 5.0]; s5 = [x for x in soft if L(x) >= 5.0]
        if h5: nxt = h5[-1]
        elif s5: nxt = s5[-1]
        elif hard or soft: nxt = max(hard + soft)
        else:
            st, hard, soft, j = cands(i, 8.0)
            nxt = max(hard + soft) if hard or soft else max(i + 1, j - 1)
    beats.append((i, nxt)); i = nxt

res = []
for k, (a, b) in enumerate(beats):
    res.append({'k': k + 1, 'sentence': W[a]['sid'], 'start': round(W[a]['t'], 2),
                'end': round(W[b]['t'] if b < len(W) else end_all, 2),
                'text': ' '.join(w['txt'].strip() for w in W[a:b])})
(job / 'beats.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
def ts(s):
    h, m = int(s // 3600), int(s % 3600 // 60); return f'{h:02}:{m:02}:{s % 60:06.3f}'.replace('.', ',')
out.write_text(''.join(f'{r["k"]}\n{ts(8 * (r["k"] - 1))} --> {ts(8 * r["k"] - 0.01)}\n{r["text"]}\n\n' for r in res), encoding='utf-8')
L = [r['end'] - r['start'] for r in res]
print(len(res), 'beats; max', round(max(L), 2), 'mean', round(sum(L) / len(L), 2), '; >8 s:', sum(x > 8 for x in L))
