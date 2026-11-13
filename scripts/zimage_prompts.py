"""Turn @Name scene prompts (the TST/Flow format with reference images) into Z-Image jobs (no reference images):
each visible character gets a fixed `Character Sheet: Name (look)` sentence and the whole film one `Seed:` (the
format of G:\\YOUTUBE\\US- Military Chronicle\\GEM_PROMPT_MILITARY_CHRONICLE.txt). docs/ZIMAGE.md.

    PY scripts/zimage_prompts.py chars.json out_jobs.json prompts_A.jsonl [prompts_B.jsonl ...] [--seed 44817]
        [--style "black-and-white war documentary style."] [--tail "Authentic 1944 period photograph, ..."]

chars.json: {"Joachim": "Joachim Lederle (German, 26 years old, round face, small round wire-rimmed spectacles, ...)",
             "Tank632": {"object": "a German Panzer IV medium tank with steel side skirts, a long 75 mm gun"}}
  a person -> "@Name (short look)" becomes the name, and the full sheet goes after the camera sentence;
  an object -> "@Name" becomes the object's words (no sheet).
prompts_*.jsonl: {"n": 12, "refs": [...], "prompt": "Medium shot, low angle, static, hard sun. @Joachim (glasses) ..."}
out: [{"n": 12, "prompt": "..."}] for scripts/zimage_batch.py.
"""
import argparse, json, re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('chars'); ap.add_argument('out'); ap.add_argument('prompts', nargs='+')
ap.add_argument('--seed', type=int, default=44817)
ap.add_argument('--style', default='black-and-white war documentary style.')
ap.add_argument('--tail', default='Authentic period photograph, well exposed, clear detail, full tonal range.')
a = ap.parse_args()
chars = json.loads(Path(a.chars).read_text(encoding='utf-8'))
people = {k: v for k, v in chars.items() if isinstance(v, str)}
objects = {k: v['object'] for k, v in chars.items() if isinstance(v, dict)}
names = '|'.join(map(re.escape, sorted(chars, key=len, reverse=True)))
# the image prompts' own closing style sentence (TST/Flow house style) is replaced by --tail
STYLE_END = re.compile(r'\s*Black and white \d{4}s.*$', re.S | re.I)

rows = []
for f in a.prompts:
    rows += [json.loads(line) for line in Path(f).read_text(encoding='utf-8').splitlines() if line.strip()]
rows.sort(key=lambda r: r['n'])
out, unknown = [], set()
for r in rows:
    p = STYLE_END.sub('', re.sub('["“”]', '', r['prompt'])).strip()
    seen = []

    def sub(m):
        n = m.group(1)
        if n in objects:
            return objects[n]
        if n not in seen:
            seen.append(n)
        return people[n].split(' (')[0]
    p = re.sub(rf'@({names})\b(\s*\([^)]*\))?', sub, p)
    unknown |= set(re.findall(r'@(\w+)', p))
    m = re.match(r'([^.]*\.)\s*(.*)', p, re.S)   # first sentence = shot size, angle, camera, light
    cam, rest = (m.group(1), m.group(2)) if m else ('', p)
    sheets = ' '.join(f'Character Sheet: {people[n]}.' for n in seen)
    z = f'{a.style} {cam} {sheets} {rest} {a.tail} Seed: {a.seed}.'
    out.append({'n': r['n'], 'prompt': re.sub(r'\s+', ' ', z).strip()})
Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
print(f'{len(out)} jobs -> {a.out}' + (f'; !! unknown @names {sorted(unknown)}' if unknown else ''))
print(out[0]['prompt'])
